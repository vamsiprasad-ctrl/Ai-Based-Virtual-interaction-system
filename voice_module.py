# ============================================================
# VOICE MODULE - Refactored for Integration
# ============================================================
# Simplified voice control emitting events

import speech_recognition as sr
import pyttsx3
import time

# Delay imports to avoid circular dependency
VOICE_CONFIG = None
EventType = None
emit_event = None


def _init_imports():
    global VOICE_CONFIG, EventType, emit_event
    from config import VOICE_CONFIG as VC
    from event_bus import EventType as ET, emit_event as EE
    VOICE_CONFIG = VC
    EventType = ET
    emit_event = EE


class VoiceController:
    """Refactored voice control - emits events"""
    
    def __init__(self):
        _init_imports()  # Initialize imports immediately
        self.recognizer = sr.Recognizer()
        self.engine = pyttsx3.init()
        self.engine.setProperty("rate", VOICE_CONFIG["speech_rate"])
        
        try:
            self.mic = sr.Microphone()
        except Exception as e:
            print(f"[VOICE] Microphone error: {e}")
            self.mic = None
        
        self.last_command_time = 0
        self.cooldown = VOICE_CONFIG["cooldown"]
        
        self.running = True
        self.event_bus = None
        self.action_translator = None
        
        print("[VOICE] Initialized")
    
    def speak(self, text):
        """Text-to-speech"""
        try:
            self.engine.say(text)
            self.engine.runAndWait()
        except:
            pass
    
    def listen(self):
        """Listen for voice command"""
        if not self.mic:
            return ""
        
        try:
            with self.mic as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                audio = self.recognizer.listen(source, timeout=VOICE_CONFIG["listen_timeout"])
            
            text = self.recognizer.recognize_google(audio)
            print(f"[VOICE] Heard: {text}")
            return text.lower()
        
        except sr.UnknownValueError:
            return ""
        except sr.RequestError as e:
            print(f"[VOICE] Error: {e}")
            return ""
        except Exception as e:
            print(f"[VOICE] Error: {e}")
            return ""
    
    def parse_intent(self, command):
        """Simple keyword-based intent matching"""
        if not command:
            return None
        
        cmd = command.lower().strip()
        
        # Direct mappings - expanded for common commands
        mappings = {
            # Navigation
            "next": "next_tab",
            "previous": "previous_tab",
            "prev": "previous_tab",
            "back": "previous_tab",
            "close": "close_tab",
            "new": "new_tab",
            "tab": "next_tab",
            
            # Copy/Paste
            "copy": "copy",
            "paste": "paste",
            "cut": "cut",
            
            # Undo/Redo
            "undo": "undo",
            "redo": "redo",
            
            # Media
            "play": "play_pause",
            "pause": "play_pause",
            "stop": "play_pause",
            "mute": "mute",
            "unmute": "volume_up",
            "volume up": "volume_up",
            "volume down": "volume_down",
            "louder": "volume_up",
            "quieter": "volume_down",
            
            # Screenshot
            "screenshot": "screenshot",
            "capture": "screenshot",
            "snap": "screenshot",
            
            # System
            "escape": "escape",
            "exit": "escape",
            "enter": "enter",
            "return": "enter",
        }
        
        for keyword, intent in mappings.items():
            if keyword in cmd:
                return intent
        
        return None
    
    def run(self):
        """Main listening loop"""
        print("[VOICE] Starting listener...")
        try:
            self.speak("Voice control ready")
        except:
            pass
        
        while self.running:
            try:
                command = self.listen()
                
                if not command:
                    time.sleep(1.0)  # Longer wait on timeout
                    continue
                
                t = time.time()
                if (t - self.last_command_time) < self.cooldown:
                    time.sleep(0.5)
                    continue
                
                intent = self.parse_intent(command)
                
                if intent:
                    emit_event(
                        EventType.VOICE_COMMAND,
                        "voice",
                        {"action": intent, "details": command},
                        priority=3
                    )
                    print(f"[VOICE] {command} -> {intent}")
                    try:
                        self.speak(f"OK")
                    except:
                        pass
                    self.last_command_time = t
                else:
                    print(f"[VOICE] Unknown command: {command}")
                
            except KeyboardInterrupt:
                self.running = False
            except Exception as e:
                print(f"[VOICE] Error: {e}")
                time.sleep(2.0)  # Longer wait on error
        
        print("[VOICE] Stopped")


if __name__ == "__main__":
    controller = VoiceController()
    controller.run()
