from .configuration import LineFollowConfig
import cv2
from collections import deque
from math import pi
import numpy as np

from .DummyMotor import DummyMotor
from .utils import proportional_roi, PID, clamp, red_mask_hsv, find_line_angle_and_offset

class LineFollower:

    HORIZONTAL_LINE = 0
    VERTICAL_LINE = 1
    VERTICAL_LINE_POS_M = np.tan(np.deg2rad(90 - LineFollowConfig.VERTICAL_LINE_DEGREE)) # 垂直線的正向斜率最小值
    VERTICAL_LINE_NEG_M = np.tan(np.deg2rad(-90 + LineFollowConfig.VERTICAL_LINE_DEGREE)) # 垂直線的負向斜率最大值
    HORIZONTAL_LINE_POS_M = np.tan(np.deg2rad(LineFollowConfig.HORIZONTAL_LINE_DEGREE)) # 水平線的正向斜率最大值
    HORIZONTAL_LINE_NEG_M = np.tan(np.deg2rad(-LineFollowConfig.HORIZONTAL_LINE_DEGREE)) # 水平線的負向斜率最小值

    def __init__(self, motorL, motorR):
        self.motorL: DummyMotor = motorL
        self.motorR: DummyMotor = motorR
        self.on: bool = True
        self.pid = PID(LineFollowConfig.KP, LineFollowConfig.KI, LineFollowConfig.KD)
        self.angles_buf = deque(maxlen=LineFollowConfig.SMOOTH_N)
        self.offsets_buf = deque(maxlen=LineFollowConfig.SMOOTH_N)
        self.offset_cal = 0 # 循跡時要偏移的距離(左負右正)

    def switch(self, on):
        self.on = on
        if not on:
            self.motorL.set_speed(0)
            self.motorR.set_speed(0)

    def get_lines(self, img, line_type: int, show_in_img = False):

        edges = cv2.Canny(img, 50, 80, apertureSize=3)

        # 4. 使用 HoughLinesP 來偵測線條 (概率霍夫變換)
        lines = cv2.HoughLinesP(edges, rho=1, theta=np.pi/180, threshold=115, minLineLength=100, maxLineGap=30)

        # 篩選線段，依照參數為HORIZONTAL 或 VERTICAL決定
        lines_filtered = []
        lines_slope = []
        if line_type == LineFollower.HORIZONTAL_LINE:
            if lines is not None:
                for line in lines:
                    x1, y1, x2, y2 = line[0]
                    # 避免垂直線 (斜率無法計算)
                    if x2 - x1 == 0:
                        continue
                    slope = -(y2 - y1) / (x2 - x1)
                    if LineFollower.HORIZONTAL_LINE_NEG_M <= slope <= LineFollower.HORIZONTAL_LINE_POS_M:
                        lines_filtered.append(line)
                        lines_slope.append(slope)
                        pass
                    pass
                pass
            pass
        elif line_type == LineFollower.VERTICAL_LINE:
            if lines is not None:
                for line in lines:
                    x1, y1, x2, y2 = line[0]
                    # 避免垂直線 (斜率無法計算)
                    if x2 - x1 == 0:
                        lines_filtered.append(line)
                        lines_slope.append(1000)
                        continue
                    slope = -(y2 - y1) / (x2 - x1)
                    if slope >= LineFollower.VERTICAL_LINE_POS_M or slope <= LineFollower.VERTICAL_LINE_NEG_M:
                        lines_filtered.append(line)
                        lines_slope.append(slope)
                        pass
                    pass
                pass
            pass

        if(show_in_img):
            # 5. 繪製偵測到的線條
            if lines is not None:
                for line in lines:
                    x1, y1, x2, y2 = line[0]
                    cv2.line(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.imshow('Line Detect Result', img)
        return lines_filtered, lines_slope

    def follow(self, frame):
        # 定義需要回傳的值
        angle_avg, offset_avg, u = 0, 0, 0
        if not self.on:
            self.motorL.set_speed(0)
            self.motorR.set_speed(0)
            return angle_avg, offset_avg, u

        roi, (rx, ry, rw, rh) = proportional_roi(frame)
        mask = red_mask_hsv(roi)

        lines_y, line_y_slope = self.get_lines(mask, LineFollower.HORIZONTAL_LINE, LineFollowConfig.SHOW_DEBUG) # 儲存水平的線條(在y軸分布)
        if len(lines_y) == 0:
            angle_rad, offset_norm, cx, cy = find_line_angle_and_offset(mask)
            if offset_norm: offset_norm -= self.offset_cal # 減去需要的篇移量

            if angle_rad is None:
                # 找不到線：策略
                self.pid.reset()
                if LineFollowConfig.NO_LINE_BRAKE:
                    left_cmd = 0
                    right_cmd = 0
                else:
                    # 也可維持上次控制量或慢速前進找線
                    left_cmd = LineFollowConfig.BASE_SPEED
                    right_cmd = LineFollowConfig.BASE_SPEED
            else:
                # 平滑
                self.angles_buf.append(angle_rad)
                self.offsets_buf.append(offset_norm)
                angle_avg = float(np.mean(self.angles_buf))
                offset_avg = float(np.mean(self.offsets_buf))

                # 將角度 & 位移合成單一 error
                # 角度：-90°~+90°，將其Normalize到約 [-1,1] 再加權
                angle_norm = angle_avg / (pi / 4)  # 以 45° 當作「滿刻度」
                angle_norm = clamp(angle_norm, -2.0, 2.0)  # 安全限制

                # error = W_ANGLE * angle_norm + W_OFFSET * offset_avg
                error = LineFollowConfig.W_OFFSET * offset_avg # 暫時只使用 offset 作為 pid 控制的 err 根據

                # PID 控制量（正值代表需要「向右修正」或相反，依下列混合）
                u = self.pid.step(error)

                # 將控制量轉成左右輪速度：
                # 正 u -> 右輪變慢、左輪變快（左轉），你也可反過來，視車體定義
                left_cmd  = LineFollowConfig.BASE_SPEED + u
                right_cmd = LineFollowConfig.BASE_SPEED - u

                # 限幅
                left_cmd  = clamp(left_cmd,  -LineFollowConfig.MAX_SPEED, LineFollowConfig.MAX_SPEED)
                right_cmd = clamp(right_cmd, -LineFollowConfig.MAX_SPEED, LineFollowConfig.MAX_SPEED)

        else:
            angle_avg, offset_avg, u = 0, 0, 0
            left_cmd = LineFollowConfig.BASE_SPEED
            right_cmd = LineFollowConfig.BASE_SPEED

        # 下發馬達
        self.motorL.set_speed(left_cmd)
        self.motorR.set_speed(right_cmd)

        return angle_avg, offset_avg, u