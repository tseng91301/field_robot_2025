import cv2
import numpy as np
import serial
import time
from motor import Motor, DualMotor

# --- PID 參數設定 ---
kP = 0.1 # TODO: 更改數值
kI = 0.0 # TODO: 更改數值
kD = 0.0 # TODO: 更改數值

pe, ie = 0.0, 0.0

# --- 透視轉換的比例座標 ---
pts_src_config = np.float32([[0.2, 0.15], [0.8, 0.15], [0.0, 1.0], [1.0, 1.0]])
bird_width, bird_height = 400, 400
pts_dst = np.float32([[0,0],[bird_width,0],[0,bird_height],[bird_width,bird_height]])

# --- Arduino Serial Setup ---
try:
    serial_motor = serial.Serial('/dev/arduino_uno-1', 115200, timeout=1)
    motorL = Motor(serial_motor); motorL.set_command_byte(0xA1); motorL.no_negative_speed = True
    motorR = Motor(serial_motor); motorR.set_command_byte(0xA2); motorR.no_negative_speed = True
    motor_dual = DualMotor(motorL, motorR)
    time.sleep(2)
    print("✅ Arduino connected")
except Exception as e:
    print("❌ Arduino connection failed:", e)
    serial_motor = None
    motor_dual = None

# --- Open Camera ---
# cap = cv2.VideoCapture("VID_20250904_211031.mp4")
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))

last_x_left = None
lane_width = 200  # bird’s-eye view 車道寬度像素
window_size = 5   # 局部滑動平均範圍

motor_dual.speed = 1.0

while True:
    ret, frame = cap.read()
    if not ret:
        break

    height, width, _ = frame.shape
    # --- 限制只取 y=0.5 以下 ---
    frame = frame[int(height*0.5):, :]
    height = frame.shape[0]  # 更新高度，後面處理需要用
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    # --- 紅色遮罩 ---
    # TODO 修改數值讓他能在草皮上看到紅繩
    lower_red1 = np.array([0, 100, 100]); upper_red1 = np.array([8, 255, 255])
    lower_red2 = np.array([172, 100, 100]); upper_red2 = np.array([180, 255, 255])
    mask = cv2.inRange(hsv, lower_red1, upper_red1) | cv2.inRange(hsv, lower_red2, upper_red2)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((5,5),np.uint8))

    # --- 透視轉換 ---
    pts_src = np.zeros_like(pts_src_config)
    pts_src[:,0] = pts_src_config[:,0]*width
    pts_src[:,1] = pts_src_config[:,1]*height
    M = cv2.getPerspectiveTransform(pts_src, pts_dst)
    mask_bird = cv2.warpPerspective(mask, M, (bird_width, bird_height))

    # --- 掃描每行取左右邊界 + 中點 (由底部向上) ---
    centers = []
    last_x_left, last_x_right = 0, 400

    for y in range(mask_bird.shape[0]-1, -1, -1):  # 底部到上方
        row = mask_bird[y, :]
        xs = np.where(row > 0)[0]

        if len(xs) == 0:
            # 沒偵測到紅線，用上一行中點
            if last_x_left is not None and last_x_right is not None:
                x_center = (last_x_left + last_x_right)/2
                centers.append((x_center, y))
            else:
                x_center = 400//2
                centers.append((x_center, y))
        else:
            x_left = xs[0]; x_right = xs[-1]
            if abs(x_left - x_right < 25): # 可能指偵測到其中一邊
                if last_x_left is not None and last_x_right is not None:
                    last_x_dist = abs(last_x_left - last_x_right)
                    if abs(x_left - last_x_left) < abs(x_right - last_x_right): # 只偵測到左邊
                        x_center = x_left + last_x_dist // 2
                        x_right = x_left + last_x_dist
                    else: # 只偵測到右邊
                        x_center = x_right - last_x_dist // 2
                        x_left = x_right - last_x_dist
                    pass
                else:
                    x_center = x_center = 400//2
                centers.append((x_center, y))
            else:
                x_center = (x_left + x_right)/2
                centers.append((x_center, y))
            last_x_left = x_left
            last_x_right = x_right

    # 由於是從底部往上掃，最後要反轉順序
    centers = centers[::-1]
    centers = np.array(centers, dtype=np.float32)

    # --- 局部滑動平均平滑中線 ---
    centers_smooth = []
    for i in range(len(centers)):
        start = max(0, i - window_size)
        end = min(len(centers), i + window_size)
        avg_x = np.mean(centers[start:end,0])
        centers_smooth.append((avg_x, centers[i,1]))
    centers_smooth = np.array(centers_smooth, dtype=np.float32)

    # --- 逆透視回原圖並畫中線 ---
    if len(centers_smooth) > 0:
        Minv = cv2.getPerspectiveTransform(pts_dst, pts_src)
        pts_back = cv2.perspectiveTransform(centers_smooth.reshape(-1,1,2), Minv).astype(int)
        for i in range(1, len(pts_back)):
            cv2.line(frame, tuple(pts_back[i-1][0]), tuple(pts_back[i][0]), (0,255,0), 2)

        # --- PID 控制 ---
        # --- PID 控制 (改用 centers_smooth 全部平均) ---
        if len(centers_smooth) > 0:
            # 取所有 x_center 的平均
            x_avg = np.mean(centers_smooth[:,0])

            # error = 平均中線 - 200 (假設 200 是車道中間)
            error = x_avg - 200

            de = error - pe
            ie += error
            pe = error
            output = -(kP*error + kI*ie + kD*de)

            if motor_dual:
                motor_dual.set_direction(output)

    cv2.imshow("Frame", frame)
    cv2.imshow("Red Mask", mask)
    if cv2.waitKey(1) & 0xFF == 27:
        break

    time.sleep(0.05)
    # while True:
    #     if cv2.waitKey(1) & 0xFF == 13:
    #         break

cap.release()
cv2.destroyAllWindows()
if serial_motor:
    serial_motor.close()