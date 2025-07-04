from serial_connection import Serial
from motor import Motor

import time

ser_motor = Serial("COM8", 115200)
motorL = Motor(ser_motor)
motorR = Motor(ser_motor)
motorL.set_command_byte(0xA1)
motorL.ser.start_receiving()
motorR.set_command_byte(0xA2)
motorR.ser.start_receiving()


while True:
    motorL.set_speed(100)
    motorR.set_speed(100)
    time.sleep(0.5)