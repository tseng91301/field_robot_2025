import cv2
import numpy as np
import math
from .DummyMotor import Motor
from .configuration import LineFollowConfig
from .utils import proportional_roi, PID, clamp, red_mask_hsv, warp_perspective


class LineFollower:
    """
    單邊循跡程式，藉由紅線的分布計算其位置與斜率，
    並用 PID 控制馬達，使車子保持在紅線一側的固定距離。
    """

    def __init__(self, motorL: Motor, motorR: Motor):
        self.motorL: Motor = motorL
        self.motorR: Motor = motorR
        self.pid = PID(LineFollowConfig.KP, LineFollowConfig.KI, LineFollowConfig.KD)
        self.base_speed = LineFollowConfig.BASE_SPEED

        self.prev_avg_offset = 0.0
        self.prev_avg_slope = 0.0

    def set_offset_amplify(self, inp: float):
        return inp**3

    def read_frame(self, frame, debug=True, return_frame = False):
        """
        1. 擷取 ROI + 透視校正
        2. 做紅色遮罩
        3. 掃描紅點平均位置
        4. 計算斜率 & 偏移
        5. 回傳
        debug=True 時會畫出 ROI、mask、各點、平均線
        """
        # --- 透視校正 ---
        frame, M = warp_perspective(frame)
        roi, (rx, ry, rw, rh) = proportional_roi(frame)
        roi = roi[:, :rw // 2]  # 只看左半邊
        mask = red_mask_hsv(roi)

        h, w = mask.shape
        print(f"h: {h}, w: {w}")
        points = []

        # --- 掃描紅線平均位置 ---
        for y in range(h-1, 0, -5):  # 從下往上，每5像素掃描
            xs = np.where(mask[y, :] > 0)[0]
            if len(xs) > 0:
                x_mean = int(np.mean(xs))
                points.append((x_mean, y))

        if len(points) < 2:
            cal_line = False
        else:
            cal_line = True

        if cal_line:
            # --- 計算斜率 & 偏移 ---
            slope_sum = 0.0
            offset_sum = 0.0
            total_dy = 0
            for i in range(len(points)-1):
                (x1, y1), (x2, y2) = points[i], points[i+1]
                dy = abs(y2 - y1)
                if dy != 0:
                    slope = (x2 - x1) / (y2 - y1)
                    slope_sum += slope * dy
                offset_sum += (points[i][0] - w // 2) * dy
                total_dy += dy

            # 斜率: 右下到左上 > 0；左下到右上 < 0
            avg_slope = slope_sum / total_dy if total_dy != 0 else 0
            avg_slope += LineFollowConfig.SLOPE_CALIBRATION
            # 偏移: 左負右正
            avg_offset = offset_sum / total_dy
            avg_offset -= (LineFollowConfig.LINE_POSITION - 0.5) * w  # 調整基準
            avg_offset = self.set_offset_amplify(avg_offset)

            # 寫入記憶中，未來沒有偵測到現就用紀錄的值
            self.prev_avg_offset = avg_offset
            self.prev_avg_slope = avg_slope
        else:
            avg_slope, avg_offset = self.prev_avg_slope, self.prev_avg_offset

        # PID 控制
        u = self.pid.step(avg_offset)

        # --- Debug 顯示 ---
        roi_debug = roi.copy()
        roi_debug = roi_debug if len(roi_debug.shape)==3 else cv2.cvtColor(roi_debug, cv2.COLOR_GRAY2BGR)
        # 畫每個掃描點
        for x, y in points:
            cv2.circle(roi_debug, (x, y), 3, (0, 255, 0), -1)

        # 畫平均 offset 線 (垂直線)
        avg_x = int(w//2 + avg_offset)
        cv2.line(roi_debug, (avg_x, 0), (avg_x, h-1), (255, 0, 0), 2)

        # 畫平均斜率線 (過 avg_x, roi 中心 y)
        y_center = h//2
        x1_line = int(avg_x - avg_slope * y_center)
        x2_line = int(avg_x + avg_slope * y_center)
        cv2.line(roi_debug, (x1_line, 0), (x2_line, h-1), (0, 0, 255), 2)

        # 顯示影像
        if debug:
            cv2.imshow("ROI Debug", roi_debug)
            cv2.imshow("Mask", mask)
        if return_frame:
            return avg_slope, avg_offset, u, mask, roi_debug

        return avg_slope, avg_offset, u

    def follow(self, frame, debug=True, return_frame = False):
        """
        執行循跡控制，更新馬達速度
        """
        if not return_frame:
            slope, offset, u = self.read_frame(frame, debug=debug)
        else:
            slope, offset, u, mask, roi_debug = self.read_frame(frame, debug=debug)
        
        if slope is None: slope = 0.0
        if offset is None: offset = 0.0
        if u is None: u = 0.0

        left_speed = clamp(self.base_speed + u, -LineFollowConfig.MAX_SPEED, LineFollowConfig.MAX_SPEED)
        right_speed = clamp(self.base_speed - u, -LineFollowConfig.MAX_SPEED, LineFollowConfig.MAX_SPEED)

        # print(f"Left: {left_speed:.2f}, Right: {right_speed:.2f}")

        self.motorL.set_speed(left_speed)
        self.motorR.set_speed(right_speed)

        if return_frame:
            return slope, offset, u, mask, roi_debug
        return slope, offset, u
