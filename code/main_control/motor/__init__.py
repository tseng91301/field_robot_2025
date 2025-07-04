import serial_connection as sc

class Motor:
    def __init__(self, ser: sc.Serial):
        self.ser = ser
        return

    def set_command_byte(self, command_byte: int):
        self.command_byte = command_byte
        return

    def set_speed(self, speed: int):
        if speed > 255:
            speed = 255
        elif speed < -255:
            speed = -255
        self.speed = speed
        outp = bytearray()
        outp.append(self.command_byte)
        outp.append(0x01 if self.speed < 0 else 0x00)
        outp.append(self.speed)
        self.ser.send_command(outp)
        return

    def get_speed(self) -> int:
        pass