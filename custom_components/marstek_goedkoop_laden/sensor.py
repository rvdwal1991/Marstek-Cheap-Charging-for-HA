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

from .i18n import tr

from homeassistant.util import dt as dt_util

from .coordinator import ChargePlanCoordinator
from .entity import ChargePlanEntity
from .planner import SELL_STATUSES, STATUSES, Plan, SellPlan, one_way_efficiency


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
    entities.append(ExpectedGainSensor(coordinator))
    entities.append(EfficiencySensor(coordinator))
    entities.append(RealizedGainSensor(coordinator, "opbrengst_vandaag"))
    entities.append(RealizedGainSensor(coordinator, "opbrengst_deze_week"))
    entities.append(RealizedGainSensor(coordinator, "opbrengst_vorige_week"))
    entities.append(RealizedGainSensor(coordinator, "opbrengst_deze_maand"))
    entities.append(RealizedGainSensor(coordinator, "opbrengst_dit_jaar"))
    async_add_entities(entities)


class ChargePlanSensor(ChargePlanEntity, SensorEntity):
    """Sensor die een waarde uit het laadplan toont."""

    entity_description: ChargePlanSensorDescription
    # Het stroomschema verandert vaak en hoeft niet in de database.
    _unrecorded_attributes = frozenset({"stroomschema"})

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
        attributes = self.entity_description.attributes_fn(self.coordinator.data)
        if "tekst" in attributes:
            attributes["tekst"] = tr(self.coordinator.language, attributes["tekst"])
        if self.entity_description.key == "laadplan":
            # Tijdlijn en controles voor de dashboardkaart.
            attributes["stroomschema"] = self.coordinator.flow
        return attributes


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
        attributes = _sell_attributes(self.coordinator.sell_plan)
        attributes["tekst"] = tr(self.coordinator.language, attributes["tekst"])
        return attributes


class ExpectedGainSensor(ChargePlanEntity, SensorEntity):
    """Geschatte opbrengst van de huidige plannen (bijladen plus verkoop)."""

    _attr_native_unit_of_measurement = "€"
    _attr_suggested_display_precision = 2
    _attr_icon = "mdi:cash-plus"

    def __init__(self, coordinator: ChargePlanCoordinator) -> None:
        super().__init__(coordinator, "verwachte_opbrengst")

    @property
    def native_value(self) -> float:
        return self.coordinator.expected_gain

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"regels": self.coordinator.flow.get("resultaat", {}).get("regels", [])}


class RealizedGainSensor(ChargePlanEntity, SensorEntity):
    """Gerealiseerde opbrengst van vandaag, deze/vorige week of deze maand (zie ledger.py)."""

    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_state_class = SensorStateClass.TOTAL
    _attr_native_unit_of_measurement = "EUR"
    _attr_suggested_display_precision = 2
    _attr_icon = "mdi:cash-check"

    def __init__(self, coordinator: ChargePlanCoordinator, key: str) -> None:
        super().__init__(coordinator, key)
        self._period = {
            "opbrengst_deze_week": "week",
            "opbrengst_vorige_week": "vorige_week",
            "opbrengst_deze_maand": "maand",
            "opbrengst_dit_jaar": "jaar",
        }.get(key, "dag")
        self._week = self._period != "dag"
        if self._period == "vorige_week":
            # Een vast eindbedrag, geen lopende teller.
            self._attr_state_class = None

    @property
    def native_value(self) -> float | None:
        ledger = self.coordinator.ledger
        if self._period == "vorige_week":
            return None if ledger.prev_week_gain is None else round(ledger.prev_week_gain, 2)
        value = {"week": ledger.week_gain, "maand": ledger.month_gain, "jaar": ledger.year_gain}.get(self._period, ledger.day_gain)
        return round(value, 2)

    @property
    def last_reset(self) -> datetime | None:
        if self._period == "vorige_week":
            return None
        ledger = self.coordinator.ledger
        start = {"week": ledger.week_start, "maand": ledger.month_start, "jaar": ledger.year_start}.get(self._period, ledger.day_start)
        return dt_util.parse_datetime(start) if start else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        ledger = self.coordinator.ledger
        attributes: dict[str, Any] = {
            "voorraad_kwh": round(ledger.stock_kwh, 2),
            "voorraad_kostprijs": round(ledger.stock_price, 3) if ledger.stock_price is not None else None,
        }
        if self._period == "dag":
            attributes.update(
                {
                    "bijgeladen_kwh": round(ledger.day_charged_kwh, 2),
                    "laadkosten": round(ledger.day_charge_cost, 2),
                    "gebruikt_kwh": round(ledger.day_used_kwh, 2),
                    "verkocht_kwh": round(ledger.day_sold_kwh, 2),
                    "afschrijving": round(ledger.day_depreciation, 2),
                }
            )
        return attributes


class EfficiencySensor(ChargePlanEntity, SensorEntity):
    """Het rendement (laden en weer ontladen) waarmee de integratie rekent."""

    _attr_native_unit_of_measurement = "%"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 1
    _attr_icon = "mdi:battery-sync"

    def __init__(self, coordinator: ChargePlanCoordinator) -> None:
        super().__init__(coordinator, "rendement")

    @property
    def native_value(self) -> float | None:
        efficiency = self.coordinator.inputs.get("efficiency")
        return round(efficiency * 100, 1) if efficiency else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        inputs = self.coordinator.inputs
        efficiency = inputs.get("efficiency")
        return {
            "bron": "gemeten uit de energietellers" if inputs.get("efficiency_measured") else "vaste waarde uit de instellingen",
            "totaal_geladen_kwh": inputs.get("charged_total"),
            "totaal_ontladen_kwh": inputs.get("discharged_total"),
            "laden_of_ontladen_apart": round(one_way_efficiency(efficiency) * 100, 1) if efficiency else None,
        }

