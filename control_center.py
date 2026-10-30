import os
import sys
import threading
import tkinter as tk
from tkinter import ttk
import pygetwindow as gw
import win32gui
import win32con

import combat_actions
import vision_engine
from health_monitor import HealthMonitor

DASHBOARD_WIDTH = 420  
DASHBOARD_HEIGHT = 780  

# Hook onto the active Moonlight capture instance stream layout context
all_windows = gw.getAllWindows()
moonlight_win = None
for win in all_windows:
    if "moonlight" in win.title.lower():
        moonlight_win = win
        vision_engine.target_hwnd = win._hWnd
        break

if not moonlight_win:
    print("[!] Moonlight instance not detected. Launch stream application first.")
    sys.exit()

root = tk.Tk()
root.title("Vision Control Center")
root.geometry(f"{DASHBOARD_WIDTH}x{DASHBOARD_HEIGHT}")
root.configure(bg="#1e1e1e")
root.resizable(False, False)
root.attributes("-topmost", True)

# System input isolation block flag (Starts locked out securely on application load)
user_input_disabled = True

# --- Unified Navigation Radar Canvas Panel (LOCKED HIGH-CONTRAST RENDERER) ---
radar_panel = tk.LabelFrame(root, text=" LIVE WORLD NAVIGATION RADAR ", font=("Arial", 9, "bold"), bg="#1e1e1e", fg="#ffff00")
radar_panel.pack(fill=tk.X, padx=10, pady=(10, 5))

# Lock down geometry frame sizes right here so Tkinter can't crush them to 0x0
radar_canvas = tk.Canvas(radar_panel, width=400, height=300, bg="#111111", highlightthickness=1, highlightbackground="#333333")
radar_canvas.pack(padx=5, pady=5, expand=False)

# --- Extended System Information Logger Panel (REPOSITIONED TO BOTTOM CONTAINER) ---
log_panel = tk.LabelFrame(root, text=" PIPELINE DEBUG ENGINE MONITOR ", font=("Arial", 9, "bold"), bg="#1e1e1e", fg="#00ff00")
log_panel.pack(fill=tk.X, padx=10, pady=5)

# Lock down the text box height to 8 text lines so it sits cleanly under the radar box
log_box = tk.Text(log_panel, font=("Consolas", 8), height=8, bg="#111111", fg="#cccccc", bd=0, wrap=tk.WORD, state=tk.DISABLED)
log_box.pack(fill=tk.X, padx=5, pady=5)

# --- Telemetry Frame with Space-Saving Layout ---
telemetry_frame = tk.Frame(root, bg="#2d2d2d", height=105)
telemetry_frame.pack(fill=tk.X, padx=10, pady=5)

# Left Column: Text Data Metrics
text_col = tk.Frame(telemetry_frame, bg="#2d2d2d")
text_col.pack(side=tk.LEFT, fill=tk.Y, padx=(10, 5), pady=5)

telemetry_label = tk.Label(text_col, text="👾 Active Targets  : 0 units\n📍 Map Node Target: Ground Floor", 
                           font=("Consolas", 9, "bold"), bg="#2d2d2d", fg="#ffff00", justify=tk.LEFT)
telemetry_label.pack(anchor=tk.W, pady=2)

# Right Column: Visual Fluid Bars
bars_col = tk.Frame(telemetry_frame, bg="#2d2d2d")
bars_col.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 10), pady=5)

# Custom Styling Configurations for TTK Progressbars (SAFE THEME BACKUPS)
style_engine = ttk.Style()
try:
    style_engine.theme_use('clam') # Clam is standard and bulletproof across all environments
except:
    pass
style_engine.configure("HP.Horizontal.TProgressbar", foreground='#ff3333', background='#ff3333', troughcolor='#331111', thickness=10)
style_engine.configure("MP.Horizontal.TProgressbar", foreground='#3366ff', background='#3366ff', troughcolor='#111133', thickness=10)

# HP Visual Gauge Row
hp_row = tk.Frame(bars_col, bg="#2d2d2d")
hp_row.pack(fill=tk.X, pady=1)
tk.Label(hp_row, text="HP:", font=("Consolas", 8, "bold"), bg="#2d2d2d", fg="#ff3333", width=3, anchor=tk.W).pack(side=tk.LEFT)
hp_progress = ttk.Progressbar(hp_row, style="HP.Horizontal.TProgressbar", orient="horizontal", length=110, mode="determinate", max=230)
hp_progress.pack(side=tk.LEFT, padx=2)
hp_val_lbl = tk.Label(hp_row, text="0/230px", font=("Consolas", 8, "bold"), bg="#2d2d2d", fg="#ffffff", width=8, anchor=tk.E)
hp_val_lbl.pack(side=tk.RIGHT)

# MP Visual Gauge Row
mp_row = tk.Frame(bars_col, bg="#2d2d2d")
mp_row.pack(fill=tk.X, pady=1)
tk.Label(mp_row, text="MP:", font=("Consolas", 8, "bold"), bg="#2d2d2d", fg="#3366ff", width=3, anchor=tk.W).pack(side=tk.LEFT)
mp_progress = ttk.Progressbar(mp_row, style="MP.Horizontal.TProgressbar", orient="horizontal", length=110, mode="determinate", max=200)
mp_progress.pack(side=tk.LEFT, padx=2)
mp_val_lbl = tk.Label(mp_row, text="0/200px", font=("Consolas", 8, "bold"), bg="#2d2d2d", fg="#ffffff", width=8, anchor=tk.E)
mp_val_lbl.pack(side=tk.RIGHT)

# --- Interactive Potion Threshold Sliders ---
slider_container = tk.LabelFrame(root, text=" DEFENSIVE THRESHOLD TUNING ", font=("Arial", 9, "bold"), bg="#1e1e1e", fg="#ffff00", padx=10, pady=5)
slider_container.pack(fill=tk.X, padx=10, pady=5)

hp_slider_lbl = tk.Label(slider_container, text="HP Potion Trigger Point: Below 150px", font=("Arial", 9), bg="#1e1e1e", fg="#cccccc")
hp_slider_lbl.pack(anchor=tk.W)
hp_slider = tk.Scale(slider_container, from_=10, to=225, orient=tk.HORIZONTAL, bg="#1e1e1e", fg="#ffffff", highlightthickness=0, bd=1)
hp_slider.set(150)
hp_slider.pack(fill=tk.X, pady=(0, 5))

mp_slider_lbl = tk.Label(slider_container, text="MP Potion Trigger Point: Below 100px", font=("Arial", 9), bg="#1e1e1e", fg="#cccccc")
mp_slider_lbl.pack(anchor=tk.W)
mp_slider = tk.Scale(slider_container, from_=10, to=200, orient=tk.HORIZONTAL, bg="#1e1e1e", fg="#ffffff", highlightthickness=0, bd=1)
mp_slider.set(100)
mp_slider.pack(fill=tk.X, pady=(0, 2))

def add_log(msg):
    log_box.config(state=tk.NORMAL)
    log_box.insert(tk.END, f"[{threading.current_thread().name[:4]}] {msg}\n")
    log_box.see(tk.END)
    log_box.config(state=tk.DISABLED)

vision_engine.logger_callback = add_log

# Setup registry pipeline link mock callbacks
sidebar_dummy = tk.Listbox(root)
vision_engine.listbox_clear_callback = lambda: sidebar_dummy.delete(0, tk.END)
vision_engine.listbox_insert_callback = lambda item: add_log(f"[REGISTRY] {item}")

# Connect structural window variables cleanly over to background engine components
vision_engine.map_label_ref = telemetry_label
vision_engine.radar_canvas_ref = radar_canvas

# Instantiate the independent background medical thread
health_manager = HealthMonitor(hp_key='x', mp_key='c')

# =========================================================
#      FORCE EXACT 1280x960 CLIENT SURFACE ALIGNMENT
# =========================================================
def force_standard_client_bounds(hwnd):
    if not hwnd:
        return
    try:
        style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
        style |= win32con.WS_CAPTION        
        style |= win32con.WS_THICKFRAME     
        style |= win32con.WS_MINIMIZEBOX    
        style |= win32con.WS_MAXIMIZEBOX    
        style |= win32con.WS_SYSMENU        
        win32gui.SetWindowLong(hwnd, win32con.GWL_STYLE, style)
        
        ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
        ex_style |= win32con.WS_EX_CLIENTEDGE
        win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, ex_style)
        
        x_win, y_win, r_win, b_win = win32gui.GetWindowRect(hwnd)
        left, top, right, bottom = win32gui.GetClientRect(hwnd)
        
        w_win, h_win = r_win - x_win, b_win - y_win
        w_client, h_client = right - left, bottom - top
        
        border_width_padding = w_win - w_client if w_client > 0 else 16
        title_bar_height_padding = h_win - h_client if h_client > 0 else 39
        
        target_width = 1280 + border_width_padding
        target_height = 960 + title_bar_height_padding
        
        win32gui.SetWindowPos(hwnd, 0, x_win, y_win, target_width, target_height, 
                              win32con.SWP_NOZORDER | win32con.SWP_FRAMECHANGED | win32con.SWP_SHOWWINDOW)
        add_log(f"[CALIBRATION] Restored standard window layout frame at 4:3 aspect ratio.")
    except Exception as e:
        add_log(f"[RESIZE ERROR] Failed to restore standard client bounds: {e}")

# =========================================================
#             INPUT ISOLATION CONTROL ENGINE
# =========================================================
def apply_window_lock_state():
    hwnd = vision_engine.target_hwnd
    if not hwnd:
        return
    current_ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
    
    if user_input_disabled:
        new_style = current_ex_style & ~win32con.WS_EX_TRANSPARENT & ~win32con.WS_EX_LAYERED
        win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, new_style)
        root.attributes("-topmost", True)
        input_lock_btn.config(text="GAME CLICK LOCK: LOCKED", bg="#ff3333", fg="white")
        add_log("[ISOLATION] Input Block Active: Window clicks are intercepted.")
    else:
        new_style = current_ex_style & ~win32con.WS_EX_TRANSPARENT & ~win32con.WS_EX_LAYERED
        win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, new_style)
        input_lock_btn.config(text="GAME CLICK LOCK: INTERACTIVE", bg="#33cc33", fg="black")
        add_log("[ISOLATION] Input Block Inactive: Manual interaction restored.")
        
    win32gui.SetWindowPos(hwnd, 0, 0, 0, 0, 0, 
                          win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOZORDER | win32con.SWP_FRAMECHANGED)

def toggle_input_lock():
    global user_input_disabled
    user_input_disabled = not user_input_disabled
    apply_window_lock_state()

def toggle_bot():
    vision_engine.bot_active = not vision_engine.bot_active
    if vision_engine.bot_active:
        bot_btn.config(text="SYSTEM BOT: ACTIVE", bg="#2e8b57", fg="white")
        add_log("[BOT ENGAGED] Logic processing threads active.")
    else:
        bot_btn.config(text="SYSTEM BOT: PAUSED", bg="#4763ff", fg="white")
        add_log("[BOT SUSPENDED] Halting virtual machine outputs.")
        combat_actions.release_all_keys(vision_engine.target_hwnd)

# Graphical Component Control Buttons (CONVERTED TO HORIZONTAL SPLIT TO SAVE VERTICAL SPACE)
button_row_frame = tk.Frame(root, bg="#1e1e1e")
button_row_frame.pack(fill=tk.X, padx=10, pady=(5, 10))

input_lock_btn = tk.Button(button_row_frame, text="LOCK: LOCKED", font=("Arial", 9, "bold"), 
                           bg="#ff3333", fg="white", command=toggle_input_lock, bd=0, height=2, width=20)
input_lock_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 2))

bot_btn = tk.Button(button_row_frame, text="BOT: PAUSED", font=("Arial", 9, "bold"), 
                    bg="#4763ff", fg="white", command=toggle_bot, bd=0, height=2, width=20)
bot_btn.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(2, 0))

def refresh_telemetry_hud():
    """Independent UI loop to paint progress bars and safely render the radar window."""
    current_hp = vision_engine.CURRENT_HP_PIXELS
    current_mp = vision_engine.CURRENT_MP_PIXELS
    
    # Update progress bar positions
    hp_progress['value'] = min(current_hp, 230)
    mp_progress['value'] = min(current_mp, 200)
    
    hp_val_lbl.config(text=f"{current_hp}/230px")
    mp_val_lbl.config(text=f"{current_mp}/200px")
    
    telemetry_string = (
        f"👾 Active Targets  : {vision_engine.TOTAL_MONSTERS_FOUND} units\n"
        f"📍 Map Node Target: {vision_engine.ON_PLATFORM_STRING}"
    )
    telemetry_label.config(text=telemetry_string)

    # =========================================================
    #   NATIVE MAIN-THREAD CANVAS REDRAW ENGINE
    # =========================================================
    if radar_canvas is not None:
        try:
            radar_canvas.delete("all")
            
            # 1. Paint boundary limits
            radar_canvas.create_rectangle(5, 5, 395, 295, outline="#333333", width=1)
            
            # 2. Force test indications onto screen layout context
            radar_canvas.create_oval(190, 140, 210, 160, fill="#ffff00", outline="#ffffff", width=1)
            radar_canvas.create_text(200, 125, text="RADAR GRAPHICS ENGINE: ACTIVE", fill="#ffff00", font=("Arial", 8, "bold"))
            
            # Paint a static blueprint baseline floor panel
            radar_canvas.create_rectangle(30, 220, 370, 235, outline="#3366ff", width=2)
            radar_canvas.create_text(40, 210, text="Diagnostic Platform Blueprint Layer", fill="#3366ff", font=("Arial", 7))

            # 3. Handle live tracking updates from memory space
            px, py = vision_engine.PLAYER_MAP_COORD
            draw_x = px if px > 0 else 50
            draw_y = py if py > 0 else 50
            
            radar_canvas.create_oval(draw_x*4-4, draw_y*3-4, draw_x*4+4, draw_y*3+4, fill="#ff3333", outline="#ffffff", width=1)
            radar_canvas.create_text(draw_x*4+8, draw_y*3, text="YOU (LIVE)", fill="#ff3333", font=("Arial", 8, "bold"), anchor="w")
            
            markers = getattr(vision_engine, 'ACTIVE_SCREEN_MARKERS', {})
            if not markers and hasattr(vision_engine, 'MAP_SPAWN_REGISTRY'):
                target_fallback = "victoria road: rocky road iii"
                for registry_key, registry_data in vision_engine.MAP_SPAWN_REGISTRY.items():
                    if target_fallback in registry_key.lower():
                        markers = registry_data.get("markers", {})
                        break
            
            if markers:
                for key, data in markers.items():
                    rect = data.get("rect",)
                    color_bgr = data.get("color",)
                    label = data.get("label", "")
                    
                    hex_color = f"#{color_bgr:02x}{color_bgr:02x}{color_bgr:02x}"
                    rx, ry, rw, rh = rect
                    
                    radar_x = int((rx / 1280.0) * 400)
                    radar_y = int((ry / 960.0) * 300)
                    radar_w = max(4, int((rw / 1280.0) * 400))
                    radar_h = max(10, int((rh / 960.0) * 300))
                    
                    radar_canvas.create_rectangle(
                        radar_x, radar_y, 
                        radar_x + radar_w, radar_y + radar_h, 
                        outline=hex_color, width=2
                    )
        except Exception as e:
            print(f"[RADAR FAIL] {e}")
            
    try:
        val_hp_trigger = int(hp_slider.get())
        val_mp_trigger = int(mp_slider.get())
        hp_slider_lbl.config(text=f"HP Potion Trigger Point: Below {val_hp_trigger}px")
        mp_slider_lbl.config(text=f"MP Potion Trigger Point: Below {val_mp_trigger}px")
        
        if hasattr(health_manager, 'hp_threshold'):
            health_manager.hp_threshold = val_hp_trigger
        if hasattr(health_manager, 'mp_threshold'):
            health_manager.mp_threshold = val_mp_trigger
    except:
        pass
        
    root.after(40, refresh_telemetry_hud)

def trace_execution_lines(frame, event, arg):
    """Intercepts and prints every single line of code executed in real-time."""
    if event == 'line':
        code = frame.f_code
        filename = code.co_filename
        # Filter layout context to only show your project script files
        if any(f in filename.lower() for f in ["control", "health", "vision", "combat"]):
            short_file = filename.replace("\\", "/").split("/")[-1]
            print(f"[TRACE] File: {short_file} | Line {frame.f_lineno} -> {code.co_name}")
    return trace_execution_lines

# Turn on the line tracing engine right here
print("\n=== SYSTEM ENGAGING REAL-TIME LINE TRACING ===")
sys.settrace(trace_execution_lines)

try:
    # Run size calibration steps prior to engine instantiation
    force_standard_client_bounds(vision_engine.target_hwnd)

    # Boot up operations
    vision_engine.load_registry_data()
    threading.Thread(target=vision_engine.background_vision_worker, name="VisionWorker", daemon=True).start()
    
    print("[DIAGNOSTIC] Calling health_manager.start now...")
    health_manager.start(add_log)
    print("[DIAGNOSTIC] Passed health_manager.start successfully.")

    root.after(200, apply_window_lock_state)
    root.after(100, refresh_telemetry_hud)
    root.mainloop()

# Run size calibration steps prior to engine instantiation
force_standard_client_bounds(vision_engine.target_hwnd)

# BIND MASTER WINDOW STRUCTURAL REFERENCING AXIS FOR OVERLAY HANDLES
vision_engine.MASTER_UI_ROOT = root

# Boot up operations
vision_engine.load_registry_data()
threading.Thread(target=vision_engine.background_vision_worker, name="VisionWorker", daemon=True).start()
health_manager.start(add_log)

root.after(200, apply_window_lock_state)
root.after(100, refresh_telemetry_hud)
root.mainloop()

except Exception as global_err:
    print(f"[CRITICAL FAILURE] Master runtime error: {global_err}")
    