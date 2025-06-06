from enum import Enum
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
import uvicorn

app = FastAPI()


class EventType(str, Enum):
    CONNECT = "connect"
    DISCONNECT = "disconnect"
    MESSAGE = "message"


class Message(BaseModel):
    client_id: str
    event_type: EventType


class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: Message):
        for connection in self.active_connections:
            await connection.send_json(message.model_dump())

    async def broadcastConnect(self, client_id: str):
        await self.broadcast(Message(client_id=client_id, event_type=EventType.CONNECT))

    async def broadcastDisconnect(self, client_id: str):
        await self.broadcast(
            Message(client_id=client_id, event_type=EventType.DISCONNECT)
        )

    async def broadcastMessage(self, client_id: str):
        await self.broadcast(Message(client_id=client_id, event_type=EventType.MESSAGE))


manager = ConnectionManager()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, client_id: str = ""):
    await manager.connect(websocket)

    await manager.broadcastConnect(client_id)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "update":
                await manager.broadcastMessage(client_id)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        await manager.broadcastDisconnect(client_id)


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
