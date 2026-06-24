"""Sensor platform for Revopoint Turntable."""

from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Callable

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import MODEL_DUAL_AXIS
from .coordinator import RevopointTurntableCoordinator
from .entity import RevopointTurntableEntity


@dataclass(frozen=True, kw_only=True)
class RevopointSensorDescription(SensorEntityDescription):
    """Description of a Revopoint sensor."""

    value_fn: Callable[[RevopointTurntableCoordinator], str | float | None]
    model_filter: set[str] | None = None


SENSORS: tuple[RevopointSensorDescription, ...] = (
    RevopointSensorDescription(
        key="motion_state",
        translation_key="motion_state",
        icon="mdi:rotate-3d-variant",
        value_fn=lambda coordinator: "moving"
        if coordinator.client.state.moving
        else "stopped",
    ),
    RevopointSensorDescription(
        key="rotation_angle",
        translation_key="rotation_angle",
        icon="mdi:angle-acute",
        native_unit_of_measurement="°",
        value_fn=lambda coordinator: coordinator.client.rotation_angle,
    ),
    RevopointSensorDescription(
        key="tilt_angle",
        translation_key="tilt_angle",
        icon="mdi:angle-acute",
        native_unit_of_measurement="°",
        value_fn=lambda coordinator: coordinator.client.state.tilt,
        model_filter={MODEL_DUAL_AXIS},
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensor entities."""
    coordinator: RevopointTurntableCoordinator = entry.runtime_data
    async_add_entities(
        RevopointSensor(coordinator, description)
        for description in SENSORS
        if description.model_filter is None
        or coordinator.model in description.model_filter
    )


class RevopointSensor(RevopointTurntableEntity, SensorEntity):
    """A Revopoint sensor entity."""

    entity_description: RevopointSensorDescription

    def __init__(
        self,
        coordinator: RevopointTurntableCoordinator,
        description: RevopointSensorDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.address}_{description.key}"

    @property
    def native_value(self) -> str | float | None:
        """Return current value."""
        return self.entity_description.value_fn(self.coordinator)
