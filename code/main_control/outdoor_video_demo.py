import time
import cv2
from line_follow_outdoor import LineFollower
from line_follow_outdoor.DummyMotor import Motor

# --- 建立 DummyMotor ---
motorL = Motor(1)
motorR = Motor(2)

# --- 建立 LineFollower ---
follower = LineFollower(motorL, motorR)

# --- 開啟影片 ---
cap = cv2.VideoCapture("video/test_outdoor/right-1.mp4")
if not cap.isOpened():
    print("無法讀取影片!")
    exit()

while True:
    ret, frame = cap.read()
    if not ret:
        break  # 影片結束

    # --- 計算紅線偏移與斜率 ---
    slope, offset, u = follower.read_frame(frame, debug=True)

    if slope is None:
        print("沒有偵測到紅線")
    else:
        print(f"平均斜率: {slope:.3f}, 平均 offset: {offset:.1f}, PID 控制輸出: {u:.3f}")

    # --- 按 ESC 鍵退出 ---
    key = cv2.waitKey(1) & 0xFF
    if key == 27:  # ESC
        break

    time.sleep(0.05)

cap.release()
cv2.destroyAllWindows()
