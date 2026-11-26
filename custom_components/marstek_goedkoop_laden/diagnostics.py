"""Diagnostiek: de invoer en het plan zoals de integratie ze nu ziet."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .coordinator import ChargePlanCoordinator


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Geef de diagnostiek van deze config entry."""
    coordinator: ChargePlanCoordinator = entry.runtime_data
    plan = coordinator.data
    inputs = dict(coordinator.inputs)
    prices = inputs.pop("prices", [])
    return {
        "instellingen": coordinator.conf,
        "prijssturing_aan": coordinator.enabled,
        "verkoop_aan": coordinator.sell_enabled,
        "negatieve_prijs_aan": coordinator.negative_enabled,
        "boekhouding": coordinator.ledger.to_dict(),
        "vasthouden_aan": coordinator.hold_enabled,
        "geen_verlies_aan": coordinator.no_loss_enabled,
        "vasthouden_actief": coordinator.hold_active,
        "negatieve_prijs_actief": coordinator.negative_active,
        "verkoopplan": {
            "status": coordinator.sell_plan.status,
            "verkoopuren": [h.isoformat() for h in coordinator.sell_plan.sell_hours],
            "vermogen_w": coordinator.sell_plan.power_w,
            "overschot_kwh": coordinator.sell_plan.energy_kwh,
            "reserve_soc": coordinator.sell_plan.reserve_soc,
            "drempelprijs": coordinator.sell_plan.threshold,
            "terugkoopprijs": coordinator.sell_plan.refill_price,
            "tekst": coordinator.sell_plan.text,
        },
        "zonneverwachting": {
            "uren": len(coordinator._solar_hours),
            "totaal_kwh": round(sum(wh for _, wh in coordinator._solar_hours) / 1000.0, 1),
            "gebruikt_overschot_kwh": plan.solar_kwh,
            "betrouwbaarheid": coordinator.solar_factor,
            "geleerd": coordinator.calibration.factor(),
            "dagen_geleerd": len(coordinator.calibration.ratios),
            "verhoudingen": coordinator.calibration.ratios,
            "teller": list(coordinator._solar_counters),
        },
        "huisverbruik": {
            "sensor": coordinator.conf.get("house_power_entity"),
            "uren_geleerd": coordinator.house.learned(),
            "profiel_w": coordinator.house.to_dict()["watts"],
        },
        "laatste_opdracht": coordinator.last_command,
        "invoer": inputs,
        "prijzen": [
            {"start": slot.start.isoformat(), "prijs": slot.price, "seconden": slot.seconds}
            for slot in prices
        ],
        "plan": {
            "status": plan.status,
            "laaduren": [h.isoformat() for h in plan.charge_hours],
            "venster": [h.isoformat() for h in plan.window],
            "einde_venster": plan.window_end.isoformat() if plan.window_end else None,
            "uren_nodig": plan.hours_needed,
            "vermogen_w": plan.power_w,
            "energie_kwh": plan.energy_kwh,
            "gemiddelde_prijs": plan.average_price,
            "klaar_tot": plan.done_until.isoformat() if plan.done_until else None,
            "tekst": plan.text,
        },
    }
