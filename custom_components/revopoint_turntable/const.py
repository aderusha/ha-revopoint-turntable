"""Constants for the Revopoint Turntable integration."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.const import Platform

DOMAIN = "revopoint_turntable"

PLATFORMS = [Platform.BUTTON, Platform.NUMBER, Platform.SENSOR, Platform.SWITCH]

CONF_MODEL = "model"

MODEL_DUAL_AXIS = "dual_axis"
MODEL_LARGE = "large"

CHARACTERISTIC_UUID = "0000ffe1-0000-1000-8000-00805f9b34fb"

DUAL_AXIS_LOCAL_NAMES = {"REVO_DUAL_AXIS_TABLE"}
LARGE_LOCAL_NAMES = {"REVO_TA500", "P_REVO_TA500"}
KNOWN_LOCAL_NAMES = DUAL_AXIS_LOCAL_NAMES | LARGE_LOCAL_NAMES

DEFAULT_NAME = "Revopoint Turntable"


@dataclass(frozen=True, slots=True)
class ModelDescription:
    """Description of a supported Revopoint turntable model."""

    name: str
    speed_min: int
    speed_max: int
    speed_step: int
    speed_native_unit: str | None
    default_speed: int


MODELS: dict[str, ModelDescription] = {
    MODEL_DUAL_AXIS: ModelDescription(
        name="Dual Axis Turntable",
        speed_min=18,
        speed_max=90,
        speed_step=1,
        speed_native_unit=None,
        default_speed=30,
    ),
    MODEL_LARGE: ModelDescription(
        name="Large Turntable",
        speed_min=0,
        speed_max=127,
        speed_step=1,
        speed_native_unit="grade",
        default_speed=30,
    ),
}

MODEL_BY_LOCAL_NAME = {
    **dict.fromkeys(DUAL_AXIS_LOCAL_NAMES, MODEL_DUAL_AXIS),
    **dict.fromkeys(LARGE_LOCAL_NAMES, MODEL_LARGE),
}

TILT_MIN = -30
TILT_MAX = 30
TILT_STEP = 1

ATTR_LAST_RESPONSE = "last_response"
ATTR_LAST_ERROR = "last_error"
ATTR_ROTATION_ANGLE_SOURCE = "rotation_angle_source"
