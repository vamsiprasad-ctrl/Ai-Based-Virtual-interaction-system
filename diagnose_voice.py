"""
Diagnostic Tool for Voice Control Setup
Checks microphone, speech recognition, and system requirements.
"""

import sys
import importlib
import subprocess

def check_python_version():
    """Check Python version"""
    version = sys.version_info
    print(f"[CHECK] Python version: {version.major}.{version.minor}.{version.micro}")
    if version.major >= 3 and version.minor >= 8:
        print("[OK] Python version is compatible")
        return True
    else:
        print("[ERROR] Python 3.8+ required")
        return False

def check_module(module_name):
    """Check if module is installed"""
    try:
        importlib.import_module(module_name)
        print(f"[OK] {module_name} is installed")
        return True
    except ImportError:
        print(f"[ERROR] {module_name} is not installed")
        return False

def check_microphone():
    """Check microphone availability"""
    try:
        import speech_recognition as sr
        mic = sr.Microphone()
        print("[OK] Microphone is available")
        return True
    except Exception as e:
        print(f"[ERROR] Microphone check failed: {e}")
        return False

def check_speech_recognition():
    """Check speech recognition service"""
    try:
        import speech_recognition as sr
        recognizer = sr.Recognizer()
        print("[OK] Speech recognition is available")
        return True
    except Exception as e:
        print(f"[ERROR] Speech recognition check failed: {e}")
        return False

def check_pyautogui():
    """Check PyAutoGUI"""
    try:
        import pyautogui
        print(f"[OK] PyAutoGUI is available (version: {pyautogui.__version__})")
        return True
    except Exception as e:
        print(f"[ERROR] PyAutoGUI check failed: {e}")
        return False

def diagnose():
    """Run all diagnostic checks"""
    print("=" * 60)
    print("VOICE CONTROL DIAGNOSTIC TOOL")
    print("=" * 60)
    
    checks = [
        ("Python Version", check_python_version),
        ("speech_recognition", lambda: check_module('speech_recognition')),
        ("pyautogui", lambda: check_module('pyautogui')),
        ("pyttsx3", lambda: check_module('pyttsx3')),
        ("sounddevice", lambda: check_module('sounddevice')),
        ("Microphone", check_microphone),
        ("Speech Recognition", check_speech_recognition),
        ("PyAutoGUI", check_pyautogui),
    ]
    
    results = []
    for check_name, check_func in checks:
        print(f"\nChecking {check_name}...")
        try:
            result = check_func()
            results.append((check_name, result))
        except Exception as e:
            print(f"[ERROR] {check_name} check failed: {e}")
            results.append((check_name, False))
    
    print("\n" + "=" * 60)
    print("DIAGNOSTIC SUMMARY")
    print("=" * 60)
    passed = sum(1 for _, result in results if result)
    total = len(results)
    print(f"Passed: {passed}/{total}")
    
    for check_name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"  [{status}] {check_name}")
    
    print("=" * 60)

if __name__ == "__main__":
    diagnose()
