import numpy as np

# 螢幕或影像大小
W, H = 640, 480  # 例如影像 640x480

# 你的比例座標
pts_src_config = np.float32([[0.2, 0.15], [0.8, 0.15], [0.0, 1.0], [1.0, 1.0]])

# 轉換成像素座標
pts_src_pixel = np.zeros_like(pts_src_config)
pts_src_pixel[:, 0] = pts_src_config[:, 0] * W  # x
pts_src_pixel[:, 1] = pts_src_config[:, 1] * H  # y

print(pts_src_pixel)
