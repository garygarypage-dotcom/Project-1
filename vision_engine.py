import os
import time
import json
import threading
import requests
import cv2
import numpy as np
import win32gui
import win32con
import win32ui
import pytesseract
import traceback
import sys

import combat_actions
from mob_detector import MobDetector  

# Initialize modular detection wrapper instance
detector_instance = MobDetector(confidence_threshold=0.52)

# =========================================================
#   FORCE PROCESS DPI AWARENESS (CRITICAL FOR 0PX FIX)
# =========================================================
try:
    import ctypes
    ctypes.windll.shcore.SetProcessDpiAwareness(2) # PROCESS_PER_MONITOR_DPI_AWARE
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

pytesseract.pytesseract.tesseract_cmd = r'C:\Users\we21\AppData\Local\Programs\Tesseract-OCR\tesseract.exe'

ACTIVE_SCREEN_MARKERS = {}
MAP_SPAWN_REGISTRY = {}
CURRENT_MAP_PLATFORMS = []   
PLAYER_MAP_COORD = (0, 0)    
ON_PLATFORM_STRING = "Ground Floor"
CURRENT_HP_PIXELS = 0
CURRENT_MP_PIXELS = 0
TOTAL_MONSTERS_FOUND = 0

MASTER_UI_ROOT = None
radar_canvas_ref = None

bot_active = False
running = True
input_locked = False  
active_trackers = []  
display_frame = None
target_hwnd = None  
ocr_in_progress = False

Y_HUD_AUTO = 844
X_HP_AUTO = 460
X_MP_AUTO = 552

logger_callback = None
listbox_clear_callback = None
listbox_insert_callback = None
map_label_ref = None

ocr_lock = threading.Lock()
frame_lock = threading.Lock() 
last_map_name = ""

CLIENT_WIDTH = 1280
CLIENT_HEIGHT = 960

def load_registry_data():
    """Reads the new master centralized database compiled directly from local game files."""
    global MAP_SPAWN_REGISTRY
    file_name = "master_navigation_db.json"
    try:
        if os.path.exists(file_name) and os.path.getsize(file_name) > 10:
            with open(file_name, "r", encoding="utf-8") as f:
                MAP_SPAWN_REGISTRY = json.load(f)
            print(f"[REGISTRY] Loaded unified master database file. Registered {len(MAP_SPAWN_REGISTRY)} maps.")
        else:
            MAP_SPAWN_REGISTRY = {}
    except Exception as e:
        print(f"[REGISTRY ERROR] Failed to parse master database: {e}")
        MAP_SPAWN_REGISTRY = {}

def dynamic_fetch_and_center_asset(mob_id):
    local_path = f"cache_{mob_id}.png"
    if os.path.exists(local_path):
        return cv2.imread(local_path, cv2.IMREAD_GRAYSCALE)
    
    fallback = np.zeros((32, 32), dtype=np.uint8)
    cv2.drawMarker(fallback, (16, 16), 255, cv2.MARKER_CROSS, 6, 1)
    return fallback

def auto_calibrate_hud_offsets(current_frame):
    global Y_HUD_AUTO, X_HP_AUTO, X_MP_AUTO
    try:
        h, w = current_frame.shape[:2]
        scan_y_start = max(0, int(h * 0.85))
        scan_y_end = min(h, int(h * 0.91))
        sample_x = 470 
        
        for y_pos in range(scan_y_start, scan_y_end):
            b, g, r = current_frame[y_pos, sample_x]
            if r > 160 and g < 50 and b < 50:
                Y_HUD_AUTO = y_pos
                X_HP_AUTO = 460   
                X_MP_AUTO = 552   
                return True
                
        backup_x = 500
        for y_pos in range(scan_y_start, scan_y_end):
            b, g, r = current_frame[y_pos, backup_x]
            if r > 160 and g < 50 and b < 50:
                Y_HUD_AUTO = y_pos
                X_HP_AUTO = 460   
                X_MP_AUTO = 552   
                return True
    except Exception:
        pass
    return True

def async_ocr_worker(crop_img):
    global last_map_name, active_trackers, CURRENT_MAP_PLATFORMS, ACTIVE_SCREEN_MARKERS, ocr_in_progress
    try:
        gray_map = cv2.cvtColor(crop_img, cv2.COLOR_BGR2GRAY)
        _, thresh_map = cv2.threshold(gray_map, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        
        with ocr_lock:
            raw_text = pytesseract.image_to_string(thresh_map, config='--psm 7').strip().lower()
            clean_text = "".join([c for c in raw_text if c.isalnum() or c.isspace() or c == ':']).strip()
        
        if len(clean_text) > 3 and clean_text != last_map_name:
            last_map_name = clean_text
            matched_key = None
            for registry_key in MAP_SPAWN_REGISTRY.keys():
                if registry_key in clean_text or clean_text in registry_key:
                    matched_key = registry_key
                    break
                    
            if matched_key:
                if listbox_clear_callback: listbox_clear_callback()
                new_trackers = []
                map_node_data = MAP_SPAWN_REGISTRY[matched_key]
                
                if map_label_ref:
                    map_label_ref.config(text=f"Current Map Identified: {matched_key.upper()}")
                
                mobs_dict = map_node_data.get("mobs", {})
                for mob_id in mobs_dict.keys():
                    if mob_id == "None": continue
                    if listbox_insert_callback: 
                        mob_info = mobs_dict[mob_id]
                        listbox_insert_callback(f"Mob ID: {mob_id} (Lv.{mob_info.get('level')}) HP:{mob_info.get('max_hp')}")
                        
                    local_path = f"cache_{mob_id}.png"
                    if os.path.exists(local_path):
                        template_matrix = cv2.imread(local_path, cv2.IMREAD_GRAYSCALE)
                        if template_matrix is not None: 
                            scaled_template = cv2.resize(template_matrix, (0, 0), fx=1.8, fy=1.8, interpolation=cv2.INTER_LINEAR)
                            new_trackers.append(cv2.Canny(scaled_template, 50, 150))
                        
                active_trackers = new_trackers
                CURRENT_MAP_PLATFORMS = map_node_data.get("platforms", [])
                ACTIVE_SCREEN_MARKERS = map_node_data.get("markers", {})
    except Exception as e:
        print(f"[OCR ERR] Failed execution block update: {e}")
    finally: 
        ocr_in_progress = False

def background_vision_worker():
    global active_trackers, bot_active, running, display_frame, CURRENT_MAP_PLATFORMS, PLAYER_MAP_COORD, ON_PLATFORM_STRING
    global CURRENT_HP_PIXELS, CURRENT_MP_PIXELS, TOTAL_MONSTERS_FOUND, ocr_in_progress, ACTIVE_SCREEN_MARKERS
    
    last_ocr_time = 0.0
    last_combat_cycle = 0.0
    print("[ENGINE] Desktop coordinate capture pipeline worker successfully engaged.")
    
    try:
        while running:
            if not target_hwnd or not win32gui.IsWindow(target_hwnd) or win32gui.IsIconic(target_hwnd):
                time.sleep(0.1)
                continue
                
            try:
                rect = win32gui.GetWindowRect(target_hwnd)
                x_win, y_win, r_win, b_win = rect
                w_win, h_win = r_win - x_win, b_win - y_win
            except:
                w_win, h_win = CLIENT_WIDTH, CLIENT_HEIGHT
                x_win, y_win = 0, 0
            
            if w_win <= 10 or h_win <= 10:
                w_win, h_win = CLIENT_WIDTH, CLIENT_HEIGHT
            
            try:
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
                
                win32gui.DeleteObject(saveBitMap.GetHandle())
                saveDC.DeleteDC()
                mfcDC.DeleteDC()
                win32gui.ReleaseDC(hdesktop, hwndDC)
            except Exception:
                time.sleep(0.015)
                continue
            
            current_frame = cv2.resize(raw_frame, (CLIENT_WIDTH, CLIENT_HEIGHT))
            annotated_frame = current_frame.copy()
            current_time = time.time()
            
            auto_calibrate_hud_offsets(current_frame)
            
            hp_segment = current_frame[Y_HUD_AUTO:Y_HUD_AUTO+5, X_HP_AUTO:X_HP_AUTO+48]
            mp_segment = current_frame[Y_HUD_AUTO:Y_HUD_AUTO+5, X_MP_AUTO:X_MP_AUTO+48]
            
            hp_b, hp_g, hp_r = cv2.split(hp_segment)
            mp_b, mp_g, mp_r = cv2.split(mp_segment)
            
            hp_mask = (hp_r > 130) & (hp_b < 100)
            CURRENT_HP_PIXELS = int(np.sum(hp_mask))
            
            mp_mask = (mp_b > 100) & (mp_r < 140)
            CURRENT_MP_PIXELS = int(np.sum(mp_mask))
            
            if current_time - last_ocr_time > 5.0 and not ocr_in_progress:
                last_ocr_time = current_time
                ocr_in_progress = True
                map_header_crop = current_frame[5:60, 5:220].copy()
                threading.Thread(target=async_ocr_worker, args=(map_header_crop,), daemon=True).start()

            minimap_zone = current_frame[80:350, 240:370]
            mini_h, mini_w = minimap_zone.shape[:2]
            gray_mini = cv2.cvtColor(minimap_zone, cv2.COLOR_BGR2GRAY)
            _, mini_thresh = cv2.threshold(gray_mini, 220, 255, cv2.THRESH_BINARY)
            M = cv2.moments(mini_thresh)
            ON_PLATFORM_STRING = "Ground Floor"
            
            if M["m00"] != 0:
                cX = int(M["m10"] / M["m00"])
                cY = int(M["m01"] / M["m00"])
                rel_x = int((cX / mini_w) * 100)
                rel_y = int((cY / mini_h) * 100)
                PLAYER_MAP_COORD = (rel_x, rel_y)
                
                for plat in CURRENT_MAP_PLATFORMS:
                    if plat["x_min"] <= rel_x <= plat["x_max"]:
                        if abs(rel_y - plat["y_level"]) < 6:
                            ON_PLATFORM_STRING = plat["name"]
                            break

            # 1. PROCESS FRAME VIA COLOR ENGINE (POPULATES detector_instance.tracked_mobs)
            TOTAL_MONSTERS_FOUND = detector_instance.process_frame(current_frame, annotated_frame, active_trackers)
            
            with frame_lock:
                display_frame = annotated_frame

            # 2. BUNDLE BOTH STATIC METADATA AND LIVE TARGETS INTO ONE PACKET
            live_dispatch_packet = {}
            
            if ACTIVE_SCREEN_MARKERS:
                for k, v in ACTIVE_SCREEN_MARKERS.items():
                    live_dispatch_packet[f"static_{k}"] = v
            
            if hasattr(detector_instance, 'tracked_mobs') and detector_instance.tracked_mobs:
                for idx, mob in enumerate(detector_instance.tracked_mobs):
                    # Explicit hardcoded literal integer array to ensure clean serialization
                    target_color = [255, 255, 0]  # Neon Cyan in BGR [Blue, Green, Red]
                    
                    live_dispatch_packet[f"mob_{idx}"] = {
                        "rect": mob.get("rect"),
                        "color": target_color,
                        "label": str(mob.get("name", "TARGET"))
                    }

            # 3. ROUTE THE LIVE PACKET DIRECTLY TO TRANS OVERLAY
            current_module = sys.modules[__name__]
            overlay_obj = getattr(current_module, 'overlay_ref', None)
            if overlay_obj is not None:
                overlay_obj.update_markers(live_dispatch_packet)
            else:
                master_ui = getattr(current_module, 'MASTER_UI_ROOT', None)
                if master_ui and hasattr(master_ui, 'overlay_instance'):
                    current_module.overlay_ref = master_ui.overlay_instance
                    master_ui.overlay_instance.update_markers(live_dispatch_packet)
            
            if bot_active:
                override_active = combat_actions.handle_platform_pathing(
                    target_hwnd, PLAYER_MAP_COORD, ON_PLATFORM_STRING, CURRENT_MAP_PLATFORMS, current_time,
                    'alt', 'space', logger_callback if logger_callback else print
                )
                if not override_active:
                    last_combat_cycle = combat_actions.handle_offense(
                        target_hwnd, TOTAL_MONSTERS_FOUND, current_time, last_combat_cycle,
                        'space', 'alt', logger_callback if logger_callback else print
                    )
            time.sleep(0.015)
    except Exception as crash_error:
        print(f"\n[CRITICAL ERROR] vision_engine.py loop crash:", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
