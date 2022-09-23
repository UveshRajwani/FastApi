import json.decoder
from typing import List, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import random
import os
from fastapi.responses import FileResponse
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
types_of_events = ["new_bid", "player_unsold", "player_sold", "start_auction", "next_player", "show_teams", "update_money"]


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


class post_mentor(BaseModel):
    name: str


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
        if user.userid == "view-only":
            self.view_only_connection = None
        else:
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

        elif receivers == "all":
            await self.send_personal_message(message, self.view_only_connection.websocket)
            await self.broadcast(message)
        else:
            for m in manager.active_connections:
                if receivers == m.userid:
                    print("kal")
                    await self.send_personal_message(message, m.websocket)

manager = ConnectionManager()


class Events:
    class_return: json
    current_index: int = 0
    current_player: Player
    auction_started = False

    @classmethod
    def event(cls, func, *args, **kwargs):
        getattr(cls, func)(*args, **kwargs)
        return cls.class_return

    @classmethod
    def start_auction(cls):
        cls.auction_started = True
        print(cls.auction_started)
        cls.current_player = auction[cls.current_index]
        cls.class_return = {"message": cls.current_player, "receiver": "view_only"}

    @classmethod
    def player_unsold(cls):
        player_unsold.append(cls.current_player)
        cls.next_player()
    @classmethod
    def update_money(cls, **kwargs):
        for mentor in manager.active_connections:
            money = 0
            if mentor.userid == kwargs["mentor"]:
                money = mentor.money
            cls.class_return = {"message": {"money": money}, "receiver": kwargs["mentor"]}
    @classmethod
    def new_bid(cls, **kwargs):
        cls.current_player['price'] += kwargs["price"]
        cls.current_player["bid_by"] = kwargs["bid_by"]
        cls.class_return = {"message": cls.current_player, "receiver": "view_only"}

    @classmethod
    def player_sold(cls, **kwargs):
        print("i was called")
        cls.current_player['sold_to'] = kwargs["sold_to"]
        m = ""
        for mentor in manager.active_connections:
            if mentor.userid == kwargs["sold_to"]:
                manager.disconnect(mentor)
                mentor.team.append(cls.current_player)
                mentor.money -= cls.current_player["price"]
                print(f"team : {mentor.team}")
                m = mentor
        manager.add_to_active_list(m)
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
        cls.class_return = {"message": {"event":"end_auction"}, "receiver": "all"}

    @classmethod
    def show_teams(cls):
        all_teams = []
        for mentor in manager.active_connections:
            team = {mentor.userid: mentor.team}
            all_teams.append(team)
        unsold = {"unsold": player_unsold}
        all_teams.append(unsold)
        cls.class_return = {"message": {"teams": all_teams}, "receiver": "view_only"}


event = Events()
player_unsold_sounds = ["thukra.mp3", "bewafa.mp3"]
player_sold_sounds = ["jio.mp3", "papa.mp3"]


@app.get("/")
async def get():
    return HTMLResponse(html)

@app.get("/show_teams")
def show_teams():
    all_teams = []
    for mentor in manager.active_connections:
            team = {mentor.userid: mentor.team}
            all_teams.append(team)
    unsold = {"unsold": player_unsold}
    all_teams.append(unsold)
    return {"teams": all_teams}
@app.get("/download/{event_name}")
def download_file(event_name: str):
    if event_name == "player_unsold":
        name_file = random.choice(seq=player_unsold_sounds)
    else:
        name_file = random.choice(seq=player_sold_sounds)
    print(name_file)
    if os.path.isfile(name_file):
        print("hello")
        return FileResponse(name_file)
    # return FileResponse(path=name_file, media_type='application/octet-stream', filename=name_file)


@app.post("/add-mentor")
async def add_mentor(name: post_mentor):
    message = name.dict()
    print(name.dict())
    await manager.data_sender(message=name.dict(), receivers="view_only")


@app.get("/start-aution")
async def start_auction():
    await manager.data_sender(message={"event": "start_auction"}, receivers="mentors_only")


@app.post("/add-auction")
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
        print(client_id)
        if not event.auction_started:
            print("helloo")
            await manager.data_sender(message={"name": client_id}, receivers="view_only")
        else:
            await manager.send_personal_message(message={"money": user.money}, websocket=websocket)
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
        print(f"WebSocketDisconnect : {user.userid}")
        manager.disconnect(user)
