import pyautogui
import time

print("Your screen size is:", pyautogui.size())
print("Testing in 3 seconds...")
time.sleep(3)

# Move to a safe spot first
pyautogui.moveTo(500, 500, duration=1)

# Left click
print("Left clicking...")
pyautogui.click(button='left')
time.sleep(1)

# Right click
print("Right clicking...")
pyautogui.click(button='right')
time.sleep(1)

# Scroll up (positive number = scroll up)
print("Scrolling up...")
pyautogui.scroll(300)
time.sleep(1)

# Scroll down (negative number = scroll down)
print("Scrolling down...")
pyautogui.scroll(-300)

print("Done!")