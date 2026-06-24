"""Button platform for Revopoint Turntable."""

from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Awaitable, Callable

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import MODEL_DUAL_AXIS
from .coordinator import RevopointTurntableCoordinator
from .entity import RevopointTurntableEntity


@dataclass(frozen=True, kw_only=True)
class RevopointButtonDescription(ButtonEntityDescription):
    """Description of a Revopoint button."""

    press_fn: Callable[[RevopointTurntableCoordinator], Awaitable[None]]
    model_filter: set[str] | None = None


BUTTONS: tuple[RevopointButtonDescription, ...] = (
    RevopointButtonDescription(
        key="rotate_clockwise",
        translation_key="rotate_clockwise",
        icon="mdi:rotate-right",
        press_fn=lambda coordinator: coordinator.client.async_rotate_clockwise(),
    ),
    RevopointButtonDescription(
        key="rotate_counterclockwise",
        translation_key="rotate_counterclockwise",
        icon="mdi:rotate-left",
        press_fn=lambda coordinator: coordinator.client.async_rotate_counterclockwise(),
    ),
    RevopointButtonDescription(
        key="stop",
        translation_key="stop",
        icon="mdi:stop",
        press_fn=lambda coordinator: coordinator.client.async_stop(),
    ),
    RevopointButtonDescription(
        key="return_to_zero_rotation",
        translation_key="return_to_zero_rotation",
        icon="mdi:home-import-outline",
        press_fn=lambda coordinator: coordinator.client.async_rotation_to_zero(),
        model_filter={MODEL_DUAL_AXIS},
    ),
    RevopointButtonDescription(
        key="return_to_zero_tilt",
        translation_key="return_to_zero_tilt",
        icon="mdi:angle-acute",
        press_fn=lambda coordinator: coordinator.client.async_tilt_to_zero(),
        model_filter={MODEL_DUAL_AXIS},
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up button entities."""
    coordinator: RevopointTurntableCoordinator = entry.runtime_data
    async_add_entities(
        RevopointButton(coordinator, description)
        for description in BUTTONS
        if description.model_filter is None
        or coordinator.model in description.model_filter
    )


class RevopointButton(RevopointTurntableEntity, ButtonEntity):
    """A Revopoint command button."""

    entity_description: RevopointButtonDescription

    def __init__(
        self,
        coordinator: RevopointTurntableCoordinator,
        description: RevopointButtonDescription,
    ) -> None:
        """Initialize the button."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.address}_{description.key}"

    async def async_press(self) -> None:
        """Handle button press."""
        await self.entity_description.press_fn(self.coordinator)
