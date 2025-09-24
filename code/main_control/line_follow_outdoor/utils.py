from .configuration import LineFollowConfig
import cv2
import time
import numpy as np

def proportional_roi(frame, bottom_start_ratio=LineFollowConfig.ROI_BOTTOM_START, height_ratio=LineFollowConfig.ROI_HEIGHT_RATIO):
    h, w = frame.shape[:2]
    y1 = int(h * bottom_start_ratio)
    y2 = int(h * min(1.0, bottom_start_ratio + height_ratio))
    roi = frame[y1:y2, 0:w]
    return roi, (0, y1, w, y2 - y1)  # ROI 與其在原圖的位置（x, y, w, h）

def warp_perspective(img, top_left_ratio=(0.25, 0.0), top_right_ratio=(0.75, 0.0),
                     bottom_left_ratio=(0.0, 1.0), bottom_right_ratio=(1.0, 1.0),
                     out_size=(400, 600)):
    """
    將 ROI 透視校正成矩形
    - top_left_ratio ... (x_ratio, y_ratio) 代表原圖相對位置
    - out_size ... 輸出影像大小 (w, h)
    """
    h, w = img.shape[:2]

    # 定義來源四邊形 (依照比例轉 pixel)
    src = np.float32([
        [w * top_left_ratio[0], h * top_left_ratio[1]],       # 左上
        [w * top_right_ratio[0], h * top_right_ratio[1]],     # 右上
        [w * bottom_left_ratio[0], h * bottom_left_ratio[1]], # 左下
        [w * bottom_right_ratio[0], h * bottom_right_ratio[1]]# 右下
    ])

    # 定義輸出矩形座標
    dst = np.float32([
        [0, 0],                 # 左上
        [out_size[0], 0],       # 右上
        [0, out_size[1]],       # 左下
        [out_size[0], out_size[1]] # 右下
    ])

    # 透視矩陣
    M = cv2.getPerspectiveTransform(src, dst)

    # 進行透視校正
    warped = cv2.warpPerspective(img, M, out_size)

    return warped, M

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