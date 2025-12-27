# ============================================================
# EYE TRACKING MODULE - Refactored for Integration
# ============================================================
# Lightweight version emitting events instead of controlling directly
# Works as part of unified multi-modal system

import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ['MEDIAPIPE_DISABLE_GPU'] = '1'

import cv2
import mediapipe as mp
import numpy as np
import time

# Delay imports to avoid circular dependency
EYE_CONFIG = None
COLORS = None
EventType = None
emit_event = None


def _init_imports():
    global EYE_CONFIG, COLORS, EventType, emit_event
    from config import EYE_CONFIG as EC, COLORS as C
    from event_bus import EventType as ET, emit_event as EE
    EYE_CONFIG = EC
    COLORS = C
    EventType = ET
    emit_event = EE


class IrisTracker:
    """Refactored eye tracking - emits events instead of direct control"""
    
    def __init__(self):
        _init_imports()  # Initialize imports immediately
        
        # Camera setup
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            print("[EYE] ERROR: Cannot open webcam!")
            raise RuntimeError("Webcam not accessible")
        
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, EYE_CONFIG["camera_width"])
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, EYE_CONFIG["camera_height"])
        self.cap.set(cv2.CAP_PROP_FPS, EYE_CONFIG["camera_fps"])
        
        # MediaPipe
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            static_image_mode=False,
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        
        # Iris indices
        self.left_iris_indices = [468, 469, 470, 471, 472]
        self.right_iris_indices = [473, 474, 475, 476, 477]
        self.left_eye_indices = [33, 160, 158, 133, 153, 144]
        self.right_eye_indices = [263, 387, 385, 362, 380, 373]
        
        # State
        self.last_left_gaze = "CENTER"
        self.last_right_gaze = "CENTER"
        self.left_gaze_start = None
        self.right_gaze_start = None
        self.last_action_time = time.time()
        
        # Blink
        self.blink_count = 0
        self.blink_time = None
        self.eyes_closed = False
        self.last_blink_time = time.time()
        self.blink_threshold = EYE_CONFIG["blink_threshold"]
        
        # Visualization
        self.gaze_trail = []
        
        self.running = True
        self.event_bus = None
        self.action_translator = None
        
        print("[EYE] Initialized")
    
    def detect_gaze(self, iris_x, eye_left, eye_right, eye_width):
        """Determine gaze direction"""
        if eye_width > 0:
            iris_ratio = (iris_x - eye_left) / eye_width
        else:
            return "CENTER"
        
        if iris_ratio < EYE_CONFIG["gaze_thresholds"]["left"]:
            return "LEFT"
        elif iris_ratio > EYE_CONFIG["gaze_thresholds"]["right"]:
            return "RIGHT"
        else:
            return "CENTER"
    
    def calculate_ear(self, landmarks, eye_indices):
        """Eye aspect ratio for blink detection"""
        eye_points = np.array([
            [landmarks[i].x, landmarks[i].y] for i in eye_indices[:6]
        ])
        
        v1 = np.linalg.norm(eye_points[1] - eye_points[5])
        v2 = np.linalg.norm(eye_points[2] - eye_points[4])
        h = np.linalg.norm(eye_points[0] - eye_points[3])
        
        return (v1 + v2) / (2.0 * h) if h > 0 else 0.5
    
    def detect_blink(self, left_ear, right_ear, t):
        """Detect blinks and emit events"""
        avg_ear = (left_ear + right_ear) / 2
        is_closed = avg_ear < self.blink_threshold
        
        if is_closed and not self.eyes_closed:
            self.blink_count += 1
            self.blink_time = t
            print(f"[EYE] Blink #{self.blink_count}")
            
            # Check sequences
            if self.blink_count == 2 and (t - self.last_blink_time) < EYE_CONFIG["double_blink_window"]:
                emit_event(
                    EventType.EYE_DOUBLE_BLINK,
                    "eye",
                    {"action": EYE_CONFIG["actions"]["double_blink"]},
                    priority=1
                )
            elif self.blink_count == 3 and (t - self.last_blink_time) < EYE_CONFIG["triple_blink_window"]:
                emit_event(
                    EventType.EYE_TRIPLE_BLINK,
                    "eye",
                    {"action": EYE_CONFIG["actions"]["triple_blink"]},
                    priority=1
                )
            
            self.last_blink_time = t
        
        if self.blink_time and (t - self.blink_time) > 1.0:
            self.blink_count = 0
            self.blink_time = None
        
        self.eyes_closed = is_closed
        return avg_ear
    
    def process_frame(self, frame):
        """Process and draw"""
        h, w, c = frame.shape
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.face_mesh.process(rgb_frame)
        t = time.time()
        
        # HUD background
        cv2.rectangle(frame, (10, 35), (605, 215), (0, 0, 0), -1)
        cv2.rectangle(frame, (10, 35), (605, 215), COLORS["primary"], 2)
        
        if not results.multi_face_landmarks:
            cv2.putText(frame, "X NO FACE", (20, 80),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, COLORS["error"], 2)
            return frame
        
        cv2.putText(frame, "[OK] FACE DETECTED", (20, 80),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, COLORS["primary"], 2)
        
        landmarks = results.multi_face_landmarks[0].landmark
        
        # Blink detection
        left_ear = self.calculate_ear(landmarks, self.left_eye_indices)
        right_ear = self.calculate_ear(landmarks, self.right_eye_indices)
        self.detect_blink(left_ear, right_ear, t)
        
        # LEFT EYE
        left_iris_x = np.mean([landmarks[i].x for i in self.left_iris_indices])
        left_eye_left = np.min([landmarks[i].x for i in self.left_eye_indices])
        left_eye_right = np.max([landmarks[i].x for i in self.left_eye_indices])
        left_eye_width = left_eye_right - left_eye_left
        
        left_gaze = self.detect_gaze(left_iris_x, left_eye_left, left_eye_right, left_eye_width)
        
        if left_gaze != self.last_left_gaze:
            self.left_gaze_start = None
            self.last_left_gaze = left_gaze
        elif left_gaze != "CENTER":
            if self.left_gaze_start is None:
                self.left_gaze_start = t
            elif (t - self.left_gaze_start) >= EYE_CONFIG["gaze_hold_time"]:
                if (t - self.last_action_time) > EYE_CONFIG["gaze_cooldown"]:
                    action_key = f"{left_gaze.lower()}_gaze"
                    action = EYE_CONFIG["actions"].get(action_key)
                    if action:
                        emit_event(
                            EventType.EYE_GAZE_LEFT,
                            "eye",
                            {"action": action, "details": action_key},
                            priority=2
                        )
                        print(f"[EYE] LEFT gaze -> {action}")
                        self.last_action_time = t
                        self.left_gaze_start = None
        
        # Draw LEFT iris
        left_iris_x_px = int(left_iris_x * w)
        left_iris_y_px = int(np.mean([landmarks[i].y for i in self.left_iris_indices]) * h)
        cv2.circle(frame, (left_iris_x_px, left_iris_y_px), EYE_CONFIG["iris_radius"], COLORS["secondary"], 3)
        cv2.circle(frame, (left_iris_x_px, left_iris_y_px), 8, COLORS["secondary"], 2)
        
        # RIGHT EYE
        right_iris_x = np.mean([landmarks[i].x for i in self.right_iris_indices])
        right_eye_left = np.min([landmarks[i].x for i in self.right_eye_indices])
        right_eye_right = np.max([landmarks[i].x for i in self.right_eye_indices])
        right_eye_width = right_eye_right - right_eye_left
        
        right_gaze = self.detect_gaze(right_iris_x, right_eye_left, right_eye_right, right_eye_width)
        
        if right_gaze != self.last_right_gaze:
            self.right_gaze_start = None
            self.last_right_gaze = right_gaze
        elif right_gaze != "CENTER":
            if self.right_gaze_start is None:
                self.right_gaze_start = t
            elif (t - self.right_gaze_start) >= EYE_CONFIG["gaze_hold_time"]:
                if (t - self.last_action_time) > EYE_CONFIG["gaze_cooldown"]:
                    action_key = f"{right_gaze.lower()}_gaze"
                    action = EYE_CONFIG["actions"].get(action_key)
                    if action:
                        emit_event(
                            EventType.EYE_GAZE_RIGHT,
                            "eye",
                            {"action": action, "details": action_key},
                            priority=2
                        )
                        print(f"[EYE] RIGHT gaze -> {action}")
                        self.last_action_time = t
                        self.right_gaze_start = None
        
        # Draw RIGHT iris
        right_iris_x_px = int(right_iris_x * w)
        right_iris_y_px = int(np.mean([landmarks[i].y for i in self.right_iris_indices]) * h)
        cv2.circle(frame, (right_iris_x_px, right_iris_y_px), EYE_CONFIG["iris_radius"], COLORS["accent"], 3)
        cv2.circle(frame, (right_iris_x_px, right_iris_y_px), 8, COLORS["accent"], 2)
        
        # Status display
        cv2.putText(frame, f"L: {self.last_left_gaze} | R: {self.last_right_gaze}", (20, 115),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, COLORS["primary"], 1)
        cv2.putText(frame, f"Blinks: {self.blink_count} | EAR: {(left_ear+right_ear)/2:.2f}", (20, 145),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, COLORS["primary"], 1)
        
        return frame
    
    def run(self):
        """Main tracking loop"""
        print("[EYE] Starting tracker...")
        
        while self.running:
            ret, frame = self.cap.read()
            if not ret:
                break
            
            frame = cv2.resize(frame, (EYE_CONFIG["camera_width"], EYE_CONFIG["camera_height"]))
            frame = self.process_frame(frame)
            
            display_frame = cv2.copyMakeBorder(frame, 0, 80, 0, 0, cv2.BORDER_CONSTANT, 
                                               value=(20, 20, 20))
            cv2.imshow("Eye Tracking", display_frame)
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                self.running = False
        
        self.cap.release()
        cv2.destroyAllWindows()
        print("[EYE] Stopped")


if __name__ == "__main__":
    tracker = IrisTracker()
    tracker.run()
