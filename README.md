# Revopoint Turntable for Home Assistant

Custom Home Assistant integration for Revopoint Bluetooth LE turntables.

## Supported Devices

- Revopoint Dual Axis Turntable (`REVO_DUAL_AXIS_TABLE`): tested with real hardware.
- Revopoint Large Turntable / TA500 (`REVO_TA500`, `P_REVO_TA500`): experimental support. This model has not been tested by the maintainer.

## Features

- Bluetooth discovery and config flow.
- Full device control for rotation and tilt.
- BLE connection switch so Home Assistant can release the device for another controller.

## HACS Installation

1. Open HACS in Home Assistant.
2. Go to `Integrations`.
3. Select the three-dot menu, then `Custom repositories`.
4. Add this repository URL: `https://github.com/aderusha/ha-revopoint-turntable`
5. Choose `Integration` as the category.
6. Install `Revopoint Turntable`.
7. Restart Home Assistant.
8. Add the integration from `Settings` -> `Devices & services`.

Bluetooth discovery should offer the turntable automatically when it is powered on and advertising.

## Manual Installation

Copy this directory:

```text
custom_components/revopoint_turntable
```

to this Home Assistant path:

```text
/config/custom_components/revopoint_turntable
```

Restart Home Assistant, then add the integration from `Settings` -> `Devices & services`.

## Entities

All supported models:

- `button`: rotate clockwise
- `button`: rotate counterclockwise
- `button`: stop
- `number`: speed
- `sensor`: motion state
- `sensor`: rotation angle
- `switch`: BLE connection

Dual Axis Turntable only:

- `button`: return to zero (rotation)
- `button`: return to zero (tilt)
- `number`: tilt
- `sensor`: rotation angle (tilt)

## BLE Connection Switch

Revopoint turntables allow one active BLE controller connection at a time. Keep the BLE connection switch on when Home Assistant should control the turntable. Turn it off to release the connection for the Revopoint mobile app, Revo Scan, or another BLE controller.

## Rotation Angle

The Dual Axis Turntable reports rotation angle after stop and return-to-zero commands. While the table is moving, this integration estimates the angle from the current speed and elapsed motion time, then uses the device-reported angle as the source of truth when it arrives.

Rotation angle values are reported as positive modulo-360 degrees; `360` wraps to `0`.

## Notes

- Large Turntable / TA500 support is included for users who can test it, but it is not maintainer-verified.
- This integration uses local Bluetooth LE control. It does not require cloud services.
- This project is not affiliated with or endorsed by Revopoint.

## License

MIT
