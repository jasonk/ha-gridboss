import logging
from dataclasses import dataclass, field
from typing import Literal, Any
from http import HTTPStatus

from aiohttp import ClientSession, ClientTimeout

from .errors import GridBossAuthError, GridBossAPIError, GridBossError
from .models import GridBoss, Inverter, Battery, DeviceOptions

_LOGGER = logging.getLogger(__name__)

@dataclass(kw_only=True)
class EG4Client:
    username: str
    password: str
    timeout: int = 60

    _session: ClientSession | None = field(default=None, init=False, repr=False)

    @property
    def session(self) -> ClientSession:
        if not self._session:
            self._session = ClientSession(
                headers={"Accept": "application/json"},
                base_url="https://monitor.eg4electronics.com",
                timeout=ClientTimeout(total=self.timeout),
            )
        return self._session
    @session.setter
    def session(self, value: ClientSession):
        self._session = value

    async def request(
        self,
        method: Literal["GET", "POST"],
        path: str,
        data: dict[str, str] | None = None,
        retry: bool = True,
    ):
        session = self.session

        async with session.request(method, path, data=data) as res:
            if res.status == HTTPStatus.UNAUTHORIZED and retry:
                await self.login()
                return await self.request(method, path, data=data, retry=False)

            if res.status == HTTPStatus.OK:
                return await res.json()
            text = await res.text()
            raise GridBossAPIError(f"API error: {text}", res)

    _login: dict[str, Any] | None = field(default=None, init=False)
    async def login(self):
        res = await self.session.post(
            "/WManage/api/login",
            data={"account": self.username, "password": self.password},
        )
        if res.status != HTTPStatus.OK:
            text = await res.text()
            raise GridBossAuthError(f"Login failed: {text}", res)

        data = await res.json()
        if not data.pop("success", None):
            raise GridBossAuthError(data.get("error", "Login failed"), res)
        self._login = data
        return self._login

    async def get_data(
        self,
        url: str,
        data: dict[str, str],
    ) -> dict[str, Any]:
        res = await self.request("POST", url, data=data)

        if isinstance(res, dict) and res.get("success", None):
            return res
        raise GridBossError(res.get("msg", "UNKNOWN_ERROR"))

    async def close(self):
        if self._session:
            await self._session.close()

    async def get_gridboss(self, plant_id: int|None = None) -> GridBoss:
        plant = self.find_plant(plant_id=plant_id)
        if not plant:
            raise GridBossError(f"Plant {plant_id} not found")
        assert self._login
        inverters = plant.get("inverters", []).copy()
        def find_midbox():
            for inv in inverters:
                if inv.get('parallelMidboxSn'):
                    inverters.remove(inv)
                    return inv
            raise ValueError("No midbox found")


        midbox = find_midbox()

        gridboss = GridBoss(
            plant_id=plant["plantId"],
            **get_device_options(midbox),
        )
        for inv in inverters:
            inverter = Inverter(
                gridboss=gridboss,
                battery_type=inv.get("batteryTypeText"),
                **get_device_options(inv),
            )
            if inv.get("withbatteryData"):
                battery_info = await self.get_inverter_battery_info(
                    inverter.serial,
                )
                for bat in battery_info.get("batteryArray", []):
                    battery = Battery(
                        inverter=inverter,
                        key=bat["batteryKey"],
                        serial=bat["batterySn"],
                        device_type=bat["batteryType"],
                        index=bat["batIndex"],
                        sw_version=bat.get("fwVersionText"),
                    )
                    inverter.batteries.append(battery)
            gridboss.inverters.append(inverter)
        return gridboss

    def find_plant(
        self,
        plant_id: int | None = None,
        serial: str | None = None,
    ) -> dict[str, Any] | None:
        if not self._login:
            return None
        plants = self._login.get("plants", [])
        if plant_id:
            for plant in plants:
                if plant.get("plantId") == plant_id:
                    return plant
        if serial:
            for plant in plants:
                for inverter in plant.get("inverters", []):
                    if inverter.get("serialNum") == serial:
                        return plant
        if len(plants) == 1:
            return plants[0]
        return None

    async def get_inverter_runtime(self, serial: str):
        return await self.get_data(
            "/WManage/api/inverter/getInverterRuntime",
            data={"serialNum": serial},
        )

    async def get_inverter_energy_info(self, serial: str):
        return await self.get_data(
            "/WManage/api/inverter/getInverterEnergyInfo",
            data={"serialNum": serial},
        )

    async def get_inverter_energy_info_parallel(self, serial: str):
        return await self.get_data(
            "/WManage/api/inverter/getInverterEnergyInfoParallel",
            data={"serialNum": serial},
        )

    async def get_inverter_battery_info(self, serial: str):
        return await self.get_data(
            "/WManage/api/battery/getBatteryInfo",
            data={"serialNum": serial},
        )

    async def get_inverter_battery_info_for_set(self, serial: str):
        return await self.get_data(
            "/WManage/api/battery/getBatteryInfoForSet",
            data={"serialNum": serial},
        )

    async def get_inverter_parallel_group_details(self, serial: str):
        return await self.get_data(
            "/WManage/api/inverterOverview/getParallelGroupDetails",
            data={"serialNum": serial},
        )

    async def get_plant_inverter_list(self, plant_id: int = -1):
        return await self.get_data(
            "/WManage/api/inverterOverview/list",
            data={
                "page": "1",
                "rows": "30",
                "plantId": str(plant_id),
                "searchText": "",
                "statusText": "all",
            },
        )

#   async def get_plant_dongle_list(self, plant_id: int = -1):
#       return await self.get_data(
#           "/WManage/api/datalog/list",
#           data={
#               "page": "1",
#               "rows": "30",
#               "plantId": str(plant_id),
#               "searchType": "serialNum",
#               "searchText": "",
#           },
#       )

# /WManage/web/config/datalog/getDongleInfo
#   serialNum=DG50902244
#{
#    "success": true,
#    "firmwareVersion": "V2.07",
#    "datalogType": "ESP_WIFI",
#    "datalogTypeText": "E Wi-Fi"
#}

#   async def get_inverter_parameters(self, serial: str):
#       params: dict[str, Any] = {}

#       for start in (0, 127, 240, 500, 2000, 5000):
#           part = await self.get_data(
#               "/WManage/web/maintain/remoteRead/read",
#               data={
#                   "inverterSn": serial,
#                   "startRegister": str(start),
#                   "pointNumber": "127",
#                   "autoRetry": "true",
#               },
#           )
#           for x in (
#               "valueFrame", "inverterSn", "deviceType",
#               "startRegister", "pointNumber",
#           ):
#               part.pop(x, None)
#           params.update(part)
#       return params

#   async def write_inverter_parameter(
#       self,
#       serial: str,
#       parameter: str,
#       value: str,
#   ) -> bool:
#       payload = {
#           "inverterSn": serial,
#           "holdParam": parameter,
#           "valueText": value,
#           "clientType": "WEB",
#           "remoteSetType": "NORMAL",
#       }
#       res = await self.request(
#           "POST",
#           "/WManage/web/maintain/remoteSet/write",
#           data=payload,
#       )
#       return res.get("success", False)

    async def get_inverter_midbox_runtime(self, serial: str):
        return await self.get_data(
            "/WManage/api/midbox/getMidboxRuntime",
            data={"serialNum": serial},
        )

def get_device_options(data: dict[str, Any]) -> DeviceOptions:
    return DeviceOptions(
        serial=data["serialNum"],
        device_type=data["deviceTypeText"],
        sw_version=data["fwVersion"],
        hw_version=data["hardwareVersion"],
    )
