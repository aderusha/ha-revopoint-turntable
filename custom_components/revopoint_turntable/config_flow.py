"""Config flow for Revopoint Turntable."""

from __future__ import annotations

from typing import Any

from homeassistant.components.bluetooth import BluetoothServiceInfoBleak
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_ADDRESS, CONF_NAME
import homeassistant.helpers.config_validation as cv
import voluptuous as vol

from .const import (
    CONF_MODEL,
    DEFAULT_NAME,
    DOMAIN,
    KNOWN_LOCAL_NAMES,
    MODEL_BY_LOCAL_NAME,
    MODEL_DUAL_AXIS,
    MODEL_LARGE,
    MODELS,
)


class RevopointTurntableConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Revopoint Turntable."""

    VERSION = 1

    _discovered: BluetoothServiceInfoBleak | None = None

    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfoBleak
    ) -> ConfigFlowResult:
        """Handle Bluetooth discovery."""
        name = (
            discovery_info.name
            or getattr(discovery_info, "local_name", None)
            or DEFAULT_NAME
        )
        if name not in KNOWN_LOCAL_NAMES:
            return self.async_abort(reason="not_supported")

        await self.async_set_unique_id(discovery_info.address.lower())
        self._abort_if_unique_id_configured()

        self._discovered = discovery_info
        self.context["title_placeholders"] = {"name": name}
        return await self.async_step_bluetooth_confirm()

    async def async_step_bluetooth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm Bluetooth discovery."""
        if self._discovered is None:
            return self.async_abort(reason="no_discovery_info")

        name = (
            self._discovered.name
            or getattr(self._discovered, "local_name", None)
            or DEFAULT_NAME
        )
        model = MODEL_BY_LOCAL_NAME.get(name, MODEL_DUAL_AXIS)

        if user_input is not None:
            return self.async_create_entry(
                title=name,
                data={
                    CONF_ADDRESS: self._discovered.address,
                    CONF_NAME: name,
                    CONF_MODEL: model,
                },
            )

        self._set_confirm_only()
        return self.async_show_form(
            step_id="bluetooth_confirm",
            description_placeholders={
                "name": name,
                "model": MODELS[model].name,
            },
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle manual setup."""
        if user_input is not None:
            address = user_input[CONF_ADDRESS].upper()
            await self.async_set_unique_id(address.lower())
            self._abort_if_unique_id_configured()

            model = user_input[CONF_MODEL]
            name = user_input.get(CONF_NAME) or MODELS[model].name
            return self.async_create_entry(
                title=name,
                data={
                    CONF_ADDRESS: address,
                    CONF_NAME: name,
                    CONF_MODEL: model,
                },
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_ADDRESS): cv.string,
                    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
                    vol.Required(CONF_MODEL, default=MODEL_DUAL_AXIS): vol.In(
                        {
                            MODEL_DUAL_AXIS: MODELS[MODEL_DUAL_AXIS].name,
                            MODEL_LARGE: MODELS[MODEL_LARGE].name,
                        }
                    ),
                }
            ),
        )
