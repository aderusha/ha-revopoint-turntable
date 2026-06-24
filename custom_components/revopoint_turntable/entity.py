"""Shared entity base for Revopoint Turntable."""

from __future__ import annotations

from typing import Any

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTR_LAST_ERROR,
    ATTR_LAST_RESPONSE,
    ATTR_ROTATION_ANGLE_SOURCE,
    DOMAIN,
)
from .coordinator import RevopointTurntableCoordinator


class RevopointTurntableEntity(CoordinatorEntity[RevopointTurntableCoordinator]):
    """Base entity for Revopoint turntables."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: RevopointTurntableCoordinator) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.address.lower())},
            manufacturer="Revopoint",
            model=coordinator.model_description.name,
            name=coordinator.device_name,
        )

    @property
    def available(self) -> bool:
        """Return whether the turntable is reachable."""
        state = self.coordinator.data
        return self.coordinator.connection_enabled and (
            (state is not None and state.connected)
            or self.coordinator.ble_device_available
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return common diagnostics attributes."""
        state = self.coordinator.data
        if state is None:
            return {
                ATTR_LAST_RESPONSE: None,
                ATTR_LAST_ERROR: None,
                ATTR_ROTATION_ANGLE_SOURCE: None,
            }
        return {
            ATTR_LAST_RESPONSE: state.last_response,
            ATTR_LAST_ERROR: state.last_error,
            ATTR_ROTATION_ANGLE_SOURCE: state.last_angle_source,
        }
