#include <Wire.h>
#include <MPU6050_light.h>

MPU6050 mpu(Wire);
#define RESET_BTN 12

class Location {
  private:
    MPU6050 *mpu;
    unsigned long update_interval;
    unsigned long last_update_time;

  public:
    float x = 0;
    float y = 0;
    float z = 0;
    float gyro_x = 0;
    float gyro_y = 0;
    float gyro_z = 0;
    float acc_x = 0;
    float acc_y = 0;
    float acc_z = 0;
    float spd_x = 0;
    float spd_y = 0;
    float spd_z = 0;

    Location(MPU6050 *mpu, unsigned long update_interval = 100) {
      this->mpu = mpu;
      this->update_interval = update_interval;
      this->last_update_time = micros();
    }

    void reset() {
      x = 0;
      y = 0;
      z = 0;
      gyro_x = 0;
      gyro_y = 0;
      gyro_z = 0;
      acc_x = 0;
      acc_y = 0;
      acc_z = 0;
      spd_x = 0;
      spd_y = 0;
      spd_z = 0;
      last_update_time = micros();
    }

    void service() {
      mpu->update();

      acc_x = mpu->getAccX();
      acc_y = mpu->getAccY();
      acc_z = mpu->getAccZ();

      float acc_threshold = 0.004; // m/s²
      if (fabs(acc_x) < acc_threshold) acc_x = 0;
      if (fabs(acc_y) < acc_threshold) acc_y = 0;
      if (fabs(acc_z) < acc_threshold) acc_z = 0;
      
      acc_x *= 9.80665;
      acc_y *= 9.80665;
      acc_z *= 9.80665;

      gyro_x = mpu->getGyroX();
      gyro_y = mpu->getGyroY();
      gyro_z = mpu->getGyroZ();

      unsigned long time_now = micros();
      float dt = (time_now - last_update_time) / 1e6;  // seconds
      if (dt <= 0) return;

      // 可加門檻，例如 fabs(acc_x) > 0.2 才積分
      spd_x += acc_x * dt;
      spd_y += acc_y * dt;
      spd_z += acc_z * dt;

      x += spd_x * dt;
      y += spd_y * dt;
      z += spd_z * dt;

      last_update_time = time_now;
    }
};

Location location(&mpu);

void setup() {
  Serial.begin(9600);
  Wire.begin();
  byte status = mpu.begin();

  Serial.print("MPU6050 status: ");
  Serial.println(status);  // 0 = success

  if (status != 0) {
    Serial.println("MPU6050 initialization failed!");
    while (1);
  }

  delay(1000);  // 建議延遲時間
  mpu.calcOffsets();  // 校正零點（請保持靜止）
  Serial.println("Calibration done!");

  pinMode(RESET_BTN, INPUT_PULLUP);
}

void loop() {
  static unsigned long last_update_time = millis();
  unsigned long time_now = millis();

  location.service();

  // if (time_now - last_update_time > 150) {
  //   last_update_time = time_now;
  //   Serial.print("X: ");
  //   Serial.print(location.x);
  //   Serial.print(" | Y: ");
  //   Serial.print(location.y);
  //   Serial.print(" | Z: ");
  //   Serial.print(location.z);

  //   Serial.print(" || Gyro X: ");
  //   Serial.print(mpu.getGyroX());
  //   Serial.print(" | Y: ");
  //   Serial.print(mpu.getGyroY());
  //   Serial.print(" | Z: ");
  //   Serial.println(mpu.getGyroZ());
  // }

  if (time_now - last_update_time > 100) {
    Serial.println(location.acc_x);
  }

  if(digitalRead(RESET_BTN) == LOW) {
    location.reset();
  }
}
