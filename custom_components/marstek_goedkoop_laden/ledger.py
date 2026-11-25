"""Boekhouding van de gerealiseerde opbrengst.

Gebruikt niets van Home Assistant, zodat het los te testen is.

Definitie van opbrengst
-----------------------
1. Stroom die de integratie uit het net bijlaadt (laadplan of negatieve prijs)
   wordt een VOORRAAD: bruikbare kWh = geladen kWh x rendement, met als kostprijs
   wat die stroom op dat moment kostte.
2. Ontlaadt de accu daarna voor eigen verbruik, dan wordt eerst die voorraad
   opgebruikt. De opbrengst is dan:
       ontladen kWh x (stroomprijs op dat moment - kostprijs per bruikbare kWh)
3. Verkoopt de integratie overschot aan het net, dan is de opbrengst:
       verkochte kWh x verkoopprijs - kostprijs
   waarbij de kostprijs die van de voorraad is, of (voor stroom die niet uit de
   voorraad komt, bijvoorbeeld zonnestroom) wat terugladen kost.
4. "Vandaag" is de som van deze boekingen sinds 00:00, "deze week" sinds
   maandag 00:00 en "deze maand" sinds de eerste van de maand. "Vorige week" is
   het eindbedrag van de week daarvoor.

Stroom die de zon in de accu stopt en die je later zelf gebruikt telt niet mee:
dat doet de Marstek ook zonder deze integratie. Wat nog in de voorraad zit, is
nog niet verdiend en telt pas mee als het wordt gebruikt.

Afschrijving: is die ingesteld, dan gaat er per ontladen kWh een bedrag van de
opbrengst af (aanschafprijs / (levensduur in cycli x capaciteit)).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime

# Een grotere sprong in een energieteller tussen twee metingen (bijvoorbeeld na
# een herstart of een storing) wordt niet geboekt: de prijs ervan is onbekend.
MAX_STEP_KWH = 1.0


@dataclass
class Ledger:
    """De stand van de boekhouding."""

    last_charged: float | None = None
    last_discharged: float | None = None
    was_grid_charging: bool = False
    stock_kwh: float = 0.0
    stock_cost: float = 0.0
    day: str | None = None
    day_gain: float = 0.0
    day_charged_kwh: float = 0.0
    day_charge_cost: float = 0.0
    day_used_kwh: float = 0.0
    day_sold_kwh: float = 0.0
    day_depreciation: float = 0.0
    week: str | None = None
    week_gain: float = 0.0
    prev_week_gain: float | None = None
    month: str | None = None
    month_gain: float = 0.0
    day_start: str | None = None
    week_start: str | None = None
    month_start: str | None = None

    @classmethod
    def from_dict(cls, data: dict | None) -> Ledger:
        ledger = cls()
        for key, value in (data or {}).items():
            if hasattr(ledger, key):
                setattr(ledger, key, value)
        return ledger

    def to_dict(self) -> dict:
        return asdict(self)

    @property
    def stock_price(self) -> float | None:
        """Kostprijs per bruikbare kWh in de voorraad."""
        return self.stock_cost / self.stock_kwh if self.stock_kwh > 0.001 else None

    def _roll(self, now: datetime) -> bool:
        """Begin een nieuwe dag of week als die is aangebroken."""
        changed = False
        day = now.date().isoformat()
        if day != self.day:
            self.day = day
            self.day_start = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
            self.day_gain = self.day_charged_kwh = self.day_charge_cost = 0.0
            self.day_used_kwh = self.day_sold_kwh = self.day_depreciation = 0.0
            changed = True
        year, week_number, weekday = now.isocalendar()
        week = f"{year}-W{week_number:02d}"
        if week != self.week:
            previous_week = self.week
            self.week = week
            monday = now.replace(hour=0, minute=0, second=0, microsecond=0)
            self.week_start = monday.fromordinal(monday.toordinal() - (weekday - 1)).replace(
                tzinfo=now.tzinfo
            ).isoformat()
            if previous_week is not None:
                self.prev_week_gain = self.week_gain
            self.week_gain = 0.0
            changed = True
        month = now.strftime("%Y-%m")
        if month != self.month:
            self.month = month
            self.month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()
            self.month_gain = 0.0
            changed = True
        return changed

    def _take_stock(self, kwh: float) -> tuple[float, float]:
        """Haal kWh uit de voorraad; geeft (afgenomen kWh, kosten daarvan)."""
        used = min(kwh, self.stock_kwh)
        if used <= 0:
            return 0.0, 0.0
        cost = used * self.stock_cost / self.stock_kwh
        self.stock_kwh -= used
        self.stock_cost -= cost
        if self.stock_kwh < 0.001:
            self.stock_kwh = self.stock_cost = 0.0
        return used, cost

    def clear_stock(self) -> bool:
        """De accu is leeg: wat er nog aan voorraad in de boeken stond vervalt."""
        if self.stock_kwh == 0 and self.stock_cost == 0:
            return False
        self.stock_kwh = self.stock_cost = 0.0
        return True

    def _book(self, gain: float) -> None:
        self.day_gain += gain
        self.week_gain += gain
        self.month_gain += gain

    def update(
        self,
        *,
        now: datetime,
        charged: float | None,
        discharged: float | None,
        price: float | None,
        grid_charging: bool,
        selling: bool,
        export_price: float | None,
        replacement_cost: float | None,
        efficiency: float,
        depreciation: float = 0.0,
    ) -> bool:
        """Verwerk de nieuwe tellerstanden. Geeft True als er iets is veranderd.

        now              : lokale tijd
        charged          : totaalteller geladen energie (kWh)
        discharged       : totaalteller ontladen energie (kWh)
        price            : stroomprijs van dit moment (EUR/kWh)
        grid_charging    : de integratie laadt nu uit het net
        selling          : de integratie verkoopt nu aan het net
        export_price     : verkoopprijs van dit moment
        replacement_cost : wat het kost om een verkochte kWh terug te laden
        depreciation     : afschrijving van de accu in euro per ontladen kWh
        """
        changed = self._roll(now)
        if charged is None or discharged is None:
            return changed
        if self.last_charged is None or self.last_discharged is None:
            self.last_charged, self.last_discharged = charged, discharged
            self.was_grid_charging = grid_charging
            return True

        d_charged = charged - self.last_charged
        d_discharged = discharged - self.last_discharged
        ours = grid_charging or self.was_grid_charging
        if grid_charging != self.was_grid_charging:
            self.was_grid_charging = grid_charging
            changed = True
        if d_charged == 0 and d_discharged == 0:
            return changed
        self.last_charged, self.last_discharged = charged, discharged

        if price is None or not (0 <= d_charged <= MAX_STEP_KWH) or not (0 <= d_discharged <= MAX_STEP_KWH):
            return True  # Tellersprong of prijs onbekend: alleen bijwerken.

        if d_charged > 0 and ours:
            self.stock_kwh += d_charged * efficiency
            self.stock_cost += d_charged * price
            self.day_charged_kwh += d_charged
            self.day_charge_cost += d_charged * price

        if d_discharged > 0:
            used, cost = self._take_stock(d_discharged)
            if selling:
                rest = d_discharged - used
                sell_price = export_price if export_price is not None else price
                rest_cost = rest * (replacement_cost if replacement_cost is not None else sell_price)
                self._book(d_discharged * sell_price - cost - rest_cost - d_discharged * depreciation)
                self.day_depreciation += d_discharged * depreciation
                self.day_sold_kwh += d_discharged
            elif used > 0:
                self._book(used * price - cost - used * depreciation)
                self.day_depreciation += used * depreciation
                self.day_used_kwh += used
        return True
