## 基本設定
### 設定 serial 指令的 buffer 大小
到 `serial_connection/commands.py` ，修改 `commands_len`
裡面有個整指令類型對應到的指令 buffer 長度

### Command Handle
mcu 回傳的回應頭:
* 0x01: 指令回應，內容 buffer 1 bytes