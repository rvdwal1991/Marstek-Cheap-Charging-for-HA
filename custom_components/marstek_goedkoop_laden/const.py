"""Constanten voor Marstek Goedkoop Laden."""

from __future__ import annotations

DOMAIN = "marstek_goedkoop_laden"

# Entiteiten
CONF_PRICE_ENTITY = "price_entity"
CONF_PRICE_ATTRIBUTE = "price_attribute"
CONF_SOC_ENTITY = "soc_entity"
CONF_CAPACITY_ENTITY = "capacity_entity"
CONF_CONTROL_MODE_ENTITY = "control_mode_entity"
CONF_FORCE_MODE_ENTITY = "force_mode_entity"
CONF_FORCE_POWER_ENTITY = "force_power_entity"
CONF_MAX_POWER_ENTITY = "max_power_entity"
CONF_CHARGED_ENERGY_ENTITY = "charged_energy_entity"
CONF_DISCHARGED_ENERGY_ENTITY = "discharged_energy_entity"
CONF_FORCE_DISCHARGE_POWER_ENTITY = "force_discharge_power_entity"
CONF_MAX_DISCHARGE_POWER_ENTITY = "max_discharge_power_entity"
CONF_MIN_SOC_ENTITY = "min_soc_entity"

# Verbinding met de Marstek: ESPHome-entiteiten (LilyGO RS485) of Modbus-registers
# via een Modbus-hub in Home Assistant (bijvoorbeeld een Elfin EW11).
CONF_CONNECTION = "connection"
CONF_MODBUS_HUB = "modbus_hub"
CONF_MODBUS_SLAVE = "modbus_slave"
CONNECTION_ESPHOME = "esphome"
CONNECTION_MODBUS = "modbus"
DEFAULT_MODBUS_HUB = "MarstekVenus"
DEFAULT_MODBUS_SLAVE = 1

# Modbus-registers van de Marstek Venus (RS485-protocol)
REG_CONTROL_MODE = 42000
REG_FORCE_MODE = 42010
REG_FORCE_CHARGE_POWER = 42020
REG_FORCE_DISCHARGE_POWER = 42021
RAW_CONTROL_ENABLE = 21930  # 0x55AA
RAW_CONTROL_DISABLE = 21947  # 0x55BB
RAW_FORCE = {0: "stop", 1: "charge", 2: "discharge"}

# Instellingen van de rekenregel
CONF_CAPACITY_KWH = "capacity_kwh"
CONF_TOP_HOURS = "top_hours"
CONF_LOOKAHEAD_HOURS = "lookahead_hours"
CONF_MIN_LOOKAHEAD_HOURS = "min_lookahead_hours"
CONF_MARGIN = "margin"
CONF_MIN_POWER = "min_power"
CONF_DEFAULT_EFFICIENCY = "default_efficiency"

# Instellingen voor verkopen
CONF_SELL_MARGIN = "sell_margin"
CONF_HOUSE_POWER = "house_power"
CONF_RESERVE_MIN_SOC = "reserve_min_soc"
CONF_MIN_SOC = "min_soc"
CONF_SELL_PRICE_FACTOR = "sell_price_factor"
CONF_SELL_PRICE_OFFSET = "sell_price_offset"
CONF_NEGATIVE_PRICE_LIMIT = "negative_price_limit"
CONF_LANGUAGE = "language"
CONF_BATTERY_PRICE = "battery_price"
CONF_BATTERY_CYCLES = "battery_cycles"

DEFAULT_PRICE_ATTRIBUTE = "forecast"
DEFAULT_CAPACITY_KWH = 5.12
DEFAULT_TOP_HOURS = 6
DEFAULT_LOOKAHEAD_HOURS = 18
DEFAULT_MIN_LOOKAHEAD_HOURS = 8
DEFAULT_MARGIN = 0.02
DEFAULT_MIN_POWER = 400
DEFAULT_MAX_POWER = 2500
DEFAULT_EFFICIENCY = 0.77
DEFAULT_SELL_MARGIN = 0.10
DEFAULT_HOUSE_POWER = 400
DEFAULT_RESERVE_MIN_SOC = 20
DEFAULT_MIN_SOC = 12
DEFAULT_SELL_PRICE_FACTOR = 1.0
DEFAULT_SELL_PRICE_OFFSET = 0.0
DEFAULT_NEGATIVE_PRICE_LIMIT = 0.0
DEFAULT_LANGUAGE = "auto"
DEFAULT_BATTERY_PRICE = 0.0
DEFAULT_BATTERY_CYCLES = 6000

# Opties van de Marstek-selects (LilyGO RS485 / ESPHome)
MODE_ENABLE = "enable"
MODE_DISABLE = "disable"
FORCE_CHARGE = "charge"
FORCE_DISCHARGE = "discharge"
FORCE_STOP = "stop"

# Na een stuuropdracht even niets nieuws sturen: de Marstek meldt zijn nieuwe
# toestand pas terug bij de volgende uitlezing, en dat kan tientallen seconden duren.
COMMAND_SETTLE_SECONDS = 30
UPDATE_INTERVAL_SECONDS = 60
