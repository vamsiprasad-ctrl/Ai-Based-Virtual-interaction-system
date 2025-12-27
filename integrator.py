# ============================================================
# INTEGRATED MULTI-MODAL CONTROLLER (MAIN)
# ============================================================
# Orchestrates eye tracking, hand gestures, and voice commands
# All running in parallel with unified action dispatch

import os
import sys
import cv2
import threading
import time
from datetime import datetime

# Suppress logs
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ['MEDIAPIPE_DISABLE_GPU'] = '1'

from config import SYSTEM_CONFIG, COLORS, log_action
from event_bus import get_event_bus, EventType, emit_event
from action_mapper import get_mapper, ActionTranslator


class MultiModalController:
    """Main controller orchestrating all input modalities"""
    
    def __init__(self):
        self.running = True
        self.start_time = time.time()
        
        # Initialize systems
        self.event_bus = get_event_bus()
        self.action_mapper = get_mapper()
        
        # Module threads
        self.threads = {}
        
        # Statistics
        self.stats = {
            "eye_actions": 0,
            "gesture_actions": 0,
            "voice_actions": 0,
            "total_actions": 0,
            "errors": 0,
        }
        
        print("\n" + "="*70)
        print("MULTI-MODAL CONTROL SYSTEM - INTEGRATED")
        print("="*70)
        print("\n[INIT] Initializing components...\n")
        
        # Register action executor
        self.event_bus.register_action_callback("*", self._execute_unified_action)
    
    def _execute_unified_action(self, action_name: str, event):
        """Execute action from any modality"""
        source = event.source
        details = event.data.get("details", "")
        
        # Map to unified action if needed
        if source == "eye":
            action = ActionTranslator.from_gaze(details) or ActionTranslator.from_blink(details)
        elif source == "gesture":
            action = ActionTranslator.from_gesture(details)
        elif source == "voice":
            action = ActionTranslator.from_voice(details)
        else:
            action = action_name
        
        # Execute unified action
        if action:
            success = self.action_mapper.execute_action(action, source, details)
            if success:
                self.stats[f"{source}_actions"] += 1
                self.stats["total_actions"] += 1
    
    def start_eye_tracker(self):
        """Start eye tracking module in separate thread"""
        def run_eye():
            try:
                print("[EYE] Starting eye tracker...")
                from eye_module import IrisTracker
                
                tracker = IrisTracker()
                tracker.event_bus = self.event_bus
                tracker.action_translator = ActionTranslator
                tracker.run()
            except ImportError as e:
                print(f"[EYE] Import error (eye tracking disabled): {e}")
                self.stats["errors"] += 1
            except Exception as e:
                print(f"[EYE] Error: {e}")
                self.stats["errors"] += 1
        
        thread = threading.Thread(target=run_eye, name="EyeTracker", daemon=True)
        self.threads["eye"] = thread
        thread.start()
    
    def start_gesture_controller(self):
        """Start hand gesture module in separate thread"""
        def run_gesture():
            try:
                print("[GESTURE] Starting gesture controller...")
                from gesture_module import HandGestureController
                
                controller = HandGestureController()
                controller.event_bus = self.event_bus
                controller.action_translator = ActionTranslator
                controller.run()
            except ImportError as e:
                print(f"[GESTURE] Import error (gestures disabled): {e}")
                self.stats["errors"] += 1
            except Exception as e:
                print(f"[GESTURE] Error: {e}")
                self.stats["errors"] += 1
        
        thread = threading.Thread(target=run_gesture, name="GestureController", daemon=True)
        self.threads["gesture"] = thread
        thread.start()
    
    def start_voice_controller(self):
        """Start voice command module in separate thread"""
        def run_voice():
            try:
                print("[VOICE] Starting voice controller...")
                from voice_module import VoiceController
                
                controller = VoiceController()
                controller.event_bus = self.event_bus
                controller.action_translator = ActionTranslator
                controller.run()
            except ImportError as e:
                print(f"[VOICE] Import error (voice disabled): {e}")
                self.stats["errors"] += 1
            except Exception as e:
                print(f"[VOICE] Error: {e}")
                self.stats["errors"] += 1
        
        thread = threading.Thread(target=run_voice, name="VoiceController", daemon=True)
        self.threads["voice"] = thread
        thread.start()
    
    def display_unified_hud(self):
        """Display unified HUD showing all modalities"""
        if not SYSTEM_CONFIG["hud_enabled"]:
            return
        
        # Create HUD window
        hud_width = 800
        hud_height = 400
        hud = self._create_blank_frame(hud_width, hud_height)
        
        while self.running:
            try:
                hud = self._create_blank_frame(hud_width, hud_height)
                
                # Header
                self._put_text(hud, "MULTI-MODAL CONTROL SYSTEM", 20, 30, 1.2, COLORS["primary"])
                
                # Session info
                elapsed = time.time() - self.start_time
                self._put_text(hud, f"Session: {int(elapsed)}s", 20, 70, 0.7, COLORS["info"])
                
                # Statistics
                y = 100
                self._put_text(hud, "ACTIONS", 20, y, 0.9, COLORS["secondary"])
                y += 30
                self._put_text(hud, f"  Eye Tracking: {self.stats['eye_actions']}", 30, y, 0.6, COLORS["info"])
                y += 25
                self._put_text(hud, f"  Hand Gestures: {self.stats['gesture_actions']}", 30, y, 0.6, COLORS["info"])
                y += 25
                self._put_text(hud, f"  Voice Commands: {self.stats['voice_actions']}", 30, y, 0.6, COLORS["info"])
                y += 25
                self._put_text(hud, f"  TOTAL: {self.stats['total_actions']}", 30, y, 0.7, COLORS["success"])
                
                # Event bus status
                y = 100
                bus_status = self.event_bus.get_status()
                status_str = "PAUSED" if bus_status["system_paused"] else "ACTIVE"
                status_color = COLORS["error"] if bus_status["system_paused"] else COLORS["success"]
                self._put_text(hud, f"System: {status_str}", hud_width - 200, y, 0.7, status_color)
                
                # Active sources
                y += 30
                active = ", ".join(bus_status["active_sources"]) if bus_status["active_sources"] else "None"
                self._put_text(hud, f"Active: {active}", hud_width - 200, y, 0.6, COLORS["info"])
                
                # Instructions
                y = hud_height - 60
                self._put_text(hud, "Q: Quit | P: Pause/Resume | D: Debug", 20, y, 0.5, COLORS["text"])
                y += 30
                self._put_text(hud, "Eye-Tracking | Hand-Gestures | Voice-Control", 20, y, 0.5, COLORS["text"])
                
                cv2.imshow("Multi-Modal Control - HUD", hud)
                
                key = cv2.waitKey(100) & 0xFF
                if key == ord('q') or key == ord('Q'):
                    self.shutdown()
                    break
                elif key == ord('p') or key == ord('P'):
                    self.event_bus._toggle_system_pause()
                elif key == ord('d') or key == ord('D'):
                    SYSTEM_CONFIG["debug_mode"] = not SYSTEM_CONFIG["debug_mode"]
                    print(f"[DEBUG] Mode: {SYSTEM_CONFIG['debug_mode']}")
                
            except Exception as e:
                print(f"[HUD] Error: {e}")
                time.sleep(0.1)
    
    def _create_blank_frame(self, w: int, h: int):
        """Create blank frame for drawing"""
        import numpy as np
        return np.zeros((h, w, 3), dtype=np.uint8)
    
    def _put_text(self, frame, text: str, x: int, y: int, scale: float = 0.7, color: tuple = (255, 255, 255)):
        """Draw text on frame"""
        cv2.putText(frame, text, (x, y), cv2.FONT_HERSHEY_SIMPLEX, scale, color, 1)
    
    def run(self):
        """Start all modules and HUD"""
        try:
            # Start all modules
            print("\n[MAIN] Starting all modules...\n")
            self.start_eye_tracker()
            time.sleep(0.5)
            self.start_gesture_controller()
            time.sleep(0.5)
            self.start_voice_controller()
            time.sleep(0.5)
            
            print("\n[MAIN] All modules started. Displaying HUD...\n")
            print("="*70)
            print("SYSTEM RUNNING - Use unified HUD to monitor all inputs")
            print("="*70 + "\n")
            
            # Display HUD (blocking)
            self.display_unified_hud()
        
        except Exception as e:
            print(f"[MAIN] Fatal error: {e}")
            self.shutdown()
    
    def shutdown(self):
        """Graceful shutdown"""
        print("\n[MAIN] Shutting down...\n")
        self.running = False
        
        # Close all windows
        cv2.destroyAllWindows()
        
        # Wait for threads
        for name, thread in self.threads.items():
            print(f"[MAIN] Stopping {name}...")
            thread.join(timeout=2.0)
        
        # Shutdown event bus
        self.event_bus.shutdown()
        
        # Print final stats
        print("\n[MAIN] SESSION STATISTICS:")
        print(f"  Duration: {time.time() - self.start_time:.1f}s")
        print(f"  Total Actions: {self.stats['total_actions']}")
        print(f"  Eye Actions: {self.stats['eye_actions']}")
        print(f"  Gesture Actions: {self.stats['gesture_actions']}")
        print(f"  Voice Actions: {self.stats['voice_actions']}")
        print(f"  Errors: {self.stats['errors']}")
        print("\n[MAIN] Goodbye!\n")
        
        sys.exit(0)


if __name__ == "__main__":
    controller = MultiModalController()
    controller.run()
