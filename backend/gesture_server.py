import asyncio
import json
import time

import pyautogui
import websockets

# ---------- Settings ----------
pyautogui.PAUSE = 0          # remove pyautogui's default 0.1s delay after each call
pyautogui.FAILSAFE = True    # slam mouse into top-left corner to abort (safety net)

HOST = "localhost"
PORT = 8765
MIN_MOVE_INTERVAL = 1 / 60   # max ~60 move updates per second
SCROLL_AMOUNT = 300
DRAG_TIMEOUT = 0.3           # release drag if no drag message for this many seconds

screen_width, screen_height = pyautogui.size()
print(f"Screen size: {screen_width}x{screen_height}")

# ---------- State ----------
last_move_time = 0.0
dragging = False
last_drag_time = 0.0


def to_pixels(x_norm, y_norm):
    """Convert normalized 0-1 coordinates to screen pixels (kept away from the
    exact corners so pyautogui's fail-safe isn't triggered by accident)."""
    x_px = int(x_norm * screen_width)
    y_px = int(y_norm * screen_height)
    x_px = max(1, min(screen_width - 2, x_px))
    y_px = max(1, min(screen_height - 2, y_px))
    return x_px, y_px


def valid_coords(data):
    x, y = data.get("x"), data.get("y")
    return isinstance(x, (int, float)) and isinstance(y, (int, float))


def end_drag():
    global dragging
    if dragging:
        pyautogui.mouseUp()
        dragging = False
        print("Drag released")


def handle_gesture(data):
    global last_move_time, dragging, last_drag_time

    try:
        gesture_type = data.get("type")
        now = time.monotonic()

        # Any non-drag message ends an active drag
        if gesture_type != "drag":
            end_drag()

        if gesture_type == "move":
            if not valid_coords(data):
                print("Move message missing valid x/y")
                return
            if now - last_move_time < MIN_MOVE_INTERVAL:
                return  # too soon since last move, skip it
            last_move_time = now
            x_px, y_px = to_pixels(data["x"], data["y"])
            pyautogui.moveTo(x_px, y_px)

        elif gesture_type == "click":
            button = data.get("button", "left")
            if button not in ("left", "right"):
                print("Unknown button:", button)
                return
            pyautogui.click(button=button)
            print(f"Click: {button}")

        elif gesture_type == "scroll":
            direction = data.get("direction")
            if direction not in ("up", "down"):
                print("Unknown scroll direction:", direction)
                return
            pyautogui.scroll(SCROLL_AMOUNT if direction == "up" else -SCROLL_AMOUNT)
            print(f"Scroll: {direction}")

        elif gesture_type == "drag":
            if not valid_coords(data):
                print("Drag message missing valid x/y")
                return
            x_px, y_px = to_pixels(data["x"], data["y"])
            if not dragging:
                pyautogui.moveTo(x_px, y_px)
                pyautogui.mouseDown()
                dragging = True
                print("Drag started")
            elif now - last_drag_time >= MIN_MOVE_INTERVAL:
                pyautogui.moveTo(x_px, y_px)
            last_drag_time = now

        else:
            print("Unknown gesture type:", gesture_type)

    except Exception as e:
        print("Error handling gesture:", e)


async def drag_watchdog():
    """Release the mouse button if drag messages stop arriving."""
    while True:
        await asyncio.sleep(0.1)
        if dragging and time.monotonic() - last_drag_time > DRAG_TIMEOUT:
            end_drag()


async def handle_connection(websocket):
    print("Browser connected!")
    try:
        async for message in websocket:
            try:
                data = json.loads(message)
            except json.JSONDecodeError:
                print("Received invalid JSON:", message)
                continue
            if not isinstance(data, dict):
                print("Message must be a JSON object")
                continue
            handle_gesture(data)
    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        end_drag()  # never leave the mouse button stuck down
        print("Browser disconnected.")


async def main():
    print(f"Gesture WebSocket server starting on ws://{HOST}:{PORT} ...")
    asyncio.create_task(drag_watchdog())
    async with websockets.serve(handle_connection, HOST, PORT):
        await asyncio.Future()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        end_drag()
        print("Server stopped.")