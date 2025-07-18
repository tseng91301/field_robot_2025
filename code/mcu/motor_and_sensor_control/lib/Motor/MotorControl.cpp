#include "MotorControl.h"
#include <Arduino.h>
#include<SerialTools.h>
#include <TimerOne.h>

Motor::Motor(int in1, int in2): in1(in1), in2(in2) {
    init();
    return;
}
Motor::Motor(int in1, int in2, int encoderA, int encoderB): in1(in1), in2(in2), encoderA(encoderA), encoderB(encoderB) {
    have_encoder_pin = true;
    init();
    return;
}
Motor::Motor(int in1, int in2, int encoderA, int encoderB, void (*isr)()): in1(in1), in2(in2), encoderA(encoderA), encoderB(encoderB) {
    have_encoder_pin = true;
    init();
    attach_interrupt_isr(isr);
    return;
}

void Motor::init() {
    if(have_encoder_pin) {
        pinMode(encoderA, INPUT_PULLUP);
        pinMode(encoderB, INPUT_PULLUP);
    }
    pinMode(in1, OUTPUT);
    pinMode(in2, OUTPUT);
    target_speed = 0;
    return;
}

void Motor::encoder() {
    static bool lastA = LOW;
    bool A = digitalRead(encoderA);
    bool B = digitalRead(encoderB);

    if (A != lastA && A == HIGH) {  // A 腳 rising edge
        if (B == LOW) {
            encoderPos++;
        } else {
            encoderPos--;
        }
    }
    lastA = A;
}


void Motor::attach_interrupt_isr(void (*isr)()) {
    attachInterrupt(digitalPinToInterrupt(encoderA), isr, CHANGE);
    have_encoder = true;
    return;
}

void Motor::update_speed() {
    static int last_encoderPos = 0;
    motor_speed = (encoderPos - last_encoderPos) / (double)(read_speed_interval * 0.001) * 60.0 / 7.0 / 27.0;
    Serial.print("Speed: ");
    Serial.println(motor_speed);
    last_encoderPos = encoderPos = 0;
    return;
}

void Motor::set_speed(int spd) {
    target_speed = spd;
    uint8_t response[] = {0xFF, callback_byte, 0x00, 0x0A};
    send_bytes(response, 4);
    return;
}

void Motor::_turn(int spd) {
    if(spd > 0) {
        analogWrite(in1, spd);
        analogWrite(in2, 0);
    }else if(spd < 0) {
        analogWrite(in1, 0);
        analogWrite(in2, spd * -1);
    }else {
        digitalWrite(in1, LOW);
        digitalWrite(in2, LOW);
    }
    return;
}

void Motor::service() {
    static unsigned long last_speed_update_time = 0;
    unsigned long now_time = millis();
    if(now_time - last_speed_update_time > read_speed_interval) {
        last_speed_update_time = now_time;
        update_speed();
    }
    int output;
    if(motor_enabled) {
        e = motor_speed - target_speed;
        e_integral += e;
        double derivative = e - e_prev;
        e_prev = e;
        output = kP * e + kI * e_integral + kD * derivative;
        // Serial.print("P: ");
        // Serial.print(kP * e);
        // Serial.print(" I: ");
        // Serial.print(kI * e_integral);
        // Serial.print(" D: ");
        // Serial.print(kD * derivative);
        // Serial.print(" Output: ");
        // Serial.println(output);
        if(output > 255) {
            output = 255;
        }else if(output < -255) {
            output = -255;
        }
    }else {
        output = 0;
    }
    _turn(output);
    delay(1);
    return;
}