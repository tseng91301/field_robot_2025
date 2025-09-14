import cv2

from line_follow import LineFollower, DummyMotor, StepCounter
from object_detection import DetectorThread, FrameHub
from motor import Motor, DualMotor
from serial_connection import Serial

from collections import Counter

import time

from rich.live import Live
from rich.table import Table

DEBUG_MODE = False
SERIAL_SIMULATION_MODE = True
SERIAL_PORT_MOTOR = "/dev/arduino_uno-1"
SERIAL_PORT_CUP = "/dev/arduino_uno-2"

# --- Arduino Serial Setup ---
try:
    # initialize motor serial connection
    serial_motor = Serial(SERIAL_PORT_MOTOR, 115200, simulate=SERIAL_SIMULATION_MODE)
    serial_motor.print_results = DEBUG_MODE
    motorL = Motor(serial_motor); motorL.set_command_byte(0xA1); motorL.no_negative_speed = True
    motorR = Motor(serial_motor); motorR.set_command_byte(0xA2); motorR.no_negative_speed = True
    motor_dual = DualMotor(motorL, motorR)
    print("✅ Serial motor connected")
    # initialize cup serial connection
    serial_cup = Serial(SERIAL_PORT_CUP, 115200, simulate=SERIAL_SIMULATION_MODE)
    serial_cup.print_results = DEBUG_MODE
    print("✅ Serial cup connected")
    time.sleep(3)
    print("Finish Arduino Initialization")
except Exception as e:
    raise Exception("❌ Arduino connection failed:", e)

# --- Open Camera ---
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    raise Exception("❌ Failed to open camera")

# Line Following
line_follower = LineFollower(motorL, motorR)
step_count = StepCounter()

# Object detection
hub = FrameHub()
detector = DetectorThread(hub)
detector.start()

try:
    with Live(refresh_per_second=10) as live:
        while True:
            # 初始化輸出表格
            detection_table = Table(title="Object Detection")
            detection_table.add_column("Object", style="cyan", no_wrap=True)
            detection_table.add_column("Number", style="magenta")
            try:
                ret, frame = cap.read()
                if ret:
                    cap_frame = frame
                else:
                    print("❌ Video loading failed")
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
                    detection_table.add_row("All", str(len(result)))
                    labels = [b[4] for b in result]
                    label_cnt = Counter(labels)
                    for label, cnt in label_cnt.items():
                        detection_table.add_row(label, str(cnt))
                    live.update(detection_table)

                # print(f"\rObject detection got {len(result)} result(s)\033[K", end="", flush=True)
                if avail:
                    # 有偵測到物件
                    pass

                if cv2.waitKey(1) & 0xFF == 27:  # Esc 離開
                    break
            except Exception as e:
                print("❌ Error while doing main loop: ", e)
                break

finally:
    cap.release()
    cv2.destroyAllWindows()