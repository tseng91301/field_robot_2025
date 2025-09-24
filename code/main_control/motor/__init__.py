import serial_connection as sc
import math

class Motor:
    def __init__(self, ser: sc.Serial):
        self.ser = ser
        self.no_negative_speed = False
        return

    def set_command_byte(self, command_byte: int):
        self.command_byte = command_byte
        return

    def set_speed(self, speed: int):
        speed = int(speed)
        if speed > 255:
            speed = 255
        elif speed < -255:
            speed = -255

        if speed < 0 and self.no_negative_speed:
            speed = 0

        self.speed = speed
        outp = bytearray()
        outp.append(self.command_byte)
        outp.append(0x01 if self.speed < 0 else 0x00)
        outp.append(int(self.speed))
        self.ser.send_command(outp)
        return

    def get_speed(self) -> int:
        pass

class DualMotor:
    def __init__(self, m1: Motor, m2: Motor):
        self.motor1 = m1
        self.motor2 = m2
        self.L_calibration = 1.0
        self.R_calibration = 1.0
        self.L_weight = 0.0
        self.R_weight = 0.0
        self.speed = 0.0
        return

    def set_speed(self, spdL, spdR):
        self.motor1.set_speed(spdL)
        self.motor2.set_speed(spdR)
        return

    def set_calibration(self, L_calibration, R_calibration):
        # Calibrate Left and Right speed.
        # input any floating number bigger than 0.0
        # To ensure the speed is the max output, we will set the big one to 1.0, and the other will be divided, respectively.
        if (L_calibration <= 0.0 or R_calibration <= 0.0):
            return

        if (L_calibration > R_calibration):
            self.R_calibration = R_calibration / L_calibration
            self.L_calibration = 1.0
        else:
            self.L_calibration = L_calibration / R_calibration
            self.R_calibration = 1.0
        return

    def set_direction(self, direction):
        """Input a direction angle between [-180, 180]
        -180: L_weight = 1.0, R_weight = -1.0
        0: L_weight = 0.0, R_weight = 0.0
        180: L_weight = -1.0, R_weight = 1.0"""
        direction = int(direction)
        if (direction < -180 or direction > 180):
            return

        if (direction <= 0 and direction >= -180):
            self.L_weight = 1.0
            self.R_weight = math.cos(direction * math.pi / 180.0)
        elif (direction > 0 and direction <= 180):
            self.L_weight = math.cos(direction * math.pi / 180.0)
            self.R_weight = 1.0

        # spd = (255 * self.speed * self.L_weight * self.L_calibration, 255 * self.speed * self.R_weight * self.R_calibration)
        # print(spd)

        self.set_speed(255 * self.speed * self.L_weight * self.L_calibration, 255 * self.speed * self.R_weight * self.R_calibration)
        return
