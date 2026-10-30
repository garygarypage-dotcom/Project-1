import win32gui
import win32con
import time
import sys
import traceback

_KEY_STATES = {}

def send_isolated_key_down(hwnd, key_code):
    if not hwnd: return
    try:
        vk_code = ord(key_code.upper()) if isinstance(key_code, str) else key_code
        if not _KEY_STATES.get(vk_code, False):
            win32gui.PostMessage(hwnd, win32con.WM_KEYDOWN, vk_code, 0)
            _KEY_STATES[vk_code] = True
    except Exception as e:
        print(f"[INPUT ERR] Key down failed for {key_code}: {e}", file=sys.stderr)

def send_isolated_key_up(hwnd, key_code):
    if not hwnd: return
    try:
        vk_code = ord(key_code.upper()) if isinstance(key_code, str) else key_code
        if _KEY_STATES.get(vk_code, False):
            win32gui.PostMessage(hwnd, win32con.WM_KEYUP, vk_code, 0)
            _KEY_STATES[vk_code] = False
    except Exception as e:
        print(f"[INPUT ERR] Key up failed for {key_code}: {e}", file=sys.stderr)

def press_and_release_key(hwnd, key_code, duration=0.05):
    if not hwnd: return
    try:
        vk_code = ord(key_code.upper()) if isinstance(key_code, str) else key_code
        win32gui.PostMessage(hwnd, win32con.WM_KEYDOWN, vk_code, 0)
        time.sleep(duration)
        win32gui.PostMessage(hwnd, win32con.WM_KEYUP, vk_code, 0)
    except Exception as e:
        print(f"[INPUT ERR] Press/Release failed for {key_code}: {e}", file=sys.stderr)

def handle_defense(hwnd, hp_pixels, mp_pixels, current_time, last_hp, last_mp, hp_key, mp_key, log_cb):
    if hp_pixels < 25 and (current_time - last_hp > 1.2):
        log_cb(f"[DEFENSE] Health threshold trigger ({hp_pixels}px). Sending use potion key.")
        press_and_release_key(hwnd, hp_key)
        last_hp = current_time
    if mp_pixels < 20 and (current_time - last_mp > 1.2):
        log_cb(f"[DEFENSE] Mana threshold trigger ({mp_pixels}px). Sending use potion key.")
        press_and_release_key(hwnd, mp_key)
        last_mp = current_time
    return last_hp, last_mp

def handle_platform_pathing(hwnd, coords, current_platform, platforms, current_time, jump_key, attack_key, log_cb):
    if not platforms or not isinstance(coords, tuple) or len(coords) < 2: return False
    rel_x = coords[0]
    active_plat = next((p for p in platforms if p["name"] == current_platform), None)
    if not active_plat: return False

    VK_LEFT, VK_RIGHT = win32con.VK_LEFT, win32con.VK_RIGHT
    if rel_x <= active_plat["x_min"] + 2:
        send_isolated_key_up(hwnd, VK_LEFT)
        send_isolated_key_down(hwnd, VK_RIGHT)
        return True
    elif rel_x >= active_plat["x_max"] - 2:
        send_isolated_key_up(hwnd, VK_RIGHT)
        send_isolated_key_down(hwnd, VK_LEFT)
        return True

    if not _KEY_STATES.get(VK_LEFT, False) and not _KEY_STATES.get(VK_RIGHT, False):
        send_isolated_key_down(hwnd, VK_RIGHT)
    return False

def handle_offense(hwnd, target_count, current_time, last_combat, attack_key, skill_key, log_cb):
    if target_count > 0 and (current_time - last_combat > 0.35):
        press_and_release_key(hwnd, attack_key, duration=0.03)
        return current_time
    return last_combat

def release_all_keys(hwnd):
    if not hwnd: return
    special_keys = {'space': win32con.VK_SPACE, 'alt': win32con.VK_MENU}
    all_nav_keys = [win32con.VK_LEFT, win32con.VK_RIGHT, win32con.VK_UP, win32con.VK_DOWN, 'space', 'alt']
    for k in all_nav_keys:
        if isinstance(k, str):
            vk_code = special_keys.get(k.lower(), ord(k.upper()) if len(k) == 1 else None)
        else:
            vk_code = k
        if vk_code is not None:
            win32gui.PostMessage(hwnd, win32con.WM_KEYUP, vk_code, 0)
    global _KEY_STATES
    _KEY_STATES.clear()