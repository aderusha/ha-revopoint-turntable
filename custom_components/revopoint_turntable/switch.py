"""Switch platform for Revopoint Turntable."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import RevopointTurntableCoordinator
from .entity import RevopointTurntableEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up switch entities."""
    coordinator: RevopointTurntableCoordinator = entry.runtime_data
    async_add_entities([RevopointConnectionSwitch(coordinator)])


class RevopointConnectionSwitch(RevopointTurntableEntity, SwitchEntity):
    """Hold or release the turntable BLE connection."""

    _attr_device_class = SwitchDeviceClass.SWITCH
    _attr_entity_category = EntityCategory.CONFIG
    _attr_translation_key = "ble_connection"

    def __init__(self, coordinator: RevopointTurntableCoordinator) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.address}_ble_connection"

    @property
    def available(self) -> bool:
        """Keep the connection switch usable while the radio is released."""
        return True

    @property
    def icon(self) -> str:
        """Return an icon that reflects whether HA holds the BLE connection."""
        return (
            "mdi:bluetooth-connect"
            if self.coordinator.connection_enabled
            else "mdi:bluetooth-off"
        )

    @property
    def is_on(self) -> bool:
        """Return whether Home Assistant should hold the BLE connection."""
        return self.coordinator.connection_enabled

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Reconnect and resume polling."""
        await self.coordinator.async_set_connection(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disconnect so a phone app or another BLE client can connect."""
        await self.coordinator.async_set_connection(False)
