import time
import serial
import threading

from .commands import ParseState, commands_len
from .command_handler import process_command

class Serial:
    def __init__(self, com: str, baudRate: int):
        self.com = com
        self.baudRate = baudRate
        self.ser = serial.Serial(self.com, self.baudRate)
        self.listeners = []
        self.running = False
        
        self.state = ParseState.WAIT_START
        self.command = None
        self.read_buffer = bytearray()
        pass

    def send_bytes(self, bytes_inp: bytearray):
        self.ser.write(bytes_inp)
        pass

    def send_command(self, command_bytes: bytearray):
        outp = bytearray()
        outp.append(0xFF)
        outp.extend(command_bytes)
        outp.append(0x0A)
        self.ser.write(outp)
        return

    def add_listener(self, callback):
        """註冊事件處理器"""
        self.listeners.append(callback)

    def start_receiving(self):
        """啟動背景接收執行緒"""
        self.running = True
        self.thread = threading.Thread(target=self._receive_loop, daemon=True)
        self.thread.start()

    def _receive_loop(self):
        """背景接收執行緒"""
        while self.running:
            if self.ser.in_waiting:
                # print(f"in_waiting: {self.ser.in_waiting}")
                data = self.ser.read(self.ser.in_waiting)
                for byte in data:
                    # print(f"byte: {byte}")

                    if self.state == ParseState.WAIT_START:
                        # print("wait start")
                        if byte == 0xFF:
                            self.state = ParseState.WAIT_COMMAND

                    elif self.state == ParseState.WAIT_COMMAND:
                        # print("wait command")
                        self.command = byte
                        self.data_length = commands_len.get(self.command, 0)
                        self.read_buffer = bytearray()
                        self.state = ParseState.WAIT_DATA

                    elif self.state == ParseState.WAIT_DATA:
                        # print("wait data")
                        self.read_buffer.append(byte)
                        if len(self.read_buffer) >= self.data_length:
                            self.state = ParseState.WAIT_END

                    elif self.state == ParseState.WAIT_END:
                        # print("wait end")
                        if byte == 0x0A:
                            process_command(self.command, self.read_buffer)
                        self.state = ParseState.WAIT_START
            time.sleep(0.02)
        return
    def stop_receiving(self):
        """停止接收"""
        self.running = False
        if hasattr(self, 'thread'):
            self.thread.join()
        self.ser.close()