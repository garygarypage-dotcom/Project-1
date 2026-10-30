import os
import sys
import threading
import tkinter as tk
import pygetwindow as gw
import win32gui
import win32con

import combat_actions
import vision_engine

# =========================================================
#       PROPORTIONALLY SCALED WIDESCREEN PARAMETERS
# =========================================================
CLIENT_WIDTH = 1280
CLIENT_HEIGHT = 960
DASHBOARD_WIDTH = 1480  
DASHBOARD_HEIGHT = 1080 

# Locate Moonlight application window safely
all_windows = gw.getAllWindows()
moonlight_win = None
for win in all_windows:
    if "moonlight" in win.title.lower():
        moonlight_win = win
        vision_engine.target_hwnd = win._hWnd  # Share handle to background processing engine
        break

if not moonlight_win:
    print("[!] Error initializing: Moonlight frame stream target window unlinked.")
    sys.exit()

root = tk.Tk()
root.title("Autonomous 1440p Widescreen Visual Mapping Client Engine")
root.geometry(f"{DASHBOARD_WIDTH}x{DASHBOARD_HEIGHT}")
root.configure(bg="#2d2d2d")
root.resizable(False, False)

# UI Layout Element Configuration
console_panel = tk.Frame(root, width=DASHBOARD_WIDTH, height=120, bg="#191919")
console_panel.place(x=0, y=CLIENT_HEIGHT)

map_status_label = tk.Label(console_panel, text="Current Map Identified: Analyzing Widescreen Layer...", font=("Arial", 11, "bold"), bg="#191919", fg="#ffff00")
map_status_label.pack(anchor="w", padx=15, pady=5)
vision_engine.map_label_ref = map_status_label  # Share UI reference with processing threads

log_box = tk.Text(console_panel, font=("Consolas", 9), bg="#191919", fg="#cccccc", bd=0, state=tk.DISABLED)
log_box.pack(fill=tk.BOTH, padx=15, pady=(0, 5))

def add_log(msg):
    log_box.config(state=tk.NORMAL)
    log_box.insert(tk.END, f"> {msg}\n")
    log_box.see(tk.END)
    log_box.config(state=tk.DISABLED)

vision_engine.logger_callback = add_log  # Route background tracking status logs to UI box
vision_engine.listbox_clear_callback = lambda: active_mobs_listbox.delete(0, tk.END)
vision_engine.listbox_insert_callback = lambda item: active_mobs_listbox.insert(tk.END, item)

stream_container = tk.Frame(root, width=CLIENT_WIDTH, height=CLIENT_HEIGHT, bg="#141414")
stream_container.place(x=200, y=0)

stream_canvas = tk.Label(stream_container, bg="#141414")
stream_canvas.pack(fill=tk.BOTH, expand=True)

sidebar = tk.Frame(root, width=200, height=CLIENT_HEIGHT, bg="#2d2d2d")
sidebar.place(x=0, y=0)

active_mobs_listbox = tk.Listbox(sidebar, bg="#191919", fg="#00ff00", font=("Arial", 10), bd=0)
active_mobs_listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

def toggle_input_lock():
    if not moonlight_win: return
    hwnd_moonlight = moonlight_win._hWnd
    old_ex_style = win32gui.GetWindowLong(hwnd_moonlight, win32con.GWL_EXSTYLE)
    if not vision_engine.input_locked:
        new_ex_style = old_ex_style | win32con.WS_EX_TRANSPARENT | win32con.WS_EX_LAYERED
        win32gui.SetWindowLong(hwnd_moonlight, win32con.GWL_EXSTYLE, new_ex_style)
        lock_btn.config(text="Game Input: LOCKED", bg="#ff3333", fg="#ffffff")
        add_log("[INPUT] Game clicks locked. Inputs will now pass through to the dashboard.")
        vision_engine.input_locked = True
    else:
        new_ex_style = old_ex_style & ~win32con.WS_EX_TRANSPARENT & ~win32con.WS_EX_LAYERED
        win32gui.SetWindowLong(hwnd_moonlight, win32con.GWL_EXSTYLE, new_ex_style)
        lock_btn.config(text="Game Input: ACTIVE", bg="#33cc33", fg="#000000")
        add_log("[INPUT] Game clicks unlocked. Interactivity restored.")
        vision_engine.input_locked = False
    win32gui.SetWindowPos(hwnd_moonlight, 0, 0, 0, 0, 0, win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOZORDER | win32con.SWP_FRAMECHANGED)

lock_btn = tk.Button(sidebar, text="Game Input: ACTIVE", font=("Arial", 10, "bold"), bg="#33cc33", fg="#000000", command=toggle_input_lock, bd=0, height=2)
lock_btn.pack(fill=tk.X, padx=10, pady=(0, 10))

def toggle_bot():
    vision_engine.bot_active = not vision_engine.bot_active
    if vision_engine.bot_active:
        bot_btn.config(text="Bot Engine: RUNNING", bg="#2e8b57", fg="white")
        add_log("[SYSTEM] Background input threads engaged.")
    else:
        bot_btn.config(text="Bot Engine: PAUSED", bg="#4763ff", fg="white")
        add_log("[SYSTEM] Background input threads safely suspended.")
        combat_actions.release_all_keys(vision_engine.target_hwnd)

bot_btn = tk.Button(sidebar, text="Bot Engine: PAUSED", font=("Arial", 10, "bold"), bg="#4763ff", fg="white", command=toggle_bot, bd=0, height=2)
bot_btn.pack(fill=tk.X, padx=10, pady=(0, 10))

def refresh_interface_canvas():
    """Main rendering loop pulls array states from background process and paints onto UI frame."""
    from PIL import Image, ImageTk
    import cv2
    if vision_engine.display_frame is not None:
        try:
            with vision_engine.ocr_lock:
                rgb = cv2.cvtColor(vision_engine.display_frame, cv2.COLOR_BGR2RGB)
            tk_img = ImageTk.PhotoImage(image=Image.fromarray(rgb))
            stream_canvas.config(image=tk_img)
            stream_canvas.image = tk_img
        except: pass
    root.after(33, refresh_interface_canvas)

def initialize_embedded_parenting():
    root.update()
    hwnd_container = stream_container.winfo_id()
    hwnd_moonlight = moonlight_win._hWnd
    
    style = win32gui.GetWindowLong(hwnd_moonlight, win32con.GWL_STYLE)
    style &= ~win32con.WS_CAPTION
    style &= ~win32con.WS_THICKFRAME
    win32gui.SetWindowLong(hwnd_moonlight, win32con.GWL_STYLE, style)
    
    win32gui.SetParent(hwnd_moonlight, hwnd_container)
    win32gui.MoveWindow(hwnd_moonlight, 0, 0, CLIENT_WIDTH, CLIENT_HEIGHT, True)
    
    # Load settings and activate background loop engine thread
    vision_engine.moonlight_win_ref = moonlight_win
    vision_engine.load_registry_data()
    
    threading.Thread(target=vision_engine.background_vision_worker, daemon=True).start()
    refresh_interface_canvas()

root.after(200, initialize_embedded_parenting)
root.mainloop()
