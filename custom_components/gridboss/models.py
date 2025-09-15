from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, TypedDict
from dataclasses import dataclass, fields, field
from functools import cached_property
import yaml

from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN
from .entities import DataSource, GridBossEntityDescription

if TYPE_CHECKING:
    from .api import EG4Client
    from .coordinator import GridBossDataCoordinator

@dataclass(kw_only=True)
class Model(ABC):
    @abstractmethod
    def unique_id(self) -> str: ...

    @abstractmethod
    def get_name(self) -> str: ...

    @abstractmethod
    def data_sources(self) -> set[DataSource]: ...

    def select_data(
        self,
        coordinator: GridBossDataCoordinator,
        data_source: DataSource,
    ) -> dict[str, Any] | None:
        return coordinator.data.get(self.unique_id(), {}).get(data_source)

    @property
    def name(self) -> str:
        return self.get_name()

    def filter_entity_descriptions[T: GridBossEntityDescription](
        self,
        descriptions: list[T],
    ) -> list[T]:
        sources = self.data_sources()
        def matches(desc: GridBossEntityDescription) -> bool:
            if isinstance(desc.data_source, str):
                return desc.data_source in sources
            if isinstance(desc.data_source, tuple):
                return any(ds in sources for ds in desc.data_source)
            return False
        return [desc for desc in descriptions if matches(desc)]

class DeviceOptions(TypedDict, total=True):
    serial: str
    device_type: str

    sw_version: str
    hw_version: str

@dataclass(kw_only=True)
class Device(Model):
    serial: str # serialNum
    device_type: str # deviceTypeText

    sw_version: str # fwVersion
    hw_version: str # hardwareVersion

    def unique_id(self) -> str:
        return str(self.serial)

    def get_name(self) -> str:
        return f"{self.device_type} ({self.serial})"

    @cached_property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self.serial)},
            serial_number=self.serial,
            name=self.name,
            manufacturer="EG4",
            model=self.device_type,
            sw_version=self.sw_version,
            hw_version=self.hw_version,
        )

@dataclass(kw_only=True)
class GridBoss(Device):
    plant_id: int
    inverters: list[Inverter] = field(default_factory=list)

    def items(self):
        yield self
        for inverter in self.inverters:
            yield inverter
            yield from inverter.batteries

    def data_sources(self) -> set[DataSource]:
        return {
            "midbox_data",
            "device_data",
            "energy_info_parallel",
            "midbox_runtime",
        }

    async def get_data(self, client: EG4Client) -> dict[str, Any]:
        serial = self.serial
        energy = await client.get_inverter_energy_info_parallel(serial)
        midbox_runtime = await client.get_inverter_midbox_runtime(serial)
        return {
            "midbox_data": midbox_runtime["midboxData"],
            "device_data": midbox_runtime["deviceData"],
            "energy_info_parallel": energy,
            "midbox_runtime": midbox_runtime,
        }

    async def get_update_data(self, client: EG4Client) -> dict[str, Any]:
        data: dict[str, dict[str, Any]] = {}
        data[self.serial] = await self.get_data(client)
        for inverter in self.inverters:
            inverter_data = await inverter.get_data(client)
            for batt in inverter_data["battery_info"].get("batteryArray", []):
                data[batt["batteryKey"]] = {"battery": batt}
            data[inverter.serial] = inverter_data
        return data

@dataclass(kw_only=True)
class Inverter(Device):
    gridboss: GridBoss = field(repr=False)

    battery_type: str | None = None # batteryTypeText
    batteries: list[Battery] = field(default_factory=list)

    def unique_id(self) -> str:
        return self.serial

    def data_sources(self) -> set[DataSource]:
        return {
            "runtime",
            "battery_info",
        }

    @cached_property
    def device_info(self) -> DeviceInfo:
        info = super().device_info
        info["via_device"] = (DOMAIN, str(self.gridboss.serial))
        return info

    async def get_data(self, client: EG4Client) -> dict[str, dict[str, Any]]:
        serial = self.serial
        runtime = await client.get_inverter_runtime(serial)
        battery_info = await client.get_inverter_battery_info(serial)
        return {
            "runtime": runtime,
            "battery_info": battery_info,
        }

@dataclass(kw_only=True)
class Battery(Model):
    inverter: Inverter = field(repr=False)
    key: str # batteryKey
    serial: str # batterySerialNum
    device_type: str # batteryType
    index: int # batIndex

    sw_version: str # fwVersionText
    hw_version: str | None = None

    def unique_id(self) -> str:
        return self.key

    def get_name(self) -> str:
        return f"{self.device_type} ({self.serial})"

    def data_sources(self) -> set[DataSource]:
        return {"battery"}

    @cached_property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self.key)},
            serial_number=self.serial,
            name=self.name,
            manufacturer="EG4",
            model=self.device_type,
            sw_version=self.sw_version,
            hw_version=self.hw_version,
            via_device=(DOMAIN, self.inverter.serial),
        )

def represent_model(dumper: yaml.SafeDumper, data: Model):
    tag = '!' + data.__class__.__name__
    return dumper.represent_mapping(tag, {
        field.name: getattr(data, field.name)
        for field in fields(data.__class__)
    })

yaml.SafeDumper.add_multi_representer(Model, represent_model)
