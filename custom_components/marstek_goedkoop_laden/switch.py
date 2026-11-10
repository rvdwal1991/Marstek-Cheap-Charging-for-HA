"""Schakelaar: prijssturing aan of uit."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import ChargePlanCoordinator
from .entity import ChargePlanEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Maak de schakelaar aan."""
    async_add_entities([PriceControlSwitch(entry.runtime_data)])


class PriceControlSwitch(ChargePlanEntity, SwitchEntity):
    """Aan: het laadplan wordt uitgevoerd. Uit: de Marstek regelt alles zelf."""

    def __init__(self, coordinator: ChargePlanCoordinator) -> None:
        super().__init__(coordinator, "prijssturing")

    @property
    def is_on(self) -> bool:
        return self.coordinator.enabled

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"laatste_opdracht": self.coordinator.last_command}

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_enabled(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_enabled(False)
