# ============================================================
# SIMPLE DEMO - Eye and Gesture (No Threading)
# ============================================================
# Quick test to verify both cameras work

import cv2
import mediapipe as mp
import numpy as np
import time

print("\n" + "="*70)
print("SIMPLE DEMO - Eye Tracking + Gesture Recognition")
print("="*70 + "\n")

print("[*] Press 'E' to test Eye Tracking")
print("[*] Press 'G' to test Hand Gestures")
print("[*] Press 'Q' to quit\n")

choice = input("[?] Select (E/G/Q): ").upper()

if choice == 'Q':
    print("[DEMO] Goodbye!")
    exit()

elif choice == 'E':
    print("\n[EYE] Starting Eye Tracker...")
    print("[EYE] Looking at your face - try moving your eyes left and right")
    print("[EYE] Press Q to stop\n")
    
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("[ERROR] Cannot open webcam!")
        exit()
    
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    
    mp_face_mesh = mp.solutions.face_mesh
    face_mesh = mp_face_mesh.FaceMesh(
        static_image_mode=False,
        max_num_faces=1,
        refine_landmarks=True,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5
    )
    
    left_iris_indices = [468, 469, 470, 471, 472]
    right_iris_indices = [473, 474, 475, 476, 477]
    left_eye_indices = [33, 160, 158, 133, 153, 144]
    right_eye_indices = [263, 387, 385, 362, 380, 373]
    
    frame_count = 0
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        frame = cv2.resize(frame, (640, 480))
        h, w, c = frame.shape
        
        # Process
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = face_mesh.process(rgb_frame)
        
        # Background
        cv2.rectangle(frame, (10, 10), (630, 70), (0, 0, 0), -1)
        cv2.rectangle(frame, (10, 10), (630, 70), (0, 255, 0), 2)
        
        if results.multi_face_landmarks:
            landmarks = results.multi_face_landmarks[0].landmark
            cv2.putText(frame, "[OK] FACE DETECTED", (20, 45),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            
            # Draw both irises
            left_iris_x = int(np.mean([landmarks[i].x for i in left_iris_indices]) * w)
            left_iris_y = int(np.mean([landmarks[i].y for i in left_iris_indices]) * h)
            cv2.circle(frame, (left_iris_x, left_iris_y), 8, (0, 200, 255), 3)
            
            right_iris_x = int(np.mean([landmarks[i].x for i in right_iris_indices]) * w)
            right_iris_y = int(np.mean([landmarks[i].y for i in right_iris_indices]) * h)
            cv2.circle(frame, (right_iris_x, right_iris_y), 8, (255, 0, 100), 3)
        else:
            cv2.putText(frame, "[X] NO FACE", (20, 45),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        
        cv2.imshow("Eye Tracking - Press Q to stop", frame)
        
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        
        frame_count += 1
    
    cap.release()
    cv2.destroyAllWindows()
    print(f"[EYE] Processed {frame_count} frames - Done!")

elif choice == 'G':
    print("\n[GESTURE] Starting Hand Gesture Detector...")
    print("[GESTURE] Show your hand - try making peace sign or thumbs up")
    print("[GESTURE] Press Q to stop\n")
    
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("[ERROR] Cannot open webcam!")
        exit()
    
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    
    mp_hands = mp.solutions.hands
    hands = mp_hands.Hands(
        static_image_mode=False,
        max_num_hands=2,
        min_detection_confidence=0.7,
        min_tracking_confidence=0.5,
        model_complexity=1,
    )
    
    frame_count = 0
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        frame = cv2.resize(frame, (640, 480))
        h, w, c = frame.shape
        
        # Process
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = hands.process(rgb_frame)
        
        # Background
        cv2.rectangle(frame, (10, 10), (630, 70), (0, 0, 0), -1)
        cv2.rectangle(frame, (10, 10), (630, 70), (0, 255, 0), 2)
        
        if results.multi_hand_landmarks:
            cv2.putText(frame, f"[OK] {len(results.multi_hand_landmarks)} HAND(S) DETECTED", (20, 45),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            
            # Draw hand landmarks
            for hand_landmarks in results.multi_hand_landmarks:
                for idx, lm in enumerate(hand_landmarks.landmark):
                    x = int(lm.x * w)
                    y = int(lm.y * h)
                    cv2.circle(frame, (x, y), 4, (255, 0, 0), -1)
        else:
            cv2.putText(frame, "[X] NO HANDS", (20, 45),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        
        cv2.imshow("Hand Gestures - Press Q to stop", frame)
        
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        
        frame_count += 1
    
    cap.release()
    cv2.destroyAllWindows()
    print(f"[GESTURE] Processed {frame_count} frames - Done!")

else:
    print("[DEMO] Invalid choice!")
