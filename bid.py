import json.decoder
from typing import List, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

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
player_sold = []
types_of_events = ["new_bid", "player_unsold", "player_sold", "start_auction", "next_player", "show_teams", "end_auction"]


class WebUser:
    def __init__(self, userid: str, websocket: WebSocket):
        self.userid = userid
        self.websocket = websocket


class Player(BaseModel):
    name: str
    image: str
    price: float
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


async def send_message_to_view_only(message: json, websocket: WebSocket):
    await websocket.send_json(data=message)


class ConnectionManager:
    def __init__(self):
        self.active_connections = []
        self.view_only_connection: WebUser

    async def connect(self, websocket: WebSocket):
        await websocket.accept()

    def disconnect(self, user: WebUser):
        if user.userid == "view-only":
            self.view_only_connection: Optional[WebUser] = None
        else:
            self.active_connections.remove(user)

    def add_to_active_list(self, user: WebUser):
        self.active_connections.append(user)

    async def send_personal_message(self, message: json, websocket: WebSocket):
        print("hello")
        await websocket.send_json(data=message)

    async def broadcast(self, message: json, ):
        for connection in self.active_connections:
            await connection.websocket.send_json(data=message)

            # if connection != websocket
            #     await connection.send_text(message)


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
    def new_bid(cls, **kwargs):
        cls.current_player = auction[cls.current_index]
        cls.current_player['price'] += kwargs["price"]
        cls.current_player["bid_by"] = kwargs["bid_by"]
        cls.class_return = cls.current_player

    @classmethod
    def next_player(cls, **kwargs):
        if cls.current_index < len(auction) - 1:
            cls.current_index += 1
            cls.current_player = auction[cls.current_index]
            cls.class_return = cls.current_player
        else:
            cls.end_auction()

    @classmethod
    def end_auction(cls):
        cls.class_return = {"end_auction": True}




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
        manager.view_only_connections = user
    else:
        user = MentorModel(userid=client_id, websocket=websocket, team=[], money=60)
        manager.add_to_active_list(user)
    try:
        while True:

            try:
                data = await websocket.receive_json()
                print(data["para"])
                if data["event"] in types_of_events:
                    res = event.event(data["event"], **data["para"])
                    await send_message_to_view_only(websocket=manager.view_only_connections.websocket, message=res)
                    print(len(auction))
            except json.decoder.JSONDecodeError:
                pass

    except WebSocketDisconnect:
        manager.disconnect(user)
        await manager.broadcast(f"Client #{client_id} left the chat")
