#include "MotorControl.h"
#include <Arduino.h>

Motor::Motor(int in1, int in2): in1(in1), in2(in2) {
    init();
    return;
}
Motor::Motor(int in1, int in2, int encoderA, int encoderB): in1(in1), in2(in2), encoderA(encoderA), encoderB(encoderB) {
    init();
    return;
}
Motor::Motor(int in1, int in2, int encoderA, int encoderB, void (*isr)(), int mode=CHANGE): in1(in1), in2(in2), encoderA(encoderA), encoderB(encoderB) {
    init();
    attach_interrupt_isr(isr, mode);
    return;
}

void Motor::init() {
    if(have_encoder_pin) {
        pinMode(encoderA, INPUT);
        pinMode(encoderB, INPUT);
    }
    pinMode(in1, OUTPUT);
    pinMode(in2, OUTPUT);
    return;
}

void Motor::encoder() {
    if(digitalRead(encoderA) == LOW) {
        return;
    }
    int encoder_a_val = digitalRead(encoderA);
    int encoder_b_val = digitalRead(encoderB);
    if(encoder_a_val == encoder_b_val) {
        encoderPos++;
    }else {
        encoderPos--;
    }
    return;
}

void Motor::attach_interrupt_isr(void (*isr)(), int mode) {
    attachInterrupt(digitalPinToInterrupt(encoderA), isr, mode);
    have_encoder = true;
    return;
}

void Motor::update_speed() {
    static int last_encoderPos = 0;
    motor_speed = (last_encoderPos - encoderPos) / (double)((double)read_speed_interval * 0.001) * 60 / 7 / 27; // RPM
    last_encoderPos = encoderPos = 0;
    return;
}

void Motor::set_speed(int spd) {
    target_speed = spd;
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
        e = target_speed - motor_speed;
        e_integral += e;
        double derivative = e - e_prev;
        e_prev = e;
        output = kP * e + kI * e_integral + kD * derivative;
        if(output > 255) {
            output = 255;
        }else if(output < -255) {
            output = -255;
        }
    }else {
        output = 0;
    }
    _turn(output);
    return;
}