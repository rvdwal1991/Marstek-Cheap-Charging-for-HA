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
    coordinator: ChargePlanCoordinator = entry.runtime_data
    async_add_entities(
        [PriceControlSwitch(coordinator), SellSwitch(coordinator), NegativePriceSwitch(coordinator)]
    )


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


class SellSwitch(ChargePlanEntity, SwitchEntity):
    """Aan: overschot wordt in de duurste uren aan het net verkocht."""

    def __init__(self, coordinator: ChargePlanCoordinator) -> None:
        super().__init__(coordinator, "verkoop")

    @property
    def is_on(self) -> bool:
        return self.coordinator.sell_enabled

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"laatste_opdracht": self.coordinator.last_command}

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_sell_enabled(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_sell_enabled(False)


class NegativePriceSwitch(ChargePlanEntity, SwitchEntity):
    """Aan (standaard): bij een negatieve prijs altijd laden op vol vermogen."""

    def __init__(self, coordinator: ChargePlanCoordinator) -> None:
        super().__init__(coordinator, "negatieve_prijs")

    @property
    def is_on(self) -> bool:
        return self.coordinator.negative_enabled

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"nu_actief": self.coordinator.negative_active}

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_negative_enabled(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_negative_enabled(False)

