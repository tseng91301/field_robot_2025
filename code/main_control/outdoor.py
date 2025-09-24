import cv2
import numpy as np
import time
import traceback
from motor import Motor, DualMotor
from serial_connection import Serial

# --- PID 參數設定 ---
kP = 0.6
kI = 0.001
kD = 0.01

LINE_OFFSET = 0
SERIAL_SIMULATION_MODE = False

pe, ie = 0.0, 0.0

# --- 透視轉換比例座標 ---
pts_src_config = np.float32([[0.0, 0.25], [1.0, 0.25], [0.0, 1.0], [1.0, 1.0]])
bird_width, bird_height = 600, 400
pts_dst = np.float32([[0,0],[bird_width,0],[0,bird_height],[bird_width,bird_height]])

# --- Arduino Serial Setup ---
try:
    serial_motor = Serial('/dev/arduino_uno-1', 115200, simulate=SERIAL_SIMULATION_MODE)
    motorL = Motor(serial_motor); motorL.set_command_byte(0xA1); motorL.no_negative_speed = True
    motorR = Motor(serial_motor); motorR.set_command_byte(0xA2); motorR.no_negative_speed = True
    motor_dual = DualMotor(motorL, motorR)
    time.sleep(1)
    print("✅ Arduino connected")
except Exception as e:
    print("❌ Arduino connection failed:", e)
    serial_motor = None
    motor_dual = None

# --- Open Camera ---
cap = cv2.VideoCapture("/dev/webcam_outdoor")
#cap = cv2.VideoCapture("1757656904112.mp4")
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))

# -- 設定影像擷取高度比例 --
FRAME_HEIGHT_CROP_RATE = 0.55

# --- 設定影片輸出 ---
fourcc = cv2.VideoWriter_fourcc(*'mp4v')
fps = 20
frame_width, frame_height = 1280, int(720 * FRAME_HEIGHT_CROP_RATE)  # 因為只取下半影像
out_frame = cv2.VideoWriter('output/video/outdoor_output_frame.mp4', fourcc, fps, (frame_width, frame_height))
out_mask = cv2.VideoWriter('output/video/outdoor_output_mask.mp4', fourcc, fps, (bird_width, bird_height), isColor=False)
if not out_frame.isOpened():
    raise RuntimeError("VideoWriter failed to open. Check path, codec and frame size!")

lane_width = 250
window_size = 5
motor_dual.speed = 0.35

try:
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        height, width, _ = frame.shape
        frame_crop = frame[int(height*FRAME_HEIGHT_CROP_RATE):, :]
        height_crop = frame_crop.shape[0]
        hsv = cv2.cvtColor(frame_crop, cv2.COLOR_BGR2HSV)

        # --- 紅色遮罩 ---
        lower_red1 = np.array([0, 100, 100]); upper_red1 = np.array([8, 255, 255])
        lower_red2 = np.array([172, 100, 100]); upper_red2 = np.array([180, 255, 255])
        mask = cv2.inRange(hsv, lower_red1, upper_red1) | cv2.inRange(hsv, lower_red2, upper_red2)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((5,5),np.uint8))

        # --- 透視轉換 ---
        pts_src = np.zeros_like(pts_src_config)
        pts_src[:,0] = pts_src_config[:,0]*width
        pts_src[:,1] = pts_src_config[:,1]*height_crop
        M = cv2.getPerspectiveTransform(pts_src, pts_dst)
        mask_bird = cv2.warpPerspective(mask, M, (bird_width, bird_height))

        # --- 掃描每行取左右邊界 + 中點 ---
        centers = []
        last_x_left, last_x_right = 0, bird_width
        for y in range(mask_bird.shape[0]-1, -1, -1):
            row = mask_bird[y, :]
            xs = np.where(row > 0)[0]
            if len(xs) == 0:
                x_center = (last_x_left + last_x_right)/2
            else:
                x_left, x_right = xs[0], xs[-1]
                if abs(x_left - x_right) < 55:
                    last_x_dist = abs(last_x_left - last_x_right)
                    if abs(x_left - last_x_left) < abs(x_right - last_x_right):
                        x_center = x_left + last_x_dist // 2
                        x_right = x_left + last_x_dist
                    else:
                        x_center = x_right - last_x_dist // 2
                        x_left = x_right - last_x_dist
                else:
                    x_center = (x_left + x_right)/2
                last_x_left = x_left
                last_x_right = x_right
            centers.append((x_center, y))

        centers = np.array(centers[::-1], dtype=np.float32)

        # --- 局部滑動平均 ---
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
                cv2.line(frame_crop, tuple(pts_back[i-1][0]), tuple(pts_back[i][0]), (0,255,0), 2)

            # --- PID 控制 ---
            x_avg = np.mean(centers_smooth[:,0])
            error = x_avg - bird_width//2 - LINE_OFFSET
            de = error - pe
            ie += error
            ie = max(min(ie, 1000), -1000)
            pe = error
            output = -(kP*error + kI*ie + kD*de)
            if motor_dual:
                motor_dual.set_direction(output)

        # --- 顯示與存檔 ---
        cv2.imshow("Frame", frame_crop)
        cv2.imshow("Red Mask", mask_bird)
        out_frame.write(frame_crop)
        out_mask.write(mask_bird)

        if cv2.waitKey(1) & 0xFF == 27:  #press ESC
            break

except Exception as e:
    import traceback
    print("❌ Error while doing main loop:")
    print("Error type:", type(e).__name__)
    print("Error message:", str(e))
    traceback.print_exc()
    tb = traceback.extract_tb(e.__traceback__)
    for filename, lineno, func, text in tb:
        print(f"Filename: {filename}, Line: {lineno}, Function: {func}, Code: {text}")

finally:
    print("🧹 Releasing resources...")
    cap.release()
    out_frame.release()
    out_mask.release()
    cv2.destroyAllWindows()
    if serial_motor:
        serial_motor.close()
    print("✅ Finished and saved videos.")
