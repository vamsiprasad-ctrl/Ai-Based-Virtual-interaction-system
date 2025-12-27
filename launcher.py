# ============================================================
# MULTI-MODAL LAUNCHER - Shows all cameras and HUD together
# ============================================================
# Better visualization of all modalities with their windows

import cv2
import threading
import time
import os

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ['MEDIAPIPE_DISABLE_GPU'] = '1'

from config import SYSTEM_CONFIG, COLORS
from event_bus import get_event_bus, EventType
from action_mapper import get_mapper, ActionTranslator


class MultiModalLauncher:
    """Launches all modules with visible window arrangement"""
    
    def __init__(self):
        self.running = True
        self.start_time = time.time()
        
        self.event_bus = get_event_bus()
        self.action_mapper = get_mapper()
        
        self.stats = {
            "eye_actions": 0,
            "gesture_actions": 0,
            "voice_actions": 0,
            "total_actions": 0,
        }
        
        print("\n" + "="*70)
        print("MULTI-MODAL CONTROL SYSTEM - LAUNCHER")
        print("="*70 + "\n")
    
    def start_all_modules(self):
        """Start eye, gesture, and voice in separate threads"""
        
        def run_eye():
            try:
                from eye_module import IrisTracker
                tracker = IrisTracker()
                tracker.event_bus = self.event_bus
                tracker.running = True
                print("[EYE] Window should appear...")
                tracker.run()
            except Exception as e:
                print(f"[EYE] Error: {type(e).__name__}: {e}")
                import traceback
                traceback.print_exc()
        
        def run_gesture():
            try:
                from gesture_module import HandGestureController
                controller = HandGestureController()
                controller.event_bus = self.event_bus
                controller.running = True
                print("[GESTURE] Window should appear...")
                controller.run()
            except Exception as e:
                print(f"[GESTURE] Error: {type(e).__name__}: {e}")
                import traceback
                traceback.print_exc()
        
        def run_voice():
            try:
                from voice_module import VoiceController
                controller = VoiceController()
                controller.event_bus = self.event_bus
                print("[VOICE] Listening started...")
                controller.run()
            except Exception as e:
                print(f"[VOICE] Error: {type(e).__name__}: {e}")
        
        
        # Start all threads as non-daemon so windows display properly
        print("[*] Starting all modules...\n")
        
        eye_thread = threading.Thread(target=run_eye, name="EyeTracker", daemon=False)
        eye_thread.start()
        time.sleep(1)
        
        gesture_thread = threading.Thread(target=run_gesture, name="GestureController", daemon=False)
        gesture_thread.start()
        time.sleep(1)
        
        voice_thread = threading.Thread(target=run_voice, name="VoiceController", daemon=False)
        voice_thread.start()
        time.sleep(1)
        
        print("\n[*] All modules started!")
        print("[*] You should see:")
        print("    - Eye Tracking window (left)")
        print("    - Hand Gestures window (right)")
        print("    - Voice listening in terminal")
        print("\n[*] Press Q in any window to quit\n")
        
        return eye_thread, gesture_thread, voice_thread
    
    def run(self):
        """Launch all modules"""
        try:
            eye_thread, gesture_thread, voice_thread = self.start_all_modules()
            
            # Wait for all threads
            eye_thread.join(timeout=600)
            gesture_thread.join(timeout=600)
            voice_thread.join(timeout=600)
            
        except KeyboardInterrupt:
            print("\n[LAUNCHER] Shutting down...")
        except Exception as e:
            print(f"[LAUNCHER] Error: {e}")
        finally:
            cv2.destroyAllWindows()
            print("[LAUNCHER] Done!\n")


if __name__ == "__main__":
    launcher = MultiModalLauncher()
    launcher.run()
