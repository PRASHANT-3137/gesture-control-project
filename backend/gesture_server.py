import asyncio
import json
import time

import pyautogui
import websockets

# ---------- Settings ----------
pyautogui.PAUSE = 0          # remove pyautogui's default 0.1s delay after each call
pyautogui.FAILSAFE = True    # slam mouse into top-left corner to pause control (safety net)

HOST = "localhost"
PORT = 8765

# Only pages served from these addresses may drive the mouse.
# None = clients that send no Origin header (not browsers).
# If you open index.html straight from disk (file://), browsers send "null" and are blocked:
# serve it with  python -m http.server 5500  and open http://localhost:5500
ALLOWED_ORIGINS = [None, "http://localhost:5500", "http://127.0.0.1:5500"]

LOOP_HZ = 120                # how often the newest cursor position is applied
SCROLL_AMOUNT = 300
CLICK_HOLD_TIME = 0.04       # button stays down this long so apps register the click
DRAG_SETTLE_TIME = 0.02      # pause after button-down before the drag starts moving
DRAG_TIMEOUT = 0.6           # release drag if no drag message for this many seconds

screen_width, screen_height = pyautogui.size()
print(f"Screen size: {screen_width}x{screen_height}")

# ---------- State ----------
target = None                # newest wanted cursor position (pixels)
applied = None               # last position actually applied
dragging = False
last_drag_time = 0.0
failsafe_active = False


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


def guarded(fn, *args, **kwargs):
    """Call a pyautogui function. Returns False if the fail-safe corner blocked it."""
    global failsafe_active
    try:
        fn(*args, **kwargs)
        failsafe_active = False
        return True
    except pyautogui.FailSafeException:
        if not failsafe_active:
            print("Fail-safe corner active: control paused until the mouse leaves the top-left corner")
            failsafe_active = True
        return False


def apply_target():
    """Move the real cursor to the newest wanted position (older ones are skipped)."""
    global applied
    if target is not None and target != applied:
        if guarded(pyautogui.moveTo, target[0], target[1]):
            applied = target


def end_drag():
    global dragging
    if dragging:
        apply_target()                       # release at the newest position
        if guarded(pyautogui.mouseUp):
            dragging = False
            print("Drag released")


async def handle_gesture(data):
    global target, dragging, last_drag_time

    try:
        gesture_type = data.get("type")
        now = time.monotonic()

        if gesture_type == "move":
            if not valid_coords(data):
                print("Move message missing valid x/y")
                return
            target = to_pixels(data["x"], data["y"])
            end_drag()                       # a plain move means the fist was opened

        elif gesture_type == "drag":
            if not valid_coords(data):
                print("Drag message missing valid x/y")
                return
            target = to_pixels(data["x"], data["y"])
            last_drag_time = now
            if not dragging:
                apply_target()
                if guarded(pyautogui.mouseDown):
                    dragging = True
                    print("Drag started")
                    await asyncio.sleep(DRAG_SETTLE_TIME)

        else:
            end_drag()                       # any other message ends an active drag

            if gesture_type == "click":
                button = data.get("button", "left")
                if button not in ("left", "right"):
                    print("Unknown button:", button)
                    return
                apply_target()               # land exactly on the newest position
                if guarded(pyautogui.mouseDown, button=button):
                    await asyncio.sleep(CLICK_HOLD_TIME)
                    guarded(pyautogui.mouseUp, button=button)
                    print(f"Click: {button}")

            elif gesture_type == "scroll":
                direction = data.get("direction")
                if direction not in ("up", "down"):
                    print("Unknown scroll direction:", direction)
                    return
                amount = SCROLL_AMOUNT if direction == "up" else -SCROLL_AMOUNT
                if guarded(pyautogui.scroll, amount):
                    print(f"Scroll: {direction}")

            else:
                print("Unknown gesture type:", gesture_type)

    except Exception as e:
        print("Error handling gesture:", e)


async def background_loop():
    """Applies only the newest cursor position at a fixed rate, and releases
    the mouse button if drag messages stop arriving."""
    interval = 1.0 / LOOP_HZ
    while True:
        try:
            apply_target()
            if dragging and time.monotonic() - last_drag_time > DRAG_TIMEOUT:
                end_drag()
        except Exception as e:
            print("Background loop error:", e)
        await asyncio.sleep(interval)


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
            await handle_gesture(data)
    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        end_drag()  # never leave the mouse button stuck down
        print("Browser disconnected.")


async def main():
    print(f"Gesture WebSocket server starting on ws://{HOST}:{PORT} ...")
    background = asyncio.create_task(background_loop())   # keep a reference so it isn't garbage-collected
    try:
        async with websockets.serve(handle_connection, HOST, PORT, origins=ALLOWED_ORIGINS):
            await asyncio.Future()
    finally:
        background.cancel()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        end_drag()
        print("Server stopped.")