import cv2

from line_follow import LineFollower, DummyMotor, StepCounter
from object_detection import DetectorThread, FrameHub
from motor import Motor, DualMotor
from serial_connection import Serial

import time

DEBUG_MODE = True

# --- Arduino Serial Setup ---
try:
    serial_motor = Serial('/dev/arduino_uno-1', 115200)
    motorL = Motor(serial_motor); motorL.set_command_byte(0xA1); motorL.no_negative_speed = True
    motorR = Motor(serial_motor); motorR.set_command_byte(0xA2); motorR.no_negative_speed = True
    motor_dual = DualMotor(motorL, motorR)
    time.sleep(3)
    print("✅ Arduino connected")
except Exception as e:
    print("❌ Arduino connection failed:", e)
    serial_motor = None
    motor_dual = None
    motorL = DummyMotor("L")
    motorR = DummyMotor("R")

# --- Open Camera ---
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("無法開啟攝影機")
    exit(1)

# Line Following
line_follower = LineFollower(motorL, motorR)
step_count = StepCounter()

# Object detection
hub = FrameHub()
detector = DetectorThread(hub)
detector.start()

try:
    while True:
        try:
            ret, frame = cap.read()
            if ret:
                cap_frame = frame
            else:
                print("Video loading failed")
                break

            # Line Following
            line_follower.follow(frame)
            # Counting Step
            step_count.read_frame(frame)

            # 主程式送 frame 給辨識節點
            if not hub.new_frame:
                hub.update_frame(frame)
                pass
            else:
                # print("pending...")
                pass

            (avail, result) = hub.get_result()
            if avail:
                # 有偵測到物件
                print(f"Got result x {len(result)}")

            if cv2.waitKey(1) & 0xFF == 27:  # Esc 離開
                break
        except Exception as e:
            print("Error while doing main loop: ", e)
            break
finally:
    cap.release()
    cv2.destroyAllWindows()