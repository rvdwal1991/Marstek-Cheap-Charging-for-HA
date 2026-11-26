"""Instelschermen voor Marstek Goedkoop Laden."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import selector

from .const import (
    CONF_CAPACITY_ENTITY,
    CONF_CONNECTION,
    CONF_MODBUS_HUB,
    CONF_MODBUS_SLAVE,
    CONNECTION_ESPHOME,
    CONNECTION_MODBUS,
    DEFAULT_MODBUS_HUB,
    DEFAULT_MODBUS_SLAVE,
    CONF_CAPACITY_KWH,
    CONF_CHARGED_ENERGY_ENTITY,
    CONF_CONTROL_MODE_ENTITY,
    CONF_DEFAULT_EFFICIENCY,
    CONF_DISCHARGED_ENERGY_ENTITY,
    CONF_FORCE_DISCHARGE_POWER_ENTITY,
    CONF_FORCE_MODE_ENTITY,
    CONF_FORCE_POWER_ENTITY,
    CONF_HOUSE_POWER,
    CONF_LOOKAHEAD_HOURS,
    CONF_MARGIN,
    CONF_MAX_DISCHARGE_POWER_ENTITY,
    CONF_MAX_POWER_ENTITY,
    CONF_MIN_LOOKAHEAD_HOURS,
    CONF_MIN_POWER,
    CONF_MIN_SOC,
    CONF_MIN_SOC_ENTITY,
    CONF_BATTERY_CYCLES,
    CONF_BATTERY_PRICE,
    CONF_LANGUAGE,
    CONF_NEGATIVE_PRICE_LIMIT,
    CONF_PRICE_ATTRIBUTE,
    CONF_PRICE_ENTITY,
    CONF_RESERVE_MIN_SOC,
    CONF_SELL_MARGIN,
    CONF_SELL_PRICE_FACTOR,
    CONF_SELL_PRICE_OFFSET,
    CONF_SOC_ENTITY,
    CONF_TOP_HOURS,
    DEFAULT_CAPACITY_KWH,
    DEFAULT_EFFICIENCY,
    DEFAULT_HOUSE_POWER,
    DEFAULT_LOOKAHEAD_HOURS,
    DEFAULT_MARGIN,
    DEFAULT_MIN_LOOKAHEAD_HOURS,
    DEFAULT_MIN_POWER,
    DEFAULT_MIN_SOC,
    DEFAULT_BATTERY_CYCLES,
    DEFAULT_BATTERY_PRICE,
    DEFAULT_LANGUAGE,
    DEFAULT_NEGATIVE_PRICE_LIMIT,
    DEFAULT_PRICE_ATTRIBUTE,
    DEFAULT_RESERVE_MIN_SOC,
    DEFAULT_SELL_MARGIN,
    DEFAULT_SELL_PRICE_FACTOR,
    DEFAULT_SELL_PRICE_OFFSET,
    DEFAULT_TOP_HOURS,
    DOMAIN,
)

# (sleutel, domein, verplicht, herkenbare eindes van de entity_id)
ENTITY_FIELDS: tuple[tuple[str, str, bool, tuple[str, ...]], ...] = (
    (CONF_PRICE_ENTITY, "sensor", True, ("zonneplan_current_hourly_electricity_tariff", "current_electricity_tariff")),
    (CONF_SOC_ENTITY, "sensor", True, ("marstek_battery_state_of_charge", "battery_state_of_charge")),
    (CONF_CONTROL_MODE_ENTITY, "select", True, ("rs485_control_mode",)),
    (CONF_FORCE_MODE_ENTITY, "select", True, ("forcible_charge_discharge",)),
    (CONF_FORCE_POWER_ENTITY, "number", True, ("forcible_charge_power",)),
    (CONF_MAX_POWER_ENTITY, "number", False, ("marstek_max_charge_power", "max_charge_power")),
    (CONF_CAPACITY_ENTITY, "sensor", False, ("marstek_battery_total_energy", "battery_total_energy")),
    (CONF_CHARGED_ENERGY_ENTITY, "sensor", False, ("marstek_total_charging_energy", "total_charging_energy")),
    (CONF_DISCHARGED_ENERGY_ENTITY, "sensor", False, ("marstek_total_discharging_energy", "total_discharging_energy")),
    (CONF_FORCE_DISCHARGE_POWER_ENTITY, "number", False, ("forcible_discharge_power",)),
    (CONF_MAX_DISCHARGE_POWER_ENTITY, "number", False, ("marstek_max_discharge_power", "max_discharge_power")),
    (CONF_MIN_SOC_ENTITY, "number", False, ("discharging_cutoff_capacity",)),
)

# Modbus (bijvoorbeeld Elfin EW11): alles zijn sensoren met de ruwe registerwaarde;
# schrijven gaat via modbus.write_register. Capaciteit, maximaal vermogen en
# ontlaadgrens zijn daar geen registers van deze opzet en vallen dus weg.
MODBUS_FIELDS: tuple[tuple[str, str, bool, tuple[str, ...]], ...] = (
    (CONF_PRICE_ENTITY, "sensor", True, ("zonneplan_current_hourly_electricity_tariff", "current_electricity_tariff")),
    (CONF_SOC_ENTITY, "sensor", True, ("battery_soc",)),
    (CONF_CONTROL_MODE_ENTITY, "sensor", True, ("my_battery_rs485_control_mode",)),
    (CONF_FORCE_MODE_ENTITY, "sensor", True, ("my_battery_force_charge_discharge_mode",)),
    (CONF_FORCE_POWER_ENTITY, "sensor", True, ("forcible_charge_power",)),
    (CONF_FORCE_DISCHARGE_POWER_ENTITY, "sensor", False, ("forcible_discharge_power",)),
    (CONF_CHARGED_ENERGY_ENTITY, "sensor", False, ("total_charging_energy",)),
    (CONF_DISCHARGED_ENERGY_ENTITY, "sensor", False, ("total_discharging_energy",)),
)

OPTIONAL_KEYS = tuple(key for key, _, required, _ in ENTITY_FIELDS if not required)


def _fields(connection: str | None):
    return MODBUS_FIELDS if connection == CONNECTION_MODBUS else ENTITY_FIELDS


def _guess(hass: HomeAssistant, domain: str, endings: tuple[str, ...]) -> str | None:
    """Zoek een entiteit waarvan de naam op een bekend einde uitkomt."""
    entity_ids = sorted(hass.states.async_entity_ids(domain))
    for ending in endings:
        for entity_id in entity_ids:
            if entity_id.endswith(ending):
                return entity_id
    return None


def _entity_schema(
    hass: HomeAssistant, current: dict[str, Any], connection: str | None = None
) -> dict[Any, Any]:
    schema: dict[Any, Any] = {}
    if connection == CONNECTION_MODBUS:
        schema[vol.Required(CONF_MODBUS_HUB, default=current.get(CONF_MODBUS_HUB) or DEFAULT_MODBUS_HUB)] = selector.TextSelector()
        schema[vol.Required(CONF_MODBUS_SLAVE, default=current.get(CONF_MODBUS_SLAVE) or DEFAULT_MODBUS_SLAVE)] = _number(1, 247, 1)
    for key, domain, required, endings in _fields(connection):
        suggested = current.get(key) if key in current else _guess(hass, domain, endings)
        marker = vol.Required if required else vol.Optional
        schema[marker(key, description={"suggested_value": suggested})] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain=domain)
        )
    return schema


def _number(minimum: float, maximum: float, step: float, unit: str | None = None) -> selector.NumberSelector:
    config = selector.NumberSelectorConfig(
        min=minimum, max=maximum, step=step, mode=selector.NumberSelectorMode.BOX
    )
    if unit is not None:
        # Een lege eenheid wordt door Home Assistant geweigerd; dan weglaten.
        config["unit_of_measurement"] = unit
    return selector.NumberSelector(config)


def _param_schema(current: dict[str, Any]) -> dict[Any, Any]:
    def default(key: str, fallback: Any) -> Any:
        value = current.get(key)
        return fallback if value is None else value

    return {
        vol.Required(CONF_LANGUAGE, default=default(CONF_LANGUAGE, DEFAULT_LANGUAGE)): selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=[
                    {"value": "auto", "label": "Automatic / Automatisch"},
                    {"value": "nl", "label": "Nederlands"},
                    {"value": "en", "label": "English"},
                ],
                mode=selector.SelectSelectorMode.DROPDOWN,
            )
        ),
        vol.Required(CONF_PRICE_ATTRIBUTE, default=default(CONF_PRICE_ATTRIBUTE, DEFAULT_PRICE_ATTRIBUTE)): selector.TextSelector(),
        vol.Required(CONF_CAPACITY_KWH, default=default(CONF_CAPACITY_KWH, DEFAULT_CAPACITY_KWH)): _number(0.5, 100, 0.01, "kWh"),
        vol.Required(CONF_DEFAULT_EFFICIENCY, default=default(CONF_DEFAULT_EFFICIENCY, DEFAULT_EFFICIENCY)): _number(0.5, 1, 0.01),
        vol.Required(CONF_BATTERY_PRICE, default=default(CONF_BATTERY_PRICE, DEFAULT_BATTERY_PRICE)): _number(0, 20000, 10, "€"),
        vol.Required(CONF_BATTERY_CYCLES, default=default(CONF_BATTERY_CYCLES, DEFAULT_BATTERY_CYCLES)): _number(500, 20000, 100),
        vol.Required(CONF_MARGIN, default=default(CONF_MARGIN, DEFAULT_MARGIN)): _number(0, 0.5, 0.005, "€/kWh"),
        vol.Required(CONF_TOP_HOURS, default=default(CONF_TOP_HOURS, DEFAULT_TOP_HOURS)): _number(1, 24, 1),
        vol.Required(CONF_LOOKAHEAD_HOURS, default=default(CONF_LOOKAHEAD_HOURS, DEFAULT_LOOKAHEAD_HOURS)): _number(2, 48, 1),
        vol.Required(CONF_MIN_LOOKAHEAD_HOURS, default=default(CONF_MIN_LOOKAHEAD_HOURS, DEFAULT_MIN_LOOKAHEAD_HOURS)): _number(1, 48, 1),
        vol.Required(CONF_MIN_POWER, default=default(CONF_MIN_POWER, DEFAULT_MIN_POWER)): _number(100, 5000, 50, "W"),
        vol.Required(CONF_NEGATIVE_PRICE_LIMIT, default=default(CONF_NEGATIVE_PRICE_LIMIT, DEFAULT_NEGATIVE_PRICE_LIMIT)): _number(-1, 1, 0.005, "€/kWh"),
        vol.Required(CONF_SELL_MARGIN, default=default(CONF_SELL_MARGIN, DEFAULT_SELL_MARGIN)): _number(0, 1, 0.005, "€/kWh"),
        vol.Required(CONF_HOUSE_POWER, default=default(CONF_HOUSE_POWER, DEFAULT_HOUSE_POWER)): _number(0, 5000, 10, "W"),
        vol.Required(CONF_RESERVE_MIN_SOC, default=default(CONF_RESERVE_MIN_SOC, DEFAULT_RESERVE_MIN_SOC)): _number(0, 100, 1, "%"),
        vol.Required(CONF_MIN_SOC, default=default(CONF_MIN_SOC, DEFAULT_MIN_SOC)): _number(0, 100, 1, "%"),
        vol.Required(CONF_SELL_PRICE_FACTOR, default=default(CONF_SELL_PRICE_FACTOR, DEFAULT_SELL_PRICE_FACTOR)): _number(0, 2, 0.001),
        vol.Required(CONF_SELL_PRICE_OFFSET, default=default(CONF_SELL_PRICE_OFFSET, DEFAULT_SELL_PRICE_OFFSET)): _number(0, 1, 0.001, "€/kWh"),
    }


def _normalize(user_input: dict[str, Any], connection: str = CONNECTION_ESPHOME) -> dict[str, Any]:
    """Leeggemaakte optionele velden expliciet op None zetten."""
    data = dict(user_input)
    data[CONF_CONNECTION] = connection
    for key in OPTIONAL_KEYS:
        data.setdefault(key, None)
    if CONF_MODBUS_SLAVE in data:
        data[CONF_MODBUS_SLAVE] = int(data[CONF_MODBUS_SLAVE])
    return data


class MarstekGoedkoopLadenConfigFlow(ConfigFlow, domain=DOMAIN):
    """Eerste keer instellen."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        return self.async_show_menu(step_id="user", menu_options=[CONNECTION_ESPHOME, CONNECTION_MODBUS])

    async def async_step_esphome(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        return await self._async_entities(CONNECTION_ESPHOME, "esphome", user_input)

    async def async_step_modbus(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        return await self._async_entities(CONNECTION_MODBUS, "modbus", user_input)

    async def _async_entities(
        self, connection: str, step_id: str, user_input: dict[str, Any] | None
    ) -> ConfigFlowResult:
        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_CONTROL_MODE_ENTITY])
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title="Marstek Goedkoop Laden", data=_normalize(user_input, connection)
            )
        return self.async_show_form(
            step_id=step_id, data_schema=vol.Schema(_entity_schema(self.hass, {}, connection))
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return MarstekGoedkoopLadenOptionsFlow()


class MarstekGoedkoopLadenOptionsFlow(OptionsFlow):
    """Entiteiten en de rekenregel aanpassen."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        current = {**self.config_entry.data, **self.config_entry.options}
        connection = current.get(CONF_CONNECTION) or CONNECTION_ESPHOME
        if user_input is not None:
            return self.async_create_entry(data=_normalize(user_input, connection))
        schema = {**_entity_schema(self.hass, current, connection), **_param_schema(current)}
        return self.async_show_form(step_id="init", data_schema=vol.Schema(schema))
