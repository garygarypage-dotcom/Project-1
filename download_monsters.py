import os
import sys
import urllib.request
import cv2
import numpy as np

print("=========================================================")
print("     MAPLESTORY AUTOMATED IMAGE TARGET GENERATOR         ")
print("=========================================================")

# UNIVERSAL ID DICTIONARY: Maps slot positions to live game database IDs.
# You can change these numbers anytime to target higher level monsters!
TARGET_MAP_MONSTERS = {
    1: 100100,   # Snail
    2: 100101,   # Blue Snail
    3: 100102,   # Red Snail
    4: 1110101,  # Shroom
    5: 1110100,  # Stump
    6: 1210100,  # Slime
    7: 1210102   # Orange Mushroom
}

def clean_and_format_sprite(raw_img_data, slot_num):
    """
    Processes the raw image binary matrix, strips transparency channels,
    and forces the texture assets into clean 32x32 template dimensions.
    """
    arr = np.asarray(bytearray(raw_img_data), dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_UNCHANGED)
    
    if img is None:
        return False

    # FIXED: Corrected multi-channel resolution index layer mapping check
    if len(img.shape) == 3 and img.shape[2] == 4:
        alpha_channel = img[:, :, 3]
        rgb_channels = img[:, :, :3]
        bg_sheet = np.zeros(rgb_channels.shape, dtype=np.uint8)
        bg_sheet[:] = (45, 45, 45) 
        alpha_factor = alpha_channel[:, :, np.newaxis] / 255.0
        img = cv2.convertScaleAbs(rgb_channels * alpha_factor + bg_sheet * (1.0 - alpha_factor))
    elif len(img.shape) != 3:
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)

    target_w, target_h = 32, 32
    h, w = img.shape[:2]
    if h == 0 or w == 0:
        return False
        
    scale = min(target_w / w, target_h / h)
    new_w, new_h = max(1, int(w * scale)), max(1, int(h * scale))
    resized_crop = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
    
    pad_h = (target_h - new_h) // 2
    pad_w = (target_w - new_w) // 2
    
    final_template = cv2.copyMakeBorder(
        resized_crop, 
        pad_h, max(0, target_h - new_h - pad_h), 
        pad_w, max(0, target_w - new_w - pad_w), 
        cv2.BORDER_CONSTANT, value=(45, 45, 45)
    )
    
    final_template = cv2.resize(final_template, (32, 32))
    filename = f"slot{slot_num}.png"
    cv2.imwrite(filename, final_template)
    print(f"[SUCCESS] Slot {slot_num} target compiled and saved as: {filename}")
    return True

def create_emergency_fallback_template(slot_num):
    """Generates a dummy solid marker placeholder block so the bot can boot up without internet."""
    fallback_matrix = np.zeros((32, 32, 3), dtype=np.uint8)
    fallback_matrix[:] = (45, 45, 200)  # Bright indicator patch
    filename = f"slot{slot_num}.png"
    cv2.imwrite(filename, fallback_matrix)
    print(f"[-] Offline Fallback: Generated dummy asset for Slot {slot_num} -> {filename}")

print("[*] Connecting directly to MapleStory.io Asset API...")
success_count = 0

for slot_num, mob_id in TARGET_MAP_MONSTERS.items():
    # FIXED: Injected API node tracking structure paths properly to prevent name errors
    url = f"https://maplestory.io{mob_id}/render/stand"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
        with urllib.request.urlopen(req, timeout=8) as response:
            raw_data = response.read()
            if clean_and_format_sprite(raw_data, slot_num):
                success_count += 1
    except Exception as e:
        print(f"[!] Target API network lookup skipped for Slot {slot_num} (Mob {mob_id})")
        create_emergency_fallback_template(slot_num)

print(f"\n[+] Complete! Generated {success_count}/7 universal target slots successfully.")
