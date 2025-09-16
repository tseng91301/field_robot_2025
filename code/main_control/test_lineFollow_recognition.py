import cv2

from line_follow import LineFollower, DummyMotor, StepCounter
from object_detection import DetectorThread, FrameHub
from motor import Motor, DualMotor
from feeding_cup import FeedingCup
from serial_connection import Serial

from level_vars import Level1, Level2

from collections import Counter

import time

from rich.live import Live
from rich.table import Table

DEBUG_MODE = False
SERIAL_SIMULATION_MODE = True
SERIAL_PORT_MOTOR = "/dev/arduino_uno-1"
SERIAL_PORT_CUP = "/dev/arduino_uno-2"

# 定義每一關之中要看那些東西
LOOK_OBJECTS_1 = ["chick", "pig", "cow"]
LOOK_OBJECTS_2 = ["machine"]
look_object_3 = [""] # 依據第一關看到的東西去設定

# 定義每個關卡的特定變數和功能
level1 = Level1()
level1.now_detected_obj = LOOK_OBJECTS_1[0] # 先設定一個預設值，讓後面有保底
level2 = Level2()

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
    cup = FeedingCup(serial_cup)
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
            main_inf_table = Table(title="Field Robot Indoor Challenge")
            main_inf_table.add_column("Title", style="cyan", no_wrap=True)
            main_inf_table.add_column("Value", style="magenta")
            detection_table = Table(title="Object Detection")
            detection_table.add_column("Label", style="cyan", no_wrap=True)
            detection_table.add_column("Count", style="magenta")
            try:
                ret, frame = cap.read()
                if ret:
                    cap_frame = frame
                else:
                    print("❌ Video loading failed")
                    break

                # Line Following
                angle_avg, offset_avg, u = line_follower.follow(frame)
                main_inf_table.add_row("Offset", str(offset_avg))
                main_inf_table.add_row("Angle", str(angle_avg))
                main_inf_table.add_row("Calibrate direction", str(u))
                # Counting Step
                step_count.read_frame(frame)
                main_inf_table.add_row("Now Level", str(step_count.level))

                # 設定每一關要看的東西，以及其他相關參數
                if step_count.level == 1: # 動物辨識關卡
                    detector.set_detect_objects(LOOK_OBJECTS_1)
                    if level1.finish_looking and not level1.light_triggered:
                        obj = level1.manual_finish()
                        light_number = LOOK_OBJECTS_1.index(obj) + 1 # 指定要亮的燈號
                        cup.set_led(light_number) # 讓 arduino 亮燈
                        level1.light_triggered = True

                elif step_count.level == 2: # 機器辨識關卡
                    level2.frame_w = frame.shape[1]
                    level2.frame_h = frame.shape[0]
                    detector.set_detect_objects(LOOK_OBJECTS_2)
                    look_object_3 = [level1.manual_finish()]

                live.update(main_inf_table) # 更新表格

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
                    # 更新 object detection 表格
                    detection_table.add_row("All", str(len(result)))
                    labels = [b[4] for b in result]
                    label_cnt = Counter(labels)
                    for label, cnt in label_cnt.items():
                        detection_table.add_row(label, str(cnt))
                    live.update(detection_table)
                    # 依照物件的 confidence 做排序
                    result.sort(key=lambda x: x[5], reverse=True)
                    if not level1.finish_looking:
                        level1.look_obj(result[0][4])
                    if level1.finish_looking or step_count.level == 2:
                        level2.get_obj(result[0])
                    

                # print(f"\rObject detection got {len(result)} result(s)\033[K", end="", flush=True)
                if avail:
                    
                    pass

                if cv2.waitKey(1) & 0xFF == 27:  # Esc 離開
                    break
            except Exception as e:
                print("❌ Error while doing main loop: ", e)
                break

finally:
    cap.release()
    cv2.destroyAllWindows()