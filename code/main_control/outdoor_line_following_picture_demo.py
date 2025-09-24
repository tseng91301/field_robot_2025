import cv2
from line_follow_outdoor import LineFollower
from line_follow_outdoor.DummyMotor import Motor

# --- 建立 DummyMotor ---
motorL = Motor(1)
motorR = Motor(2)

# --- 建立 LineFollower ---
follower = LineFollower(motorL, motorR)

# --- 讀取圖片 ---
img = cv2.imread("outdoor_line.png")
if img is None:
    print("讀取圖片失敗!")
    exit()

slope, offset, u = follower.read_frame(img, debug=True)


if slope is None:
    print("沒有偵測到紅線")
else:
    print(f"平均斜率: {slope:.3f}")
    print(f"平均 offset: {offset:.1f}")
    print(f"PID 控制輸出: {u:.3f}")

# --- 顯示 debug 視覺化 ---
print("按任意鍵關閉視窗")
# 等待按任意鍵
cv2.waitKey(0)
cv2.destroyAllWindows()