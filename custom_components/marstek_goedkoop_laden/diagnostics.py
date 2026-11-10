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
