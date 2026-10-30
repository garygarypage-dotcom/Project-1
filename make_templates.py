import cv2
import mss
import numpy as np
import pygetwindow as gw
import sys

print("--- AUTOMATED LIVE TEMPLATE GENERATOR ---")

# Target your Moonlight stream window
all_windows = gw.getAllWindows()
moonlight_win = None
ignore_list = ["chrome", "edge", "firefox", "cmd", "command prompt", "notepad"]

for win in all_windows:
    title_lower = win.title.lower()
    if "moonlight" in title_lower and not any(ignore in title_lower for ignore in ignore_list):
        moonlight_win = win
        break

if not moonlight_win:
    print("\n[!] ERROR: Could not find your Moonlight app window.")
    print("Make sure Moonlight is open and streaming before running this script!")
    sys.exit()

# Activate and bring the window to focus
try:
    moonlight_win.activate()
except:
    pass

# Capture the exact current stream dimensions live
monitor = {
    "top": moonlight_win.top,
    "left": moonlight_win.left,
    "width": moonlight_win.width,
    "height": moonlight_win.height
}

with mss.MSS() as sct:
    # Grab the screen matrix
    screen = np.array(sct.grab(monitor))
    img = cv2.cvtColor(screen, cv2.COLOR_BGRA2BGR)
    h, w, _ = img.shape
    
    print(f"[+] Live Stream Captured: {w}x{h} pixels.")

    # Calculate proportional mapping zones based on your standard baseline layout
    # (This tracks the stationary gray 'HP' and 'MP' letters on your UI bar)
    hp_y = int(h * 0.941)
    hp_x = int(w * 0.381)
    hp_h = int(h * 0.02)
    hp_w = int(w * 0.025)
    
    mp_y = int(h * 0.941)
    mp_x = int(w * 0.453)
    mp_h = int(h * 0.02)
    mp_w = int(w * 0.025)

    # 1. Slice out the permanent HP Label box frame
    hp_crop = img[hp_y:hp_y+hp_h, hp_x:hp_x+hp_w]
    if hp_crop.size > 0:
        cv2.imwrite("hp_template.png", hp_crop)
        print("[+] Generated 'hp_template.png' cleanly from stream.")
    else:
        print("[!] Slicing Error: HP boundaries fell out of range.")

    # 2. Slice out the permanent MP Label box frame
    mp_crop = img[mp_y:mp_y+mp_h, mp_x:mp_x+mp_w]
    if mp_crop.size > 0:
        cv2.imwrite("mp_template.png", mp_crop)
        print("[+] Generated 'mp_template.png' cleanly from stream.")
    else:
        print("[!] Slicing Error: MP boundaries fell out of range.")

print("\nTemplate processing complete! You can now launch vision_engine.py safely.")
