"""De zonneverwachting leert van de werkelijke opbrengst."""
import importlib.util
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import unittest

_spec = importlib.util.spec_from_file_location(
    "calibration", Path(__file__).parent.parent / "custom_components/marstek_goedkoop_laden/calibration.py"
)
calibration = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(calibration)

TZ = timezone(timedelta(hours=1))


def at(text):
    return datetime.fromisoformat(text + "+01:00")


def local(moment):
    return moment.astimezone(TZ)


def sun(day, wh_per_hour, hours=range(9, 16)):
    return tuple((at(f"{day}T{h:02d}:00:00"), float(wh_per_hour)) for h in hours)


class CalibrationTest(unittest.TestCase):
    def day(self, cal, day, forecast_wh, produced_kwh, total_start=1000.0):
        """Eén volledige dag: voorspelling de avond ervoor, productie vanaf middernacht."""
        before = date.fromisoformat(day) - timedelta(days=1)
        cal.record_forecast(before, sun(day, forecast_wh), local)
        cal.record_production(at(f"{day}T00:30:00"), total_start)
        cal.record_production(at(f"{day}T23:50:00"), total_start + produced_kwh)

    def test_geen_factor_zonder_dagen(self):
        self.assertIsNone(calibration.SolarCalibration().factor())

    def test_leert_de_mediaan_van_de_verhouding(self):
        cal = calibration.SolarCalibration()
        total = 1000.0
        # voorspeld 7 x 700 Wh = 4,9 kWh; geleverd 2,0 kWh -> 0,41
        for i, day in enumerate(("2026-11-10", "2026-11-11", "2026-11-12", "2026-11-13")):
            self.day(cal, day, 700, 2.0, total)
            total += 2.0
        cal.record_production(at("2026-11-14T00:30:00"), total)  # sluit de laatste dag af
        self.assertEqual(len(cal.ratios), 4)
        self.assertAlmostEqual(cal.factor(), 2.0 / 4.9, delta=0.01)

    def test_te_weinig_dagen_geen_factor(self):
        cal = calibration.SolarCalibration()
        self.day(cal, "2026-11-10", 700, 2.0)
        self.day(cal, "2026-11-11", 700, 2.0)
        cal.record_production(at("2026-11-12T00:30:00"), 1004.0)
        self.assertEqual(len(cal.ratios), 2)
        self.assertIsNone(cal.factor())

    def test_halve_dag_telt_niet_mee(self):
        cal = calibration.SolarCalibration()
        cal.record_forecast(date(2026, 11, 10), sun("2026-11-11", 700), local)
        cal.record_production(at("2026-11-11T11:00:00"), 1000.0)  # eerste meting na zonsopkomst
        cal.record_production(at("2026-11-11T23:50:00"), 1001.0)
        cal.record_production(at("2026-11-12T00:30:00"), 1001.0)
        self.assertEqual(cal.ratios, [])

    def test_dag_met_bijna_geen_voorspelling_telt_niet_mee(self):
        cal = calibration.SolarCalibration()
        self.day(cal, "2026-11-10", 20, 0.0)  # 0,14 kWh voorspeld
        cal.record_production(at("2026-11-11T00:30:00"), 1000.0)
        self.assertEqual(cal.ratios, [])

    def test_voorspelling_van_een_begonnen_dag_blijft_staan(self):
        cal = calibration.SolarCalibration()
        cal.record_forecast(date(2026, 11, 9), sun("2026-11-10", 700), local)
        first = cal.forecast["2026-11-10"]
        cal.record_forecast(date(2026, 11, 10), sun("2026-11-10", 100), local)  # vandaag: niet meer aanpassen
        self.assertEqual(cal.forecast["2026-11-10"], first)

    def test_factor_wordt_begrensd(self):
        cal = calibration.SolarCalibration()
        cal.ratios = [0.02, 0.03, 0.04]
        self.assertEqual(cal.factor(), calibration.MIN_FACTOR)
        cal.ratios = [1.4, 1.3, 1.5]
        self.assertEqual(cal.factor(), calibration.MAX_FACTOR)

    def test_bewaren_en_herstellen(self):
        cal = calibration.SolarCalibration()
        self.day(cal, "2026-11-10", 700, 2.0)
        cal.ratios = [0.4, 0.5, 0.3]
        again = calibration.SolarCalibration.from_dict(cal.to_dict())
        self.assertEqual(again.ratios, cal.ratios)
        self.assertEqual(again.forecast, cal.forecast)
        self.assertEqual(again.factor(), cal.factor())
        self.assertIsNone(calibration.SolarCalibration.from_dict({"ratios": "kapot"}).factor())


if __name__ == "__main__":
    unittest.main()
