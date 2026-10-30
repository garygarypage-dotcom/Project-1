import queue
import sys
import traceback
import tkinter as tk
import win32api
import win32con
import win32gui

class TransparentOverlay:
    def __init__(self):
        self.target_hwnd = None
        self.root = None
        self.canvas = None
        self.data_queue = queue.Queue(maxsize=5)
        self.loop_counter = 0

    def start(self, target_hwnd, master_root=None):
        """
        Initializes a hardware click-through frame clamped over the target game stream window bounds.
        """
        print(f"[DIAGNOSTIC] Initializing TransparentOverlay with target HWND: {target_hwnd}")
        self.target_hwnd = target_hwnd
        
        if master_root:
            self.root = tk.Toplevel(master_root)
            print("[DIAGNOSTIC] Layered overlay attached as Toplevel child node.")
        else:
            self.root = tk.Toplevel()
            print("[DIAGNOSTIC] Layered overlay running on separate structural Tk instance.")
            
        self.root.overrideredirect(True)
        
        # Color key mask definition configuration block
        self.root.config(bg="#000002")
        self.root.attributes("-transparentcolor", "#000002")
        self.root.attributes("-topmost", True)
        
        self.canvas = tk.Canvas(self.root, bg="#000002", highlightthickness=0, bd=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        self.root.update()
        hwnd_overlay = int(self.root.wm_frame(), 16)
        print(f"[DIAGNOSTIC] Created native overlay window surface frame context ID: {hwnd_overlay}")
        
        # Set click-through attributes explicitly using Win32 API calls
        try:
            extended_style = win32gui.GetWindowLong(hwnd_overlay, win32con.GWL_EXSTYLE)
            new_styles = extended_style | win32con.WS_EX_TRANSPARENT | win32con.WS_EX_LAYERED | win32con.WS_EX_TOOLWINDOW
            win32gui.SetWindowLong(hwnd_overlay, win32con.GWL_EXSTYLE, new_styles)
            print("[DIAGNOSTIC] Successfully injected click-through extended window flag configurations.")
        except Exception as style_err:
            print(f"[DIAGNOSTIC CRITICAL ERROR] Failed setting extended window attributes: {style_err}")

        self._default_sync_loop()
        self._queue_poll_loop()

    def update_markers(self, markers):
        """Thread-safe entry-point routing target marker dictionaries into the loop queues."""
        if self.data_queue.full():
            try:
                self.data_queue.get_nowait()
            except queue.Empty:
                pass
        try:
            self.data_queue.put_nowait(markers)
        except queue.Full:
            print("[DIAGNOSTIC ENGINE WARN] Marker pipeline input queue congested.")

    def _queue_poll_loop(self):
        """Asynchronous update loop parsing incoming tracking frames directly on canvas context."""
        self.loop_counter += 1
        
        # Print a heartbeat update trace log every 100 cycles to confirm thread survival
        if self.loop_counter % 100 == 0:
            print(f"[DIAGNOSTIC HEARTBEAT] Canvas paint loop is active. Current queue length size: {self.data_queue.qsize()}")

        if not self.canvas:
            print("[DIAGNOSTIC ERROR] Drawing cycle halted: Tkinter canvas references are null.")
            return
            
        try:
            v_eng = sys.modules.get('vision_engine')
            player_x, player_y = getattr(v_eng, 'PLAYER_MAP_COORD', (50, 50))
            
            scroll_offset_x = (player_x - 50) * 18
            scroll_offset_y = (player_y - 50) * 14
            
            while not self.data_queue.empty():
                markers = self.data_queue.get_nowait()
                self.canvas.delete("all")
                
                # --- NATIVE DIAGNOSTIC VISUAL BORDER LAYER ---
                # Paints an immediate alignment border box regardless of detection updates
                self.canvas.create_rectangle(5, 5, 1275, 955, outline="#ff0000", width=2)
                self.canvas.create_text(20, 25, text="[SYSTEM TARGETING HARDWARE OVERLAY ONLINE]", 
                                        fill="#ff0000", font=("Consolas", 10, "bold"), anchor=tk.W)
                
                if not markers:
                    if self.loop_counter % 100 == 0:
                        print("[DIAGNOSTIC HUD INFO] Render loop skipped drawing step: Incoming tracking data is empty.")
                    continue
                    
                for key, data in markers.items():
                    rect = data.get("rect")
                    if not rect or len(rect) < 4:
                        print(f"[DIAGNOSTIC ITEM WARN] Skipped marker {key}: Malformed coordinate matrix list format.")
                        continue
                        
                    color_bgr = data.get("color", [0, 255, 255])
                    label = data.get("label", "")
                    
                    # Unified parsing conversion layer standardizing BGR parameters into hexadecimal strings
                    if isinstance(color_bgr, int):
                        hex_color = f"#{color_bgr:06x}"
                    elif isinstance(color_bgr, (list, tuple)) and len(color_bgr) >= 3:
                        hex_color = f"#{color_bgr[2]:02x}{color_bgr[1]:02x}{color_bgr[0]:02x}"
                    else:
                        hex_color = "#ffff00"
                        
                    x1, y1, w, h = rect[0], rect[1], rect[2], rect[3]
                    search_str = f"{key} {label}".lower()
                    
                    if "ladder" in search_str or "rope" in search_str or "node" in search_str:
                        dynamic_x1 = x1 - scroll_offset_x
                        dynamic_y1 = y1 - scroll_offset_y
                    else:
                        dynamic_x1 = x1
                        dynamic_y1 = y1
                    
                    if hex_color == "#000002":
                        hex_color = "#ff00ff"
                        
                    self.canvas.create_rectangle(
                        dynamic_x1, dynamic_y1, 
                        dynamic_x1 + w, dynamic_y1 + h, 
                        outline=hex_color, width=3
                    )
                    
                    if label:
                        self.canvas.create_text(
                            dynamic_x1, dynamic_y1 - 10, 
                            text=str(label).upper(), fill=hex_color, 
                            font=("Consolas", 9, "bold"), anchor=tk.W
                        )
        except Exception as e:
            print(f"\n[DIAGNOSTIC PIPELINE CRASH] Exception inside canvas execution loop: {e}")
            traceback.print_exc(file=sys.stdout)
        finally:
            if self.root:
                self.root.after(20, self._queue_poll_loop)

    def _default_sync_loop(self):
        """Keeps window boundaries snapped precisely over the underlying game context process instance window coordinates."""
        if self.target_hwnd and win32gui.IsWindow(self.target_hwnd):
            if not win32gui.IsIconic(self.target_hwnd):
                try:
                    rect = win32gui.GetWindowRect(self.target_hwnd)
                    x, y, r, b = rect
                    w, h = r - x, b - y
                    
                    target_geometry = f"{w}x{h}+{x}+{y}"
                    if self.loop_counter % 200 == 0:
                        print(f"[DIAGNOSTIC POSITION SYNC] Overlay position synchronized to target: {target_geometry}")
                    
                    self.root.geometry(target_geometry)
                    self.root.deiconify()
                    self.root.lift()
                except Exception as pos_err:
                    print(f"[DIAGNOSTIC WARN] Boundary tracking sync failed temporarily: {pos_err}")
            else:
                self.root.withdraw()
        else:
            if self.loop_counter % 100 == 0:
                print("[DIAGNOSTIC ERROR] Target game application instance window reference handle is disconnected or dead.")
                
        self.root.after(40, self._default_sync_loop)

    def _default_sync_loop(self):
        """Forces window tracking updates to clamp perfectly onto the game window position coordinates."""
        if self.target_hwnd and win32gui.IsWindow(self.target_hwnd):
            if not win32gui.IsIconic(self.target_hwnd):
                try:
                    rect = win32gui.GetWindowRect(self.target_hwnd)
                    x, y, r, b = rect
                    w, h = r - x, b - y
                    
                    # FIXED BOUNDARY PROTECTION:
                    # If window metrics collapse or clip, ignore the update cycle
                    if w <= 10 or h <= 10 or (x == 0 and y == 0 and w == 0):
                        self.root.after(40, self._default_sync_loop)
                        return

                    target_geometry = f"{w}x{h}+{x}+{y}"
                    
                    # Only apply the geometry update if the position values actually change
                    if getattr(self, '_last_geo', '') != target_geometry:
                        self.root.geometry(target_geometry)
                        self._last_geo = target_geometry
                        
                    self.root.deiconify()
                    self.root.lift()
                except Exception:
                    pass
            else:
                self.root.withdraw()
        self.root.after(40, self._default_sync_loop)

def draw_custom_screen_markers(target_hwnd, markers_dict):
    """
    Fallback drawing context using native Win32 device context pen utilities.
    """
    if not target_hwnd or win32gui.IsIconic(target_hwnd) or not markers_dict:
        return

    try:
        left, top, right, bottom = win32gui.GetClientRect(target_hwnd)
        w_win = right - left
        h_win = bottom - top

        scale_x = w_win / 1280.0
        scale_y = h_win / 960.0

        hdc = win32gui.GetDC(target_hwnd)
        win32gui.SetBkMode(hdc, win32con.TRANSPARENT)

        for marker_id, config in markers_dict.items():
            rect_data = config.get("rect")
            if not rect_data or len(rect_data) < 4:
                continue
                
            color_data = config.get("color", [255, 255, 0])
            thickness = config.get("thickness", 2)
            label = config.get("label", "")
            
            rx, ry, rw, rh = rect_data[0], rect_data[1], rect_data[2], rect_data[3]
            abs_x = int(rx * scale_x)
            abs_y = int(ry * scale_y)
            abs_w = int(rw * scale_x)
            abs_h = int(rh * scale_y)

            if isinstance(color_data, (list, tuple)) and len(color_data) >= 3:
                r_c, g_c, b_c = color_data[2], color_data[1], color_data[0]
            else:
                r_c, g_c, b_c = 255, 255, 0

            pen = win32gui.CreatePen(win32con.PS_SOLID, thickness, win32api.RGB(r_c, g_c, b_c))
            old_pen = win32gui.SelectObject(hdc, pen)
            win32gui.SetTextColor(hdc, win32api.RGB(r_c, g_c, b_c))

            win32gui.MoveToEx(hdc, abs_x, abs_y)
            win32gui.LineTo(hdc, abs_x + abs_w, abs_y)
            win32gui.LineTo(hdc, abs_x + abs_w, abs_y + abs_h)
            win32gui.LineTo(hdc, abs_x, abs_y + abs_h)
            win32gui.LineTo(hdc, abs_x, abs_y)

            if label:
                win32gui.DrawText(hdc, str(label), -1, 
                                  (abs_x, abs_y - 18, abs_x + 400, abs_y), 
                                  win32con.DT_LEFT | win32con.DT_NOCLIP)

            win32gui.SelectObject(hdc, old_pen)
            win32gui.DeleteObject(pen)

        win32gui.ReleaseDC(target_hwnd, hdc)
    except Exception as e:
        print(f"\n[DIAGNOSTIC CRITICAL GDI ERROR] native GDI engine failed: {e}")
