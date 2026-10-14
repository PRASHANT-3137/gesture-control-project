import pyautogui
import time

print("Your screen size is:", pyautogui.size())

print("Moving mouse in 3 seconds... move your hand away from the mouse!")
time.sleep(3)

# Move cursor to hardcoded position (x=500, y=500)
pyautogui.moveTo(500, 500, duration=1)

print("Done! Cursor should now be at (500, 500)")