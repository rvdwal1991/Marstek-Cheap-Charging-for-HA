# Changelog

All notable changes. Entries marked **Breaking** or **Behaviour change** can change what you
see or what the integration does after updating. No entity has been removed or renamed so far, and the
attribute names of the sensors and the `stroomschema` structure have only been extended.

## 1.26.1 (2026-11-26)
- **Docs:** a *Key points* list under the mode table in all eight READMEs: dynamic prices, negative
  prices, solar forecast with learning, depreciation, cost price, connections, cards and languages.
- **Fix (Swedish):** the card names in the card picker and the README title were still Dutch
  ("Goedkoop Laden"); they now read "Billig Laddning".
- No change in behaviour.

## 1.26.0 (2026-11-26)
- **New: the solar forecast reliability is learned.** Forecasts are often too rosy, especially in winter
  (on one roof the panels delivered about 40 % of the forecast). The integration now compares each
  day's forecast with what the panels really produced (the production counter of the solar source in
  the Energy dashboard) and uses the median of the last days as the reliability, from 3 completed days
  on. Until then, and when you turn *Learn the reliability from the actual production* off, the
  *Solar forecast reliability* setting applies. It needs Home Assistant to run through midnight, so a
  day with a restart in the early morning does not count. The result is in the diagnostics under
  `zonneverwachting`.
- **Behaviour change** (only with a solar forecast in the Energy dashboard): the night charge can
  differ from before once enough days are learned, usually charging more because the learned
  reliability is lower than the 70 % default.

## 1.25.1 (2026-11-26)
- **Prices card for phones and touch:** tap or drag over the chart to pick an hour, the price, the time
  and what happens in that hour appear above the chart (it shows the current hour by default). The
  whole column is touchable, the chart is drawn at the real card width so the text stays readable, and
  price labels on the bars switch off by themselves when the bars get too narrow.

## 1.25.0 (2026-11-26)
- **Cleanup, no change in behaviour:** the flow chart and the solar forecast moved out of
  `coordinator.py` into `flow.py` and `solar.py`, the long update routine is split into steps, and
  unused code is gone.
- **Options screen in groups** (Battery, Charging, Negative price, Solar, Selling, and the entities in
  a collapsed group). Every setting is still there and keeps its value; only the layout changed.
- **README rewritten** in all languages: shorter, with a quick start and an overview of the modes at
  the top, compatibility and settings grouped, and the technical details at the bottom.

## 1.24.1 (2026-11-26)
- **Fix:** the manifest now lists `energy` under `after_dependencies`, because the solar forecast is read
  from the Energy dashboard. This also fixes the hassfest check on GitHub. Nothing else changes.

## 1.24.0 (2026-11-26)
- **New: house power sensor** (optional). Choose a sensor with the power the whole house uses (W or kW,
  without the battery) and the integration learns your average consumption per hour of the day, for
  weekdays and weekends separately. The solar surplus is then the forecast minus that learned
  consumption per hour, so a midday that the house eats up itself leaves no surplus and the battery is
  charged full as before. Without the sensor the fixed *Selling: average own consumption* is used, as
  before. A car charger skews the average (one reading is capped at 3500 W), so leave it out if you can.
- Acknowledgements section in the READMEs: the Tweakers forum thread and the authors of the
  configurations and the integration this one builds on.

## 1.23.1 (2026-11-26)
- **Fix:** right after a restart the solar forecast could still be empty and then stayed empty for 30
  minutes. An empty forecast is now retried after 5 minutes.

## 1.23.0 (2026-11-26)
- **New: solar forecast.** The integration reads the expected solar yield from the Home Assistant Energy
  dashboard (Forecast.Solar, Solcast, Open-Meteo and others; nothing extra to set up) and charges less
  from the grid at night when the sun will fill the battery during the day, so the solar surplus is not
  lost to the grid. The plan text and flow chart show the expected surplus. With no forecast in the
  Energy dashboard nothing changes.
- **Behaviour change** (only with a solar forecast in the Energy dashboard): the night charge can be
  lower than a full battery, or skipped. Turn it off with *Use the solar forecast*, or set the
  reliability (default 70 %) lower to be more careful. The own consumption of *Selling: average own
  consumption* is used for the daytime load. Not tested on a real forecast yet, only with simulated data.

## 1.22.0 (2026-11-26)
- **New: six more languages** besides Dutch and English: Frysk, Deutsch, Français, Español, Svenska and
  Norsk (Bokmål). They cover the plan text, the flow chart, the cards, the Home Assistant screens and
  entity names, and there is a README per language. The *Language* option lists them. The translations
  were made with AI and have not been checked by native speakers: corrections are welcome.
- **Behaviour change:** with *Language* on Automatic, Home Assistant in one of these languages now gets
  texts in that language (before, anything but Dutch showed English). Other languages still get English.
- **Cards:** three new optional cards, *status* (what is happening now, SoC, price, next step), *prices*
  (price chart with the charge, sell and negative hours, no apexcharts needed) and *stock* (charged
  stock, cost price, efficiency, depreciation). All seven cards can be set up in the card editor, find the
  charge plan sensor themselves when `entity` is left out, and have options such as `lanes` and
  `show_timeline`. The `stroomschema` attribute got `id` per part plus `overzicht` and `prijzen`; nothing
  was removed.

## 1.21.0 (2026-11-26)
- New option *Negative price: how to divide the energy*: *Spread by value* (default, unchanged) or
  *Maximum gain*, which fills the best negative hours first at full power. Nothing changes unless you
  switch the option.

## 1.20.0 (2026-11-26)
- **Behaviour change:** the energy in a negative-price window is now divided over the hours **by their
  value** (more in the more negative hours, up to what an hour can take) instead of evenly over the
  cheapest hours. Hours that would stay below the minimum charge power drop out and their share goes to
  the others. The flow chart shows the kWh per hour. For the example −0.03 / −0.20 / −0.12 with 3 kWh to
  charge, the expected gain goes from about €0.49 to €0.52.

## 1.19.0 (2026-11-26)
- **Behaviour change:** *Charging at a negative price* now looks at the whole window of consecutive
  negative hours. It picks the hours with the lowest price (as few as needed to fill the battery),
  skips hours that earn less, and spreads the energy evenly over the chosen hours instead of always
  charging at full power. Plan text and flow chart show the window, chosen hours, power and expected
  gain. With a single negative hour and a battery that needs more than that hour can give, it still
  charges at full power, as before.

## 1.18.0 (2026-11-26)
- **New:** Marstek Venus E v3 over Modbus TCP. Two ways: the *Modbus in Home Assistant* option now also
  accepts the register sensors of
  [MarstekVenusV3-modbus-TCP-IP](https://github.com/fonske/MarstekVenusV3-modbus-TCP-IP) (state of
  charge lives in register 34002), and a new option *Marstek Venus Modbus integration* uses the entities
  of [ViperRNMC/marstek_venus_modbus](https://github.com/ViperRNMC/marstek_venus_modbus).
- Modbus option: optional sensors for maximum charge power (44002), maximum discharge power (44003, also
  written for *Hold* and *No loss*), battery capacity and the energy counters.
- Not tested on real hardware, only with simulated calls. The charge and discharge cut-off is not
  available on the Venus E v3, the fixed value from the options is used.

## 1.17.0 (2026-11-26)
- **New:** support for a Marstek connected through a **Modbus hub in Home Assistant**, for example an
  Elfin EW11 with [MarstekVenus-ElfinEW11](https://github.com/Superduper1969/MarstekVenus-ElfinEW11).
  Setup now first asks how the Marstek is connected (*LilyGO RS485 with ESPHome* or *Modbus in Home
  Assistant*). The Modbus variant reads the raw register sensors and writes registers 42000, 42010,
  42020 and 42021 through `modbus.write_register`.
- Not available with Modbus: maximum charge and discharge power, the discharge cut-off and the battery
  capacity entity (those registers are not part of that setup), so *Hold* and *No loss* are not
  available there. The fixed capacity and cut-off from the options are used instead.
- Existing installations keep working unchanged (they stay on the ESPHome variant). Tested with
  simulated Modbus calls only, not yet on a real Elfin EW11.

## 1.16.1 (2026-11-26)
- **Fix:** a charge was marked `klaar` (done) after its first hour when the planned charge hours were
  not consecutive (for example 22:00, 01:00, 02:00). The remaining hours were skipped. It now carries
  on after a gap.

## 1.16.0 (2026-11-25)
- Gain card: new tile *This year*, and the card is configurable with `tiles`, `expected_details` and
  `notes` (YAML or card editor).

## 1.15.0 (2026-11-25)
- New sensor *Gain this year* (`*_gain_this_year`).

## 1.14.0 (2026-11-25)
- New options *Battery purchase price* and *Battery lifetime (cycles)*. The resulting depreciation per
  kWh is subtracted from the realized and expected gain.
- **Behaviour change (only if the purchase price is above 0, default 0):** depreciation is also used in
  the decisions. An hour must still beat the wear to count for charging, selling needs the wear on top
  of the sell margin, and *Hold* and *No loss* use cost price plus wear as break-even price.

## 1.13.0 (2026-11-23)
- New sensors *Gain last week* and *Gain this month*, and tiles for them on the gain card.
- Note: entity IDs of new sensors follow the language Home Assistant had when they were created
  (for example `*_gain_last_week` on an English system).

## 1.12.0 (2026-11-22)
- **Behaviour change:** hours that are less than half a cent above the charging limit still count. On
  nearly flat nights more hours now qualify than before.

## 1.11.1 (2026-11-16)
- The *Selling* lane of the flow card says when selling becomes possible instead of only showing a stop.

## 1.11.0 (2026-11-15)
- New option *Language* (Automatic, Nederlands, English) for plan text, flow chart and cards.
- New Marstek icon.

## 1.10.0 (2026-11-15)
- **Breaking:** plan text, flow chart and cards now follow the language of Home Assistant (Dutch for
  Dutch, English for any other language). Anything that matches on the Dutch text of the `tekst`
  attribute or of the flow steps needs adapting. State values (`laden`, `gepland`, …) and attribute names
  are unchanged. In 1.11.0 this became selectable.
- English README (default); the Dutch one is `README.nl.md`.

## 1.9.1 (2026-11-15)
- **Behaviour change:** the charge window no longer breaks on one hour just above the limit (a gap of up
  to two hours is allowed), and the planned energy is capped by what the chosen hours can deliver.
  Plans can look different from before.

## 1.9.0 (2026-11-13)
- New switch *No loss*, off by default.

## 1.8.0 (2026-11-13)
- Efficiency measured from the energy counters, with its own sensor. The one-way efficiency is the
  square root of it (before: a fixed 0.88).

## 1.7.1 (2026-11-13)
- New switch *Hold below cost price*, on by default. It sets the maximum discharge power to 0 while the
  price is below the cost price of the charged stock.

## 1.6.0 (2026-11-13)
- Compact card with the switches of all modes.

## 1.5.0 (2026-11-13)
- Realized gain (today, this week) and three cards.

## 1.4.0 (2026-11-13)
- Expected gain of the plan.

## 1.3.0 (2026-11-13)
- Flow chart card for the dashboard.

## 1.2.0 (2026-11-13)
- Charge at full power at a negative price, with its own switch (on by default).

## 1.1.2 (2026-11-11)
- Lessons from the first charge night: the forcible discharge power is only restored after a sale.

## 1.1.1 (2026-11-10)
- Selling surplus as a separate option (off by default).

## 1.0.1 (2026-11-10)
- No longer trusts the lagging state of the Marstek after a command.

## 1.0.0 (2026-11-10)
- First version: charging in the cheapest published hours, spread over those hours.
