"""
Test PyAutoGUI functionality
Verifies that keyboard and mouse automation is working correctly
"""

import pyautogui
import time

def test_keyboard():
    """Test keyboard simulation"""
    print("[TEST] Keyboard simulation...")
    try:
        # Test hotkey
        pyautogui.hotkey('alt', 'tab')
        time.sleep(0.5)
        print("[OK] Hotkey test passed")
        return True
    except Exception as e:
        print(f"[ERROR] Keyboard test failed: {e}")
        return False

def test_mouse():
    """Test mouse simulation"""
    print("[TEST] Mouse simulation...")
    try:
        # Get current position
        x, y = pyautogui.position()
        print(f"[INFO] Current mouse position: ({x}, {y})")
        
        # Move mouse
        pyautogui.moveTo(x + 10, y + 10, duration=0.5)
        time.sleep(0.5)
        
        # Move back
        pyautogui.moveTo(x, y, duration=0.5)
        time.sleep(0.5)
        
        print("[OK] Mouse test passed")
        return True
    except Exception as e:
        print(f"[ERROR] Mouse test failed: {e}")
        return False

def test_typing():
    """Test text typing"""
    print("[TEST] Text typing...")
    try:
        pyautogui.typewrite('hello world')
        time.sleep(0.5)
        print("[OK] Typing test passed")
        return True
    except Exception as e:
        print(f"[ERROR] Typing test failed: {e}")
        return False

def main():
    """Run all PyAutoGUI tests"""
    print("=" * 60)
    print("PYAUTOGUI FUNCTIONALITY TEST")
    print("=" * 60)
    
    tests = [
        test_keyboard,
        test_mouse,
        test_typing,
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"[ERROR] Test execution failed: {e}")
            results.append(False)
        time.sleep(1)
    
    print("=" * 60)
    passed = sum(1 for r in results if r)
    total = len(results)
    print(f"Results: {passed}/{total} tests passed")
    print("=" * 60)

if __name__ == "__main__":
    print("[WARNING] Make sure the cursor is in a text field before running!")
    time.sleep(3)
    main()
