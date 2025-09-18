import cv2
import threading
import time
import numpy as np

from . import configuration
from ultralytics import YOLO

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
                        for (x, y, w, h, label, confidence) in self.result:
                            cv2.rectangle(self.frame, (x, y), (x+w, y+h), (0, 0, 255), 5)
                            cv2.putText(self.frame, f'{label} {confidence:.2f}', (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 0, 0), 2)
            if not self.result_available:
                ret = (False, [])
            else:
                self.result_available = False
                ret = (True, self.result)
            if configuration.DEBUG_MODE:
                cv2.imshow("Detection result", self.frame)
                pass
            return ret


class DetectorThread(threading.Thread):
    def __init__(self, hub: FrameHub):
        super().__init__(daemon=True)
        self.hub = hub
        self.running = True
        self.processing = False
        self.model = YOLO(configuration.model_path)
        self.limitDetect = False
        self.detect_objects = []
        self.detect_confidence = 0.8
        return

    def set_detect_objects(self, objects: list):
        self.detect_objects = objects
        self.limitDetect = True
        return

    def set_min_confidence(self, confidence: float):
        self.detect_confidence = confidence
        return

    def run(self):
        while self.running:
            frame = self.hub.get_frame()
            detect_boxes = []
            if frame is not None and self.hub.new_frame:
                detect_result = self.model(frame, verbose=False, show=False)
                # 顯示結果
                for result in detect_result:
                    boxes = result.boxes
                    for box in boxes:
                        # 將張量轉換為標量
                        label = self.model.names[int(box.cls.item())]
                        if (self.limitDetect and label not in self.detect_objects) or box.conf.item() < self.detect_confidence:
                            # 辨識到的物件不在需要辨識的物件範圍內，或是信心值不夠
                            continue
                        x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                        confidence = box.conf.item()
                        detect_boxes.append((x1, y1, x2-x1, y2-y1, label, confidence))

                self.hub.set_result(detect_boxes)
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
                hub.update_frame(frame)
                pass
            else:
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
