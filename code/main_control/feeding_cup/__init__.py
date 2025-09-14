import serial_connection as sc
import asyncio
import struct

class FeedingCup:
    def __init__(self, ser: sc.Serial):
        self.ser = ser
        self.initial_step = 0 # 步進馬達一開始的位置
        self.trigger_step = 0 # 伸出手臂觸發飼料機的步進馬達步數
        self.now_step = 0 # 目前記錄的步數
        return
    
    def set_command_byte(self, command_byte: int, read_byte: int):
        self.command_byte = command_byte # 指令發送的裝置代碼
        self.read_byte = read_byte # 查看重量的指令代碼
        return
    
    def turn(self, step: int):
        outp = bytearray()
        outp.append(self.command_byte)
        outp.append(0x00 if step > 0 else 0x01)
        outp.append(abs(step))
        self.ser.send_command(outp)
        self.now_step += step
        return
    
    def turn_to(self, step: int):
        self.turn(step - self.now_step)
        return
    
    def elongation(self):
        # 伸長
        self.turn_to(self.initial_step + self.trigger_step)
        return
    
    def put_back(self):
        # 縮短
        self.turn_to(self.initial_step)
        return
    
    def set_initial_step(self, step: int, goTo: bool = True):
        self.initial_step = step
        if goTo:
            self.turn_to(step)
        return
    
    async def weight(self):
        # 讀取重量
        outp = bytearray()
        outp.append(self.read_byte)
        outp.append(0x00)
        self.ser.send_command(outp)
        # 等待 4 bytes float
        buffer = await self.ser.read_bytes(4)

        # 解析 float
        value = struct.unpack('<f', buffer[:4])[0]
        return value
    

