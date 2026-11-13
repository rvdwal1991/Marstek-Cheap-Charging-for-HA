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


if __name__ == "__main__":
    unittest.main()
