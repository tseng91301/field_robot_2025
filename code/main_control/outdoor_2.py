import cv2
import numpy as np
import time
import traceback
from motor import Motor
from serial_connection import Serial

from line_follow_outdoor import LineFollower

SERIAL_SIMULATION_MODE = False
SHOW_FRAME = False
RECORD_FRAME = True

# --- Arduino Serial Setup ---
try:
    serial_motor = Serial('/dev/arduino_uno-1', 115200, simulate=SERIAL_SIMULATION_MODE)
    motorL = Motor(serial_motor); motorL.set_command_byte(0xA1); motorL.no_negative_speed = True
    motorR = Motor(serial_motor); motorR.set_command_byte(0xA2); motorR.no_negative_speed = True
    time.sleep(1)
    print("✅ Arduino connected")
except Exception as e:
    print("❌ Arduino connection failed:", e)
    exit(1)

line_follower = LineFollower(motorL, motorR)

# --- Open Camera ---
cap = cv2.VideoCapture("/dev/webcam_outdoor")
# cap = cv2.VideoCapture("video/test_outdoor/left-1.mp4")
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))

# -- 設定影像擷取高度比例 --
FRAME_HEIGHT_CROP_RATE = 0.55

# --- 設定影片輸出 ---
if RECORD_FRAME:
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    fps = 20
    frame_width, frame_height = 200, 240  # 因為只取下半影像
    out_frame = cv2.VideoWriter('output/video/outdoor_output_frame.mp4', fourcc, fps, (frame_width, frame_height))
    out_mask = cv2.VideoWriter('output/video/outdoor_output_mask.mp4', fourcc, fps, (frame_width, frame_height), isColor=False)
    if not out_frame.isOpened() or not out_mask.isOpened():
        raise RuntimeError("VideoWriter failed to open. Check path, codec and frame size!")

try:
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        if RECORD_FRAME:
            slope, offset, u, mask, roi_debug = line_follower.follow(frame, debug=SHOW_FRAME, return_frame=RECORD_FRAME)
        else:
            slope, offset, u = line_follower.follow(frame, debug=SHOW_FRAME)
        print(f"[Line Follow] Offset={offset:.2f}, Slope={slope:.2f}, Control={u:.3f}")

        if RECORD_FRAME:
            out_frame.write(roi_debug)
            out_mask.write(mask)

        if cv2.waitKey(1) & 0xFF == 27:  #press ESC
            break
            
        time.sleep(0.03)

except Exception as e:
    import traceback
    print("❌ Error while doing main loop:")
    print("Error type:", type(e).__name__)
    print("Error message:", str(e))
    traceback.print_exc()
    tb = traceback.extract_tb(e.__traceback__)
    for filename, lineno, func, text in tb:
        print(f"Filename: {filename}, Line: {lineno}, Function: {func}, Code: {text}")

finally:
    print("🧹 Releasing resources...")
    cap.release()
    cv2.destroyAllWindows()
    if RECORD_FRAME:
        out_frame.release()
        out_mask.release()
    if serial_motor:
        serial_motor.close()
    print("✅ Finished and saved videos.")
