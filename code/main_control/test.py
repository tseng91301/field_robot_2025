import cv2

from line_follow import LineFollower, DummyMotor, StepCounter

DEBUG_MODE = True

cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("無法開啟攝影機")
    exit(1)

motorL = DummyMotor("L")
motorR = DummyMotor("R")
line_follower = LineFollower(motorL, motorR)
step_count = StepCounter()

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

            if cv2.waitKey(1) & 0xFF == 27:  # Esc 離開
                break
        except Exception as e:
            print("Error while doing main loop: ", e)
            break
finally:
    cap.release()
    cv2.destroyAllWindows()