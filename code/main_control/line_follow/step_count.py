import cv2
import numpy as np

from .configuration import StepCountConfig

class StepCounter:
    def __init__(self):
        self.consecutive_detected = 0
        self.consecutive_not_detected = 0
        self.level = 0
        self.waiting_for_reset = False

    def read_frame(self, frame_inp: np.ndarray):
        # frame = frame_inp.copy()
        frame = frame_inp
        h, w, _ = frame.shape

        # 計算 ROI 區域 (底下 25%，左右 ±15%)
        y_start = int(h * StepCountConfig.Y_START)
        y_end = int(h * StepCountConfig.Y_END)
        x_start = int(w * 0.5 - w * StepCountConfig.X_WIDTH / 2)
        x_end = int(w * 0.5 + w * StepCountConfig.X_WIDTH / 2)
        roi = frame[y_start:y_end, x_start:x_end]

        # 轉 HSV 找紅色
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        mask1 = cv2.inRange(hsv, StepCountConfig.H_LOW1, StepCountConfig.H_HIGH1)
        mask2 = cv2.inRange(hsv, StepCountConfig.H_LOW2, StepCountConfig.H_HIGH2)
        mask = cv2.bitwise_or(mask1, mask2)

        # 計算紅色佔比
        red_ratio = np.sum(mask > 0) / mask.size
        detected = red_ratio > 0.9

        if not self.waiting_for_reset:
            if detected:
                self.consecutive_detected += 1
                if self.consecutive_detected >= 10:
                    self.level += 1
                    print(f"✅ 偵測到紅線！關卡 +1 → 現在 level = {self.level}")
                    self.waiting_for_reset = True
                    self.consecutive_detected = 0
            else:
                self.consecutive_detected = 0
        else:
            if not detected:
                self.consecutive_not_detected += 1
                if self.consecutive_not_detected >= 30:
                    print("🔄 狀態重設，可以偵測下一條紅線了")
                    self.waiting_for_reset = False
                    self.consecutive_not_detected = 0
            else:
                self.consecutive_not_detected = 0

        if StepCountConfig.SHOW_DEBUG:
            # 畫 ROI 框線
            cv2.rectangle(frame, (x_start, y_start), (x_end, y_end), (0, 255, 0), 2)
            cv2.imshow("frame", frame)
            cv2.imshow("mask", mask)
