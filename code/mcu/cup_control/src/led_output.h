#ifndef LED_CONFIG_H
#define LED_CONFIG_H
#include <Arduino.h>
#define DISTRIBUTION_LED_R_PIN 4
#define DISTRIBUTION_LED_G_PIN 3
#define DISTRIBUTION_LED_B_PIN 2

void init_weight_distribute_led() {
    pinMode(DISTRIBUTION_LED_R_PIN, OUTPUT);
    pinMode(DISTRIBUTION_LED_G_PIN, OUTPUT);
    pinMode(DISTRIBUTION_LED_B_PIN, OUTPUT);
    return;
}

void set_weight_distribute(uint8_t color) {
    switch (color) {
        case 1: // Green
            digitalWrite(DISTRIBUTION_LED_R_PIN, LOW);
            analogWrite(DISTRIBUTION_LED_G_PIN, 255);
            digitalWrite(DISTRIBUTION_LED_B_PIN, LOW);
            break;
        case 2: // Yellow
            digitalWrite(DISTRIBUTION_LED_R_PIN, HIGH);
            analogWrite(DISTRIBUTION_LED_G_PIN, 80);
            digitalWrite(DISTRIBUTION_LED_B_PIN, LOW);
            break;
        case 3: // Red
            digitalWrite(DISTRIBUTION_LED_R_PIN, HIGH);
            analogWrite(DISTRIBUTION_LED_G_PIN, 0);
            digitalWrite(DISTRIBUTION_LED_B_PIN, LOW);
            break;
        default:
            digitalWrite(DISTRIBUTION_LED_R_PIN, LOW);
            digitalWrite(DISTRIBUTION_LED_G_PIN, LOW);
            digitalWrite(DISTRIBUTION_LED_B_PIN, LOW);
            break;
    }

}

#endif