import logging
from dataclasses import dataclass
from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorDeviceClass,
    BinarySensorEntityDescription,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import GridBossConfigEntry
from .entities import GridBossEntity, GridBossEntityDescription
from .utils import ignore

_LOGGER = logging.getLogger(__name__)

@dataclass(frozen=True, kw_only=True)
class GridBossBinarySensorEntityDescription(
    BinarySensorEntityDescription, GridBossEntityDescription,
):
    pass

SENSORS: list[GridBossBinarySensorEntityDescription] = [
    GridBossBinarySensorEntityDescription(
        name="Lost",
        key="lost",
        icon="mdi:alert",
        device_class=BinarySensorDeviceClass.PROBLEM,
        data_source=("midbox_runtime", "runtime", "battery_info"),
    ),
    GridBossBinarySensorEntityDescription(
        name="Battery Shared",
        key="batShared",
        data_source="runtime",
    ),
    GridBossBinarySensorEntityDescription(
        name="Allow Generator Exercise",
        key="allowGenExercise",
        data_source="device_data",
    ),
    GridBossBinarySensorEntityDescription(
        name="Generator Dry Contact",
        key="genDryContact",
        data_source="device_data",
        transform=lambda x: x == 'ON',
    ),
    GridBossBinarySensorEntityDescription(
        name="Notice Active",
        key="noticeInfo",
        icon="mdi:alert",
        device_class=BinarySensorDeviceClass.PROBLEM,
        data_source="battery",
    ),
]

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: GridBossConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    ignore(hass)
    coordinator = config_entry.runtime_data
    gridboss = coordinator.gridboss

    for item in gridboss.items():
        descs = item.filter_entity_descriptions(SENSORS)
        if descs:
            _LOGGER.debug("Adding %d sensors for %s", len(descs), item.name)
            async_add_entities([
                GridBossBinarySensor(coordinator, desc, item)
                for desc in descs
            ])

class GridBossBinarySensor( # pyright: ignore
    GridBossEntity[GridBossBinarySensorEntityDescription],
    BinarySensorEntity,
):
    def get_data(self):
        value = super().get_data()
        return bool(value)

    @callback
    def _handle_coordinator_update(self) -> None:
        self._attr_is_on = bool(self.get_data())
        self.async_write_ha_state()
