"""Het gemiddelde verbruik van het huis per uur van de dag, geleerd uit een vermogenssensor.

Het zonne-overschot is de verwachte opbrengst min wat het huis zelf verbruikt. Dat
verbruik is niet de hele dag gelijk: 's ochtends en 's avonds meer dan midden op de dag,
in het weekend anders dan door de week. Daarom leert de integratie per uur van de dag
(apart voor werkdagen en weekend) het gemiddelde verbruik, en gebruikt dat in plaats van
één vast getal.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

# Eén meting wordt afgekapt: een laadpaal of oven die even vol aan staat verpest anders
# het gemiddelde van dat uur.
CLIP_W = 3500.0
# Het gewicht van een nieuw uur ten opzichte van wat er al geleerd is.
ALPHA = 0.15
# Minimaal aantal metingen in een uur voordat het meetelt.
MIN_SAMPLES = 20
SLOTS = 48  # 24 uur voor werkdagen, 24 voor het weekend


def slot(moment: datetime) -> int:
    """Het vak van een moment (lokale tijd): uur van de dag, werkdag of weekend."""
    return (24 if moment.weekday() >= 5 else 0) + moment.hour


class HouseProfile:
    """Het geleerde verbruik per uur van de dag."""

    def __init__(self) -> None:
        self.watts: list[float | None] = [None] * SLOTS
        self._hour: datetime | None = None
        self._sum = 0.0
        self._count = 0

    # ------------------------------------------------------------------ leren

    def sample(self, now: datetime, watts: float | None) -> bool:
        """Neem een meting op (lokale tijd). Geeft True als het profiel is gewijzigd."""
        changed = False
        hour = now.replace(minute=0, second=0, microsecond=0)
        if self._hour is not None and hour != self._hour:
            changed = self._finish()
        if self._hour is None or hour != self._hour:
            self._hour, self._sum, self._count = hour, 0.0, 0
        if watts is not None and watts >= 0:
            self._sum += min(float(watts), CLIP_W)
            self._count += 1
        return changed

    def _finish(self) -> bool:
        """Verwerk het afgelopen uur in het profiel."""
        if self._hour is None or self._count < MIN_SAMPLES:
            return False
        mean = self._sum / self._count
        index = slot(self._hour)
        old = self.watts[index]
        self.watts[index] = mean if old is None else old * (1 - ALPHA) + mean * ALPHA
        return True

    # ----------------------------------------------------------------- lezen

    def at(self, moment: datetime) -> float | None:
        """Het verwachte verbruik (W) in het uur van dit moment (lokale tijd), of None."""
        return self.watts[slot(moment)]

    def table(self) -> tuple[float, ...]:
        """Voor de planner: 48 waarden in watt, 0 waar nog niets geleerd is."""
        return tuple(round(w) if w else 0.0 for w in self.watts)

    def learned(self) -> int:
        return sum(1 for w in self.watts if w)

    # ----------------------------------------------------------------- bewaren

    def to_dict(self) -> dict[str, Any]:
        return {"watts": [None if w is None else round(w, 1) for w in self.watts]}

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "HouseProfile":
        profile = cls()
        values = (data or {}).get("watts")
        if isinstance(values, list) and len(values) == SLOTS:
            profile.watts = [float(v) if isinstance(v, (int, float)) else None for v in values]
        return profile
