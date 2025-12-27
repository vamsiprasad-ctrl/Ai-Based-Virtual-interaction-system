"""
Backup version of voice_control.py
This is the previous version before the latest enhancements.
Kept for reference and rollback purposes.
"""

import speech_recognition as sr
import pyautogui
import pyttsx3
import time
import os

class VoiceController:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        try:
            self.mic = sr.Microphone()
        except Exception as e:
            print(f"[ERROR] Microphone setup failed: {e}")
            raise
        
        self.engine = pyttsx3.init()
        self.engine.setProperty('rate', 150)
        self.engine.setProperty('volume', 0.9)
        print("[VOICE] Voice Controller Ready (Backup Version)")

    def listen(self):
        """Listen for voice input"""
        try:
            with self.mic as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                audio = self.recognizer.listen(source, timeout=10)
            
            text = self.recognizer.recognize_google(audio)
            return text.lower()
        except sr.UnknownValueError:
            return None
        except sr.RequestError as e:
            print(f"[ERROR] Speech recognition service error: {e}")
            return None

    def speak(self, text):
        """Text to speech feedback"""
        try:
            self.engine.say(text)
            self.engine.runAndWait()
        except Exception as e:
            print(f"[ERROR] TTS error: {e}")

    def execute_intent(self, intent):
        """Execute voice command"""
        actions = {
            "open_browser": lambda: os.system("start chrome"),
            "open_notepad": lambda: os.system("notepad"),
            "open_calculator": lambda: os.system("calc"),
            "copy": lambda: pyautogui.hotkey('ctrl', 'c'),
            "paste": lambda: pyautogui.hotkey('ctrl', 'v'),
            "undo": lambda: pyautogui.hotkey('ctrl', 'z'),
            "minimize": lambda: pyautogui.hotkey('alt', 'F9'),
            "maximize": lambda: pyautogui.hotkey('alt', 'F10'),
        }
        
        if intent in actions:
            try:
                actions[intent]()
                self.speak(f"{intent} executed")
                return True
            except Exception as e:
                print(f"[ERROR] Execution failed: {e}")
                return False
        
        return False

    def run(self):
        """Main loop"""
        self.speak("Voice control started")
        while True:
            try:
                print("Listening...")
                command = self.listen()
                
                if command:
                    print(f"Heard: {command}")
                    # Simple keyword matching
                    if "browser" in command:
                        self.execute_intent("open_browser")
                    elif "notepad" in command:
                        self.execute_intent("open_notepad")
                    elif "calculator" in command:
                        self.execute_intent("open_calculator")
                    elif "copy" in command:
                        self.execute_intent("copy")
                    elif "paste" in command:
                        self.execute_intent("paste")
                    else:
                        print("Command not recognized")
                        self.speak("Command not recognized")
            except KeyboardInterrupt:
                self.speak("Voice control stopped")
                break
            except Exception as e:
                print(f"[ERROR] Unexpected error: {e}")

if __name__ == "__main__":
    vc = VoiceController()
    vc.run()
