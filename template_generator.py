import cv2
import mss
import numpy as np
import pygetwindow as gw
import sys

print("=========================================================")
print("     MAPLESTORY STATIC HUD LABEL TEMPLATE GENERATOR      ")
print("=========================================================")
print("CRITICAL TIP:")
print("-> DO NOT click inside the solid red or solid blue fluid bars!")
print("-> Click exactly on the gray 'HP' and 'MP' text labels or the")
print("   static background slot borders directly next to them.")
print("=========================================================")

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
    print("Make sure Moonlight is open and streaming the game before running this script!")
    sys.exit()

try:
    moonlight_win.activate()
except:
    pass

monitor = {
    "top": moonlight_win.top,
    "left": moonlight_win.left,
    "width": moonlight_win.width,
    "height": moonlight_win.height
}

click_count = 0
img_display = None

def manual_crop_event(event, x, y, flags, param):
    global click_count, img_display
    if event == cv2.EVENT_LBUTTONDBLCLK:
        click_count += 1
        
        # Crop a precise 24x14 pixel frame centered directly around your double-click
        w_box, h_box = 24, 14
        x_start = max(0, x - (w_box // 2))
        y_start = max(0, y - (h_box // 2))
        
        crop_matrix = img_display[y_start:y_start+h_box, x_start:x_start+w_box]
        
        if click_count == 1:
            cv2.imwrite("hp_template.png", crop_matrix)
            print(f"[SUCCESS] Recorded HP Anchor -> Saved 'hp_template.png' from position X:{x}, Y:{y}.")
            cv2.rectangle(img_display, (x_start, y_start), (x_start+w_box, y_start+h_box), (0, 0, 255), 2)
            cv2.putText(img_display, "HP HUD TEXT TARGET", (x_start, y_start - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)
            cv2.imshow("MANUAL STATIC HUD LABEL SELECTION", img_display)
            print("-> Now, double-click exactly on the gray 'MP' label text.")
            
        elif click_count == 2:
            cv2.imwrite("mp_template.png", crop_matrix)
            print(f"[SUCCESS] Recorded MP Anchor -> Saved 'mp_template.png' from position X:{x}, Y:{y}.")
            cv2.rectangle(img_display, (x_start, y_start), (x_start+w_box, y_start+h_box), (255, 0, 0), 2)
            cv2.putText(img_display, "MP HUD TEXT TARGET", (x_start, y_start - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 0, 0), 1)
            cv2.imshow("MANUAL STATIC HUD LABEL SELECTION", img_display)
            print("\n[COMPLETE] Both permanent anchors stored! Press 'q' to exit safely.")

with mss.MSS() as sct:
    screen = np.array(sct.grab(monitor))
    img_display = cv2.cvtColor(screen, cv2.COLOR_BGRA2BGR)
    
    WINDOW_NAME = "MANUAL STATIC HUD LABEL SELECTION"
    cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_AUTOSIZE)
    cv2.setMouseCallback(WINDOW_NAME, manual_crop_event)
    
    cv2.imshow(WINDOW_NAME, img_display)
    print("[*] Game snapshot frozen. Double-click the stationary gray text elements at the bottom.")
    
    while True:
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

cv2.destroyAllWindows()
print("\nTemplate mapping complete! Run vision_engine.py now.")
