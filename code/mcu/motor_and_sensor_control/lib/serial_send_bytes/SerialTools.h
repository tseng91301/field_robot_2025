#pragma once

#include<Arduino.h>
void send_bytes(uint8_t *bytes, int length) {
    for(int i = 0; i < length; i++) {
        Serial.write(bytes[i]);
    }
    return;
}