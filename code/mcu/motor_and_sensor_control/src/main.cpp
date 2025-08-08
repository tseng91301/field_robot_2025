#include <Arduino.h>
#include <MotorControl.h>
#include <Wire.h>
#include <MPU6050_light.h>
#include <Accelerator.h>

#define MOTOR_L1 5
#define MOTOR_L2 6
#define ENCODER_LA 2
#define ENCODER_LB 4
#define MOTOR_R1 9
#define MOTOR_R2 10
#define ENCODER_RA 5
#define ENCODER_RB 8

Motor *motorL = nullptr;
Motor *motorR = nullptr;
DualMotor dualMotor(motorL, motorR);

MPU6050 mpu(Wire);
Location location(&mpu);

double KP = 0.1;
double KI = 0.1;
double KD = 0.1;

/// @brief Motor Encoder ISR Function
void encoderISR_L() {
    if (motorL) motorL->encoder();
}
void encoderISR_R() {
    if (motorR) motorR->encoder();
}

void setup() {
    Serial.begin(115200);

    Wire.begin();
    byte status = mpu.begin();
    if (status != 0) {
        Serial.println("MPU6050 initialization failed!");
        while (1);
    }
    delay(1000);
    mpu.calcOffsets(); // 校正零點（請保持靜止）

    // 初始化馬達腳位和 encoder function
    motorL = new Motor(MOTOR_L1, MOTOR_L2, ENCODER_LA, ENCODER_LB, encoderISR_L);
    motorL->set_callback_byte(0xA1);
    motorR = new Motor(MOTOR_R1, MOTOR_R2, ENCODER_RA, ENCODER_RB, encoderISR_R);
    motorR->set_callback_byte(0xA2);

    dualMotor.speed = 1.0;
}

void loop() {
    static double pe = 0.0; // Previous error
    static double i = 0.0; // I value

    // 計算前進的旋轉偏移量，並做出 PID 控制校正
    double e = location.gyro_z;
    i += e;
    double d = e - pe;
    pe = e;
    double correction = KP * e + KI * i + KD * d;

    dualMotor.set_direction(-correction);

    // 馬達服務
    dualMotor.service();

    // 位置計算服務
    location.service();
}
