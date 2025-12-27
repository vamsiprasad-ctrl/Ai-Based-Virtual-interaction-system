"""
Test New Commands - Verify newly added voice commands are working
Tests file navigation, app launchers, and media controls
"""

from voice_control import VoiceController

def test_file_navigation():
    """Test arrow key and file navigation commands"""
    print("\n" + "=" * 60)
    print("FILE NAVIGATION TESTS")
    print("=" * 60)
    
    vc = VoiceController()
    commands = [
        ("arrow up", "Move up"),
        ("arrow down", "Move down"),
        ("arrow left", "Move left"),
        ("arrow right", "Move right"),
        ("home key", "Go to beginning"),
        ("end key", "Go to end"),
        ("page up", "Page up"),
        ("page down", "Page down"),
    ]
    
    passed = 0
    for cmd, desc in commands:
        try:
            result = vc.execute(cmd)
            if result:
                print(f"[OK] {desc}: '{cmd}' ✓")
                passed += 1
            else:
                print(f"[FAIL] {desc}: '{cmd}' ✗")
        except Exception as e:
            print(f"[ERROR] {desc}: {e}")
    
    print(f"\nFile Navigation: {passed}/{len(commands)} passed")
    return passed == len(commands)

def test_app_launchers():
    """Test application launcher commands"""
    print("\n" + "=" * 60)
    print("APP LAUNCHER TESTS")
    print("=" * 60)
    
    vc = VoiceController()
    commands = [
        ("open notepad", "Notepad"),
        ("open calculator", "Calculator"),
        ("open terminal", "Terminal"),
        ("open explorer", "File Explorer"),
        ("open discord", "Discord"),
        ("open spotify", "Spotify"),
    ]
    
    passed = 0
    for cmd, name in commands:
        try:
            result = vc.execute(cmd)
            if result:
                print(f"[OK] {name}: '{cmd}' ✓")
                passed += 1
            else:
                print(f"[FAIL] {name}: '{cmd}' ✗")
        except Exception as e:
            print(f"[ERROR] {name}: {e}")
    
    print(f"\nApp Launchers: {passed}/{len(commands)} passed")
    return passed == len(commands)

def test_media_controls():
    """Test media control commands"""
    print("\n" + "=" * 60)
    print("MEDIA CONTROL TESTS")
    print("=" * 60)
    
    vc = VoiceController()
    commands = [
        ("play", "Play"),
        ("pause", "Pause"),
        ("next track", "Next track"),
        ("previous track", "Previous track"),
        ("mute", "Mute"),
    ]
    
    passed = 0
    for cmd, desc in commands:
        try:
            result = vc.execute(cmd)
            if result:
                print(f"[OK] {desc}: '{cmd}' ✓")
                passed += 1
            else:
                print(f"[FAIL] {desc}: '{cmd}' ✗")
        except Exception as e:
            print(f"[ERROR] {desc}: {e}")
    
    print(f"\nMedia Controls: {passed}/{len(commands)} passed")
    return passed == len(commands)

def main():
    """Run all new command tests"""
    print("=" * 60)
    print("NEW COMMANDS TEST SUITE")
    print("=" * 60)
    
    try:
        results = [
            test_file_navigation(),
            test_app_launchers(),
            test_media_controls(),
        ]
        
        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        if all(results):
            print("ALL TESTS PASSED!")
        else:
            print("SOME TESTS FAILED!")
        print("=" * 60)
        
    except Exception as e:
        print(f"[ERROR] Test suite failed: {e}")

if __name__ == "__main__":
    main()
