"""Tests voor de rekenregel. Draaien met:  python3 -m unittest discover -s tests

De prijzen zijn de echte Zonneplan-uurprijzen van 9-11 november 2026.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import importlib.util
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "planner", ROOT.parent / "custom_components" / "marstek_goedkoop_laden" / "planner.py"
)
planner = importlib.util.module_from_spec(SPEC)
sys.modules["planner"] = planner
SPEC.loader.exec_module(planner)

TZ = timezone(timedelta(hours=1))
PRICES = [
    planner.PriceSlot(datetime.fromisoformat(row["start"]), row["price"])
    for row in json.loads((ROOT / "prijzen_2026_11_10.json").read_text())
]
ETA = planner.clamp_efficiency(1837.74, 1418.82, 0.77)


def at(text: str) -> datetime:
    return datetime.fromisoformat(text + "+01:00")


def plan(now, soc, charging=False, active=True, memory=None, max_power=2500):
    return planner.compute_plan(
        prices=PRICES,
        now=at(now),
        soc=soc,
        capacity_kwh=5.12,
        max_power_w=max_power,
        efficiency=ETA,
        charging=charging,
        active=active,
        memory=memory,
        tz=TZ,
    )


def hours(result):
    return [h.astimezone(TZ).strftime("%d %H:%M") for h in result.charge_hours]


class PlannerTest(unittest.TestCase):
    def test_avond_ervoor_lege_accu(self):
        result = plan("2026-11-10T19:40:00", 12)
        self.assertEqual(result.status, "gepland")
        self.assertEqual(hours(result), ["11 02:00", "11 03:00", "11 04:00"])
        self.assertEqual(result.power_w, 2100)
        self.assertEqual(result.window[0].astimezone(TZ).strftime("%d %H:%M"), "10 23:00")
        self.assertEqual(result.window_end.astimezone(TZ).strftime("%d %H:%M"), "11 07:00")
        self.assertIn("Laden morgen om 02:00, 03:00, 04:00 op ca. 2100 W", result.text)
        self.assertIn("klaar om 05:00", result.text)

    def test_minder_uren_bij_vollere_accu(self):
        self.assertEqual(hours(plan("2026-11-10T19:40:00", 50)), ["11 03:00", "11 04:00"])
        self.assertEqual(hours(plan("2026-11-10T19:40:00", 90)), ["11 03:00"])

    def test_volle_accu_laadt_niet(self):
        result = plan("2026-11-10T19:40:00", 100)
        self.assertEqual(result.status, "vol")
        self.assertEqual(result.charge_hours, ())
        self.assertIsNone(result.power_w)

    def test_verloop_van_de_nacht(self):
        memory = plan("2026-11-11T01:59:00", 12).memory()
        start = plan("2026-11-11T02:00:30", 12, charging=True, memory=memory)
        self.assertEqual(start.status, "laden")
        self.assertEqual(start.power_w, 2100)

        # Onderweg blijven de drie uren staan en blijft het vermogen gelijkmatig.
        halfway = plan("2026-11-11T02:40:00", 38, charging=True, memory=start.memory())
        self.assertEqual(hours(halfway), ["11 02:00", "11 03:00", "11 04:00"])
        self.assertLessEqual(halfway.power_w, 2100)

        later = plan("2026-11-11T04:30:00", 88, charging=True, memory=halfway.memory())
        self.assertEqual(hours(later), ["11 04:00"])
        self.assertLess(later.power_w, 2000)

        # Vol: klaar, tot het einde van het venster, zonder vasthouden.
        full = plan("2026-11-11T04:50:00", 99, charging=True, memory=later.memory())
        self.assertEqual(full.status, "klaar")
        self.assertEqual(full.done_until.astimezone(TZ).strftime("%H:%M"), "07:00")

        # Zakt de SoC daarna door eigen verbruik, dan start hij niet opnieuw.
        again = plan("2026-11-11T05:30:00", 96, memory=full.memory())
        self.assertEqual(again.status, "klaar")
        self.assertEqual(again.charge_hours, ())

    def test_uren_om_is_klaar_ook_als_niet_vol(self):
        memory = plan("2026-11-11T04:59:00", 90, charging=True,
                      memory=planner.PlanMemory("laden", (at("2026-11-11T04:00:00"),),
                                                at("2026-11-11T07:00:00"))).memory()
        result = plan("2026-11-11T05:00:20", 93, charging=True, memory=memory)
        self.assertEqual(result.status, "klaar")

    def test_sturing_uit_raakt_niet_klaar(self):
        memory = planner.PlanMemory("laden", (at("2026-11-11T04:00:00"),), at("2026-11-11T07:00:00"))
        result = plan("2026-11-11T05:00:20", 12, active=False, memory=memory)
        self.assertNotEqual(result.status, "klaar")
        self.assertEqual(result.status, "laden")

    def test_geen_laadmoment_overdag(self):
        result = plan("2026-11-11T08:00:00", 40)
        self.assertEqual(result.status, "geen")
        self.assertEqual(result.charge_hours, ())

    def test_lager_maximum_geeft_meer_uren(self):
        result = plan("2026-11-10T19:40:00", 12, max_power=1200)
        self.assertEqual(len(result.charge_hours), 5)
        self.assertLessEqual(result.power_w, 1200)

    def test_zonder_soc_of_prijzen(self):
        self.assertEqual(plan("2026-11-10T19:40:00", None).status, "onbekend")
        empty = planner.compute_plan(prices=[], now=at("2026-11-10T19:40:00"), soc=50,
                                     capacity_kwh=5.12, max_power_w=2500, efficiency=ETA,
                                     charging=False, active=True)
        self.assertEqual(empty.status, "onbekend")

    def test_vermogen_schiet_niet_omhoog_aan_het_eind(self):
        memory = planner.PlanMemory("laden", (at("2026-11-11T04:00:00"),), at("2026-11-11T07:00:00"))
        result = plan("2026-11-11T04:55:00", 96, charging=True, memory=memory)
        self.assertEqual(result.status, "laden")
        self.assertLessEqual(result.power_w, 1000)


def sell(now, soc, house=150.0, selling=False, previous=(), margin=0.10, factor=1.0, offset=0.0):
    charge = plan(now, soc)
    return planner.compute_sell_plan(
        charge_plan=charge,
        now=at(now),
        soc=soc,
        capacity_kwh=5.12,
        max_power_w=2500,
        efficiency=ETA,
        min_soc=12,
        selling=selling,
        previous_hours=previous,
        params=planner.SellParams(margin=margin, house_power_w=house, price_factor=factor, price_offset=offset),
        tz=TZ,
    )


class SellPlannerTest(unittest.TestCase):
    def test_overschot_in_duurste_uur(self):
        result = sell("2026-11-10T15:10:00", 95)
        self.assertEqual(result.status, "gepland")
        self.assertEqual([h.astimezone(TZ).strftime("%H:%M") for h in result.sell_hours], ["16:00"])
        self.assertGreater(result.energy_kwh, 1.0)
        self.assertIn("Verkopen om 16:00", result.text)
        self.assertIn("terugladen vanaf 03:00", result.text)

    def test_verkoopt_in_het_uur_zelf(self):
        result = sell("2026-11-10T16:05:00", 95)
        self.assertEqual(result.status, "verkopen")
        self.assertLessEqual(result.power_w, 2500)

    def test_geen_overschot_bij_normaal_winterverbruik(self):
        # 400 W huisverbruik tot 03:00 vraagt de hele accu: er valt niets te verkopen.
        result = sell("2026-11-10T16:05:00", 95, house=400.0)
        self.assertEqual(result.status, "geen")
        self.assertIn("geen overschot", result.text)
        self.assertEqual(result.reserve_soc, 100.0)

    def test_reserve_blijft_staan(self):
        result = sell("2026-11-10T16:05:00", 95)
        self.assertGreaterEqual(result.reserve_soc, 15.0)
        self.assertLess(result.energy_kwh, (95 - result.reserve_soc) / 100 * 5.12)

    def test_stopt_op_de_reserve(self):
        first = sell("2026-11-10T16:05:00", 95)
        # De reserve zakt mee met de tijd tot het terugladen; onder de reserve stopt de verkoop.
        later = sell("2026-11-10T16:40:00", 95, selling=True, previous=first.sell_hours)
        self.assertLess(later.reserve_soc, first.reserve_soc)
        low = sell("2026-11-10T16:40:00", later.reserve_soc - 1, selling=True, previous=first.sell_hours)
        self.assertEqual(low.status, "geen")

    def test_opbrengst_te_laag(self):
        result = sell("2026-11-10T16:05:00", 95, margin=0.40)
        self.assertEqual(result.status, "geen")
        self.assertIn("opbrengst is te laag", result.text)

    def test_kale_prijs_na_salderen(self):
        # Na 2027: alleen de kale marktprijs; dan loont verkopen op deze dag niet.
        result = sell("2026-11-10T16:05:00", 95, factor=1 / 1.21, offset=0.108)
        self.assertEqual(result.status, "geen")

    def test_niet_tijdens_of_zonder_laadvenster(self):
        self.assertEqual(sell("2026-11-11T03:10:00", 95).status, "geen")
        self.assertEqual(sell("2026-11-11T12:00:00", 95).status, "geen")
        self.assertEqual(sell("2026-11-10T16:05:00", None).status, "onbekend")

    def test_lopende_verkoop_houdt_zijn_uren(self):
        first = sell("2026-11-10T16:05:00", 95)
        later = sell("2026-11-10T16:30:00", 80, selling=True, previous=first.sell_hours)
        self.assertEqual(later.status, "verkopen")
        self.assertEqual(later.sell_hours, first.sell_hours)


class GainTest(unittest.TestCase):
    def test_bijladen_levert_meer_op_dan_het_kost(self):
        result = plan("2026-11-10T19:40:00", 12)
        self.assertAlmostEqual(result.cost_eur, round(result.energy_kwh * result.average_price, 2), places=2)
        self.assertGreater(result.value_eur, result.cost_eur)
        self.assertAlmostEqual(result.gain_eur, result.value_eur - result.cost_eur, places=2)
        # 5,1 kWh voor ca. € 0,37, later gebruikt tegen ca. € 0,61 x 77 % rendement.
        self.assertGreater(result.gain_eur, 0.3)
        self.assertLess(result.gain_eur, 1.0)

    def test_geen_plan_geen_bedrag(self):
        self.assertIsNone(plan("2026-11-10T19:40:00", 100).gain_eur)

    def test_verkoop_opbrengst(self):
        result = sell("2026-11-10T16:05:00", 95)
        self.assertGreater(result.gain_eur, 0)
        self.assertAlmostEqual(result.gain_eur, result.revenue_eur - result.refill_cost_eur, places=1)
        self.assertIsNone(sell("2026-11-10T16:05:00", 95, house=400.0).gain_eur)


PRICES_15 = [
    planner.PriceSlot(datetime.fromisoformat(row["start"]), row["price"])
    for row in json.loads((ROOT / "prijzen_2026_11_15.json").read_text())
]


def plan15(now, soc, max_power=2500, charging=False, memory=None):
    return planner.compute_plan(
        prices=PRICES_15, now=at(now), soc=soc, capacity_kwh=5.12, max_power_w=max_power,
        efficiency=0.773, charging=charging, active=True, memory=memory,
        params=planner.PlanParams(margin=0.03), tz=TZ,
    )


class WindowGapTest(unittest.TestCase):
    """15 november 2026: 00:00 (0,29) zat net boven de grens en knipte het venster door."""

    def test_een_uur_op_de_grens_knipt_het_venster_niet(self):
        result = plan15("2026-11-15T15:45:00", 11)
        starts = [h.astimezone(TZ).strftime("%H:%M") for h in result.window]
        self.assertEqual(starts[0], "23:00")
        self.assertEqual(starts[-1], "05:00")
        self.assertIn("00:00", starts)  # in het venster, maar niet laadwaardig

    def test_kiest_de_goedkoopste_uren_en_plant_niet_te_veel_in_een_uur(self):
        result = plan15("2026-11-15T15:45:00", 11)
        self.assertEqual(hours(result), ["16 02:00", "16 03:00", "16 04:00"])
        self.assertEqual(result.hours_needed, 3)
        self.assertAlmostEqual(result.energy_kwh, 5.2, delta=0.1)
        self.assertLessEqual(result.power_w, 2500)
        self.assertNotIn("te kort", result.text)

    def test_te_kort_venster_plant_niet_meer_in_dan_er_past(self):
        # Maar twee laadwaardige uren in het venster: niet 5,2 kWh beloven.
        short = [s for s in PRICES_15 if s.start.astimezone(TZ).strftime("%d %H") in
                 ("15 10", "15 11", "15 12", "15 13", "15 14", "15 15", "15 16", "15 17", "15 18",
                  "15 19", "15 20", "15 21", "15 22", "15 23", "16 00", "16 01", "16 02", "16 03")]
        result = planner.compute_plan(
            prices=short, now=at("2026-11-15T15:45:00"), soc=11, capacity_kwh=5.12, max_power_w=1000,
            efficiency=0.773, charging=False, active=True, params=planner.PlanParams(margin=0.03,
            min_lookahead_hours=4), tz=TZ,
        )
        if result.charge_hours:
            self.assertLessEqual(result.energy_kwh, len(result.charge_hours) * 1.0 * 0.9 + 0.01)
            self.assertLessEqual(result.power_w, 1000)

    def test_zeer_laag_maximum_geeft_gedeeltelijk_plan(self):
        result = plan15("2026-11-15T15:45:00", 11, max_power=600)
        self.assertGreaterEqual(len(result.charge_hours), 1)
        self.assertLessEqual(result.energy_kwh, len(result.charge_hours) * 0.6 * 0.9 + 0.01)
        if result.energy_kwh < 5.0:
            self.assertIn("van", result.text)


PRICES_23 = [
    planner.PriceSlot(datetime.fromisoformat(row["start"]), row["price"])
    for row in json.loads((ROOT / "prijzen_2026_11_23.json").read_text())
]


class VlakkeNachtTest(unittest.TestCase):
    """23 november 2026: 02:00, 03:00 en 04:00 verschilden minder dan een halve cent."""

    def test_bijna_gelijke_uren_vallen_niet_af(self):
        result = planner.compute_plan(
            prices=PRICES_23, now=at("2026-11-22T15:45:00"), soc=12, capacity_kwh=5.12,
            max_power_w=2500, efficiency=0.772, charging=False, active=True,
            params=planner.PlanParams(margin=0.03), tz=TZ,
        )
        self.assertEqual(hours(result), ["23 02:00", "23 03:00", "23 04:00"])
        self.assertNotIn("te kort", result.text)


class AfschrijvingTest(unittest.TestCase):
    def test_afschrijving_maakt_bijladen_minder_aantrekkelijk(self):
        def run(dep):
            return planner.compute_plan(
                prices=PRICES_15, now=at("2026-11-15T15:45:00"), soc=11, capacity_kwh=5.12,
                max_power_w=2500, efficiency=0.773, charging=False, active=True,
                params=planner.PlanParams(margin=0.03, depreciation=dep), tz=TZ,
            )
        zonder, met, veel = run(0.0), run(0.03), run(0.2)
        self.assertEqual(len(zonder.charge_hours), 3)
        self.assertLessEqual(len(met.charge_hours), len(zonder.charge_hours))
        self.assertLess(met.gain_eur, zonder.gain_eur)
        self.assertEqual(veel.charge_hours, ())


PRICES_25 = [
    planner.PriceSlot(datetime.fromisoformat(row["start"]), row["price"])
    for row in json.loads((ROOT / "prijzen_2026_11_25.json").read_text())
]


class GatTussenLaaduren(unittest.TestCase):
    """25 november 2026: laden om 22:00, 01:00 en 02:00; na 22:00 ging de status op 'klaar'."""

    def plan(self, now, soc, charging, memory):
        return planner.compute_plan(
            prices=PRICES_25, now=at(now), soc=soc, capacity_kwh=5.12, max_power_w=2500,
            efficiency=0.77, charging=charging, active=True, memory=memory,
            params=planner.PlanParams(margin=0.03), tz=TZ,
        )

    def test_na_een_gat_gaat_de_laadbeurt_door(self):
        first = self.plan("2026-11-25T22:05:00", 13, False, planner.PlanMemory())
        self.assertEqual(hours(first), ["25 22:00", "26 01:00", "26 02:00"])
        memory = planner.PlanMemory(
            status=first.status, charge_hours=first.charge_hours, window_end=first.window_end
        )
        second = self.plan("2026-11-25T23:00:05", 46, False, memory)
        self.assertNotEqual(second.status, planner.STATUS_DONE)
        self.assertTrue(second.charge_hours)
        self.assertTrue(all(h > at("2026-11-25T23:00:05") for h in second.charge_hours))

    def test_na_het_laatste_uur_is_het_klaar(self):
        memory = planner.PlanMemory(
            status=planner.STATUS_CHARGING, charge_hours=(at("2026-11-26T02:00:00"),),
            window_end=at("2026-11-26T06:00:00"),
        )
        result = self.plan("2026-11-26T03:00:05", 97, False, memory)
        self.assertEqual(result.status, planner.STATUS_DONE)


class NegatiefVensterTest(unittest.TestCase):
    """Laden in een venster met negatieve prijzen: de beste uren, uitgesmeerd."""

    @staticmethod
    def slots(prices, start="2026-11-12T12:00:00"):
        first = at(start)
        return [planner.PriceSlot(first + timedelta(hours=i), p) for i, p in enumerate(prices)]

    def run_plan(self, prices, now, soc, previous=(), max_gain=False):
        return planner.plan_negative(
            self.slots(prices), at(now), soc, capacity_kwh=5.12, max_power_w=2500,
            min_power_w=400, limit=0.0, previous=previous, max_gain=max_gain,
        )

    def test_geen_negatief_uur_geen_plan(self):
        self.assertIsNone(self.run_plan([0.2, 0.1, 0.3], "2026-11-12T12:10:00", 40))

    def test_voorbeeld_weinig_opbrengend_uur_valt_af(self):
        # -0,03, -0,20, -0,12 en accu op 40 %: 3,1 kWh. Het eerste uur zou onder het
        # minimale vermogen blijven en valt af.
        prices = [0.30, -0.03, -0.20, -0.12, 0.25]
        result = self.run_plan(prices, "2026-11-12T13:00:05", 40)
        self.assertEqual(result.status, planner.NEGATIVE_WAITING)
        self.assertEqual(result.hours, (at("2026-11-12T14:00:00"), at("2026-11-12T15:00:00")))
        self.assertIsNone(result.power_w)
        result = self.run_plan(prices, "2026-11-12T14:00:05", 40)
        self.assertEqual(result.status, planner.NEGATIVE_CHARGING)
        self.assertEqual(len(result.window), 3)
        # Verdeeld naar waarde: het beste uur (-0,20) krijgt meer dan het andere (-0,12).
        first, second = result.allocation[at("2026-11-12T14:00:00")], result.allocation[at("2026-11-12T15:00:00")]
        self.assertAlmostEqual(first / second, 0.20 / 0.12, delta=0.05)
        self.assertAlmostEqual(first + second, 3.07, delta=0.02)
        self.assertGreater(result.gain, 3.07 * 0.16)  # beter dan gelijk verdelen
        self.assertTrue(1500 <= result.power_w < 2500)
        self.assertIn("in 2 van 2 negatieve uren", result.text)

    def test_energie_naar_waarde_van_de_uren(self):
        result = self.run_plan([-0.10, -0.30], "2026-11-12T12:00:05", 50)
        low, high = result.allocation[at("2026-11-12T12:00:00")], result.allocation[at("2026-11-12T13:00:00")]
        self.assertAlmostEqual(high / low, 3.0, delta=0.05)

    def test_uur_dat_te_vol_zit_wordt_op_vol_vermogen_geladen(self):
        # Een enkel negatief uur dat de accu niet kan vullen: vol vermogen.
        result = self.run_plan([-0.2], "2026-11-12T12:10:00", 40)
        self.assertEqual(result.power_w, 2500)

    def test_maximale_opbrengst_vult_het_beste_uur_eerst(self):
        prices = [0.30, -0.03, -0.20, -0.12, 0.25]
        # 13:00 (-0,03) wordt overgeslagen.
        result = self.run_plan(prices, "2026-11-12T13:00:05", 40, max_gain=True)
        self.assertEqual(result.status, planner.NEGATIVE_WAITING)
        # 14:00 (-0,20): vol vermogen, 2,25 kWh; de rest (0,82 kWh) naar -0,12.
        result = self.run_plan(prices, "2026-11-12T14:00:00", 40, max_gain=True)
        self.assertEqual(result.status, planner.NEGATIVE_CHARGING)
        self.assertEqual(result.power_w, 2500)
        self.assertAlmostEqual(result.allocation[at("2026-11-12T14:00:00")], 2.25, delta=0.01)
        self.assertAlmostEqual(result.allocation[at("2026-11-12T15:00:00")], 3.072 - 2.25, delta=0.02)
        by_value = self.run_plan(prices, "2026-11-12T14:00:00", 40)
        self.assertGreater(result.gain, by_value.gain)  # 0,55 tegen 0,52
        # Het laatste uur krijgt het restje op een lager vermogen.
        late = self.run_plan(prices, "2026-11-12T15:00:00", 84, max_gain=True)  # nog 0,8 kWh
        self.assertLess(late.power_w, 1500)

    def test_lege_accu_gebruikt_alle_uren(self):
        prices = [-0.03, -0.20, -0.12]
        result = self.run_plan(prices, "2026-11-12T12:00:05", 5)
        self.assertEqual(len(result.hours), 3)
        self.assertEqual(result.status, planner.NEGATIVE_CHARGING)

    def test_volle_accu(self):
        result = self.run_plan([-0.1, -0.2], "2026-11-12T12:10:00", 99)
        self.assertEqual(result.status, planner.NEGATIVE_FULL)

    def test_eerder_gekozen_uur_krijgt_speling_bij_minimaal_vermogen(self):
        prices = [-0.04, -0.20]
        first = at("2026-11-12T12:00:00")
        result = self.run_plan(prices, "2026-11-12T12:00:05", 60)
        self.assertNotIn(first, result.hours)  # ~340 W is onder het minimum
        result = self.run_plan(prices, "2026-11-12T12:00:05", 60, previous=(first,))
        self.assertIn(first, result.hours)


class ZonneverwachtingTest(unittest.TestCase):
    """De zon vult de accu overdag bij, dus 's nachts hoeft er minder uit het net."""

    @staticmethod
    def sun(day, per_hour_wh, hours=range(9, 17)):
        return tuple((at(f"{day}T{h:02d}:00:00"), per_hour_wh) for h in hours)

    def run_plan(self, soc, solar, factor=1.0):
        return planner.compute_plan(
            prices=PRICES, now=at("2026-11-10T19:40:00"), soc=soc, capacity_kwh=5.12,
            max_power_w=2500, efficiency=ETA, charging=False, active=True,
            params=planner.PlanParams(solar=solar, solar_factor=factor, house_power_w=400),
            tz=TZ,
        )

    def test_zonder_verwachting_volledig_bijladen(self):
        base = self.run_plan(12, ())
        self.assertGreater(base.energy_kwh, 4.5)
        self.assertEqual(base.solar_kwh, 0)

    def test_veel_zon_laat_ruimte_over(self):
        result = self.run_plan(12, self.sun("2026-11-11", 3000))
        self.assertGreater(result.solar_kwh, 5)
        # Genoeg zon om de hele accu bij te vullen: alleen het eigen verbruik tot de
        # zon opkomt wordt bijgeladen (een paar kWh minder dan vol).
        base = self.run_plan(12, ())
        self.assertLess(result.energy_kwh, base.energy_kwh - 1.5)
        self.assertIn("de zon vult de rest bij", result.text)
        self.assertTrue(any(step["titel"] == "Zon verwacht" for step in result.steps))

    def test_weinig_zon_verandert_niets(self):
        base = self.run_plan(12, ())
        result = self.run_plan(12, self.sun("2026-11-11", 350))  # onder het eigen verbruik
        self.assertEqual(result.energy_kwh, base.energy_kwh)
        self.assertEqual(result.solar_kwh, 0)

    def test_betrouwbaarheid_dempt_de_verwachting(self):
        sunny = self.run_plan(12, self.sun("2026-11-11", 1200), factor=1.0)
        careful = self.run_plan(12, self.sun("2026-11-11", 1200), factor=0.5)
        self.assertLess(sunny.energy_kwh, careful.energy_kwh)

    def test_accu_al_genoeg_gevuld_voor_het_zonne_overschot(self):
        # Accu op 60 % en veel zon: niets bijladen, de zon doet het.
        result = self.run_plan(60, self.sun("2026-11-11", 3000))
        self.assertEqual(result.status, planner.STATUS_FULL)
        self.assertEqual(result.charge_hours, ())
        self.assertIn("De zon vult de accu bij", result.text)


if __name__ == "__main__":
    unittest.main()
