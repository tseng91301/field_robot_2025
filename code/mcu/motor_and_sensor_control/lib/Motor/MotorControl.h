#pragma once

#include<Arduino.h>


class Motor {
    private:
        // Pin Definition
        bool have_encoder = false;
        bool have_encoder_pin = false;
        int in1;
        int in2;
        int encoderA;
        int encoderB;
        
        // Switch
        bool motor_enabled = true;

        // Encoder Reading
        unsigned long read_speed_interval = 150;
        
        double encoderSpeed = 0;

        // PID Control constants
        double kP = 1.2;
        double kI = 0.004;
        double kD = 0.0;
        double e_prev = 0;
        double e = 0;
        double e_integral = 0;

        // Speed Control
        int target_speed;
        void _turn(int spd);
        void update_speed();
        double motor_speed = 0;

        // init
        void init();

        // Serial command callback
        uint8_t callback_byte;

    public:
        volatile long encoderPos = 0;
        // Construction
        Motor(int in1, int in2); // Without encoder
        Motor(int in1, int in2, int encoderA, int encoderB); // With encoder
        Motor(int in1, int in2, int encoderA, int encoderB, void (*isr)()); // With encoder and ISR

        // Public Function Call
        void attach_interrupt_isr(void (*isr)());
        void set_callback_byte(uint8_t callback_byte) { this->callback_byte = callback_byte; }

        void set_speed(int inp);
        double get_current_speed();

        // encoder function
        void encoder();

        // Loop Service
        void service();

};
