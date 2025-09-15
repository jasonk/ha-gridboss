from __future__ import annotations

import logging
from datetime import timedelta
from typing import TYPE_CHECKING

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.config_entries import ConfigEntry

from .api import EG4Client
from .const import (
    CONF_USERNAME,
    CONF_PASSWORD,
    CONF_PLANT_ID,
    CONF_POLLING_INTERVAL,
    DEFAULT_POLLING_INTERVAL,
)
from .errors import GridBossAuthError, GridBossError
if TYPE_CHECKING:
    from .models import GridBoss

_LOGGER = logging.getLogger(__name__)

type GridBossConfigEntry = ConfigEntry[GridBossDataCoordinator]

class GridBossDataCoordinator(DataUpdateCoordinator):

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        self._hass = hass
        self._config_entry = config_entry

        conf = config_entry.data

        interval = conf.get(CONF_POLLING_INTERVAL, DEFAULT_POLLING_INTERVAL)
        super().__init__(
            hass,
            _LOGGER,
            name=config_entry.title,
            config_entry=config_entry,
            update_interval=timedelta(seconds=interval),
            always_update=False,
        )

        self.client = EG4Client(
            username = conf[CONF_USERNAME],
            password = conf[CONF_PASSWORD],
        )
        self.plant_id = conf[CONF_PLANT_ID]
        assert isinstance(self.plant_id, int)
        self.gridboss: GridBoss

    async def _async_setup(self):
        login = await self.client.login()
        assert isinstance(login, dict)
        self.gridboss = await self.client.get_gridboss(self.plant_id)

    async def _async_update_data(self):
        try:
            return await self.gridboss.get_update_data(self.client)
        except GridBossAuthError as err:
            # Raising ConfigEntryAuthFailed will cancel future updates
            # and start a config flow with SOURCE_REAUTH
            # (async_step_reauth).
            raise ConfigEntryAuthFailed from err
        except GridBossError as err:
            raise UpdateFailed from err
