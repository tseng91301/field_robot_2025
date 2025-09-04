import cv2
import numpy as np
import serial
import time

from motor import Motor, DualMotor

# PID 參數設定
kP = 0.1
kI = 0.0
kD = 0.0
e = 0.0
pe = 0.0
ie = 0.0

# 透視轉換的四個位置點(比例)，順序: 左上, 右上, 左下, 右下
pts_src_config = np.float32([[0.2, 0.15], [0.8, 0.15], [0.0, 1.0], [1.0, 1.0]])
pts_dst_config = np.float32([[0, 0], [1, 0], [0, 1], [1, 1]])

#Orin NX
# --- Arduino Serial Setup ---
try:
    serial_motor = serial.Serial('/dev/arduino_uno-1', 115200, timeout=1)
    motorL = Motor(serial_motor)
    motorL.set_command_byte(0xA1)
    motorR = Motor(serial_motor)
    motorR.set_command_byte(0xA2)
    motor_dual = DualMotor(motorL, motorR)
    # arduino = serial.Serial('/dev/ttyACM0', 115200, timeout=1)
    time.sleep(2)  # Give Arduino time to reset
    print("✅ Arduino connected")
except Exception as e:
    print("❌ Arduino connection failed:", e)
    arduino = None

# --- Open Camera ---
# cap = cv2.VideoCapture(0)
cap = cv2.VideoCapture("VID_20250904_211031.mp4")
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))

if not cap.isOpened():
    print("❌ Failed to open camera")
    exit()

def find_lane_center_with_slope(roi, y_offset, frame, lane_width=400):
    """
    單邊追蹤 + 斜率判斷左右線
    roi       : 二值化的車道區域
    y_offset  : ROI 在原圖的起始 y 座標
    frame     : 原圖，用來畫 debug
    lane_width: 假設車道寬度
    """
    contours, _ = cv2.findContours(roi, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    left_lines = []
    right_lines = []

    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        if w * h < 200:
            continue
        cx = x + w // 2
        cy = y + h // 2 + y_offset

        # 計算線的斜率
        if w != 0:
            slope = h / w  # 用矩形高/寬近似斜率
        else:
            slope = float('inf')

        # 判斷左右線
        if slope < 0.5:  # 假設左線斜率偏小（靠右傾斜）
            left_lines.append((cx, cy))
        else:
            right_lines.append((cx, cy))

        # 畫出中心點
        cv2.circle(frame, (cx, cy), 5, (0, 255, 0), -1)

    # 選最左邊和最右邊的線
    left_line = min(left_lines, key=lambda p: p[0]) if left_lines else None
    right_line = max(right_lines, key=lambda p: p[0]) if right_lines else None

    # 單邊追蹤補齊
    if left_line is None and right_line is not None:
        left_line = (right_line[0] - lane_width, right_line[1])
    if right_line is None and left_line is not None:
        right_line = (left_line[0] + lane_width, left_line[1])

    # 計算車道中心
    lane_center = None
    if left_line and right_line:
        lane_center = (left_line[0] + right_line[0]) // 2
        cy = (left_line[1] + right_line[1]) // 2
        cv2.circle(frame, (lane_center, cy), 6, (255, 0, 0), -1)

    return lane_center

cv2.namedWindow("Frame", cv2.WINDOW_NORMAL)
cv2.resizeWindow("Frame", 1280, 720)
while True:
    ret, frame = cap.read()
    if not ret:
        print("❌ Frame capture failed")
        break

    height, width, _ = frame.shape
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    # Red detection (HSV)
    lower_red1 = np.array([0, 100, 100])
    upper_red1 = np.array([8, 255, 255])
    lower_red2 = np.array([172, 100, 100])
    upper_red2 = np.array([180, 255, 255])

    mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
    mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
    mask = cv2.bitwise_or(mask1, mask2)

    # Morphology to reduce noise
    kernel = np.ones((5, 5), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    
    # --- 2. 透視變換 (Bird's-eye) ---
    # 假設已知四個角點，順序: 左上, 右上, 左下, 右下
    # 轉換成像素座標
    pts_src = np.zeros_like(pts_src_config)
    pts_src[:, 0] = pts_src_config[:, 0] * width  # x
    pts_src[:, 1] = pts_src_config[:, 1] * height  # y
    pts_dst = np.zeros_like(pts_dst_config)
    pts_dst[:, 0] = pts_dst_config[:, 0] * width  # x
    pts_dst[:, 1] = pts_dst_config[:, 1] * height  # y
    M = cv2.getPerspectiveTransform(pts_src, pts_dst)
    mask_bird = cv2.warpPerspective(mask, M, (width, height))

    # Regions of Interest (ROI)
    roi_near = mask_bird[int(height * 0.6):int(height * 0.8), :]
    roi_far = mask_bird[int(height * 0.3):int(height * 0.5), :]

    # Find lane centers
    # center_near = find_lane_center_with_slope(roi_near, int(height * 0.6), frame, (0, 255, 0))
    # center_far = find_lane_center_with_slope(roi_far, int(height * 0.3), frame, (0, 0, 255))
    center_near = find_lane_center_with_slope(roi_near, int(height * 0.6), frame, 400)
    center_far = find_lane_center_with_slope(roi_far, int(height * 0.3), frame, 400)

    print("center_near: ", center_near)
    print("center_far: ", center_far)

    if center_near and center_far:
        # Insert PID value
        e = center_far - center_near
        ie += e
        d = e - pe
        pe = e
        val = int(kP * e + kI * ie + kD * d)

        # motor_dual.set_direction(val)

        print("賽道方向:", val)

    # Debug display (enable if you have GUI)
    cv2.imshow("Frame", frame)
    # cv2.imshow("Mask", mask)
    if cv2.waitKey(1) & 0xFF == 27:  # ESC to quit
        break

    while True:
        if cv2.waitKey(1) & 0xFF == 13:  
            break


cap.release()
cv2.destroyAllWindows()
if serial_motor:
    serial_motor.close()

