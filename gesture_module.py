# ============================================================
# GESTURE MODULE - Refactored for Integration
# ============================================================
# Emits events instead of direct control

import cv2
import mediapipe as mp
import pyautogui
import numpy as np
import math
import time

# Delay imports to avoid circular dependency
GESTURE_CONFIG = None
COLORS = None
EventType = None
emit_event = None


def _init_imports():
    global GESTURE_CONFIG, COLORS, EventType, emit_event
    from config import GESTURE_CONFIG as GC, COLORS as C
    from event_bus import EventType as ET, emit_event as EE
    GESTURE_CONFIG = GC
    COLORS = C
    EventType = ET
    emit_event = EE


class HandGestureController:
    """Refactored gesture control - emits events"""
    
    def __init__(self):
        _init_imports()  # Initialize imports immediately
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            print("[GESTURE] ERROR: Cannot open webcam!")
            raise RuntimeError("Webcam not accessible")
        
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, GESTURE_CONFIG["camera_width"])
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, GESTURE_CONFIG["camera_height"])
        
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=GESTURE_CONFIG["max_hands"],
            min_detection_confidence=GESTURE_CONFIG["detection_confidence"],
            min_tracking_confidence=GESTURE_CONFIG["tracking_confidence"],
            model_complexity=1,
        )
        
        self.prev_gesture = None
        self.stable_count = 0
        self.gesture_frames_required = GESTURE_CONFIG["gesture_frames_required"]
        
        self.last_action_time = 0
        self.action_cooldown = GESTURE_CONFIG["action_cooldown"]
        self.system_paused = False
        self.last_pause_toggle_time = 0
        self.pause_cooldown = GESTURE_CONFIG["pause_cooldown"]
        
        self.running = True
        self.event_bus = None
        self.action_translator = None
        
        # Finger landmarks
        self.IDX = self.mp_hands.HandLandmark.INDEX_FINGER_TIP
        self.MID = self.mp_hands.HandLandmark.MIDDLE_FINGER_TIP
        self.RING = self.mp_hands.HandLandmark.RING_FINGER_TIP
        self.PIN = self.mp_hands.HandLandmark.PINKY_TIP
        self.TMB = self.mp_hands.HandLandmark.THUMB_TIP
        self.TMB_MCP = self.mp_hands.HandLandmark.THUMB_MCP
        self.IDX_MCP = self.mp_hands.HandLandmark.INDEX_FINGER_MCP
        
        print("[GESTURE] Initialized")
    
    @staticmethod
    def _dist(a, b):
        return math.hypot(a.x - b.x, a.y - b.y)
    
    def _finger_states(self, lm):
        """Detect which fingers are extended"""
        idx_up = lm[self.IDX].y < lm[self.mp_hands.HandLandmark.INDEX_FINGER_PIP].y
        mid_up = lm[self.MID].y < lm[self.mp_hands.HandLandmark.MIDDLE_FINGER_PIP].y
        ring_up = lm[self.RING].y < lm[self.mp_hands.HandLandmark.RING_FINGER_PIP].y
        pin_up = lm[self.PIN].y < lm[self.mp_hands.HandLandmark.PINKY_PIP].y
        
        thumb_dist = self._dist(lm[self.TMB], lm[self.TMB_MCP])
        tmb_extended = thumb_dist > 0.04
        
        return {
            'thumb': tmb_extended,
            'index': idx_up,
            'middle': mid_up,
            'ring': ring_up,
            'pinky': pin_up,
        }
    
    def _detect_gesture(self, lm):
        """Detect gesture from hand landmarks"""
        states = self._finger_states(lm)
        thumb = states['thumb']
        idx = states['index']
        mid = states['middle']
        ring = states['ring']
        pin = states['pinky']
        
        pinch_dist = self._dist(lm[self.TMB], lm[self.IDX])
        pinch = pinch_dist < 0.06
        
        all_down = (not thumb) and (not idx) and (not mid) and (not ring) and (not pin)
        
        # Priority ordering
        if pinch and mid:
            return 'ok'
        if pinch:
            return 'pinch'
        if idx and not mid and not ring and not pin:
            return 'move'
        if idx and mid and not ring and not pin:
            return 'peace'
        if idx and mid and ring and pin:
            return 'open_palm'
        if pin and (not idx) and (not mid) and (not ring):
            return 'pinky_up'
        if idx and mid and ring:
            return 'scroll_up'
        if mid and ring and pin:
            return 'scroll_down'
        if all_down:
            return 'fist'
        if thumb and (not idx) and (not mid) and (not ring) and (not pin):
            return 'thumbs_up'
        
        return 'neutral'
    
    def _move_cursor(self, frame_w, frame_h, idx_tip):
        """Move mouse cursor"""
        if idx_tip is None:
            return
        
        norm_x = max(0.0, min(1.0, idx_tip.x))
        norm_y = max(0.0, min(1.0, idx_tip.y))
        
        screen_w, screen_h = pyautogui.size()
        x = int(norm_x * screen_w)
        y = int(norm_y * screen_h)
        
        pyautogui.moveTo(x, y)
    
    def process_frame(self, frame):
        """Process and draw"""
        h, w, c = frame.shape
        frame = cv2.flip(frame, 1)
        
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.hands.process(rgb_frame)
        
        gesture_now = 'neutral'
        
        # HUD
        cv2.rectangle(frame, (0, 0), (480, 180), (0, 0, 0), -1)
        cv2.putText(frame, f"Gesture: {gesture_now}", (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.9, COLORS["secondary"], 2)
        
        if results.multi_hand_landmarks:
            lm = results.multi_hand_landmarks[0].landmark
            gesture_now = self._detect_gesture(lm)
            
            # Stability
            if gesture_now == self.prev_gesture:
                self.stable_count += 1
            else:
                self.stable_count = 1
            
            self.prev_gesture = gesture_now
            
            stable = self.stable_count >= self.gesture_frames_required
            
            # Move cursor
            self._move_cursor(w, h, lm[self.IDX])
            
            # Emit events for stable gestures
            t = time.time()
            
            if stable and gesture_now == 'pinky_up':
                if (t - self.last_pause_toggle_time) > self.pause_cooldown:
                    emit_event(EventType.GESTURE_PAUSE, "gesture", {}, priority=3)
                    self.last_pause_toggle_time = t
            
            if stable and not self.system_paused and gesture_now != 'neutral':
                if (t - self.last_action_time) > self.action_cooldown:
                    action = GESTURE_CONFIG["actions"].get(gesture_now)
                    if action:
                        emit_event(
                            EventType.GESTURE_DETECTED,
                            "gesture",
                            {"action": action, "details": gesture_now},
                            priority=2
                        )
                        print(f"[GESTURE] {gesture_now} -> {action}")
                        self.last_action_time = t
        
        # HUD update
        confidence = min(100, int((self.stable_count / self.gesture_frames_required) * 100))
        cv2.putText(frame, f"Confidence: {confidence}%", (10, 70),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, COLORS["primary"], 1)
        cv2.putText(frame, f"Status: {'PAUSED' if self.system_paused else 'ACTIVE'}", (10, 100),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, COLORS["error"] if self.system_paused else COLORS["success"], 1)
        cv2.putText(frame, "Q: Quit | P: Pause", (10, 170),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, COLORS["text"], 1)
        
        return frame
    
    def run(self):
        """Main loop"""
        print("[GESTURE] Starting controller...")
        
        while self.running:
            ret, frame = self.cap.read()
            if not ret:
                break
            
            frame = self.process_frame(frame)
            cv2.imshow("Hand Gestures", frame)
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                self.running = False
            elif key == ord('p'):
                self.system_paused = not self.system_paused
        
        self.cap.release()
        cv2.destroyAllWindows()
        print("[GESTURE] Stopped")


if __name__ == "__main__":
    controller = HandGestureController()
    controller.run()
