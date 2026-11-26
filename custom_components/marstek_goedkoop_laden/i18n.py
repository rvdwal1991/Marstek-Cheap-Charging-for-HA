"""Vertaling van de leesbare teksten (plan, stroomschema) naar andere talen.

De planner en de coördinator schrijven hun teksten in het Nederlands. Staat de taal
van de integratie op iets anders dan Nederlands, dan worden de teksten hier vlak
voor het tonen vertaald met de tabel in ``i18n_langs/<taal>.json``. De
statuswaarden en attribuutnamen blijven ongewijzigd.
"""
from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Any

#: Beschikbare talen (Nederlands is de brontaal).
LANGUAGES = ("nl", "en", "fy", "de", "fr", "es", "sv", "nb")
# Taalcodes die naar een beschikbare taal verwijzen.
_ALIASES = {"no": "nb", "nn": "nb"}

_DIR = Path(__file__).parent / "i18n_langs"


class _Table:
    """Zinsdelen en getalpatronen van één taal."""

    def __init__(self, data: dict[str, Any]) -> None:
        # Langste zinsdelen eerst, zodat een kort woord een lange zin niet verknipt.
        self.phrases = sorted(
            ((nl, text) for nl, text in data["phrases"] if nl), key=lambda pair: len(pair[0]), reverse=True
        )
        self.pre = [(re.compile(p), r) for p, r in data["pre"]]
        self.post = [(re.compile(p), r) for p, r in data["post"]]
        self.cache: dict[str, str] = {}


def _load() -> dict[str, _Table]:
    tables: dict[str, _Table] = {}
    for code in LANGUAGES:
        path = _DIR / f"{code}.json"
        if code != "nl" and path.exists():
            tables[code] = _Table(json.loads(path.read_text(encoding="utf-8")))
    return tables


_TABLES = _load()


def resolve(language: str | None) -> str:
    """De taalcode die gebruikt wordt: een beschikbare taal, anders Engels."""
    code = (language or "nl").lower().replace("_", "-")
    for candidate in (code, code.split("-")[0]):
        candidate = _ALIASES.get(candidate, candidate)
        if candidate in LANGUAGES:
            return candidate
    return "en"


def _translate(table: _Table, text: str) -> str:
    cached = table.cache.get(text)
    if cached is not None:
        return cached
    result = text
    for pattern, repl in table.pre:
        result = pattern.sub(repl, result)
    # Vervang de zinsdelen via één doorloop zodat een vertaling niet opnieuw wordt vertaald.
    pieces: list[str] = []
    index = 0
    while index < len(result):
        for nl, translated in table.phrases:
            if result.startswith(nl, index) and _word_edge(result, index, nl):
                pieces.append(translated)
                index += len(nl)
                break
        else:
            pieces.append(result[index])
            index += 1
    result = "".join(pieces)
    for pattern, repl in table.post:
        result = pattern.sub(repl, result)
    if len(table.cache) < 2000:
        table.cache[text] = result
    return result


def _word_edge(text: str, index: int, phrase: str) -> bool:
    """Vervang alleen hele woorden, niet delen van een woord."""
    if text[index].isalpha() and index > 0 and text[index - 1].isalpha():
        return False
    end = index + len(phrase)
    if phrase[-1].isalpha() and end < len(text) and text[end].isalpha():
        return False
    return True


def is_dutch(language: str | None) -> bool:
    return resolve(language) == "nl"


def tr(language: str | None, value: Any, skip: tuple[str, ...] = ("icoon", "soort", "schakelaar", "id", "status", "start")) -> Any:
    """Vertaal een tekst, of alle teksten in een lijst of woordenboek."""
    code = resolve(language)
    if code == "nl":
        return value
    return _tr(_TABLES.get(code) or _TABLES["en"], value, skip)


def _tr(table: _Table, value: Any, skip: tuple[str, ...]) -> Any:
    if isinstance(value, str):
        return _translate(table, value)
    if isinstance(value, dict):
        return {k: (v if k in skip else _tr(table, v, skip)) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_tr(table, v, skip) for v in value]
    return value
