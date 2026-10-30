import os
import sys
import cv2
import numpy as np

print("=========================================================")
print("   MAPLESTORY AUTOMATED IMAGE TARGET LOCAL GENERATOR     ")
print("=========================================================")

TOTAL_SLOTS = 7

def create_local_placeholder_template(slot_num):
    """Generates a high-contrast target marker placeholder frame cleanly."""
    fallback_matrix = np.zeros((32, 32, 3), dtype=np.uint8)
    # Fill with a neutral gray background matching the template baseline setup
    fallback_matrix[:] = (45, 45, 45)
    
    # Draw a small center crosshair indicator to verify the asset is active
    cv2.drawMarker(fallback_matrix, (16, 16), (0, 255, 255), cv2.MARKER_CROSS, 8, 1)
    
    filename = f"slot{slot_num}.png"
    cv2.imwrite(filename, fallback_matrix)
    print(f"[READY] Slot {slot_num} placeholder compiled -> {filename}")

print("[*] Instantiating localized baseline template sheets...")
for slot_idx in range(1, TOTAL_SLOTS + 1):
    create_local_placeholder_template(slot_idx)

print(f"\n[+] Complete! All {TOTAL_SLOTS} local tracking target slots are initialized.")
print("You can now safely open vision_engine.py and click game objects to assign custom targets.")
