from .configuration import LineFollowConfig
import cv2
import numpy as np
import time
import math

def proportional_roi(frame, bottom_start_ratio=LineFollowConfig.ROI_BOTTOM_START, height_ratio=LineFollowConfig.ROI_HEIGHT_RATIO):
    h, w = frame.shape[:2]
    y1 = int(h * bottom_start_ratio)
    y2 = int(h * min(1.0, bottom_start_ratio + height_ratio))
    roi = frame[y1:y2, 0:w]
    return roi, (0, y1, w, y2 - y1)  # ROI 與其在原圖的位置（x, y, w, h）

def clamp(v, lo, hi):
    return max(lo, min(hi, v))

def red_mask_hsv(bgr):
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    mask1 = cv2.inRange(hsv, LineFollowConfig.H_LOW1, LineFollowConfig.H_HIGH1)
    mask2 = cv2.inRange(hsv, LineFollowConfig.H_LOW2, LineFollowConfig.H_HIGH2)
    mask = cv2.bitwise_or(mask1, mask2)
    # 形態學去噪
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (LineFollowConfig.KERNEL_SIZE, LineFollowConfig.KERNEL_SIZE))
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
    if len(areas) == 0 or max(areas) < LineFollowConfig.MIN_AREA:
        return None, None, None, None

    # 取最大連通區塊（更穩定）
    c = cnts[int(np.argmax(areas))]
    area = cv2.contourArea(c)
    if area < LineFollowConfig.MIN_AREA:
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
    angle_rad = math.atan2(vy, vx)  # -pi ~ pi；但 fitLine 通常給 -pi/2~pi/2 方向

    # 偏移：以 ROI 中心為 0
    h, w = mask.shape[:2]
    offset_norm = (cx - (w / 2)) / (w / 2)  # -1(最左) ~ +1(最右)

    return angle_rad, float(offset_norm), cx, cy

class PID:
    def __init__(self, kp, ki, kd, clamp_i=LineFollowConfig.INTEGRAL_CLAMP):
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