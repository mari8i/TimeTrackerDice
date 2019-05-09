/* ============================================
I2Cdev device library code is placed under the MIT license
Copyright (c) 2012 Jeff Rowberg
Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:
The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
===============================================
*/

#include <ESP8266WiFi.h>
#include <DNSServer.h>
#include <WiFiClient.h>
#include <WiFiManager.h>
#include <ESP8266HTTPClient.h>
#include <EEPROM.h>
#include "I2Cdev.h"

#define __AVR__
#include "MPU6050_6Axis_MotionApps20.h"
#include "Wire.h"

#define PRINTLN(x) Serial.println(x)
#define PRINT(x) Serial.print(x)
//#define PRINTLN(x)
//#define PRINT(x)

#define INTERRUPT_PIN D5

#define OUTPUT_READABLE_GRAVITY

#define FACES_NUMBER                9
#define FACE_CHANGE_DELAY_THRESHOLD 5000UL
#define FACE_CHECK_DELAY            500UL


const VectorFloat faces[FACES_NUMBER] =
  {
   VectorFloat(1.0f,    0.0f,   0.0f),
   VectorFloat(-0.40f,	0.03f,	0.91f),
   VectorFloat(-0.38f,	0.92f,	-0.02f),
   VectorFloat(-0.37f,	0.02f,	-0.93f),
   VectorFloat(-0.40f,	-0.92f,	-0.03f),
   VectorFloat(0.32f,	0.01f,	0.95f),
   VectorFloat(0.32f,	0.95f,	-0.01f),
   VectorFloat(0.32f,	0.01f,	-0.95f),
   VectorFloat(0.32f,	-0.95f,	-0.01f)
  };

const char DEVICE_NAME[] = "TimeTrackerDice";

MPU6050 mpu;

bool dmpInitialized = false;
uint8_t mpuIntStatus;
uint8_t devStatus;
uint16_t packetSize;
uint16_t fifoCount;
uint8_t fifoBuffer[128];

Quaternion q;
VectorFloat gravity;

int lastFace = FACES_NUMBER;
int lastConfirmedFace = FACES_NUMBER;
unsigned long lastFaceChange = 0UL;
unsigned long faceCheckTimer = 0UL;

struct { 
  char username[40] = "";
  char password[40] = "";
} credentials;

WiFiClient wifiClient;

volatile bool mpuInterrupt = false;
void dmpDataReady() {
    mpuInterrupt = true;
}

void mpuSetup() {
  Wire.begin(D1, D2);
  Wire.setClock(400000);

  // initialize device
  PRINTLN(F("Initializing I2C devices..."));
  mpu.initialize();
  pinMode(INTERRUPT_PIN, INPUT);

  // verify connection
  PRINTLN(F("Testing device connections..."));
  PRINTLN(mpu.testConnection() ? F("MPU6050 connection successful") : F("MPU6050 connection failed"));

  // load and configure the DMP
  PRINTLN(F("Initializing DMP..."));
  devStatus = mpu.dmpInitialize();

  // make sure it worked (returns 0 if so)
  if (devStatus == 0) {
    // turn on the DMP, now that it's ready
    PRINTLN(F("Enabling DMP..."));
    mpu.setDMPEnabled(true);

    // enable Arduino interrupt detection
    PRINTLN(F("Enabling interrupt detection (Arduino external interrupt 0)..."));
    attachInterrupt(digitalPinToInterrupt(INTERRUPT_PIN), dmpDataReady, RISING);
    mpuIntStatus = mpu.getIntStatus();

    // set our DMP Ready flag so the main loop() function knows it's okay to use it
    PRINTLN(F("DMP ready! Waiting for first interrupt..."));
    dmpInitialized = true;

    // get expected DMP packet size for later comparison
    packetSize = mpu.dmpGetFIFOPacketSize();
  } else {
    // ERROR!
    // 1 = initial memory load failed
    // 2 = DMP configuration updates failed
    // (if it's going to break, usually the code will be 1)
    PRINT(F("DMP Initialization failed (code "));
    PRINT(devStatus);
    PRINTLN(F(")"));
  }
}

float getVectorDistance(VectorFloat* v1, VectorFloat* v2) {
  // Eucleidian distance is sqrt(sum((x1 - x2)^2 + (y1 - y2)^2 + (z1
  // - z2)^2)) But we need the value just for comparison, and the
  // faster the better, so we remove the sqrt

  return (pow(v1->x - v2->x, 2.0f) +
          pow(v1->y - v2->y, 2.0f) +
          pow(v1->z - v2->z, 2.0f));
}

int getCurrentFace(VectorFloat* gravity) {
  float min = 0.0f;
  int res = -1;

  for (int f = 0; f < FACES_NUMBER; f++) {
    VectorFloat vf = faces[f];
    float distance = getVectorDistance(gravity, &vf);
    if (res == -1 || distance < min) {
      res = f;
      min = distance;
    }
  }

  return res;
}

bool isFaceChanged(int currentFace) {
  bool faceChanged = false;

  if (lastFace != currentFace) {
    lastFace = currentFace;
    lastFaceChange = millis();
  } else if (lastConfirmedFace != currentFace &&
             lastFaceChange <= (millis() - FACE_CHANGE_DELAY_THRESHOLD)) {
    faceChanged = true;
    lastConfirmedFace = currentFace;
  }

  return faceChanged;
}

void notifyFaceChanged(int currentFace) {
  PRINT(F("Notifying change to face: "));
  PRINTLN(currentFace);

  HTTPClient http;
  String postData = "face=" + currentFace;

  http.begin(wifiClient, "http://192.168.1.143:8080/face/" + String(currentFace));
  http.addHeader("Content-Type", "application/x-www-form-urlencoded");

  int httpCode = http.POST(postData);
  String payload = http.getString();

  PRINTLN(httpCode);
  PRINTLN(payload);

  http.end();
}

void mpu_loop() {
  // if programming failed, don't try to do anything
  if (!dmpInitialized) return;

  // wait for MPU interrupt or extra packet(s) available
  if (!mpuInterrupt && fifoCount < packetSize) return;

  mpuInterrupt = false;
  mpuIntStatus = mpu.getIntStatus();

  fifoCount = mpu.getFIFOCount();

  // check for overflow (this should never happen unless our code is too inefficient)
  if ((mpuIntStatus & 0x10) || fifoCount == 1024) {
    mpu.resetFIFO();
    PRINTLN(F("FIFO overflow!"));
  } else if (mpuIntStatus & 0x02) {
    while (fifoCount < packetSize) {
      fifoCount = mpu.getFIFOCount();
    }

    mpu.getFIFOBytes(fifoBuffer, packetSize);
    fifoCount -= packetSize;

    mpu.dmpGetQuaternion(&q, fifoBuffer);
    mpu.dmpGetGravity(&gravity, &q);

    if (faceCheckTimer <= (millis() - FACE_CHECK_DELAY)) {
      int currentFace = getCurrentFace(&gravity);
      if (isFaceChanged(currentFace)) {
	notifyFaceChanged(currentFace);
      }
      faceCheckTimer = millis();

#ifdef OUTPUT_READABLE_GRAVITY
      PRINT("gravity\t");
      PRINT(gravity.x);
      PRINT("\t");
      PRINT(gravity.y);
      PRINT("\t");
      PRINTLN(gravity.z);
#endif
    }
  }
}

void setup(void) {
  Serial.begin(9600);
  EEPROM.begin(512);

  EEPROM.get(0, credentials);
  
  WiFiManager wifiManager;
  //wifiManager.resetSettings();
  
  WiFiManagerParameter ttUsername("ttusername", "TimeTrackerDice username", credentials.username, 40);
  wifiManager.addParameter(&ttUsername);
  WiFiManagerParameter ttPassword("ttpassword", "TimeTrackerDice password", credentials.password, 40);
  wifiManager.addParameter(&ttPassword);

  wifiManager.autoConnect(DEVICE_NAME);

  PRINT(F("WiFi connected! IP address: "));
  PRINTLN(WiFi.localIP());

  strncpy(credentials.username, ttUsername.getValue(), 40);
  strncpy(credentials.password, ttPassword.getValue(), 40);
  
  EEPROM.put(0, credentials);
  EEPROM.commit();
  
  mpuSetup();
}

void loop(void) {
  if (WiFi.status() != WL_CONNECTED) {
    PRINTLN("*** Disconnected from AP so rebooting ***");
    ESP.reset();
  }

  mpu_loop();
}
