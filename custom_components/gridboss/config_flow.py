import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult

from .api import EG4Client
from .errors import GridBossAuthError
from .const import (
    DOMAIN,
    CONF_USERNAME,
    CONF_PASSWORD,
    CONF_PLANT_ID,
    CONF_SERIAL,
    CONF_POLLING_INTERVAL,
    DEFAULT_POLLING_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema({
    vol.Required(CONF_USERNAME): str,
    vol.Required(CONF_PASSWORD): str,
    vol.Optional(CONF_SERIAL): int,
    vol.Optional(CONF_PLANT_ID): int,
    vol.Optional(CONF_POLLING_INTERVAL, default=DEFAULT_POLLING_INTERVAL): int,
})


class GridBossConfigFlow(ConfigFlow, domain=DOMAIN):

    VERSION = 1
    MINOR_VERSION = 0

    async def _validate_input(
        self,
        user_input: dict[str, Any],
    ) -> int | None:
        client = EG4Client(
            username=user_input[CONF_USERNAME],
            password=user_input[CONF_PASSWORD],
        )
        await client.login()
        plant = client.find_plant(
            plant_id=user_input.get(CONF_PLANT_ID),
            serial=user_input.get(CONF_SERIAL),
        )
        if plant:
            return plant.get("plantId")
        return None

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input:
            try:
                plant = await self._validate_input(user_input)
                if plant:
                    await self.async_set_unique_id(str(plant))
                    self._abort_if_unique_id_configured()
                    user_input[CONF_PLANT_ID] = plant
                    return self.async_create_entry(
                        title=f"Solar Plant {plant}",
                        data=user_input,
                    )
            except GridBossAuthError:
                errors["base"] = "invalid_auth"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=CONFIG_SCHEMA,
            errors=errors,
        )

    async def async_step_reconfigure(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        if user_input is not None:
            plant = await self._validate_input(user_input)
            if plant:
                await self.async_set_unique_id(str(plant))
                self._abort_if_unique_id_mismatch()
                return self.async_update_reload_and_abort(
                    self._get_reconfigure_entry(),
                    data_updates=user_input,
                )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=CONFIG_SCHEMA,
        )
