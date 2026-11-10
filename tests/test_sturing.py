"""Tests voor de aansturing van de Marstek, met een nagebootst Home Assistant.

Home Assistant zelf is hier niet nodig: de paar onderdelen die de coördinator
gebruikt worden door eenvoudige vervangers nagebootst.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
import importlib
import json
from pathlib import Path
import sys
import types
import unittest

ROOT = Path(__file__).resolve().parent
TZ = timezone(timedelta(hours=1))
CLOCK = {"now": datetime(2026, 11, 10, 19, 40, tzinfo=TZ)}


def _module(name, **attrs):
    module = types.ModuleType(name)
    module.__dict__.update(attrs)
    sys.modules[name] = module
    return module


class _Coordinator:
    def __init__(self, hass, logger, *, name, config_entry, update_interval):
        self.hass = hass
        self.config_entry = config_entry
        self.data = None

    def __class_getitem__(cls, item):
        return cls

    async def async_refresh(self):
        self.data = await self._async_update_data()

    async def async_request_refresh(self):
        await self.async_refresh()


class _Store:
    def __init__(self, hass, version, key):
        self.saved = None

    def __class_getitem__(cls, item):
        return cls

    async def async_load(self):
        return None

    def async_delay_save(self, func, delay):
        self.saved = func()


def _parse(value):
    try:
        return datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None


_module("homeassistant")
_module("homeassistant.config_entries", ConfigEntry=object)
_module(
    "homeassistant.const",
    STATE_UNAVAILABLE="unavailable",
    STATE_UNKNOWN="unknown",
    Platform=types.SimpleNamespace(SENSOR="sensor", SWITCH="switch"),
)
_module("homeassistant.core", Event=object, HomeAssistant=object, callback=lambda f: f)
_module("homeassistant.helpers")
_module("homeassistant.helpers.event", async_track_state_change_event=lambda *a: (lambda: None))
_module("homeassistant.helpers.storage", Store=_Store)
_module("homeassistant.helpers.update_coordinator", DataUpdateCoordinator=_Coordinator)
_dt = _module(
    "homeassistant.util.dt",
    utcnow=lambda: CLOCK["now"].astimezone(timezone.utc),
    now=lambda: CLOCK["now"],
    parse_datetime=_parse,
    DEFAULT_TIME_ZONE=TZ,
)
_module("homeassistant.util", dt=_dt)

sys.path.insert(0, str(ROOT.parent / "custom_components"))
coordinator_module = importlib.import_module("marstek_goedkoop_laden.coordinator")

FORECAST = [
    {
        "start_date": row["start"],
        "end_date": (datetime.fromisoformat(row["start"]) + timedelta(hours=1)).isoformat(),
        "price_tax_included": {"amount": round(row["price"] * 1e7)},
    }
    for row in json.loads((ROOT / "prijzen_2026_11_10.json").read_text())
]

CONF = {
    "price_entity": "sensor.prijs",
    "soc_entity": "sensor.soc",
    "control_mode_entity": "select.rs485",
    "force_mode_entity": "select.forceer",
    "force_power_entity": "number.laadvermogen",
    "max_power_entity": "number.max_laden",
    "capacity_entity": None,
    "charged_energy_entity": "sensor.geladen",
    "discharged_energy_entity": "sensor.ontladen",
    "force_discharge_power_entity": "number.ontlaadvermogen",
    "max_discharge_power_entity": "number.max_ontladen",
    "min_soc_entity": "number.min_soc",
    "house_power": 150,
}


class _State:
    def __init__(self, state, attributes=None):
        self.state = str(state)
        self.attributes = attributes or {}


class _Hass:
    """Home Assistant-vervanger: de Marstek voert elke opdracht meteen uit."""

    def __init__(self, soc):
        self.calls = []
        self.values = {
            "sensor.prijs": _State("0.5", {"forecast": FORECAST}),
            "sensor.soc": _State(soc),
            "select.rs485": _State("disable"),
            "select.forceer": _State("charge"),
            "number.laadvermogen": _State(2500),
            "number.max_laden": _State(2500),
            "number.ontlaadvermogen": _State(2500),
            "number.max_ontladen": _State(2500),
            "number.min_soc": _State(12),
            "sensor.geladen": _State(1837.74),
            "sensor.ontladen": _State(1418.82),
        }
        self.states = types.SimpleNamespace(get=self.values.get)
        self.services = types.SimpleNamespace(async_call=self._call)

    async def _call(self, domain, service, data, blocking=False):
        value = data.get("option", data.get("value"))
        self.calls.append((data["entity_id"], value))
        self.values[data["entity_id"]] = _State(value)

    def set(self, entity_id, value):
        self.values[entity_id] = _State(value, self.values[entity_id].attributes)

    def get(self, entity_id):
        return self.values[entity_id].state


def make(soc, conf=None):
    hass = _Hass(soc)
    entry = types.SimpleNamespace(data=dict(conf or CONF), options={}, entry_id="test")
    return hass, coordinator_module.ChargePlanCoordinator(hass, entry)


def run(coro):
    return asyncio.run(coro)


def at(text):
    CLOCK["now"] = datetime.fromisoformat(text + "+01:00")


class SturingTest(unittest.TestCase):
    def test_sturing_uit_stuurt_niets(self):
        at("2026-11-11T02:05:00")
        hass, coordinator = make(12)
        run(coordinator.async_refresh())
        self.assertEqual(coordinator.data.status, "laden")
        self.assertEqual(hass.calls, [])

    def test_laadnacht(self):
        at("2026-11-10T19:40:00")
        hass, coordinator = make(12)
        run(coordinator.async_set_enabled(True))
        self.assertEqual(coordinator.data.status, "gepland")
        self.assertEqual(hass.calls, [])

        # 02:00: vermogen zetten, forceren op charge, RS485 aan - in die volgorde.
        at("2026-11-11T02:00:20")
        run(coordinator.async_refresh())
        self.assertEqual(
            hass.calls,
            [("number.laadvermogen", 1900), ("select.forceer", "charge"), ("select.rs485", "enable")],
        )

        # Binnen de wachttijd na een opdracht wordt er niets nieuws gestuurd.
        hass.calls.clear()
        at("2026-11-11T02:00:40")
        run(coordinator.async_refresh())
        self.assertEqual(hass.calls, [])

        # Onderweg wordt alleen het vermogen bijgesteld.
        at("2026-11-11T03:30:00")
        hass.set("sensor.soc", 60)
        run(coordinator.async_refresh())
        self.assertEqual(coordinator.data.status, "laden")
        self.assertEqual([c[0] for c in hass.calls], ["number.laadvermogen"])
        self.assertEqual(hass.get("select.rs485"), "enable")

        # Vol: RS485 uit, forceren op charge, vermogen terug naar het maximum.
        hass.calls.clear()
        at("2026-11-11T04:50:00")
        hass.set("sensor.soc", 99)
        run(coordinator.async_refresh())
        self.assertEqual(coordinator.data.status, "klaar")
        self.assertEqual(
            hass.calls,
            [("select.rs485", "disable"), ("select.forceer", "charge"), ("number.laadvermogen", 2500)],
        )

        # Daarna, bij zakkende SoC in hetzelfde venster: geen nieuwe start.
        hass.calls.clear()
        at("2026-11-11T05:40:00")
        hass.set("sensor.soc", 95)
        run(coordinator.async_refresh())
        self.assertEqual(coordinator.data.status, "klaar")
        self.assertEqual(hass.calls, [])

    def test_uitzetten_tijdens_laden_geeft_vrij(self):
        at("2026-11-11T02:10:00")
        hass, coordinator = make(12)
        run(coordinator.async_set_enabled(True))
        self.assertEqual(hass.get("select.rs485"), "enable")
        run(coordinator.async_set_enabled(False))
        self.assertEqual(hass.get("select.rs485"), "disable")
        self.assertEqual(hass.get("select.forceer"), "charge")
        self.assertEqual(hass.get("number.laadvermogen"), "2500")

    def test_handmatig_ontladen_blijft_ongemoeid(self):
        at("2026-11-11T02:10:00")
        hass, coordinator = make(12)
        hass.set("select.rs485", "enable")
        hass.set("select.forceer", "discharge")
        run(coordinator.async_set_enabled(True))
        run(coordinator.async_set_sell_enabled(True))
        self.assertEqual(hass.calls, [])

    def test_marstek_onbereikbaar_stuurt_niets(self):
        at("2026-11-11T02:10:00")
        hass, coordinator = make(12)
        hass.set("select.rs485", "unavailable")
        run(coordinator.async_set_enabled(True))
        self.assertEqual(hass.calls, [])

    def test_verkoop(self):
        at("2026-11-10T15:10:00")
        hass, coordinator = make(95)
        run(coordinator.async_set_sell_enabled(True))
        self.assertEqual(coordinator.sell_plan.status, "gepland")
        self.assertEqual(hass.calls, [])

        # 16:00: ontlaadvermogen zetten, forceren op discharge, RS485 aan.
        at("2026-11-10T16:00:20")
        run(coordinator.async_refresh())
        self.assertEqual(coordinator.sell_plan.status, "verkopen")
        self.assertEqual([c[0] for c in hass.calls], ["number.ontlaadvermogen", "select.forceer", "select.rs485"])
        self.assertEqual(hass.get("select.forceer"), "discharge")
        self.assertEqual(hass.get("select.rs485"), "enable")

        # Op de reserve: stoppen en alles terug in de rusttoestand.
        hass.calls.clear()
        at("2026-11-10T16:45:00")
        hass.set("sensor.soc", 30)
        run(coordinator.async_refresh())
        self.assertEqual(coordinator.sell_plan.status, "geen")
        self.assertEqual(hass.get("select.rs485"), "disable")
        self.assertEqual(hass.get("select.forceer"), "charge")
        self.assertEqual(hass.get("number.ontlaadvermogen"), "2500")

    def test_verkoop_uit_tijdens_verkopen_geeft_vrij(self):
        at("2026-11-10T16:05:00")
        hass, coordinator = make(95)
        run(coordinator.async_set_sell_enabled(True))
        self.assertEqual(hass.get("select.forceer"), "discharge")
        run(coordinator.async_set_sell_enabled(False))
        self.assertEqual(hass.get("select.rs485"), "disable")
        self.assertEqual(hass.get("select.forceer"), "charge")

    def test_alleen_verkoop_aan_laat_handmatig_laden_met_rust(self):
        at("2026-11-10T12:00:00")
        hass, coordinator = make(50)
        hass.set("select.rs485", "enable")
        run(coordinator.async_set_sell_enabled(True))
        self.assertEqual(hass.calls, [])

    def test_zonder_ontlaadentiteit_geen_verkoop(self):
        at("2026-11-10T16:05:00")
        conf = dict(CONF, force_discharge_power_entity=None)
        hass, coordinator = make(95, conf)
        run(coordinator.async_set_sell_enabled(True))
        self.assertEqual(coordinator.sell_plan.status, "onbekend")
        self.assertEqual(hass.calls, [])


if __name__ == "__main__":
    unittest.main()
