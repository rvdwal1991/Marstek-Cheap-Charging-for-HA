"""De zonneverwachting uit het Energie-dashboard van Home Assistant.

Dat dashboard kent de verwachting van Forecast.Solar, Solcast, Open-Meteo en andere
integraties, dus er is niets extra in te stellen. De functies van Home Assistant zelf
worden pas hier geimporteerd, zodat een ontbrekend of veranderd Energie-onderdeel de
integratie niet stukmaakt: dan is er gewoon geen verwachting.
"""
from __future__ import annotations

from datetime import datetime

from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util


async def async_read_forecast(
    hass: HomeAssistant,
) -> tuple[tuple[tuple[datetime, float], ...], tuple[str, ...]]:
    """Geef ((uurbegin, Wh), ...) en de tellers (entity_id's) van de zonnepanelen uit het Energie-dashboard.

    De tellers dienen om te leren hoeveel van de verwachting er echt wordt gehaald.
    """
    from homeassistant.components.energy import async_get_manager
    from homeassistant.components.energy.websocket_api import async_get_energy_platforms

    manager = await async_get_manager(hass)
    entry_ids: set[str] = set()
    counters: list[str] = []
    for source in (manager.data or {}).get("energy_sources", []):
        if source.get("type") == "solar":
            entry_ids.update(source.get("config_entry_solar_forecast") or [])
            if source.get("stat_energy_from"):
                counters.append(source["stat_energy_from"])
    platforms = await async_get_energy_platforms(hass) if entry_ids else {}
    per_hour: dict[datetime, float] = {}
    for entry_id in entry_ids:
        entry = hass.config_entries.async_get_entry(entry_id)
        if entry is None or entry.domain not in platforms:
            continue
        forecast = await platforms[entry.domain](hass, entry_id)
        for stamp, wh in ((forecast or {}).get("wh_hours") or {}).items():
            moment = dt_util.parse_datetime(stamp)
            if moment is None:
                continue
            # Een halfuursperiode telt op bij het uur waar ze in valt.
            hour = moment.replace(minute=0, second=0, microsecond=0)
            per_hour[hour] = per_hour.get(hour, 0.0) + float(wh)
    return tuple(sorted(per_hour.items())), tuple(counters)
