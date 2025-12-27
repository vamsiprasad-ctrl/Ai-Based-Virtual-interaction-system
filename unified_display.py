# ============================================================
# UNIFIED MULTI-MODAL SYSTEM - Eyes + Gestures + Voice
# ============================================================
# Single display window showing both eye and gesture cameras

import cv2
import mediapipe as mp
import numpy as np
import threading
import time
import os

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ['MEDIAPIPE_DISABLE_GPU'] = '1'

from config import EYE_CONFIG, GESTURE_CONFIG, COLORS
from event_bus import EventType, get_event_bus, emit_event


class UnifiedDisplay:
    """Combined eye tracking and gesture recognition with single display"""
    
    def __init__(self):
        self.event_bus = get_event_bus()
        self.running = True
        
        # Eye components
        self.eye_cap = cv2.VideoCapture(0)
        if not self.eye_cap.isOpened():
            raise RuntimeError("Cannot open camera for eye tracking")
        self.eye_cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.eye_cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        # Gesture components
        self.gesture_cap = cv2.VideoCapture(0)
        if not self.gesture_cap.isOpened():
            raise RuntimeError("Cannot open camera for gesture recognition")
        self.gesture_cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.gesture_cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        # MediaPipe Face Mesh
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            static_image_mode=False,
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        
        # MediaPipe Hands
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=2,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.5,
            model_complexity=1
        )
        
        # Eye landmarks
        self.left_iris_indices = [468, 469, 470, 471, 472]
        self.right_iris_indices = [473, 474, 475, 476, 477]
        self.left_eye_indices = [33, 160, 158, 133, 153, 144]
        self.right_eye_indices = [263, 387, 385, 362, 380, 373]
        
        # State
        self.eye_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        self.gesture_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        self.eye_status = "Initializing..."
        self.gesture_status = "Initializing..."
        
        self.eye_gaze = "CENTER"
        self.gesture_type = "neutral"
        
        print("[UNIFIED] Display initialized")
    
    def process_eye_frame(self, frame):
        """Process eye tracking frame"""
        h, w, c = frame.shape
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.face_mesh.process(rgb_frame)
        
        # HUD
        cv2.rectangle(frame, (10, 10), (630, 100), (0, 0, 0), -1)
        cv2.rectangle(frame, (10, 10), (630, 100), (0, 255, 0), 2)
        cv2.putText(frame, "EYE TRACKING", (20, 40),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        
        if not results.multi_face_landmarks:
            cv2.putText(frame, "No face detected", (20, 70),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 1)
            self.eye_status = "No face"
            return frame
        
        landmarks = results.multi_face_landmarks[0].landmark
        
        # Draw eyes
        left_iris_x = int(np.mean([landmarks[i].x for i in self.left_iris_indices]) * w)
        left_iris_y = int(np.mean([landmarks[i].y for i in self.left_iris_indices]) * h)
        cv2.circle(frame, (left_iris_x, left_iris_y), 10, (0, 200, 255), 3)
        cv2.putText(frame, "L", (left_iris_x - 20, left_iris_y - 15),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 200, 255), 1)
        
        right_iris_x = int(np.mean([landmarks[i].x for i in self.right_iris_indices]) * w)
        right_iris_y = int(np.mean([landmarks[i].y for i in self.right_iris_indices]) * h)
        cv2.circle(frame, (right_iris_x, right_iris_y), 10, (255, 0, 100), 3)
        cv2.putText(frame, "R", (right_iris_x + 10, right_iris_y - 15),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 100), 1)
        
        cv2.putText(frame, "Face detected", (20, 70),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 1)
        self.eye_status = "Face OK"
        
        return frame
    
    def process_gesture_frame(self, frame):
        """Process gesture recognition frame"""
        h, w, c = frame.shape
        frame = cv2.flip(frame, 1)
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.hands.process(rgb_frame)
        
        # HUD
        cv2.rectangle(frame, (10, 10), (630, 100), (0, 0, 0), -1)
        cv2.rectangle(frame, (10, 10), (630, 100), (100, 0, 255), 2)
        cv2.putText(frame, "GESTURE RECOGNITION", (20, 40),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (100, 0, 255), 2)
        
        if not results.multi_hand_landmarks:
            cv2.putText(frame, "No hands detected", (20, 70),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 1)
            self.gesture_status = "No hands"
            return frame
        
        # Draw hand landmarks
        for hand_landmarks in results.multi_hand_landmarks:
            for idx, lm in enumerate(hand_landmarks.landmark):
                x = int(lm.x * w)
                y = int(lm.y * h)
                cv2.circle(frame, (x, y), 4, (100, 0, 255), -1)
        
        cv2.putText(frame, f"Hands: {len(results.multi_hand_landmarks)}", (20, 70),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (100, 0, 255), 1)
        self.gesture_status = f"{len(results.multi_hand_landmarks)} hand(s)"
        
        return frame
    
    def run_eye_loop(self):
        """Eye processing loop (background thread)"""
        try:
            while self.running:
                ret, frame = self.eye_cap.read()
                if not ret:
                    break
                frame = cv2.resize(frame, (640, 480))
                self.eye_frame = self.process_eye_frame(frame)
        except Exception as e:
            print(f"[EYE] Loop error: {e}")
        finally:
            self.eye_cap.release()
    
    def run_gesture_loop(self):
        """Gesture processing loop (background thread)"""
        try:
            while self.running:
                ret, frame = self.gesture_cap.read()
                if not ret:
                    break
                frame = cv2.resize(frame, (640, 480))
                self.gesture_frame = self.process_gesture_frame(frame)
        except Exception as e:
            print(f"[GESTURE] Loop error: {e}")
        finally:
            self.gesture_cap.release()
    
    def run_voice_loop(self):
        """Voice processing loop (background thread)"""
        try:
            from voice_module import VoiceController
            controller = VoiceController()
            controller.event_bus = self.event_bus
            controller.run()
        except Exception as e:
            print(f"[VOICE] Error: {e}")
    
    def run(self):
        """Main display loop with all modalities"""
        print("\n" + "="*70)
        print("UNIFIED MULTI-MODAL SYSTEM - Eyes + Gestures + Voice")
        print("="*70)
        print("[UNIFIED] Starting all modules...\n")
        print("[*] You should see TWO windows:")
        print("    LEFT:  Eye Tracking")
        print("    RIGHT: Gesture Recognition")
        print("[*] Voice commands listening in background")
        print("[*] Press Q in either window to quit\n")
        print("="*70 + "\n")
        
        # Start background threads
        eye_thread = threading.Thread(target=self.run_eye_loop, daemon=True)
        eye_thread.start()
        time.sleep(0.5)
        
        gesture_thread = threading.Thread(target=self.run_gesture_loop, daemon=True)
        gesture_thread.start()
        time.sleep(0.5)
        
        voice_thread = threading.Thread(target=self.run_voice_loop, daemon=True)
        voice_thread.start()
        
        print("[UNIFIED] All threads started!")
        print("[UNIFIED] Displaying dual camera feed...\n")
        
        # Main display loop
        try:
            frame_count = 0
            while self.running:
                # Create combined display (2x1 side by side)
                h, w = 480, 640
                combined = np.zeros((h, w*2 + 20, 3), dtype=np.uint8)
                combined[:, :] = (20, 20, 20)
                
                # Left: Eye tracking
                combined[:h, :w] = self.eye_frame
                
                # Right: Gesture recognition
                combined[:h, w+20:] = self.gesture_frame
                
                cv2.imshow("EYE TRACKING (Left) | GESTURE RECOGNITION (Right) - Press Q to quit", combined)
                
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    print("\n[UNIFIED] Shutting down...")
                    self.running = False
                    break
                
                frame_count += 1
                if frame_count % 100 == 0:
                    print(f"[UNIFIED] Frame {frame_count} | EYE: {self.eye_status} | GESTURE: {self.gesture_status}")
                
                time.sleep(0.001)
        
        except Exception as e:
            print(f"[UNIFIED] Display error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.running = False
            eye_thread.join(timeout=2)
            gesture_thread.join(timeout=2)
            voice_thread.join(timeout=2)
            cv2.destroyAllWindows()
            print("[UNIFIED] Done!\n")


if __name__ == "__main__":
    try:
        display = UnifiedDisplay()
        display.run()
    except Exception as e:
        print(f"[ERROR] {e}")
