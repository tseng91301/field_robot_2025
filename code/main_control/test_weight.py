import asyncio
import struct
import serial

START_BYTE = 0xFF

async def talk_to_arduino(port="COM14", baudrate=115200):
    ser = serial.Serial(port, baudrate, timeout=0.1)  # 短 timeout
    await asyncio.sleep(3)  # 等 Arduino reset
    print("✅ Arduino connected")

    # 傳送封包: [0xFF][0xB1][0x00][\n]
    packet = bytes([START_BYTE, 0xB1, 0x00, 0x0A])
    ser.write(packet)
    print("📤 Sent command:", packet)

    # 等待 4 bytes float
    buffer = bytearray()
    while len(buffer) < 4:
        n = ser.in_waiting
        if n:
            buffer.extend(ser.read(n))
        await asyncio.sleep(0.01)  # 給 CPU 休息

    # 解析 float
    value = struct.unpack('<f', buffer[:4])[0]
    print("📥 Received float:", value)
    return value


async def main():
    while True:
        value = await talk_to_arduino("COM14", 115200)
        print("✅ Final result:", value)
        await asyncio.sleep(0.05)



if __name__ == "__main__":
    asyncio.run(main())
