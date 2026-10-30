import cv2
import numpy as np

class MobDetector:
    def __init__(self, confidence_threshold=0.52):
        self.confidence_threshold = confidence_threshold
        self.tracked_mobs = []

    def process_frame(self, current_frame, annotated_frame, active_trackers):
        """
        Bypasses Canny template image matching to isolate active targets 
        directly through localized color spectrum analysis blocks.
        """
        self.tracked_mobs = []
        monster_count = 0

        try:
            # 1. Convert frame array context safely into HSV color space spectrum
            hsv = cv2.cvtColor(current_frame, cv2.COLOR_BGR2HSV)

            # 2. Define a wide, high-visibility color mask targeting character/mob highlights
            # This captures vibrant reddish/orange tints (like names, tags, and capes)
            lower_bound1 = np.array([0, 100, 100])
            upper_bound1 = np.array([10, 255, 255])
            lower_bound2 = np.array([160, 100, 100])
            upper_bound2 = np.array([180, 255, 255])

            mask1 = cv2.inRange(hsv, lower_bound1, upper_bound1)
            mask2 = cv2.inRange(hsv, lower_bound2, upper_bound2)
            combined_color_mask = cv2.bitwise_or(mask1, mask2)

            # 3. Extract contours from the generated binary matrix mask layers
            contours, _ = cv2.findContours(combined_color_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            for contour in contours:
                # Filter out microscopic pixel noise shapes to capture real targets
                area = cv2.contourArea(contour)
                if 80 < area < 4000:
                    x, y, w, h = cv2.boundingRect(contour)
                    
                    # Ensure bounding structures fall within standard monster grid shapes
                    if 15 < w < 120 and 15 < h < 120:
                        monster_count += 1
                        
                        mob_bounds_dict = {
                            "rect": [int(x), int(y), int(w), int(h)],
                            "name": f"ACTIVE TARGET #{monster_count}"
                        }
                        self.tracked_mobs.append(mob_bounds_dict)

                        # Draw fallback local validation shapes on dashboard preview widgets
                        cv2.rectangle(annotated_frame, (x, y), (x + w, y + h), (0, 255, 255), 2)

            if monster_count > 0:
                print(f"[MOB DIAGNOSTIC] Color isolation engine extracted {monster_count} live game targets.")

            return monster_count

        except Exception as e:
            print(f"[MOB DETECTOR COLOR ENGINE FAIL] Loop exception raised: {e}")
            return 0
