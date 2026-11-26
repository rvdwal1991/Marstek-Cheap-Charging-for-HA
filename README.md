<img src="custom_components/marstek_goedkoop_laden/brand/icon.png" width="96" align="right" alt="">

# Marstek Cheap Charging for Home Assistant

🇬🇧 English · [🇳🇱 Nederlands](README.nl.md) · [🏳️ Frysk](README.fy.md) · [🇩🇪 Deutsch](README.de.md) · [🇫🇷 Français](README.fr.md) · [🇪🇸 Español](README.es.md) · [🇸🇪 Svenska](README.sv.md) · [🇳🇴 Norsk](README.nb.md)

[![Open your Home Assistant instance and open this repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=rvdwal1991&repository=Marstek-Cheap-Charging-for-HA&category=integration)
[![Open your Home Assistant instance and start setting up the integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=marstek_goedkoop_laden)

Tops up a Marstek Venus home battery from the grid during the cheapest hours of a dynamic
electricity contract, so it is full before prices go up.

The starting point is **self-sufficiency**. The battery keeps regulating itself (anti-feed,
zero on the meter). This integration adds one thing: charging from the grid in the cheapest
hours. There is also a separate option, off by default, to **sell surplus** in the most
expensive hours.

> **Hardware and compatibility.** The integration controls a Marstek Venus through its RS485 control
> registers. Only the first row has been run on a real battery:
>
> | Connection | Model | Status |
> |---|---|---|
> | LilyGO T-CAN485 + ESPHome (RS485) | Venus E v2 | **Tested** on real hardware (the setup it was built on) |
> | Modbus hub in Home Assistant, via RS485-to-TCP converter (Elfin EW11 and similar) | Venus E v1/v2 | Tested with simulated calls only |
> | Modbus hub in Home Assistant, direct over Ethernet | Venus E v3 | Tested with simulated calls only |
> | *Marstek Venus Modbus* integration (ViperRNMC) | Venus E v3 | Tested with simulated calls only |
> | Any of the above | Venus A, Venus D, other models | **Not checked, not tested.** They are said to share the control registers, but that is unverified. Set the battery capacity in the options (default 5.12 kWh). |
> | Cloud, app or other integrations | any | Not supported |
>
> The connections in detail:
>
> - **LilyGO T-CAN485 running ESPHome** over RS485, using the
>   [MarstekVenus-LilygoRS485](https://github.com/Superduper1969/MarstekVenus-LilygoRS485)
>   configuration. This is the setup the integration was built on and tested with. It uses the
>   entities that this setup exposes: *RS485 Control Mode*, *Forcible Charge/Discharge*,
>   *Forcible Charge Power* (required) and, optionally, *Max. Charge Power*, *Max. Discharge Power*,
>   *Forcible Discharge Power*, *Discharging Cutoff Capacity* and the total charged/discharged
>   energy counters.
> - **Modbus in Home Assistant**, with a Modbus hub that you define yourself in `configuration.yaml`:
>   an Elfin EW11 or another RS485-to-TCP converter
>   ([MarstekVenus-ElfinEW11](https://github.com/Superduper1969/MarstekVenus-ElfinEW11)), or the
>   **Venus E v3 straight over Ethernet** (Modbus TCP, port 502, unit 1, EMS V144 or newer;
>   [MarstekVenusV3-modbus-TCP-IP](https://github.com/fonske/MarstekVenusV3-modbus-TCP-IP)). The
>   integration reads that setup's register sensors and writes the registers 42000 (RS485 control),
>   42010 (force mode), 42020/42021 (forcible charge/discharge power) and, if you give the sensors,
>   44002/44003 (maximum charge/discharge power) with `modbus.write_register`. With the maximum
>   discharge power, *Hold* and *No loss* work as well; without it they are not available. The
>   Venus E v3 keeps its state of charge in register 34002 (scale 0.1), not in 32104.
> - **The *Marstek Venus Modbus* integration**
>   ([ViperRNMC/marstek_venus_modbus](https://github.com/ViperRNMC/marstek_venus_modbus)), which
>   also talks Modbus TCP (Ethernet on a Venus E v3, or an RS485 gateway). Choose this when you
>   already use that integration: it supplies the entities (`switch` RS485 control mode, `select`
>   force mode, `number` powers). Enable the *RS485 control mode* switch and *Force mode* select
>   there first, they are disabled by default.
>
> The Modbus and Marstek Venus Modbus options are **new and so far only tested with simulated
> calls, not on real hardware**.
>
> Other ways of connecting the battery (cloud, other integrations) are untested and most likely do
> not work, because they do not offer these RS485 control entities.
>
> **Dynamic energy prices:** this integration only makes sense with a **dynamic electricity
> contract**, where the price changes every hour. It charges in the cheapest hours and avoids
> the expensive ones, so with a fixed tariff there is nothing to gain. It was built around the
> Dutch market and Zonneplan prices (hourly prices, published for the next day between 13:00 and
> 15:00). Any price sensor with an hourly price list as an attribute will do, see
> [Price sensor](#price-sensor).
>
> **Language:** the plan text, the flow chart and the cards follow the *Language* option
> (Automatic, Nederlands, English, Frysk, Deutsch, Français, Español, Svenska or Norsk;
> Automatic follows Home Assistant when it is one of these, otherwise English). Entity names follow the language of Home Assistant. State values and attribute names (`laden`, `tekst`, …) are fixed.

## What it does

1. **Is charging worth it?** An hour is cheap enough if its price is lower than
   `efficiency × (mean of the 6 most expensive hours in the next 18 hours) − margin`.
   The efficiency (charge and discharge round trip, about 77 % on my unit) is measured from
   the Marstek's energy counters.
2. **Window.** The first block of cheap hours is the charge window. One or two hours that are
   just not cheap enough do not break the block; charging only happens in the cheap hours
   themselves.
3. **Charge hours.** Within that window it picks the cheapest hours, exactly as many as needed
   to get from the current SoC to 100 %. If the window is too short to fill the battery, it
   plans only what fits and says so in the plan text.
4. **Spread the power.** Charge power is the energy still to be added divided by the time left
   in the charge hours. This keeps load on the grid connection and the house circuit as low as
   possible. The power is adjusted along the way.
5. **Done is done.** When the charge hours are over or the battery is full, the Marstek goes
   back to anti-feed. It does not start again in the same window and does not hold the charge.

Only **published** prices are used. The plan for the night therefore appears as soon as
tomorrow's prices are known (with Zonneplan between 13:00 and 15:00).

Example (10 November 2026, battery at 12 %): cheap window 23:00–07:00, charging at 02:00,
03:00 and 04:00 at about 1900 W for an average of €0.37, versus €0.55–0.67 during the day.

## Charging at a negative price

If the hourly price is negative, the battery charges from the grid, regardless of the charge plan
and even when price control is off. This has its own switch, **on by default**.

It looks at the whole **window** of consecutive negative hours, not just the current hour, and
makes the most of it:

1. It works out how much the battery can still take (SoC to 100 %).
2. It divides that energy over the hours **by their value**: the more negative the price, the more
   is charged in that hour (up to what an hour can take at the maximum power). Example: three
   negative hours at −€0.03, −€0.20 and −€0.12 and 3 kWh still to charge. The −€0.20 hour gets
   about 1.9 kWh and the −€0.12 hour about 1.2 kWh. The −€0.03 hour would stay below the minimum
   charge power, so it drops out and its share goes to the other two.
3. Because the energy is spread over the hours, the power stays lower than charging at full
   power for a short while. If the battery can take more than the window offers, every hour is
   filled to the maximum. A single hour that cannot fill the battery is charged at full power.
4. The plan text and the flow chart show the window, the chosen hours, the power and the expected
   gain (what you are paid to charge).

The option *Negative price: how to divide the energy* switches between two ways:

- **Spread by value** (default): as described above, lower power, slightly less gain.
- **Maximum gain**: the hours are filled one by one, best price first, each at full power, and the
  remainder goes to the next best hour. In the example the −€0.20 hour takes 2.25 kWh at full power
  and the −€0.12 hour the remaining 0.8 kWh, which earns about €0.55 instead of €0.52. The cost is
  more short bursts at full power.

As soon as the price turns positive again or the battery is full, the Marstek goes back to
anti-feed. The plan is recalculated every minute; an hour that was already in use gets a little extra
room before it drops out for being below the minimum power.

The limit is adjustable (*Negative price: limit*, default €0.00). The price is taken from the
price sensor, so with Zonneplan that is the price including taxes.

## Solar forecast

With solar panels the battery gets filled for free during the day. If you charge it full from the
grid at night, the solar surplus has no room left and goes to the grid for little or nothing,
which matters more now that net metering (*salderingsregeling*) is ending. So the integration
takes the expected solar yield into account:

1. It reads the forecast from the **Energy dashboard** of Home Assistant (*Settings → Dashboards →
   Energy → Solar panels → Solar production forecast*). Forecast.Solar, Solcast, Open-Meteo and
   other forecast integrations work, and there is nothing extra to set up. Without a forecast
   there, nothing changes.
2. It works out the expected surplus: per hour the forecast, multiplied by the reliability
   setting (default 70 %), minus your own consumption (the *Selling: average own consumption*
   setting).
3. It charges at night only so much that there is room for that surplus by the time the sun
   comes up: the energy your own consumption uses up until then, plus what is still needed. On a
   sunny day that can be a few kWh instead of a full battery, or nothing at all (the plan text
   then says the sun will fill the battery).
4. A cloudy day gives a small or no surplus, and then the battery is charged full as before.

This can be turned off with *Use the solar forecast*. The forecast is read every 30 minutes. It
only lowers the amount to charge; it does not move charge hours and does not change selling.

## Hold below cost price

Energy charged from the grid has a cost price: the charge price divided by the efficiency. If
the battery gave that energy back right after charging, in hours that are cheaper than that
cost price, charging would cost money. Discharging is therefore blocked as long as:

- there is charged stock in the battery (see *Gain*), and
- the hourly price is lower than the cost price of that stock.

The house then uses grid power, which is cheaper at that moment than what is in the battery.
As soon as the price reaches the cost price, or the stock is used up, the Marstek takes over
again. This has its own switch, **on by default**.

Technically the integration sets the maximum discharge power (*Max. Discharge power*) to 0.
The Marstek stays in anti-feed, so charging from solar surplus carries on. If another
automation sets that power to a different value during the hold (for example a limiter for an
EV charger), the integration remembers that value, sets it to 0 again and restores the
remembered value afterwards.

Note: the Marstek cannot tell grid-charged energy from solar energy. During a hold the whole
battery is therefore not discharged.

## No loss

A separate switch (off by default) that makes the integration strict: energy charged from the
grid is never used or sold below its cost price.

- **Hold is enforced**, even if the *Hold* switch is off.
- **Selling below cost price is blocked.** If there is charged stock in the battery and the
  sell price is lower than its cost price, nothing is sold.

Every booked kWh then earns at least its cost price, so a day's gain cannot go below zero.
What it cannot rule out:

- **Standstill.** If the price stays below the cost price for a long time, the battery stays
  blocked from discharging, including stored solar energy.
- **Deviating efficiency.** The cost price uses the average efficiency. If the battery returns
  less than that in a cycle, it is empty before the stock in the books is used up; the rest
  expires without booking a loss.
- **Wear** of the battery is not counted; use the minimum gain per kWh for that.

The integration recalculates immediately when a new price period starts, so a hold never
starts up to a minute late.

## Selling (optional)

Selling has its own switch and is independent of charging. Only what is really left over is
sold. An hour is used for selling when all of this holds:

1. **A cheap charge is coming**: a charge window with published prices lies ahead, so the cost
   of recharging is known.
2. **Revenue is clearly higher than recharging**: sell price ≥ charge price divided by the
   efficiency, plus the sell margin (default €0.10 per kWh).
3. **There is surplus above the reserve.** The reserve is the Marstek's discharge cut-off plus
   the expected own consumption until recharging (average house power × hours), with an
   adjustable minimum (default 20 %).
4. **It is one of the most expensive hours** before the charge window.

As with charging, the sell power is spread over the chosen hours. At the reserve, selling
stops and the Marstek goes back to anti-feed.

In winter there is rarely a surplus: with a 5 kWh battery, own consumption until the next
charge usually takes the whole charge. The option mostly does something when the sun fills
the battery and there is an evening price peak.

**After the end of net metering** (the Dutch *salderingsregeling*, 1 January 2027) feeding in
earns less than the hourly price. Then set *Sell price: factor* and *deduction*: sell price =
hourly price × factor − deduction. For the bare market price at Zonneplan that is roughly
0.826 and €0.108.

## Controlling the Marstek

The integration controls the battery through the RS485 interface (LilyGO T-CAN485 with
ESPHome):

| Moment | Commands |
|---|---|
| Start charging | set charge power → *Forcible charge/discharge* to `charge` → *RS485 Control Mode* to `enable` |
| While charging | adjust charge power (steps of 100 W) |
| Done, or price control off | *RS485 Control Mode* to `disable`, forcible back to `charge`, charge power back to the maximum |
| Start selling | set discharge power → forcible to `discharge` → *RS485 Control Mode* to `enable` |
| Selling done, or selling off | same as done: back to the idle state |

Forced **dis**charging that you start yourself is left alone. Forced charging that you start
yourself is reset as long as price control is on; switch it off first if you want that.

## Entities

| Entity | Contents |
|---|---|
| `switch.*_price_control` | On: the charge plan is carried out. Off: the Marstek regulates everything itself. Turning it off puts the Marstek back in anti-feed immediately. |
| `switch.*_charge_at_negative_price` | On (default): always charge at full power when the hourly price is negative. Attribute `nu_actief`. |
| `switch.*_hold_below_cost_price` | On (default): do not discharge while the hourly price is below the cost price of the charged stock. Attributes `nu_actief`, `tot`, `voorraad_kwh`, `kostprijs`. |
| `switch.*_no_loss` | On: hold enforced and never sell below cost price. Attributes `vasthouden_actief`, `verkoop_tegengehouden`, `voorraad_kwh`, `kostprijs`. |
| `switch.*_selling` | On: surplus is sold in the most expensive hours. Independent of price control. |
| `sensor.*_sell_plan` | State: `verkopen`, `gepland`, `geen` or `onbekend`. Attributes: `verkoopuren`, `vermogen`, `overschot_kwh`, `reserve_soc`, `drempelprijs`, `terugkoopprijs` and `tekst`. |
| `sensor.*_charge_plan` | State: `laden`, `gepland`, `klaar`, `vol`, `geen` or `onbekend`. Attributes: `laaduren`, `venster`, `eind`, `uren_nodig`, `vermogen`, `klaar_tot`, `tekst` (readable summary) and `stroomschema` (timeline and checks for the card). |
| `sensor.*_planned_charge_power` | The spread charge power in W. |
| `sensor.*_energy_to_charge` | Energy from the grid needed to fill up, in kWh. |
| `sensor.*_charge_start` / `*_charge_end` | Start and end of the planned charge. |
| `sensor.*_gain_today` / `*_gain_this_week` / `*_gain_this_month` | Realized gain in euros since 00:00, since Monday 00:00 and since the first of the month (see *Gain*). Attributes: the stock and, for today, what was charged and used. |
| `sensor.*_gain_this_year` | Realized gain since 1 January. |
| `sensor.*_gain_last_week` | The final gain of the previous week. |
| `sensor.*_expected_gain` | Estimated gain of the current plans in euros (charging plus selling); attribute `regels` holds the breakdown. |
| `sensor.*_efficiency` | The efficiency used, in percent. Attribute `bron`: measured from the energy counters or the fixed value. |
| `sensor.*_average_charge_price` | Average price of the charge hours in €/kWh. |

The names above are for an English installation. With Home Assistant set to Dutch they are
named `*_laadplan`, `*_prijssturing` and so on. The state values and attribute names are the
same in both languages.

## Installation

1. Install with HACS (button above, or add this repository as a custom repository, category
   *Integration*), or copy `custom_components/marstek_goedkoop_laden` to
   `/config/custom_components/`. Restart Home Assistant.
2. Go to *Settings → Devices & services → Add integration → Marstek Goedkoop Laden*.
3. Choose how your Marstek is connected (*LilyGO RS485 with ESPHome*, *Modbus in Home Assistant* or *Marstek Venus Modbus integration*),
   then the price sensor and the Marstek entities. Whatever is detected is pre-filled. For Modbus you
   also enter the name of your Modbus hub (for example `MarstekVenus`) and the slave address.

Requires Home Assistant 2026.3 or newer.

### Price sensor

The integration reads the prices from an attribute of one sensor (default `forecast`):

- Zonneplan hourly prices: `start_date`, `end_date`, `price_tax_included.amount`
- Zonneplan (old): `datetime`, `electricity_price`
- Generic: `start` (or `start_time`, `datetime`) and `price` (or `value`, `prijs`) in €/kWh

### Settings

Under *Configure* on the integration:

| Setting | Default | Meaning |
|---|---|---|
| Language | Automatic | Language of the plan text, flow chart and cards: Automatic, Nederlands, English, Frysk, Deutsch, Français, Español, Svenska or Norsk. |
| Battery purchase price | €0 | Used for depreciation. 0 turns depreciation off. |
| Battery lifetime (cycles) | 6000 | Expected number of full cycles. Depreciation per kWh = price ÷ (cycles × capacity); for example €1,500 over 6,000 cycles of 5.12 kWh is about €0.049 per kWh. |
| Use the solar forecast | On | Take the expected solar yield from the Energy dashboard into account when charging at night. |
| Solar forecast reliability | 70 % | The part of the forecast to count on. Lower is more careful. |
| Minimum gain per kWh | €0.02 | What charging must earn at least, after charge losses. Hours less than half a cent above the limit still count, so a nearly flat night is not cut up over a fraction of a cent. |
| Number of most expensive hours | 6 | How many expensive hours later on an hour is compared with. |
| Hours to look ahead | 18 | How far past an hour to look for expensive hours. |
| Minimum known hours ahead | 8 | Hours with fewer known prices after them are ignored. |
| Minimum charge power | 400 W | Lower limit when spreading. |
| Efficiency when the counters are missing | 0.77 | The efficiency is computed from the Marstek's energy counters (total discharged ÷ total charged, clamped to 70–95 %). This fixed value only applies when those counters are missing. The one-way efficiency for charging or discharging alone is its square root. |
| Battery capacity | 5.12 kWh | Only used when no capacity sensor is set. |
| Negative price: limit | €0.00 | Below this hourly price the battery charges at full power. |
| Selling: minimum gain per kWh | €0.10 | What selling must earn at least after recharging. |
| Selling: average own consumption | 400 W | Determines the reserve until recharging. |
| Selling: minimum reserve | 20 % | Nothing is sold below this SoC. |
| Sell price: factor and deduction | 1 and €0 | Sell price = hourly price × factor − deduction. |

The maximum charge power (the Marstek's *Max. Charge power*) determines the number of charge
hours. Set it lower and it plans more hours and charges more gently.

## Dashboard

### Cards from the integration

The integration ships seven cards; no resource needs to be added. Refresh the browser after
installing or updating. Every card can be set up in the card editor (the visual editor) as well as
in YAML, and when you leave `entity` out the charge plan sensor is found automatically.

| Card | Contents |
|---|---|
| `custom:marstek-goedkoop-laden-card` | Flow chart: today's timeline and, per part (charging, selling, negative price, hold), which checks pass and where it stops. |
| `custom:marstek-goedkoop-laden-compact-card` | The same in a few lines: the timeline, the outcome per part with the reason, and one line with the gain. |
| `custom:marstek-goedkoop-laden-opbrengst-card` | Gain only: today, this week, last week, this month and the expectation of the current plan. |
| `custom:marstek-goedkoop-laden-schakelaars-card` | Compact: buttons to turn charging, selling, charging at negative price, hold and no loss on or off. |
| `custom:marstek-goedkoop-laden-status-card` | What is happening now, the state of charge as a bar, the price now and the next step. |
| `custom:marstek-goedkoop-laden-prijzen-card` | Price chart without extra cards: the hours with charging, selling and negative prices marked, and a line for now. |
| `custom:marstek-goedkoop-laden-voorraad-card` | The charged stock, its cost price, the efficiency, the depreciation per kWh and the capacity. |

```yaml
type: custom:marstek-goedkoop-laden-card
entity: sensor.marstek_goedkoop_laden_laadplan   # optional
title: Price control                             # optional
opbrengst: false                                 # optional, see below
```

The gain card can be customized, in YAML or in the card editor:

```yaml
type: custom:marstek-goedkoop-laden-opbrengst-card
tiles: [vandaag, maand, jaar]   # any of: vandaag, week, vorige_week, maand, jaar, verwacht (in this order)
expected_details: false         # hide the lines per part of the plan (default: true)
notes: false                    # hide the note below the card (default: true)
```

| Option | Default | Meaning |
|---|---|---|
| `tiles` | all six | Which tiles to show and in which order: today, this week, last week, this month, this year, expected (plan). |
| `expected_details` | `true` | The lines with the expected gain per part (charging, selling). |
| `notes` | `true` | The note with the charged stock, what was charged today and the depreciation. |

Options of the other cards (all are also in the card editor):

| Card | Option | Default | Meaning |
|---|---|---|---|
| flow, compact | `show_timeline` | `true` | Show today's timeline. |
| flow, compact, switches | `lanes` | all five | Which parts to show: `bijladen`, `verkoop`, `negatief`, `vasthouden`, `geen_verlies`. |
| status | `show_soc`, `show_price`, `show_next` | `true` | The state of charge bar, the price now, the next step. |
| prices | `hours_back` | `2` | Hours of the past to show. |
| prices | `hours_ahead` | `0` | Hours ahead to show; 0 is up to the last known price. |
| prices | `show_values` | `false` | Print the price above each bar (up to 24 bars). |
| prices | `height` | `140` | Height of the chart in pixels. |
| stock | `tiles` | all five | `voorraad`, `kostprijs`, `rendement`, `afschrijving`, `capaciteit`. |
| stock | `notes` | `true` | The note below the card. |

`opbrengst` decides whether the flow card also shows the gain: off by default for the regular
card, one line by default for the compact card. In the flow chart green is a check that
passes, red is the check where it stops and dashed is an outcome where nothing happens. All
cards read the `stroomschema` attribute of the charge plan sensor.

## Gain

**Depreciation.** If you set a purchase price, every kWh the battery discharges costs a bit of wear: price ÷ (cycles × capacity). It is subtracted from the realized gain (today, week, month), counted in the expected gain, and used in the decisions: an hour is only worth charging if it still beats the wear, selling needs the wear on top of the sell margin, and *Hold* and *No loss* treat cost price plus wear as the break-even price. With a price of 0 (default) nothing changes.

There are two kinds of gain: what the current plan is expected to earn, and what has actually
been earned.

### Expected (estimate in advance)

- **Charging**: what the energy to buy costs, versus what it is worth later. That worth is the
  efficiency times the average price of the expensive hours the charge hour was compared with.
- **Selling**: the revenue of the surplus, minus what recharging costs.

During a charge only what is still to be charged counts.

### Today and this week (realized)

1. Energy the integration charges from the grid (charge plan or negative price) becomes
   **stock**: usable kWh = charged kWh × efficiency, with as cost price what that energy cost
   at that moment.
2. If the battery then discharges for own consumption, that stock is used first. The gain is
   `discharged kWh × (electricity price at that moment − cost price per usable kWh)`.
3. When selling, the gain is `sold kWh × sell price − cost price`; for energy that does not
   come from the stock (solar energy) the cost price is what recharging costs.
4. **Today** is the sum since 00:00, **this week** since Monday 00:00 and **this month** since the first of the month. **Last week** is the final amount of the week before.

What is still in the stock has not been earned yet and only counts once it is used. Energy
that the sun puts in the battery and that you use yourself later does not count: the Marstek
does that without this integration too. The amounts come from the Marstek's energy counters
and the hourly price at that moment; a counter jump after a fault is not booked.

### Separate cards

Plan line (Markdown card):

```yaml
type: markdown
content: >-
  **Charge plan:** {{ state_attr('sensor.marstek_goedkoop_laden_laadplan', 'tekst') }}
  {% if is_state('switch.marstek_goedkoop_laden_prijssturing', 'off') %}
  · ⚠️ price control is **off**{% endif %}
```

The price card above does the same without extra cards. As an alternative, a chart with
[apexcharts-card](https://github.com/RomRider/apexcharts-card): the Zonneplan
prices of today and tomorrow, green = charging, blue = rest of the cheap window, grey = other.
Repeat the series three times with `'laden'`, `'venster'` and `'rest'` in place of `KIES`:

```yaml
type: custom:apexcharts-card
graph_span: 48h
span:
  start: day
now:
  show: true
  label: now
stacked: true
series:
  - entity: sensor.zonneplan_current_hourly_electricity_tariff
    name: Charging
    type: column
    color: "#22c55e"
    data_generator: |
      const a = hass.states['sensor.marstek_goedkoop_laden_laadplan'].attributes;
      const L = new Set((a.laaduren || []).map(s => new Date(s).getTime()));
      const V = new Set((a.venster || []).map(s => new Date(s).getTime()));
      return (entity.attributes.forecast || []).map(i => {
        const t = new Date(i.start_date).getTime();
        const k = L.has(t) ? 'laden' : (V.has(t) ? 'venster' : 'rest');
        return [t, k === 'KIES' ? Math.round(i.price_tax_included.amount / 1e5) / 100 : null];
      });
```

## Development

The calculation rule lives separately from Home Assistant in `planner.py` and has tests with
real prices. The control logic is tested against a faked Home Assistant
(`tests/test_sturing.py`):

```bash
python3 -m unittest discover -s tests -v
```


## Changelog

See [CHANGELOG.md](CHANGELOG.md), including the breaking changes.

## License

Apache 2.0, see [LICENSE](LICENSE).
