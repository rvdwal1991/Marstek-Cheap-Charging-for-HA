"""Rekenregel voor het laadplan.

Dit bestand gebruikt bewust niets van Home Assistant, zodat de rekenregel los
te testen is (zie tests/test_planner.py).

Uitgangspunt: de batterij draait zelf anti-feed (zelfvoorzienend). Het plan
bepaalt alleen wanneer er uit het net wordt BIJgeladen, zodat de accu vol is
voordat de stroom duur wordt. Er wordt nooit geforceerd ontladen en na het
bijladen wordt de accu niet vastgehouden.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, tzinfo
import math

STATUS_CHARGING = "laden"
STATUS_PLANNED = "gepland"
STATUS_DONE = "klaar"
STATUS_FULL = "vol"
STATUS_NONE = "geen"
STATUS_UNKNOWN = "onbekend"
STATUSES = [
    STATUS_CHARGING,
    STATUS_PLANNED,
    STATUS_DONE,
    STATUS_FULL,
    STATUS_NONE,
    STATUS_UNKNOWN,
]

# Vanaf deze SoC geldt de accu als vol.
FULL_SOC = 99.0
# Deel van de netstroom dat in de accu belandt (alleen de laadkant).
CHARGE_EFFICIENCY = 0.88
# Het aantal laaduren rekent met 90 % van het maximale vermogen, omdat de
# Marstek bij hoge SoC terugregelt.
POWER_DERATE = 0.9
# Het uitgesmeerde vermogen mikt op klaar zijn na 92 % van de resterende tijd.
TIME_DERATE = 0.92
# Ondergrens voor de resterende tijd, zodat het vermogen aan het eind van het
# laatste laaduur niet omhoog schiet.
MIN_REMAINING_HOURS = 0.5
POWER_STEP_W = 100


@dataclass(frozen=True)
class PriceSlot:
    """Eén prijsvak (bij Zonneplan: een uur)."""

    start: datetime
    price: float
    seconds: float = 3600.0

    @property
    def end(self) -> datetime:
        return self.start + timedelta(seconds=self.seconds)


@dataclass(frozen=True)
class PlanParams:
    """Instellingen van de rekenregel."""

    top_hours: int = 6
    lookahead_hours: int = 18
    min_lookahead_hours: int = 8
    margin: float = 0.02
    min_power_w: int = 400


@dataclass(frozen=True)
class PlanMemory:
    """Wat het vorige plan was; nodig om een lopende laadbeurt af te maken."""

    status: str = STATUS_UNKNOWN
    charge_hours: tuple[datetime, ...] = ()
    window_end: datetime | None = None
    done_until: datetime | None = None


@dataclass(frozen=True)
class Plan:
    """Het laadplan op dit moment."""

    status: str = STATUS_UNKNOWN
    charge_hours: tuple[datetime, ...] = ()
    window: tuple[datetime, ...] = ()
    window_end: datetime | None = None
    hours_needed: int = 0
    power_w: int | None = None
    energy_kwh: float = 0.0
    average_price: float | None = None
    charge_end: datetime | None = None
    done_until: datetime | None = None
    text: str = "Geen prijzen of SoC beschikbaar"
    prices: tuple[PriceSlot, ...] = field(default=(), repr=False)

    @property
    def charge_start(self) -> datetime | None:
        return self.charge_hours[0] if self.charge_hours else None

    def memory(self) -> PlanMemory:
        return PlanMemory(self.status, self.charge_hours, self.window_end, self.done_until)


def clamp_efficiency(charged_kwh: float | None, discharged_kwh: float | None, default: float) -> float:
    """Rendement laden->ontladen uit de energietellers, begrensd op 0,70-0,95."""
    if charged_kwh and discharged_kwh and charged_kwh > 0:
        eta = discharged_kwh / charged_kwh
    else:
        eta = default
    return min(max(eta, 0.70), 0.95)


def _worth_charging(prices: list[PriceSlot], efficiency: float, params: PlanParams) -> list[bool]:
    """Per vak: is de prijs laag genoeg tegenover de dure vakken erna?"""
    result = []
    for index, slot in enumerate(prices):
        ahead = sorted(
            (s.price for s in prices[index + 1 : index + 1 + params.lookahead_hours]),
            reverse=True,
        )
        if len(ahead) < params.min_lookahead_hours:
            result.append(False)
            continue
        top = ahead[: params.top_hours]
        result.append(slot.price <= efficiency * (sum(top) / len(top)) - params.margin)
    return result


def _first_run(flags: list[bool]) -> list[int]:
    """Het eerste aaneengesloten blok waarvoor de vlag waar is."""
    run: list[int] = []
    for index, flag in enumerate(flags):
        if flag:
            run.append(index)
        elif run:
            break
    return run


def _euro(value: float, digits: int = 2) -> str:
    return f"{value:.{digits}f}".replace(".", ",")


def compute_plan(
    *,
    prices: list[PriceSlot],
    now: datetime,
    soc: float | None,
    capacity_kwh: float,
    max_power_w: float,
    efficiency: float,
    charging: bool,
    active: bool,
    memory: PlanMemory | None = None,
    params: PlanParams | None = None,
    tz: tzinfo | None = None,
) -> Plan:
    """Bereken het laadplan.

    prices   : gepubliceerde prijsvakken, oplopend; voorbije vakken mogen erin staan.
    charging : de Marstek is nu geforceerd aan het laden.
    active   : de prijssturing staat aan (alleen dan kan een laadbeurt 'klaar' raken).
    """
    params = params or PlanParams()
    memory = memory or PlanMemory()
    prices = [slot for slot in sorted(prices, key=lambda s: s.start) if slot.end > now]

    if soc is None or not prices:
        return Plan(done_until=memory.done_until, prices=tuple(prices))

    def local(moment: datetime) -> datetime:
        return moment.astimezone(tz) if tz else moment

    worth = _worth_charging(prices, efficiency, params)
    run = _first_run(worth)
    window = tuple(prices[i].start for i in run)
    window_end = prices[run[-1]].end if run else None

    energy = 0.0 if soc >= FULL_SOC else (100.0 - soc) / 100.0 * capacity_kwh / CHARGE_EFFICIENCY
    needed = 0 if energy == 0 else max(1, math.ceil(energy / (max_power_w / 1000.0 * POWER_DERATE)))

    previous = set(memory.charge_hours)
    kept = [i for i in run if prices[i].start in previous]
    if needed > 0 and charging and 0 in kept:
        # Eenmaal aan het laden blijven de geplande vakken staan; anders wordt
        # het plan steeds korter en het vermogen steeds hoger.
        chosen = kept
    else:
        chosen = sorted(sorted(run, key=lambda i: (prices[i].price, i))[:needed])

    remaining = sum(
        (prices[i].end - max(now, prices[i].start)).total_seconds() / 3600.0 for i in chosen
    )
    power: int | None = None
    if chosen:
        raw = energy / max(remaining * TIME_DERATE, MIN_REMAINING_HOURS) * 1000.0
        power = int(math.ceil(raw / POWER_STEP_W) * POWER_STEP_W)
        power = int(min(max(power, params.min_power_w), max_power_w))

    # Klaar voor dit venster: niet opnieuw starten en niet vasthouden.
    done_until = None
    if memory.done_until is not None and now < memory.done_until:
        done_until = memory.done_until
    elif (
        active
        and memory.status == STATUS_CHARGING
        and (0 not in chosen or prices[0].start not in previous)
    ):
        if memory.window_end is not None and memory.window_end > now:
            done_until = memory.window_end
        else:
            done_until = now + timedelta(hours=1)

    common = dict(window=window, window_end=window_end, hours_needed=needed, prices=tuple(prices))

    if done_until is not None:
        return Plan(
            status=STATUS_DONE,
            done_until=done_until,
            text="Bijladen is klaar · de Marstek regelt weer zelf (anti-feed)",
            **common,
        )

    if chosen:
        hours = tuple(prices[i].start for i in chosen)
        average = sum(prices[i].price for i in chosen) / len(chosen)
        charge_end = prices[chosen[-1]].end
        day = "morgen " if local(hours[0]).date() != local(now).date() else ""
        times = ", ".join(local(h).strftime("%H:%M") for h in hours)
        text = (
            f"Laden {day}om {times} op ca. {power} W "
            f"({_euro(energy, 1)} kWh, gem. € {_euro(average)}) · "
            f"klaar om {local(charge_end).strftime('%H:%M')}"
        )
        return Plan(
            status=STATUS_CHARGING if 0 in chosen else STATUS_PLANNED,
            charge_hours=hours,
            power_w=power,
            energy_kwh=round(energy, 2),
            average_price=round(average, 4),
            charge_end=charge_end,
            text=text,
            **common,
        )

    if run:
        return Plan(status=STATUS_FULL, text="Accu is vol · bijladen is niet nodig", **common)

    return Plan(
        status=STATUS_NONE,
        text=(
            "Geen laadmoment in de gepubliceerde prijzen "
            "(prijsverschil te klein, of morgen is nog niet bekend)"
        ),
        **common,
    )
