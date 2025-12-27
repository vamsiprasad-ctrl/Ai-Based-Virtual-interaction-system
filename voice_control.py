import speech_recognition as sr
import pyautogui
import pyttsx3
import time
import os
import json

# Optional Gemini setup (may be unavailable in some environments)
try:
    import google.generativeai as genai
    # Accept either GEMINI_API_KEY (user set) or GOOGLE_API_KEY (SDK common var)
    API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if API_KEY:
        genai.configure(api_key=API_KEY)
        GEMINI_MODEL = genai.GenerativeModel("gemini-1.5-flash")
        GEMINI_AVAILABLE = True
    else:
        print('[WARN] Gemini API key not found. Set GEMINI_API_KEY or GOOGLE_API_KEY to enable Gemini fallback.')
        GEMINI_AVAILABLE = False
        GEMINI_MODEL = None
except Exception:
    print('[WARN] google-generativeai library not available or failed to import.')
    GEMINI_AVAILABLE = False
    GEMINI_MODEL = None

# Optional sounddevice fallback when PyAudio is missing
try:
    import sounddevice as sd
    import numpy as np
    SOUNDDEVICE_AVAILABLE = True
except Exception:
    SOUNDDEVICE_AVAILABLE = False

class VoiceController:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.use_sounddevice = False
        try:
            self.mic = sr.Microphone()
        except Exception as e:
            print("[ERROR] Microphone not available via PyAudio:", e)
            if SOUNDDEVICE_AVAILABLE:
                print("[INFO] Falling back to sounddevice for audio capture")
                self.mic = None
                self.use_sounddevice = True
            else:
                print("[ERROR] Neither PyAudio nor sounddevice available. Install one to enable microphone.")
                raise

        self.engine = pyttsx3.init()
        self.engine.setProperty("rate", 170)

        self.last_command_time = 0
        self.cooldown = 1.0

        print("[VOICE] Voice Controller Ready")
        self.speak("Voice control activated")

    def speak(self, text):
        try:
            self.engine.say(text)
            self.engine.runAndWait()
        except:
            pass

    def listen(self):
        # If fallback enabled, capture audio via sounddevice
        if self.use_sounddevice:
            fs = 16000
            duration = 4  # seconds
            print("[REC] Recording (sounddevice)...")
            try:
                recording = sd.rec(int(duration * fs), samplerate=fs, channels=1, dtype='int16')
                sd.wait()
                raw_data = recording.tobytes()
                audio_data = sr.AudioData(raw_data, fs, 2)
            except Exception as e:
                print("[ERROR] sounddevice recording failed:", e)
                return ""

            try:
                command = self.recognizer.recognize_google(audio_data)
                print(f"[SPEECH] You said: {command}")
                return command.lower()
            except sr.UnknownValueError:
                print("[WARN] Speech recognition could not understand audio")
                return ""
            except sr.RequestError as e:
                print(f"[WARN] Google API error: {e}")
                return ""
            except Exception as e:
                print(f"[ERROR] Recognition error: {e}")
                return ""

        # Default path (PyAudio + Microphone)
        try:
            with self.mic as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                print("[LISTEN] Listening...")
                audio = self.recognizer.listen(source, phrase_time_limit=4)

            try:
                text = self.recognizer.recognize_google(audio)
                print(f"[SPEECH] You said: {text}")
                return text.lower()
            except sr.UnknownValueError:
                print("[WARN] Speech recognition could not understand audio. Try speaking louder.")
                return ""
            except sr.RequestError as e:
                print(f"[WARN] Google API error: {e}")
                print("   (Check internet connection)")
                return ""
        except Exception as e:
            print(f"[ERROR] Microphone error: {e}")
            return ""

    # ---------------- GEMINI INTENT ----------------
    def gemini_intent(self, user_command):
        if not GEMINI_AVAILABLE or GEMINI_MODEL is None:
            return None
        prompt = f"""
Convert the user command into ONE intent.
Return ONLY JSON like {{ "intent": "close_tab" }}.

Supported intents:
open_browser, open_notepad, open_terminal,
new_tab, reopen_tab, close_tab,
next_tab, previous_tab,
close_window, minimize_window, maximize_window,
scroll_up, scroll_down,
enter, escape,
copy, paste, cut, select_all, undo, redo, find,
mute, volume_up, volume_down, play_pause,
show_desktop, lock_screen, task_manager, open_settings,
screenshot, exit_system

User command: "{user_command}"
"""
        try:
            response = GEMINI_MODEL.generate_content(prompt)
            raw = response.text.strip()
            print("[GEMINI] Raw response:", raw)

            start = raw.find("{")
            end = raw.rfind("}") + 1
            if start == -1 or end == -1:
                return None

            data = json.loads(raw[start:end])
            return data.get("intent")

        except Exception as e:
            print("[WARN] Gemini error:", e)
            return None

    # ---------------- LOCAL INTENT (KEYWORD-BASED, NATURAL) ----------------
    def local_intent(self, command):
        cmd = (command or "").lower().strip()
        if not cmd:
            return None

        # quick cleanup
        for p in ["please ", "could you ", "would you ", "hey "]:
            if cmd.startswith(p):
                cmd = cmd[len(p):].strip()

        # keyword -> intent mapping (contains match)
        mapping = {
            # Browser & Web
            "open_browser": ["open browser", "open chrome", "launch browser", "start browser", "open google"],
            "open_chrome": ["open chrome", "launch chrome"],
            "open_firefox": ["open firefox", "launch firefox"],
            "open_edge": ["open edge", "open microsoft edge", "launch edge"],
            # Text & Office
            "open_notepad": ["open notepad", "start notepad"],
            "open_wordpad": ["open wordpad", "start wordpad"],
            "open_word": ["open word", "open office word", "open microsoft word"],
            "open_excel": ["open excel", "open spreadsheet"],
            "open_powerpoint": ["open powerpoint", "open presentation"],
            # System & Tools
            "open_terminal": ["open terminal", "open cmd", "open command prompt", "start terminal"],
            "open_calculator": ["open calculator", "calculator"],
            "open_paint": ["open paint", "start paint"],
            "open_explorer": ["open explorer", "open file explorer", "open files"],
            # Development & Code Editors
            "open_vscode": ["open vscode", "launch vscode", "open vs code", "open code", "code"],
            "open_git": ["open git", "git bash", "launch git"],
            # Media & Entertainment
            "open_vlc": ["open vlc", "open video player", "start vlc"],
            "open_spotify": ["open spotify", "launch spotify", "open music"],
            "open_youtube": ["open youtube", "launch youtube", "open youtube"],
            "open_netflix": ["open netflix", "launch netflix"],
            # Communication
            "open_discord": ["open discord", "launch discord"],
            "open_telegram": ["open telegram", "launch telegram"],
            "open_slack": ["open slack", "launch slack"],
            "open_teams": ["open teams", "launch teams", "open microsoft teams"],
            "open_whatsapp": ["open whatsapp", "launch whatsapp"],
            # Browser Tabs & Navigation
            "new_tab": ["new tab", "open new tab", "open tab"],
            "close_tab": ["close tab", "close this tab", "bye tab"],
            "reopen_tab": ["reopen tab", "restore tab"],
            "next_tab": ["next tab", "switch tab", "go to next tab"],
            "previous_tab": ["previous tab", "go back tab", "previous"],
            # Window Management
            "close_window": ["close window", "close this window", "close app", "quit app"],
            "minimize_window": ["minimize", "minimise", "minimize window"],
            "maximize_window": ["maximize", "maximize window", "fullscreen"],
            # File Navigation & Search
            "arrow_up": ["up", "go up", "move up", "arrow up", "previous item"],
            "arrow_down": ["down", "go down", "move down", "arrow down", "next item"],
            "arrow_left": ["left", "go left", "move left", "arrow left"],
            "arrow_right": ["right", "go right", "move right", "arrow right"],
            "page_up": ["page up", "page previous", "scroll up"],
            "page_down": ["page down", "page next", "scroll down"],
            "home": ["home", "go to start"],
            "end": ["end", "go to end"],
            # Scrolling
            "scroll_up": ["scroll up", "scroll up page"],
            "scroll_down": ["scroll down", "scroll down page"],
            # Keyboard Control
            "enter": ["press enter", "hit enter", "enter", "confirm", "select"],
            "escape": ["press escape", "escape", "esc", "cancel"],
            "tab": ["press tab", "tab"],
            "backspace": ["backspace", "delete back", "go back"],
            "delete": ["delete", "remove"],
            "space": ["space", "spacebar"],
            # Text Editing
            "copy": ["copy that", "copy"],
            "paste": ["paste"],
            "cut": ["cut"],
            "select_all": ["select all", "highlight all"],
            "undo": ["undo", "undo that"],
            "redo": ["redo"],
            "find": ["find", "search in page", "search"],
            "replace": ["replace", "find and replace"],
            # Media Control
            "play_pause": ["play", "pause", "play pause", "resume"],
            "mute": ["mute"],
            "volume_up": ["volume up", "increase volume", "turn up volume"],
            "volume_down": ["volume down", "decrease volume", "turn down volume"],
            "next_track": ["next track", "next song", "skip"],
            "previous_track": ["previous track", "previous song", "go back"],
            # System Control
            "show_desktop": ["show desktop", "minimize all"],
            "lock_screen": ["lock screen", "lock pc"],
            "task_manager": ["task manager", "open task manager"],
            "open_settings": ["open settings", "settings"],
            "refresh": ["refresh", "reload", "refresh page"],
            # Capture & Share
            "screenshot": ["screenshot", "take screenshot", "capture screen"],
            "screen_record": ["screen record", "record screen", "start recording"],
            # Exit
            "exit_system": ["exit system", "stop voice", "stop listening", "shutdown voice control"]
        }

        for intent, phrases in mapping.items():
            for phrase in phrases:
                if phrase in cmd:
                    return intent

        return None

    # ---------------- EXECUTE INTENT ----------------
    def execute_intent(self, intent):
        print(f"[INTENT] Intent matched: {intent}")

        actions = {
            # Browser & Web
            "open_chrome": lambda: self._safe_execute(lambda: os.system("start chrome"), "open_chrome"),
            "open_firefox": lambda: self._safe_execute(lambda: os.system("start firefox"), "open_firefox"),
            "open_edge": lambda: self._safe_execute(lambda: os.system("start msedge"), "open_edge"),
            "open_browser": lambda: self._safe_execute(lambda: os.system("start chrome"), "open_browser"),
            # Text & Office
            "open_notepad": lambda: self._safe_execute(lambda: os.system("start notepad"), "open_notepad"),
            "open_wordpad": lambda: self._safe_execute(lambda: os.system("start wordpad"), "open_wordpad"),
            "open_word": lambda: self._safe_execute(lambda: os.system("start winword"), "open_word"),
            "open_excel": lambda: self._safe_execute(lambda: os.system("start excel"), "open_excel"),
            "open_powerpoint": lambda: self._safe_execute(lambda: os.system("start powerpnt"), "open_powerpoint"),
            # System & Tools
            "open_terminal": lambda: self._safe_execute(lambda: os.system("start cmd"), "open_terminal"),
            "open_calculator": lambda: self._safe_execute(lambda: os.system("start calc"), "open_calculator"),
            "open_paint": lambda: self._safe_execute(lambda: os.system("start mspaint"), "open_paint"),
            "open_explorer": lambda: self._safe_execute(lambda: os.system("start explorer"), "open_explorer"),
            # Development & Code Editors
            "open_vscode": lambda: self._safe_execute(lambda: os.system("code"), "open_vscode"),
            "open_git": lambda: self._safe_execute(lambda: os.system("start bash"), "open_git"),
            # Media & Entertainment
            "open_vlc": lambda: self._safe_execute(lambda: os.system("start vlc"), "open_vlc"),
            "open_spotify": lambda: self._safe_execute(lambda: os.system("start spotify"), "open_spotify"),
            "open_youtube": lambda: self._safe_execute(lambda: os.system("start https://youtube.com"), "open_youtube"),
            "open_netflix": lambda: self._safe_execute(lambda: os.system("start https://netflix.com"), "open_netflix"),
            # Communication
            "open_discord": lambda: self._safe_execute(lambda: os.system("start discord"), "open_discord"),
            "open_telegram": lambda: self._safe_execute(lambda: os.system("start telegram"), "open_telegram"),
            "open_slack": lambda: self._safe_execute(lambda: os.system("start slack"), "open_slack"),
            "open_teams": lambda: self._safe_execute(lambda: os.system("start teams"), "open_teams"),
            "open_whatsapp": lambda: self._safe_execute(lambda: os.system("start https://web.whatsapp.com"), "open_whatsapp"),
            # Browser Tabs & Navigation
            "new_tab": lambda: self._safe_execute(lambda: pyautogui.hotkey("ctrl","t"), "new_tab"),
            "reopen_tab": lambda: self._safe_execute(lambda: pyautogui.hotkey("ctrl","shift","t"), "reopen_tab"),
            "close_tab": lambda: self._safe_execute(lambda: pyautogui.hotkey("ctrl","w"), "close_tab"),
            "next_tab": lambda: self._safe_execute(lambda: pyautogui.hotkey("ctrl","tab"), "next_tab"),
            "previous_tab": lambda: self._safe_execute(lambda: pyautogui.hotkey("ctrl","shift","tab"), "previous_tab"),
            # Window Management
            "close_window": lambda: self._safe_execute(lambda: pyautogui.hotkey("alt","f4"), "close_window"),
            "minimize_window": lambda: self._safe_execute(lambda: pyautogui.hotkey("winleft","down"), "minimize_window"),
            "maximize_window": lambda: self._safe_execute(lambda: pyautogui.hotkey("winleft","up"), "maximize_window"),
            # Navigation & Arrow Keys
            "arrow_up": lambda: self._safe_execute(lambda: pyautogui.press("up"), "arrow_up"),
            "arrow_down": lambda: self._safe_execute(lambda: pyautogui.press("down"), "arrow_down"),
            "arrow_left": lambda: self._safe_execute(lambda: pyautogui.press("left"), "arrow_left"),
            "arrow_right": lambda: self._safe_execute(lambda: pyautogui.press("right"), "arrow_right"),
            "page_up": lambda: self._safe_execute(lambda: pyautogui.press("pageup"), "page_up"),
            "page_down": lambda: self._safe_execute(lambda: pyautogui.press("pagedown"), "page_down"),
            "home": lambda: self._safe_execute(lambda: pyautogui.press("home"), "home"),
            "end": lambda: self._safe_execute(lambda: pyautogui.press("end"), "end"),
            # Scrolling
            "scroll_up": lambda: self._safe_execute(lambda: pyautogui.scroll(400), "scroll_up"),
            "scroll_down": lambda: self._safe_execute(lambda: pyautogui.scroll(-400), "scroll_down"),
            # Keyboard Control
            "enter": lambda: self._safe_execute(lambda: pyautogui.press("enter"), "enter"),
            "escape": lambda: self._safe_execute(lambda: pyautogui.press("esc"), "escape"),
            "tab": lambda: self._safe_execute(lambda: pyautogui.press("tab"), "tab"),
            "backspace": lambda: self._safe_execute(lambda: pyautogui.press("backspace"), "backspace"),
            "delete": lambda: self._safe_execute(lambda: pyautogui.press("delete"), "delete"),
            "space": lambda: self._safe_execute(lambda: pyautogui.press("space"), "space"),
            # Text Editing
            "copy": lambda: self._safe_execute(lambda: pyautogui.hotkey("ctrl","c"), "copy"),
            "paste": lambda: self._safe_execute(lambda: pyautogui.hotkey("ctrl","v"), "paste"),
            "cut": lambda: self._safe_execute(lambda: pyautogui.hotkey("ctrl","x"), "cut"),
            "select_all": lambda: self._safe_execute(lambda: pyautogui.hotkey("ctrl","a"), "select_all"),
            "undo": lambda: self._safe_execute(lambda: pyautogui.hotkey("ctrl","z"), "undo"),
            "redo": lambda: self._safe_execute(lambda: pyautogui.hotkey("ctrl","shift","z"), "redo"),
            "find": lambda: self._safe_execute(lambda: pyautogui.hotkey("ctrl","f"), "find"),
            "replace": lambda: self._safe_execute(lambda: pyautogui.hotkey("ctrl","h"), "replace"),
            # Media Control
            "play_pause": lambda: self._safe_execute(lambda: pyautogui.press("playpause"), "play_pause"),
            "mute": lambda: self._safe_execute(lambda: pyautogui.press("volumemute"), "mute"),
            "volume_up": lambda: self._safe_execute(lambda: pyautogui.press("volumeup"), "volume_up"),
            "volume_down": lambda: self._safe_execute(lambda: pyautogui.press("volumedown"), "volume_down"),
            "next_track": lambda: self._safe_execute(lambda: pyautogui.press("nexttrack"), "next_track"),
            "previous_track": lambda: self._safe_execute(lambda: pyautogui.press("prevtrack"), "previous_track"),
            # System Control
            "show_desktop": lambda: self._safe_execute(lambda: pyautogui.hotkey("winleft","d"), "show_desktop"),
            "lock_screen": lambda: self._safe_execute(lambda: pyautogui.hotkey("winleft","l"), "lock_screen"),
            "task_manager": lambda: self._safe_execute(lambda: pyautogui.hotkey("ctrl","shift","esc"), "task_manager"),
            "open_settings": lambda: self._safe_execute(lambda: pyautogui.hotkey("winleft","i"), "open_settings"),
            "refresh": lambda: self._safe_execute(lambda: pyautogui.press("f5"), "refresh"),
            # Capture & Share
            "screenshot": self.take_screenshot,
            "screen_record": lambda: self._safe_execute(lambda: pyautogui.hotkey("winleft","alt","r"), "screen_record"),
            # Exit
            "exit_system": lambda: False,
        }

        action = actions.get(intent)
        if action:
            try:
                print(f"[EXEC] Executing: {intent}")
                result = action()
                if result is not False:
                    print(f"[OK] {intent} executed")
                    self.speak(intent.replace("_", " "))
                    return True if intent != "exit_system" else False
                else:
                    return False
            except Exception as e:
                print(f"[ERROR] Error executing {intent}: {type(e).__name__}: {e}")
                import traceback
                traceback.print_exc()
                self.speak(f"Error executing {intent}")
                return True
        else:
            print(f"[ERROR] Action '{intent}' not found in actions dict")
            self.speak("Action not supported")
            return True

    def _safe_execute(self, func, name):
        """Execute function with error handling and logging"""
        try:
            print(f"  [RUN] {name}...")
            func()
            time.sleep(0.2)  # Small delay to ensure command processes
            print(f"  [DONE] {name} completed")
            return True
        except Exception as e:
            print(f"  [FAIL] {name} failed: {e}")
            raise

    def take_screenshot(self):
        try:
            os.makedirs("screenshots", exist_ok=True)
            fname = f"screenshots/screenshot_{int(time.time())}.png"
            print(f"[SCREENSHOT] Taking screenshot, saving to: {fname}")
            pyautogui.screenshot(fname)
            # Verify file was created
            if os.path.exists(fname):
                file_size = os.path.getsize(fname)
                print(f"[OK] Screenshot saved: {fname} ({file_size} bytes)")
                self.speak("Screenshot saved")
            else:
                print(f"[ERROR] Screenshot file not created at {fname}")
                self.speak("Screenshot failed - file not created")
        except Exception as e:
            print(f"[ERROR] Screenshot error: {e}")
            self.speak(f"Screenshot failed: {str(e)}")

    # ---------------- MAIN EXECUTE ----------------
    def execute(self, command):
        if not command:
            return True

        t = time.time()
        if t - self.last_command_time < self.cooldown:
            return True

        print(f"[CMD] Command received: '{command}'")

        # Try local natural intent parsing first
        local = self.local_intent(command)
        if local:
            print(f"[LOCAL] Local parser matched: {local}")
            if local in ["exit_system"]:
                self.speak("Voice control stopped")
                return False
            return self.execute_intent(local)

        # If local parser didn't match, try Gemini (if available)
        print("[GEMINI] No local match, sending to Gemini...")
        intent = self.gemini_intent(command)
        if intent:
            print(f"[GEMINI] Gemini matched: {intent}")
            return self.execute_intent(intent)
        else:
            print("[ERROR] No intent matched (local or Gemini)")
            self.speak("Command not recognized")

        self.last_command_time = t
        return True

    def run(self):
        running = True
        while running:
            command = self.listen()
            if command:
                running = self.execute(command)


if __name__ == "__main__":
    VoiceController().run()
