import logging
from dataclasses import dataclass
from datetime import datetime

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.const import (
    PERCENTAGE,
    UnitOfPower,
    UnitOfElectricPotential,
    UnitOfElectricCurrent,
    UnitOfEnergy,
    UnitOfFrequency,
    UnitOfMass,
    UnitOfTemperature,
)
from homeassistant.util.dt import parse_datetime

from .coordinator import GridBossConfigEntry
from .entities import GridBossEntity, GridBossEntityDescription
from .utils import ignore

_LOGGER = logging.getLogger(__name__)

def parse_timestamp(value: str|None) -> datetime | None:
    if value is None:
        return None
    value = value.strip().replace(" ", "T")
    if not value.endswith("Z"):
        value += "Z"
    return parse_datetime(value)

@dataclass(frozen=True, kw_only=True)
class GridBossSensorEntityDescription(
    SensorEntityDescription, GridBossEntityDescription,
):
    # From EntityDescription:
    #   key: str
    #   device_class: str | None = None
    #   entity_category: EntityCategory | None = None
    #   entity_registry_enabled_default: bool = True
    #   entity_registry_visible_default: bool = True
    #   force_update: bool = False
    #   icon: str | None = None
    #   has_entity_name: bool = False
    #   name: str | UndefinedType | None = UNDEFINED
    #   translation_key: str | None = None
    #   translation_placeholders: Mapping[str, str] | None = None
    #   unit_of_measurement: str | None = None

    # From SensorEntityDescription:
    #   device_class: SensorDeviceClass
    #   native_unit_of_measurement: str
    #   options: list[str]
    #   state_class: SensorStateClass | str
    #   suggested_display_precision
    #   suggested_unit_of_measurement

    scale: float | None = None


SENSORS: list[GridBossSensorEntityDescription] = [
    GridBossSensorEntityDescription(
        name="Status",
        key="statusText",
        icon="mdi:information-outline",
        data_source=("midbox_runtime", "runtime", "battery"),
    ),
    GridBossSensorEntityDescription(
        name="Firmware Code",
        key="fwCode",
        data_source=("midbox_runtime", "runtime"),
    ),
    GridBossSensorEntityDescription(
        name="Last Update",
        key="serverTime",
        device_class=SensorDeviceClass.TIMESTAMP,
        transform=parse_timestamp,
        data_source=("midbox_data", "device_data", "runtime"),
    ),
    GridBossSensorEntityDescription(
        name="CO2 Reduction",
        key="totalCo2ReductionText",
        icon="mdi:molecule-co2",
        native_unit_of_measurement=UnitOfMass.KILOGRAMS,
        state_class=SensorStateClass.TOTAL,
        transform=lambda v: float(v.split(" ")[0]) if v else None,
        data_source="energy_info_parallel",
    ),
    GridBossSensorEntityDescription(
        name="Coal Reduction",
        key="totalCoalReductionText",
        icon="mdi:smoke",
        native_unit_of_measurement=UnitOfMass.KILOGRAMS,
        state_class=SensorStateClass.TOTAL,
        transform=lambda v: float(v.split(" ")[0]) if v else None,
        data_source="energy_info_parallel",
    ),
    GridBossSensorEntityDescription(
        name="Trees Saved",
        key="totalTreeEquivalentText",
        icon="mdi:forest",
        native_unit_of_measurement="trees",
        state_class=SensorStateClass.TOTAL,
        transform=lambda v: float(v) if v else None,
        data_source="energy_info_parallel",
    ),
    GridBossSensorEntityDescription(
        name="Battery Capacity",
        key="capacityPercent",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        data_source="battery_info",
    ),
    GridBossSensorEntityDescription(
        name="Battery Status",
        key="batStatus",
        data_source="battery_info",
    ),
    GridBossSensorEntityDescription(
        name="Number of Batteries",
        key="totalNumber",
        native_unit_of_measurement="batteries",
        data_source="battery_info",
    ),
    GridBossSensorEntityDescription(
        name="Battery Capacity",
        key="fullCapacity",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        icon="mdi:battery",
        scale=0.0512,
        data_source="battery_info",
    ),
    GridBossSensorEntityDescription(
        name="Battery Capacity Remaining",
        key="remainCapacity",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        icon="mdi:battery",
        scale=0.0512,
        data_source="battery_info",
    ),
    GridBossSensorEntityDescription(
        name="Charge Level",
        key="soc",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        data_source="battery",
    ),
    GridBossSensorEntityDescription(
        name="Battery Type",
        key="batteryType",
        icon="mdi:information-outline",
        data_source=("device_data", "runtime", "battery"),
    ),
    GridBossSensorEntityDescription(
        name="Total Voltage",
        key="totalVoltage",
        scale=0.01,
        data_source="battery",
    ),
    GridBossSensorEntityDescription(
        name="Last Update",
        key="lastUpdateTime",
        device_class=SensorDeviceClass.TIMESTAMP,
        transform=parse_timestamp,
        data_source="battery",
    ),
    GridBossSensorEntityDescription(
        name="Health",
        key="soh",
        native_unit_of_measurement=PERCENTAGE,
        data_source="battery",
    ),
    GridBossSensorEntityDescription(
        name="Firmware Version",
        key="fwVersionText",
        data_source="battery",
    ),
    GridBossSensorEntityDescription(
        name="Cycles",
        key="cycleCnt",
        data_source="battery",
    ),
    GridBossSensorEntityDescription(
        name="Notice",
        key="noticeInfo",
        icon="mdi:alert",
        data_source="battery",
    ),
    GridBossSensorEntityDescription(
        name="Charge Voltage Reference",
        key="batChargeVoltRef",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        scale=0.1,
        icon="mdi:flash",
        data_source="battery",
    ),
]

for x in ("Min", "Max"):
    SENSORS.extend([
        GridBossSensorEntityDescription(
            name=f"{x}imum Cell Voltage",
            key=f"bat{x}CellVoltage",
            native_unit_of_measurement=UnitOfElectricPotential.VOLT,
            scale=0.001,
            icon="mdi:flash",
            data_source="battery",
        ),
        GridBossSensorEntityDescription(
            name=f"{x}imum Cell Temperature",
            key=f"bat{x}CellTemp",
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            icon="mdi:thermometer-lines",
            scale=0.1,
            data_source="battery",
        ),
        GridBossSensorEntityDescription(
            name=f"{x}imum Cell Voltage Cell Number",
            key=f"bat{x}CellNumVolt",
            data_source="battery",
        ),
        GridBossSensorEntityDescription(
            name=f"{x}imum Cell Temperature Cell Number",
            key=f"bat{x}CellNumTemp",
            data_source="battery",
        ),
    ])

### RMS Voltage
for name_prefix, key_prefix in [
    ("Grid", "grid"),
    ("UPS", "ups"),
    ("Generator", "gen"),
]:
    SENSORS.extend([
        GridBossSensorEntityDescription(
            name=f"{name_prefix}{' ' + x if x else ''} RMS Voltage",
            key=f"{key_prefix}{x}RmsVolt",
            native_unit_of_measurement=UnitOfElectricPotential.VOLT,
            scale=0.1,
            icon="mdi:flash",
            data_source="midbox_data",
        ) for x in ("", "L1", "L2")
    ])

### RMS Current and Active Power
for name_prefix, key_prefix in [
    ("Grid", "grid"),
    ("UPS", "ups"),
    ("Generator", "gen"),
    ("Load", "load"),
    ("Smart Load 1", "smartLoad1"),
    ("Smart Load 2", "smartLoad2"),
    ("Smart Load 3", "smartLoad3"),
    ("Smart Load 4", "smartLoad4"),
]:
    SENSORS.extend([
        GridBossSensorEntityDescription(
            name=f"{name_prefix} {x} RMS Current",
            key=f"{key_prefix}{x}RmsCurr",
            native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
            # scale=0.1, # TODO - ???
            icon="mdi:flash",
            data_source="midbox_data",
        ) for x in ("L1", "L2")
    ])
    SENSORS.extend([
        GridBossSensorEntityDescription(
            name=f"{name_prefix} {x} Active Power",
            key=f"{key_prefix}{x}ActivePower",
            native_unit_of_measurement=UnitOfPower.WATT,
            icon="mdi:flash",
            data_source="midbox_data",
        ) for x in ("L1", "L2")
    ])

for name, key, icon in [
    ("Solar Generated", "Yielding", "mdi:solar-power"),
    ("Battery Charging", "Charging", "mdi:battery-charging"),
    ("Battery Discharging", "Discharging", "mdi:home-battery-outline"),
    ("Energy Usage", "Usage", "mdi:home-import-outline"),
    ("Imported from Grid", "Import", "mdi:transmission-tower-import"),
    ("Exported to Grid", "Export", "mdi:transmission-tower-export"),
]:
    SENSORS.extend([
        GridBossSensorEntityDescription(
            name=f"{name} Today",
            key=f"today{key}",
            icon=icon,
            native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
            device_class=SensorDeviceClass.ENERGY,
            state_class=SensorStateClass.TOTAL_INCREASING,
            scale=0.1,
            data_source="energy_info_parallel",
        ),
        GridBossSensorEntityDescription(
            name=f"{name} Total",
            key=f"total{key}",
            icon=icon,
            native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
            device_class=SensorDeviceClass.ENERGY,
            state_class=SensorStateClass.TOTAL,
            scale=0.1,
            data_source="energy_info_parallel",
        ),
    ])

for x in (1, 2, 3):
    SENSORS.extend([
        GridBossSensorEntityDescription(
            name=f"PV{x} Voltage",
            key=f"vpv{x}",
            native_unit_of_measurement=UnitOfElectricPotential.VOLT,
            scale=0.1,
            icon="mdi:flash",
            data_source=("device_data", "runtime"),
        ),
        GridBossSensorEntityDescription(
            name=f"PV{x} Power",
            key=f"ppv{x}",
            native_unit_of_measurement=UnitOfPower.WATT,
            icon="mdi:flash",
            data_source=("device_data", "runtime"),
        ),
    ])

for key, name in [
    ("ppv", "PV Power Total"),
    ("consumptionPower", "Consumption Power"),
]:
    SENSORS.append(GridBossSensorEntityDescription(
        name=name,
        key=key,
        native_unit_of_measurement=UnitOfPower.WATT,
        icon="mdi:flash",
        data_source=("device_data", "runtime"),
    ))

SENSORS.extend([
    GridBossSensorEntityDescription(
        name="Generator Power",
        key="genPower",
        native_unit_of_measurement=UnitOfPower.WATT,
        icon="mdi:flash",
        data_source="device_data",
    ),
    GridBossSensorEntityDescription(
        name="Generator Voltage",
        key="genVolt",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        scale=0.1,
        data_source="device_data",
    ),
])

for key, name in [
    ("vacr", "AC Voltage (R-phase)"),
    ("vacs", "AC Voltage (S-phase)"),
    ("vact", "AC Voltage (T-phase)"),
    # Disabled because their values make no sense...
    #("vepsr", "Off-grid Output Voltage (R-phase)"),
    #("vepss", "Off-grid Output Voltage (S-phase)"),
    #("vepst", "Off-grid Output Voltage (T-phase)"),
    ("vBus1", "Bus 1 Voltage"),
    ("vBus2", "Bus 2 Voltage"),
    ("vBat", "Battery Voltage"),
]:
    SENSORS.append(GridBossSensorEntityDescription(
        name=name,
        key=key,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        scale=0.1,
        icon="mdi:flash",
        data_source=("device_data", "runtime"),
    ))

for key, name in [
    ("fac", "AC Frequency"),
    ("feps", "EPS Frequency"),
]:
    SENSORS.append(GridBossSensorEntityDescription(
        name=name,
        key=key,
        native_unit_of_measurement=UnitOfFrequency.HERTZ,
        device_class=SensorDeviceClass.FREQUENCY,
        scale=0.01,
        icon="mdi:sine-wave",
        data_source=("device_data", "runtime"),
    ))

for key, name in [
    ("genFreq", "Generator Frequency"),
    ("gridFreq", "Grid Frequency"),
    ("phaseLockFreq", "Phase Lock Frequency"),
]:
    SENSORS.append(GridBossSensorEntityDescription(
        name=name,
        key=key,
        native_unit_of_measurement=UnitOfFrequency.HERTZ,
        device_class=SensorDeviceClass.FREQUENCY,
        scale=0.01,
        icon="mdi:sine-wave",
        data_source="midbox_data",
    ))

for key, name in [
    ("tradiator1", "Radiator Temperature 1"),
    ("tradiator2", "Radiator Temperature 2"),
    ("tinner", "Internal Ring Temperature"),
    ("tBat", "Battery Temperature"),
]:
    SENSORS.append(GridBossSensorEntityDescription(
        name=name,
        key=key,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        icon="mdi:thermometer-lines",
        data_source=("device_data", "runtime"),
    ))


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: GridBossConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    ignore(hass)
    coordinator = config_entry.runtime_data
    gridboss = coordinator.gridboss

    for item in gridboss.items():
        descs = item.filter_entity_descriptions(SENSORS)
        if descs:
            _LOGGER.debug("Adding %d sensors for %s", len(descs), item.name)
            async_add_entities([
                GridBossSensor(coordinator, desc, item)
                for desc in descs
            ])

class GridBossSensor( # pyright: ignore
    GridBossEntity[GridBossSensorEntityDescription],
    SensorEntity,
):
    def get_data(self):
        value = super().get_data()
        if isinstance(value, (int, float)) and self._desc.scale:
            value *= self._desc.scale
        return value

    @callback
    def _handle_coordinator_update(self) -> None:
        self._attr_native_value = self.get_data()
        self.async_write_ha_state()
