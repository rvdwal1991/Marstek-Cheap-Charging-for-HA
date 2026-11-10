"""Leest de invoer, berekent het laadplan en stuurt de Marstek aan."""

from __future__ import annotations

from datetime import datetime, timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .const import (
    COMMAND_SETTLE_SECONDS,
    CONF_CAPACITY_ENTITY,
    CONF_CAPACITY_KWH,
    CONF_CHARGED_ENERGY_ENTITY,
    CONF_CONTROL_MODE_ENTITY,
    CONF_DEFAULT_EFFICIENCY,
    CONF_DISCHARGED_ENERGY_ENTITY,
    CONF_FORCE_DISCHARGE_POWER_ENTITY,
    CONF_FORCE_MODE_ENTITY,
    CONF_FORCE_POWER_ENTITY,
    CONF_HOUSE_POWER,
    CONF_LOOKAHEAD_HOURS,
    CONF_MARGIN,
    CONF_MAX_DISCHARGE_POWER_ENTITY,
    CONF_MAX_POWER_ENTITY,
    CONF_MIN_LOOKAHEAD_HOURS,
    CONF_MIN_POWER,
    CONF_MIN_SOC,
    CONF_MIN_SOC_ENTITY,
    CONF_PRICE_ATTRIBUTE,
    CONF_PRICE_ENTITY,
    CONF_RESERVE_MIN_SOC,
    CONF_SELL_MARGIN,
    CONF_SELL_PRICE_FACTOR,
    CONF_SELL_PRICE_OFFSET,
    CONF_SOC_ENTITY,
    CONF_TOP_HOURS,
    DEFAULT_CAPACITY_KWH,
    DEFAULT_EFFICIENCY,
    DEFAULT_HOUSE_POWER,
    DEFAULT_LOOKAHEAD_HOURS,
    DEFAULT_MARGIN,
    DEFAULT_MAX_POWER,
    DEFAULT_MIN_LOOKAHEAD_HOURS,
    DEFAULT_MIN_POWER,
    DEFAULT_MIN_SOC,
    DEFAULT_PRICE_ATTRIBUTE,
    DEFAULT_RESERVE_MIN_SOC,
    DEFAULT_SELL_MARGIN,
    DEFAULT_SELL_PRICE_FACTOR,
    DEFAULT_SELL_PRICE_OFFSET,
    DEFAULT_TOP_HOURS,
    DOMAIN,
    FORCE_CHARGE,
    FORCE_DISCHARGE,
    FORCE_STOP,
    MODE_DISABLE,
    MODE_ENABLE,
    UPDATE_INTERVAL_SECONDS,
)
from .planner import (
    SELL_SELLING,
    STATUS_CHARGING,
    Plan,
    PlanMemory,
    PlanParams,
    PriceSlot,
    SellParams,
    SellPlan,
    clamp_efficiency,
    compute_plan,
    compute_sell_plan,
)

_LOGGER = logging.getLogger(__name__)

STORAGE_VERSION = 1


def parse_prices(raw: Any) -> list[PriceSlot]:
    """Maak prijsvakken van het forecast-attribuut van de prijssensor.

    Ondersteund:
    - Zonneplan (uurprijzen): start_date, end_date, price_tax_included.amount (x 1e-7)
    - Zonneplan (oud):        datetime, electricity_price (x 1e-7)
    - Algemeen:               start | start_time | datetime  en  price | value | prijs
    """
    slots: list[PriceSlot] = []
    if not isinstance(raw, list):
        return slots
    for row in raw:
        if not isinstance(row, dict):
            continue
        start_raw = (
            row.get("start_date") or row.get("start") or row.get("start_time") or row.get("datetime")
        )
        start = dt_util.parse_datetime(str(start_raw)) if start_raw else None
        if start is None:
            continue
        if start.tzinfo is None:
            start = start.replace(tzinfo=dt_util.DEFAULT_TIME_ZONE)

        price: float | None = None
        included = row.get("price_tax_included")
        if isinstance(included, dict) and included.get("amount") is not None:
            price = float(included["amount"]) / 1e7
        elif row.get("electricity_price") is not None:
            price = float(row["electricity_price"]) / 1e7
        else:
            for key in ("price", "value", "prijs"):
                if row.get(key) is not None:
                    price = float(row[key])
                    break
        if price is None:
            continue

        seconds = 3600.0
        end_raw = row.get("end_date") or row.get("end") or row.get("end_time")
        end = dt_util.parse_datetime(str(end_raw)) if end_raw else None
        if end is not None:
            if end.tzinfo is None:
                end = end.replace(tzinfo=dt_util.DEFAULT_TIME_ZONE)
            if end > start:
                seconds = (end - start).total_seconds()
        slots.append(PriceSlot(start, price, seconds))
    slots.sort(key=lambda slot: slot.start)
    return slots


class ChargePlanCoordinator(DataUpdateCoordinator[Plan]):
    """Berekent elke minuut het laadplan en voert het uit als de sturing aan staat."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            config_entry=entry,
            update_interval=timedelta(seconds=UPDATE_INTERVAL_SECONDS),
        )
        self.conf: dict[str, Any] = {**entry.data, **entry.options}
        self.enabled = False
        self.sell_enabled = False
        self.sell_plan = SellPlan()
        # Waar als de integratie zelf een verkoop (forceer-ontladen) heeft gestart.
        self._selling = False
        self._sell_hours: tuple[datetime, ...] = ()
        self.inputs: dict[str, Any] = {}
        self.last_command: str | None = None
        self._memory = PlanMemory()
        self._store: Store[dict[str, Any]] = Store(
            hass, STORAGE_VERSION, f"{DOMAIN}.{entry.entry_id}"
        )
        self._settle_until: datetime | None = None

    # ------------------------------------------------------------------ opslag

    async def async_load(self) -> None:
        """Lees de bewaarde toestand (sturing aan/uit en het vorige plan)."""
        data = await self._store.async_load() or {}
        self.enabled = bool(data.get("enabled", False))
        self.sell_enabled = bool(data.get("sell_enabled", False))
        self._selling = bool(data.get("selling", False))

        def moment(value: Any) -> datetime | None:
            return dt_util.parse_datetime(value) if isinstance(value, str) else None

        hours = tuple(h for h in (moment(v) for v in data.get("charge_hours", [])) if h)
        self._sell_hours = tuple(
            h for h in (moment(v) for v in data.get("sell_hours", [])) if h
        )
        self._memory = PlanMemory(
            status=data.get("status", PlanMemory().status),
            charge_hours=hours,
            window_end=moment(data.get("window_end")),
            done_until=moment(data.get("done_until")),
        )

    def _save(self) -> None:
        memory = self._memory
        self._store.async_delay_save(
            lambda: {
                "enabled": self.enabled,
                "sell_enabled": self.sell_enabled,
                "selling": self._selling,
                "sell_hours": [h.isoformat() for h in self._sell_hours],
                "status": memory.status,
                "charge_hours": [h.isoformat() for h in memory.charge_hours],
                "window_end": memory.window_end.isoformat() if memory.window_end else None,
                "done_until": memory.done_until.isoformat() if memory.done_until else None,
            },
            5,
        )

    # ----------------------------------------------------------------- invoer

    def _state(self, key: str) -> str | None:
        entity_id = self.conf.get(key)
        if not entity_id:
            return None
        state = self.hass.states.get(entity_id)
        if state is None or state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN, ""):
            return None
        return state.state

    def _number(self, key: str) -> float | None:
        value = self._state(key)
        if value is None:
            return None
        try:
            return float(value)
        except ValueError:
            return None

    def _read_inputs(self) -> dict[str, Any]:
        price_state = self.hass.states.get(self.conf.get(CONF_PRICE_ENTITY, ""))
        attribute = self.conf.get(CONF_PRICE_ATTRIBUTE) or DEFAULT_PRICE_ATTRIBUTE
        prices = parse_prices(price_state.attributes.get(attribute) if price_state else None)
        control = self._state(CONF_CONTROL_MODE_ENTITY)
        force = self._state(CONF_FORCE_MODE_ENTITY)
        return {
            "prices": prices,
            "soc": self._number(CONF_SOC_ENTITY),
            "capacity_kwh": self._number(CONF_CAPACITY_ENTITY)
            or float(self.conf.get(CONF_CAPACITY_KWH, DEFAULT_CAPACITY_KWH)),
            "max_power_w": self._number(CONF_MAX_POWER_ENTITY) or DEFAULT_MAX_POWER,
            "force_power_w": self._number(CONF_FORCE_POWER_ENTITY),
            "max_discharge_power_w": self._number(CONF_MAX_DISCHARGE_POWER_ENTITY)
            or DEFAULT_MAX_POWER,
            "force_discharge_power_w": self._number(CONF_FORCE_DISCHARGE_POWER_ENTITY),
            "min_soc": self._number(CONF_MIN_SOC_ENTITY)
            or float(self.conf.get(CONF_MIN_SOC, DEFAULT_MIN_SOC)),
            "efficiency": clamp_efficiency(
                self._number(CONF_CHARGED_ENERGY_ENTITY),
                self._number(CONF_DISCHARGED_ENERGY_ENTITY),
                float(self.conf.get(CONF_DEFAULT_EFFICIENCY, DEFAULT_EFFICIENCY)),
            ),
            "control_mode": control,
            "force_mode": force,
            "charging": control == MODE_ENABLE and force == FORCE_CHARGE,
        }

    @property
    def params(self) -> PlanParams:
        conf = self.conf
        return PlanParams(
            top_hours=int(conf.get(CONF_TOP_HOURS, DEFAULT_TOP_HOURS)),
            lookahead_hours=int(conf.get(CONF_LOOKAHEAD_HOURS, DEFAULT_LOOKAHEAD_HOURS)),
            min_lookahead_hours=int(conf.get(CONF_MIN_LOOKAHEAD_HOURS, DEFAULT_MIN_LOOKAHEAD_HOURS)),
            margin=float(conf.get(CONF_MARGIN, DEFAULT_MARGIN)),
            min_power_w=int(conf.get(CONF_MIN_POWER, DEFAULT_MIN_POWER)),
        )

    @property
    def sell_params(self) -> SellParams:
        conf = self.conf
        return SellParams(
            margin=float(conf.get(CONF_SELL_MARGIN, DEFAULT_SELL_MARGIN)),
            house_power_w=float(conf.get(CONF_HOUSE_POWER, DEFAULT_HOUSE_POWER)),
            reserve_min_soc=float(conf.get(CONF_RESERVE_MIN_SOC, DEFAULT_RESERVE_MIN_SOC)),
            price_factor=float(conf.get(CONF_SELL_PRICE_FACTOR, DEFAULT_SELL_PRICE_FACTOR)),
            price_offset=float(conf.get(CONF_SELL_PRICE_OFFSET, DEFAULT_SELL_PRICE_OFFSET)),
            min_power_w=int(conf.get(CONF_MIN_POWER, DEFAULT_MIN_POWER)),
        )

    @property
    def can_sell(self) -> bool:
        """Verkopen kan alleen als de entiteit voor het ontlaadvermogen is ingesteld."""
        return bool(self.conf.get(CONF_FORCE_DISCHARGE_POWER_ENTITY))

    # ------------------------------------------------------------------ update

    async def _async_update_data(self) -> Plan:
        inputs = self._read_inputs()
        self.inputs = inputs
        plan = compute_plan(
            prices=inputs["prices"],
            now=dt_util.utcnow(),
            soc=inputs["soc"],
            capacity_kwh=inputs["capacity_kwh"],
            max_power_w=inputs["max_power_w"],
            efficiency=inputs["efficiency"],
            charging=inputs["charging"],
            active=self.enabled,
            memory=self._memory,
            params=self.params,
            tz=dt_util.DEFAULT_TIME_ZONE,
        )
        if plan.memory() != self._memory:
            self._memory = plan.memory()
            self._save()

        now = dt_util.utcnow()
        if not self.can_sell:
            sell = SellPlan(text="Verkopen is niet ingesteld: kies de entiteit voor het ontlaadvermogen")
        else:
            sell = compute_sell_plan(
                charge_plan=plan,
                now=now,
                soc=inputs["soc"],
                capacity_kwh=inputs["capacity_kwh"],
                max_power_w=inputs["max_discharge_power_w"],
                efficiency=inputs["efficiency"],
                min_soc=inputs["min_soc"],
                selling=self._selling,
                previous_hours=self._sell_hours,
                params=self.sell_params,
                tz=dt_util.DEFAULT_TIME_ZONE,
            )
        self.sell_plan = sell
        if sell.sell_hours != self._sell_hours:
            self._sell_hours = sell.sell_hours
            self._save()

        if self.enabled or self.sell_enabled or self._selling:
            await self._async_apply(plan, sell, inputs)
        return plan

    @callback
    def async_start_listening(self) -> None:
        """Reken direct opnieuw als de prijzen, de SoC of de Marstek veranderen."""
        keys = (
            CONF_PRICE_ENTITY,
            CONF_SOC_ENTITY,
            CONF_CONTROL_MODE_ENTITY,
            CONF_FORCE_MODE_ENTITY,
            CONF_MAX_POWER_ENTITY,
        )
        entities = [self.conf[key] for key in keys if self.conf.get(key)]

        @callback
        def _changed(event: Event) -> None:
            self.hass.async_create_task(self.async_request_refresh())

        self.config_entry.async_on_unload(
            async_track_state_change_event(self.hass, entities, _changed)
        )

    # ----------------------------------------------------------------- sturing

    async def _async_select(self, key: str, option: str) -> None:
        await self.hass.services.async_call(
            "select",
            "select_option",
            {"entity_id": self.conf[key], "option": option},
            blocking=True,
        )

    async def _async_set_number(self, key: str, watts: float) -> None:
        await self.hass.services.async_call(
            "number",
            "set_value",
            {"entity_id": self.conf[key], "value": int(watts)},
            blocking=True,
        )

    def _settle(self, command: str) -> None:
        self.last_command = f"{dt_util.now().isoformat(timespec='seconds')} {command}"
        self._settle_until = dt_util.utcnow() + timedelta(seconds=COMMAND_SETTLE_SECONDS)
        _LOGGER.info("Marstek: %s", command)

    def _set_selling(self, selling: bool) -> None:
        if self._selling != selling:
            self._selling = selling
            self._save()

    async def _async_apply(self, plan: Plan, sell: SellPlan, inputs: dict[str, Any]) -> None:
        """Breng de Marstek in de toestand die bij de plannen hoort."""
        control, force = inputs["control_mode"], inputs["force_mode"]
        if control is None or force is None:
            return  # Marstek niet bereikbaar: niets sturen.
        if self._settle_until is not None and dt_util.utcnow() < self._settle_until:
            return
        if control == MODE_ENABLE and force == FORCE_DISCHARGE and not self._selling:
            return  # Handmatig forceer-ontladen laten we met rust.

        want_charge = self.enabled and plan.status == STATUS_CHARGING and bool(plan.power_w)
        want_sell = (
            not want_charge
            and self.sell_enabled
            and self.can_sell
            and sell.status == SELL_SELLING
            and bool(sell.power_w)
        )

        try:
            if want_charge:
                current = inputs["force_power_w"]
                if current is None or abs(current - plan.power_w) >= 50:
                    await self._async_set_number(CONF_FORCE_POWER_ENTITY, plan.power_w)
                    self._settle(f"laadvermogen {plan.power_w} W")
                if not inputs["charging"]:
                    await self._async_select(CONF_FORCE_MODE_ENTITY, FORCE_CHARGE)
                    await self._async_select(CONF_CONTROL_MODE_ENTITY, MODE_ENABLE)
                    self._set_selling(False)
                    self._settle(f"bijladen gestart op {plan.power_w} W")
            elif want_sell:
                current = inputs["force_discharge_power_w"]
                if current is None or abs(current - sell.power_w) >= 50:
                    await self._async_set_number(CONF_FORCE_DISCHARGE_POWER_ENTITY, sell.power_w)
                    self._settle(f"verkoopvermogen {sell.power_w} W")
                if not (self._selling and control == MODE_ENABLE and force == FORCE_DISCHARGE):
                    await self._async_select(CONF_FORCE_MODE_ENTITY, FORCE_DISCHARGE)
                    await self._async_select(CONF_CONTROL_MODE_ENTITY, MODE_ENABLE)
                    self._set_selling(True)
                    self._settle(f"verkopen gestart op {sell.power_w} W")
            elif self._selling:
                await self._async_release(inputs)
                self._settle("verkopen gestopt, terug naar anti-feed")
            elif control == MODE_ENABLE and (self.enabled or force == FORCE_STOP):
                # Forceer-laden dat niet bij het plan hoort alleen terugzetten als
                # de prijssturing aan staat.
                await self._async_release(inputs)
                self._settle("bijladen gestopt, terug naar anti-feed")
            elif force == FORCE_STOP:
                # Rusttoestand herstellen: RS485 uit met forceren op charge, zodat
                # handmatig forceer-laden werkt zoals de gebruiker gewend is.
                await self._async_select(CONF_FORCE_MODE_ENTITY, FORCE_CHARGE)
                self._settle("forceren terug op charge (rusttoestand)")
        except Exception:  # noqa: BLE001 - een mislukte opdracht mag de berekening niet stoppen
            _LOGGER.exception("Aansturen van de Marstek mislukt")

    async def _async_release(self, inputs: dict[str, Any]) -> None:
        """Zet de Marstek terug in zijn rusttoestand: RS485 uit, anti-feed."""
        await self._async_select(CONF_CONTROL_MODE_ENTITY, MODE_DISABLE)
        # Altijd sturen, ook als Home Assistant al 'charge' toont: de toestand
        # van de selects loopt achter op de Marstek.
        await self._async_select(CONF_FORCE_MODE_ENTITY, FORCE_CHARGE)
        current = inputs["force_power_w"]
        if current is None or abs(current - inputs["max_power_w"]) >= 1:
            await self._async_set_number(CONF_FORCE_POWER_ENTITY, inputs["max_power_w"])
        if self.can_sell:
            current = inputs["force_discharge_power_w"]
            if current is None or abs(current - inputs["max_discharge_power_w"]) >= 1:
                await self._async_set_number(
                    CONF_FORCE_DISCHARGE_POWER_ENTITY, inputs["max_discharge_power_w"]
                )
        self._set_selling(False)

    async def async_set_enabled(self, enabled: bool) -> None:
        """Zet de prijssturing aan of uit."""
        self.enabled = enabled
        self._save()
        self._settle_until = None
        if not enabled:
            inputs = self._read_inputs()
            control, force = inputs["control_mode"], inputs["force_mode"]
            if control == MODE_ENABLE and force in (FORCE_CHARGE, FORCE_STOP):
                try:
                    await self._async_release(inputs)
                    self._settle("prijssturing uit, terug naar anti-feed")
                except Exception:  # noqa: BLE001
                    _LOGGER.exception("Terugzetten van de Marstek mislukt")
        await self.async_refresh()

    async def async_set_sell_enabled(self, enabled: bool) -> None:
        """Zet het verkopen aan of uit."""
        self.sell_enabled = enabled
        self._save()
        self._settle_until = None
        if not enabled and self._selling:
            try:
                await self._async_release(self._read_inputs())
                self._settle("verkoop uit, terug naar anti-feed")
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Terugzetten van de Marstek mislukt")
        await self.async_refresh()
