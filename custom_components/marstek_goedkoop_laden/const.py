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

# Instellingen van de rekenregel
CONF_CAPACITY_KWH = "capacity_kwh"
CONF_TOP_HOURS = "top_hours"
CONF_LOOKAHEAD_HOURS = "lookahead_hours"
CONF_MIN_LOOKAHEAD_HOURS = "min_lookahead_hours"
CONF_MARGIN = "margin"
CONF_MIN_POWER = "min_power"
CONF_DEFAULT_EFFICIENCY = "default_efficiency"

DEFAULT_PRICE_ATTRIBUTE = "forecast"
DEFAULT_CAPACITY_KWH = 5.12
DEFAULT_TOP_HOURS = 6
DEFAULT_LOOKAHEAD_HOURS = 18
DEFAULT_MIN_LOOKAHEAD_HOURS = 8
DEFAULT_MARGIN = 0.02
DEFAULT_MIN_POWER = 400
DEFAULT_MAX_POWER = 2500
DEFAULT_EFFICIENCY = 0.77

# Opties van de Marstek-selects (LilyGO RS485 / ESPHome)
MODE_ENABLE = "enable"
MODE_DISABLE = "disable"
FORCE_CHARGE = "charge"
FORCE_DISCHARGE = "discharge"
FORCE_STOP = "stop"

# Na een stuuropdracht even niets nieuws sturen: de Marstek meldt zijn nieuwe
# toestand pas na een paar seconden terug.
COMMAND_SETTLE_SECONDS = 12
UPDATE_INTERVAL_SECONDS = 60
