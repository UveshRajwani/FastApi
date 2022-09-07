from typing import List

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

app = FastAPI()

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
            <input type="text" id="messageText" autocomplete="off"/>
            <button>Send</button>
        </form>
        <ul id='messages'>
        </ul>
        <script>
            var client_id = Date.now()
            document.querySelector("#ws-id").textContent = client_id;
            var ws = new WebSocket(`ws://localhost:8000/ws/${client_id}`);
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


class WebUser:
    def __init__(self, userid: int, websocket: WebSocket):
        self.userid = userid
        self.websocket = websocket


class Player(BaseModel):
    name: str
    image: str
    start: int


class PlayersModel(BaseModel):
    players_model: List[Player]


# class Player:
#     def __init__(self, name: str, image: str, price: int):
#         self.name = name
#         self.image = image
#         self.price = price


class ConnectionManager:
    def __init__(self):
        self.active_connections = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()

    def disconnect(self, user: WebUser):
        self.active_connections.remove(user)

    def add_to_active_list(self, user: WebUser):
        self.active_connections.append(user)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str, ):
        for connection in self.active_connections:
            await connection.websocket.send_text(message)
            # if connection != websocket:
            #     await connection.send_text(message)


manager = ConnectionManager()


@app.get("/")
async def get():
    return HTMLResponse(html)


@app.post("/add-auction")
def add_players(players_model: PlayersModel):
    players_dict = players_model.dict()
    for player in players_dict['players_model']:
        auction.append(player)
    return auction


@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: int):
    await manager.connect(websocket)
    user = WebUser(userid=client_id, websocket=websocket)
    manager.add_to_active_list(user)
    try:
        while True:
            data = await websocket.receive_text()
            print(manager.active_connections)
            print(data, type(data), int(data))
            await manager.broadcast(f"Client #{client_id} says: {data}")
    except WebSocketDisconnect:
        manager.disconnect(user)
        await manager.broadcast(f"Client #{client_id} left the chat")
