import time
import math
import sys
import winsound
from threading import Thread

import cv2
import numpy as np
import pyautogui

try:
    import mediapipe as mp
except ImportError:
    print("mediapipe not installed. Please install requirements first.")
    sys.exit(1)


class HandGestureController:
    def __init__(self,
                 camera_index: int = 0,
                 max_hands: int = 1,
                 detection_confidence: float = 0.7,
                 tracking_confidence: float = 0.6,
                 move_smoothing: float = 0.8,
                 gesture_frames_required: int = 2):
        self.camera_index = camera_index
        self.move_smoothing = np.clip(move_smoothing, 0.0, 1.0)
        self.gesture_frames_required = max(1, int(gesture_frames_required))

        self.cap = cv2.VideoCapture(self.camera_index)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=max_hands,
            min_detection_confidence=detection_confidence,
            min_tracking_confidence=tracking_confidence,
            model_complexity=1,
        )
        self.mp_draw = mp.solutions.drawing_utils
        self.mp_styles = mp.solutions.drawing_styles

        screen_w, screen_h = pyautogui.size()
        self.screen_w = screen_w
        self.screen_h = screen_h

        self.prev_mouse_x = screen_w // 2
        self.prev_mouse_y = screen_h // 2
        
        # Calibration mode
        self.calibration_mode = False
        self.calibration_data = {
            'min_x': 0.0,
            'max_x': 1.0,
            'min_y': 0.0,
            'max_y': 1.0,
        }

        self.prev_gesture = None
        self.stable_count = 0
        
        # Gesture hints dictionary
        self.gesture_hints = {
            'move': 'Index Only ☝️',
            'pinch': 'Thumb + Index 👌',
            'ok': 'Thumb + Index (Middle Up) ✌️',
            'scroll_up': 'Index + Middle + Ring ☝️☝️☝️',
            'scroll_down': 'Middle + Ring + Pinky ✌️☝️',
            'peace': 'Index + Middle ✌️',
            'fist': 'All Fingers Down ✊',
            'thumbs_up': 'Thumb Up 👍',
            'thumbs_down': 'Thumb Down 👎',
            'open_palm': 'All Fingers Up 🖐️',
            'pinky_up': 'Pinky Only 🤙 (Toggle Pause)',
            'neutral': 'Waiting...'
        }
        
        # Sound feedback enabled
        self.sound_enabled = True
        
        # Debug logging (set True to print finger states every frame)
        self.debug_logging = False
        
        # Test mode (disable actual actions, only detect gestures)
        self.test_mode = False
        
        # System pause state (safety lock to prevent accidental actions)
        self.system_paused = False
        self.last_pause_toggle_time = 0.0
        self.pause_toggle_cooldown = 0.8  # Delay in seconds between pause toggles
        
        # Dynamic sensitivity control
        self.sensitivity_mode = 'normal'  # 'slow', 'normal', 'fast'
        self.last_sensitivity_change = 0.0
        self.sensitivity_hold_time = 1.5  # seconds to hold for mode switch

        # Pinch/drag state machine
        self.is_pinching = False
        self.pinch_start_time = 0.0
        self.last_pinch_end_time = 0.0
        self.is_dragging = False
        self.double_click_window = 0.35
        self.drag_hold_threshold = 0.5

        # Action cooldowns and repeat pacing
        self.last_action_time = 0.0
        self.action_cooldown = 0.3  # Reduced from 0.6 for smoother copy->paste flow
        self.scroll_interval_frames = 4
        self.frame_index = 0

        # Sequence detection (peace -> fist)
        self.last_stable_gesture = None
        self.last_stable_time = 0.0
        self.sequence_window = 1.2
        self.prev_stable_gesture = None
        self.prev_stable_time = 0.0

        # Named indices for landmarks
        self.IDX = self.mp_hands.HandLandmark.INDEX_FINGER_TIP
        self.IDX_PIP = self.mp_hands.HandLandmark.INDEX_FINGER_PIP
        self.MID = self.mp_hands.HandLandmark.MIDDLE_FINGER_TIP
        self.MID_PIP = self.mp_hands.HandLandmark.MIDDLE_FINGER_PIP
        self.RING = self.mp_hands.HandLandmark.RING_FINGER_TIP
        self.RING_PIP = self.mp_hands.HandLandmark.RING_FINGER_PIP
        self.PIN = self.mp_hands.HandLandmark.PINKY_TIP
        self.PIN_PIP = self.mp_hands.HandLandmark.PINKY_PIP
        self.TMB = self.mp_hands.HandLandmark.THUMB_TIP
        self.TMB_IP = self.mp_hands.HandLandmark.THUMB_IP
        self.TMB_MCP = self.mp_hands.HandLandmark.THUMB_MCP
        self.WRIST = self.mp_hands.HandLandmark.WRIST
        self.IDX_MCP = self.mp_hands.HandLandmark.INDEX_FINGER_MCP
        self.MID_MCP = self.mp_hands.HandLandmark.MIDDLE_FINGER_MCP
        self.RING_MCP = self.mp_hands.HandLandmark.RING_FINGER_MCP
        self.PIN_MCP = self.mp_hands.HandLandmark.PINKY_MCP

    @staticmethod
    def _dist(a, b):
        return math.hypot(a.x - b.x, a.y - b.y)

    def _finger_states(self, lm, handedness_label: str):
        # Simplified and more reliable finger detection
        # Use PIP joint as main reference - easier to detect extended fingers
        
        # Fingers are "up" if tip is above PIP joint
        idx_up = lm[self.IDX].y < lm[self.IDX_PIP].y
        mid_up = lm[self.MID].y < lm[self.MID_PIP].y
        ring_up = lm[self.RING].y < lm[self.RING_PIP].y
        pin_up = lm[self.PIN].y < lm[self.PIN_PIP].y

        # Simplified thumb detection using distance from palm center
        thumb_dist = self._dist(lm[self.TMB], lm[self.TMB_MCP])
        tmb_extended = thumb_dist > 0.04
        
        # Thumb orientation for thumbs up/down gestures (using INDEX_MCP for better accuracy)
        tmb_tip = lm[self.TMB]
        idx_mcp = lm[self.IDX_MCP]
        thumb_up_orientation = tmb_tip.y < idx_mcp.y - 0.05
        thumb_down_orientation = tmb_tip.y > idx_mcp.y + 0.05

        states = {
            'thumb': tmb_extended,
            'index': idx_up,
            'middle': mid_up,
            'ring': ring_up,
            'pinky': pin_up,
            'thumb_up_orientation': thumb_up_orientation,
            'thumb_down_orientation': thumb_down_orientation,
        }
        return states

    def _detect_gesture(self, lm, handedness_label: str):
        states = self._finger_states(lm, handedness_label)
        thumb = states['thumb']
        idx = states['index']
        mid = states['middle']
        ring = states['ring']
        pin = states['pinky']

        # Enhanced distance-based detection for pinch
        pinch_dist = self._dist(lm[self.TMB], lm[self.IDX])
        pinch = pinch_dist < 0.06  # Slightly increased threshold for better detection
        
        # Distance between middle and ring for better scroll detection
        mid_ring_dist = self._dist(lm[self.MID], lm[self.RING])
        fingers_together = mid_ring_dist < 0.05

        all_up = thumb and idx and mid and ring and pin
        all_down = (not thumb) and (not idx) and (not mid) and (not ring) and (not pin)

        # Priority ordering to avoid conflicts (requested order)
        # 1) Pinch & OK
        if pinch and mid:
            return 'ok'
        if pinch:
            return 'pinch'

        # 2) Cursor move (index priority)
        if idx and not mid and not ring and not pin:
            return 'move'

        # 3) Peace
        if idx and mid and not ring and not pin:
            return 'peace'

        # 4) Open palm (all fingers up - must check BEFORE scroll)
        if idx and mid and ring and pin:
            return 'open_palm'

        # 5) Pinky only (check BEFORE scroll to avoid conflicts) - ignore thumb
        if pin and (not idx) and (not mid) and (not ring):
            return 'pinky_up'

        # 6) Scroll (check AFTER pinky to avoid conflicts)
        if idx and mid and ring:
            return 'scroll_up'
        if mid and ring and pin:
            return 'scroll_down'

        # Fist
        if all_down:
            return 'fist'

        # Thumbs up / down (only thumb extended, orientation determines up/down)
        if thumb and (not idx) and (not mid) and (not ring) and (not pin):
            if states['thumb_up_orientation']:
                return 'thumbs_up'
            if states['thumb_down_orientation']:
                return 'thumbs_down'
            # ambiguous thumb-only, no orientation -> no-op
            return 'neutral'

        return 'neutral'

    def _move_cursor(self, frame_w, frame_h, idx_tip):
        # Define active tracking area with relaxed margins for better coverage
        margin_x = 0.05  # Reduced from 0.1
        margin_y = 0.1   # Reduced from 0.15
        
        # Normalize to active area with amplification
        norm_x = (idx_tip.x - margin_x) / (1.0 - 2 * margin_x)
        norm_y = (idx_tip.y - margin_y) / (1.0 - 2 * margin_y)
        
        # Clamp to 0-1 range
        norm_x = max(0.0, min(1.0, norm_x))
        norm_y = max(0.0, min(1.0, norm_y))
        
        # Map to screen coordinates
        x = int(norm_x * self.screen_w)
        y = int(norm_y * self.screen_h)
        
        # Clamp to screen bounds
        x = max(0, min(x, self.screen_w - 1))
        y = max(0, min(y, self.screen_h - 1))
        
        sx = int(self.prev_mouse_x + (x - self.prev_mouse_x) * self.move_smoothing)
        sy = int(self.prev_mouse_y + (y - self.prev_mouse_y) * self.move_smoothing)
        self.prev_mouse_x, self.prev_mouse_y = sx, sy
        if self.is_dragging:
            pyautogui.moveTo(sx, sy)
        else:
            pyautogui.moveTo(sx, sy)

    def _handle_pinch_state(self, gesture_now, idx_tip):
        t = time.time()
        if gesture_now == 'pinch':
            if not self.is_pinching:
                # Pinch started
                self.is_pinching = True
                self.pinch_start_time = t
                # Double click detection: if recent pinch ended
                if (t - self.last_pinch_end_time) <= self.double_click_window:
                    if not self.test_mode:
                        pyautogui.doubleClick()
                    else:
                        print("[TEST] Action would be: doubleClick")
                    self.last_action_time = t
            else:
                # If held long enough and not yet dragging -> start drag
                if (not self.is_dragging) and (t - self.pinch_start_time >= self.drag_hold_threshold):
                    if not self.test_mode:
                        pyautogui.mouseDown()
                    else:
                        print("[TEST] Action would be: mouseDown (drag start)")
                    self.is_dragging = True
        else:
            # Pinch released
            if self.is_pinching:
                held_time = time.time() - self.pinch_start_time
                if self.is_dragging:
                    if not self.test_mode:
                        pyautogui.mouseUp()
                    else:
                        print("[TEST] Action would be: mouseUp (drag end)")
                    self.is_dragging = False
                else:
                    # If quick pinch (no drag) and not consumed by double click -> left click
                    if held_time < self.drag_hold_threshold:
                        # Avoid firing if a double click just happened in the same window
                        if (time.time() - self.last_action_time) > 0.1:
                            if not self.test_mode:
                                pyautogui.click()
                            else:
                                print("[TEST] Action would be: click")
                            self.last_action_time = time.time()
                self.is_pinching = False
                self.last_pinch_end_time = time.time()

    def _play_sound(self, frequency: int = 1000, duration: int = 100):
        """Play sound feedback in background thread"""
        if not self.sound_enabled:
            return
        def play():
            try:
                winsound.Beep(frequency, duration)
            except:
                pass
        Thread(target=play, daemon=True).start()

    def _trigger_once(self, action: str):
        t = time.time()
        if (t - self.last_action_time) < self.action_cooldown:
            return
        
        # In test mode, skip actual actions but still play feedback
        if self.test_mode:
            self._play_sound(600, 100)  # Test mode beep
            print(f"[TEST] Action would be: {action}")
            self.last_action_time = t
            return
        
        # Sound map: action -> (frequency, duration)
        sound_map = {
            'right_click': (800, 100),
            'enter': (1200, 80),
            'escape': (600, 80),
            'copy': (1000, 100),
            'paste': (1100, 100),
            'close_tab': (900, 100),
            'show_desktop': (1400, 150),
            'backspace': (700, 100),
        }
        
        if action == 'right_click':
            pyautogui.click(button='right')
        elif action == 'enter':
            pyautogui.press('enter')
        elif action == 'escape':
            pyautogui.press('esc')
        elif action == 'backspace':
            pyautogui.press('backspace')
        elif action == 'copy':
            pyautogui.hotkey('ctrl', 'c')
        elif action == 'paste':
            pyautogui.hotkey('ctrl', 'v')
        elif action == 'close_tab':
            pyautogui.hotkey('ctrl', 'w')
        elif action == 'show_desktop':
            pyautogui.hotkey('winleft', 'd')
        
        # Play sound feedback
        if action in sound_map:
            freq, dur = sound_map[action]
            self._play_sound(freq, dur)
        
        self.last_action_time = t

    def _calibrate_cursor(self, idx_tip):
        """Update calibration bounds during calibration mode"""
        if not self.calibration_mode or idx_tip is None:
            return
        
        # Update min/max bounds
        self.calibration_data['min_x'] = min(self.calibration_data['min_x'], idx_tip.x)
        self.calibration_data['max_x'] = max(self.calibration_data['max_x'], idx_tip.x)
        self.calibration_data['min_y'] = min(self.calibration_data['min_y'], idx_tip.y)
        self.calibration_data['max_y'] = max(self.calibration_data['max_y'], idx_tip.y)

    def _move_cursor_calibrated(self, frame_w, frame_h, idx_tip):
        """Move cursor using calibration bounds"""
        if idx_tip is None:
            return
        
        # Get calibration data
        min_x = self.calibration_data.get('min_x', 0.0)
        max_x = self.calibration_data.get('max_x', 1.0)
        min_y = self.calibration_data.get('min_y', 0.0)
        max_y = self.calibration_data.get('max_y', 1.0)
        
        # Normalize using calibration data
        range_x = max_x - min_x if max_x > min_x else 1.0
        range_y = max_y - min_y if max_y > min_y else 1.0
        
        norm_x = (idx_tip.x - min_x) / range_x
        norm_y = (idx_tip.y - min_y) / range_y
        
        # Clamp to 0-1
        norm_x = max(0.0, min(1.0, norm_x))
        norm_y = max(0.0, min(1.0, norm_y))
        
        # Map to screen
        x = int(norm_x * self.screen_w)
        y = int(norm_y * self.screen_h)
        
        x = max(0, min(x, self.screen_w - 1))
        y = max(0, min(y, self.screen_h - 1))
        
        sx = int(self.prev_mouse_x + (x - self.prev_mouse_x) * self.move_smoothing)
        sy = int(self.prev_mouse_y + (y - self.prev_mouse_y) * self.move_smoothing)
        self.prev_mouse_x, self.prev_mouse_y = sx, sy
        
        if self.is_dragging:
            pyautogui.moveTo(sx, sy)
        else:
            pyautogui.moveTo(sx, sy)

    def run(self):
        if not self.cap.isOpened():
            print('Could not open webcam. Exiting.')
            return

        try:
            while True:
                self.frame_index += 1
                success, img = self.cap.read()
                if not success:
                    continue

                # Mirror for natural interaction
                img = cv2.flip(img, 1)
                img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                res = self.hands.process(img_rgb)

                gesture_now = 'neutral'
                idx_tip = None
                handed_label = 'Right'

                if res.multi_hand_landmarks:
                    # Use the first hand detected
                    lm = res.multi_hand_landmarks[0].landmark
                    # Handedness
                    if res.multi_handedness:
                        handed_label = res.multi_handedness[0].classification[0].label

                    gesture_now = self._detect_gesture(lm, handed_label)
                    idx_tip = lm[self.IDX]
                    states = self._finger_states(lm, handed_label)  # Get finger states for direct control
                    
                    # Step 4: DEBUG - print gesture and finger states (enable via self.debug_logging)
                    if self.debug_logging:
                        print(f"Gesture: {gesture_now} | Index:{states['index']} Mid:{states['middle']} Ring:{states['ring']} Pin:{states['pinky']} Thumb:{states['thumb']} | Conf:{self.stable_count}/{self.gesture_frames_required}")
                    
                    # NOTE: Sensitivity control removed to avoid conflicts with paste action
                    # Fist gesture is now dedicated to paste only (short hold)
                    # Sensitivity can be controlled via keyboard in future if needed
                    
                    # Calibration data collection
                    if self.calibration_mode:
                        self._calibrate_cursor(idx_tip)

                    # Draw landmarks for debugging
                    self.mp_draw.draw_landmarks(
                        img,
                        res.multi_hand_landmarks[0],
                        self.mp_hands.HAND_CONNECTIONS,
                        self.mp_styles.get_default_hand_landmarks_style(),
                        self.mp_styles.get_default_hand_connections_style(),
                    )

                # Gesture stability logic
                if gesture_now == self.prev_gesture:
                    self.stable_count += 1
                else:
                    self.stable_count = 1
                    self.prev_gesture = gesture_now

                stable = self.stable_count >= self.gesture_frames_required

                # Cursor movement: direct index detection (most reliable)
                if res.multi_hand_landmarks:
                    states = self._finger_states(res.multi_hand_landmarks[0].landmark, handed_label)
                    if states['index'] and idx_tip is not None:
                        if self.calibration_mode:
                            self._move_cursor_calibrated(img.shape[1], img.shape[0], idx_tip)
                        else:
                            self._move_cursor(img.shape[1], img.shape[0], idx_tip)

                # Pinch/drag state handling always runs so drag can persist while stqable
                self._handle_pinch_state(gesture_now, idx_tip)

                # Pinky gesture always works for pause/resume (outside of pause check)
                if stable and gesture_now == 'pinky_up':
                    # Toggle system pause (safety lock) - always accessible
                    t = time.time()
                    if (t - self.last_pause_toggle_time) >= self.pause_toggle_cooldown:
                        self.system_paused = not self.system_paused
                        status = "PAUSED" if self.system_paused else "ACTIVE"
                        print(f"System {status}")
                        self._play_sound(1300 if self.system_paused else 900, 200)
                        self.last_pause_toggle_time = t

                # One-shot actions when stable (blocked when paused)
                if stable and not self.system_paused:
                    # Record last and previous stable gestures for sequences
                    if gesture_now != self.last_stable_gesture:
                        self.prev_stable_gesture = self.last_stable_gesture
                        self.prev_stable_time = self.last_stable_time
                        self.last_stable_gesture = gesture_now
                        self.last_stable_time = time.time()

                    if gesture_now == 'ok':
                        self._trigger_once('right_click')
                    elif gesture_now == 'scroll_up':
                        if self.frame_index % self.scroll_interval_frames == 0:
                            if not self.test_mode:
                                scroll_amt = int(120 * self.move_smoothing)
                                pyautogui.scroll(scroll_amt)
                            else:
                                print("[TEST] Action would be: scroll_up")
                    elif gesture_now == 'scroll_down':
                        if self.frame_index % self.scroll_interval_frames == 0:
                            if not self.test_mode:
                                scroll_amt = int(120 * self.move_smoothing)
                                pyautogui.scroll(-scroll_amt)
                            else:
                                print("[TEST] Action would be: scroll_down")
                    elif gesture_now == 'thumbs_up':
                        self._trigger_once('enter')
                    elif gesture_now == 'thumbs_down':
                        self._trigger_once('escape')
                    elif gesture_now == 'peace':
                        self._trigger_once('copy')
                    elif gesture_now == 'fist':
                        # Sequence check: previous stable was peace within window -> close tab; else paste
                        if self.prev_stable_gesture == 'peace' and (time.time() - self.prev_stable_time) <= self.sequence_window:
                            self._trigger_once('close_tab')
                        else:
                            # Allow paste even if recent copy - bypass cooldown for smooth workflow
                            if self.prev_stable_gesture == 'peace':
                                self.last_action_time = 0  # Reset to allow paste immediately after copy
                            self._trigger_once('paste')
                    elif gesture_now == 'open_palm':
                        self._trigger_once('show_desktop')

                # Enhanced HUD overlay with gesture guide and confidence bar
                h, w = img.shape[:2]
                
                # Background panel
                panel_height = 200 if self.calibration_mode else 160
                cv2.rectangle(img, (0, 0), (480, panel_height), (0, 0, 0), -1)
                
                # Gesture name and hint
                cv2.putText(img, f'Gesture: {gesture_now}', (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 255), 2)
                hint = self.gesture_hints.get(gesture_now, 'Waiting...')
                cv2.putText(img, hint, (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (100, 200, 100), 1)
                
                # Sensitivity mode indicator
                sensitivity_colors = {
                    'slow': (100, 100, 255),    # Blue - slow
                    'normal': (100, 200, 100),  # Green - normal
                    'fast': (255, 100, 100),    # Red - fast
                }
                sens_color = sensitivity_colors.get(self.sensitivity_mode, (100, 200, 100))
                cv2.putText(img, f'Sensitivity: {self.sensitivity_mode.upper()}', (10, 90), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, sens_color, 2)
                
                # Confidence bar
                confidence = min(100, int((self.stable_count / self.gesture_frames_required) * 100))
                bar_width = 200
                bar_height = 15
                filled = int(bar_width * confidence / 100)
                cv2.rectangle(img, (10, 80), (10 + bar_width, 80 + bar_height), (100, 100, 100), 1)
                cv2.rectangle(img, (10, 80), (10 + filled, 80 + bar_height), (0, 255, 100), -1)
                cv2.putText(img, f'{confidence}%', (220, 92), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
                
                # Calibration mode info
                if self.calibration_mode:
                    cv2.putText(img, 'CALIBRATION MODE', (10, 125), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 165, 255), 2)
                    cv2.putText(img, 'Move finger to corners. Press C to finish.', (10, 155), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 200, 255), 1)
                    # Draw calibration bounds
                    cv2.rectangle(img, 
                        (int(self.calibration_data['min_x'] * w), int(self.calibration_data['min_y'] * h)),
                        (int(self.calibration_data['max_x'] * w), int(self.calibration_data['max_y'] * h)),
                        (0, 165, 255), 2)
                
                # Help text
                cv2.putText(img, 'Q: Quit | C: Calibrate | T: Test Mode', (10, panel_height - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
                
                # System pause indicator
                if self.system_paused:
                    cv2.rectangle(img, (0, panel_height), (480, panel_height + 50), (0, 100, 200), -1)
                    cv2.putText(img, 'SYSTEM PAUSED ✋', (10, panel_height + 35), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 2)
                
                
                # Test mode indicator
                pause_offset = 50 if self.system_paused else 0
                if self.test_mode:
                    cv2.rectangle(img, (0, panel_height + pause_offset), (480, panel_height + pause_offset + 40), (0, 0, 255), -1)
                    cv2.putText(img, 'TEST MODE - Actions Disabled', (10, panel_height + pause_offset + 28), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)

                cv2.imshow('Hand Gesture Control - Press Q to Quit', img)
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    break
                elif key == ord('c'):
                    # Toggle calibration mode
                    self.calibration_mode = not self.calibration_mode
                    if self.calibration_mode:
                        print("Calibration mode STARTED - Move your finger to screen corners")
                        self.calibration_data = {
                            'min_x': 1.0,
                            'max_x': 0.0,
                            'min_y': 1.0,
                            'max_y': 0.0,
                        }
                        self._play_sound(1500, 200)  # Beep to confirm start
                    else:
                        print("Calibration mode FINISHED")
                        print(f"Calibration data: {self.calibration_data}")
                        self._play_sound(1000, 100)  # Beep to confirm end
                elif key == ord('t'):
                    # Toggle test mode
                    self.test_mode = not self.test_mode
                    status = "ENABLED" if self.test_mode else "DISABLED"
                    print(f"Test mode {status}")
                    self._play_sound(1100, 150)

        finally:
            if self.is_dragging:
                pyautogui.mouseUp()
            self.cap.release()
            cv2.destroyAllWindows()


def main():
    controller = HandGestureController(
        camera_index=0,
        max_hands=1,
        detection_confidence=0.7,
        tracking_confidence=0.6,
        move_smoothing=0.8,
        gesture_frames_required=2,
    )
    controller.run()


if __name__ == '__main__':
    main()
