import asyncio
import websockets

async def listen_to_suggestions():
    uri = "ws://localhost:8000/ws/suggestions"
    async with websockets.connect(uri) as websocket:
        print("Connected to WebSocket server")
        while True:
            message = await websocket.recv()
            print(f"Received suggestion: {message}")

if __name__ == "__main__":
    asyncio.run(listen_to_suggestions())