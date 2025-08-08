#include <Arduino.h>
#include <MotorControl.h>
#include <Wire.h>
#include <MPU6050_light.h>
#include <Accelerator.h>
#include <SerialTools.h>

#define MOTOR_L1 5
#define MOTOR_L2 6
#define ENCODER_LA 2
#define ENCODER_LB 4
#define MOTOR_R1 9
#define MOTOR_R2 10
#define ENCODER_RA 3
#define ENCODER_RB 8

Motor *motorL = nullptr;
Motor *motorR = nullptr;
DualMotor dualMotor(motorL, motorR);

MPU6050 mpu(Wire);
Location location(&mpu);
SerialUtils<HardwareSerial> serial(&Serial, 115200, '\n');

float KP = 0.0;
float KI = 0.0;
float KD = 0.0;

/// @brief Motor Encoder ISR Function
void encoderISR_L() {
    if (motorL) motorL->encoder();
}
void encoderISR_R() {
    if (motorR) motorR->encoder();
}

void set_pid(String input) {
  float kp, ki, kd;

  int firstSpace = input.indexOf(' ');
  int secondSpace = input.indexOf(' ', firstSpace + 1);
  
  if (firstSpace == -1 || secondSpace == -1) {
    Serial.println("Invalid Input");
    return;
  }

  String kp_str = input.substring(0, firstSpace);
  String ki_str = input.substring(firstSpace + 1, secondSpace);
  String kd_str = input.substring(secondSpace + 1);

  kp = kp_str.toFloat();
  ki = ki_str.toFloat();
  kd = kd_str.toFloat();

  if (kp == 0 && kp_str != "0" && kp_str != "0.0") {
    Serial.println("Invalid kp");
    return;
  }
  if (ki == 0 && ki_str != "0" && ki_str != "0.0") {
    Serial.println("Invalid ki");
    return;
  }
  if (kd == 0 && kd_str != "0" && kd_str != "0.0") {
    Serial.println("Invalid kd");
    kd = 0.0;
  }

  Serial.print("Kp=");
  Serial.print(kp);
  Serial.print(", Ki=");
  Serial.print(ki);
  Serial.print(", Kd=");
  Serial.println(kd);

  // 這裡可以把 kp, ki, kd 賦值給全域變數或 PID 參數
  KP = kp;
  KI = ki;
  KD = kd;
}

void setup() {
    Serial.begin(115200);

    while(1) {
        Wire.begin();
        byte status = mpu.begin();
        if (status != 0) {
            Serial.println("MPU6050 initialization failed!");
            delay(300);
        } else {
            break;
        }
    }
    
    delay(1000);
    mpu.calcOffsets(); // 校正零點（請保持靜止）

    // 初始化馬達腳位和 encoder function
    motorL = new Motor(MOTOR_L1, MOTOR_L2, ENCODER_LA, ENCODER_LB, encoderISR_L);
    motorL->set_callback_byte(0xA1);
    motorL->reversed = true;
    motorR = new Motor(MOTOR_R1, MOTOR_R2, ENCODER_RA, ENCODER_RB, encoderISR_R);
    motorR->set_callback_byte(0xA2);

    dualMotor.speed = 1.0;
}

void loop() {
    static double pe = 0.0; // Previous error
    static double i = 0.0; // I value

    if(serial.queue_size() > 0) {
        String msg = serial.get_buffer();
        set_pid(msg);
    }

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
    // static unsigned long last_print_gyroZ_time = millis();
    // unsigned long now_time = millis();
    // if (now_time - last_print_gyroZ_time > 100) {
    //     Serial.println(location.gyro_z);
    //     last_print_gyroZ_time = now_time;
    // }

    // 指令接收器
    serial.service();
}
