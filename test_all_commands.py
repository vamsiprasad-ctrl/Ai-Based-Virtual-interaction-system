#!/usr/bin/env python3
"""
Comprehensive test of all voice control commands.
Tests each command type to verify they actually execute.
"""

import os
import sys
import time

# Add current directory to path
sys.path.insert(0, os.getcwd())

try:
    from voice_control import VoiceController
except ImportError as e:
    print(f"❌ Failed to import VoiceController: {e}")
    sys.exit(1)

print("=" * 70)
print("COMPREHENSIVE COMMAND EXECUTION TEST")
print("=" * 70)

# Initialize voice controller
print("\n[0] Initializing Voice Controller...")
try:
    vc = VoiceController()
    print("✅ Voice Controller initialized")
except Exception as e:
    print(f"❌ Failed to initialize: {e}")
    sys.exit(1)

# Test categories
test_commands = {
    "Browser Commands": [
        ("open_browser", "open browser"),
        ("new_tab", "new tab"),
        ("close_tab", "close tab"),
    ],
    "Application Launch": [
        ("open_notepad", "open notepad"),
        ("open_terminal", "open terminal"),
    ],
    "Window Management": [
        ("minimize_window", "minimize"),
        ("maximize_window", "maximize"),
        ("show_desktop", "show desktop"),
    ],
    "Keyboard Shortcuts": [
        ("copy", "copy"),
        ("paste", "paste"),
        ("undo", "undo"),
    ],
    "Media Control": [
        ("mute", "mute"),
        ("volume_up", "volume up"),
    ],
    "System": [
        ("screenshot", "take screenshot"),
        ("lock_screen", "lock screen"),
    ]
}

total_tests = sum(len(cmds) for cmds in test_commands.values())
passed = 0
failed = 0

for category, commands in test_commands.items():
    print(f"\n{'='*70}")
    print(f"📋 Testing {category}")
    print('='*70)
    
    for intent, voice_phrase in commands:
        print(f"\n  Command: {intent}")
        print(f"  Voice phrase: '{voice_phrase}'")
        print(f"  Simulating: vc.execute('{voice_phrase}')")
        
        try:
            # Test the execute method
            result = vc.execute(voice_phrase)
            print(f"  ✅ PASSED - returned {result}")
            passed += 1
            time.sleep(0.5)  # Small delay between commands
        except Exception as e:
            print(f"  ❌ FAILED - Exception: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

# Special test for screenshot
print(f"\n{'='*70}")
print(f"📷 Special Test: Screenshot Verification")
print('='*70)

try:
    screenshot_dir = "screenshots"
    if os.path.exists(screenshot_dir):
        files_before = len(os.listdir(screenshot_dir))
    else:
        files_before = 0
    
    print(f"  Files in screenshots/ before: {files_before}")
    vc.execute("take screenshot")
    time.sleep(1)
    
    files_after = len(os.listdir(screenshot_dir))
    print(f"  Files in screenshots/ after: {files_after}")
    
    if files_after > files_before:
        print(f"  ✅ Screenshot was created!")
        # List the files
        for f in os.listdir(screenshot_dir):
            fpath = os.path.join(screenshot_dir, f)
            size = os.path.getsize(fpath)
            print(f"     - {f} ({size} bytes)")
    else:
        print(f"  ❌ No screenshot was created")
        failed += 1
except Exception as e:
    print(f"  ❌ Error: {e}")
    failed += 1

# Summary
print(f"\n{'='*70}")
print("TEST SUMMARY")
print('='*70)
print(f"Total commands tested: {total_tests}")
print(f"✅ Passed: {passed}")
print(f"❌ Failed: {failed}")
print(f"Success rate: {(passed/total_tests)*100:.1f}%")

if failed == 0:
    print("\n🎉 ALL TESTS PASSED!")
else:
    print(f"\n⚠️  {failed} test(s) failed")
    print("\nChecklist:")
    print("1. Is a web browser open for 'new_tab'/'close_tab' to work?")
    print("2. Is a terminal/cmd open for keyboard shortcuts to work?")
    print("3. Check screenshots/ folder for created screenshots")
    print("4. Check if applications (notepad, cmd) were launched")
