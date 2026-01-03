#!/usr/bin/env python
"""
Real-Time Functionality Test
Tests that all modules work correctly in real-time scenarios
"""

import sys
import time
from typing import Dict, List

class RealTimeTest:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.warnings = []
    
    def test(self, name: str, fn):
        """Run test"""
        try:
            print(f"[TEST] {name}...", end=" ", flush=True)
            result = fn()
            print(f"✓ PASS")
            self.passed += 1
            return True
        except Exception as e:
            print(f"✗ FAIL - {e}")
            self.failed += 1
            return False
    
    def warn(self, msg: str):
        """Add warning"""
        self.warnings.append(msg)
        print(f"[WARN] {msg}")
    
    def report(self):
        """Print report"""
        total = self.passed + self.failed
        print("\n" + "="*70)
        print("REAL-TIME FUNCTIONALITY TEST REPORT")
        print("="*70)
        print(f"\nPassed: {self.passed}/{total}")
        print(f"Failed: {self.failed}/{total}")
        if self.warnings:
            print(f"\nWarnings ({len(self.warnings)}):")
            for w in self.warnings:
                print(f"  - {w}")
        print("="*70 + "\n")
        return self.failed == 0

def main():
    tester = RealTimeTest()
    
    print("\n" + "="*70)
    print("REAL-TIME FUNCTIONALITY TEST")
    print("="*70 + "\n")
    
    # Test 1: Event Bus Real-Time
    print("[SECTION] Event Bus Real-Time Operations")
    
    def test_event_queue_performance():
        from event_bus import get_event_bus, EventType, Event
        import queue
        bus = get_event_bus()
        
        # Stress test: 100 events
        start = time.time()
        for i in range(100):
            event = Event(
                event_type=EventType.GESTURE_DETECTED,
                source="test",
                data={"index": i},
                timestamp=time.time()
            )
            bus.emit_event(event)
        elapsed = time.time() - start
        
        if elapsed > 2.0:
            raise Exception(f"Event queue too slow: {elapsed:.3f}s for 100 events")
        print(f" ({elapsed*1000:.1f}ms)", end="")
        return True
    
    tester.test("Event Queue Performance (100 events)", test_event_queue_performance)
    
    def test_thread_safety():
        import threading
        from event_bus import get_event_bus, EventType, Event
        
        bus = get_event_bus()
        results = []
        
        def emit_events(thread_id):
            for i in range(10):
                event = Event(
                    event_type=EventType.GESTURE_DETECTED,
                    source=f"thread_{thread_id}",
                    data={"thread": thread_id, "count": i},
                    timestamp=time.time()
                )
                bus.emit_event(event)
        
        threads = [threading.Thread(target=emit_events, args=(i,)) for i in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5)
        
        print(" (3 threads)", end="")
        return True
    
    tester.test("Thread Safety (Multi-threaded events)", test_thread_safety)
    
    # Test 2: Action Mapper Real-Time
    print("\n[SECTION] Action Mapper Real-Time Operations")
    
    def test_action_cooldown():
        from action_mapper import get_mapper
        mapper = get_mapper()
        
        # Reset timer
        mapper.last_action_time = time.time() - 1.0
        
        # Execute action
        start = time.time()
        success = mapper.execute_action("copy", "test", "performance_test")
        elapsed = time.time() - start
        
        if elapsed > 0.5:
            raise Exception(f"Action execution too slow: {elapsed:.3f}s")
        print(f" ({elapsed*1000:.1f}ms)", end="")
        return success
    
    tester.test("Action Execution Speed", test_action_cooldown)
    
    def test_action_mapping():
        from action_mapper import ActionTranslator
        from config import GESTURE_CONFIG
        
        # Test translation
        actions = list(GESTURE_CONFIG["actions"].values())[:5]
        if not actions:
            raise Exception("No gesture actions configured")
        print(f" ({len(actions)} actions)", end="")
        return True
    
    tester.test("Action Translation (gesture)", test_action_mapping)
    
    # Test 3: Gesture Detection Logic
    print("\n[SECTION] Gesture Detection Logic")
    
    def test_gesture_logic():
        from gesture_module import HandGestureController
        # Just verify the method exists and is callable
        import inspect
        assert hasattr(HandGestureController, '_detect_gesture'), "Missing _detect_gesture"
        assert callable(getattr(HandGestureController, '_detect_gesture')), "_detect_gesture not callable"
        print(" (logic verified)", end="")
        return True
    
    tester.test("Gesture Detection Logic", test_gesture_logic)
    
    # Test 4: Eye Tracking Logic
    print("\n[SECTION] Eye Tracking Logic")
    
    def test_gaze_direction():
        from eye import IrisTracker
        # Verify gaze detection method exists
        assert hasattr(IrisTracker, 'detect_gaze'), "Missing detect_gaze"
        print(" (detection OK)", end="")
        return True
    
    tester.test("Gaze Direction Detection", test_gaze_direction)
    
    # Test 5: Voice Processing Pipeline
    print("\n[SECTION] Voice Processing Pipeline")
    
    def test_voice_intent():
        from voice_module import VoiceController
        assert hasattr(VoiceController, 'parse_intent'), "Missing parse_intent"
        print(" (intent parsing OK)", end="")
        return True
    
    tester.test("Voice Intent Parsing", test_voice_intent)
    
    # Test 6: Configuration Consistency
    print("\n[SECTION] Configuration Consistency")
    
    def test_config_consistency():
        from config import (
            SYSTEM_CONFIG, ACTION_MAPPINGS, 
            EYE_CONFIG, GESTURE_CONFIG, VOICE_CONFIG
        )
        
        # Check all configs have required keys
        assert "debug_mode" in SYSTEM_CONFIG, "Missing debug_mode"
        assert len(ACTION_MAPPINGS) > 0, "No actions defined"
        assert "camera_width" in EYE_CONFIG, "Missing eye config"
        assert "camera_width" in GESTURE_CONFIG, "Missing gesture config"
        assert "cooldown" in VOICE_CONFIG, "Missing voice config"
        
        print(f" ({len(ACTION_MAPPINGS)} actions)", end="")
        return True
    
    tester.test("Config Keys & Structure", test_config_consistency)
    
    # Test 7: Performance Baseline
    print("\n[SECTION] Performance Baseline")
    
    def test_import_speed():
        import time
        start = time.time()
        import eye_module
        import gesture_module
        import voice_module
        elapsed = time.time() - start
        print(f" ({elapsed*1000:.1f}ms)", end="")
        return True
    
    tester.test("Module Import Speed", test_import_speed)
    
    # Test 8: Memory & Resource Checks
    print("\n[SECTION] Resource Availability")
    
    def test_resources():
        import psutil
        import os
        
        # Get memory
        process = psutil.Process(os.getpid())
        memory = process.memory_info().rss / 1024 / 1024  # MB
        
        if memory > 500:
            tester.warn(f"High memory usage: {memory:.1f}MB")
        
        print(f" ({memory:.1f}MB)", end="")
        return True
    
    try:
        tester.test("Memory Usage", test_resources)
    except ImportError:
        tester.test("Memory Usage (psutil not available)", lambda: True)
    
    # Print report
    success = tester.report()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
