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
    CONF_CONNECTION,
    CONF_MODBUS_HUB,
    CONF_MODBUS_SLAVE,
    CONNECTION_MARSTEK_MODBUS,
    CONNECTION_MODBUS,
    DEFAULT_MODBUS_HUB,
    DEFAULT_MODBUS_SLAVE,
    RAW_CONTROL_DISABLE,
    RAW_CONTROL_ENABLE,
    RAW_FORCE,
    REG_CONTROL_MODE,
    REG_FORCE_CHARGE_POWER,
    REG_FORCE_DISCHARGE_POWER,
    REG_FORCE_MODE,
    REG_MAX_CHARGE_POWER,
    REG_MAX_DISCHARGE_POWER,
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
    CONF_BATTERY_CYCLES,
    CONF_BATTERY_PRICE,
    CONF_LANGUAGE,
    CONF_NEGATIVE_PRICE_LIMIT,
    CONF_HOUSE_ENTITY,
    CONF_NEGATIVE_STRATEGY,
    CONF_SOLAR_LEARN,
    CONF_SOLAR_RELIABILITY,
    CONF_USE_SOLAR,
    HOLD_MIN_STOCK_KWH,
    DEFAULT_SOLAR_LEARN,
    DEFAULT_SOLAR_RELIABILITY,
    DEFAULT_USE_SOLAR,
    NEGATIVE_STRATEGY_MAX_GAIN,
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
    DEFAULT_BATTERY_CYCLES,
    DEFAULT_BATTERY_PRICE,
    DEFAULT_LANGUAGE,
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
from .calibration import SolarCalibration
from .flow import build_flow
from .house import HouseProfile
from .i18n import resolve as resolve_language, tr
from .solar import async_read_forecast
from .ledger import Ledger
from .planner import (
    NEGATIVE_CHARGING,
    SELL_SELLING,
    STATUS_CHARGING,
    Plan,
    PlanMemory,
    NegativePlan,
    PlanParams,
    PriceSlot,
    SellParams,
    SellPlan,
    clamp_efficiency,
    compute_plan,
    compute_sell_plan,
    negative_price_slot,
    plan_negative,
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
        # Laden op vol vermogen bij een negatieve prijs: staat standaard aan.
        self.negative_enabled = True
        self.negative_active = False
        self.negative_plan: NegativePlan | None = None
        self._negative_hours: tuple[datetime, ...] = ()
        # Waar als de integratie zelf zo'n laadbeurt heeft gestart.
        self._negative_charging = False
        # Waar als de integratie zelf een verkoop (forceer-ontladen) heeft gestart.
        self._selling = False
        # Het forceer-ontlaadvermogen van voor de verkoop, om na afloop terug te zetten.
        self._discharge_power_before: float | None = None
        self._sell_hours: tuple[datetime, ...] = ()
        self.inputs: dict[str, Any] = {}
        # Verwachte zonne-opbrengst uit het Energie-dashboard: (uurbegin, Wh).
        self._solar_hours: tuple[tuple[datetime, float], ...] = ()
        # Geleerd verbruik van het huis per uur van de dag (uit de optionele vermogenssensor).
        self.house = HouseProfile()
        # Leert hoeveel van de zonneverwachting er echt wordt gehaald.
        self.calibration = SolarCalibration()
        self._solar_counters: tuple[str, ...] = ()
        self._solar_checked: datetime | None = None
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
        self.house = HouseProfile.from_dict(data.get("house_profile"))
        self.calibration = SolarCalibration.from_dict(data.get("solar_calibration"))
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
                "house_profile": self.house.to_dict(),
                "solar_calibration": self.calibration.to_dict(),
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
        if self.is_modbus:
            control, force = self._decode_modbus(control, force)
        elif self.is_marstek_modbus:
            control = {"on": MODE_ENABLE, "off": MODE_DISABLE}.get(control or "")
            force = {"standby": FORCE_STOP}.get(force or "", force)
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
            depreciation=self.depreciation,
            solar=self._solar_hours if conf.get(CONF_USE_SOLAR, DEFAULT_USE_SOLAR) else (),
            solar_factor=self.solar_factor,
            house_power_w=float(conf.get(CONF_HOUSE_POWER, DEFAULT_HOUSE_POWER)),
            house_profile=self.house.table() if conf.get(CONF_HOUSE_ENTITY) else (),
        )

    @property
    def solar_factor(self) -> float:
        """De betrouwbaarheid van de zonneverwachting: geleerd uit de werkelijke opbrengst, of de instelling."""
        configured = float(self.conf.get(CONF_SOLAR_RELIABILITY, DEFAULT_SOLAR_RELIABILITY)) / 100.0
        if self.conf.get(CONF_SOLAR_LEARN, DEFAULT_SOLAR_LEARN):
            learned = self.calibration.factor()
            if learned is not None:
                return learned
        return configured

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
            depreciation=self.depreciation,
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

    async def _async_refresh_solar(self) -> None:
        """Lees de zonneverwachting (om de 30 min). Lukt het niet, dan blijft de lijst leeg."""
        now = dt_util.utcnow()
        if not self.conf.get(CONF_USE_SOLAR, DEFAULT_USE_SOLAR):
            self._solar_hours = ()
            return
        if self._solar_checked is not None and now - self._solar_checked < timedelta(minutes=30):
            return
        self._solar_checked = now
        try:
            self._solar_hours, self._solar_counters = await async_read_forecast(self.hass)
            if self.calibration.record_forecast(
                dt_util.now().date(), self._solar_hours, dt_util.as_local
            ):
                self._save()
        except Exception:  # noqa: BLE001 - de verwachting is optioneel
            _LOGGER.debug("Zonneverwachting niet beschikbaar", exc_info=True)
            self._solar_hours = ()
        if not self._solar_hours:
            # Na een herstart zijn de verwachtingen er soms nog niet: over 5 minuten opnieuw.
            self._solar_checked = now - timedelta(minutes=25)

    def _sample_production(self) -> None:
        """Lees de teller van de zonnepanelen om de verwachting te vergelijken met de werkelijkheid."""
        if not self._solar_counters or not self.conf.get(CONF_SOLAR_LEARN, DEFAULT_SOLAR_LEARN):
            return
        total, seen = 0.0, False
        for entity_id in self._solar_counters:
            state = self.hass.states.get(entity_id)
            if state is None or state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN, ""):
                return  # een teller ontbreekt: liever niets meten dan een halve dag
            try:
                value = float(state.state)
            except ValueError:
                return
            unit = getattr(state, "attributes", {}).get("unit_of_measurement")
            total += value * {"Wh": 0.001, "MWh": 1000.0}.get(unit, 1.0)
            seen = True
        if seen and self.calibration.record_production(dt_util.now(), total):
            self._save()

    def _sample_house(self) -> None:
        """Leer het verbruik van het huis per uur van de dag (optionele sensor)."""
        entity_id = self.conf.get(CONF_HOUSE_ENTITY)
        if not entity_id:
            return
        state = self.hass.states.get(entity_id)
        watts: float | None = None
        if state is not None and state.state not in (STATE_UNAVAILABLE, STATE_UNKNOWN, ""):
            try:
                watts = float(state.state)
            except ValueError:
                watts = None
            if watts is not None and getattr(state, "attributes", {}).get("unit_of_measurement") == "kW":
                watts *= 1000.0
        if self.house.sample(dt_util.now(), watts):
            self._save()

    async def _async_update_data(self) -> Plan:
        self._sample_house()
        await self._async_refresh_solar()
        self._sample_production()
        inputs = self._read_inputs()
        self.inputs = inputs
        now = dt_util.utcnow()

        plan = self._compute_charge_plan(inputs)
        sell = self._compute_sell_plan(plan, inputs, now)
        limit, slot = self._update_negative(plan, inputs, now)
        price_now = self._update_ledger(plan, sell, inputs, now)
        self._update_hold(plan, sell, inputs, now, price_now)
        await self._async_apply_hold(inputs)

        if (
            self.enabled
            or self.sell_enabled
            or self._selling
            or self.negative_active
            or self._negative_charging
        ):
            await self._async_apply(plan, sell, inputs)

        self.flow = tr(self.language, self._build_flow(plan, sell, inputs, now, limit, slot))
        self.flow["taal"] = self.language

        if self.negative_active and self.negative_plan is not None:
            # Alleen de weergave: het bewaarde plan blijft het echte laadplan.
            hours = tuple(sorted({*self.negative_plan.hours, *plan.charge_hours}))
            return replace(
                plan,
                status=STATUS_CHARGING,
                charge_hours=hours,
                power_w=self.negative_plan.power_w,
                text=self.negative_plan.text,
            )
        return plan

    def _compute_charge_plan(self, inputs: dict[str, Any]) -> Plan:
        """Het laadplan voor de goedkope uren; onthoudt wat het vorige plan was."""
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
        return plan

    def _compute_sell_plan(self, plan: Plan, inputs: dict[str, Any], now: datetime) -> SellPlan:
        """Het verkoopplan (alleen als er een ontlaadvermogen is ingesteld)."""
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
        return sell

    def _update_negative(
        self, plan: Plan, inputs: dict[str, Any], now: datetime
    ) -> tuple[float, PriceSlot | None]:
        """Laden bij een negatieve prijs: nu laden, los van het plan. Geeft (grens, huidig vak)."""
        limit = float(self.conf.get(CONF_NEGATIVE_PRICE_LIMIT, DEFAULT_NEGATIVE_PRICE_LIMIT))
        slot = negative_price_slot(plan.prices, now, limit)
        self.negative_plan = None
        if self.negative_enabled and slot is not None:
            self.negative_plan = plan_negative(
                plan.prices,
                now,
                inputs["soc"],
                inputs["capacity_kwh"],
                inputs["max_power_w"],
                float(self.conf.get(CONF_MIN_POWER, DEFAULT_MIN_POWER)),
                limit,
                self._negative_hours,
                self.conf.get(CONF_NEGATIVE_STRATEGY) == NEGATIVE_STRATEGY_MAX_GAIN,
            )
        self._negative_hours = self.negative_plan.hours if self.negative_plan else ()
        self.negative_active = bool(
            self.negative_plan and self.negative_plan.status == NEGATIVE_CHARGING
        )
        return limit, slot

    def _export_price(self, price: float | None) -> float | None:
        """Wat een kWh opbrengt als hij aan het net wordt geleverd."""
        if price is None:
            return None
        params = self.sell_params
        return price * params.price_factor - params.price_offset

    def _update_ledger(
        self, plan: Plan, sell: SellPlan, inputs: dict[str, Any], now: datetime
    ) -> float | None:
        """Boek de gerealiseerde opbrengst aan de hand van de energietellers. Geeft de prijs nu."""
        current = next((s for s in plan.prices if s.start <= now < s.end), None)
        price_now = current.price if current else None
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
            export_price=self._export_price(price_now),
            replacement_cost=(
                sell.refill_price / inputs["efficiency"] if sell.refill_price else None
            ),
            efficiency=inputs["efficiency"],
            depreciation=self.depreciation,
        ):
            self._save()
        return price_now

    def _update_hold(
        self, plan: Plan, sell: SellPlan, inputs: dict[str, Any], now: datetime, price_now: float | None
    ) -> None:
        """Vasthouden en Geen verlies: wanneer mag de accu niet ontladen of verkopen?"""
        # Is de accu leeg (en wordt er niet geladen), dan vervalt de voorraad in de boeken.
        soc = inputs["soc"]
        if (
            soc is not None
            and soc <= inputs["min_soc"] + 1
            and not inputs["charging"]
            and self.ledger.clear_stock()
        ):
            self._save()
        cost = self.stock_cost()
        has_stock = self.ledger.stock_kwh >= HOLD_MIN_STOCK_KWH and cost is not None
        export_now = self._export_price(price_now)
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
            and has_stock
            and price_now is not None
            and price_now < cost
            and not selling_now
        )
        self.hold_until = None
        if self.hold_active:
            self.hold_until = next(
                (s.start for s in plan.prices if s.start > now and s.price >= cost), None
            )

    # ---------------------------------------------------------- stroomschema

    @property
    def depreciation(self) -> float:
        """Afschrijving van de accu in euro per kWh: prijs / (cycli x capaciteit)."""
        price = float(self.conf.get(CONF_BATTERY_PRICE) or DEFAULT_BATTERY_PRICE)
        cycles = float(self.conf.get(CONF_BATTERY_CYCLES) or DEFAULT_BATTERY_CYCLES)
        capacity = float(self.inputs.get("capacity_kwh") or self.conf.get(CONF_CAPACITY_KWH) or 0)
        if price <= 0 or cycles <= 0 or capacity <= 0:
            return 0.0
        return price / (cycles * capacity)

    def stock_cost(self) -> float | None:
        """Kostprijs van de voorraad inclusief afschrijving: onder die prijs is gebruiken verlies."""
        base = self.ledger.stock_price
        return None if base is None else base + self.depreciation

    @property
    def language(self) -> str:
        """De taal van de teksten: de keuze in de opties, of anders die van Home Assistant."""
        chosen = self.conf.get(CONF_LANGUAGE, DEFAULT_LANGUAGE)
        return resolve_language(self.hass.config.language if chosen in (None, "auto") else chosen)

    def switch_entity(self, key: str) -> str | None:
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
        return build_flow(self, plan, sell, inputs, now, limit, negative_slot)

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

    @property
    def is_modbus(self) -> bool:
        return self.conf.get(CONF_CONNECTION) == CONNECTION_MODBUS

    @property
    def is_marstek_modbus(self) -> bool:
        return self.conf.get(CONF_CONNECTION) == CONNECTION_MARSTEK_MODBUS

    @staticmethod
    def _decode_modbus(control: str | None, force: str | None) -> tuple[str | None, str | None]:
        """Zet de ruwe registerwaarden om naar de woorden van de ESPHome-selects."""
        def raw(value: str | None) -> int | None:
            try:
                return int(float(value)) if value is not None else None
            except ValueError:
                return None

        control_raw = raw(control)
        control_text = (
            MODE_ENABLE if control_raw == RAW_CONTROL_ENABLE
            else MODE_DISABLE if control_raw == RAW_CONTROL_DISABLE
            else None
        )
        return control_text, RAW_FORCE.get(raw(force))

    async def _async_write_register(self, address: int, value: int) -> None:
        await self.hass.services.async_call(
            "modbus",
            "write_register",
            {
                "hub": self.conf.get(CONF_MODBUS_HUB) or DEFAULT_MODBUS_HUB,
                "slave": int(self.conf.get(CONF_MODBUS_SLAVE) or DEFAULT_MODBUS_SLAVE),
                "address": address,
                "value": int(value),
            },
            blocking=True,
        )

    async def _async_select(self, key: str, option: str) -> None:
        if self.is_modbus:
            if key == CONF_CONTROL_MODE_ENTITY:
                value = RAW_CONTROL_ENABLE if option == MODE_ENABLE else RAW_CONTROL_DISABLE
                await self._async_write_register(REG_CONTROL_MODE, value)
            else:
                code = {v: k for k, v in RAW_FORCE.items()}[option]
                await self._async_write_register(REG_FORCE_MODE, code)
            return
        if self.is_marstek_modbus:
            if key == CONF_CONTROL_MODE_ENTITY:
                await self.hass.services.async_call(
                    "switch",
                    "turn_on" if option == MODE_ENABLE else "turn_off",
                    {"entity_id": self.conf[key]},
                    blocking=True,
                )
                return
            option = "standby" if option == FORCE_STOP else option
        await self.hass.services.async_call(
            "select",
            "select_option",
            {"entity_id": self.conf[key], "option": option},
            blocking=True,
        )

    async def _async_set_number(self, key: str, watts: float) -> None:
        if self.is_modbus:
            address = {
                CONF_FORCE_POWER_ENTITY: REG_FORCE_CHARGE_POWER,
                CONF_FORCE_DISCHARGE_POWER_ENTITY: REG_FORCE_DISCHARGE_POWER,
                CONF_MAX_POWER_ENTITY: REG_MAX_CHARGE_POWER,
                CONF_MAX_DISCHARGE_POWER_ENTITY: REG_MAX_DISCHARGE_POWER,
            }.get(key)
            if address is not None:
                await self._async_write_register(address, int(watts))
            return
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
                power = int(self.negative_plan.power_w or inputs["max_power_w"])
                current = inputs["force_power_w"]
                if self._power_differs(current, power, inputs["charging"]):
                    await self._async_set_number(CONF_FORCE_POWER_ENTITY, power)
                    self._settle(f"laadvermogen {power} W (negatieve prijs)")
                if not inputs["charging"]:
                    await self._async_select(CONF_FORCE_MODE_ENTITY, FORCE_CHARGE)
                    await self._async_select(CONF_CONTROL_MODE_ENTITY, MODE_ENABLE)
                    self._set_selling(False)
                    self._settle(f"negatieve prijs: laden op {power} W")
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

