import cv2

from line_follow import LineFollower
from line_follow import StepCounter
from object_detection import DetectorThread, FrameHub
from motor import Motor, DualMotor
from feeding_cup import FeedingCup
from serial_connection import Serial

from level_vars import Level1, Level2, Level3

from collections import Counter
import signal
import sys
import time
import asyncio

# 顯示表格
from rich.live import Live
from rich.table import Table
from rich.layout import Layout

# 錯誤資訊處理
import traceback

DEBUG_MODE = False
SERIAL_SIMULATION_MODE = False
SERIAL_PORT_MOTOR = "/dev/arduino_uno-1"
SERIAL_PORT_CUP = "/dev/arduino_uno-2"
CAMERA_OUTDOOR_PATH = "/dev/webcam_outdoor"
CAMERA_INDOOR_PATH = "/dev/webcam_indoor"
# CAMERA_OUTDOOR_PATH = 0
# CAMERA_INDOOR_PATH = 0

# 定義每一關之中要看那些東西
LOOK_OBJECTS_1 = ["chick", "pig", "cow"]
# LOOK_OBJECTS_1 = ["chicken", "pig", "cows"]
LOOK_OBJECTS_2 = ["machine"]
look_object_3 = [""] # 依據第一關看到的東西去設定
ANIMAL_FEEDING_WEIGHT = {"chick": 75, "pig": 155, "cow": 205} # 每一種動物需要的飼料重量

# 定義每個關卡的特定變數和功能
level1 = Level1(); level1.look_objects = LOOK_OBJECTS_1
level1.now_detected_obj = LOOK_OBJECTS_1[0] # 先設定一個預設值，讓後面有保底
level2 = Level2(); level2.look_objects = LOOK_OBJECTS_2
level3 = Level3(); level3.look_objects = look_object_3

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
    cup = FeedingCup(serial_cup); cup.set_command_byte(0x00, 0xB2, 0xB1, 0xB3,0xB4)
    print("✅ Serial cup connected")
    time.sleep(3)
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

cap_object_detection = cv2.VideoCapture(CAMERA_INDOOR_PATH)
cap_object_detection.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap_object_detection.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
cap_object_detection.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))

if not cap_object_detection.isOpened():
    raise Exception(f"❌ Failed to open camera ({CAMERA_INDOOR_PATH})")

# Line Following
line_follower = LineFollower(motorL, motorR)
step_count = StepCounter()

# Object detection
hub = FrameHub()
detector = DetectorThread(hub)
detector.start()

# 程式結束時的釋放資源
def cleanUp(_, __):
    # print(_)
    # print(__)
    print("Turnning off the motor...")
    motorL.set_speed(0)
    motorR.set_speed(0)
    if serial_motor:
        serial_motor.close()
    if serial_cup:
        serial_cup.close()
    cap_object_detection.release()
    cap_line_follow.release()
    cv2.destroyAllWindows()
    print("Process has been terminated safely with value 0.")
    return
signal.signal(signal.SIGINT, cleanUp)  # 捕獲 Ctrl+C
signal.signal(signal.SIGTERM, cleanUp)  # 捕獲終止信號

try:
    motorL.turn_on(1)
    motorR.turn_on(1)
    with Live(refresh_per_second=10) as live:
        while True:
            # 初始化輸出表格
            layout = Layout()
            layout.split_row(
                Layout(name="left"),
                Layout(name="right")
            )
            main_inf_table = Table(title="Field Robot Indoor Challenge")
            main_inf_table.add_column("Title", style="cyan", no_wrap=True)
            main_inf_table.add_column("Value", style="magenta")
            detection_table = Table(title="Object Detection")
            detection_table.add_column("Label", style="cyan", no_wrap=True)
            detection_table.add_column("Count", style="magenta")
            #try:
            ret_line_follow, frame_line_follow = cap_line_follow.read()
            if ret_line_follow:
                pass
            else:
                print("❌ Video (Line Follow) loading failed")
                break

            ret_object_detection, frame_object_detection = cap_object_detection.read()
            if ret_object_detection:
                pass
            else:
                print("❌ Video (Object detection) loading failed")
                break

            # Line Following
            # angle_avg, offset_avg, u = line_follower.follow(frame_line_follow)
            angle_avg, offset_avg, u = 0, 0, 0
            main_inf_table.add_row("Offset", str(offset_avg))
            main_inf_table.add_row("Angle", str(angle_avg))
            main_inf_table.add_row("Calibrate direction", str(u))
            # Counting Step
            # step_count.read_frame(frame_line_follow)
            main_inf_table.add_row("Now Level", str(step_count.level))

            # 設定每一關要看的東西，以及其他相關參數
            if step_count.level == 1: # 動物辨識關卡
                detector.set_detect_objects(LOOK_OBJECTS_1)
                if level1.finish_looking and not level1.light_triggered:
                    obj = level1.manual_finish()
                    look_object_3 = [obj] # 設定第三關要看的東西
                    level3.look_objects = [obj]
                    light_number = LOOK_OBJECTS_1.index(obj) + 1 # 指定要亮的燈號
                    print(f"Light Number: {light_number}")
                    # line_follower.switch(False)
                    motorL.turn_on(0); motorR.turn_on(0)
                    cup.set_animal_led_wait(light_number) # 讓 arduino 亮燈
                    print("already finished led")
                    # line_follower.switch(True)
                    motorL.turn_on(1); motorR.turn_on(1)
                    level1.light_triggered = True
                    step_count.level = 2
                    detector.set_detect_objects(LOOK_OBJECTS_2)
                    detector.del_result()

            elif step_count.level == 2: # 機器辨識關卡
                level2.frame_w = frame_object_detection.shape[1]
                level2.frame_h = frame_object_detection.shape[0]
                # line_follower.switch(False if level2.stop else True)
                time.sleep(14)
                # time.sleep(10)
                # if level2.machine_available and not level2.used_machine:
                if True:
                    print("Level2: Using machine")
                    # line_follower.switch(False)
                    motorL.turn_on(0); motorR.turn_on(0)
                    # 之後更改成觸發飼料機的程式，這裡用閃兩下代替
                    cup.set_led(1)
                    time.sleep(0.2)
                    cup.set_led(0)
                    time.sleep(0.2)
                    cup.set_led(1)
                    time.sleep(0.2)
                    cup.set_led(0)
                    time.sleep(0.2)
                    # asyncio.run(cup.feed(ANIMAL_FEEDING_WEIGHT[look_object_3[0]]))
                    # line_follower.switch(True)
                    motorL.turn_on(1); motorR.turn_on(1)
                    level2.used_machine = True
                    print("Machine used successfully!")
                    step_count.level = 3
                    detector.set_detect_objects(look_object_3)
                    detector.del_result()
                    level3.look_objects = look_object_3

            elif step_count.level == 3: # 動物飼料放置關卡
                level3.frame_w = frame_object_detection.shape[1]
                level3.frame_h = frame_object_detection.shape[0]
                # line_follower.switch(False if level3.stop else True)
                if level3.animal_available and not level3.fed_animal:
                    print("Level3: Feeding...")
                    # line_follower.switch(False)
                    motorL.turn_on(0); motorR.turn_on(0)
                    obj = level1.manual_finish() #notice
                    light_number = LOOK_OBJECTS_1.index(obj) + 1
                    cup.set_animal_led_wait(light_number, 3) # 讓 arduino 亮燈
                    time.sleep(3)# 之後更改成餵養動物的程式
                    # line_follower.switch(True)
                    motorL.turn_on(1); motorR.turn_on(1)
                    level3.fed_animal = True
                    print("Feed successfully!")
                    step_count.level += 1

            # 主程式送 frame 給辨識節點
            if not hub.new_frame:
                hub.update_frame(frame_object_detection)
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
                # 有進行辨識才更新物件辨識表格
                layout["right"].update(detection_table)
                # 依照物件的 confidence 做排序
                result.sort(key=lambda x: x[5], reverse=True)
                if len(result)>0:
                    if step_count.level == 1:
                        # Level 1: 藉由結果來查看動物種類
                        level1.look_obj(result[0][4])
                    if step_count.level == 2:
                        # Level 2: 藉由結果去看機器現在的偏離量
                        offset = level2.get_obj(result[0])
                        main_inf_table.add_row("Level 2 machine offset", str(offset))
                    if step_count.level == 3:
                        # Level 3: 藉由結果去看動物目標位置
                        offset = level3.get_obj(result[0])
                        main_inf_table.add_row("Level 3 animal offset", str(offset))

            # 更新主要資訊表格
            layout["left"].update(main_inf_table)
            # 更新所有表格
            live.update(layout)

            if cv2.waitKey(1) & 0xFF == 27:  # Esc 離開
                break

except Exception as e:
    print("❌ Error while doing main loop: ")
    print("Error type:", type(e).__name__)
    print("Error message:", str(e))

    # 印出完整錯誤堆疊
    traceback.print_exc()

    # 或取得錯誤發生位置（檔案、行號等）
    tb = traceback.extract_tb(e.__traceback__)
    for filename, lineno, func, text in tb:
        print(f"Filename: {filename}, Line: {lineno}, Function: {func}, Code: {text}")

finally:
    cleanUp(None, None)


