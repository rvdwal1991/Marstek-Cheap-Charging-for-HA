<img src="custom_components/marstek_goedkoop_laden/brand/icon.png" width="96" align="right" alt="">

# Marstek Cheap Charging for Home Assistant

🇬🇧 English · [🇳🇱 Nederlands](README.nl.md) · [🏳️ Frysk](README.fy.md) · [🇩🇪 Deutsch](README.de.md) · [🇫🇷 Français](README.fr.md) · [🇪🇸 Español](README.es.md) · [🇸🇪 Svenska](README.sv.md) · [🇳🇴 Norsk](README.nb.md)

[![Open your Home Assistant instance and open this repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=rvdwal1991&repository=Marstek-Cheap-Charging-for-HA&category=integration)
[![Open your Home Assistant instance and start setting up the integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=marstek_goedkoop_laden)

Tops up a Marstek Venus home battery from the grid during the cheapest hours of a dynamic
electricity contract, so it is full before prices go up.

The starting point is **self-sufficiency**: the battery keeps regulating itself (anti-feed, zero
on the meter). This integration adds one thing, charging from the grid in the cheapest hours,
plus a few optional extras around it.

**You need:**

- a **dynamic electricity contract** with hourly prices. With a fixed tariff there is nothing to
  gain. It was built around the Dutch market and Zonneplan (prices for the next day appear
  between 13:00 and 15:00), but any sensor with an hourly price list will do, see
  [Price sensor](#price-sensor);
- a Marstek Venus that Home Assistant can control over RS485 or Modbus, see
  [Compatibility](#compatibility). **Only the LilyGO RS485 + ESPHome setup has been tested on a
  real battery.**
- Home Assistant 2026.3 or newer.

## What it does

| Mode | Default | What it does |
|---|---|---|
| **Price control** | off | Charges from the grid in the cheapest hours and spreads the power over them. |
| **Charge at negative price** | on | Charges when the hourly price is negative, and makes the most of the window. |
| **Solar forecast** | on | Charges less at night when the sun will fill the battery during the day. Needs a solar forecast in the Energy dashboard. |
| **Hold below cost price** | on | Does not discharge while the grid is cheaper than the charged stock cost. |
| **No loss** | off | Strict version of hold: also never sells charged stock below cost price. |
| **Selling** | off | Sells surplus in the most expensive hours. |

Each mode has its own switch. **Price control is off after installing**: set the integration up,
check that the plan text on the charge plan sensor looks right, then turn it on.

## Quick start

1. Install with HACS (button above, or add this repository as a custom repository, category
   *Integration*), or copy `custom_components/marstek_goedkoop_laden` to
   `/config/custom_components/`. Restart Home Assistant.
2. *Settings → Devices & services → Add integration → Marstek Goedkoop Laden*.
3. Choose how your Marstek is connected, then the price sensor and the Marstek entities.
   Whatever is detected is pre-filled. For Modbus you also enter the name of your Modbus hub (for
   example `MarstekVenus`) and the slave address.
4. Turn on the **Price control** switch when the plan looks right.
5. Add cards: *Edit dashboard → Add card → search "Marstek"*, see [Dashboard cards](#dashboard-cards).

Texts (plan line, flow chart, cards) follow the *Language* option: Automatic, Nederlands,
English, Frysk, Deutsch, Français, Español, Svenska or Norsk. Automatic follows Home Assistant
when it is one of these, otherwise English.

## How the charge plan works

1. **Is charging worth it?** An hour is cheap enough if its price is lower than
   `efficiency × (mean of the 6 most expensive hours in the next 18 hours) − margin`. The
   efficiency (charge and discharge round trip, about 77 % measured here) comes from the
   Marstek's energy counters.
2. **Window.** The first block of cheap hours is the charge window. One or two hours that are
   just not cheap enough do not break the block; charging only happens in the cheap hours
   themselves.
3. **Charge hours.** Within that window it picks the cheapest hours, exactly as many as needed
   to get from the current SoC to 100 %. If the window is too short to fill the battery, it
   plans only what fits and says so in the plan text.
4. **Spread the power.** Charge power is the energy still to be added divided by the time left
   in the charge hours. This keeps the load on the grid connection low. The power is adjusted
   along the way.
5. **Done is done.** When the charge hours are over or the battery is full, the Marstek goes
   back to anti-feed. It does not start again in the same window.

Only **published** prices are used, so the plan for the night appears as soon as tomorrow's
prices are known. Example (10 November 2026, battery at 12 %): cheap window 23:00–07:00,
charging at 02:00, 03:00 and 04:00 at about 1900 W for an average of €0.37, versus €0.55–0.67
during the day.

### Charging at a negative price

If the hourly price is negative the battery charges, regardless of the charge plan and even
when price control is off. It looks at the whole **window** of consecutive negative hours:

1. It works out how much the battery can still take (SoC to 100 %).
2. It divides that energy over the hours **by their value**: the more negative the price, the
   more is charged in that hour, up to what an hour can take at the maximum power. Example:
   −€0.03, −€0.20 and −€0.12 with 3 kWh to charge gives about 1.9 kWh in the −€0.20 hour and
   1.2 kWh in the −€0.12 hour. The −€0.03 hour would stay below the minimum charge power, so it
   drops out and its share goes to the other two.
3. Spreading keeps the power lower than a short burst at full power. A single hour that cannot
   fill the battery is charged at full power.

The option *Negative price: how to divide the energy* can be set to **Maximum gain**: the best
hour is filled first at full power, then the next one. In the example that earns about €0.55
instead of €0.52, at the cost of more bursts at full power. The plan is recalculated every
minute, and an hour already in use gets a little extra room before it drops out.

### Solar forecast

With solar panels the battery fills for free during the day. If you charge it full from the
grid at night, the surplus has no room left and goes to the grid for little or nothing, which
matters more now that net metering (*salderingsregeling*) is ending. So the integration looks at
the expected solar yield:

1. It reads the forecast from the **Energy dashboard** (*Settings → Dashboards → Energy → Solar
   panels → Solar production forecast*). Forecast.Solar, Solcast, Open-Meteo and other forecast
   integrations work, with nothing extra to set up. Without a forecast there, nothing changes.
2. It works out the expected surplus: per hour the forecast, multiplied by the reliability,
   minus your own consumption in that hour. Forecasts are often too rosy, especially in winter.
   With *Learn the reliability from the actual production* on, the integration compares each day's
   forecast with what the panels really produced (the production counter from the Energy
   dashboard) and uses the median of the last days as the reliability, once it has at least 3 days.
   Until then, and when learning is off, the *Solar forecast reliability* setting (default 70 %)
   applies. Your own consumption in that hour: With a *House power sensor*
   the integration learns your average consumption per hour of the day (weekdays and weekends
   separately) and uses that, so a midday that the house eats up itself leaves no surplus.
   Without the sensor the fixed *Selling: average own consumption* is used.
3. It charges at night only so much that there is room for that surplus when the sun comes up:
   what your own consumption uses up until then, plus what is still needed. On a sunny day that
   can be a few kWh instead of a full battery, or nothing (the plan text then says the sun will
   fill the battery). A cloudy day gives little or no surplus, and the battery is charged full.

The forecast is read every 30 minutes. It only lowers the amount to charge; it does not move
charge hours and does not change selling.

### Hold and no loss

Energy charged from the grid has a cost price: the charge price divided by the efficiency. If the
battery gave that energy back in hours cheaper than that, charging would cost money.
**Hold** therefore blocks discharging as long as there is charged stock in the battery (see
[Gain](#gain)) and the hourly price is below the cost price of that stock. The house then uses grid
power, which is cheaper at that moment. As soon as the price reaches the cost price, or the stock
is used up, the Marstek takes over again.

Technically the integration sets the maximum discharge power to 0. The Marstek stays in
anti-feed, so charging from solar surplus carries on. If another automation sets that power
during the hold (for example a limiter for an EV charger), the integration remembers that value
and restores it afterwards. The Marstek cannot tell grid energy from solar energy, so during a
hold the whole battery is not discharged. Hold needs the entity for the maximum discharge
power.

**No loss** is a separate, stricter switch: hold is enforced even if the Hold switch is off, and
nothing is sold below the cost price. Every booked kWh then earns at least its cost price. What it
cannot rule out:

- **Standstill:** if the price stays below the cost price for a long time, the battery stays
  blocked, including stored solar energy.
- **Deviating efficiency:** if the battery returns less than the average efficiency, it is empty
  before the stock in the books is used up; the rest expires without booking a loss.
- **Wear** is not counted unless you set a purchase price (see [Gain](#gain)).

### Selling

Selling has its own switch and is independent of charging. Only what is really left over is
sold. An hour is used for selling when all of this holds:

1. **A cheap charge is coming**: a charge window with published prices lies ahead, so the cost
   of recharging is known.
2. **Revenue is clearly higher than recharging**: sell price ≥ charge price divided by the
   efficiency, plus the sell margin (default €0.10 per kWh).
3. **There is surplus above the reserve**: the Marstek's discharge cut-off plus the expected own
   consumption until recharging, with an adjustable minimum (default 20 %).
4. **It is one of the most expensive hours** before the charge window.

The sell power is spread over the chosen hours; at the reserve, selling stops. In winter there
is rarely a surplus; the option mostly does something when the sun fills the battery and there is
an evening price peak. It needs the entity for the forcible discharge power.

**After the end of net metering** (the Dutch *salderingsregeling*, 1 January 2027) feeding in
earns less than the hourly price. Then set *Sell price: factor* and *deduction*: sell price =
hourly price × factor − deduction. For the bare market price at Zonneplan that is roughly 0.826
and €0.108.

## Compatibility

The integration controls a Marstek Venus through its RS485 control registers.

| Connection | Model | Status |
|---|---|---|
| LilyGO T-CAN485 + ESPHome (RS485) | Venus E v2 | **Tested** on real hardware (the setup it was built on) |
| Modbus hub in Home Assistant, via RS485-to-TCP converter (Elfin EW11 and similar) | Venus E v1/v2 | Tested with simulated calls only |
| Modbus hub in Home Assistant, direct over Ethernet | Venus E v3 | Tested with simulated calls only |
| *Marstek Venus Modbus* integration (ViperRNMC) | Venus E v3 | Tested with simulated calls only |
| Any of the above | Venus A, Venus D, other models | **Not checked, not tested.** They are said to share the control registers, but that is unverified. Set the battery capacity in the options (default 5.12 kWh). |
| Cloud, app or other integrations | any | Not supported |

- **LilyGO T-CAN485 running ESPHome** over RS485, using the
  [MarstekVenus-LilygoRS485](https://github.com/Superduper1969/MarstekVenus-LilygoRS485)
  configuration. It uses the entities that this setup exposes: *RS485 Control Mode*, *Forcible
  Charge/Discharge*, *Forcible Charge Power* (required) and, optionally, *Max. Charge Power*,
  *Max. Discharge Power*, *Forcible Discharge Power*, *Discharging Cutoff Capacity* and the total
  charged/discharged energy counters.
- **Modbus in Home Assistant**, with a Modbus hub that you define yourself in
  `configuration.yaml`: an Elfin EW11 or another RS485-to-TCP converter
  ([MarstekVenus-ElfinEW11](https://github.com/Superduper1969/MarstekVenus-ElfinEW11)), or the
  **Venus E v3 straight over Ethernet** (Modbus TCP, port 502, unit 1, EMS V144 or newer;
  [MarstekVenusV3-modbus-TCP-IP](https://github.com/fonske/MarstekVenusV3-modbus-TCP-IP)). The
  integration reads that setup's register sensors and writes the registers 42000 (RS485 control),
  42010 (force mode), 42020/42021 (forcible charge/discharge power) and, if you give the sensors,
  44002/44003 (maximum charge/discharge power) with `modbus.write_register`. Without the maximum
  discharge power, *Hold* and *No loss* are not available. The Venus E v3 keeps its state of
  charge in register 34002 (scale 0.1), not in 32104.
- **The *Marstek Venus Modbus* integration**
  ([ViperRNMC/marstek_venus_modbus](https://github.com/ViperRNMC/marstek_venus_modbus)), which
  also talks Modbus TCP. Choose this when you already use it: it supplies the entities (`switch`
  RS485 control mode, `select` force mode, `number` powers). Enable the *RS485 control mode*
  switch and *Force mode* select there first, they are disabled by default.

### What the integration sends to the Marstek

| Moment | Commands |
|---|---|
| Start charging | set charge power → force mode `charge` → RS485 control `enable` |
| While charging | adjust charge power (steps of 100 W) |
| Done, or price control off | RS485 control `disable`, force mode back to `charge`, charge power back to the maximum |
| Start selling | set discharge power → force mode `discharge` → RS485 control `enable` |
| Selling done, or selling off | same as done: back to the idle state |

Forced **dis**charging that you start yourself is left alone. Forced charging that you start
yourself is reset as long as price control is on; switch it off first if you want that.

## Settings

Under *Configure* on the integration. The options are in groups; the entities are in a
collapsed group at the bottom.

### Price sensor

The integration reads the prices from an attribute of one sensor (default `forecast`):

- Zonneplan hourly prices: `start_date`, `end_date`, `price_tax_included.amount`
- Zonneplan (old): `datetime`, `electricity_price`
- Generic: `start` (or `start_time`, `datetime`) and `price` (or `value`, `prijs`) in €/kWh

### Options

| Group | Setting | Default | Meaning |
|---|---|---|---|
| | Language | Automatic | Language of the plan text, flow chart and cards. |
| Battery | Battery capacity | 5.12 kWh | Only used when no capacity sensor is set. |
| Battery | Efficiency when the counters are missing | 0.77 | The efficiency is computed from the Marstek's energy counters (total discharged ÷ total charged, clamped to 70–95 %). This fixed value only applies when those counters are missing. The one-way efficiency is its square root. |
| Battery | Battery purchase price | €0 | Used for depreciation. 0 turns it off. |
| Battery | Battery lifetime (cycles) | 6000 | Depreciation per kWh = price ÷ (cycles × capacity); €1,500 over 6,000 cycles of 5.12 kWh is about €0.049 per kWh. |
| Battery | Discharge cut-off | 12 % | Used when no cut-off entity is set. |
| Charging | Minimum gain per kWh | €0.02 | What charging must earn at least, after charge losses. Hours less than half a cent above the limit still count, so a nearly flat night is not cut up over a fraction of a cent. |
| Charging | Minimum charge power | 400 W | Lower limit when spreading. |
| Charging | Attribute holding the prices | `forecast` | The attribute of the price sensor with the hourly prices. |
| Charging | Number of most expensive hours to compare with | 6 | How many expensive hours later on an hour is compared with. |
| Charging | Hours to look ahead | 18 | How far past an hour to look for expensive hours. |
| Charging | Minimum known hours ahead | 8 | Hours with fewer known prices after them are ignored. |
| Negative price | Negative price: limit | €0.00 | Below this hourly price the battery charges. |
| Negative price | Negative price: how to divide the energy | By value | By value (lower power) or maximum gain (best hours first). |
| Solar | Use the solar forecast | On | Take the expected solar yield from the Energy dashboard into account when charging at night. |
| Solar | Learn the reliability from the actual production | On | Compare each day's solar forecast with what the panels really produced and use the median of the last days as the reliability (from 3 days on). |
| Solar | Solar forecast reliability | 70 % | The part of the forecast to count on. Lower is more careful. |
| Solar | House power sensor | none | Optional sensor with the power the whole house uses (W or kW), without the battery. A car charger skews the average, so leave it out if you can. |
| Selling | Selling: minimum gain per kWh | €0.10 | What selling must earn at least after recharging. |
| Selling | Selling: average own consumption | 400 W | Determines the reserve until recharging, and is the fixed own consumption for the solar surplus. |
| Selling | Selling: minimum reserve | 20 % | Nothing is sold below this SoC. |
| Selling | Sell price: factor and deduction | 1 and €0 | Sell price = hourly price × factor − deduction. |

The maximum charge power (the Marstek's *Max. Charge power*) determines the number of charge
hours. Set it lower and it plans more hours and charges more gently.

## Dashboard cards

The integration ships seven cards; no resource needs to be added. Refresh the browser after
installing or updating. Every card can be set up in the card editor as well as in YAML, and when
you leave `entity` out the charge plan sensor is found automatically.

| Card | Contents |
|---|---|
| `custom:marstek-goedkoop-laden-card` | Flow chart: today's timeline and, per part (charging, selling, negative price, hold), which checks pass and where it stops. |
| `custom:marstek-goedkoop-laden-compact-card` | The same in a few lines: the timeline, the outcome per part with the reason, and one line with the gain. |
| `custom:marstek-goedkoop-laden-opbrengst-card` | Gain only: today, this week, last week, this month, this year and the expectation of the current plan. |
| `custom:marstek-goedkoop-laden-schakelaars-card` | Compact: buttons to turn the modes on or off. |
| `custom:marstek-goedkoop-laden-status-card` | What is happening now, the state of charge as a bar, the price now and the next step. |
| `custom:marstek-goedkoop-laden-prijzen-card` | Price chart without extra cards: the hours with charging, selling and negative prices marked, and a line for now. |
| `custom:marstek-goedkoop-laden-voorraad-card` | The charged stock, its cost price, the efficiency, the depreciation per kWh and the capacity. |

```yaml
type: custom:marstek-goedkoop-laden-opbrengst-card
entity: sensor.marstek_goedkoop_laden_laadplan   # optional
title: Gain                                      # optional
tiles: [vandaag, maand, jaar]                    # which tiles, in this order
notes: false                                     # hide the note below the card
```

| Card | Option | Default | Meaning |
|---|---|---|---|
| all | `entity`, `title` | found automatically, none | The charge plan sensor and a title. |
| flow, compact | `show_timeline` | `true` | Show today's timeline. |
| flow, compact | `opbrengst` | off, one line | Also show the gain. |
| flow, compact, switches | `lanes` | all five | Which parts to show: `bijladen`, `verkoop`, `negatief`, `vasthouden`, `geen_verlies`. |
| gain | `tiles` | all six | Any of `vandaag`, `week`, `vorige_week`, `maand`, `jaar`, `verwacht`, in this order. |
| gain | `expected_details`, `notes` | `true` | The lines per part of the plan; the note with stock, today's charge and depreciation. |
| status | `show_soc`, `show_price`, `show_next` | `true` | The state of charge bar, the price now, the next step. |
| prices | `hours_back`, `hours_ahead` | `2`, `0` | Hours of the past; hours ahead (0 is up to the last known price). |
| prices | `show_values`, `height` | `false`, `140` | Print the price above each bar (up to 24 bars); height in pixels. |
| stock | `tiles`, `notes` | all five, `true` | `voorraad`, `kostprijs`, `rendement`, `afschrijving`, `capaciteit`; the note below the card. |

In the flow chart green is a check that passes, red is the check where it stops and dashed is an
outcome where nothing happens. Plan line in a Markdown card:

```yaml
type: markdown
content: >-
  **Charge plan:** {{ state_attr('sensor.marstek_goedkoop_laden_laadplan', 'tekst') }}
  {% if is_state('switch.marstek_goedkoop_laden_prijssturing', 'off') %}
  · ⚠️ price control is **off**{% endif %}
```

## Gain

There are two kinds of gain: what the current plan is expected to earn, and what has actually
been earned.

**Expected (estimate in advance).** Charging: what the energy to buy costs, versus what it is
worth later (the efficiency times the average price of the expensive hours the charge hour was
compared with). Selling: the revenue of the surplus, minus what recharging costs. During a
charge only what is still to be charged counts.

**Realized (today, week, month, year).**

1. Energy the integration charges from the grid (charge plan or negative price) becomes
   **stock**: usable kWh = charged kWh × efficiency, with as cost price what that energy cost
   at that moment.
2. If the battery then discharges for own consumption, that stock is used first. The gain is
   `discharged kWh × (electricity price at that moment − cost price per usable kWh)`.
3. When selling, the gain is `sold kWh × sell price − cost price`; for energy that does not come
   from the stock (solar energy) the cost price is what recharging costs.
4. **Today** counts since 00:00, **this week** since Monday 00:00, **this month** since the first
   and **this year** since 1 January. **Last week** is the final amount of the week before.

What is still in the stock has not been earned yet and only counts once it is used. Energy that
the sun puts in the battery and that you use yourself later does not count: the Marstek does that
without this integration too. The amounts come from the Marstek's energy counters and the hourly
price at that moment; a counter jump after a fault is not booked.

**Depreciation.** If you set a purchase price, every kWh the battery discharges costs a bit of
wear: price ÷ (cycles × capacity). It is subtracted from the realized gain, counted in the
expected gain and used in the decisions: an hour is only worth charging if it still beats the
wear, selling needs the wear on top of the sell margin, and *Hold* and *No loss* treat cost
price plus wear as the break-even price. With a price of 0 (default) nothing changes.

## Entities

| Entity | Contents |
|---|---|
| `switch.*_price_control` | On: the charge plan is carried out. Off: the Marstek regulates everything itself. |
| `switch.*_charge_at_negative_price` | On (default): charge when the hourly price is negative. |
| `switch.*_hold_below_cost_price` | On (default): do not discharge below the cost price of the stock. |
| `switch.*_no_loss` | On: hold enforced and never sell below cost price. |
| `switch.*_selling` | On: surplus is sold in the most expensive hours. Independent of price control. |
| `sensor.*_charge_plan` | State: `laden`, `gepland`, `klaar`, `vol`, `geen` or `onbekend`. Attributes: `tekst` (readable summary), `laaduren`, `venster`, `stroomschema` (timeline, checks, prices and overview for the cards) and more. |
| `sensor.*_sell_plan` | State: `verkopen`, `gepland`, `geen` or `onbekend`. Attributes: `verkoopuren`, `overschot_kwh`, `reserve_soc`, `tekst` and more. |
| `sensor.*_planned_charge_power`, `*_energy_to_charge`, `*_charge_start`, `*_charge_end`, `*_average_charge_price` | The spread charge power in W, the energy still to charge in kWh, start and end of the planned charge, and its average price in €/kWh. |
| `sensor.*_gain_today`, `*_gain_this_week`, `*_gain_last_week`, `*_gain_this_month`, `*_gain_this_year` | Realized gain in euros (see [Gain](#gain)). |
| `sensor.*_expected_gain` | Estimated gain of the current plans in euros; attribute `regels` holds the breakdown. |
| `sensor.*_efficiency` | The efficiency used, in percent. Attribute `bron`: measured or fixed. |

Entity names follow the language of Home Assistant when the entity is created (with Dutch they are
named `*_laadplan`, `*_prijssturing` and so on). **State values and attribute names are Dutch in
every language** (`laden`, `tekst`, …); they are fixed so that automations keep working.

## Development

The calculation rule lives separately from Home Assistant in `planner.py` and has tests with
real prices. The control logic is tested against a faked Home Assistant:

```bash
python3 -m unittest discover -s tests -v
```

## Changelog

See [CHANGELOG.md](CHANGELOG.md), including the breaking changes.

## Acknowledgements

This integration stands on the work of the Marstek Venus community:

- The [Tweakers forum thread](https://gathering.tweakers.net/forum/list_messages/2282240/0) where this community work is discussed, an honorable mention for everyone there who shares findings and configurations.
- [Superduper1969](https://github.com/Superduper1969) for the LilyGO RS485 and Elfin EW11 configurations this integration is built around, and scruysberghs, who is thanked in those configurations.
- [fonske](https://github.com/fonske) for the Modbus TCP configuration of the Venus E v3.
- [ViperRNMC](https://github.com/ViperRNMC) for the Marstek Venus Modbus integration.

## License

Apache 2.0, see [LICENSE](LICENSE).
