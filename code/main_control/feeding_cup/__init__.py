import serial_connection as sc
import asyncio
import struct
import time

class FeedingCup:
    def __init__(self, ser: sc.Serial):
        self.ser = ser
        self.initial_step = 0 # 步進馬達一開始的位置
        self.trigger_step = 0 # 伸出手臂觸發飼料機的步進馬達步數
        self.now_step = 0 # 目前記錄的步數
        self.command_byte_stepper = 0x00
        self.command_byte_led = 0x00
        return

    def set_command_byte(self, command_byte_stepper: int, command_byte_led: int, read_byte: int, command_feed_byte: int):
        self.command_byte_stepper = command_byte_stepper # 步進馬達指令發送的裝置代碼
        self.read_byte = read_byte # 查看重量的指令代碼
        self.command_byte_led = command_byte_led # 分類顯示 LED 的指令代碼
        self.command_feed_byte = command_feed_byte # 觸發飼料機的指令代碼
        return

    def turn(self, step: int):
        outp = bytearray()
        outp.append(self.command_byte_stepper)
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

    def set_animal_led(self, color: int):
        """
        呼叫後立即送出開燈指令，並在背景 3 秒後自動關燈。
        """
        async def task():
            outp = bytearray([self.command_byte_led, color])
            self.ser.send_command(outp)

            await asyncio.sleep(2)

            outp = bytearray([self.command_byte_led, 0])
            self.ser.send_command(outp)

        # 建立背景任務，不會阻塞主程式
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(task())
        except RuntimeError:
            # 如果沒有正在跑的 loop，就自己開一個
            asyncio.run(task())

    def set_animal_led_wait(self, color: int):
        outp = bytearray([self.command_byte_led, color])
        self.ser.send_command(outp)

        time.sleep(2)

        outp = bytearray([self.command_byte_led, 0])
        self.ser.send_command(outp)

    def set_led(self, color: int):
        outp = bytearray([self.command_byte_led, color])
        self.ser.send_command(outp)

    async def use_machine(self, weight: int):
        # 目前只能同步呼叫，否則裝置可能會有出錯的風險
        outp = bytearray([self.command_feed_byte, weight])
        self.ser.send_command(outp)
        await self.ser.read_bytes(1) # 等待 Arduino 處理完成
        return

