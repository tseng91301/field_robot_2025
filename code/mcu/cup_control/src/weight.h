#ifndef WEIGHT_H
#define WEIGHT_H
#include <Arduino.h>
#include "HX711.h"

class Weight {
    private:
        int dt;
        int sck;
        int scale_factor;
        HX711 scale;
    
    public:
        Weight(int dt_p, int sck_p, int f) {
            dt = dt_p;
            sck = sck_p;
            scale_factor = f;
            scale.begin(dt, sck);
            scale.set_scale(scale_factor);
            scale.tare();
        }

        void tare() {
            scale.tare();
        }

        float get_weight(int times = 1) {
            float w = scale.get_units(times);
            return w;
        }
};
#endif