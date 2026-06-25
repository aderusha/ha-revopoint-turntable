# Revopoint Turntable

Custom Home Assistant integration for Revopoint Bluetooth LE turntables.

Supported models:

- Revopoint Dual Axis Turntable (`REVO_DUAL_AXIS_TABLE`), tested with real hardware.
- Revopoint Large Turntable / TA500 (`REVO_TA500`, `P_REVO_TA500`), experimental and not maintainer-tested.

## Entities

All supported models:

- Buttons: rotate clockwise, rotate counterclockwise, stop.
- Number: speed.
- Sensors: motion state, rotation angle.
- Switch: BLE connection.

Dual Axis Turntable only:

- Buttons: return to zero (rotation), return to zero (tilt).
- Number: tilt.
- Sensor: rotation angle (tilt).

## BLE Connection

Revopoint turntables allow one active BLE controller connection at a time. Turn the BLE connection switch off when you want Home Assistant to release the turntable for another controller.

Rotation angle values are reported as positive modulo-360 degrees; `360` wraps to `0`.

## Installation

Install with HACS as a custom integration repository, or copy this folder to:

```text
/config/custom_components/revopoint_turntable
```

Restart Home Assistant, then add the integration from `Settings` -> `Devices & services`.

## Notes

- Large Turntable / TA500 support needs user testing.
- This integration uses local Bluetooth LE control and does not require cloud services.
- This project is not affiliated with or endorsed by Revopoint.
