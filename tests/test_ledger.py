"""Tests voor de boekhouding van de gerealiseerde opbrengst."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "ledger", ROOT.parent / "custom_components" / "marstek_goedkoop_laden" / "ledger.py"
)
ledger_module = importlib.util.module_from_spec(SPEC)
sys.modules["ledger"] = ledger_module
SPEC.loader.exec_module(ledger_module)
Ledger = ledger_module.Ledger

TZ = timezone(timedelta(hours=1))
ETA = 0.8


def at(text):
    return datetime.fromisoformat(text + "+01:00")


def step(ledger, when, charged, discharged, price, grid=False, selling=False, export=None, replace=None):
    return ledger.update(
        now=at(when), charged=charged, discharged=discharged, price=price, grid_charging=grid,
        selling=selling, export_price=export, replacement_cost=replace, efficiency=ETA,
    )


class LedgerTest(unittest.TestCase):
    def test_laden_en_later_gebruiken(self):
        ledger = Ledger()
        step(ledger, "2026-11-11T01:59:00", 100.0, 50.0, 0.40)
        # 5 kWh uit het net voor 0,40: 4 kWh bruikbaar, kostprijs 0,50 per kWh.
        for i in range(1, 6):
            step(ledger, f"2026-11-11T02:{i * 10:02d}:00", 100.0 + i, 50.0, 0.40, grid=True)
        self.assertAlmostEqual(ledger.stock_kwh, 4.0)
        self.assertAlmostEqual(ledger.stock_cost, 2.0)
        self.assertAlmostEqual(ledger.stock_price, 0.50)
        self.assertAlmostEqual(ledger.day_gain, 0.0)  # Nog niets verdiend.
        # 1 kWh gebruikt bij 0,70: 0,20 winst.
        step(ledger, "2026-11-11T08:00:00", 105.0, 51.0, 0.70)
        self.assertAlmostEqual(ledger.day_gain, 0.20)
        self.assertAlmostEqual(ledger.stock_kwh, 3.0)
        # 1 kWh gebruikt bij 0,45: 0,05 verlies.
        step(ledger, "2026-11-11T13:00:00", 105.0, 52.0, 0.45)
        self.assertAlmostEqual(ledger.day_gain, 0.15)
        self.assertAlmostEqual(ledger.week_gain, 0.15)

    def test_zonnestroom_telt_niet_mee(self):
        ledger = Ledger()
        step(ledger, "2026-11-11T12:00:00", 100.0, 50.0, 0.30)
        step(ledger, "2026-11-11T12:30:00", 100.8, 50.0, 0.30)  # geladen, maar niet door ons
        step(ledger, "2026-11-11T18:00:00", 100.8, 50.6, 0.60)
        self.assertEqual(ledger.stock_kwh, 0.0)
        self.assertEqual(ledger.day_gain, 0.0)

    def test_laatste_tellerstap_na_het_laden_telt_nog_mee(self):
        ledger = Ledger()
        step(ledger, "2026-11-11T02:00:00", 100.0, 50.0, 0.40, grid=True)
        step(ledger, "2026-11-11T02:30:00", 100.5, 50.0, 0.40, grid=True)
        step(ledger, "2026-11-11T02:31:00", 100.6, 50.0, 0.40, grid=False)
        self.assertAlmostEqual(ledger.day_charged_kwh, 0.6)

    def test_nieuwe_dag_en_week(self):
        ledger = Ledger()
        step(ledger, "2026-11-14T02:00:00", 100.0, 50.0, 0.40, grid=True)  # zaterdag
        step(ledger, "2026-11-14T02:30:00", 101.0, 50.0, 0.40, grid=True)
        step(ledger, "2026-11-14T08:00:00", 101.0, 50.5, 0.70)
        self.assertAlmostEqual(ledger.day_gain, 0.10)
        step(ledger, "2026-11-15T08:00:00", 101.0, 50.5, 0.70)  # zondag: nieuwe dag, zelfde week
        self.assertEqual(ledger.day_gain, 0.0)
        self.assertAlmostEqual(ledger.week_gain, 0.10)
        step(ledger, "2026-11-16T08:00:00", 101.0, 50.5, 0.70)  # maandag: nieuwe week
        self.assertEqual(ledger.week_gain, 0.0)
        self.assertEqual(ledger.week_start, "2026-11-16T00:00:00+01:00")
        # De voorraad blijft over de dag- en weekgrens heen staan.
        self.assertAlmostEqual(ledger.stock_kwh, 0.3)

    def test_tellersprong_wordt_niet_geboekt(self):
        ledger = Ledger()
        step(ledger, "2026-11-11T02:00:00", 100.0, 50.0, 0.40, grid=True)
        step(ledger, "2026-11-11T09:00:00", 104.0, 53.0, 0.40, grid=True)
        self.assertEqual(ledger.stock_kwh, 0.0)
        self.assertEqual(ledger.day_gain, 0.0)
        self.assertEqual(ledger.last_charged, 104.0)

    def test_verkoop(self):
        ledger = Ledger()
        step(ledger, "2026-11-10T16:00:00", 100.0, 50.0, 0.69)
        # 1 kWh zonnestroom verkocht voor 0,69; terugladen kost 0,48.
        step(ledger, "2026-11-10T16:30:00", 100.0, 51.0, 0.69, selling=True, export=0.69, replace=0.48)
        self.assertAlmostEqual(ledger.day_gain, 0.21)
        self.assertAlmostEqual(ledger.day_sold_kwh, 1.0)

    def test_opslaan_en_teruglezen(self):
        ledger = Ledger()
        step(ledger, "2026-11-11T02:00:00", 100.0, 50.0, 0.40, grid=True)
        step(ledger, "2026-11-11T02:30:00", 101.0, 50.0, 0.40, grid=True)
        copy = Ledger.from_dict(ledger.to_dict())
        self.assertEqual(copy, ledger)
        self.assertEqual(Ledger.from_dict({"onbekend": 1}).stock_kwh, 0.0)


if __name__ == "__main__":
    unittest.main()
