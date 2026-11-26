"""Leert hoeveel van de zonneverwachting er in werkelijkheid wordt gehaald.

Voorspellingen van zonnepanelen zijn per dak en per seizoen anders (in de winter vaak veel te
rooskleurig). Daarom legt de integratie per dag vast wat er voor die dag was voorspeld en
vergelijkt dat na afloop met wat de panelen echt leverden. De mediaan van de laatste dagen is
dan de betrouwbaarheid waarmee gerekend wordt.
"""
from __future__ import annotations

from datetime import date, datetime
from statistics import median
from typing import Any

# Zoveel afgeronde dagen bewaren we, en zoveel zijn er minstens nodig.
KEEP_DAYS = 14
MIN_DAYS = 3
# Alleen dagen met een echte voorspelling tellen; op een dag met bijna niets verwacht zegt de
# verhouding niets.
MIN_FORECAST_KWH = 0.5
# Een dag begint pas "volledig" als de eerste meting van die dag voor zonsopkomst was.
FULL_DAY_BEFORE_HOUR = 5
MIN_FACTOR, MAX_FACTOR = 0.15, 1.0


class SolarCalibration:
    """De voorspelde en werkelijke opbrengst per dag, en de betrouwbaarheid die daaruit volgt."""

    def __init__(self) -> None:
        self.forecast: dict[str, float] = {}  # datum -> voorspelde kWh
        self.ratios: list[float] = []  # werkelijk / voorspeld, oud naar nieuw
        self._day: str | None = None
        self._start: float | None = None
        self._last: float | None = None
        self._complete = False

    # ---------------------------------------------------------------- voorspelling

    def record_forecast(self, today: date, hours: tuple[tuple[datetime, float], ...], local) -> bool:
        """Onthoud per dag de voorspelde kWh. Een dag die begonnen is, wordt niet meer aangepast."""
        totals: dict[str, float] = {}
        for start, wh in hours:
            day = local(start).date().isoformat()
            totals[day] = totals.get(day, 0.0) + wh / 1000.0
        changed = False
        for day, kwh in totals.items():
            if date.fromisoformat(day) > today or day not in self.forecast:
                if self.forecast.get(day) != round(kwh, 3):
                    self.forecast[day] = round(kwh, 3)
                    changed = True
        # Oude dagen opruimen.
        for day in [d for d in self.forecast if date.fromisoformat(d) < today.fromordinal(today.toordinal() - 3)]:
            del self.forecast[day]
            changed = True
        return changed

    # ------------------------------------------------------------------ productie

    def record_production(self, now: datetime, total_kwh: float | None) -> bool:
        """Geef de teller (kWh, oplopend) van de zonnepanelen; sluit de vorige dag af bij een nieuwe dag."""
        if total_kwh is None:
            return False
        day = now.date().isoformat()
        changed = False
        if self._day != day:
            changed = self._finish_day()
            self._day, self._start, self._last = day, total_kwh, total_kwh
            self._complete = now.hour < FULL_DAY_BEFORE_HOUR
            return True
        if self._last is None or total_kwh >= self._last:
            self._last = total_kwh
        return changed

    def _finish_day(self) -> bool:
        if not (self._day and self._complete and self._start is not None and self._last is not None):
            return False
        actual = self._last - self._start
        predicted = self.forecast.get(self._day)
        if actual < 0 or predicted is None or predicted < MIN_FORECAST_KWH:
            return False
        self.ratios.append(round(min(max(actual / predicted, 0.05), 1.5), 3))
        del self.ratios[:-KEEP_DAYS]
        return True

    # ----------------------------------------------------------------------- uitkomst

    def factor(self) -> float | None:
        """De geleerde betrouwbaarheid (0,15 - 1), of None als er nog te weinig dagen zijn."""
        if len(self.ratios) < MIN_DAYS:
            return None
        return round(min(max(median(self.ratios[-7:]), MIN_FACTOR), MAX_FACTOR), 3)

    # ------------------------------------------------------------------ bewaren

    def to_dict(self) -> dict[str, Any]:
        return {
            "forecast": self.forecast,
            "ratios": self.ratios,
            "day": self._day,
            "start": self._start,
            "last": self._last,
            "complete": self._complete,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "SolarCalibration":
        calibration = cls()
        data = data or {}
        forecast = data.get("forecast")
        if isinstance(forecast, dict):
            calibration.forecast = {str(k): float(v) for k, v in forecast.items() if isinstance(v, (int, float))}
        ratios = data.get("ratios")
        if isinstance(ratios, list):
            calibration.ratios = [float(r) for r in ratios if isinstance(r, (int, float))][-KEEP_DAYS:]
        calibration._day = data.get("day") if isinstance(data.get("day"), str) else None
        calibration._start = data.get("start") if isinstance(data.get("start"), (int, float)) else None
        calibration._last = data.get("last") if isinstance(data.get("last"), (int, float)) else None
        calibration._complete = bool(data.get("complete"))
        return calibration
