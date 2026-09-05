import asyncio
import json
import pyautogui
import websockets

# Get your screen size once at startup
screen_width, screen_height = pyautogui.size()
print(f"Screen size: {screen_width}x{screen_height}")

async def handle_connection(websocket):
    print("Browser connected!")
    try:
        async for message in websocket:
            try:
                data = json.loads(message)
                handle_gesture(data)
            except json.JSONDecodeError:
                print("Received invalid JSON:", message)
    except websockets.exceptions.ConnectionClosed:
        print("Browser disconnected.")

def handle_gesture(data):
    try:
        gesture_type = data.get("type")

        if gesture_type == "move":
            x_norm = data.get("x")
            y_norm = data.get("y")
            x_px = int(x_norm * screen_width)
            y_px = int(y_norm * screen_height)
            pyautogui.moveTo(x_px, y_px)
            print(f"Move to ({x_px}, {y_px})")

        elif gesture_type == "click":
            button = data.get("button", "left")
            pyautogui.click(button=button)
            print(f"Click: {button}")

        elif gesture_type == "scroll":
            direction = data.get("direction")
            amount = 300 if direction == "up" else -300
            pyautogui.scroll(amount)
            print(f"Scroll: {direction}")

        elif gesture_type == "drag":
            x_norm = data.get("x")
            y_norm = data.get("y")
            x_px = int(x_norm * screen_width)
            y_px = int(y_norm * screen_height)
            pyautogui.dragTo(x_px, y_px, duration=0.2)
            print(f"Drag to ({x_px}, {y_px})")

        else:
            print("Unknown gesture type:", gesture_type)

    except Exception as e:
        print("Error handling gesture:", e)

async def main():
    print("Gesture WebSocket server starting on ws://localhost:8765 ...")
    async with websockets.serve(handle_connection, "localhost", 8765):
        await asyncio.Future()

asyncio.run(main())