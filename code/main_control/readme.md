## 程式架構
* 此資料夾頂層放的是可以直接執行的程式，例如 `main.py` 是機器人運行的主程式，也可以加入其他 test 程式檔案來測試函式庫等相關功能
* `line_follow/` 底下放的是與室內紅線循跡相關的程式碼，若要 import ，直接 import `__init__.py` 底下 import 的 class name 即可
    * `LineFollower` 負責循跡的部分，藉由紅線偏移來算出馬達校正方向
    * `StepCounter` 負責關卡計算，藉由觀察是否抵達紅線交叉點來判斷目前是否要進入下一關
* `motor/` 底下放的是與馬達相關的程式碼
* `serial_connection/` 底下放的是負責進行 Serial 通訊的程式碼
### 程式套件關聯性
1. `motor` 會調用 `serial_connection` 的函式，因此再引入 `motor` 函式庫不能缺乏 `serial_connection`


## 基本設定
### 設定 serial 指令的 buffer 大小
到 `serial_connection/commands.py` ，修改 `commands_len`
裡面有個整指令類型對應到的指令 buffer 長度

### Command Handle
mcu 回傳的回應頭:
* 0x01: 指令回應，內容 buffer 1 bytes