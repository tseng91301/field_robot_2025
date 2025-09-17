from .configuration import LineFollowConfig
import cv2
from collections import deque
from math import pi
import numpy as np

from .DummyMotor import DummyMotor
from .utils import proportional_roi, PID, clamp, red_mask_hsv, find_line_angle_and_offset

class LineFollower:
    def __init__(self, motorL, motorR):
        self.motorL: DummyMotor = motorL
        self.motorR: DummyMotor = motorR
        self.on: bool = False
        self.pid = PID(LineFollowConfig.KP, LineFollowConfig.KI, LineFollowConfig.KD)
        self.angles_buf = deque(maxlen=LineFollowConfig.SMOOTH_N)
        self.offsets_buf = deque(maxlen=LineFollowConfig.SMOOTH_N)
        self.offset_cal = 0 # 循跡時要偏移的距離(左負右正)

    def follow(self, frame):
        # 定義需要回傳的值
        angle_avg, offset_avg, u = None, None, None

        roi, (rx, ry, rw, rh) = proportional_roi(frame)
        mask = red_mask_hsv(roi)

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

        # 下發馬達
        self.motorL.set_speed(left_cmd)
        self.motorR.set_speed(right_cmd)

        if LineFollowConfig.SHOW_DEBUG:
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
        
        return angle_avg, offset_avg, u