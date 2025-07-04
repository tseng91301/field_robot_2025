from enum import Enum, auto

class ParseState(Enum):
    WAIT_START = auto()       # 等待起始字元
    WAIT_COMMAND = auto()     # 等待指令類型
    WAIT_DATA = auto()        # 讀取指令資料（長度根據指令類型）
    WAIT_END = auto()         # 等待封包結尾字元

commands_len = {
    0xA1: 1, # 左馬達速度設定回應
    0xA2: 1, # 右馬達速度設定回應
}