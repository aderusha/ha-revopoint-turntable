"""BLE protocol helpers for Revopoint turntables."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
import logging
from time import monotonic
import re

from bleak import BleakError
from bleak.backends.device import BLEDevice
from bleak_retry_connector import (
    BleakClientWithServiceCache,
    close_stale_connections,
    establish_connection,
)

from .const import CHARACTERISTIC_UUID, MODEL_DUAL_AXIS, MODEL_LARGE, MODELS

_LOGGER = logging.getLogger(__name__)

_DATA_RE = re.compile(r"^\+DATA=(?P<values>[-+0-9.,]+);?$")
_TILT_ZERO_EPSILON = 0.5
_POST_STOP_QUERY_SUPPRESSION_SECONDS = 8.0
_DUAL_AXIS_RATE_DEGREES_PER_SECOND: tuple[tuple[int, float], ...] = (
    (18, 20.71),
    (24, 15.93),
    (36, 10.46),
    (54, 6.67),
    (72, 5.05),
    (90, 4.05),
)
_TURNANGLE_RE = re.compile(r"\+OK,TURNANGLE=(?P<angle>[-+]?[0-9]+(?:\.[0-9]+)?)")
_TURNCONTINUE_RE = re.compile(r"\+OK,TURNCONTINUE=(?P<direction>-?1)")
_TURNSTOP_RE = re.compile(r"\+OK,TURNSTOP")
_TILTVALUE_RE = re.compile(
    r"^\+OK,TILTVALUE=(?P<angle>[-+]?[0-9]+(?:\.[0-9]+)?);?$"
)
_FAIL_RE = re.compile(r"^\+FAIL,ERR=(?P<code>[0-9]+);?$")


class RevopointTurntableError(Exception):
    """Base exception for Revopoint turntable errors."""


class RevopointTurntableConnectionError(RevopointTurntableError):
    """Raised when the turntable cannot be reached."""


class RevopointTurntableCommandError(RevopointTurntableError):
    """Raised when a command fails."""


@dataclass(slots=True)
class RevopointState:
    """Runtime state parsed from device notifications."""

    connected: bool = False
    moving: bool = False
    speed: int | None = None
    tilt: float | None = None
    last_angle: int | None = None
    last_angle_source: str | None = None
    last_response: str | None = None
    last_error: str | None = None


class RevopointTurntableClient:
    """Small async client for the Revopoint BLE ASCII protocol."""

    def __init__(
        self,
        address: str,
        name: str,
        model: str,
        ble_device_callback: Callable[[], BLEDevice | None],
        update_callback: Callable[[], None],
    ) -> None:
        """Initialize the client."""
        self.address = address
        self.name = name
        self.model = model
        self.state = RevopointState(speed=MODELS[model].default_speed)
        self._ble_device_callback = ble_device_callback
        self._update_callback = update_callback
        self._client: BleakClientWithServiceCache | None = None
        self._lock = asyncio.Lock()
        self._pending_data_context: str | None = None
        self._suppress_query_until = 0.0
        self._rotation_started_at: float | None = None
        self._rotation_direction: int | None = None
        self._rotation_base_angle: int | None = None
        self._rotation_target_angle: int | None = None

    async def async_connect(self) -> None:
        """Connect and subscribe to notifications."""
        if self._client and self._client.is_connected:
            return

        ble_device = self._ble_device_callback()
        if ble_device is None:
            raise RevopointTurntableConnectionError(
                f"No Bluetooth advertisement found for {self.address}"
            )

        _LOGGER.debug(
            "Connecting to Revopoint turntable %s via BLE device %s details=%s",
            self.address,
            ble_device,
            getattr(ble_device, "details", None),
        )

        await close_stale_connections(ble_device)
        try:
            self._client = await establish_connection(
                BleakClientWithServiceCache,
                ble_device,
                self.name,
                ble_device_callback=self._ble_device_callback,
                disconnected_callback=self._disconnected,
            )
            await self._client.start_notify(CHARACTERISTIC_UUID, self._notification)
        except (BleakError, TimeoutError) as err:
            self.state.connected = False
            self.state.last_error = str(err)
            self._update_callback()
            raise RevopointTurntableConnectionError(str(err)) from err

        self.state.connected = True
        self.state.last_error = None
        self._update_callback()

    async def async_disconnect(self) -> None:
        """Disconnect from the turntable."""
        client = self._client
        self._client = None
        if client and client.is_connected:
            try:
                await client.stop_notify(CHARACTERISTIC_UUID)
            except BleakError:
                _LOGGER.debug("Failed to stop notifications from %s", self.address)
            await client.disconnect()
        self._mark_disconnected()
        self._update_callback()

    async def async_query(self) -> None:
        """Query the device for its current state when supported."""
        if self.model == MODEL_DUAL_AXIS:
            self._pending_data_context = None
            await self._write("+QR,TILTVALUE;", data_context="tilt")

    async def async_set_speed(self, speed: int) -> None:
        """Set the turntable speed."""
        if self.model == MODEL_LARGE:
            await self._write(f"CT+SETSPEED({speed});")
        else:
            device_speed = self._ha_speed_to_device_speed(speed)
            await self._write(f"+CT,TURNSPEED={device_speed};")
        self.state.speed = speed
        self._update_callback()

    async def async_rotate_clockwise(self) -> None:
        """Start clockwise continuous rotation."""
        self._pending_data_context = None
        if self.model == MODEL_LARGE:
            started_at = monotonic()
            await self._write_large_start(0)
        else:
            started_at = monotonic()
            await self._write("+CT,TURNCONTINUE=1;")
        self._mark_rotation_started(1, started_at)

    async def async_rotate_counterclockwise(self) -> None:
        """Start counterclockwise continuous rotation."""
        self._pending_data_context = None
        if self.model == MODEL_LARGE:
            started_at = monotonic()
            await self._write_large_start(1)
        else:
            started_at = monotonic()
            await self._write("+CT,TURNCONTINUE=-1;")
        self._mark_rotation_started(-1, started_at)

    async def async_stop(self) -> None:
        """Stop rotation."""
        self._pending_data_context = None
        if self.model == MODEL_LARGE:
            await self._write("CT+SETSTOP();")
            self._clear_rotation_estimate()
        else:
            self._suppress_query_until = (
                monotonic() + _POST_STOP_QUERY_SUPPRESSION_SECONDS
            )
            stop_at = monotonic()
            await self._write("+CT,STOP;", wait=False)
            self._estimate_stop_angle(stop_at)
            self._clear_rotation_estimate(keep_direction=True)
        self.state.moving = False
        self._update_callback()

    async def async_rotation_to_zero(self) -> None:
        """Run the dual-axis rotation return-to-zero command."""
        if self.model != MODEL_DUAL_AXIS:
            raise RevopointTurntableCommandError("Return to zero is unsupported")
        started_at = monotonic()
        await self._write("+CT,TOZERO;")
        self._mark_rotation_to_zero_started(started_at)

    async def async_tilt_to_zero(self) -> None:
        """Run the dual-axis tilt return-to-zero command."""
        if self.model != MODEL_DUAL_AXIS:
            raise RevopointTurntableCommandError("Tilt return to zero is unsupported")
        await self._write("+CR,TOZERO;")
        self.state.tilt = 0
        self._update_callback()

    async def async_set_tilt(self, angle: float) -> None:
        """Set the dual-axis tilt angle."""
        if self.model != MODEL_DUAL_AXIS:
            raise RevopointTurntableCommandError("Tilt is unsupported")
        await self._write(f"+CR,TILTVALUE={angle:g};")
        self.state.tilt = self._normalize_tilt(angle)
        self._update_callback()

    async def _write_large_start(self, direction: int) -> None:
        """Send the Large Turntable continuous-rotation command."""
        await self._write(f"CT+START({direction},0", wait=False)
        await asyncio.sleep(0.1)
        await self._write(",0,0,0,0);", wait=False)

    def _ha_speed_to_device_speed(self, speed: int) -> int:
        """Convert HA's faster-is-higher speed to device seconds/revolution."""
        if self.model != MODEL_DUAL_AXIS:
            return speed
        return 108 - speed

    @staticmethod
    def _normalize_tilt(angle: float) -> float:
        """Snap tiny near-zero tilt noise to the physical zero position."""
        return 0.0 if abs(angle) < _TILT_ZERO_EPSILON else angle

    @staticmethod
    def _normalize_rotation_angle(angle: float) -> int:
        """Round and wrap rotation angles to one signed revolution."""
        rounded_angle = round(angle)
        if rounded_angle == 0:
            return 0

        magnitude = abs(rounded_angle) % 360
        if magnitude == 0:
            return 0

        return magnitude if rounded_angle > 0 else -magnitude

    def _mark_rotation_started(self, direction: int, started_at: float) -> None:
        """Mark a rotation run as active."""
        base_angle = self._rotation_baseline_angle()
        self._suppress_query_until = 0.0
        self.state.moving = True
        self.state.last_angle_source = "estimated"
        self._rotation_started_at = started_at
        self._rotation_direction = direction
        self._rotation_base_angle = base_angle or 0
        self._rotation_target_angle = None
        self._update_callback()

    def _mark_rotation_to_zero_started(self, started_at: float) -> None:
        """Mark a return-to-zero run as active."""
        self._suppress_query_until = 0.0
        base_angle = self._rotation_baseline_angle()
        if base_angle is None:
            self.state.last_angle_source = "estimated"
            self._update_callback()
            return

        if base_angle == 0:
            self.state.last_angle = 0
            self.state.last_angle_source = "estimated"
            self._update_callback()
            return

        self.state.moving = True
        self.state.last_angle_source = "estimated"
        self._rotation_started_at = started_at
        self._rotation_direction = -1 if base_angle > 0 else 1
        self._rotation_base_angle = base_angle
        self._rotation_target_angle = 0
        self._update_callback()

    def _rotation_baseline_angle(self) -> int | None:
        """Return the best current angle to anchor a new command."""
        if self.state.moving:
            estimated_angle = self._estimated_rotation_angle()
            if estimated_angle is not None:
                return estimated_angle
        return self.state.last_angle

    @property
    def rotation_angle(self) -> int | None:
        """Return the current displayed rotation angle."""
        if self.state.moving:
            return self._estimated_rotation_angle()
        return self.state.last_angle

    def _calibrated_degrees_per_second(self, device_speed: int) -> float:
        """Return empirically calibrated dual-axis turntable speed."""
        if self.model != MODEL_DUAL_AXIS:
            return 360 / device_speed

        points = _DUAL_AXIS_RATE_DEGREES_PER_SECOND
        if device_speed <= points[0][0]:
            return points[0][1]
        if device_speed >= points[-1][0]:
            return points[-1][1]
        for (low_speed, low_rate), (high_speed, high_rate) in zip(points, points[1:]):
            if low_speed <= device_speed <= high_speed:
                fraction = (device_speed - low_speed) / (high_speed - low_speed)
                return low_rate + fraction * (high_rate - low_rate)
        return 360 / device_speed

    def _estimated_rotation_angle(self, at_time: float | None = None) -> int | None:
        """Estimate the angle for the active rotation run."""
        if (
            self.model != MODEL_DUAL_AXIS
            or self.state.speed is None
            or self._rotation_started_at is None
            or self._rotation_direction is None
        ):
            return

        device_speed = self._ha_speed_to_device_speed(self.state.speed)
        if device_speed <= 0:
            return None

        elapsed = (at_time or monotonic()) - self._rotation_started_at
        if elapsed < 0:
            return None

        travel = self._calibrated_degrees_per_second(device_speed) * elapsed
        base_angle = (
            self._rotation_base_angle
            if self._rotation_base_angle is not None
            else self.state.last_angle or 0
        )

        if self._rotation_target_angle is not None:
            delta = self._rotation_target_angle - base_angle
            if delta == 0:
                return self._rotation_target_angle
            step = min(abs(delta), travel)
            direction = 1 if delta > 0 else -1
            return self._normalize_rotation_angle(base_angle + (direction * step))

        signed_travel = travel if self._rotation_direction == 1 else -travel
        return self._normalize_rotation_angle(base_angle + signed_travel)

    def _estimate_stop_angle(self, stopped_at: float | None = None) -> None:
        """Estimate the current angle when the final notification is missing."""
        angle = self._estimated_rotation_angle(stopped_at)
        if angle is None:
            return
        self.state.last_angle = angle
        self.state.last_angle_source = "estimated"

    def update_motion_estimate(self) -> None:
        """Persist target estimates when a commanded move should be complete."""
        if not self.state.moving or self._rotation_target_angle is None:
            return

        angle = self._estimated_rotation_angle()
        if angle != self._rotation_target_angle:
            return

        self.state.last_angle = angle
        self.state.last_angle_source = "estimated"
        self.state.moving = False
        self._clear_rotation_estimate()

    def _normalize_turn_angle_notification(self, raw_angle: float) -> int:
        """Normalize Revopoint turn-angle notification quirks."""
        direction = self._rotation_direction
        if direction == 1:
            travel = raw_angle % 360
            if travel > 359.5:
                travel = 0
            return self._normalize_rotation_angle(travel)
        if direction == -1:
            return self._normalize_rotation_angle(-(abs(raw_angle) % 360))
        return self._normalize_rotation_angle(raw_angle)

    def _clear_rotation_estimate(self, *, keep_direction: bool = False) -> None:
        """Clear the active rotation estimate context."""
        direction = self._rotation_direction
        self._rotation_started_at = None
        self._rotation_direction = None
        self._rotation_base_angle = None
        self._rotation_target_angle = None
        if keep_direction:
            self._rotation_direction = direction

    @property
    def query_suppressed(self) -> bool:
        """Return whether polling should pause for stop-angle notifications."""
        return monotonic() < self._suppress_query_until

    async def _write(
        self,
        command: str,
        wait: bool = True,
        data_context: str | None = None,
    ) -> None:
        """Write a command to the control characteristic."""
        async with self._lock:
            await self.async_connect()
            assert self._client is not None
            if data_context is not None:
                self._pending_data_context = data_context
            try:
                _LOGGER.debug("Revopoint command to %s: %s", self.address, command)
                await self._client.write_gatt_char(
                    CHARACTERISTIC_UUID,
                    command.encode("utf-8"),
                    response=False,
                )
            except (BleakError, TimeoutError) as err:
                self._mark_disconnected()
                self.state.last_error = str(err)
                self._update_callback()
                raise RevopointTurntableConnectionError(str(err)) from err
            if wait:
                await asyncio.sleep(0.15)

    def _notification(self, _sender: int, data: bytearray) -> None:
        """Handle a BLE notification."""
        text = data.decode("utf-8", errors="replace").strip()
        self.state.last_response = text
        self.state.last_error = None
        _LOGGER.debug("Revopoint notification from %s: %r", self.address, text)

        if match := _FAIL_RE.match(text):
            self.state.last_error = match.group("code")
        elif match := _TURNANGLE_RE.search(text):
            angle = self._normalize_turn_angle_notification(
                float(match.group("angle"))
            )
            self.state.last_angle = angle
            self.state.last_angle_source = "device"
            self.state.moving = False
            self._clear_rotation_estimate()
            _LOGGER.debug(
                "Revopoint turn angle from %s parsed as %s degrees",
                self.address,
                angle,
            )
        elif match := _TURNCONTINUE_RE.search(text):
            base_angle = self._rotation_baseline_angle()
            self._rotation_direction = int(match.group("direction"))
            self._rotation_started_at = monotonic()
            self._rotation_base_angle = base_angle or 0
            self._rotation_target_angle = None
            self.state.last_angle_source = "estimated"
            self.state.moving = True
        elif _TURNSTOP_RE.search(text):
            self._suppress_query_until = (
                monotonic() + _POST_STOP_QUERY_SUPPRESSION_SECONDS
            )
            self._estimate_stop_angle()
            self._clear_rotation_estimate(keep_direction=True)
            self.state.moving = False
        elif match := _TILTVALUE_RE.match(text):
            self.state.tilt = self._normalize_tilt(float(match.group("angle")))
        elif match := _DATA_RE.match(text):
            values = tuple(float(value) for value in match.group("values").split(","))
            context = self._pending_data_context
            self._pending_data_context = None
            if context == "tilt" and values:
                self.state.tilt = self._normalize_tilt(values[0])

        self._update_callback()

    def _disconnected(self, _client: BleakClientWithServiceCache) -> None:
        """Handle BLE disconnection."""
        self._mark_disconnected()
        self._update_callback()

    def _mark_disconnected(self) -> None:
        """Mark connection loss and stop estimates that can no longer be verified."""
        if self.state.moving:
            self._estimate_stop_angle()
            self._clear_rotation_estimate()
            self.state.moving = False
        self.state.connected = False
