# DO NOT DELETE IMPORT BLOCK
import numpy as np
from dataclasses import dataclass

# 參數設定
class GeneralConfig:
    # 紅線的 mask 邊界值
    # HSV 紅色閾值（兩段）
    H_LOW1  = np.array([0, 100, 100])   # 視情況調 S/V 閾值（避免陰影/反光）
    H_HIGH1 = np.array([10, 255, 255])
    H_LOW2  = np.array([149, 58, 81])
    H_HIGH2 = np.array([180, 255, 255])

# 影像辨識循跡
class LineFollowConfig:

    # 直線辨識的畫面擷取大小
    ROI_BOTTOM_START = 0.60   # 從畫面高度的 60% 開始（0~1）
    ROI_HEIGHT_RATIO = 0.40   # ROI 高度佔整畫面的 30%（0~1）

    VERTICAL_LINE_DEGREE = 35 # 垂直線角度誤差範圍
    HORIZONTAL_LINE_DEGREE = 25 # 水平線角度誤差範圍

    LINE_POSITION = 0.3 # 紅線所在的基準 X 位置 (數字從左到右是 0.0 ~ 1.0)
    SLOPE_CALIBRATION = 0.23 # 算出來的斜率會加上這個數值

    # 紅線的 mask 邊界值
    # HSV 紅色閾值（兩段）
    H_LOW1  = GeneralConfig.H_LOW1
    H_HIGH1 = GeneralConfig.H_HIGH1
    H_LOW2  = GeneralConfig.H_LOW2
    H_HIGH2 = GeneralConfig.H_HIGH2

    KERNEL_SIZE = 5          # 形態學去噪
    MIN_AREA    = 300        # 最小紅色區塊像素面積（過小視為噪音）

    # PID 權重與係數
    W_ANGLE  = 0.7           # 角度誤差權重
    W_OFFSET = 0.3           # 位置誤差權重（兩者加總為 1 較直覺）

    KP = 0.0004               # 比例增益（可依車體/速度調整）
    KI = 0.0001                 # 積分增益（先從 0 開始，避免積分飄移）
    KD = 0.00015                # 微分增益
    INTEGRAL_CLAMP = 0.5     # 限制積分項的幅度（-0.5 ~ 0.5）

    BASE_SPEED = 60         # 你的例子：兩輪基準速度 100
    MAX_SPEED  = 100         # 馬達速度上限（含負值）

    # 平滑：保存最近 N 個角度/偏移
    SMOOTH_N = 5

    # 找不到線時策略
    NO_LINE_BRAKE = True     # True：煞停；False：維持基準速度直行或保留上次控制量

    # 視覺化除錯
    SHOW_DEBUG = True