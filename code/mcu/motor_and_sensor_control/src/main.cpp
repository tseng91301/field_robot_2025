#include <Arduino.h>
#include <MotorControl.h>

#define MOTOR_L1 3
#define MOTOR_L2 11
#define ENCODER_LA 2
#define ENCODER_LB 4
#define MOTOR_R1 9
#define MOTOR_R2 10
#define ENCODER_RA 5
#define ENCODER_RB 8

Motor *motorL = nullptr;
Motor *motorR = nullptr;

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
        case 0xA1: return 2;  // 左馬達速度
        case 0xA2: return 2;  // 右馬達速度
        case 0xB1: return 4;  // 其他指令（範例）
        default: return 0;
    }
}

void processCommand(uint8_t cmd, uint8_t* data) {
    switch (cmd) {
        case 0xA1: {
            uint8_t sign = data[0];
            uint8_t abs_value = data[1];
            int16_t speed = (sign == 0) ? abs_value : -abs_value;
            motorL->set_speed(speed);
            // Serial.print("Set Left Motor Speed: ");
            // Serial.println(speed);
            break;
        }
        case 0xA2: {
            uint8_t sign = data[0];
            uint8_t abs_value = data[1];
            int16_t speed = (sign == 0) ? abs_value : -abs_value;
            motorR->set_speed(speed);
            // Serial.print("Set Right Motor Speed: ");
            // Serial.println(speed);
            break;
        }
        case 0xB1: {
            // 其他指令處理
            break;
        }
        default:
            Serial.println("Unknown command");
            break;
    }
}

/// @brief Motor Encoder ISR Function
void encoderISR_L() {
    if (motorL) motorL->encoder();
}
void encoderISR_R() {
    if (motorR) motorR->encoder();
}

void setup() {
    Serial.begin(115200);
    motorL = new Motor(MOTOR_L1, MOTOR_L2, ENCODER_LA, ENCODER_LB, encoderISR_L);
    motorL->set_callback_byte(0xA1);
    motorR = new Motor(MOTOR_R1, MOTOR_R2, ENCODER_RA, ENCODER_RB, encoderISR_R);
    motorR->set_callback_byte(0xA2);
    // Serial.println("Ready. Send speed:");
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

    // 馬達服務
    motorL->service();
}
