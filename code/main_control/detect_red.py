import cv2
import numpy as np
import serial
import time

from motor import Motor, DualMotor

# PID 參數設定
kP = 0.1
kI = 0.0
kD = 0.0
e = 0.0
pe = 0.0
ie = 0.0

#Orin NX
# --- Arduino Serial Setup ---
try:
    serial_motor = serial.Serial('/dev/ttyACM0', 115200, timeout=1)
    motorL = Motor(serial_motor, 0xA1)
    motorR = Motor(serial_motor, 0xA2)
    motor_dual = DualMotor(motorL, motorR)
    # arduino = serial.Serial('/dev/ttyACM0', 115200, timeout=1)
    time.sleep(2)  # Give Arduino time to reset
    print("✅ Arduino connected")
except Exception as e:
    print("❌ Arduino connection failed:", e)
    arduino = None

# --- Open Camera ---
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))

if not cap.isOpened():
    print("❌ Failed to open camera")
    exit()

def find_lane_center(roi, y_offset, frame, color=(0, 255, 0)):
    contours, _ = cv2.findContours(roi, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    centers = []
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        if w * h > 200:
            cx = x + w // 2
            cy = y + h // 2 + y_offset
            centers.append((cx, cy))
            cv2.circle(frame, (cx, cy), 5, color, -1)
    if len(centers) >= 2:
        centers = sorted(centers, key=lambda p: p[0])
        left, right = centers[0], centers[-1]
        lane_center = (left[0] + right[0]) // 2
        cv2.circle(frame, (lane_center, (left[1] + right[1]) // 2), 6, (255, 0, 0), -1)
        return lane_center
    return None

while True:
    ret, frame = cap.read()
    if not ret:
        print("❌ Frame capture failed")
        break

    height, width, _ = frame.shape
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    # Red detection (HSV)
    lower_red1 = np.array([0, 100, 100])
    upper_red1 = np.array([8, 255, 255])
    lower_red2 = np.array([172, 100, 100])
    upper_red2 = np.array([180, 255, 255])

    mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
    mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
    mask = cv2.bitwise_or(mask1, mask2)

    # Morphology to reduce noise
    kernel = np.ones((5, 5), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

    # Regions of Interest (ROI)
    roi_near = mask[int(height * 0.6):int(height * 0.8), :]
    roi_far = mask[int(height * 0.3):int(height * 0.5), :]

    # Find lane centers
    center_near = find_lane_center(roi_near, int(height * 0.6), frame, (0, 255, 0))
    center_far = find_lane_center(roi_far, int(height * 0.3), frame, (0, 0, 255))

    if center_near and center_far:
        # Insert PID value
        e = center_far - center_near
        ie += e
        d = e - pe
        pe = e
        val = int(kP * e + kI * ie + kD * d)

        motor_dual.set_direction(val)

        # if diff > 50:
        #     curve = "右轉"
        #     if arduino:
        #         arduino.write(b'R\n')
        # elif diff < -50:
        #     curve = "左轉"
        #     if arduino:
        #         arduino.write(b'L\n')
        # else:
        #     curve = "直走"
        #     if arduino:
        #         arduino.write(b'S\n')
        print("賽道方向:", val)

    # Debug display (enable if you have GUI)
    cv2.imshow("Frame", frame)
    cv2.imshow("Mask", mask)
    if cv2.waitKey(1) & 0xFF == 27:  # ESC to quit
        break

cap.release()
cv2.destroyAllWindows()
if serial_motor:
    serial_motor.close()

