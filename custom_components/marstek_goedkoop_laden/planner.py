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
def one_way_efficiency(efficiency: float) -> float:
    """Rendement van alleen laden of alleen ontladen.

    Het gemeten rendement is laden en weer ontladen samen. Het verlies wordt
    gelijk over beide kanten verdeeld: de wortel van het totaal (77 % -> 88 %).
    """
    return math.sqrt(efficiency)

# Het aantal laaduren rekent met 90 % van het maximale vermogen, omdat de
# Marstek bij hoge SoC terugregelt.
POWER_DERATE = 0.9
# Het uitgesmeerde vermogen mikt op klaar zijn na 85 % van de resterende tijd,
# zodat de accu ook echt vol is aan het eind van het laatste laaduur.
TIME_DERATE = 0.85
# Ondergrens voor de resterende tijd, zodat het vermogen aan het eind van het
# laatste laaduur niet omhoog schiet.
MIN_REMAINING_HOURS = 0.25
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
    # De controles die tot dit plan leidden, voor het stroomschema op het dashboard.
    steps: tuple[dict, ...] = ()
    # Schatting in euro: wat het bijladen kost, wat die stroom later waard is
    # (rendement x de dure uren waarmee is vergeleken) en het verschil.
    cost_eur: float | None = None
    value_eur: float | None = None
    gain_eur: float | None = None

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


def _use_prices(prices: list[PriceSlot], params: PlanParams) -> list[float | None]:
    """Per vak: de gemiddelde prijs van de duurste vakken erna (None = te weinig bekend).

    Dat is de prijs waartegen bijgeladen stroom naar verwachting wordt gebruikt.
    """
    result: list[float | None] = []
    for index in range(len(prices)):
        ahead = sorted(
            (s.price for s in prices[index + 1 : index + 1 + params.lookahead_hours]),
            reverse=True,
        )
        if len(ahead) < params.min_lookahead_hours:
            result.append(None)
            continue
        top = ahead[: params.top_hours]
        result.append(sum(top) / len(top))
    return result


# Uren die minder dan een halve cent boven de drempel liggen tellen ook mee. Zonder
# deze speling valt bij een bijna vlakke nacht een uur af om een fractie van een cent.
WORTH_TOLERANCE = 0.005


def _worth_charging(prices: list[PriceSlot], efficiency: float, params: PlanParams) -> list[bool]:
    """Per vak: is de prijs laag genoeg tegenover de dure vakken erna?"""
    return [
        use is not None and slot.price <= efficiency * use - params.margin + WORTH_TOLERANCE
        for slot, use in zip(prices, _use_prices(prices, params))
    ]


# Een of twee uren die net niet goedkoop genoeg zijn, onderbreken het laadvenster niet.
MAX_GAP_HOURS = 2


def _worth_run(flags: list[bool], max_gap: int = MAX_GAP_HOURS) -> list[int]:
    """De laadwaardige vakken van het eerste goedkope venster.

    Het venster begint bij het eerste laadwaardige vak en loopt door zolang het
    volgende laadwaardige vak binnen `max_gap` vakken ligt. Zo knipt één vak dat
    op de grens zit (bijvoorbeeld € 0,29 tussen vakken van € 0,28 en € 0,27) het
    venster niet in tweeën.
    """
    run: list[int] = []
    gap = 0
    for index, flag in enumerate(flags):
        if flag:
            run.append(index)
            gap = 0
        elif run:
            gap += 1
            if gap > max_gap:
                break
    return run


def _euro(value: float, digits: int = 2) -> str:
    return f"{value:.{digits}f}".replace(".", ",")


def step(title: str, detail: str, kind: str) -> dict:
    """Eén stap in het stroomschema. kind: ok, stop, actie of eind."""
    return {"titel": title, "detail": detail, "soort": kind}


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
        return Plan(
            done_until=memory.done_until,
            prices=tuple(prices),
            steps=(
                step("Prijzen en SoC bekend", "Geen prijzen of SoC beschikbaar", "stop"),
                step("Geen bijladen", "Wacht op gegevens", "eind"),
            ),
        )

    def local(moment: datetime) -> datetime:
        return moment.astimezone(tz) if tz else moment

    def clock(moment: datetime) -> str:
        return local(moment).strftime("%H:%M")

    worth = _worth_charging(prices, efficiency, params)
    run = _worth_run(worth)
    # Het venster loopt aaneen van het eerste tot het laatste laadwaardige vak; geladen
    # wordt alleen in de laadwaardige vakken zelf (`run`).
    window = tuple(prices[i].start for i in range(run[0], run[-1] + 1)) if run else ()
    window_end = prices[run[-1]].end if run else None

    energy = (
        0.0
        if soc >= FULL_SOC
        else (100.0 - soc) / 100.0 * capacity_kwh / one_way_efficiency(efficiency)
    )
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
    # Er past niet meer in dan de gekozen uren aankunnen: is er te weinig goedkoop
    # venster, dan wordt er minder geladen dan er nodig is.
    if chosen:
        energy_plan = min(energy, remaining * max_power_w / 1000.0 * POWER_DERATE)
    else:
        energy_plan = 0.0
    partial = bool(chosen) and energy_plan < energy - 0.05
    power: int | None = None
    if chosen:
        raw = energy_plan / max(remaining * TIME_DERATE, MIN_REMAINING_HOURS) * 1000.0
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

    if run:
        window_step = step(
            "Goedkoop venster", f"{clock(prices[run[0]].start)} – {clock(window_end)}", "ok"
        )
    else:
        window_step = step("Geen goedkoop venster", "Niet in de gepubliceerde prijzen", "stop")
    if needed > 0:
        need_step = step("Accu niet vol", f"Nog {_euro(energy, 1)} kWh nodig", "ok")
    else:
        need_step = step("Accu is vol", "Bijladen is niet nodig", "stop")

    if done_until is not None:
        return Plan(
            status=STATUS_DONE,
            done_until=done_until,
            text="Bijladen is klaar · de Marstek regelt weer zelf (anti-feed)",
            steps=(
                step("Laadbeurt gedaan", "In dit goedkope venster", "ok"),
                step("Klaar", f"Geen nieuwe start tot {clock(done_until)}", "eind"),
            ),
            **common,
        )

    if chosen:
        hours = tuple(prices[i].start for i in chosen)
        average = sum(prices[i].price for i in chosen) / len(chosen)
        charge_end = prices[chosen[-1]].end
        use = _use_prices(prices, params)
        share = energy_plan / len(chosen)
        cost = energy_plan * average
        value = sum(share * efficiency * (use[i] if use[i] is not None else prices[i].price / efficiency) for i in chosen)
        day = "morgen " if local(hours[0]).date() != local(now).date() else ""
        times = ", ".join(local(h).strftime("%H:%M") for h in hours)
        amount = (
            f"{_euro(energy_plan, 1)} van {_euro(energy, 1)} kWh"
            if partial
            else f"{_euro(energy_plan, 1)} kWh"
        )
        text = (
            f"Laden {day}om {times} op ca. {power} W "
            f"({amount}, gem. € {_euro(average)}) · "
            f"klaar om {local(charge_end).strftime('%H:%M')}"
        )
        if partial:
            text += " · het goedkope venster is te kort om vol te komen"
        return Plan(
            status=STATUS_CHARGING if 0 in chosen else STATUS_PLANNED,
            charge_hours=hours,
            power_w=power,
            energy_kwh=round(energy_plan, 2),
            average_price=round(average, 4),
            charge_end=charge_end,
            text=text,
            cost_eur=round(cost, 2),
            value_eur=round(value, 2),
            # Afgerond zo dat de getoonde bedragen op elkaar aansluiten.
            gain_eur=round(round(value, 2) - round(cost, 2), 2),
            steps=(
                window_step,
                need_step,
                step(
                    f"Laden, {len(chosen)} uur",
                    f"Ca. {power} W, gemiddeld € {_euro(average)}"
                    + (f" · {_euro(energy_plan, 1)} van {_euro(energy, 1)} kWh" if partial else ""),
                    "actie",
                ),
            ),
            **common,
        )

    if run:
        return Plan(
            status=STATUS_FULL,
            text="Accu is vol · bijladen is niet nodig",
            steps=(window_step, need_step, step("Geen bijladen", "Stopt bij deze stap", "eind")),
            **common,
        )

    return Plan(
        status=STATUS_NONE,
        text=(
            "Geen laadmoment in de gepubliceerde prijzen "
            "(prijsverschil te klein, of morgen is nog niet bekend)"
        ),
        steps=(window_step, step("Geen bijladen", "Prijsverschil te klein of morgen onbekend", "eind")),
        **common,
    )


# --------------------------------------------------------------------- verkoop

SELL_SELLING = "verkopen"
SELL_PLANNED = "gepland"
SELL_NONE = "geen"
SELL_UNKNOWN = "onbekend"
SELL_STATUSES = [SELL_SELLING, SELL_PLANNED, SELL_NONE, SELL_UNKNOWN]

# Extra SoC boven de ontlaadgrens van de Marstek die altijd blijft staan.
MIN_SOC_BUFFER = 3.0
# Aantal goedkoopste uren van het laadvenster waarmee de terugkoopprijs wordt bepaald.
REFILL_HOURS = 3


@dataclass(frozen=True)
class SellParams:
    """Instellingen voor verkopen."""

    margin: float = 0.10
    house_power_w: float = 400.0
    reserve_min_soc: float = 20.0
    price_factor: float = 1.0
    price_offset: float = 0.0
    min_power_w: int = 400
    min_surplus_kwh: float = 0.3


@dataclass(frozen=True)
class SellPlan:
    """Het verkoopplan op dit moment."""

    status: str = SELL_UNKNOWN
    sell_hours: tuple[datetime, ...] = ()
    power_w: int | None = None
    energy_kwh: float = 0.0
    reserve_soc: float | None = None
    average_price: float | None = None
    threshold: float | None = None
    refill_price: float | None = None
    text: str = "Geen prijzen of SoC beschikbaar"
    steps: tuple[dict, ...] = ()
    # Schatting in euro: opbrengst van de verkoop, wat terugladen kost en het verschil.
    revenue_eur: float | None = None
    refill_cost_eur: float | None = None
    gain_eur: float | None = None


def compute_sell_plan(
    *,
    charge_plan: Plan,
    now: datetime,
    soc: float | None,
    capacity_kwh: float,
    max_power_w: float,
    efficiency: float,
    min_soc: float,
    selling: bool,
    previous_hours: tuple[datetime, ...] = (),
    params: SellParams | None = None,
    tz: tzinfo | None = None,
) -> SellPlan:
    """Bepaal of en wanneer er overschot aan het net wordt verkocht.

    Verkopen gebeurt alleen als alles hieronder geldt:
    1. er ligt een goedkoop laadvenster met gepubliceerde prijzen in het verschiet;
    2. de verkoopprijs is hoger dan terugladen kost (laadprijs / rendement) plus de marge;
    3. er is overschot boven de reserve: de ondergrens plus het verwachte eigen
       verbruik tot het terugladen;
    4. het uur hoort bij de duurste uren tot dat laadvenster.

    selling        : de integratie is nu zelf aan het verkopen.
    previous_hours : de verkoopuren van het vorige plan (om een lopende verkoop af te maken).
    """
    params = params or SellParams()
    prices = list(charge_plan.prices)
    none_step = step("Geen verkoop", "Stopt bij deze stap", "eind")

    def later(detail: str) -> dict:
        return step("Geen verkoop gepland", detail, "eind")
    if soc is None or not prices:
        return SellPlan(
            steps=(step("Prijzen en SoC bekend", "Geen prijzen of SoC beschikbaar", "stop"), none_step)
        )

    def local(moment: datetime) -> datetime:
        return moment.astimezone(tz) if tz else moment

    def export(price: float) -> float:
        return price * params.price_factor - params.price_offset

    window = set(charge_plan.window)
    window_slots = [slot for slot in prices if slot.start in window]
    if not window_slots:
        return SellPlan(
            status=SELL_NONE,
            text="Geen verkoop: er is nog geen goedkoop laadvenster bekend",
            steps=(
                step("Wacht op laadvenster", "Nog geen goedkoop laadvenster bekend", "wacht"),
                later("Zodra de prijzen van morgen bekend zijn"),
            ),
        )
    if min(slot.start for slot in window_slots) <= now:
        return SellPlan(
            status=SELL_NONE,
            text="Geen verkoop: het goedkope laadvenster loopt",
            steps=(
                step("Laadvenster loopt nu", "Stroom is nu goedkoop", "wacht"),
                later("Na het laadvenster, als er overschot is"),
            ),
        )

    cheapest = sorted(window_slots, key=lambda s: (s.price, s.start))
    refill = cheapest[: min(REFILL_HOURS, len(cheapest))]
    refill_price = sum(s.price for s in refill) / len(refill)
    refill_at = cheapest[0].start
    threshold = refill_price / efficiency + params.margin

    hours_until = max((refill_at - now).total_seconds() / 3600.0, 0.0)
    discharge_efficiency = one_way_efficiency(efficiency)
    own_use_kwh = params.house_power_w / 1000.0 * hours_until / discharge_efficiency
    reserve_soc = min(
        100.0,
        max(
            min_soc + MIN_SOC_BUFFER,
            params.reserve_min_soc,
            min_soc + own_use_kwh / capacity_kwh * 100.0,
        ),
    )
    surplus = (soc - reserve_soc) / 100.0 * capacity_kwh * discharge_efficiency
    common = dict(
        reserve_soc=round(reserve_soc, 1), threshold=round(threshold, 4), refill_price=round(refill_price, 4)
    )

    candidates = [
        slot
        for slot in prices
        if slot.start < refill_at and slot.start not in window and export(slot.price) >= threshold
    ]
    refill_step = step(
        "Laadbeurt komt eraan",
        f"Terugladen vanaf {local(refill_at).strftime('%H:%M')} voor ca. € {_euro(refill_price)}",
        "ok",
    )
    best = max((export(s.price) for s in prices if s.start < refill_at), default=None)
    if not candidates:
        detail = f" (hoogste € {_euro(best)}, nodig € {_euro(threshold)})" if best is not None else ""
        short = f"€ {_euro(best)}, nodig € {_euro(threshold)}" if best is not None else "Geen uren"
        return SellPlan(
            status=SELL_NONE,
            text=f"Geen verkoop: de opbrengst is te laag{detail}",
            steps=(
                refill_step,
                step("Opbrengst te laag", short, "stop"),
                later(f"Verkoopt vanaf € {_euro(threshold)}, vóór {local(refill_at).strftime('%H:%M')}"),
            ),
            **common,
        )
    price_step = step(
        "Opbrengst hoog genoeg", f"€ {_euro(best)}, nodig € {_euro(threshold)}", "ok"
    )

    if surplus <= (0.0 if selling else params.min_surplus_kwh):
        return SellPlan(
            status=SELL_NONE,
            text=f"Geen verkoop: geen overschot boven de reserve van {round(reserve_soc)} %",
            steps=(
                refill_step,
                price_step,
                step("Geen overschot", f"Reserve is {round(reserve_soc)} %", "stop"),
                later(f"Verkoopt zodra de SoC boven {round(reserve_soc)} % komt"),
            ),
            **common,
        )

    needed = max(1, math.ceil(surplus / (max_power_w / 1000.0 * POWER_DERATE)))
    previous = set(previous_hours)
    kept = [slot for slot in candidates if slot.start in previous]
    if selling and kept and kept[0].start <= now:
        chosen = kept
    else:
        ranked = sorted(candidates, key=lambda s: (-export(s.price), s.start))[:needed]
        chosen = sorted(ranked, key=lambda s: s.start)

    remaining = sum((s.end - max(now, s.start)).total_seconds() / 3600.0 for s in chosen)
    # Niet meer verkopen dan de gekozen uren aankunnen.
    sold = min(surplus, remaining * max_power_w / 1000.0 * POWER_DERATE)
    raw = sold / max(remaining * TIME_DERATE, MIN_REMAINING_HOURS) * 1000.0
    power = int(math.ceil(raw / POWER_STEP_W) * POWER_STEP_W)
    power = int(min(max(power, params.min_power_w), max_power_w))

    average = sum(export(s.price) for s in chosen) / len(chosen)
    day = "morgen " if local(chosen[0].start).date() != local(now).date() else ""
    times = ", ".join(local(s.start).strftime("%H:%M") for s in chosen)
    text = (
        f"Verkopen {day}om {times} op ca. {power} W "
        f"({_euro(sold, 1)} kWh boven reserve {round(reserve_soc)} %, gem. € {_euro(average)}) · "
        f"terugladen vanaf {local(refill_at).strftime('%H:%M')} voor ca. € {_euro(refill_price)}"
    )
    return SellPlan(
        status=SELL_SELLING if chosen[0].start <= now else SELL_PLANNED,
        sell_hours=tuple(s.start for s in chosen),
        power_w=power,
        energy_kwh=round(sold, 2),
        average_price=round(average, 4),
        text=text,
        revenue_eur=round(sold * average, 2),
        refill_cost_eur=round(sold * refill_price / efficiency, 2),
        gain_eur=round(sold * (average - refill_price / efficiency), 2),
        steps=(
            refill_step,
            price_step,
            step(
                "Overschot boven reserve",
                f"{_euro(sold, 1)} kWh boven {round(reserve_soc)} %",
                "ok",
            ),
            step(
                f"Verkopen, {len(chosen)} uur",
                f"Ca. {power} W, gemiddeld € {_euro(average)}",
                "actie",
            ),
        ),
        **common,
    )


# ------------------------------------------------------------- negatieve prijs


def negative_price_slot(prices: list[PriceSlot] | tuple[PriceSlot, ...], now: datetime, limit: float = 0.0) -> PriceSlot | None:
    """Het lopende prijsvak als de prijs daarvan onder de grens ligt, anders None."""
    for slot in prices:
        if slot.start <= now < slot.end:
            return slot if slot.price < limit else None
    return None

