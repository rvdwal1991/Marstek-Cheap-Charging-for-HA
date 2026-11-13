"""Marstek Goedkoop Laden: laad de thuisbatterij bij in de goedkoopste uren."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import ChargePlanCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.SWITCH]

CARD_FILE = "marstek-goedkoop-laden-card.js"
CARD_URL = f"/{DOMAIN}/{CARD_FILE}"


async def _async_register_card(hass: HomeAssistant) -> None:
    """Maak de dashboardkaart beschikbaar, zonder dat er een resource nodig is."""
    if hass.data.get(f"{DOMAIN}_card"):
        return
    hass.data[f"{DOMAIN}_card"] = True

    from pathlib import Path

    from homeassistant.components.frontend import add_extra_js_url
    from homeassistant.components.http import StaticPathConfig
    from homeassistant.loader import async_get_integration

    path = Path(__file__).parent / "frontend" / CARD_FILE
    await hass.http.async_register_static_paths(
        [StaticPathConfig(CARD_URL, str(path), cache_headers=False)]
    )
    integration = await async_get_integration(hass, DOMAIN)
    add_extra_js_url(hass, f"{CARD_URL}?v={integration.version}")


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Zet de integratie op vanuit een config entry."""
    await _async_register_card(hass)
    coordinator = ChargePlanCoordinator(hass, entry)
    await coordinator.async_load()
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    coordinator.async_start_listening()
    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Ruim de integratie op.

    De Marstek wordt hier bewust niet omgezet: bij een herstart van Home
    Assistant moet een lopende laadbeurt gewoon doorlopen.
    """
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Herlaad na een wijziging van de instellingen."""
    await hass.config_entries.async_reload(entry.entry_id)
