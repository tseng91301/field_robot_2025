import cv2
import numpy as np

# 載入圖片
img = cv2.imread("outdoor_line.png")
img_hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

def nothing(x):
    pass

cv2.namedWindow("Trackbars")
cv2.resizeWindow("Trackbars", 800, 600)  # 你可以改成更大

# 第一組 HSV
cv2.createTrackbar("H1 Min", "Trackbars", 0, 180, nothing)
cv2.createTrackbar("H1 Max", "Trackbars", 10, 180, nothing)
cv2.createTrackbar("S1 Min", "Trackbars", 100, 255, nothing)
cv2.createTrackbar("S1 Max", "Trackbars", 255, 255, nothing)
cv2.createTrackbar("V1 Min", "Trackbars", 100, 255, nothing)
cv2.createTrackbar("V1 Max", "Trackbars", 255, 255, nothing)

# 第二組 HSV
cv2.createTrackbar("H2 Min", "Trackbars", 170, 180, nothing)
cv2.createTrackbar("H2 Max", "Trackbars", 180, 180, nothing)
cv2.createTrackbar("S2 Min", "Trackbars", 100, 255, nothing)
cv2.createTrackbar("S2 Max", "Trackbars", 255, 255, nothing)
cv2.createTrackbar("V2 Min", "Trackbars", 100, 255, nothing)
cv2.createTrackbar("V2 Max", "Trackbars", 255, 255, nothing)

while True:
    # 第一組參數
    h1_min = cv2.getTrackbarPos("H1 Min", "Trackbars")
    h1_max = cv2.getTrackbarPos("H1 Max", "Trackbars")
    s1_min = cv2.getTrackbarPos("S1 Min", "Trackbars")
    s1_max = cv2.getTrackbarPos("S1 Max", "Trackbars")
    v1_min = cv2.getTrackbarPos("V1 Min", "Trackbars")
    v1_max = cv2.getTrackbarPos("V1 Max", "Trackbars")

    # 第二組參數
    h2_min = cv2.getTrackbarPos("H2 Min", "Trackbars")
    h2_max = cv2.getTrackbarPos("H2 Max", "Trackbars")
    s2_min = cv2.getTrackbarPos("S2 Min", "Trackbars")
    s2_max = cv2.getTrackbarPos("S2 Max", "Trackbars")
    v2_min = cv2.getTrackbarPos("V2 Min", "Trackbars")
    v2_max = cv2.getTrackbarPos("V2 Max", "Trackbars")

    # 兩組範圍
    lower1 = np.array([h1_min, s1_min, v1_min])
    upper1 = np.array([h1_max, s1_max, v1_max])
    lower2 = np.array([h2_min, s2_min, v2_min])
    upper2 = np.array([h2_max, s2_max, v2_max])

    # 過濾 mask
    mask1 = cv2.inRange(img_hsv, lower1, upper1)
    mask2 = cv2.inRange(img_hsv, lower2, upper2)
    mask = cv2.bitwise_or(mask1, mask2)  # 合併兩組

    result = cv2.bitwise_and(img, img, mask=mask)

    cv2.imshow("Original", img)
    cv2.imshow("Mask", mask)
    cv2.imshow("Result", result)

    key = cv2.waitKey(1) & 0xFF
    if key == 27:  # ESC 離開
        break
    elif key == ord("s"):  # 存檔
        hsv_ranges = {
            "range1": {"lower": lower1.tolist(), "upper": upper1.tolist()},
            "range2": {"lower": lower2.tolist(), "upper": upper2.tolist()}
        }
        print("儲存 HSV 範圍:", hsv_ranges)
        with open("hsv_ranges.txt", "a") as f:
            f.write(str(hsv_ranges) + "\n")

cv2.destroyAllWindows()
