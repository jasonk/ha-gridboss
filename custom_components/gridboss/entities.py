from __future__ import annotations

from abc import ABC
from typing import Any, Literal, TYPE_CHECKING
from collections.abc import Callable

from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity import EntityDescription


if TYPE_CHECKING:
    from .models import GridBoss, Inverter, Battery
    from .coordinator import GridBossDataCoordinator

DataSource = Literal[
    "energy_info_parallel",
    "parallel_group_details",
    "midbox_runtime",
    "midbox_data",
    "device_data",
    "battery_info",
    "energy_info",
    "runtime",
    "battery",
]

class GridBossEntityDescription(EntityDescription):
    data_source: DataSource | tuple[DataSource, ...]
    transform: Callable[[Any], Any] | None = None
    description: str | None = None


class GridBossEntity[D: GridBossEntityDescription](
    #CoordinatorEntity[GridBossDataCoordinator],
    CoordinatorEntity,
    ABC,
):

    def __init__(
        self,
        coordinator: GridBossDataCoordinator,
        description: D,
        source: GridBoss|Inverter|Battery,
    ):
        super().__init__(coordinator)

        self.entity_description = description # type: ignore[assignment]
        self._desc = description
        self.source = source
        self.has_entity_name = True

        if isinstance(description.name, str):
            self._attr_name = description.name
        self._attr_unique_id = f"{source.unique_id()}_{description.key}"

        if description.icon:
            self._attr_icon = description.icon
        if description.description:
            self._attr_description = description.description

        if description.device_class:
            self._attr_device_class = description.device_class

        self._attr_device_info = source.device_info

    def find_data_source(self):
        data = self.coordinator.data.get(self.source.unique_id(), {})
        src = self._desc.data_source
        if isinstance(src, str):
            return data.get(src, {})
        if isinstance(src, tuple):
            for s in src:
                subdata = data.get(s, {})
                if subdata:
                    return subdata
        return {}

    def get_data(self):
        data = self.find_data_source()
        value = data.get(self._desc.key)
        if self._desc.transform:
            return self._desc.transform(value)
        return value

#   async def async_turn_on(self, **kwargs):
#       """Turn the light on.
#       Example method how to request data updates.
#       """
#       # Do the turning on.
#       # ...

#       # Update the data
#       await self.coordinator.async_request_refresh()
