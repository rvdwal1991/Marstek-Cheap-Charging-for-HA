"""Het geleerde verbruik van het huis per uur."""
import importlib.util
from datetime import datetime, timedelta, timezone
from pathlib import Path
import unittest

_spec = importlib.util.spec_from_file_location(
    "house", Path(__file__).parent.parent / "custom_components/marstek_goedkoop_laden/house.py"
)
house = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(house)

TZ = timezone(timedelta(hours=1))


def at(text):
    return datetime.fromisoformat(text + "+01:00")


class HouseProfileTest(unittest.TestCase):
    def feed(self, profile, day, hour, watts, minutes=60):
        for minute in range(minutes):
            profile.sample(at(f"{day}T{hour:02d}:{minute:02d}:00"), watts)

    def test_leert_het_uurgemiddelde(self):
        profile = house.HouseProfile()
        self.feed(profile, "2026-11-12", 12, 600)  # donderdag
        self.assertIsNone(profile.at(at("2026-11-12T12:30:00")))  # uur is nog niet afgesloten
        profile.sample(at("2026-11-12T13:00:00"), 100)
        self.assertEqual(profile.at(at("2026-11-12T12:30:00")), 600)
        self.assertEqual(profile.learned(), 1)

    def test_werkdag_en_weekend_apart(self):
        profile = house.HouseProfile()
        self.feed(profile, "2026-11-12", 12, 300)  # donderdag
        self.feed(profile, "2026-11-14", 12, 900)  # zaterdag
        profile.sample(at("2026-11-14T13:00:00"), 0)
        self.assertEqual(profile.at(at("2026-11-12T12:00:00")), 300)
        self.assertEqual(profile.at(at("2026-11-14T12:00:00")), 900)

    def test_nieuw_uur_telt_met_gewicht(self):
        profile = house.HouseProfile()
        self.feed(profile, "2026-11-12", 12, 400)
        self.feed(profile, "2026-11-19", 12, 800)  # een week later
        profile.sample(at("2026-11-19T13:00:00"), 0)
        self.assertAlmostEqual(profile.at(at("2026-11-12T12:00:00")), 400 * 0.85 + 800 * 0.15, delta=1)

    def test_piek_wordt_afgekapt_en_te_weinig_metingen_tellen_niet(self):
        profile = house.HouseProfile()
        self.feed(profile, "2026-11-12", 8, 11000)  # laadpaal
        self.feed(profile, "2026-11-12", 9, 500, minutes=5)  # te weinig metingen
        profile.sample(at("2026-11-12T10:00:00"), 0)
        self.assertEqual(profile.at(at("2026-11-12T08:00:00")), house.CLIP_W)
        self.assertIsNone(profile.at(at("2026-11-12T09:00:00")))

    def test_bewaren(self):
        profile = house.HouseProfile()
        self.feed(profile, "2026-11-12", 12, 450)
        profile.sample(at("2026-11-12T13:00:00"), 0)
        again = house.HouseProfile.from_dict(profile.to_dict())
        self.assertEqual(again.table(), profile.table())
        self.assertEqual(house.HouseProfile.from_dict({"watts": [1]}).learned(), 0)
        self.assertEqual(house.HouseProfile.from_dict(None).learned(), 0)


if __name__ == "__main__":
    unittest.main()
