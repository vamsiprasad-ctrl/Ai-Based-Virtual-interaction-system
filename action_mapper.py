# ============================================================
# ACTION MAPPER - Unified Action Dispatcher
# ============================================================
# Executes actions from any modality using consistent interface
# Prevents duplicate actions and enforces cooldowns

import pyautogui
import time
from typing import Dict, Callable
from event_bus import EventType
from config import (
    ACTION_MAPPINGS, 
    SYSTEM_CONFIG, 
    log_action,
    COLORS
)


class ActionMapper:
    """Maps events to system actions"""
    
    def __init__(self):
        self.last_action_time = 0
        self.action_history = []
        self.action_callbacks = {}
        self.sound_enabled = True
        
        # Create action executors
        self.executors = {
            "hotkey": self._execute_hotkey,
            "press": self._execute_press,
            "click": self._execute_click,
            "custom": self._execute_custom,
        }
        
        print("[ActionMapper] Initialized")
    
    def register_action_handler(self, action_name: str, callback: Callable):
        """Register custom action handler"""
        self.action_callbacks[action_name] = callback
    
    def execute_action(self, action_name: str, source: str, details: str = None) -> bool:
        """
        Execute an action (main entry point)
        
        Args:
            action_name: Name of action to execute
            source: Source modality (eye, gesture, voice)
            details: Additional details for logging
        
        Returns:
            True if action executed, False if blocked
        """
        
        # Check cooldown
        if not self._check_cooldown():
            if SYSTEM_CONFIG["debug_mode"]:
                print(f"[ActionMapper] Action blocked by cooldown: {action_name}")
            return False
        
        # Get action command
        if action_name in self.action_callbacks:
            # Custom action
            try:
                self.action_callbacks[action_name](action_name, source, details)
                self._record_action(action_name, source, details)
                log_action(action_name, source, details)
                return True
            except Exception as e:
                print(f"[ActionMapper] Custom action error: {e}")
                return False
        
        # Standard action
        if action_name not in ACTION_MAPPINGS:
            print(f"[ActionMapper] Unknown action: {action_name}")
            return False
        
        action_type, action_data = ACTION_MAPPINGS[action_name]
        
        # Execute
        try:
            executor = self.executors.get(action_type)
            if executor:
                executor(action_data)
                self.last_action_time = time.time()
                self._record_action(action_name, source, details)
                log_action(action_name, source, details)
                return True
            else:
                print(f"[ActionMapper] Unknown action type: {action_type}")
                return False
        
        except Exception as e:
            print(f"[ActionMapper] Execution error: {e}")
            return False
    
    def _check_cooldown(self) -> bool:
        """Check if enough time has passed since last action"""
        elapsed = time.time() - self.last_action_time
        return elapsed >= 0.2  # 200ms minimum between actions
    
    def _execute_hotkey(self, keys: tuple):
        """Execute keyboard hotkey"""
        try:
            pyautogui.hotkey(*keys)
            time.sleep(0.05)
        except Exception as e:
            print(f"[ActionMapper] Hotkey error: {e}")
    
    def _execute_press(self, key: str):
        """Press single key"""
        try:
            pyautogui.press(key)
            time.sleep(0.05)
        except Exception as e:
            print(f"[ActionMapper] Press error: {e}")
    
    def _execute_click(self, button: str = "left"):
        """Mouse click"""
        try:
            pyautogui.click(button=button)
            time.sleep(0.05)
        except Exception as e:
            print(f"[ActionMapper] Click error: {e}")
    
    def _execute_custom(self, callback: Callable):
        """Execute custom callback"""
        try:
            callback()
            time.sleep(0.05)
        except Exception as e:
            print(f"[ActionMapper] Custom execution error: {e}")
    
    def _record_action(self, action_name: str, source: str, details: str = None):
        """Record action in history"""
        self.action_history.append({
            "action": action_name,
            "source": source,
            "time": time.time(),
            "details": details
        })
        
        # Keep last 100 actions
        if len(self.action_history) > 100:
            self.action_history.pop(0)
    
    def get_action_history(self, limit: int = 20) -> list:
        """Get recent action history"""
        return self.action_history[-limit:]
    
    def get_action_stats(self) -> Dict:
        """Get action execution statistics"""
        if not self.action_history:
            return {}
        
        stats = {}
        for record in self.action_history:
            action = record["action"]
            source = record["source"]
            key = f"{action} ({source})"
            stats[key] = stats.get(key, 0) + 1
        
        return stats


# Global action mapper instance
_mapper = None


def get_mapper() -> ActionMapper:
    """Get or create global action mapper"""
    global _mapper
    if _mapper is None:
        _mapper = ActionMapper()
    return _mapper


def execute_action(action_name: str, source: str, details: str = None) -> bool:
    """Convenience function"""
    return get_mapper().execute_action(action_name, source, details)


# ============================================================
# ACTION TRANSLATOR - Convert modality-specific actions to unified actions
# ============================================================

class ActionTranslator:
    """Translates modality-specific actions to unified action names"""
    
    @staticmethod
    def from_gaze(gaze_direction: str) -> str:
        """Translate gaze direction to action"""
        from config import EYE_CONFIG
        
        gaze_key = f"{gaze_direction.lower()}_gaze"
        return EYE_CONFIG["actions"].get(gaze_key)
    
    @staticmethod
    def from_blink(blink_type: str) -> str:
        """Translate blink type to action"""
        from config import EYE_CONFIG
        
        return EYE_CONFIG["actions"].get(blink_type)
    
    @staticmethod
    def from_gesture(gesture_name: str) -> str:
        """Translate gesture to action"""
        from config import GESTURE_CONFIG
        
        return GESTURE_CONFIG["actions"].get(gesture_name)
    
    @staticmethod
    def from_voice(voice_command: str) -> str:
        """Translate voice command to action"""
        from config import VOICE_CONFIG
        
        return VOICE_CONFIG["actions"].get(voice_command)
