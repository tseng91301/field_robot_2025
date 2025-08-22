import cv2
import numpy as np
import time
from collections import deque
from math import atan2, pi

# =========================
# 參數區（依需求可調）
# =========================
ROI_BOTTOM_START = 0.60   # 從畫面高度的 60% 開始（0~1）
ROI_HEIGHT_RATIO = 0.30   # ROI 高度佔整畫面的 30%（0~1）

# HSV 紅色閾值（兩段）
H_LOW1  = np.array([0,   90,  80])   # 視情況調 S/V 閾值（避免陰影/反光）
H_HIGH1 = np.array([10, 255, 255])
H_LOW2  = np.array([170, 90,  80])
H_HIGH2 = np.array([180, 255, 255])

KERNEL_SIZE = 5          # 形態學去噪
MIN_AREA    = 300        # 最小紅色區塊像素面積（過小視為噪音）

# PID 權重與係數
W_ANGLE  = 0.7           # 角度誤差權重
W_OFFSET = 0.3           # 位置誤差權重（兩者加總為 1 較直覺）

KP = 180.0               # 比例增益（可依車體/速度調整）
KI = 0.0                 # 積分增益（先從 0 開始，避免積分飄移）
KD = 60.0                # 微分增益
INTEGRAL_CLAMP = 0.5     # 限制積分項的幅度（-0.5 ~ 0.5）

BASE_SPEED = 100         # 你的例子：兩輪基準速度 100
MAX_SPEED  = 255         # 馬達速度上限（含負值）

# 平滑：保存最近 N 個角度/偏移
SMOOTH_N = 5

# 找不到線時策略
NO_LINE_BRAKE = True     # True：煞停；False：維持基準速度直行或保留上次控制量

# 視覺化除錯
SHOW_DEBUG = True


# =========================
# 馬達控制（請換成你的實作）
# =========================
class DummyMotor:
    def set_speed(self, v):
        # 這裡只打印，實機請送到你的馬達驅動
        print(f"{self.__class__.__name__}: {int(v)}")

motorL = DummyMotor()
motorR = DummyMotor()

def clamp(v, lo, hi):
    return max(lo, min(hi, v))

def proportional_roi(frame, bottom_start_ratio=ROI_BOTTOM_START, height_ratio=ROI_HEIGHT_RATIO):
    h, w = frame.shape[:2]
    y1 = int(h * bottom_start_ratio)
    y2 = int(h * min(1.0, bottom_start_ratio + height_ratio))
    roi = frame[y1:y2, 0:w]
    return roi, (0, y1, w, y2 - y1)  # ROI 與其在原圖的位置（x, y, w, h）

def red_mask_hsv(bgr):
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    mask1 = cv2.inRange(hsv, H_LOW1, H_HIGH1)
    mask2 = cv2.inRange(hsv, H_LOW2, H_HIGH2)
    mask = cv2.bitwise_or(mask1, mask2)
    # 形態學去噪
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (KERNEL_SIZE, KERNEL_SIZE))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, k)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, k)
    return mask

def find_line_angle_and_offset(mask):
    """
    回傳：
      angle_rad: 線方向相對 x 軸的角度（-pi/2 ~ +pi/2）
      offset_norm: 紅色線的「水平質心相對 ROI 中心」的歸一化偏移（-1 ~ +1）
      cx, cy: 質心座標（像素；ROI 座標系）
    若找不到，回傳 (None, None, None, None)
    """
    # 面積過小則直接判斷為沒線
    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    areas = [cv2.contourArea(c) for c in cnts]
    if len(areas) == 0 or max(areas) < MIN_AREA:
        return None, None, None, None

    # 取最大連通區塊（更穩定）
    c = cnts[int(np.argmax(areas))]
    area = cv2.contourArea(c)
    if area < MIN_AREA:
        return None, None, None, None

    # 質心（offset 用）
    M = cv2.moments(c)
    if M["m00"] == 0:
        return None, None, None, None
    cx = int(M["m10"] / M["m00"])
    cy = int(M["m01"] / M["m00"])

    # 用所有紅色像素做線性擬合（比 Hough 對曲率/斷裂更容錯）
    pts = cv2.findNonZero(mask)
    if pts is None or len(pts) < 30:
        return None, None, None, None
    line = cv2.fitLine(pts, cv2.DIST_L2, 0, 0.01, 0.01)
    vx, vy, x0, y0 = line.flatten()
    # 角度：相對 x 軸
    angle_rad = atan2(vy, vx)  # -pi ~ pi；但 fitLine 通常給 -pi/2~pi/2 方向

    # 偏移：以 ROI 中心為 0
    h, w = mask.shape[:2]
    offset_norm = (cx - (w / 2)) / (w / 2)  # -1(最左) ~ +1(最右)

    return angle_rad, float(offset_norm), cx, cy

class PID:
    def __init__(self, kp, ki, kd, clamp_i=INTEGRAL_CLAMP):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.clamp_i = clamp_i
        self.e_prev = 0.0
        self.i_term = 0.0
        self.t_prev = None

    def reset(self):
        self.e_prev = 0.0
        self.i_term = 0.0
        self.t_prev = None

    def step(self, error):
        t = time.time()
        if self.t_prev is None:
            dt = 0.03  # 給個小 dt 避免第一步爆衝
        else:
            dt = max(1e-3, t - self.t_prev)

        # PID
        p = error
        self.i_term = clamp(self.i_term + error * dt, -self.clamp_i, self.clamp_i)
        d = (error - self.e_prev) / dt

        u = self.kp * p + self.ki * self.i_term + self.kd * d

        # 更新
        self.e_prev = error
        self.t_prev = t
        return u

pid = PID(KP, KI, KD)

# 平滑緩衝
angles_buf = deque(maxlen=SMOOTH_N)
offsets_buf = deque(maxlen=SMOOTH_N)

# =========================
# 主循環（攝影機來源自行替換）
# =========================
cap = cv2.VideoCapture(0)  # 實機可換成你的串流/樹莓派攝像頭
if not cap.isOpened():
    print("無法開啟攝影機")
    exit(1)

try:
    while True:
        ok, frame = cap.read()
        if not ok:
            print("讀取影像失敗")
            break

        roi, (rx, ry, rw, rh) = proportional_roi(frame)
        mask = red_mask_hsv(roi)

        angle_rad, offset_norm, cx, cy = find_line_angle_and_offset(mask)

        if angle_rad is None:
            # 找不到線：策略
            pid.reset()
            if NO_LINE_BRAKE:
                left_cmd = 0
                right_cmd = 0
            else:
                # 也可維持上次控制量或慢速前進找線
                left_cmd = BASE_SPEED
                right_cmd = BASE_SPEED
        else:
            # 平滑
            angles_buf.append(angle_rad)
            offsets_buf.append(offset_norm)
            angle_avg = float(np.mean(angles_buf))
            offset_avg = float(np.mean(offsets_buf))

            # 將角度 & 位移合成單一 error
            # 角度：-90°~+90°，將其Normalize到約 [-1,1] 再加權
            angle_norm = angle_avg / (pi / 4)  # 以 45° 當作「滿刻度」
            angle_norm = clamp(angle_norm, -2.0, 2.0)  # 安全限制

            error = W_ANGLE * angle_norm + W_OFFSET * offset_avg

            # PID 控制量（正值代表需要「向右修正」或相反，依下列混合）
            u = pid.step(error)

            # 將控制量轉成左右輪速度：
            # 正 u -> 右輪變慢、左輪變快（左轉），你也可反過來，視車體定義
            left_cmd  = BASE_SPEED - u
            right_cmd = BASE_SPEED + u

            # 限幅
            left_cmd  = clamp(left_cmd,  -MAX_SPEED, MAX_SPEED)
            right_cmd = clamp(right_cmd, -MAX_SPEED, MAX_SPEED)

        # 下發馬達
        motorL.set_speed(left_cmd)
        motorR.set_speed(right_cmd)

        if SHOW_DEBUG:
            dbg = frame.copy()
            # 畫 ROI
            cv2.rectangle(dbg, (rx, ry), (rx+rw, ry+rh), (0, 255, 255), 2)

            # 在 ROI 畫 mask 與偵測點
            roi_bgr = roi.copy()
            mask_vis = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)

            if angle_rad is not None:
                cv2.circle(roi_bgr, (int(cx), int(cy)), 6, (0, 255, 0), -1)
                # 在 ROI 畫出 fitLine 方向
                # 由 (x0,y0) + t*(vx,vy) 畫到兩端
                hv, wv = mask.shape[:2]
                # 估兩端點（t很大，取畫面寬範圍）
                vx, vy = np.cos(angle_rad), np.sin(angle_rad)
                # 用質心當作線上點（視覺直觀）
                x0, y0 = cx, cy
                t = 1000
                x1, y1 = int(x0 - t*vx), int(y0 - t*vy)
                x2, y2 = int(x0 + t*vx), int(y0 + t*vy)
                cv2.line(roi_bgr, (x1, y1), (x2, y2), (255, 0, 0), 2)

                # 文字資訊
                offset_px = (cx - (rw/2))
                txt = f"angle(deg)={angle_rad*180/pi:5.1f}  offset_norm={offset_norm:+.2f}  u={u:+.1f}"
                cv2.putText(dbg, txt, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (50, 220, 50), 2)
            else:
                cv2.putText(dbg, "NO RED LINE", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2)

            # 疊回 ROI 視覺
            dbg[ry:ry+rh, rx:rx+rw] = cv2.addWeighted(roi_bgr, 0.7, mask_vis, 0.3, 0)

            cv2.imshow("debug", dbg)
            if cv2.waitKey(1) & 0xFF == 27:  # Esc 離開
                break

finally:
    cap.release()
    cv2.destroyAllWindows()
