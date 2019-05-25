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

/*
 * WARNING:
 * Remember to comment the ISR not in IRAM error in:
 * ~/.platformio/packages/framework-arduinoespressif8266@2.20501.190515/cores/esp8266/core_esp8266_wiring_digital.cpp
 */


#include <ESP8266WiFi.h>
#include <DNSServer.h>
#include <ESP8266HTTPClient.h>
#include <WiFiClientSecureBearSSL.h>

#include <WiFiManager.h>
#include <EEPROM.h>
#include <ArduinoJson.h>
#include "I2Cdev.h"

#define __AVR__
#include "MPU6050_6Axis_MotionApps20.h"
#include "Wire.h"

//#define PRINTLN(x) Serial.println(x)
//#define PRINT(x) Serial.print(x)
#define PRINTLN(x)
#define PRINT(x)

#define INTERRUPT_PIN D5

//#define OUTPUT_READABLE_GRAVITY

#define FACES_NUMBER                9
#define FACE_CHANGE_DELAY_THRESHOLD 2000UL
#define FACE_CHECK_DELAY            500UL
#define JSON_BUFFER_SIZE            200

#define HTTP_CONNECTION_TIMEOUT     10000UL

#define AUTHENTICATION_RETRIES      3
#define NOTIFY_FACE_RETRIES         3

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
const String HOSTNAME = "timetracker.mariotti.dev";
const uint8_t fingerprint[20] = {0x47, 0xD2, 0x02, 0xDA, 0xD0, 0xE7, 0xFF, 0xE6, 0xE7, 0x04, 0xB6, 0x4C, 0x2D, 0x3A, 0x51, 0x7F, 0x77, 0x8E, 0x7E, 0x29};

const int PORT = 443;

MPU6050 mpu;

bool dmpInitialized = false;
uint8_t mpuIntStatus;
uint8_t devStatus;
uint16_t packetSize;
uint16_t fifoCount;
uint8_t fifoBuffer[128];

int lastFace = FACES_NUMBER;
int lastConfirmedFace = FACES_NUMBER;
unsigned long lastFaceChange = 0UL;
unsigned long faceCheckTimer = 0UL;
String token = "";
bool authenticated = false;

struct {
  char username[40] = "";
  char password[40] = "";
} credentials;

void resetWifi() {
  PRINTLN("RESETTING WIFI SETTINGS");
  WiFi.disconnect(true);
  delay(3000);
  ESP.reset();
  delay(3000);
}

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
    PRINTLN(digitalPinToInterrupt(INTERRUPT_PIN));
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

bool authenticateAux() {
  bool result = false;

  PRINT(F("Authenticating with credentials: "));
  PRINT(String(credentials.username));
  PRINT(F(" - "));
  PRINTLN(String(credentials.password));

  String postData;
  {
    StaticJsonDocument<JSON_BUFFER_SIZE> doc;
    doc["username"] = String(credentials.username);
    doc["password"] = String(credentials.password);
    serializeJson(doc, postData);

    PRINT("Payload is: ");
    PRINTLN(postData);
  }

  int httpCode = -1;
  String payload;

  std::unique_ptr<BearSSL::WiFiClientSecure>client(new BearSSL::WiFiClientSecure);
  client->setFingerprint(fingerprint);

  HTTPClient https;
  if (https.begin(*client, "https://" + HOSTNAME + "/login/")) {
    https.addHeader("Content-Type", "application/json");
    httpCode = https.POST(postData);
    payload = https.getString();
    https.end();
  }
  
  PRINTLN(httpCode);
  PRINTLN(payload);

  if (httpCode == 200) {
    StaticJsonDocument<JSON_BUFFER_SIZE> doc;
    deserializeJson(doc, payload);
    token = String(doc["token"].as<String>());

    PRINTLN(F("AUTHENTICATED! TOKEN: "));
    PRINTLN(token);
    authenticated = true;
    result = true;
  } else {
    PRINTLN("NOT AUTHENTICATED");
    authenticated = false;
  }

  return result;
}

void authenticate() {
  int _try = 0;

  while (_try < AUTHENTICATION_RETRIES) {
    PRINT("Authentication try ");
    PRINTLN(_try);
    if (authenticateAux()) {
      return;
    }
    _try++;
  }

  resetWifi();
}

int notifyFaceChangedAux(int currentFace) {
  PRINT(F("Notifying change to face: "));
  PRINTLN(currentFace);

  int httpCode = -1;
  String payload;
  String postData = "HelloWorld";

  std::unique_ptr<BearSSL::WiFiClientSecure>client(new BearSSL::WiFiClientSecure);
  client->setFingerprint(fingerprint);

  HTTPClient https;
  PRINT("AUTHENTICATING WITH: ");
  PRINTLN(token);
  
  if (https.begin(*client, "https://" + HOSTNAME + "/faces/" + String(currentFace))) {  // HTTPS
    https.addHeader("Authorization", "Token " + token);  
    https.addHeader("Content-Type", "application/json");

    httpCode = https.POST(postData);
    payload = https.getString();

    https.end();
  } 

  return httpCode;
}

void notifyFaceChanged(int currentFace) {
  int _try = 0;

  while (_try < NOTIFY_FACE_RETRIES) {
    PRINT("NOTIFYING FACE CHANGE TRY ");
    PRINTLN(_try);

    int httpCode = notifyFaceChangedAux(currentFace);

    if (httpCode == 200) {
      PRINTLN("FACE CHANGED NOTIFIED!");
      return;
    } else if (httpCode == 401) {
      PRINTLN("UNAUTHORIZED CALL.. AUTHENTICATING AND TRYING AGAIN!");
      authenticate();
    } else {
      PRINT("FACE CHANGED FAILED WITH STATUS ");
      PRINTLN(httpCode);
    }

    _try++;
  }
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
    Quaternion q;
    VectorFloat gravity;

    while (fifoCount < packetSize) {
      fifoCount = mpu.getFIFOCount();
    }

    mpu.getFIFOBytes(fifoBuffer, packetSize);
    fifoCount -= packetSize;

    mpu.dmpGetQuaternion(&q, fifoBuffer);
    mpu.dmpGetGravity(&gravity, &q);

    if (faceCheckTimer <= (millis() - FACE_CHECK_DELAY)) {
      faceCheckTimer = millis();
      int currentFace = getCurrentFace(&gravity);
      if (isFaceChanged(currentFace)) {
	notifyFaceChanged(currentFace);
      }

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

bool initEEPROM() {
  EEPROM.begin(512);
  EEPROM.get(0, credentials);

  PRINTLN("CURRENT USERNAME:");
  PRINTLN(credentials.username);

  if (strlen(credentials.username) > 32) {
    PRINTLN("NO USERNAME FOUND, RESETTING");
    strncpy(credentials.username, "", 40);
    strncpy(credentials.password, "", 40);
    return false;
  }

  return true;
}

void setup(void) {
  Serial.begin(9600);

  initEEPROM();

  WiFiManager wifiManager;

  WiFiManagerParameter ttUsername("ttusername", "TimeTrackerDice username", credentials.username, 40);
  wifiManager.addParameter(&ttUsername);
  WiFiManagerParameter ttPassword("ttpassword", "TimeTrackerDice password", credentials.password, 40);
  wifiManager.addParameter(&ttPassword);

  bool connected = wifiManager.autoConnect(DEVICE_NAME);

  if (connected) {
    PRINT(F("WiFi connected! IP address: "));
    PRINTLN(WiFi.localIP());

    PRINTLN(ttUsername.getValue());

    strncpy(credentials.username, ttUsername.getValue(), 40);
    strncpy(credentials.password, ttPassword.getValue(), 40);

    authenticate();
    
    mpuSetup();

    EEPROM.put(0, credentials);
    EEPROM.commit();
  }
}

void loop(void) {
  if (WiFi.status() != WL_CONNECTED) {
    PRINTLN("*** Disconnected from AP so rebooting ***");
    ESP.reset();
  }

  //  if (authenticated) {
  mpu_loop();
    //}
}
