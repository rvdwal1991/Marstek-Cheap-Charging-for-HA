"""Vertaling van de leesbare teksten (plan, stroomschema) naar het Engels.

De planner en de coördinator schrijven hun teksten in het Nederlands. Staat Home
Assistant op een andere taal dan Nederlands, dan worden de teksten hier vlak voor
het tonen vertaald. De statuswaarden en attribuutnamen blijven ongewijzigd.
"""
from __future__ import annotations

import re
from typing import Any

# (Nederlands, Engels). Gedeelten tussen {} zijn getallen of tijden en blijven staan.
# Langste zinsdelen eerst: dat gebeurt hieronder automatisch.
_PHRASES: list[tuple[str, str]] = [
    # --- laadplan
    ("Geen laadmoment in de gepubliceerde prijzen (prijsverschil te klein, of morgen is nog niet bekend)",
     "No charge moment in the published prices (price difference too small, or tomorrow is not known yet)"),
    ("Bijladen is klaar · de Marstek regelt weer zelf (anti-feed)",
     "Charging done · the Marstek regulates itself again (anti-feed)"),
    ("Accu is vol · bijladen is niet nodig", "Battery is full · charging not needed"),
    (" · het goedkope venster is te kort om vol te komen", " · the cheap window is too short to fill up"),
    ("Prijsverschil te klein of morgen onbekend", "Price difference too small or tomorrow unknown"),
    ("Geen prijzen of SoC beschikbaar", "No prices or SoC available"),
    ("Niet in de gepubliceerde prijzen", "Not in the published prices"),
    ("Prijzen en SoC bekend", "Prices and SoC known"),
    ("Geen goedkoop venster", "No cheap window"),
    ("Goedkoop venster", "Cheap window"),
    ("In dit goedkope venster", "In this cheap window"),
    ("Bijladen is niet nodig", "Charging not needed"),
    ("Wacht op gegevens", "Waiting for data"),
    ("Geen bijladen gepland", "No charging planned"),
    ("Geen bijladen", "No charging"),
    ("Accu niet vol", "Battery not full"),
    ("Accu is vol", "Battery is full"),
    ("Laadbeurt gedaan", "Charge done"),
    ("Geen nieuwe start tot", "No new start until"),
    ("Stopt bij deze stap", "Stops at this step"),
    ("Klaar", "Done"),
    # --- verkoopplan
    ("Verkopen is niet ingesteld: kies de entiteit voor het ontlaadvermogen",
     "Selling is not set up: choose the entity for the discharge power"),
    ("Geen verkoop: er is nog geen goedkoop laadvenster bekend", "No selling: no cheap charge window known yet"),
    ("Geen verkoop: het goedkope laadvenster loopt", "No selling: the cheap charge window is running"),
    ("Geen verkoop: de opbrengst is te laag", "No selling: revenue is too low"),
    ("Geen verkoop: geen overschot boven de reserve van", "No selling: no surplus above the reserve of"),
    ("Nog geen goedkoop laadvenster", "No cheap charge window yet"),
    ("Geen laadbeurt bekend", "No charge known"),
    ("Laadvenster loopt nu", "Charge window is running"),
    ("Stroom is nu goedkoop", "Electricity is cheap now"),
    ("Laadbeurt komt eraan", "Charge coming up"),
    ("Opbrengst hoog genoeg", "Revenue high enough"),
    ("Opbrengst te laag", "Revenue too low"),
    ("Overschot boven reserve", "Surplus above reserve"),
    ("Geen overschot", "No surplus"),
    ("Geen verkoop gepland", "No selling planned"),
    ("Geen verkoop", "No selling"),
    ("Geen uren", "No hours"),
    ("Reserve is", "Reserve is"),
    # --- stroomschema (coordinator)
    ("Laden op vol vermogen (negatieve prijs)", "Charging at full power (negative price)"),
    ("Negatieve prijs (", "Negative price ("),
    ("laden op vol vermogen", "charging at full power"),
    ("Laden op vol vermogen", "Charging at full power"),
    ("Bijladen uit het net", "Charging from the grid"),
    ("Verkopen aan het net", "Selling to the grid"),
    ("Ontladen (handmatig)", "Discharging (manual)"),
    ("Stilgezet (handmatig)", "Stopped (manual)"),
    ("Marstek niet bereikbaar", "Marstek not reachable"),
    ("Vasthouden: ontladen geblokkeerd", "Hold: discharging blocked"),
    ("Zelf regelen (anti-feed)", "Self-regulating (anti-feed)"),
    ("Wordt niet uitgevoerd: bijladen staat uit", "Not carried out: charging is off"),
    ("Wordt niet uitgevoerd: verkopen staat uit", "Not carried out: selling is off"),
    ("ontladen vrij", "discharging released"),
    ("Prijs komt boven de kostprijs van", "Price rises above the cost price of"),
    ("Geen acties gepland", "No actions planned"),
    ("De Marstek blijft zelf regelen", "The Marstek keeps regulating itself"),
    ("Weer zelf regelen (anti-feed)", "Regulating itself again (anti-feed)"),
    ("Prijs onder de grens", "Price below the limit"),
    ("Laden op vol vermogen", "Charging at full power"),
    ("Niets te laden", "Nothing to charge"),
    ("Niet actief", "Not active"),
    ("Wacht op een negatief uur", "Waiting for a negative hour"),
    ("Prijs niet onder", "Price not below"),
    ("Prijs onbekend", "Price unknown"),
    ("Niet ingesteld", "Not set up"),
    ("Kies de entiteit voor het maximale ontlaadvermogen", "Choose the entity for the maximum discharge power"),
    ("Kies de entiteit voor het ontlaadvermogen", "Choose the entity for the discharge power"),
    ("Geen bijgeladen voorraad", "No charged stock"),
    ("Niets om vast te houden", "Nothing to hold"),
    ("De Marstek regelt zelf", "The Marstek regulates itself"),
    ("Bijgeladen voorraad", "Charged stock"),
    ("kostprijs €", "cost price €"),
    ("Tot de prijs boven", "Until the price is above"),
    (" komt", ""),
    ("Prijs onder kostprijs", "Price below cost price"),
    ("Prijs niet onder kostprijs", "Price not below cost price"),
    ("Ontladen geblokkeerd", "Discharging blocked"),
    ("Ontladen vrij", "Discharging released"),
    ("De voorraad wordt met winst gebruikt", "The stock is used at a profit"),
    ("Voorraad bewaakt", "Stock guarded"),
    ("alleen boven", "only above"),
    ("Geen voorraad", "No stock"),
    ("Nu niets te bewaken", "Nothing to guard now"),
    ("Ontladen boven kostprijs", "Discharging above cost price"),
    ("Vasthouden geldt altijd", "Hold always applies"),
    ("Verkopen boven kostprijs", "Selling above cost price"),
    ("Nooit onder de kostprijs", "Never below the cost price"),
    ("Onder de kostprijs", "Below the cost price"),
    ("Voorraad kost", "Stock costs"),
    ("Tegengehouden door geen verlies", "Blocked by no loss"),
    ("Verkopen ingesteld", "Selling set up"),
    ("Staat uit", "Off"),
    ("Bijladen", "Charging"),
    ("Vasthouden", "Hold"),
    ("Negatieve prijs", "Negative price"),
    ("Geen verlies", "No loss"),
    ("verkopen voor", "sell for"),
    ("terugladen kost", "recharging costs"),
    # --- losse woorden en zinsdelen
    ("Terugladen vanaf", "Recharging from"),
    ("terugladen vanaf", "recharging from"),
    ("Nog ", ""),  # zie _REGEX: "Nog X kWh nodig"
    ("nodig", "needed"),
    ("hoogste", "highest"),
    ("gemiddeld", "average"),
    ("gem.", "avg."),
    ("voor ca.", "for approx."),
    ("op ca.", "at approx."),
    ("Ca.", "Approx."),
    ("boven reserve", "above reserve"),
    ("boven", "above"),
    ("Verkoop", "Selling"),
    ("Verkopen", "Selling"),
    ("verkopen", "selling"),
    ("bijladen", "charging"),
    ("Laden", "Charging"),
    ("klaar om", "done at"),
    ("klaar", "done"),
    ("morgen ", "tomorrow "),
    ("Tot ", "Until "),
    ("om ", "at "),
    (" van ", " of "),
    ("Nu", "Now"),
    ("Geen", "No"),
]

# Zinsdelen met een getal ervoor of erna.
_REGEX: list[tuple[str, str]] = [
    (r"Nog (\S+) kWh nodig", r"\1 kWh still needed"),
    (r"inkopen voor (€ \S+), later (€ \S+) waard", r"buy for \1, worth \2 later"),
    (r"(\d+) uur\b", r"\1 h"),
    (r"(\d),(\d)", r"\1.\2"),
]

_ORDERED = sorted(_PHRASES, key=lambda pair: len(pair[0]), reverse=True)
_CACHE: dict[str, str] = {}


def _translate(text: str) -> str:
    cached = _CACHE.get(text)
    if cached is not None:
        return cached
    result = text
    for pattern, repl in _REGEX[:2]:
        result = re.sub(pattern, repl, result)
    # Vervang de zinsdelen via één doorloop zodat een vertaling niet opnieuw wordt vertaald.
    marker = "\x00"
    pieces: list[str] = []
    index = 0
    lowered = result
    while index < len(lowered):
        for nl, en in _ORDERED:
            if nl and lowered.startswith(nl, index) and _word_edge(lowered, index, nl):
                pieces.append(en)
                index += len(nl)
                break
        else:
            pieces.append(lowered[index])
            index += 1
    result = "".join(pieces).replace(marker, "")
    for pattern, repl in _REGEX[2:]:
        result = re.sub(pattern, repl, result)
    if len(_CACHE) < 2000:
        _CACHE[text] = result
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
    return (language or "nl").lower().startswith("nl")


def tr(language: str | None, value: Any, skip: tuple[str, ...] = ("icoon", "soort", "schakelaar")) -> Any:
    """Vertaal een tekst, of alle teksten in een lijst of woordenboek."""
    if is_dutch(language):
        return value
    if isinstance(value, str):
        return _translate(value)
    if isinstance(value, dict):
        return {k: (v if k in skip else tr(language, v, skip)) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [tr(language, v, skip) for v in value]
    return value
