# ============================================================
# EVENT BUS - Thread-Safe Multi-Modal Event System
# ============================================================
# Handles communication between eye tracking, gestures, and voice
# Prevents conflicts and enforces input prioritization

import queue
import threading
from typing import Dict, List, Callable, Any
from enum import Enum
from dataclasses import dataclass
from datetime import datetime
import time

from config import SYSTEM_CONFIG


class EventType(Enum):
    """Types of events from different modalities"""
    # Eye tracking events
    EYE_GAZE_LEFT = "eye_gaze_left"
    EYE_GAZE_RIGHT = "eye_gaze_right"
    EYE_GAZE_CENTER = "eye_gaze_center"
    EYE_BLINK = "eye_blink"
    EYE_DOUBLE_BLINK = "eye_double_blink"
    EYE_TRIPLE_BLINK = "eye_triple_blink"
    
    # Gesture events
    GESTURE_DETECTED = "gesture_detected"
    GESTURE_PINCH = "gesture_pinch"
    GESTURE_PEACE = "gesture_peace"
    GESTURE_PAUSE = "gesture_pause"
    
    # Voice events
    VOICE_COMMAND = "voice_command"
    VOICE_INTENT = "voice_intent"
    
    # System events
    ACTION_REQUESTED = "action_requested"
    ACTION_EXECUTED = "action_executed"
    ACTION_BLOCKED = "action_blocked"
    SYSTEM_PAUSE = "system_pause"
    SYSTEM_RESUME = "system_resume"


@dataclass
class Event:
    """Unified event structure"""
    event_type: EventType
    source: str  # "eye", "gesture", "voice"
    data: Dict[str, Any]
    timestamp: float
    priority: int = 0  # Higher = more important
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = time.time()


class EventBus:
    """Thread-safe event bus for multi-modal coordination"""
    
    def __init__(self, max_queue_size: int = 100):
        self.event_queue = queue.Queue(maxsize=max_queue_size)
        self.listeners: Dict[EventType, List[Callable]] = {}
        self.action_callbacks: Dict[str, Callable] = {}
        
        # State tracking
        self.system_paused = False
        self.last_event_time: Dict[str, float] = {
            "eye": 0,
            "gesture": 0,
            "voice": 0,
        }
        self.last_action_time = 0
        self.active_sources = set()
        
        # Lock for thread safety
        self.lock = threading.Lock()
        
        # Processing thread
        self.running = True
        self.processor_thread = threading.Thread(
            target=self._process_events,
            daemon=True,
            name="EventBusProcessor"
        )
        self.processor_thread.start()
        
        print("[EventBus] Initialized and ready")
    
    def register_listener(self, event_type: EventType, callback: Callable):
        """Register a callback for specific event type"""
        with self.lock:
            if event_type not in self.listeners:
                self.listeners[event_type] = []
            self.listeners[event_type].append(callback)
    
    def register_action_callback(self, action_name: str, callback: Callable):
        """Register callback for action execution"""
        with self.lock:
            self.action_callbacks[action_name] = callback
    
    def emit_event(self, event: Event) -> bool:
        """Emit event from a modality (thread-safe)"""
        try:
            self.event_queue.put(event, block=False)
            
            with self.lock:
                self.last_event_time[event.source] = event.timestamp
                self.active_sources.add(event.source)
            
            return True
        except queue.Full:
            print(f"[EventBus] Queue full, dropping event: {event.event_type}")
            return False
    
    def _process_events(self):
        """Main event processing loop"""
        while self.running:
            try:
                event = self.event_queue.get(timeout=0.1)
                self._handle_event(event)
            except queue.Empty:
                continue
            except Exception as e:
                print(f"[EventBus] Error processing event: {e}")
    
    def _handle_event(self, event: Event):
        """Handle single event with conflict resolution"""
        
        # Check system pause state
        if self.system_paused and event.source != "voice":
            self._emit_blocked_event(event, "system_paused")
            return
        
        # Handle pause/resume
        if event.event_type == EventType.GESTURE_PAUSE:
            self._toggle_system_pause()
            return
        
        # Conflict resolution based on priority
        if not self._should_process_event(event):
            self._emit_blocked_event(event, "conflict_resolution")
            return
        
        # Notify listeners
        self._notify_listeners(event)
        
        # Execute action if present
        if "action" in event.data:
            self._execute_action(event.data["action"], event)
    
    def _should_process_event(self, event: Event) -> bool:
        """Determine if event should be processed based on priority and conflicts"""
        with self.lock:
            # Voice always processes
            if event.source == "voice":
                return True
            
            # Check if voice is active (recent)
            time_since_voice = time.time() - self.last_event_time.get("voice", 0)
            if time_since_voice < 0.5 and event.source != "voice":
                return False  # Voice is active, block other inputs
            
            # Check inter-source conflicts
            if event.source == "eye" and "gesture" in self.active_sources:
                if not SYSTEM_CONFIG["allow_simultaneous"]["eye_gesture"]:
                    return False
            
            return True
    
    def _notify_listeners(self, event: Event):
        """Notify all listeners for event type"""
        with self.lock:
            callbacks = self.listeners.get(event.event_type, []).copy()
        
        for callback in callbacks:
            try:
                callback(event)
            except Exception as e:
                print(f"[EventBus] Listener error: {e}")
    
    def _execute_action(self, action_name: str, event: Event):
        """Execute registered action callback"""
        with self.lock:
            callback = self.action_callbacks.get(action_name)
        
        if callback:
            try:
                callback(action_name, event)
                self.last_action_time = time.time()
            except Exception as e:
                print(f"[EventBus] Action execution error: {e}")
        else:
            print(f"[EventBus] No handler for action: {action_name}")
    
    def _emit_blocked_event(self, event: Event, reason: str):
        """Log blocked event"""
        if SYSTEM_CONFIG["debug_mode"]:
            print(f"[EventBus] Event blocked: {event.event_type} ({reason})")
    
    def _toggle_system_pause(self):
        """Toggle system pause state"""
        with self.lock:
            self.system_paused = not self.system_paused
        
        status = "PAUSED" if self.system_paused else "RESUMED"
        print(f"[EventBus] System {status}")
        
        # Emit system event
        if self.system_paused:
            event = Event(
                event_type=EventType.SYSTEM_PAUSE,
                source="system",
                data={},
                timestamp=time.time()
            )
        else:
            event = Event(
                event_type=EventType.SYSTEM_RESUME,
                source="system",
                data={},
                timestamp=time.time()
            )
        
        self._notify_listeners(event)
    
    def get_status(self) -> Dict[str, Any]:
        """Get current bus status"""
        with self.lock:
            return {
                "system_paused": self.system_paused,
                "active_sources": list(self.active_sources),
                "last_event_times": self.last_event_time.copy(),
                "queue_size": self.event_queue.qsize(),
            }
    
    def shutdown(self):
        """Gracefully shutdown event bus"""
        self.running = False
        self.processor_thread.join(timeout=2.0)
        print("[EventBus] Shutdown complete")


# Global event bus instance
_event_bus = None


def get_event_bus() -> EventBus:
    """Get or create global event bus"""
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
    return _event_bus


def emit_event(event_type: EventType, source: str, data: Dict[str, Any], priority: int = 0):
    """Convenience function to emit events"""
    event = Event(
        event_type=event_type,
        source=source,
        data=data,
        timestamp=time.time(),
        priority=priority
    )
    return get_event_bus().emit_event(event)
