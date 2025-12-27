# ============================================================
# UNIFIED CONFIGURATION - Multi-Modal Control System
# ============================================================
# Central configuration for all input modalities
# Shared action mappings, thresholds, and system parameters

# ============================================================
# ACTION MAPPINGS - UNIFIED ACROSS ALL MODALITIES
# ============================================================

# Actions that can be triggered by any modality
ACTION_MAPPINGS = {
    # Navigation
    "next_tab": ("hotkey", ("ctrl", "tab")),
    "previous_tab": ("hotkey", ("ctrl", "shift", "tab")),
    "close_tab": ("hotkey", ("ctrl", "w")),
    "new_tab": ("hotkey", ("ctrl", "t")),
    
    # Window Management
    "close_window": ("hotkey", ("alt", "f4")),
    "minimize": ("hotkey", ("winleft", "down")),
    "maximize": ("hotkey", ("winleft", "up")),
    "show_desktop": ("hotkey", ("winleft", "d")),
    
    # Text Editing
    "copy": ("hotkey", ("ctrl", "c")),
    "paste": ("hotkey", ("ctrl", "v")),
    "cut": ("hotkey", ("ctrl", "x")),
    "select_all": ("hotkey", ("ctrl", "a")),
    "undo": ("hotkey", ("ctrl", "z")),
    "redo": ("hotkey", ("ctrl", "shift", "z")),
    
    # Media Control
    "play_pause": ("press", "playpause"),
    "volume_up": ("press", "volumeup"),
    "volume_down": ("press", "volumedown"),
    "mute": ("press", "volumemute"),
    
    # System
    "screenshot": ("press", "printscreen"),
    "escape": ("press", "esc"),
    "enter": ("press", "enter"),
    "backspace": ("press", "backspace"),
}

# ============================================================
# EYE TRACKING CONFIGURATION
# ============================================================

EYE_CONFIG = {
    "camera_width": 1280,
    "camera_height": 720,
    "camera_fps": 30,
    
    # Gaze detection
    "gaze_hold_time": 0.8,  # seconds to hold gaze before action
    "gaze_cooldown": 1.2,  # cooldown between gaze actions
    "gaze_thresholds": {
        "left": 0.40,    # iris_ratio < 0.40
        "right": 0.60,   # iris_ratio > 0.60
    },
    
    # Blink detection
    "blink_threshold": 0.25,  # EAR threshold
    "double_blink_window": 0.5,  # seconds
    "triple_blink_window": 0.7,  # seconds
    
    # Actions
    "actions": {
        "left_gaze": "previous_tab",
        "right_gaze": "next_tab",
        "double_blink": "next_tab",
        "triple_blink": "show_desktop",
    },
    
    # Display
    "display_width": 1280,
    "display_height": 800,
    "iris_radius": 12,
    "trail_length": 15,
}

# ============================================================
# HAND GESTURE CONFIGURATION
# ============================================================

GESTURE_CONFIG = {
    "camera_width": 1280,
    "camera_height": 720,
    
    # Detection
    "max_hands": 1,
    "detection_confidence": 0.7,
    "tracking_confidence": 0.6,
    "gesture_frames_required": 2,
    
    # Movement
    "move_smoothing": 0.8,
    "drag_hold_threshold": 0.5,
    "double_click_window": 0.35,
    
    # Cooldown
    "action_cooldown": 0.3,
    "pause_cooldown": 0.8,
    
    # Actions mapped to gestures
    "actions": {
        "pinch": "copy",
        "peace": "paste",
        "scroll_up": "next_tab",
        "scroll_down": "previous_tab",
        "ok": "enter",
        "fist": "escape",
        "thumbs_up": "play_pause",
        "thumbs_down": "volume_down",
        "open_palm": "show_desktop",
        "pinky_up": "pause_toggle",  # Special: toggles system pause
    },
    
    # Sound feedback
    "sound_enabled": True,
}

# ============================================================
# VOICE COMMAND CONFIGURATION
# ============================================================

VOICE_CONFIG = {
    "listen_timeout": 4,  # seconds
    "cooldown": 1.0,  # cooldown between commands
    "use_gemini": True,  # Use Gemini for intent parsing
    
    # Actions mapped to voice commands
    "actions": {
        "next_tab": "next_tab",
        "previous_tab": "previous_tab",
        "close_tab": "close_tab",
        "new_tab": "new_tab",
        "copy": "copy",
        "paste": "paste",
        "undo": "undo",
        "redo": "redo",
        "play": "play_pause",
        "pause": "play_pause",
        "mute": "mute",
        "volume_up": "volume_up",
        "volume_down": "volume_down",
        "screenshot": "screenshot",
    },
    
    # TTS settings
    "speech_rate": 170,
    "engine": "pyttsx3",
}

# ============================================================
# SYSTEM CONFIGURATION
# ============================================================

SYSTEM_CONFIG = {
    # Input prioritization (higher = higher priority)
    "input_priority": {
        "voice": 3,        # Highest priority
        "gesture": 2,      # Medium priority
        "eye": 1,          # Lowest priority
    },
    
    # Conflict resolution
    "allow_simultaneous": {
        "voice_eye": False,       # Voice cancels eye tracking
        "voice_gesture": False,   # Voice cancels gesture
        "eye_gesture": True,      # Eye and gesture can work together
    },
    
    # Display
    "hud_enabled": True,
    "show_metrics": True,
    "show_fps": False,
    
    # Logging
    "debug_mode": False,
    "log_actions": True,
    "log_file": "action_log.txt",
    
    # Threading
    "thread_timeout": 1.0,
    "event_queue_size": 100,
}

# ============================================================
# COLOR SCHEME (for HUD)
# ============================================================

COLORS = {
    "primary": (0, 255, 0),        # Bright green
    "secondary": (0, 255, 255),    # Cyan
    "accent": (0, 165, 255),       # Orange
    "error": (0, 0, 255),          # Red
    "warning": (0, 255, 100),      # Green-yellow
    "success": (0, 255, 0),        # Green
    "info": (100, 200, 255),       # Light blue
    "background": (20, 20, 20),    # Dark gray
    "text": (255, 255, 255),       # White
}

# ============================================================
# HELPER FUNCTIONS
# ============================================================

def get_action_command(action_name):
    """Get the pyautogui command for an action"""
    if action_name in ACTION_MAPPINGS:
        return ACTION_MAPPINGS[action_name]
    return None

def get_action_from_gesture(gesture):
    """Get action name from gesture"""
    return GESTURE_CONFIG["actions"].get(gesture)

def get_action_from_gaze(gaze_direction):
    """Get action name from gaze direction"""
    return EYE_CONFIG["actions"].get(gaze_direction)

def get_action_from_voice(voice_command):
    """Get action name from voice command"""
    return VOICE_CONFIG["actions"].get(voice_command)

# ============================================================
# LOGGING
# ============================================================

def log_action(action_name, source, details=None):
    """Log action to file and console"""
    if SYSTEM_CONFIG["log_actions"]:
        import time
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {source.upper()} -> {action_name}"
        if details:
            log_entry += f" ({details})"
        
        print(log_entry)
        
        try:
            with open(SYSTEM_CONFIG["log_file"], "a") as f:
                f.write(log_entry + "\n")
        except:
            pass
