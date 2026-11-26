"""Alle talen zijn compleet: tabellen, kaartteksten, vertaalbestand en README."""
import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parent.parent
INTEGRATION = ROOT / "custom_components" / "marstek_goedkoop_laden"
LANGS = ("fy", "de", "fr", "es", "sv", "nb")


def keys(tree, prefix=""):
    if isinstance(tree, dict):
        for key, value in tree.items():
            yield from keys(value, f"{prefix}.{key}")
    else:
        yield prefix


def placeholders(text):
    return sorted(re.findall(r"\{[a-z_]+\}", text))


class LanguageTest(unittest.TestCase):
    def test_i18n_tables(self):
        en = json.loads((INTEGRATION / "i18n_langs" / "en.json").read_text())
        for code in LANGS:
            with self.subTest(code):
                data = json.loads((INTEGRATION / "i18n_langs" / f"{code}.json").read_text())
                self.assertEqual([p[0] for p in data["phrases"]], [p[0] for p in en["phrases"]])
                # een fragment dat in het Engels leeg is (bijv. "Nog ") mag leeg blijven
                empty_en = {p[0] for p in en["phrases"] if not p[1].strip()}
                self.assertTrue(all(p[1].strip() or p[0] in empty_en for p in data["phrases"]))
                self.assertEqual(len(data["pre"]), len(en["pre"]))
                for (src, dst), (src_en, _) in zip(data["pre"], en["pre"]):
                    self.assertEqual(src, src_en)  # dezelfde Nederlandse patronen
                    re.compile(src)
                    # dezelfde groepen terug in de vertaling
                    groups = re.findall(r"\\(\d)", dst)
                    self.assertEqual(sorted(groups), sorted(re.findall(r"\\(\d)", dict(en["pre"])[src])))
                # alleen het uur-patroon, geen decimale punt (komma blijft komma)
                self.assertEqual(len(data["post"]), 1)
                self.assertEqual(data["post"][0][0], en["post"][0][0])
                self.assertEqual(set(data["card"]), set(en["card"]))
                for nl, text in data["card"].items():
                    self.assertTrue(text.strip(), nl)
                    self.assertEqual(placeholders(text), placeholders(nl), nl)

    def test_home_assistant_translations(self):
        en = json.loads((INTEGRATION / "translations" / "en.json").read_text())
        for code in LANGS:
            with self.subTest(code):
                data = json.loads((INTEGRATION / "translations" / f"{code}.json").read_text())
                self.assertEqual(sorted(keys(data)), sorted(keys(en)))

    def test_readme(self):
        en = (ROOT / "README.md").read_text()

        def shape(text):
            return (
                len(re.findall(r"^#{1,3} ", text, re.M)),
                text.count("```"),
                len(re.findall(r"^\|", text, re.M)),
                len(re.findall(r"https?://", text)),
            )

        for code in LANGS:
            with self.subTest(code):
                text = (ROOT / f"README.{code}.md").read_text()
                self.assertEqual(shape(text), shape(en))
                self.assertIn("my.home-assistant.io/redirect/hacs_repository", text)


if __name__ == "__main__":
    unittest.main()
