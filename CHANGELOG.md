# Changelog

## 0.1.2

- Report rotation angles as positive modulo-360 values.
- Estimate return-to-zero motion using the shortest wrapped distance to zero.

## 0.1.1

- Wrap estimated rotation angle values to one signed revolution.
- Stop active rotation estimates when the BLE connection drops.

## 0.1.0

- Initial public release.
- Add Bluetooth discovery and setup flow.
- Add Dual Axis Turntable rotation, tilt, return-to-zero, speed, motion, and angle entities.
- Add experimental Large Turntable / TA500 rotation and speed controls.
- Add BLE connection switch.
- Add local integration branding.
