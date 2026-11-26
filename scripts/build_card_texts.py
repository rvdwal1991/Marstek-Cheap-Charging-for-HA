#!/usr/bin/env python3
"""Zet de kaarttteksten uit i18n_langs/*.json in de JavaScript van de kaart.

Draaien na elke wijziging van een vertaling:  python3 scripts/build_card_texts.py
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "custom_components" / "marstek_goedkoop_laden"
CARD = ROOT / "frontend" / "marstek-goedkoop-laden-card.js"
BEGIN, END = "// <texts:begin>\n", "// <texts:end>\n"


def main() -> None:
    texts = {}
    for path in sorted((ROOT / "i18n_langs").glob("*.json")):
        texts[path.stem] = json.loads(path.read_text(encoding="utf-8"))["card"]
    body = "const TEXTS = " + json.dumps(texts, ensure_ascii=False, indent=2) + ";\n"
    source = CARD.read_text(encoding="utf-8")
    start = source.index(BEGIN) + len(BEGIN)
    stop = source.index(END)
    CARD.write_text(source[:start] + body + source[stop:], encoding="utf-8")
    print("kaarttekst voor:", ", ".join(texts))


if __name__ == "__main__":
    main()
