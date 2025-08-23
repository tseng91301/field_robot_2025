import cv2
import threading
import time
import numpy as np

from . import configuration

class FrameHub:
    def __init__(self):
        self.frame = None            # 最新 frame
        self.result = None           # 最新辨識結果 (list of (x,y,w,h))
        self.new_frame = False       # 是否有新 frame
        self.lock = threading.Lock() # 保護共用資源
        self.result_available = False

    def update_frame(self, frame):
        with self.lock:
            self.frame = frame.copy()
            self.new_frame = True

    def get_frame(self):
        with self.lock:
            return self.frame.copy() if self.frame is not None else None

    def set_result(self, result):
        with self.lock:
            self.result = result
            self.result_available = True
            self.new_frame = False   # frame 已處理完

    def get_result(self):
        with self.lock:
            ret = tuple()
            if configuration.DEBUG_MODE:
                    if self.result_available and (self.result is not None):
                        for (x, y, w, h) in self.result:
                            cv2.rectangle(self.frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
            if not self.result_available:
                ret = (False, None)
            else:
                self.result_available = False
                ret = (True, self.result)
            cv2.imshow("Detection result", self.frame)
            return ret


class DetectorThread(threading.Thread):
    def __init__(self, hub: FrameHub):
        super().__init__(daemon=True)
        self.hub = hub
        self.running = True
        self.processing = False

    def run(self):
        while self.running:
            frame = self.hub.get_frame()
            if frame is not None and self.hub.new_frame:
                # 模擬：做影像辨識 (這裡用臉部辨識做範例)
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                detector = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
                faces = detector.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5)

                # 確保回傳 numpy.ndarray，不是 list
                if faces is None or len(faces) == 0:
                    faces = np.empty((0, 4), dtype=int)

                self.hub.set_result(faces)
            else:
                time.sleep(0.01)  # 沒新 frame → 稍微休息


def main():
    hub = FrameHub()
    detector = DetectorThread(hub)
    detector.start()

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("無法開啟攝影機")
        return

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            # 主程式送 frame 給辨識節點
            if not hub.new_frame:
                # print("update frame")
                hub.update_frame(frame)
                pass
            else:
                # print("pending...")
                pass

            # 主程式讀取最新結果
            avail, result = hub.get_result()
            print(avail)
            if avail and (result is not None):
                for (x, y, w, h) in result:
                    cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)

            cv2.imshow("Main", frame)

            if cv2.waitKey(1) & 0xFF == 27:
                break
    finally:
        cap.release()
        cv2.destroyAllWindows()
        detector.running = False


if __name__ == "__main__":
    main()
