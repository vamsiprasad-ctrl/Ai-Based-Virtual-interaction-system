qcc# Hand Gesture Control (Model 1)

Real-time hand gesture control using a webcam, MediaPipe Hands, and PyAutoGUI for mouse/keyboard actions.

## Features

- Index up only → Move cursor
- Thumb + Index pinch → Left click
- Pinch twice quickly → Double click
- Pinch and hold → Drag & drop
- OK gesture (pinch + middle up) → Right click
- Index + Middle + Ring up → Scroll up
- Middle + Ring + Pinky up → Scroll down
- Thumbs Up → Enter
- Thumbs Down → Escape
- Peace (Index + Middle up) → Copy (Ctrl + C)
- Fist (all down) → Paste (Ctrl + V)
- Peace then Fist (within ~1.2s) → Close tab (Ctrl + W)
- Open palm (all up) → Show desktop (Win + D)

All actions require gesture stability across multiple consecutive frames to avoid false triggers.

## Requirements

- Windows with a webcam
- Python 3.9+ recommended

## Install

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

On first run, Windows may prompt for Camera access. PyAutoGUI will move your mouse and send keys—ensure you’re ready.

## Run

```
python hand_gesture_control.py
```

- Press Q in the preview window to quit.
- For best results, use a well-lit background and keep your hand within the frame.

## Notes

- Cursor movement is smoothed; you can adjust move_smoothing and gesture_frames_required in main().
- Pinch detection uses thumb–index distance with a hold-to-drag threshold and a short double-click window.
- Thumbs up/down distinction uses thumb-only detection plus thumb tip position relative to wrist (up vs down).
- The OK gesture is resolved before pinch actions to avoid conflict.

## Troubleshooting

- If the webcam feed is black: close other apps using the camera and retry.
- If MediaPipe import fails: pip install mediapipe then rerun.
- If PyAutoGUI errors about failsafe: move mouse to a screen corner to abort; you can disable failsafe via pyautogui.FAILSAFE = False at the top (not recommended).
- Gestures ambiguous or flaky? Increase gesture_frames_required (e.g., 7) and ensure good lighting.
