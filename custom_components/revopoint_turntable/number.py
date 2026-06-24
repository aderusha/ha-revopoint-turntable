"""Number platform for Revopoint Turntable."""

from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Awaitable, Callable

from homeassistant.components.number import NumberEntity, NumberEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import MODEL_DUAL_AXIS, TILT_MAX, TILT_MIN, TILT_STEP
from .coordinator import RevopointTurntableCoordinator
from .entity import RevopointTurntableEntity


@dataclass(frozen=True, kw_only=True)
class RevopointNumberDescription(NumberEntityDescription):
    """Description of a Revopoint number."""

    value_fn: Callable[[RevopointTurntableCoordinator], float | None]
    set_fn: Callable[[RevopointTurntableCoordinator, float], Awaitable[None]]
    model_filter: set[str] | None = None


def _speed_description(
    coordinator: RevopointTurntableCoordinator,
) -> RevopointNumberDescription:
    model = coordinator.model_description
    return RevopointNumberDescription(
        key="speed",
        translation_key="speed",
        icon="mdi:speedometer",
        native_min_value=model.speed_min,
        native_max_value=model.speed_max,
        native_step=model.speed_step,
        native_unit_of_measurement=model.speed_native_unit,
        value_fn=lambda item: item.client.state.speed,
        set_fn=lambda item, value: item.client.async_set_speed(int(value)),
    )


TILT_DESCRIPTION = RevopointNumberDescription(
    key="tilt",
    translation_key="tilt",
    icon="mdi:angle-acute",
    native_min_value=TILT_MIN,
    native_max_value=TILT_MAX,
    native_step=TILT_STEP,
    native_unit_of_measurement="deg",
    value_fn=lambda coordinator: coordinator.client.state.tilt,
    set_fn=lambda coordinator, value: coordinator.client.async_set_tilt(value),
    model_filter={MODEL_DUAL_AXIS},
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up number entities."""
    coordinator: RevopointTurntableCoordinator = entry.runtime_data
    descriptions = [_speed_description(coordinator), TILT_DESCRIPTION]
    async_add_entities(
        RevopointNumber(coordinator, description)
        for description in descriptions
        if description.model_filter is None
        or coordinator.model in description.model_filter
    )


class RevopointNumber(RevopointTurntableEntity, NumberEntity):
    """A Revopoint number entity."""

    entity_description: RevopointNumberDescription

    def __init__(
        self,
        coordinator: RevopointTurntableCoordinator,
        description: RevopointNumberDescription,
    ) -> None:
        """Initialize the number."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.address}_{description.key}"

    @property
    def native_value(self) -> float | None:
        """Return current value."""
        return self.entity_description.value_fn(self.coordinator)

    async def async_set_native_value(self, value: float) -> None:
        """Set the value."""
        await self.entity_description.set_fn(self.coordinator, value)
