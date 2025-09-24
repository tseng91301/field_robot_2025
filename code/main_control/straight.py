from motor import Motor, DualMotor
from serial_connection import Serial
import time

SERIAL_PORT_MOTOR = "/dev/arduino_uno-1"
serial_motor = Serial(SERIAL_PORT_MOTOR, 115200, simulate=False)

motorL = Motor(serial_motor); motorL.set_command_byte(0xA1); motorL.no_negative_speed = True
motorR = Motor(serial_motor); motorR.set_command_byte(0xA2); motorR.no_negative_speed = True

time.sleep(1)

while True:
    motorL.set_speed(100)
    motorR.set_speed(100)
    time.sleep(0.05)