#include <Arduino.h>
#include <Stepper.h>
#include "weight.h"
#include "led_output.h"

#define STEPS_PER_RESOLUTION 2048
Stepper myStepper(STEPS_PER_RESOLUTION, 8, 10, 9, 11);  // Initialize the stepper motor with 4 control pins

Weight weight(6, 5, -945);

void use_feeder(float target_weight) {
    myStepper.step(5000);    // Move the motor forward 9000 steps
    float weight_got = weight.get_weight();
    while (weight_got < target_weight) {
        weight_got = weight.get_weight();
    }
    myStepper.step(-5000);
}

// Byte command handle

#define START_BYTE 0xFF
enum ParseState {
    WAIT_START,
    WAIT_COMMAND,
    WAIT_DATA,
    WAIT_END
};
ParseState parseState = WAIT_START;
uint8_t command = 0;
uint8_t *dataBuffer;  // 你可以根據需求調整
uint8_t dataLength = 0;
uint8_t bytesRead = 0;

uint8_t getDataLengthForCommand(uint8_t cmd) {
    switch (cmd) {
        case 0xB1: return 1; // 查看重量 (會有延遲 + 回傳)
        case 0xB2: return 1; // 亮 led 燈
        case 0xB3: return 1; // 獲取對應重量的飼料 (會有延遲+回傳須同步)
        default: return 0;
    }
}

void processCommand(uint8_t cmd, uint8_t* data) {
    switch (cmd) {
        case 0xB1: { // 查看重量
            uint8_t _ = data[0];
            float weight_value = weight.get_weight();
            // Serial.print("Weight: ");
            // Serial.println(weight_value);
            byte *b = (byte*)&weight_value;
            for (int i = 0; i < 4; i++) Serial.write(b[i]);
            delete data;
            break;
        }
        case 0xB2: { // 設定重量分類 LED 燈顏色
            uint8_t color = data[0];
            set_weight_distribute(color);
            delete data;
            break;
        }
        case 0xB3: {
            uint8_t target_weight = data[0];
            use_feeder(target_weight);
            delete data;
            Serial.write(0xB3); // Return success value
            break;
        }
        default:
            Serial.println("Unknown command");
            break;
    }
}

void setup() {
    Serial.begin(115200);
    pinMode(LED_BUILTIN, OUTPUT);
    init_weight_distribute_led();
    weight.tare();
    myStepper.setSpeed(15);  // Set motor speed to 15 RPM (rotations per minute)
}

void loop() {
    // 讀取 Serial 資料
    if (Serial.available()) {
        uint8_t read_byte = Serial.read();
        switch (parseState) {
            case WAIT_START:
                if (read_byte == START_BYTE) {
                    parseState = WAIT_COMMAND;
                }
                break;
            case WAIT_COMMAND:
                command = read_byte;
                dataLength = getDataLengthForCommand(command);
                dataBuffer = new uint8_t[dataLength];
                bytesRead = 0;
                if (dataLength == 0) {
                    parseState = WAIT_START;  // 無效指令
                } else {
                    parseState = WAIT_DATA;
                }
                break;
            case WAIT_DATA:
                dataBuffer[bytesRead++] = read_byte;
                if (bytesRead >= dataLength) {
                    parseState = WAIT_END;
                }
                break;
            case WAIT_END:
                if (read_byte == '\n') {
                    processCommand(command, dataBuffer);
                } else {
                    Serial.println("Invalid packet end");
                }
                parseState = WAIT_START;  // 重置
                break;
        }
    }

}

