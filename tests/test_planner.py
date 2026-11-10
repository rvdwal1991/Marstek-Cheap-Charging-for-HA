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
        self.assertEqual(result.power_w, 1900)
        self.assertEqual(result.window[0].astimezone(TZ).strftime("%d %H:%M"), "10 23:00")
        self.assertEqual(result.window_end.astimezone(TZ).strftime("%d %H:%M"), "11 07:00")
        self.assertIn("Laden morgen om 02:00, 03:00, 04:00 op ca. 1900 W", result.text)
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
        self.assertEqual(start.power_w, 1900)

        # Onderweg blijven de drie uren staan en blijft het vermogen gelijkmatig.
        halfway = plan("2026-11-11T02:40:00", 38, charging=True, memory=start.memory())
        self.assertEqual(hours(halfway), ["11 02:00", "11 03:00", "11 04:00"])
        self.assertLessEqual(halfway.power_w, 1900)

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
        self.assertLessEqual(result.power_w, 600)


if __name__ == "__main__":
    unittest.main()
