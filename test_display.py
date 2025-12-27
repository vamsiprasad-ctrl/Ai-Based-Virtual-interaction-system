# ============================================================
# TEST: Check if OpenCV can display windows
# ============================================================

import cv2
import numpy as np
import time

print("[TEST] Starting window display test...")

# Create a simple colored frame
frame = np.zeros((480, 640, 3), dtype=np.uint8)
frame[:, :] = (0, 255, 0)  # Green

cv2.imshow("Test Window", frame)
print("[TEST] Window created - you should see a green window")
print("[TEST] Press ANY KEY to continue...")

cv2.waitKey(0)
cv2.destroyAllWindows()

print("[TEST] Done!")
