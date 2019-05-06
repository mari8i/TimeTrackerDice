# TimeTrackerDice

The TimeTrackerDice is a WiFi device that allows you to track the time
you spend on your tasks by simply switching the dice face!

This project is still a work in progress.

## How is it made

The TimeTrackerDice has a 3d-printed frame, designed using OnShape.

Here is the link of the project: https://cad.onshape.com/documents/e1ad1b4e8f5b8f67452415e8/w/5826cb1a892e7a9f9424e4a3/e/1ad90cf2e74edadef74df1f5

I will soon upload the STL files as well (also on ThingiVerse probably..)

The core of the TimeTrackerDice is a NodeMCU v2 WiFi
Microcontroller. An accelerometer (MPU-6050) is used to find out the
current dice face.

The Microcontroller is powered by a 18650 battery via a charger module.


## TODO

- [x] Drinking beer
- [ ] Microcontroller code
- [ ] Backend server (with Toggl integration)
- [ ] Frontend interface for better usability
- [ ] Authentication
- [ ] Sharing 3D Model
- [ ] Schematics
- [ ] App?
- [ ] Testing

## Useful links

- http://www.giuseppecaccavale.it/arduino/mpu-6050-gy-521-arduino-tutorial/
- https://github.com/jrowberg/i2cdevlib/tree/master/Arduino/MPU6050
- https://playground.arduino.cc/Main/MPU-6050/
- https://gzuliani.bitbucket.io/arduino/arduino-mpu6050.html
- https://www.instructables.com/id/MPU6050-Arduino-6-Axis-Accelerometer-Gyro-GY-521-B/
- https://github.com/tzapu/WiFiManager
- https://github.com/jrowberg/i2cdevlib/tree/master/Arduino/MPU6050
