import os
import sys

# Set environment variables BEFORE any imports to suppress logs
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'  # Suppress TensorFlow logs: 3=ERROR only
os.environ['MEDIAPIPE_DISABLE_GPU'] = '1'
os.environ['TF_FORCE_GPU_ALLOW_GROWTH'] = 'false'

import warnings
warnings.filterwarnings('ignore')

import cv2
import mediapipe as mp
import pyautogui
import numpy as np
import time
import io
import logging

# Suppress all loggers after imports
logging.getLogger('tensorflow').setLevel(logging.ERROR)
logging.getLogger('mediapipe').setLevel(logging.ERROR)
for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)

# ============================================================
# MediaPipe IrisTracker - Advanced Eye Tracking with Iris Detection
# ============================================================

class IrisTracker:
    def __init__(self):
        """Initialize camera and MediaPipe FaceMesh with iris detection"""
        # Camera setup - high resolution for better eye tracking
        self.cap = cv2.VideoCapture(0)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        self.cap.set(cv2.CAP_PROP_FPS, 30)
        
        # Initialize MediaPipe FaceMesh with iris refinement
        # refine_landmarks=True provides 10 iris landmarks (5 per eye)
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            static_image_mode=False,
            max_num_faces=1,
            refine_landmarks=True,  # CRITICAL: Enables iris detection
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        
        # Iris landmark indices (from MediaPipe documentation with refine_landmarks=True)
        # Left eye iris: landmarks 468-472 (5 points)
        # Right eye iris: landmarks 473-477 (5 points)
        self.left_iris_indices = [468, 469, 470, 471, 472]
        self.right_iris_indices = [473, 474, 475, 476, 477]
        
        # Eye landmarks for bounds calculation
        # Left eye contour: landmarks 33, 160, 158, 133, 153, 144
        # Right eye contour: landmarks 263, 387, 385, 362, 380, 373
        self.left_eye_indices = [33, 160, 158, 133, 153, 144]
        self.right_eye_indices = [263, 387, 385, 362, 380, 373]
        
        # State tracking
        self.last_left_gaze = "CENTER"
        self.last_right_gaze = "CENTER"
        self.left_gaze_start = None
        self.right_gaze_start = None
        self.last_action_time = time.time()
        
        # Blink tracking
        self.blink_count = 0
        self.blink_time = None
        self.eyes_closed = False
        self.last_blink_time = time.time()
        self.blink_threshold = 0.25  # EAR threshold for closed eyes
        
        # Wink detection (single eye)
        self.left_eye_closed = False
        self.right_eye_closed = False
        self.last_left_wink_time = time.time()
        self.last_right_wink_time = time.time()
        
        # Gaze trail for visualization
        self.gaze_trail = []
        self.max_trail_length = 15
        
        # Session statistics
        self.session_start = time.time()
        self.action_count = 0
        self.blink_total = 0
        self.calibration_mode = False
        self.calibration_points = []
        
        # Head position tracking
        self.head_position = {"x": 0, "y": 0, "z": 0}
        
        # Gaze stability and accuracy
        self.gaze_stability = 0.0
        self.consecutive_same_gaze = 0
        
        self.running = True
        self.debug_mode = False
        
    def get_iris_position(self, landmarks, iris_indices):
        """Average iris landmark positions (5 points per iris)"""
        iris_points = np.array([
            [landmarks[i].x, landmarks[i].y] for i in iris_indices
        ])
        iris_x = np.mean(iris_points[:, 0])
        iris_y = np.mean(iris_points[:, 1])
        return iris_x, iris_y
    
    def get_eye_bounds(self, landmarks, eye_indices):
        """Get left and right bounds of eye from 6 landmark points"""
        eye_points = np.array([
            [landmarks[i].x, landmarks[i].y] for i in eye_indices
        ])
        eye_left = np.min(eye_points[:, 0])
        eye_right = np.max(eye_points[:, 0])
        eye_width = eye_right - eye_left
        return eye_left, eye_right, eye_width
    
    def calculate_ear(self, landmarks, eye_indices):
        """Calculate Eye Aspect Ratio (EAR) for blink detection"""
        # EAR = distance(vertical) / distance(horizontal)
        # Using simplified version with available landmarks
        eye_points = np.array([
            [landmarks[i].x, landmarks[i].y] for i in eye_indices[:6]
        ])
        
        # Vertical distances
        v1 = np.linalg.norm(eye_points[1] - eye_points[5])
        v2 = np.linalg.norm(eye_points[2] - eye_points[4])
        
        # Horizontal distance
        h = np.linalg.norm(eye_points[0] - eye_points[3])
        
        # EAR calculation
        ear = (v1 + v2) / (2.0 * h) if h > 0 else 0.5
        return ear
    
    def detect_blink(self, left_ear, right_ear, t):
        """Detect blinks and count sequences"""
        avg_ear = (left_ear + right_ear) / 2
        
        # Detect if eyes are closed
        is_closed = avg_ear < self.blink_threshold
        
        # Detect individual eye closure (wink)
        left_closed = left_ear < self.blink_threshold
        right_closed = right_ear < self.blink_threshold
        
        # # DISABLED: Wink detection causes confusion with blink detection
        # # LEFT WINK detection
        # if left_closed and not self.left_eye_closed and not right_closed:
        #     if (t - self.last_left_wink_time) > 0.5:
        #         print(f"[WINK] Left Eye | Volume Up")
        #         pyautogui.press('volumeup')
        #         self.last_left_wink_time = t
        #         self.action_count += 1
        # 
        # # RIGHT WINK detection
        # if right_closed and not self.right_eye_closed and not left_closed:
        #     if (t - self.last_right_wink_time) > 0.5:
        #         print(f"[WINK] Right Eye | Volume Down")
        #         pyautogui.press('volumedown')
        #         self.last_right_wink_time = t
        #         self.action_count += 1
        
        # Blink detected (transition from open to closed)
        if is_closed and not self.eyes_closed:
            self.blink_count += 1
            self.blink_time = t
            self.blink_total += 1
            print(f"[BLINK] Blink #{self.blink_count} detected")
            
            # Check for blink sequences
            if self.blink_count == 2 and (t - self.last_blink_time) < 0.5:
                print(f"[DOUBLE BLINK] Next Tab (Ctrl+Tab)")
                pyautogui.hotkey('ctrl', 'tab')  # Next Tab
                self.action_count += 1
            elif self.blink_count == 3 and (t - self.last_blink_time) < 0.7:
                print(f"[TRIPLE BLINK] Switch Window (Alt+Tab)")
                pyautogui.hotkey('alt', 'tab')  # Switch window
                self.action_count += 1
            
            self.last_blink_time = t
        
        # Reset blink count after timeout
        if self.blink_time and (t - self.blink_time) > 1.0:
            self.blink_count = 0
            self.blink_time = None
        
        self.eyes_closed = is_closed
        self.left_eye_closed = left_closed
        self.right_eye_closed = right_closed
        return avg_ear
    
    def detect_gaze(self, iris_x, eye_left, eye_right, eye_width):
        """
        Determine gaze direction based on iris position within eye bounds.
        Thresholds optimized for MediaPipe iris detection:
        - LEFT: iris_ratio < 0.40
        - CENTER: 0.40 <= iris_ratio <= 0.60
        - RIGHT: iris_ratio > 0.60
        """
        if eye_width > 0:
            iris_ratio = (iris_x - eye_left) / eye_width
        else:
            return "CENTER"
        
        # CORRECT: Natural gaze direction mapping
        # iris on left side (low ratio) = looking LEFT
        # iris on right side (high ratio) = looking RIGHT
        if iris_ratio < 0.40:
            return "LEFT"
        elif iris_ratio > 0.60:
            return "RIGHT"
        else:
            return "CENTER"
    
    def track_head_position(self, landmarks):
        """Track head position using facial landmarks"""
        # Get key facial points for head pose estimation
        nose = landmarks[1]
        left_eye = landmarks[33]
        right_eye = landmarks[263]
        
        self.head_position["x"] = nose.x
        self.head_position["y"] = nose.y
        self.head_position["z"] = nose.z
    
    def update_gaze_trail(self, iris_x, iris_y, w, h):
        """Update gaze trail for visualization"""
        point = (int(iris_x * w), int(iris_y * h))
        self.gaze_trail.append(point)
        
        if len(self.gaze_trail) > self.max_trail_length:
            self.gaze_trail.pop(0)
    
    def draw_gaze_trail(self, frame):
        """Draw gaze trajectory trail"""
        if len(self.gaze_trail) < 2:
            return
        
        for i in range(1, len(self.gaze_trail)):
            # Gradient color from old to new
            alpha = i / len(self.gaze_trail)
            color = (int(255 * alpha), int(200 * (1 - alpha)), 100)
            thickness = max(1, int(3 * alpha))
            cv2.line(frame, self.gaze_trail[i-1], self.gaze_trail[i], color, thickness)
    
    def process_frame(self, frame):
        """Process frame and detect eye gaze"""
        h, w, c = frame.shape
        # Action deduplication: Only one action per frame
        action_triggered = False
        
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Run MediaPipe FaceMesh
        results = self.face_mesh.process(rgb_frame)
        t = time.time()
        
        # Draw HUD background
        cv2.rectangle(frame, (10, 55), (450, 230), (20, 20, 20), -1)
        cv2.rectangle(frame, (10, 55), (450, 230), (0, 255, 0), 2)
        
        if not results.multi_face_landmarks:
            cv2.putText(frame, "X NO FACE FOUND", (20, 80),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            return frame
        
        cv2.putText(frame, "[OK] FACE DETECTED", (20, 80),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        landmarks = results.multi_face_landmarks[0].landmark
        
        # ===== HEAD POSITION TRACKING =====
        self.track_head_position(landmarks)
        
        # ===== BLINK DETECTION =====
        left_ear = self.calculate_ear(landmarks, self.left_eye_indices)
        right_ear = self.calculate_ear(landmarks, self.right_eye_indices)
        avg_ear = self.detect_blink(left_ear, right_ear, t)
        
        # ===== LEFT EYE PROCESSING =====
        left_iris_x, left_iris_y = self.get_iris_position(landmarks, self.left_iris_indices)
        left_eye_left, left_eye_right, left_eye_width = self.get_eye_bounds(
            landmarks, self.left_eye_indices
        )
        
        left_gaze = self.detect_gaze(left_iris_x, left_eye_left, left_eye_right, left_eye_width)
        
        # Update left eye state
        if left_gaze != self.last_left_gaze:
            self.left_gaze_start = None
            self.last_left_gaze = left_gaze
        elif left_gaze != "CENTER":
            if self.left_gaze_start is None:
                self.left_gaze_start = t
            elif (t - self.left_gaze_start) >= 0.8:  # 0.8 second hold time (increased from 0.4s)
                if (t - self.last_action_time) > 1.2:  # 1.2 second cooldown
                    if left_gaze == "LEFT":
                        hold_time = t - self.left_gaze_start
                        print(f"[ACTION] LEFT EYE <- LEFT (Hold {hold_time:.2f}s) | Ctrl+Shift+Tab | Previous Tab")
                        pyautogui.hotkey('ctrl', 'shift', 'tab')  # Previous Tab
                        self.last_action_time = t
                        self.left_gaze_start = None
        
        # Draw left iris - ENHANCED VISIBILITY
        left_iris_x_px = int(left_iris_x * w)
        left_iris_y_px = int(left_iris_y * h)
        # Update gaze trail
        self.update_gaze_trail(left_iris_x, left_iris_y, w, h)
        # Outer circle (larger)
        cv2.circle(frame, (left_iris_x_px, left_iris_y_px), 12, (0, 255, 255), 3)  # Bright cyan outline
        # Middle circle
        cv2.circle(frame, (left_iris_x_px, left_iris_y_px), 8, (255, 255, 0), 2)   # Yellow
        # Inner filled circle
        cv2.circle(frame, (left_iris_x_px, left_iris_y_px), 5, (255, 255, 0), -1)  # Yellow fill
        # Crosshair
        cv2.line(frame, (left_iris_x_px - 15, left_iris_y_px), (left_iris_x_px + 15, left_iris_y_px), (0, 255, 255), 2)
        cv2.line(frame, (left_iris_x_px, left_iris_y_px - 15), (left_iris_x_px, left_iris_y_px + 15), (0, 255, 255), 2)
        
        # ===== RIGHT EYE PROCESSING =====
        right_iris_x, right_iris_y = self.get_iris_position(landmarks, self.right_iris_indices)
        right_eye_left, right_eye_right, right_eye_width = self.get_eye_bounds(
            landmarks, self.right_eye_indices
        )
        
        right_gaze = self.detect_gaze(right_iris_x, right_eye_left, right_eye_right, right_eye_width)
        
        # Update right eye state
        if right_gaze != self.last_right_gaze:
            self.right_gaze_start = None
            self.last_right_gaze = right_gaze
        elif right_gaze != "CENTER":
            if self.right_gaze_start is None:
                self.right_gaze_start = t
            elif (t - self.right_gaze_start) >= 0.8:  # 0.8 second hold time (increased from 0.4s)
                if (t - self.last_action_time) > 1.2:  # 1.2 second cooldown
                    if right_gaze == "RIGHT":
                        hold_time = t - self.right_gaze_start
                        print(f"[ACTION] RIGHT EYE -> RIGHT (Hold {hold_time:.2f}s) | Ctrl+Tab | Next Tab")
                        pyautogui.hotkey('ctrl', 'tab')  # Next Tab
                        self.last_action_time = t
                        self.right_gaze_start = None
        
        # Draw right iris - ENHANCED VISIBILITY
        right_iris_x_px = int(right_iris_x * w)
        right_iris_y_px = int(right_iris_y * h)
        # Outer circle (larger)
        cv2.circle(frame, (right_iris_x_px, right_iris_y_px), 12, (0, 165, 255), 3)  # Bright orange outline
        # Middle circle
        cv2.circle(frame, (right_iris_x_px, right_iris_y_px), 8, (0, 255, 255), 2)   # Cyan
        # Inner filled circle
        cv2.circle(frame, (right_iris_x_px, right_iris_y_px), 5, (0, 255, 255), -1)  # Cyan fill
        # Crosshair
        cv2.line(frame, (right_iris_x_px - 15, right_iris_y_px), (right_iris_x_px + 15, right_iris_y_px), (0, 165, 255), 2)
        cv2.line(frame, (right_iris_x_px, right_iris_y_px - 15), (right_iris_x_px, right_iris_y_px + 15), (0, 165, 255), 2)
        
        # ===== DETAILED HUD DISPLAY =====
        # Panel background
        cv2.rectangle(frame, (10, 35), (605, 215), (0, 0, 0), -1)
        cv2.rectangle(frame, (10, 35), (605, 215), (0, 255, 0), 2)
        
        # Title
        cv2.putText(frame, "??? Detecting...", (25, 65),
                   cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2)
        
        # Eye Corners
        left_eye_left_px = int(left_eye_left * w)
        right_eye_right_px = int(left_eye_right * w)
        cv2.putText(frame, f"Eye Corners: L={left_eye_left_px}px, R={right_eye_right_px}px", (25, 95),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 0), 1)
        
        # Pupil Position (using left eye iris as example)
        pupil_pos = int(left_iris_x_px)
        cv2.putText(frame, f"Pupil Position: X={pupil_pos}px", (25, 120),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 0), 1)
        
        # Gaze Ratio with breakdown
        left_ratio = (left_iris_x - left_eye_left) / left_eye_width if left_eye_width > 0 else 0.5
        right_ratio = (right_iris_x - right_eye_left) / right_eye_width if right_eye_width > 0 else 0.5
        avg_ratio = (left_ratio + right_ratio) / 2
        
        ratio_text = f"Gaze Ratio: {avg_ratio:.2f} (L:{left_ratio:.1f} | C:0.5 | R:{right_ratio:.1f})"
        cv2.putText(frame, ratio_text, (25, 145),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 0), 1)
        
        # Cooldown timer
        cooldown = max(0, 1.2 - (t - self.last_action_time))
        cooldown_text = f"Cooldown: {cooldown:.2f}s"
        cv2.putText(frame, cooldown_text, (25, 170),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 0), 1)
        
        # Status line - Current gaze
        status_text = f"Status: L={self.last_left_gaze} | R={self.last_right_gaze}"
        cv2.putText(frame, status_text, (25, 195),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 0), 1)
        
        # Blink indicator
        blink_color = (0, 0, 255) if self.eyes_closed else (0, 255, 0)
        blink_text = f"Blink: {'CLOSED' if self.eyes_closed else 'OPEN'} | EAR: {avg_ear:.2f} | Count: {self.blink_count}"
        cv2.putText(frame, blink_text, (25, 220),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.55, blink_color, 1)
        
        # ===== DRAW GAZE TRAIL =====
        self.draw_gaze_trail(frame)
        
        # ===== SIDE PANEL - STATISTICS =====
        session_time = time.time() - self.session_start
        stats_x = w - 300
        cv2.rectangle(frame, (stats_x - 10, 50), (w - 10, 300), (0, 0, 0), -1)
        cv2.rectangle(frame, (stats_x - 10, 50), (w - 10, 300), (0, 255, 200), 2)
        
        cv2.putText(frame, "SESSION STATS", (stats_x, 75),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 200), 1)
        cv2.putText(frame, f"Time: {int(session_time)}s", (stats_x, 100),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 255, 100), 1)
        cv2.putText(frame, f"Actions: {self.action_count}", (stats_x, 120),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 255, 100), 1)
        cv2.putText(frame, f"Blinks: {self.blink_total}", (stats_x, 140),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 255, 100), 1)
        cv2.putText(frame, f"Head X: {self.head_position['x']:.2f}", (stats_x, 160),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 255, 100), 1)
        cv2.putText(frame, f"Head Y: {self.head_position['y']:.2f}", (stats_x, 180),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 255, 100), 1)
        cv2.putText(frame, f"L-EAR: {left_ear:.3f}", (stats_x, 200),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 200, 255), 1)
        cv2.putText(frame, f"R-EAR: {right_ear:.3f}", (stats_x, 220),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 200, 255), 1)
        cv2.putText(frame, f"Wink L: {'YES' if self.left_eye_closed else 'NO'}", (stats_x, 240),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 100, 255), 1)
        cv2.putText(frame, f"Wink R: {'YES' if self.right_eye_closed else 'NO'}", (stats_x, 260),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 100, 255), 1)
        # Instructions at bottom
        cv2.putText(frame, "Q: Quit | D: Debug Toggle", (20, h - 20),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        
        return frame
    
    def run(self):
        """Main tracking loop"""
        print("=" * 60)
        print("EYE TRACKING MODULE - MediaPipe IRIS DETECTION")
        print("=" * 60)
        
        print("\n[1] Opening camera...")
        if not self.cap.isOpened():
            print("[X] Cannot open camera")
            return
        print("[OK] Camera OK (1280x720@30fps)")
        
        print("[2] Loading MediaPipe FaceMesh...")
        print("[OK] MediaPipe loaded with iris detection")
        
        print("[3] Display initialized (1280x800)")
        print("\n[4] Running MediaPipe eye tracking (Press Q to quit)\n")
        
        frame_count = 0
        while self.running:
            ret, frame = self.cap.read()
            if not ret:
                print("✗ Cannot read frame")
                break
            
            frame = cv2.resize(frame, (1280, 720))
            frame = self.process_frame(frame)
            
            frame_count += 1
            
            # Display window at 1280x800
            display_frame = cv2.copyMakeBorder(frame, 0, 80, 0, 0, cv2.BORDER_CONSTANT, 
                                               value=(20, 20, 20))
            cv2.imshow("Eye Tracking - MediaPipe", display_frame)
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                self.running = False
            elif key == ord('d'):
                self.debug_mode = not self.debug_mode
                print(f"Debug mode: {'ON' if self.debug_mode else 'OFF'}")
        
        self.cap.release()
        cv2.destroyAllWindows()
        print("\n[OK] Eye tracking closed")

if __name__ == "__main__":
    tracker = IrisTracker()
    tracker.run()
