import serial

ser = serial.Serial("/dev/arduino_uno-2", 115200)

while True:
    cmd = input("輸入 HEX (例如 01 FF 0A): ")
    data = bytes.fromhex(cmd)
    ser.write(data)
    print("送出:", data)

    resp = ser.read(ser.in_waiting or 1)
    if resp:
        print("收到:", resp.hex().upper())
