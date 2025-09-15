from typing import Final

DOMAIN: Final = "gridboss"
PLATFORMS: Final = [
    "binary_sensor",
    "sensor",
]

CONF_USERNAME: Final = "username"
CONF_PASSWORD: Final = "password" # noqa: S105
CONF_PLANT_ID: Final = "plant_id"
CONF_SERIAL: Final = "serial_number"

CONF_POLLING_INTERVAL: Final = "polling_interval_seconds"
DEFAULT_POLLING_INTERVAL: Final = 30
