"""Coordinator for Revopoint Turntable entities."""

from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.components import bluetooth
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ADDRESS, CONF_NAME
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import CONF_MODEL, DEFAULT_NAME, DOMAIN, MODELS
from .protocol import (
    RevopointState,
    RevopointTurntableClient,
    RevopointTurntableError,
)

_LOGGER = logging.getLogger(__name__)


class RevopointTurntableCoordinator(DataUpdateCoordinator[RevopointState]):
    """Coordinate state for one Revopoint turntable."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        self.entry = entry
        self.address: str = entry.data[CONF_ADDRESS]
        self.model = entry.data[CONF_MODEL]
        self.model_description = MODELS[self.model]
        self.device_name = entry.data.get(CONF_NAME) or DEFAULT_NAME
        self.connection_enabled = bool(entry.options.get("connection_enabled", True))
        self._estimate_update_unsub: CALLBACK_TYPE | None = None

        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"{DOMAIN}_{self.address}",
            update_interval=timedelta(seconds=15),
        )
        self.client = RevopointTurntableClient(
            address=self.address,
            name=self.device_name,
            model=self.model,
            ble_device_callback=self._ble_device,
            update_callback=self._handle_client_update,
        )

    async def async_setup(self) -> None:
        """Prime state from the device without starting motion."""
        await self.async_config_entry_first_refresh()

    async def _async_update_data(self) -> RevopointState:
        """Query latest state."""
        if not self.connection_enabled:
            if self.client.state.connected:
                await self.client.async_disconnect()
            return self.client.state

        if self.client.state.moving or self.client.query_suppressed:
            return self.client.state

        try:
            await self.client.async_query()
        except RevopointTurntableError as err:
            _LOGGER.debug("Unable to update %s: %s", self.address, err)
        return self.client.state

    async def async_set_connection(self, enabled: bool) -> None:
        """Set whether Home Assistant should hold the BLE connection."""
        self.connection_enabled = bool(enabled)
        self.hass.config_entries.async_update_entry(
            self.config_entry,
            options={
                **self.config_entry.options,
                "connection_enabled": self.connection_enabled,
            },
        )
        if self.connection_enabled:
            await self.async_request_refresh()
            return

        await self.client.async_disconnect()
        self.async_set_updated_data(self.client.state)

    async def async_disconnect(self) -> None:
        """Disconnect the BLE client."""
        self._stop_estimate_updates()
        await self.client.async_disconnect()

    @property
    def ble_device_available(self) -> bool:
        """Return whether Home Assistant has a connectable BLE advertisement."""
        return self._ble_device() is not None

    def _ble_device(self):
        """Return the latest BLE device for this address."""
        return bluetooth.async_ble_device_from_address(
            self.hass, self.address, connectable=True
        )

    def _handle_client_update(self) -> None:
        """Publish client state to entities."""
        self._update_estimate_timer()
        self.async_set_updated_data(self.client.state)

    def _update_estimate_timer(self) -> None:
        """Start or stop moving-angle estimate updates."""
        if self.client.state.moving and self._estimate_update_unsub is None:
            self._estimate_update_unsub = async_track_time_interval(
                self.hass,
                self._async_estimate_tick,
                timedelta(seconds=1),
            )
        elif not self.client.state.moving:
            self._stop_estimate_updates()

    def _stop_estimate_updates(self) -> None:
        """Cancel moving-angle estimate updates."""
        if self._estimate_update_unsub is not None:
            self._estimate_update_unsub()
            self._estimate_update_unsub = None

    @callback
    def _async_estimate_tick(self, _now) -> None:
        """Publish an updated moving-angle estimate."""
        self.client.update_motion_estimate()
        if not self.client.state.moving:
            self._stop_estimate_updates()
        self.async_set_updated_data(self.client.state)
