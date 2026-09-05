import asyncio
import websockets

async def handle_connection(websocket):
    print("A client connected!")
    try:
        async for message in websocket:
            print("Received message:", message)
    except websockets.exceptions.ConnectionClosed:
        print("Client disconnected.")

async def main():
    print("WebSocket server starting on ws://localhost:8765 ...")
    async with websockets.serve(handle_connection, "localhost", 8765):
        await asyncio.Future()  # runs forever until you stop it (Ctrl+C)

asyncio.run(main())