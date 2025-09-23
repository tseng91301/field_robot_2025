import cv2
import time
import signal
import sys
import traceback

from line_follow import LineFollower, StepCounter
from motor import Motor, DualMotor
from serial_connection import Serial

DEBUG_MODE = False
SERIAL_PORT_MOTOR = "/dev/arduino_uno-1"
CAMERA_OUTDOOR_PATH = "1757656793512.mp4"
# CAMERA_OUTDOOR_PATH = 0  # 如果要用筆電內建攝像頭可以改成 0

# --- Arduino Serial Setup ---
try:
    serial_motor = Serial(SERIAL_PORT_MOTOR, 115200, simulate=True)
    serial_motor.print_results = DEBUG_MODE

    motorL = Motor(serial_motor)
    motorL.set_command_byte(0xA1)
    motorL.no_negative_speed = True

    motorR = Motor(serial_motor)
    motorR.set_command_byte(0xA2)
    motorR.no_negative_speed = True

    motor_dual = DualMotor(motorL, motorR)

    print("✅ Serial motor connected")
    time.sleep(2)
    print("Finish Arduino Initialization")

except Exception as e:
    raise Exception("❌ Arduino connection failed:", e)

# --- Open Camera ---
cap_line_follow = cv2.VideoCapture(CAMERA_OUTDOOR_PATH)
cap_line_follow.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap_line_follow.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
cap_line_follow.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))

if not cap_line_follow.isOpened():
    raise Exception(f"❌ Failed to open camera ({CAMERA_OUTDOOR_PATH})")

# --- Line Following ---
line_follower = LineFollower(motorL, motorR)

# --- Clean up ---
def cleanUp(_, __):
    print("Turnning off the motor...")
    motorL.set_speed(0)
    motorR.set_speed(0)
    if serial_motor:
        serial_motor.close()
    cap_line_follow.release()
    cv2.destroyAllWindows()
    print("Process terminated safely.")
    sys.exit(0)

signal.signal(signal.SIGINT, cleanUp)   # Ctrl+C
signal.signal(signal.SIGTERM, cleanUp)  # kill

try:
    while True:
        ret, frame = cap_line_follow.read()
        if not ret:
            print("❌ Video (Line Follow) loading failed")
            break

        # 呼叫循線邏輯
        angle_avg, offset_avg, u = line_follower.follow(frame)

        # 可以在終端機印出 debug 資訊
        print(f"[Line Follow] Offset={offset_avg:.2f}, Angle={angle_avg:.2f}, Control={u}")
        time.sleep(0.02)

        # 按下 ESC 離開
        if cv2.waitKey(1) & 0xFF == 27:
            break

except Exception as e:
    print("❌ Error while running line follow: ")
    print("Error type:", type(e).__name__)
    print("Error message:", str(e))
    traceback.print_exc()

finally:
    cleanUp(None, None)
