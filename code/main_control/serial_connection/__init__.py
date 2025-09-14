import time
import serial
import threading
import asyncio

from .commands import ParseState, commands_len
from .command_handler import process_command

class Serial:
    def __init__(self, com: str, baudRate: int, simulate = False):
        self.com = com
        self.baudRate = baudRate
        self.simulate = simulate
        self.print_results = False
        if not self.simulate:
            self.ser = serial.Serial(self.com, self.baudRate)
        else:
            self.ser = None
        self.listeners = []
        self.running = False
        
        self.state = ParseState.WAIT_START
        self.command = None
        self.read_buffer = bytearray()
        self.readLock = asyncio.Lock()
        pass

    def send_bytes(self, bytes_inp: bytearray):
        if self.simulate:
            if self.print_results:
                print(f"Send bytes: ", bytes_inp)
            return
        self.ser.write(bytes_inp)
        return

    def send_command(self, command_bytes: bytearray):
        outp = bytearray()
        outp.append(0xFF)
        outp.extend(command_bytes)
        outp.append(0x0A)
        self.send_bytes(outp)
        return
    
    async def read_bytes(self, length: int, timeout: float = None):
        async with self.readLock:
            buffer = bytearray()
            if self.simulate:
                return bytearray(length)
            start = asyncio.get_event_loop().time()
            while len(buffer) < length:
                n = self.ser.in_waiting
                if n:
                    need = length - len(buffer)
                    buffer.extend(self.ser.read(min(n, need)))
                if timeout and asyncio.get_event_loop().time() - start > timeout:
                    raise asyncio.TimeoutError("Serial read timeout")
                await asyncio.sleep(0.01)
            return buffer
        
    def close(self):
        self.ser.close()