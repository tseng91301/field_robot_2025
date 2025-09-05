import cv2
import numpy as np
import serial
import time

# -------------------
# --- Arduino Setup ---
# -------------------
try:
    arduino = serial.Serial('/dev/ttyACM0', 115200, timeout=1)
    time.sleep(2)  # 給 Arduino reset
    print("✅ Arduino connected")
except Exception as e:
    print("❌ Arduino connection failed:", e)
    exit()

# -------------------
# --- Motor Class ---
# -------------------
class MotorDual:
    def __init__(self, ser, command_byte=0x01):
        self.ser = ser
        self.command_byte = command_byte
        self.speed = 0

    def set_speed(self, speed: int):
        if speed > 255:
            speed = 255
        elif speed < -255:
            speed = -255
        self.speed = speed

        outp = bytearray()
        outp.append(self.command_byte)
        outp.append(0x01 if self.speed < 0 else 0x00)
        outp.append(int(abs(self.speed)))
        self.ser.write(bytes(outp))

# 初始化馬達
motor_dual = MotorDual(arduino)

# -------------------
# --- PID Parameters ---
# -------------------
Kp = 0.5
Ki = 0.01
Kd = 0.1
pe = 0
ie = 0

# -------------------
# --- Video Capture ---
# -------------------
cap = cv2.VideoCapture(0)  # 攝影機 ID
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
if not cap.isOpened():
    print("❌ Camera not found")
    exit()

# -------------------
# --- Main Loop ---
# -------------------
while True:
    ret, frame = cap.read()
    if not ret:
        break

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 120, 255, cv2.THRESH_BINARY_INV)

    # 找輪廓
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    centers = []

    for cnt in contours:
        M = cv2.moments(cnt)
        if M["m00"] != 0:
            cx = int(M["m10"]/M["m00"])
            cy = int(M["m01"]/M["m00"])
            centers.append((cx, cy))

    centers = np.array(centers, dtype=np.float32)
    centers_smooth = []

    # 簡單平滑
    if len(centers) > 0:
        window_size = 3
        for i in range(len(centers)):
            start = max(0, i - window_size)
            end = min(len(centers), i + window_size)
            avg_x = np.mean(centers[start:end, 0])
            centers_smooth.append((avg_x, centers[i, 1]))
        centers_smooth = np.array(centers_smooth, dtype=np.float32)

    # -------------------
    # --- Draw Line ---
    # -------------------
    if len(centers_smooth) > 0:
        for i in range(1, len(centers_smooth)):
            cv2.line(frame,
                     tuple(centers_smooth[i-1].astype(int)),
                     tuple(centers_smooth[i].astype(int)),
                     (0, 255, 0), 2)

    # -------------------
    # --- PID Control ---
    # -------------------
    if len(centers_smooth) > 0:
        x_avg = np.mean(centers_smooth[:, 0])
        error = x_avg - 200  # 假設中線在 X=200

        de = error - pe
        ie += error
        pe = error

        output = Kp * error + Ki * ie + Kd * de
        output = int(max(min(output, 255), -255))  # 限制速度範圍

        motor_dual.set_speed(output)

    # -------------------
    # --- Show Frame (optional headless: 可註解掉) ---
    # -------------------
    # cv2.imshow("Frame", frame)
    # if cv2.waitKey(1) & 0xFF == ord('q'):
    #     break

cap.release()
# cv2.destroyAllWindows()
