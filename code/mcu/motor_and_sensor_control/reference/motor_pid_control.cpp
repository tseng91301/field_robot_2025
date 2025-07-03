#include <Arduino.h>
#include <TimerOne.h>

volatile long encoderPos = 0;
double encoderSpeed = 0;

const unsigned long read_speed_interval = 100; // ms

void encoder();

#define MOTOR_1 5
#define MOTOR_2 6

#define ENCODER_A 2
#define ENCODER_B 7

#define kP 1.5
#define kI 0.08
#define kD 0

int TARGET_SPEED = 100; // RPM

int lasterror = 0;
long long integral = 0;

int motor_speed = 0;

bool motor_enabled = true;

void _turn(int speed) {
    if(motor_enabled == false) {
        digitalWrite(MOTOR_1, LOW);
        digitalWrite(MOTOR_2, LOW);
        return;
    }
    if(speed > 0) {
        analogWrite(MOTOR_1, speed);
        analogWrite(MOTOR_2, 0);
    }else if(speed < 0) {
        analogWrite(MOTOR_1, 0);
        analogWrite(MOTOR_2, speed * -1);
    }else {
        digitalWrite(MOTOR_1, LOW);
        digitalWrite(MOTOR_2, LOW);
    }
}
void update_speed() {
    static int last_encoderPos = 0;
    motor_speed = (last_encoderPos - encoderPos) / (double)((double)read_speed_interval * 0.001) * 60 / 7 / 27;
    last_encoderPos = encoderPos = 0;
    Serial.println(motor_speed);
    static int output = 0;
    if(motor_enabled) {
        int error = TARGET_SPEED - motor_speed;
        integral += error;
        int derivative = error - lasterror;
        lasterror = error;
        output += kP * error + kI * integral + kD * derivative;
        if(output > 255) {
            output = 255;
        }else if(output < -255) {
            output = -255;
        }
    }
    // Serial.println("Output: " + String(output));
    _turn(output);
    // _turn(120);
}



void setup() {
    pinMode(MOTOR_1, OUTPUT);
    pinMode(MOTOR_2, OUTPUT);
    pinMode(ENCODER_A, INPUT_PULLUP);
    pinMode(ENCODER_B, INPUT_PULLUP);

    Serial.begin(115200);
    
    attachInterrupt(digitalPinToInterrupt(ENCODER_A), encoder, CHANGE);
    
}

void loop() {
    if(Serial.available() > 0) {
        char c = Serial.read();
        if(c == 's') {
            motor_enabled = !motor_enabled;
        }
    }
    static unsigned long last_speed_time = 0;
    unsigned long time = millis();
    if(time - last_speed_time > read_speed_interval) {
        last_speed_time = time;
        update_speed();
    }
    // Serial.print("P: ");
    // Serial.print(kP * error);
    // Serial.print(" I: ");
    // Serial.print(kI * integral);
    // Serial.print(" D: ");
    // Serial.print(kD * derivative);
    // Serial.print(" Output: ");
    // Serial.println(output);
    
}

void encoder() {
    if(digitalRead(ENCODER_A) == LOW) {
        return;
    }
    int encoder_a_val = digitalRead(ENCODER_A);
    int encoder_b_val = digitalRead(ENCODER_B);
    if(encoder_a_val == encoder_b_val) {
        encoderPos++;
    }else {
        encoderPos--;
    }
}
