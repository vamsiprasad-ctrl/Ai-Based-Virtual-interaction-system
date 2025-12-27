"""
Quick Test - Fast verification of voice control functionality
Tests 3 basic commands to ensure system is working
"""

from voice_control import VoiceController
import time

def quick_test():
    """Run quick test of voice control"""
    print("=" * 60)
    print("QUICK TEST - VOICE CONTROL")
    print("=" * 60)
    
    try:
        vc = VoiceController()
        print("[OK] Voice Controller initialized\n")
        
        # Test 1: Copy command
        print("[TEST 1] Testing copy command...")
        vc.execute("copy")
        print("[OK] Copy test passed\n")
        time.sleep(0.5)
        
        # Test 2: Browser command
        print("[TEST 2] Testing open browser command...")
        vc.execute("open browser")
        print("[OK] Browser test passed\n")
        time.sleep(0.5)
        
        # Test 3: Screenshot command
        print("[TEST 3] Testing screenshot command...")
        vc.execute("take screenshot")
        print("[OK] Screenshot test passed\n")
        
        print("=" * 60)
        print("ALL QUICK TESTS PASSED!")
        print("=" * 60)
        
    except Exception as e:
        print(f"[ERROR] Quick test failed: {e}")
        print("=" * 60)

if __name__ == "__main__":
    quick_test()
