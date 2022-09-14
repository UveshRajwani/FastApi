import json.decoder
from typing import List, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from enum import Enum
import json
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

html = """
<!DOCTYPE html>
<html>
    <head>
        <title>Chat</title>
    </head>
    <body>
        <h1>WebSocket Chat</h1>
        <h2>Your ID: <span id="ws-id"></span></h2>
        <form action="" onsubmit="sendMessage(event)">
            <input type="json" id="messageText" autocomplete="off"/>
            <button>Send</button>
        </form>
        <ul id='messages'>
        </ul>
        <script>
            var client_id = Date.now()
            document.querySelector("#ws-id").textContent = client_id;
            var ws = new WebSocket(`ws://localhost:8000/ws/hello`);
            ws.onmessage = function(event) {
                var messages = document.getElementById('messages')
                var message = document.createElement('li')
                var content = document.createTextNode(event.data)
                message.appendChild(content)
                messages.appendChild(message)
            };
            function sendMessage(event) {
                var input = document.getElementById("messageText")
                ws.send(input.value)
                input.value = ''
                event.preventDefault()
            }
        </script>
    </body>
</html>
"""
auction = []
player_unsold = []
types_of_events = ["new_bid", "player_unsold", "player_sold", "start_auction", "next_player", "show_teams"]


class WebUser:
    def __init__(self, userid: str, websocket: WebSocket):
        self.userid = userid
        self.websocket = websocket


class Player(BaseModel):
    name: str
    image: str
    price: int
    bid_by: Optional[str] = None
    sold_to: Optional[str] = None


class PlayersModel(BaseModel):
    players_model: List[Player]


class MentorModel(WebUser):
    def __init__(self, userid: str, websocket: WebSocket, team: List, money: int):
        WebUser.__init__(self, userid, websocket)
        self.team = team
        self.money = money


# class Player:
#     def __init__(self, name: str, image: str, price: int):
#         self.name = name
#         self.image = image
#         self.price = price


class ConnectionManager:
    def __init__(self):
        self.view_only_connection = None
        self.active_connections = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()

    def disconnect(self, user: WebUser):
        self.active_connections.remove(user)

    def add_to_active_list(self, user: WebUser):
        self.active_connections.append(user)

    def add_view_only_websocket(self, user: WebUser):
        self.view_only_connection = user

    async def send_personal_message(self, message: json, websocket: WebSocket):
        await websocket.send_json(data=message)

    async def broadcast(self, message: json, ):
        for connection in self.active_connections:
            await connection.websocket.send_json(data=message)

    async def data_sender(self, message: json, receivers):
        print(message, receivers)
        if receivers == "view_only":
            await self.send_personal_message(message, self.view_only_connection.websocket)
        elif receivers == "mentors_only":
            await self.broadcast(message)
        else:
            await self.send_personal_message(message, self.view_only_connection.websocket)
            await self.broadcast(message)


manager = ConnectionManager()


class Events:
    class_return: json
    current_index: int = 0
    current_player: Player

    @classmethod
    def event(cls, func, *args, **kwargs):
        getattr(cls, func)(*args, **kwargs)
        return cls.class_return

    @classmethod
    def start_auction(cls):
        cls.current_player = auction[cls.current_index]
        cls.class_return = {"message": cls.current_player, "receiver": "view_only"}

    @classmethod
    def player_unsold(cls):
        player_unsold.append(cls.current_player)
        cls.next_player()

    @classmethod
    def new_bid(cls, **kwargs):
        cls.current_player['price'] += kwargs["price"]
        cls.current_player["bid_by"] = kwargs["bid_by"]
        cls.class_return = {"message": cls.current_player, "receiver": "view_only"}

    @classmethod
    def player_sold(cls, **kwargs):
        cls.current_player['sold_to'] = kwargs["sold_to"]
        m = ""
        for mentor in manager.active_connections:
            if mentor.userid == kwargs["sold_to"]:
                manager.disconnect(mentor)
                mentor.team.append(cls.current_player)
                mentor.money -= cls.current_player["price"]
                m = mentor
            manager.add_to_active_list(m)
        cls.class_return = {"message": {"player": cls.current_player}, "receiver": "view_only"}
        cls.next_player()

    @classmethod
    def next_player(cls, **kwargs):
        if cls.current_index < len(auction) - 1:
            cls.current_index += 1
            cls.current_player = auction[cls.current_index]
            cls.class_return = {"message": cls.current_player, "receiver": "view_only"}
        else:
            cls.end_auction()

    @classmethod
    def end_auction(cls):
        cls.class_return = {"message": "end_auction", "receiver": "all"}

    @classmethod
    def show_teams(cls):
        all_teams = []
        for mentor in manager.active_connections:
            all_teams.append(f"{mentor.userid}:{mentor.team}")
        all_teams.append(f"unSold:{player_unsold}")
        jsonStr = json.dumps(all_teams)
        cls.class_return = {"message": all_teams, "receiver": "all"}


event = Events()


@app.get("/")
async def get():
    return HTMLResponse(html)


@app.post("/add-auction")
# @app.options("/add-auction")
def add_players(players_model: PlayersModel):
    players_dict = players_model.dict()
    for player in players_dict['players_model']:
        auction.append(player)
    return {"done": "done"}


@app.get("/get-auction")
def add_auction():
    return {"players": auction}


@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await manager.connect(websocket)
    if client_id == "view-only":
        user = WebUser(userid=client_id, websocket=websocket)
        print("here")
        manager.add_view_only_websocket(user)
    else:
        user = MentorModel(userid=client_id, websocket=websocket, team=[], money=600)
        manager.add_to_active_list(user)
    try:
        while True:

            try:
                data = await websocket.receive_json()
                print(data)
                if data["event"] in types_of_events:
                    try:
                        res = event.event(data["event"], **data["para"])
                    except KeyError:
                        res = event.event(data["event"])
                    await manager.data_sender(message=res["message"], receivers=res["receiver"])
            except json.decoder.JSONDecodeError:
                pass

    except WebSocketDisconnect:
        manager.disconnect(user)
        await manager.broadcast(f"Client #{client_id} left the chat")
