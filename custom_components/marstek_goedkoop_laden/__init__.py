"""Marstek Goedkoop Laden: laad de thuisbatterij bij in de goedkoopste uren."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .coordinator import ChargePlanCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.SWITCH]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Zet de integratie op vanuit een config entry."""
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
