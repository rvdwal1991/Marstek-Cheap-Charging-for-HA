"""Sensoren: het laadplan en de belangrijkste getallen eruit."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfEnergy, UnitOfPower
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import ChargePlanCoordinator
from .entity import ChargePlanEntity
from .planner import SELL_STATUSES, STATUSES, Plan, SellPlan


def _iso(moment: datetime | None) -> str | None:
    return moment.isoformat() if moment else None


def _plan_attributes(plan: Plan) -> dict[str, Any]:
    """Attributen met dezelfde namen als de eerdere template-sensor."""
    return {
        "laaduren": [h.isoformat() for h in plan.charge_hours],
        "venster": [h.isoformat() for h in plan.window],
        "eind": _iso(plan.window_end),
        "uren_nodig": plan.hours_needed,
        "vermogen": plan.power_w,
        "klaar_tot": _iso(plan.done_until),
        "tekst": plan.text,
    }


def _sell_attributes(sell: SellPlan) -> dict[str, Any]:
    return {
        "verkoopuren": [h.isoformat() for h in sell.sell_hours],
        "vermogen": sell.power_w,
        "overschot_kwh": sell.energy_kwh,
        "reserve_soc": sell.reserve_soc,
        "gemiddelde_prijs": sell.average_price,
        "drempelprijs": sell.threshold,
        "terugkoopprijs": sell.refill_price,
        "tekst": sell.text,
    }


@dataclass(frozen=True, kw_only=True)
class ChargePlanSensorDescription(SensorEntityDescription):
    """Beschrijving van een sensor."""

    value_fn: Callable[[Plan], Any]
    attributes_fn: Callable[[Plan], dict[str, Any]] | None = None


SENSORS: tuple[ChargePlanSensorDescription, ...] = (
    ChargePlanSensorDescription(
        key="laadplan",
        device_class=SensorDeviceClass.ENUM,
        options=STATUSES,
        value_fn=lambda plan: plan.status,
        attributes_fn=_plan_attributes,
    ),
    ChargePlanSensorDescription(
        key="laadvermogen",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda plan: plan.power_w,
    ),
    ChargePlanSensorDescription(
        key="bij_te_laden",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=1,
        value_fn=lambda plan: plan.energy_kwh if plan.charge_hours else None,
    ),
    ChargePlanSensorDescription(
        key="start_bijladen",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda plan: plan.charge_start,
    ),
    ChargePlanSensorDescription(
        key="einde_bijladen",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda plan: plan.charge_end,
    ),
    ChargePlanSensorDescription(
        key="laadprijs",
        native_unit_of_measurement="€/kWh",
        suggested_display_precision=3,
        value_fn=lambda plan: plan.average_price,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Maak de sensoren aan."""
    coordinator: ChargePlanCoordinator = entry.runtime_data
    entities: list[SensorEntity] = [
        ChargePlanSensor(coordinator, description) for description in SENSORS
    ]
    entities.append(SellPlanSensor(coordinator))
    async_add_entities(entities)


class ChargePlanSensor(ChargePlanEntity, SensorEntity):
    """Sensor die een waarde uit het laadplan toont."""

    entity_description: ChargePlanSensorDescription

    def __init__(
        self, coordinator: ChargePlanCoordinator, description: ChargePlanSensorDescription
    ) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> Any:
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        if self.entity_description.attributes_fn is None:
            return None
        return self.entity_description.attributes_fn(self.coordinator.data)


class SellPlanSensor(ChargePlanEntity, SensorEntity):
    """Het verkoopplan: of en wanneer er overschot aan het net wordt verkocht."""

    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = SELL_STATUSES

    def __init__(self, coordinator: ChargePlanCoordinator) -> None:
        super().__init__(coordinator, "verkoopplan")

    @property
    def native_value(self) -> str:
        return self.coordinator.sell_plan.status

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return _sell_attributes(self.coordinator.sell_plan)

