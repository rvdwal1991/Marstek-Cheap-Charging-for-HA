"""De Engelse vertaling van plan en stroomschema laat geen Nederlandse woorden over."""
import importlib.util
import pathlib
import re
import unittest

_spec = importlib.util.spec_from_file_location(
    "i18n", pathlib.Path(__file__).parent.parent / "custom_components/marstek_goedkoop_laden/i18n.py"
)
i18n = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(i18n)

DUTCH = re.compile(
    r"\b(geen|niet|accu|laden|bijladen|verkop\w*|prijs|nodig|uur|vol|klaar|tot|boven|onder|"
    r"voorraad|ontladen|vasthouden|staat|uit|nog|kostprijs|vermogen|zelf|regelt|regel)\b",
    re.IGNORECASE,
)


class TranslateTest(unittest.TestCase):
    def test_dutch_is_unchanged(self):
        self.assertEqual(i18n.tr("nl", "Geen verkoop"), "Geen verkoop")
        self.assertEqual(i18n.tr(None, "Geen verkoop"), "Geen verkoop")

    def test_sentences(self):
        self.assertEqual(
            i18n.tr("en", "Laden morgen om 02:00, 03:00 op ca. 2100 W (5,2 kWh, gem. € 0,26) · klaar om 04:00"),
            "Charging tomorrow at 02:00, 03:00 at approx. 2100 W (5.2 kWh, avg. € 0.26) · done at 04:00",
        )
        self.assertEqual(i18n.tr("en", "Nog 5,2 kWh nodig"), "5.2 kWh still needed")

    def test_structures_keep_identifiers(self):
        flow = {"banen": [{"titel": "Bijladen", "icoon": "mdi:x", "stappen": [{"titel": "Accu is vol", "soort": "stop"}]}]}
        out = i18n.tr("en", flow)
        self.assertEqual(out["banen"][0]["titel"], "Charging")
        self.assertEqual(out["banen"][0]["icoon"], "mdi:x")
        self.assertEqual(out["banen"][0]["stappen"][0]["soort"], "stop")
        self.assertEqual(out["banen"][0]["stappen"][0]["titel"], "Battery is full")

    def test_coordinator_texts_have_no_dutch_left(self):
        src = (pathlib.Path(__file__).parent.parent / "custom_components/marstek_goedkoop_laden")
        strings = set()
        for name in ("planner.py", "coordinator.py"):
            text = (src / name).read_text()
            for line in text.splitlines():
                if re.search(r"step\(|text=|\"titel\"|detail|doing = |kind", line):
                    strings.update(re.findall(r'"([A-Z][^"\n{}]{3,})"', line))
        leftovers = []
        for s in sorted(strings):
            if " " not in s or s.startswith(("Het ", "De ", "Een ", "Bereken", "Eén")):
                continue
            out = i18n.tr("en", s)
            if DUTCH.search(out):
                leftovers.append((s, out))
        self.assertEqual(leftovers, [])


if __name__ == "__main__":
    unittest.main()
