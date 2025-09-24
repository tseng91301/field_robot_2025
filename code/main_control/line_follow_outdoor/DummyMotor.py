# =========================
# 馬達控制（請換成你的實作）
# =========================
from .configuration import LineFollowConfig
class Motor:
    def __init__(self, id):
        self.id = id
    def set_speed(self, v):
        # 這裡只打印，實機請送到你的馬達驅動
        if LineFollowConfig.SHOW_DEBUG:
            print(f"{self.id}: {int(v)}")