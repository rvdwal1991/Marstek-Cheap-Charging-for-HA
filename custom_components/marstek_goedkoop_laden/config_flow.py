"""Instelschermen voor Marstek Goedkoop Laden."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import selector

from .const import (
    CONF_CAPACITY_ENTITY,
    CONF_CAPACITY_KWH,
    CONF_CHARGED_ENERGY_ENTITY,
    CONF_CONTROL_MODE_ENTITY,
    CONF_DEFAULT_EFFICIENCY,
    CONF_DISCHARGED_ENERGY_ENTITY,
    CONF_FORCE_MODE_ENTITY,
    CONF_FORCE_POWER_ENTITY,
    CONF_LOOKAHEAD_HOURS,
    CONF_MARGIN,
    CONF_MAX_POWER_ENTITY,
    CONF_MIN_LOOKAHEAD_HOURS,
    CONF_MIN_POWER,
    CONF_PRICE_ATTRIBUTE,
    CONF_PRICE_ENTITY,
    CONF_SOC_ENTITY,
    CONF_TOP_HOURS,
    DEFAULT_CAPACITY_KWH,
    DEFAULT_EFFICIENCY,
    DEFAULT_LOOKAHEAD_HOURS,
    DEFAULT_MARGIN,
    DEFAULT_MIN_LOOKAHEAD_HOURS,
    DEFAULT_MIN_POWER,
    DEFAULT_PRICE_ATTRIBUTE,
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
)

OPTIONAL_KEYS = tuple(key for key, _, required, _ in ENTITY_FIELDS if not required)


def _guess(hass: HomeAssistant, domain: str, endings: tuple[str, ...]) -> str | None:
    """Zoek een entiteit waarvan de naam op een bekend einde uitkomt."""
    entity_ids = sorted(hass.states.async_entity_ids(domain))
    for ending in endings:
        for entity_id in entity_ids:
            if entity_id.endswith(ending):
                return entity_id
    return None


def _entity_schema(hass: HomeAssistant, current: dict[str, Any]) -> dict[Any, Any]:
    schema: dict[Any, Any] = {}
    for key, domain, required, endings in ENTITY_FIELDS:
        suggested = current.get(key) if key in current else _guess(hass, domain, endings)
        marker = vol.Required if required else vol.Optional
        schema[marker(key, description={"suggested_value": suggested})] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain=domain)
        )
    return schema


def _number(minimum: float, maximum: float, step: float, unit: str | None = None) -> selector.NumberSelector:
    return selector.NumberSelector(
        selector.NumberSelectorConfig(
            min=minimum,
            max=maximum,
            step=step,
            unit_of_measurement=unit,
            mode=selector.NumberSelectorMode.BOX,
        )
    )


def _param_schema(current: dict[str, Any]) -> dict[Any, Any]:
    def default(key: str, fallback: Any) -> Any:
        value = current.get(key)
        return fallback if value is None else value

    return {
        vol.Required(CONF_PRICE_ATTRIBUTE, default=default(CONF_PRICE_ATTRIBUTE, DEFAULT_PRICE_ATTRIBUTE)): selector.TextSelector(),
        vol.Required(CONF_CAPACITY_KWH, default=default(CONF_CAPACITY_KWH, DEFAULT_CAPACITY_KWH)): _number(0.5, 100, 0.01, "kWh"),
        vol.Required(CONF_DEFAULT_EFFICIENCY, default=default(CONF_DEFAULT_EFFICIENCY, DEFAULT_EFFICIENCY)): _number(0.5, 1, 0.01),
        vol.Required(CONF_MARGIN, default=default(CONF_MARGIN, DEFAULT_MARGIN)): _number(0, 0.5, 0.005, "€/kWh"),
        vol.Required(CONF_TOP_HOURS, default=default(CONF_TOP_HOURS, DEFAULT_TOP_HOURS)): _number(1, 24, 1),
        vol.Required(CONF_LOOKAHEAD_HOURS, default=default(CONF_LOOKAHEAD_HOURS, DEFAULT_LOOKAHEAD_HOURS)): _number(2, 48, 1),
        vol.Required(CONF_MIN_LOOKAHEAD_HOURS, default=default(CONF_MIN_LOOKAHEAD_HOURS, DEFAULT_MIN_LOOKAHEAD_HOURS)): _number(1, 48, 1),
        vol.Required(CONF_MIN_POWER, default=default(CONF_MIN_POWER, DEFAULT_MIN_POWER)): _number(100, 5000, 50, "W"),
    }


def _normalize(user_input: dict[str, Any]) -> dict[str, Any]:
    """Leeggemaakte optionele velden expliciet op None zetten."""
    data = dict(user_input)
    for key in OPTIONAL_KEYS:
        data.setdefault(key, None)
    return data


class MarstekGoedkoopLadenConfigFlow(ConfigFlow, domain=DOMAIN):
    """Eerste keer instellen."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_CONTROL_MODE_ENTITY])
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title="Marstek Goedkoop Laden", data=_normalize(user_input))
        return self.async_show_form(
            step_id="user", data_schema=vol.Schema(_entity_schema(self.hass, {}))
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return MarstekGoedkoopLadenOptionsFlow()


class MarstekGoedkoopLadenOptionsFlow(OptionsFlow):
    """Entiteiten en de rekenregel aanpassen."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data=_normalize(user_input))
        current = {**self.config_entry.data, **self.config_entry.options}
        schema = {**_entity_schema(self.hass, current), **_param_schema(current)}
        return self.async_show_form(step_id="init", data_schema=vol.Schema(schema))
