## 指令架構
### 傳輸協議
使用 Serial Connection 做為基底
一個傳輸封包有的東西:
1. 起始字元 0xFF
2. 指令名稱 [一個 byte 的數據，參閱附錄對照表]
3. 指令內容 [多個 bytes ，視指令同而變動]
4. 指令結尾 0x0A

接收流程:
* MCU 一開始狀態是 `WAIT_START`
* 讀到 0xFF 時，狀態改變為 `WAIT_COMMAND`
* 狀態為 `WAIT_COMMAND` 時，接收到一個 byte 會變成指令碼，接著狀態改為 `WAIT_DATA`
* 狀態為 `WAIT_DATA` 時，會持續接收內容並擴充 byte 陣列
* 當接收到的 data byte 數量達到 特定 command 定義的數量，會停止接收，並等待 0x0A，狀態更改為 `WAIT_END`
* 狀態為 `WAIT_END` 並讀取到 0x0A，將狀態改回 `WAIT_START`，同時執行對應指令

## Appendix
指令架構:
* 0xA1: 設定左馬達速度 buffer: 2bytes (第一個是正負號，0 為正； 1 為負，第二個是數值 0 ~ 255)
* 0xA2: 設定右馬達速度 buffer: 2bytes (同上)