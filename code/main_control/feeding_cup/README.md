# 主控電腦端 - 飼料杯控制程式使用說明
## include 部分
本程式會使用 serial connection 功能，因此需要在 main 程式的路徑下放置 `serial_connection/` 專案
## 參數設置部分
1. `ser`: 放入一個 `serial_connection.Serial` 物件
2. `initial_step`: 飼料杯步進馬達的初始位置，預設 0 ，使用 `set_initial_step()` 函式設置
3. `trigger_step`: 飼料杯步進馬達伸長時走的步數，可直接設置
4. `now_step`: 紀錄步進馬達目前的位置，需要校正時直接調整