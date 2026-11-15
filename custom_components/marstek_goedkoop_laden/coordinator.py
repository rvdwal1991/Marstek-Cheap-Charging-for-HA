"""Leest de invoer, berekent het laadplan en stuurt de Marstek aan."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.event import async_track_state_change_event, async_track_time_change
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
    CONF_NEGATIVE_PRICE_LIMIT,
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
    DEFAULT_NEGATIVE_PRICE_LIMIT,
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
from .i18n import tr
from .ledger import Ledger
from .planner import (
    FULL_SOC,
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
    negative_price_slot,
    step,
)

_LOGGER = logging.getLogger(__name__)

# Onder deze voorraad (kWh) wordt er niet vastgehouden.
HOLD_MIN_STOCK_KWH = 0.1

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
        # Laden op vol vermogen bij een negatieve prijs: staat standaard aan.
        self.negative_enabled = True
        self.negative_active = False
        # Waar als de integratie zelf zo'n laadbeurt heeft gestart.
        self._negative_charging = False
        # Waar als de integratie zelf een verkoop (forceer-ontladen) heeft gestart.
        self._selling = False
        # Het forceer-ontlaadvermogen van voor de verkoop, om na afloop terug te zetten.
        self._discharge_power_before: float | None = None
        self._sell_hours: tuple[datetime, ...] = ()
        self.inputs: dict[str, Any] = {}
        # Tijdlijn en controles voor de dashboardkaart.
        self.flow: dict[str, Any] = {"tijdlijn": [], "banen": []}
        # Verwachte opbrengst van de huidige plannen, in euro (schatting).
        self.expected_gain: float = 0.0
        # Boekhouding van de gerealiseerde opbrengst (vandaag en deze week).
        self.ledger = Ledger()
        # Vasthouden: niet ontladen zolang de prijs onder de kostprijs van de
        # bijgeladen voorraad ligt. Staat standaard aan.
        self.hold_enabled = True
        self.hold_active = False
        # Geen verlies: dwingt het vasthouden af (ook als die schakelaar uit staat)
        # en verkoopt bijgeladen voorraad nooit onder de kostprijs.
        self.no_loss_enabled = False
        self.sell_blocked = False
        self.hold_until: datetime | None = None
        # Waar als de integratie zelf het maximale ontlaadvermogen op 0 heeft gezet,
        # met de waarde die er daarvoor stond (of die een ander er intussen in zette).
        self._holding = False
        self._discharge_limit_before: float | None = None
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
        self.negative_enabled = bool(data.get("negative_enabled", True))
        self._negative_charging = bool(data.get("negative_charging", False))
        self._selling = bool(data.get("selling", False))
        self._discharge_power_before = data.get("discharge_power_before")
        self.ledger = Ledger.from_dict(data.get("ledger"))
        self.hold_enabled = bool(data.get("hold_enabled", True))
        self.no_loss_enabled = bool(data.get("no_loss_enabled", False))
        self._holding = bool(data.get("holding", False))
        self._discharge_limit_before = data.get("discharge_limit_before")

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
                "negative_enabled": self.negative_enabled,
                "negative_charging": self._negative_charging,
                "selling": self._selling,
                "discharge_power_before": self._discharge_power_before,
                "ledger": self.ledger.to_dict(),
                "hold_enabled": self.hold_enabled,
                "no_loss_enabled": self.no_loss_enabled,
                "holding": self._holding,
                "discharge_limit_before": self._discharge_limit_before,
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
            "charged_total": self._number(CONF_CHARGED_ENERGY_ENTITY),
            "discharged_total": self._number(CONF_DISCHARGED_ENERGY_ENTITY),
            "max_discharge_raw": self._number(CONF_MAX_DISCHARGE_POWER_ENTITY),
            # Tijdens vasthouden staat het ontlaadvermogen op 0; reken dan met
            # de waarde van daarvoor.
            "max_discharge_power_w": (self._discharge_limit_before if self._holding else None)
            or self._number(CONF_MAX_DISCHARGE_POWER_ENTITY)
            or DEFAULT_MAX_POWER,
            "force_discharge_power_w": self._number(CONF_FORCE_DISCHARGE_POWER_ENTITY),
            "min_soc": self._number(CONF_MIN_SOC_ENTITY)
            or float(self.conf.get(CONF_MIN_SOC, DEFAULT_MIN_SOC)),
            "efficiency_measured": bool(
                self._number(CONF_CHARGED_ENERGY_ENTITY) and self._number(CONF_DISCHARGED_ENERGY_ENTITY)
            ),
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
    def hold_on(self) -> bool:
        """Vasthouden geldt als zijn eigen schakelaar aan staat of 'geen verlies' aan staat."""
        return self.hold_enabled or self.no_loss_enabled

    @property
    def can_hold(self) -> bool:
        """Vasthouden kan alleen als het maximale ontlaadvermogen is ingesteld."""
        return bool(self.conf.get(CONF_MAX_DISCHARGE_POWER_ENTITY))

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

        # Negatieve prijs: nu laden op vol vermogen, los van het plan.
        limit = float(self.conf.get(CONF_NEGATIVE_PRICE_LIMIT, DEFAULT_NEGATIVE_PRICE_LIMIT))
        slot = negative_price_slot(plan.prices, now, limit)
        soc = inputs["soc"]
        self.negative_active = bool(
            self.negative_enabled and slot is not None and soc is not None and soc < FULL_SOC
        )

        # Gerealiseerde opbrengst bijwerken aan de hand van de energietellers.
        current = next((s for s in plan.prices if s.start <= now < s.end), None)
        price_now = current.price if current else None
        sell_params = self.sell_params
        if self.ledger.update(
            now=dt_util.now(),
            charged=inputs["charged_total"],
            discharged=inputs["discharged_total"],
            price=price_now,
            grid_charging=bool(
                inputs["charging"]
                and (
                    self.negative_active
                    or self._negative_charging
                    or (self.enabled and plan.status == STATUS_CHARGING)
                )
            ),
            selling=self._selling,
            export_price=(
                price_now * sell_params.price_factor - sell_params.price_offset
                if price_now is not None
                else None
            ),
            replacement_cost=(
                sell.refill_price / inputs["efficiency"] if sell.refill_price else None
            ),
            efficiency=inputs["efficiency"],
        ):
            self._save()

        # Vasthouden: is de accu leeg (en wordt er niet geladen), dan vervalt de
        # voorraad in de boeken.
        soc = inputs["soc"]
        if (
            soc is not None
            and soc <= inputs["min_soc"] + 1
            and not inputs["charging"]
            and self.ledger.clear_stock()
        ):
            self._save()
        cost = self.ledger.stock_price
        has_stock = self.ledger.stock_kwh >= HOLD_MIN_STOCK_KWH and cost is not None
        export_now = (
            price_now * sell_params.price_factor - sell_params.price_offset
            if price_now is not None
            else None
        )
        # Geen verlies: bijgeladen voorraad niet verkopen onder de kostprijs.
        self.sell_blocked = bool(
            self.no_loss_enabled and has_stock and export_now is not None and export_now < cost
        )
        selling_now = self._selling or (
            self.sell_enabled and sell.status == SELL_SELLING and not self.sell_blocked
        )
        self.hold_active = bool(
            self.hold_on
            and self.can_hold
            and self.ledger.stock_kwh >= HOLD_MIN_STOCK_KWH
            and cost is not None
            and price_now is not None
            and price_now < cost
            and not selling_now
        )
        self.hold_until = None
        if self.hold_active:
            self.hold_until = next(
                (s.start for s in plan.prices if s.start > now and s.price >= cost), None
            )
        await self._async_apply_hold(inputs)

        if (
            self.enabled
            or self.sell_enabled
            or self._selling
            or self.negative_active
            or self._negative_charging
        ):
            await self._async_apply(plan, sell, inputs)

        self.flow = tr(
            self.hass.config.language, self._build_flow(plan, sell, inputs, now, limit, slot)
        )

        if self.negative_active and slot is not None:
            # Alleen de weergave: het bewaarde plan blijft het echte laadplan.
            power = int(inputs["max_power_w"])
            price = f"{slot.price:.2f}".replace(".", ",")
            hours = tuple(sorted({slot.start, *plan.charge_hours}))
            return replace(
                plan,
                status=STATUS_CHARGING,
                charge_hours=hours,
                power_w=power,
                text=f"Negatieve prijs (€ {price}): laden op vol vermogen ({power} W)",
            )
        return plan

    # ---------------------------------------------------------- stroomschema

    def _switch_entity(self, key: str) -> str | None:
        """De entity_id van een van de eigen schakelaars (voor de schakelaarkaart)."""
        return er.async_get(self.hass).async_get_entity_id(
            "switch", DOMAIN, f"{self.config_entry.entry_id}_{key}"
        )

    def _build_flow(
        self,
        plan: Plan,
        sell: SellPlan,
        inputs: dict[str, Any],
        now: datetime,
        limit: float,
        negative_slot: PriceSlot | None,
    ) -> dict[str, Any]:
        """Tijdlijn en controles per onderdeel, voor de kaart op het dashboard."""

        def clock(moment: datetime) -> str:
            return dt_util.as_local(moment).strftime("%H:%M")

        def euro(value: float, digits: int = 2) -> str:
            return f"{value:.{digits}f}".replace(".", ",")

        def ranges(hours: tuple[datetime, ...]) -> list[tuple[datetime, datetime]]:
            result: list[tuple[datetime, datetime]] = []
            for start in sorted(hours):
                end = start + timedelta(hours=1)
                if result and result[-1][1] == start:
                    result[-1] = (result[-1][0], end)
                else:
                    result.append((start, end))
            return result

        cost = self.ledger.stock_price
        control, force = inputs["control_mode"], inputs["force_mode"]
        if self.negative_active:
            doing = "Laden op vol vermogen (negatieve prijs)"
        elif control == MODE_ENABLE and force == FORCE_CHARGE:
            doing = "Bijladen uit het net"
        elif control == MODE_ENABLE and force == FORCE_DISCHARGE:
            doing = "Verkopen aan het net" if self._selling else "Ontladen (handmatig)"
        elif control == MODE_ENABLE and force == FORCE_STOP:
            doing = "Stilgezet (handmatig)"
        elif control is None:
            doing = "Marstek niet bereikbaar"
        elif self.hold_active:
            doing = "Vasthouden: ontladen geblokkeerd"
        else:
            doing = "Zelf regelen (anti-feed)"

        events: list[tuple[datetime, datetime, dict]] = []
        for start, end in ranges(plan.charge_hours):
            if end <= now:
                continue
            if self.enabled:
                detail = f"Ca. {plan.power_w} W, {euro(plan.energy_kwh, 1)} kWh, gemiddeld € {euro(plan.average_price or 0)}"
                kind = "actie"
            else:
                detail = "Wordt niet uitgevoerd: bijladen staat uit"
                kind = "eind"
            events.append((start, end, step(f"{clock(start)} – {clock(end)} · bijladen", detail, kind)))
        for start, end in ranges(sell.sell_hours):
            if end <= now:
                continue
            if self.sell_enabled:
                detail = f"Ca. {sell.power_w} W, {euro(sell.energy_kwh, 1)} kWh, gemiddeld € {euro(sell.average_price or 0)}"
                kind = "actie"
            else:
                detail = "Wordt niet uitgevoerd: verkopen staat uit"
                kind = "eind"
            events.append((start, end, step(f"{clock(start)} – {clock(end)} · verkopen", detail, kind)))
        if self.hold_active and self.hold_until is not None and cost is not None:
            events.append(
                (
                    self.hold_until,
                    self.hold_until,
                    step(
                        f"{clock(self.hold_until)} · ontladen vrij",
                        f"Prijs komt boven de kostprijs van € {euro(cost)}",
                        "eind",
                    ),
                )
            )
        events.sort(key=lambda item: item[0])

        timeline = [step("Nu", doing, "nu")]
        timeline.extend(item[2] for item in events)
        # Na de laatste laad- of verkoopactie regelt de Marstek weer zelf. Het
        # vrijgeven van het ontladen is zelf al zo'n eindpunt.
        last = max(events, key=lambda item: item[1]) if events else None
        if last is None:
            timeline.append(step("Geen acties gepland", "De Marstek blijft zelf regelen", "eind"))
        elif last[0] != last[1]:
            timeline.append(step(f"{clock(last[1])} · klaar", "Weer zelf regelen (anti-feed)", "eind"))

        if negative_slot is not None:
            price_step = step("Prijs onder de grens", f"Nu € {euro(negative_slot.price)}", "ok")
            soc = inputs["soc"]
            if soc is not None and soc < FULL_SOC:
                negative_steps = [
                    price_step,
                    step("Accu niet vol", f"SoC {round(soc)} %", "ok"),
                    step("Laden op vol vermogen", f"{int(inputs['max_power_w'])} W", "actie"),
                ]
            else:
                negative_steps = [
                    price_step,
                    step("Accu is vol", "Niets te laden", "stop"),
                    step("Niet actief", "Stopt bij deze stap", "eind"),
                ]
        else:
            current = next((s for s in plan.prices if s.start <= now < s.end), None)
            detail = f"Nu € {euro(current.price)}" if current else "Prijs onbekend"
            negative_steps = [
                step(f"Prijs niet onder € {euro(limit)}", detail, "stop"),
                step("Niet actief", "Wacht op een negatief uur", "eind"),
            ]

        current_slot = next((s for s in plan.prices if s.start <= now < s.end), None)
        if not self.can_hold:
            hold_steps = [
                step("Niet ingesteld", "Kies de entiteit voor het maximale ontlaadvermogen", "stop"),
                step("Niet actief", "Stopt bij deze stap", "eind"),
            ]
        elif self.ledger.stock_kwh < HOLD_MIN_STOCK_KWH or cost is None:
            hold_steps = [
                step("Geen bijgeladen voorraad", "Niets om vast te houden", "stop"),
                step("Niet actief", "De Marstek regelt zelf", "eind"),
            ]
        else:
            stock_step = step(
                "Bijgeladen voorraad",
                f"{euro(self.ledger.stock_kwh, 1)} kWh, kostprijs € {euro(cost)}",
                "ok",
            )
            price_text = f"Nu € {euro(current_slot.price)}" if current_slot else "Prijs onbekend"
            if self.hold_active:
                until = f"Tot {clock(self.hold_until)}" if self.hold_until else f"Tot de prijs boven € {euro(cost)} komt"
                hold_steps = [
                    stock_step,
                    step("Prijs onder kostprijs", price_text, "ok"),
                    step("Ontladen geblokkeerd", until, "actie"),
                ]
            else:
                hold_steps = [
                    stock_step,
                    step("Prijs niet onder kostprijs", price_text, "stop"),
                    step("Ontladen vrij", "De voorraad wordt met winst gebruikt", "eind"),
                ]

        if self.no_loss_enabled:
            if self.ledger.stock_kwh >= HOLD_MIN_STOCK_KWH and cost is not None:
                guard = step(
                    "Voorraad bewaakt",
                    f"{euro(self.ledger.stock_kwh, 1)} kWh, alleen boven € {euro(cost)}",
                    "actie",
                )
            else:
                guard = step("Geen voorraad", "Nu niets te bewaken", "eind")
            no_loss_steps = [
                step("Ontladen boven kostprijs", "Vasthouden geldt altijd", "ok"),
                step("Verkopen boven kostprijs", "Nooit onder de kostprijs", "ok"),
                guard,
            ]
        else:
            no_loss_steps = []

        if self.can_sell:
            sell_steps = list(sell.steps)
            if self.sell_blocked and sell_steps and sell_steps[-1]["soort"] == "actie":
                sell_steps[-1] = step("Onder de kostprijs", f"Voorraad kost € {euro(cost or 0)}", "stop")
                sell_steps.append(step("Geen verkoop", "Tegengehouden door geen verlies", "eind"))
        else:
            sell_steps = [
                step("Verkopen ingesteld", "Kies de entiteit voor het ontlaadvermogen", "stop"),
                step("Geen verkoop", "Niet ingesteld", "eind"),
            ]

        def money(value: float) -> str:
            return f"€ {euro(abs(value))}"

        lines: list[dict[str, Any]] = []
        total = 0.0
        if not self.enabled:
            lines.append({"titel": "Bijladen", "bedrag": None, "detail": "Staat uit"})
        elif plan.gain_eur is not None and plan.charge_hours:
            total += plan.gain_eur
            lines.append(
                {
                    "titel": "Bijladen",
                    "bedrag": plan.gain_eur,
                    "detail": f"{euro(plan.energy_kwh, 1)} kWh inkopen voor {money(plan.cost_eur or 0)}, later {money(plan.value_eur or 0)} waard",
                }
            )
        else:
            lines.append({"titel": "Bijladen", "bedrag": 0.0, "detail": "Geen bijladen gepland"})
        if not self.sell_enabled:
            lines.append({"titel": "Verkoop", "bedrag": None, "detail": "Staat uit"})
        elif sell.gain_eur is not None and sell.sell_hours:
            total += sell.gain_eur
            lines.append(
                {
                    "titel": "Verkoop",
                    "bedrag": sell.gain_eur,
                    "detail": f"{euro(sell.energy_kwh, 1)} kWh verkopen voor {money(sell.revenue_eur or 0)}, terugladen kost {money(sell.refill_cost_eur or 0)}",
                }
            )
        else:
            lines.append({"titel": "Verkoop", "bedrag": 0.0, "detail": "Geen verkoop gepland"})
        self.expected_gain = round(total, 2)

        return {
            "tijdlijn": timeline,
            "resultaat": {
                "totaal": round(total, 2),
                "regels": lines,
                "vandaag": round(self.ledger.day_gain, 2),
                "week": round(self.ledger.week_gain, 2),
                "geladen_kwh": round(self.ledger.day_charged_kwh, 2),
                "laadkosten": round(self.ledger.day_charge_cost, 2),
                "gebruikt_kwh": round(self.ledger.day_used_kwh + self.ledger.day_sold_kwh, 2),
                "voorraad_kwh": round(self.ledger.stock_kwh, 2),
                "voorraad_prijs": (
                    round(self.ledger.stock_price, 3) if self.ledger.stock_price is not None else None
                ),
            },
            "banen": [
                {"titel": "Bijladen", "icoon": "mdi:battery-charging", "aan": self.enabled, "stappen": list(plan.steps), "schakelaar": self._switch_entity("prijssturing")},
                {"titel": "Verkoop", "icoon": "mdi:transmission-tower-export", "aan": self.sell_enabled, "stappen": sell_steps, "schakelaar": self._switch_entity("verkoop")},
                {"titel": "Negatieve prijs", "icoon": "mdi:cash-minus", "aan": self.negative_enabled, "stappen": negative_steps, "schakelaar": self._switch_entity("negatieve_prijs")},
                {"titel": "Vasthouden", "icoon": "mdi:lock-clock", "aan": self.hold_on, "stappen": hold_steps, "schakelaar": self._switch_entity("vasthouden")},
                {"titel": "Geen verlies", "icoon": "mdi:shield-check", "aan": self.no_loss_enabled, "stappen": no_loss_steps, "schakelaar": self._switch_entity("geen_verlies")},
            ],
        }

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

        # Direct opnieuw rekenen als een nieuw prijsvak begint, zodat vasthouden
        # en vrijgeven niet tot een minuut te laat komen.
        @callback
        def _slot_started(now: datetime) -> None:
            self.hass.async_create_task(self.async_request_refresh())

        self.config_entry.async_on_unload(
            async_track_time_change(self.hass, _slot_started, minute=(0, 15, 30, 45), second=2)
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

    @staticmethod
    def _power_differs(current: float | None, target: float, running: bool) -> bool:
        """Moet het vermogen opnieuw worden gezet?

        Bij de start altijd; onderweg pas bij een verschil van 150 W of meer,
        zodat het niet elke minuut tussen twee stappen heen en weer springt.
        """
        if current is None:
            return True
        return abs(current - target) >= (150 if running else 50)

    def _set_negative_charging(self, charging: bool) -> None:
        if self._negative_charging != charging:
            self._negative_charging = charging
            self._save()

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

        want_negative = self.negative_active
        want_charge = (
            not want_negative
            and self.enabled
            and plan.status == STATUS_CHARGING
            and bool(plan.power_w)
        )
        want_sell = (
            not want_negative
            and not want_charge
            and self.sell_enabled
            and self.can_sell
            and sell.status == SELL_SELLING
            and bool(sell.power_w)
            and not self.sell_blocked
        )

        try:
            if want_negative:
                power = int(inputs["max_power_w"])
                current = inputs["force_power_w"]
                if current is None or abs(current - power) >= 50:
                    await self._async_set_number(CONF_FORCE_POWER_ENTITY, power)
                    self._settle(f"laadvermogen {power} W (negatieve prijs)")
                if not inputs["charging"]:
                    await self._async_select(CONF_FORCE_MODE_ENTITY, FORCE_CHARGE)
                    await self._async_select(CONF_CONTROL_MODE_ENTITY, MODE_ENABLE)
                    self._set_selling(False)
                    self._settle(f"negatieve prijs: laden op vol vermogen ({power} W)")
                self._set_negative_charging(True)
            elif want_charge:
                self._set_negative_charging(False)
                current = inputs["force_power_w"]
                if self._power_differs(current, plan.power_w, inputs["charging"]):
                    await self._async_set_number(CONF_FORCE_POWER_ENTITY, plan.power_w)
                    self._settle(f"laadvermogen {plan.power_w} W")
                if not inputs["charging"]:
                    await self._async_select(CONF_FORCE_MODE_ENTITY, FORCE_CHARGE)
                    await self._async_select(CONF_CONTROL_MODE_ENTITY, MODE_ENABLE)
                    self._set_selling(False)
                    self._settle(f"bijladen gestart op {plan.power_w} W")
            elif want_sell:
                current = inputs["force_discharge_power_w"]
                if not self._selling and self._discharge_power_before is None:
                    self._discharge_power_before = current
                    self._save()
                if self._power_differs(current, sell.power_w, self._selling):
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
            elif self._negative_charging:
                await self._async_release(inputs)
                self._settle("negatieve prijs voorbij of accu vol, terug naar anti-feed")
            elif self.enabled and control == MODE_ENABLE:
                # Forceer-laden dat niet bij het plan hoort alleen terugzetten als
                # de prijssturing aan staat.
                await self._async_release(inputs)
                self._settle("bijladen gestopt, terug naar anti-feed")
            elif (self.enabled or self.sell_enabled) and force == FORCE_STOP:
                # Rusttoestand herstellen: RS485 uit met forceren op charge, zodat
                # handmatig forceer-laden werkt zoals de gebruiker gewend is.
                await self._async_select(CONF_FORCE_MODE_ENTITY, FORCE_CHARGE)
                self._settle("forceren terug op charge (rusttoestand)")
        except Exception:  # noqa: BLE001 - een mislukte opdracht mag de berekening niet stoppen
            _LOGGER.exception("Controlling the Marstek failed")

    async def _async_apply_hold(self, inputs: dict[str, Any]) -> None:
        """Blokkeer of geef het ontladen vrij via het maximale ontlaadvermogen.

        Anti-feed blijft aan staan, dus laden uit zonne-overschot gaat gewoon door.
        Zet iets anders het ontlaadvermogen tijdens het vasthouden terug (zoals een
        begrenzer voor de laadpaal), dan onthouden we die waarde voor na afloop en
        zetten we het weer op 0.
        """
        if not self.can_hold:
            return
        raw = inputs["max_discharge_raw"]
        if raw is None:
            return  # Marstek niet bereikbaar.
        try:
            if self.hold_active:
                if raw > 0:
                    self._discharge_limit_before = raw
                    await self._async_set_number(CONF_MAX_DISCHARGE_POWER_ENTITY, 0)
                    if not self._holding:
                        self.last_command = (
                            f"{dt_util.now().isoformat(timespec='seconds')} "
                            "vasthouden: ontladen geblokkeerd"
                        )
                        _LOGGER.info("Marstek: hold, discharging blocked")
                    self._holding = True
                    self._save()
            elif self._holding:
                restore = self._discharge_limit_before or DEFAULT_MAX_POWER
                await self._async_set_number(CONF_MAX_DISCHARGE_POWER_ENTITY, restore)
                self._holding = False
                self._discharge_limit_before = None
                self.last_command = (
                    f"{dt_util.now().isoformat(timespec='seconds')} "
                    f"vasthouden voorbij: ontladen vrij ({int(restore)} W)"
                )
                _LOGGER.info("Marstek: hold over, discharging released")
                self._save()
        except Exception:  # noqa: BLE001
            _LOGGER.exception("Adjusting the maximum discharge power failed")

    async def _async_release(self, inputs: dict[str, Any]) -> None:
        """Zet de Marstek terug in zijn rusttoestand: RS485 uit, anti-feed."""
        await self._async_select(CONF_CONTROL_MODE_ENTITY, MODE_DISABLE)
        # Altijd sturen, ook als Home Assistant al 'charge' toont: de toestand
        # van de selects loopt achter op de Marstek.
        await self._async_select(CONF_FORCE_MODE_ENTITY, FORCE_CHARGE)
        current = inputs["force_power_w"]
        if current is None or abs(current - inputs["max_power_w"]) >= 1:
            await self._async_set_number(CONF_FORCE_POWER_ENTITY, inputs["max_power_w"])
        # Het forceer-ontlaadvermogen alleen terugzetten als wij het voor een
        # verkoop hebben veranderd, en dan naar de waarde van daarvoor.
        if self.can_sell and self._discharge_power_before is not None:
            await self._async_set_number(
                CONF_FORCE_DISCHARGE_POWER_ENTITY, self._discharge_power_before
            )
            self._discharge_power_before = None
            self._save()
        self._set_selling(False)
        self._set_negative_charging(False)

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
                    _LOGGER.exception("Restoring the Marstek failed")
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
                _LOGGER.exception("Restoring the Marstek failed")
        await self.async_refresh()

    async def async_set_negative_enabled(self, enabled: bool) -> None:
        """Zet laden bij een negatieve prijs aan of uit."""
        self.negative_enabled = enabled
        self._save()
        self._settle_until = None
        if not enabled and self._negative_charging:
            try:
                await self._async_release(self._read_inputs())
                self._settle("laden bij negatieve prijs uit, terug naar anti-feed")
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Restoring the Marstek failed")
        await self.async_refresh()

    async def async_set_hold_enabled(self, enabled: bool) -> None:
        """Zet vasthouden onder de kostprijs aan of uit."""
        self.hold_enabled = enabled
        self._save()
        await self.async_refresh()

    async def async_set_no_loss_enabled(self, enabled: bool) -> None:
        """Zet 'geen verlies' aan of uit."""
        self.no_loss_enabled = enabled
        self._save()
        self._settle_until = None
        await self.async_refresh()

