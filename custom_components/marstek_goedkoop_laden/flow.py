"""Het stroomschema voor de dashboardkaarten: tijdlijn, controles per onderdeel en resultaat.

Dit is alleen weergave: er wordt hier niets gestuurd of berekend dat het gedrag
van de Marstek beinvloedt. De coordinator geeft zichzelf mee en deze module leest
zijn toestand.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from homeassistant.util import dt as dt_util

from .const import (
    CONF_NEGATIVE_STRATEGY,
    FORCE_CHARGE,
    FORCE_DISCHARGE,
    FORCE_STOP,
    HOLD_MIN_STOCK_KWH,
    MODE_ENABLE,
    NEGATIVE_STRATEGY_MAX_GAIN,
)
from .planner import NEGATIVE_CHARGING, NEGATIVE_WAITING, Plan, PriceSlot, SellPlan, step


def build_flow(
    c: Any,
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

    cost = c.stock_cost()
    control, force = inputs["control_mode"], inputs["force_mode"]
    if c.negative_active:
        doing = "Laden op vol vermogen (negatieve prijs)"
    elif control == MODE_ENABLE and force == FORCE_CHARGE:
        doing = "Bijladen uit het net"
    elif control == MODE_ENABLE and force == FORCE_DISCHARGE:
        doing = "Verkopen aan het net" if c._selling else "Ontladen (handmatig)"
    elif control == MODE_ENABLE and force == FORCE_STOP:
        doing = "Stilgezet (handmatig)"
    elif control is None:
        doing = "Marstek niet bereikbaar"
    elif c.hold_active:
        doing = "Vasthouden: ontladen geblokkeerd"
    else:
        doing = "Zelf regelen (anti-feed)"

    events: list[tuple[datetime, datetime, dict]] = []
    for start, end in ranges(plan.charge_hours):
        if end <= now:
            continue
        if c.enabled:
            detail = f"Ca. {plan.power_w} W, {euro(plan.energy_kwh, 1)} kWh, gemiddeld € {euro(plan.average_price or 0)}"
            kind = "actie"
        else:
            detail = "Wordt niet uitgevoerd: bijladen staat uit"
            kind = "eind"
        events.append((start, end, step(f"{clock(start)} – {clock(end)} · bijladen", detail, kind)))
    for start, end in ranges(sell.sell_hours):
        if end <= now:
            continue
        if c.sell_enabled:
            detail = f"Ca. {sell.power_w} W, {euro(sell.energy_kwh, 1)} kWh, gemiddeld € {euro(sell.average_price or 0)}"
            kind = "actie"
        else:
            detail = "Wordt niet uitgevoerd: verkopen staat uit"
            kind = "eind"
        events.append((start, end, step(f"{clock(start)} – {clock(end)} · verkopen", detail, kind)))
    if c.hold_active and c.hold_until is not None and cost is not None:
        events.append(
            (
                c.hold_until,
                c.hold_until,
                step(
                    f"{clock(c.hold_until)} · ontladen vrij",
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
        neg = c.negative_plan
        if neg is not None and neg.status in (NEGATIVE_CHARGING, NEGATIVE_WAITING):
            window_text = f"{clock(neg.window[0].start)} – {clock(neg.window[-1].end)} · {len(neg.window)} uur"
            picked = ", ".join(
                f"{clock(start)} {euro(kwh, 1)} kWh" for start, kwh in sorted((neg.allocation or {}).items())
            ) or "–"
            negative_steps = [
                price_step,
                step("Negatief venster", window_text, "ok"),
                step("Beste uren eerst vol" if c.conf.get(CONF_NEGATIVE_STRATEGY) == NEGATIVE_STRATEGY_MAX_GAIN else "Energie naar waarde per uur", picked, "ok"),
            ]
            if neg.status == NEGATIVE_CHARGING:
                negative_steps.append(step("Laden uitgesmeerd", f"{neg.power_w} W · {euro(neg.energy_kwh, 1)} kWh · verwacht € {euro(neg.gain)}", "actie"))
            else:
                negative_steps.append(step("Dit uur overslaan", "Een ander uur levert meer op", "wacht"))
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
    if not c.can_hold:
        hold_steps = [
            step("Niet ingesteld", "Kies de entiteit voor het maximale ontlaadvermogen", "stop"),
            step("Niet actief", "Stopt bij deze stap", "eind"),
        ]
    elif c.ledger.stock_kwh < HOLD_MIN_STOCK_KWH or cost is None:
        hold_steps = [
            step("Geen bijgeladen voorraad", "Niets om vast te houden", "stop"),
            step("Niet actief", "De Marstek regelt zelf", "eind"),
        ]
    else:
        stock_step = step(
            "Bijgeladen voorraad",
            f"{euro(c.ledger.stock_kwh, 1)} kWh, kostprijs € {euro(cost)}",
            "ok",
        )
        price_text = f"Nu € {euro(current_slot.price)}" if current_slot else "Prijs onbekend"
        if c.hold_active:
            until = f"Tot {clock(c.hold_until)}" if c.hold_until else f"Tot de prijs boven € {euro(cost)} komt"
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

    if c.no_loss_enabled:
        if c.ledger.stock_kwh >= HOLD_MIN_STOCK_KWH and cost is not None:
            guard = step(
                "Voorraad bewaakt",
                f"{euro(c.ledger.stock_kwh, 1)} kWh, alleen boven € {euro(cost)}",
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

    if c.can_sell:
        sell_steps = list(sell.steps)
        if c.sell_blocked and sell_steps and sell_steps[-1]["soort"] == "actie":
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
    if not c.enabled:
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
    if not c.sell_enabled:
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
    c.expected_gain = round(total, 2)

    charge_hours = set(plan.charge_hours)
    sell_hours = set(sell.sell_hours)
    negative_hours = set(c.negative_plan.hours) if c.negative_plan else set()
    window_start = now - timedelta(hours=3)
    prices = []
    for slot in plan.prices:
        if slot.end <= window_start:
            continue
        kind = (
            "negatief" if slot.start in negative_hours
            else "laden" if slot.start in charge_hours
            else "verkoop" if slot.start in sell_hours
            else "negatief_venster" if slot.price < limit
            else ""
        )
        prices.append({"start": slot.start.isoformat(), "prijs": round(slot.price, 4), "soort": kind})
    current_price = next((s.price for s in plan.prices if s.start <= now < s.end), None)
    stock_cost = c.stock_cost()
    overview = {
        "status": plan.status,
        "bezig": doing,
        "soc": inputs["soc"],
        "prijs_nu": None if current_price is None else round(current_price, 4),
        "laadvermogen_w": plan.power_w,
        "rendement": round(inputs["efficiency"], 3),
        "afschrijving_per_kwh": round(c.depreciation, 4),
        "kostprijs": None if stock_cost is None else round(stock_cost, 4),
        "grens_negatief": limit,
        "capaciteit_kwh": inputs["capacity_kwh"],
        "zon_overschot_kwh": plan.solar_kwh,
    }

    return {
        "tijdlijn": timeline,
        "overzicht": overview,
        "prijzen": prices,
        "resultaat": {
            "totaal": round(total, 2),
            "regels": lines,
            "vandaag": round(c.ledger.day_gain, 2),
            "week": round(c.ledger.week_gain, 2),
            "vorige_week": (
                round(c.ledger.prev_week_gain, 2) if c.ledger.prev_week_gain is not None else None
            ),
            "maand": round(c.ledger.month_gain, 2),
            "jaar": round(c.ledger.year_gain, 2),
            "geladen_kwh": round(c.ledger.day_charged_kwh, 2),
            "laadkosten": round(c.ledger.day_charge_cost, 2),
            "afschrijving": round(c.ledger.day_depreciation, 2),
            "gebruikt_kwh": round(c.ledger.day_used_kwh + c.ledger.day_sold_kwh, 2),
            "voorraad_kwh": round(c.ledger.stock_kwh, 2),
            "voorraad_prijs": (
                round(c.ledger.stock_price, 3) if c.ledger.stock_price is not None else None
            ),
        },
        "banen": [
            {"id": "bijladen", "titel": "Bijladen", "icoon": "mdi:battery-charging", "aan": c.enabled, "stappen": list(plan.steps), "schakelaar": c.switch_entity("prijssturing")},
            {"id": "verkoop", "titel": "Verkoop", "icoon": "mdi:transmission-tower-export", "aan": c.sell_enabled, "stappen": sell_steps, "schakelaar": c.switch_entity("verkoop")},
            {"id": "negatief", "titel": "Negatieve prijs", "icoon": "mdi:cash-minus", "aan": c.negative_enabled, "stappen": negative_steps, "schakelaar": c.switch_entity("negatieve_prijs")},
            {"id": "vasthouden", "titel": "Vasthouden", "icoon": "mdi:lock-clock", "aan": c.hold_on, "stappen": hold_steps, "schakelaar": c.switch_entity("vasthouden")},
            {"id": "geen_verlies", "titel": "Geen verlies", "icoon": "mdi:shield-check", "aan": c.no_loss_enabled, "stappen": no_loss_steps, "schakelaar": c.switch_entity("geen_verlies")},
        ],
    }
