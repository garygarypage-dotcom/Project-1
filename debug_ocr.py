import mss
import cv2
import numpy as np
import pygetwindow as gw
import pytesseract

pytesseract.pytesseract.tesseract_cmd = r'C:\Users\we21\AppData\Local\Programs\Tesseract-OCR\tesseract.exe'

all_windows = gw.getAllWindows()
moonlight_win = None
for win in all_windows:
    if "moonlight" in win.title.lower():
        moonlight_win = win
        break

if not moonlight_win:
    print("[!] Error: Moonlight streaming window must be open!")
    exit()

print("[*] Target window linked. Capturing coordinates...")
with mss.MSS() as sct:
    monitor = {"top": moonlight_win.top, "left": moonlight_win.left, "width": moonlight_win.width, "height": moonlight_win.height}
    screen = np.array(sct.grab(monitor))
    raw_frame = cv2.cvtColor(screen, cv2.COLOR_BGRA2BGR)
    current_frame = cv2.resize(raw_frame, (800, 600))
    
    # RE-ALIGNED MINI-MAP REGION INDEX HOOKS
    minimap_crop = current_frame[104:122, 45:225]
    minimap_crop = cv2.resize(minimap_crop, (0, 0), fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    
    # NEW RAW CONTRAST FILTER PROCESSING FOR PREVENTING SOLID WHITE RENDERS
    thresh_map = cv2.cvtColor(minimap_crop, cv2.COLOR_BGR2GRAY)
    thresh_map = cv2.GaussianBlur(thresh_map, (3, 3), 0)
    
    cv2.imwrite("ocr_test_crop.png", thresh_map)
    print("[+] Saved 'ocr_test_crop.png' to your folder.")
    
    raw_text = pytesseract.image_to_string(thresh_map, config='--psm 6').strip()
    print(f"\n[OCR RESULT] Text read from screen: '{raw_text}'")
