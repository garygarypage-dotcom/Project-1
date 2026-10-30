import cv2
import numpy as np
import win32gui
import win32ui
import win32con
import pygetwindow as gw

# Find Moonlight application window safely
target_hwnd = None
for win in gw.getAllWindows():
    if "moonlight" in win.title.lower():
        target_hwnd = win._hWnd
        break

if not target_hwnd:
    print("[!] Moonlight instance not found. Make sure it's running on your screen!")
    exit()

# 1. Execute the absolute screen capture code currently running in your pipeline
rect = win32gui.GetWindowRect(target_hwnd)
x_win, y_win, r_win, b_win = rect
w_win, h_win = r_win - x_win, b_win - y_win

hdesktop = win32gui.GetDesktopWindow()
hwndDC = win32gui.GetWindowDC(hdesktop)
mfcDC  = win32ui.CreateDCFromHandle(hwndDC)
saveDC = mfcDC.CreateCompatibleDC()

saveBitMap = win32ui.CreateBitmap()
saveBitMap.CreateCompatibleBitmap(mfcDC, w_win, h_win)
saveDC.SelectObject(saveBitMap)
saveDC.BitBlt((0, 0), (w_win, h_win), mfcDC, (x_win, y_win), win32con.SRCCOPY)

bmpinfo = saveBitMap.GetInfo()
bmpstr = saveBitMap.GetBitmapBits(True)
raw_frame = np.frombuffer(bmpstr, dtype=np.uint8).reshape(bmpinfo['bmHeight'], bmpinfo['bmWidth'], 4)
raw_frame = cv2.cvtColor(raw_frame, cv2.COLOR_BGRA2BGR)

# Cleanup resources safely
win32gui.DeleteObject(saveBitMap.GetHandle())
saveDC.DeleteDC()
mfcDC.DeleteDC()
win32gui.ReleaseDC(hdesktop, hwndDC)

# Resize to standard workspace size exactly like the engine does
current_frame = cv2.resize(raw_frame, (1280, 960))

# 2. Draw direct coordinate guide lines onto the image
# This creates a grid every 100 pixels horizontally and vertically
for x in range(100, 1280, 100):
    cv2.line(current_frame, (x, 0), (x, 960), (255, 255, 0), 1)
    cv2.putText(current_frame, str(x), (x, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 0), 1)

for y in range(100, 960, 100):
    cv2.line(current_frame, (0, y), (1280, y), (255, 255, 0), 1)
    cv2.putText(current_frame, str(y), (10, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 0), 1)

# Save the raw image output straight to your project directory
output_filename = "debug_pipeline_view.png"
cv2.imwrite(output_filename, current_frame)
print(f"\n[SUCCESS] Saved visual capture template to: {output_filename}")
print("Open this image to see exactly what the engine sees, along with its coordinates!\n")
