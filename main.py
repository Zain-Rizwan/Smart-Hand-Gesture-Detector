import cv2
import mediapipe as mp
import pyautogui
import math
import time
import threading
from tkinter import *

# Setup MediaPipe
mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils
hands = mp_hands.Hands(max_num_hands=1)

# GUI Variables
running = False
status_text = None
cap = None

# Smoothing Variables ⬅️ ADDED
prev_x, prev_y = 0, 0
smoothing = 7

# Helpers
def distance(pt1, pt2):
    return math.hypot(pt1[0] - pt2[0], pt1[1] - pt2[1])

def is_open_palm(landmarks):
    fingers = [8, 12, 16, 20]
    return sum(landmarks[f].y < landmarks[f-2].y for f in fingers) >= 4

def is_closed_fist(landmarks):
    fingers = [8, 12, 16, 20]
    return sum(landmarks[f].y > landmarks[f-2].y for f in fingers) >= 4

def update_status(text):
    status_text.set(f"Status: {text}")

def gesture_control():
    global running, cap, prev_x, prev_y

    screen_width, screen_height = pyautogui.size()
    prev_click_time = 0
    play_state = None
    volume_tracking_active = False
    volume_baseline = 30  # Default distance between thumb and index

    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)  # ⬅️ LOWER RESOLUTION
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    def finger_is_up(lm, tip, pip):
        return lm[tip].y < lm[pip].y

    def finger_is_down(lm, tip, pip):
        return lm[tip].y > lm[pip].y

    def all_fingers_down(lm):
        return not any([finger_is_up(lm, 8, 6), finger_is_up(lm, 12, 10),
                        finger_is_up(lm, 16, 14), finger_is_up(lm, 20, 18), 
                        finger_is_up(lm, 4, 2)])

    def all_fingers_down2(lm):
        return not any([finger_is_down(lm, 6, 10),
                        finger_is_down(lm, 6, 14), finger_is_down(lm, 6, 18), 
                        finger_is_down(lm, 6, 2)])
    # for left click and to check if 3 fingers are down
    def all_fingers_left_click(lm):
        return not any([finger_is_down(lm, 6, 14), finger_is_down(lm, 6, 18), 
                        finger_is_down(lm, 6, 2)])
    def all_fingers_right_click(lm):
    # Index (8, 6) and Middle (12, 10) up, others down
        return (
            finger_is_up(lm, 8, 6) and 
            finger_is_up(lm, 12, 10) and
            finger_is_up(lm, 16, 14) and  
            finger_is_down(lm, 20, 18) and  # Pinky down
            finger_is_down(lm, 4,13)        # Thumb down
        )
    def thumb_correct(lm):
        return lm[5].x < lm[4].x


    while running:
        success, frame = cap.read()
        if not success:
            break

        frame = cv2.flip(frame, 1)
        frame_height, frame_width, _ = frame.shape
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        result = hands.process(rgb)

        if result.multi_hand_landmarks:
            for hand_landmarks in result.multi_hand_landmarks:
                lm = hand_landmarks.landmark

                # Finger states
                index_up = finger_is_up(lm, 8, 6)
                middle_up = finger_is_up(lm, 12, 10)
                ring_up = finger_is_up(lm, 16, 14)
                pinky_up = finger_is_up(lm, 20, 18)
                thumb_up = finger_is_up(lm, 4, 2)

                # Coordinates
                index_tip = lm[8]
                index_x = int(index_tip.x * frame_width)
                index_y = int(index_tip.y * frame_height)
                screen_x = screen_width * index_tip.x
                screen_y = screen_height * index_tip.y

                thumb_tip = lm[4]
                index_tip = lm[8]
                middle_tip = lm[12]
                middle_x = int(middle_tip.x * frame_width)
                middle_y = int(middle_tip.y * frame_height)

                thumb_index_dist = distance(
                    (int(lm[4].x * frame_width), int(lm[4].y * frame_height)),
                    (int(lm[8].x * frame_width), int(lm[8].y * frame_height))
            )


                middle_index_dist = distance(
                    (index_x, index_y), 
                    (middle_x, middle_y)
                )

                current_time = time.time()
                gesture_interrupted = False

                # Cursor Movement with smoothing ⬅️ UPDATED
                if index_up and all_fingers_down2(lm) and thumb_correct(lm):
                    curr_x, curr_y = screen_x, screen_y
                    smooth_x = prev_x + (curr_x - prev_x) / smoothing
                    smooth_y = prev_y + (curr_y - prev_y) / smoothing
                    pyautogui.moveTo(smooth_x, smooth_y)
                    prev_x, prev_y = smooth_x, smooth_y
                    update_status("Cursor Moved")
                    gesture_interrupted = False

                # Left Click
                elif finger_is_up(lm, 8, 6) and finger_is_up(lm,12,10) and all_fingers_left_click(lm):
                    if (current_time - prev_click_time) > 1:
                        pyautogui.click()
                        update_status("Left Click")
                        prev_click_time = current_time
                        gesture_interrupted = True

                # Right Click
                elif all_fingers_right_click(lm):
                    if (current_time - prev_click_time) > 1:
                        pyautogui.click(button='right')
                        update_status("Right Click")
                        prev_click_time = current_time
                        gesture_interrupted = True

                # Play / Pause
                elif is_open_palm(lm) and play_state != "Play":
                    pyautogui.press('playpause')
                    play_state = "Play"
                    update_status("Play Media")
                    time.sleep(1)
                    gesture_interrupted = True

                elif is_closed_fist(lm) and play_state != "Pause":
                    pyautogui.press('playpause')
                    play_state = "Pause"
                    update_status("Pause Media")
                    time.sleep(1)
                    gesture_interrupted = True

                # Volume Control
                if gesture_interrupted:
                    volume_tracking_active = False
                    volume_baseline = 30
                else:
                    if not volume_tracking_active:
                        volume_tracking_active = True
                        volume_baseline = thumb_index_dist

                    diff = thumb_index_dist - volume_baseline
                    if abs(diff) > 10:
                        volume_steps = int(abs(diff) / 5)
                        if diff > 0:
                            for _ in range(volume_steps):
                                pyautogui.press('volumeup')
                            update_status("Volume Up")
                        else:
                            for _ in range(volume_steps):
                                pyautogui.press('volumedown')
                            update_status("Volume Down")
                        volume_baseline = thumb_index_dist



                mp_drawing.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)

        cv2.imshow("Gesture Control", frame)
        if cv2.waitKey(1) & 0xFF == 27:
            break

    cap.release()
    cv2.destroyAllWindows()
    update_status("Stopped")

def start_gesture_thread():
    global running
    if not running:
        running = True
        threading.Thread(target=gesture_control).start()
        update_status("Started")

def stop_gesture():
    global running, cap
    running = False
    if cap:
        cap.release()
    update_status("Stopping...")

# GUI Setup
root = Tk()
root.title("Contactless HCI System")
root.geometry("300x200")

status_text = StringVar()
status_text.set("Status: Idle")

Label(root, text="Contactless HCI with Gestures", font=("Arial", 14)).pack(pady=10)
Label(root, textvariable=status_text).pack(pady=5)

Button(root, text="Start", width=15, command=start_gesture_thread).pack(pady=5)
Button(root, text="Stop", width=15, command=stop_gesture).pack(pady=5)
Button(root, text="Exit", width=15, command=root.quit).pack(pady=5)

root.mainloop()
