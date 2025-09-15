from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from .coordinator import GridBossConfigEntry, GridBossDataCoordinator
from .utils import ignore
from .const import CONF_USERNAME, CONF_PASSWORD, CONF_PLANT_ID, CONF_SERIAL

TO_REDACT = {
    CONF_USERNAME, CONF_PASSWORD, CONF_PLANT_ID, CONF_SERIAL,
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    config_entry: GridBossConfigEntry,
) -> dict[str, Any]:
    ignore(hass)
    coordinator: GridBossDataCoordinator = config_entry.runtime_data

    return async_redact_data({
        "config_entry": config_entry.data,
        "data": coordinator.data,
    }, TO_REDACT)
