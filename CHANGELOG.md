# Changelog

All notable changes. Entries marked **Breaking** or **Behaviour change** can change what you
see or what the integration does after updating. No entity has been removed or renamed so far, and the
attribute names of the sensors and the `stroomschema` structure have only been extended.

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
