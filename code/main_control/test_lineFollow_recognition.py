import cv2

from line_follow import LineFollower, DummyMotor, StepCounter
from object_detection import DetectorThread, FrameHub

DEBUG_MODE = True

cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("無法開啟攝影機")
    exit(1)

motorL = DummyMotor("L")
motorR = DummyMotor("R")

# Line Following
line_follower = LineFollower(motorL, motorR)
step_count = StepCounter()

# Object detection
hub = FrameHub()
detector = DetectorThread(hub)
detector.start()

try:
    while True:
        try:
            ret, frame = cap.read()
            if ret:
                cap_frame = frame
            else:
                print("Video loading failed")
                break

            line_follower.follow(frame)
            step_count.read_frame(frame)

            # 主程式送 frame 給辨識節點
            if not hub.new_frame:
                # print("update frame")
                hub.update_frame(frame)
                pass
            else:
                # print("pending...")
                pass

            (avail, result) = hub.get_result()
            if avail:
                # 有偵測到物件
                print(result.shape)

            if cv2.waitKey(1) & 0xFF == 27:  # Esc 離開
                break
        except Exception as e:
            print("Error while doing main loop: ", e)
            break
finally:
    cap.release()
    cv2.destroyAllWindows()