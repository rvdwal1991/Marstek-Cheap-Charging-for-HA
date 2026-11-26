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
_registry = types.SimpleNamespace(
    async_get_entity_id=lambda domain, platform, unique_id: f"{domain}.{unique_id.split('_', 1)[1]}"
)
_er = _module("homeassistant.helpers.entity_registry", async_get=lambda hass: _registry)
_module("homeassistant.helpers", entity_registry=_er)
_module(
    "homeassistant.helpers.event",
    async_track_state_change_event=lambda *a: (lambda: None),
    async_track_time_change=lambda *a, **k: (lambda: None),
)
_module("homeassistant.helpers.storage", Store=_Store)
_module("homeassistant.helpers.update_coordinator", DataUpdateCoordinator=_Coordinator)
_dt = _module(
    "homeassistant.util.dt",
    utcnow=lambda: CLOCK["now"].astimezone(timezone.utc),
    now=lambda: CLOCK["now"],
    as_local=lambda moment: moment.astimezone(TZ),
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


MODBUS_CONF = {
    "connection": "modbus",
    "modbus_hub": "MarstekVenus",
    "modbus_slave": 1,
    "price_entity": "sensor.prijs",
    "soc_entity": "sensor.soc",
    "control_mode_entity": "sensor.rs485_raw",
    "force_mode_entity": "sensor.force_raw",
    "force_power_entity": "sensor.laad_raw",
    "force_discharge_power_entity": "sensor.ontlaad_raw",
    "max_discharge_power_entity": "sensor.max_ontlaad_raw",
    "house_power": 150,
}
MODBUS_SENSORS = {
    42000: "sensor.rs485_raw",
    42010: "sensor.force_raw",
    42020: "sensor.laad_raw",
    42021: "sensor.ontlaad_raw",
    44003: "sensor.max_ontlaad_raw",
}
VIPER_CONF = {
    "connection": "marstek_modbus",
    "price_entity": "sensor.prijs",
    "soc_entity": "sensor.soc",
    "control_mode_entity": "switch.rs485",
    "force_mode_entity": "select.force_mode",
    "force_power_entity": "number.laadvermogen",
    "force_discharge_power_entity": "number.ontlaadvermogen",
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
        self.config = types.SimpleNamespace(language="nl")
        self.states = types.SimpleNamespace(get=self.values.get)
        self.services = types.SimpleNamespace(async_call=self._call)

    async def _call(self, domain, service, data, blocking=False):
        if domain == "switch":
            self.calls.append((data["entity_id"], service))
            self.values[data["entity_id"]] = _State("on" if service == "turn_on" else "off")
            return
        if domain == "modbus":
            self.calls.append((data["hub"], data["slave"], data["address"], data["value"]))
            sensor = MODBUS_SENSORS.get(data["address"])
            if sensor:
                self.values[sensor] = _State(data["value"])
            return
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


class ModbusTest(unittest.TestCase):
    """Elfin EW11 / Modbus-hub: ruwe registerwaarden lezen, registers schrijven."""

    def make(self, soc):
        hass, coordinator = make(soc, MODBUS_CONF)
        hass.values.update(
            {
                "sensor.rs485_raw": _State(21947),
                "sensor.force_raw": _State(1),
                "sensor.laad_raw": _State(2500),
                "sensor.ontlaad_raw": _State(2500),
                "sensor.max_ontlaad_raw": _State(2500),
            }
        )
        return hass, coordinator

    def test_laadnacht_schrijft_registers(self):
        at("2026-11-10T19:40:00")
        hass, coordinator = self.make(12)
        run(coordinator.async_set_enabled(True))
        self.assertEqual(hass.calls, [])

        at("2026-11-11T02:00:20")
        run(coordinator.async_refresh())
        # vermogen (42020), richting charge (42010), RS485 aan 0x55AA (42000)
        self.assertEqual(
            hass.calls,
            [
                ("MarstekVenus", 1, 42020, 2100),
                ("MarstekVenus", 1, 42010, 1),
                ("MarstekVenus", 1, 42000, 21930),
            ],
        )

        hass.calls.clear()
        at("2026-11-11T03:30:00")
        hass.set("sensor.soc", 60)
        run(coordinator.async_refresh())
        self.assertEqual(coordinator.data.status, "laden")

        hass.calls.clear()
        at("2026-11-11T04:50:00")
        hass.set("sensor.soc", 99)
        run(coordinator.async_refresh())
        self.assertEqual(coordinator.data.status, "klaar")
        # RS485 uit 0x55BB, richting charge, vermogen terug naar het maximum
        self.assertEqual(
            hass.calls,
            [
                ("MarstekVenus", 1, 42000, 21947),
                ("MarstekVenus", 1, 42010, 1),
                ("MarstekVenus", 1, 42020, 2500),
            ],
        )

    def test_ruwe_waarden_worden_gelezen(self):
        decode = coordinator_module.ChargePlanCoordinator._decode_modbus
        self.assertEqual(decode("21930", "1"), ("enable", "charge"))
        self.assertEqual(decode("21947.0", "2"), ("disable", "discharge"))
        self.assertEqual(decode("0", "0"), (None, "stop"))
        self.assertEqual(decode(None, "x"), (None, None))

    def test_vasthouden_met_max_ontlaadregister(self):
        hass, coordinator = self.make(50)
        self.assertTrue(coordinator.can_hold)
        run(coordinator._async_set_number("max_discharge_power_entity", 0))
        self.assertEqual(hass.calls[-1], ("MarstekVenus", 1, 44003, 0))
        self.assertEqual(hass.get("sensor.max_ontlaad_raw"), "0")

    def test_geen_vasthouden_zonder_max_ontlaadregister(self):
        conf = {k: v for k, v in MODBUS_CONF.items() if k != "max_discharge_power_entity"}
        hass, coordinator = make(50, conf)
        self.assertFalse(coordinator.can_hold)


class MarstekModbusIntegrationTest(unittest.TestCase):
    """Integratie "Marstek Venus Modbus" (ViperRNMC): schakelaar + select."""

    def make(self, soc):
        hass, coordinator = make(soc, VIPER_CONF)
        hass.values.update(
            {
                "switch.rs485": _State("off"),
                "select.force_mode": _State("charge"),
                "number.laadvermogen": _State(2500),
                "number.ontlaadvermogen": _State(2500),
            }
        )
        return hass, coordinator

    def test_laadnacht(self):
        at("2026-11-10T19:40:00")
        hass, coordinator = self.make(12)
        run(coordinator.async_set_enabled(True))
        at("2026-11-11T02:00:20")
        run(coordinator.async_refresh())
        self.assertEqual(
            hass.calls,
            [("number.laadvermogen", 2100), ("select.force_mode", "charge"), ("switch.rs485", "turn_on")],
        )
        hass.calls.clear()
        at("2026-11-11T04:50:00")
        hass.set("sensor.soc", 99)
        run(coordinator.async_refresh())
        self.assertEqual(coordinator.data.status, "klaar")
        self.assertEqual(
            hass.calls,
            [("switch.rs485", "turn_off"), ("select.force_mode", "charge"), ("number.laadvermogen", 2500)],
        )

    def test_standby_is_stop(self):
        hass, coordinator = self.make(50)
        hass.set("switch.rs485", "on")
        hass.set("select.force_mode", "standby")
        inputs = coordinator._read_inputs()
        self.assertEqual((inputs["control_mode"], inputs["force_mode"]), ("enable", "stop"))
        run(coordinator._async_select("force_mode_entity", "stop"))
        self.assertEqual(hass.calls[-1], ("select.force_mode", "standby"))


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
            [("number.laadvermogen", 2100), ("select.forceer", "charge"), ("select.rs485", "enable")],
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

    def test_ontlaadvermogen_blijft_staan_na_laden(self):
        # De laadpaal-begrenzer zet 's nachts het maximale ontlaadvermogen op 150 W.
        # Dat mag na het bijladen niet in het forceer-ontlaadvermogen belanden.
        at("2026-11-11T02:10:00")
        hass, coordinator = make(12)
        hass.set("number.max_ontladen", 150)
        run(coordinator.async_set_enabled(True))
        at("2026-11-11T05:00:10")
        hass.set("sensor.soc", 97)
        run(coordinator.async_refresh())
        self.assertEqual(coordinator.data.status, "klaar")
        self.assertEqual(hass.get("select.rs485"), "disable")
        self.assertEqual(hass.get("number.ontlaadvermogen"), "2500")
        self.assertNotIn("number.ontlaadvermogen", [c[0] for c in hass.calls])

    def test_vermogen_springt_niet_heen_en_weer(self):
        at("2026-11-11T02:10:00")
        hass, coordinator = make(12)
        run(coordinator.async_set_enabled(True))
        hass.calls.clear()
        # Een stap van 100 W verschil onderweg leidt niet tot een nieuwe opdracht.
        hass.set("number.laadvermogen", coordinator.data.power_w + 100)
        at("2026-11-11T02:11:00")
        run(coordinator.async_refresh())
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
        # (Het vermogen wordt alleen gezet als het afwijkt van wat er al stond.)
        self.assertEqual([c[0] for c in hass.calls][-2:], ["select.forceer", "select.rs485"])
        self.assertEqual(float(hass.get("number.ontlaadvermogen")), coordinator.sell_plan.power_w)
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

    def test_negatieve_prijs_laadt_op_vol_vermogen(self):
        # Standaard aan, ook als prijssturing en verkoop uit staan.
        at("2026-11-11T13:10:00")
        hass, coordinator = make(40)
        forecast = [dict(row) for row in FORECAST]
        for row in forecast:
            if row["start_date"].startswith("2026-11-11T13:00"):
                row["price_tax_included"] = {"amount": -250000}
        hass.values["sensor.prijs"] = _State("0", {"forecast": forecast})
        hass.set("number.laadvermogen", 1200)
        self.assertTrue(coordinator.negative_enabled)
        run(coordinator.async_refresh())
        self.assertTrue(coordinator.negative_active)
        self.assertEqual(coordinator.data.status, "laden")
        self.assertIn("Negatieve prijs", coordinator.data.text)
        self.assertEqual(
            hass.calls,
            [("number.laadvermogen", 2500), ("select.forceer", "charge"), ("select.rs485", "enable")],
        )

        # Vol: vrijgeven.
        hass.calls.clear()
        at("2026-11-11T13:40:00")
        hass.set("sensor.soc", 99)
        run(coordinator.async_refresh())
        self.assertFalse(coordinator.negative_active)
        self.assertEqual(hass.get("select.rs485"), "disable")

    def test_negatief_venster_slaat_duurste_uur_over_en_smeert_uit(self):
        # 13:00 -0,03, 14:00 -0,20, 15:00 -0,12; accu op 40 %.
        hass, coordinator = make(40)
        forecast = [dict(row) for row in FORECAST]
        for row in forecast:
            for hour, euro in (("13", -0.03), ("14", -0.20), ("15", -0.12)):
                if row["start_date"].startswith(f"2026-11-11T{hour}:00"):
                    row["price_tax_included"] = {"amount": round(euro * 1e7)}
        hass.values["sensor.prijs"] = _State("0", {"forecast": forecast})
        hass.set("number.laadvermogen", 1200)

        # Eerste uur levert het minst op: niet laden.
        at("2026-11-11T13:10:00")
        run(coordinator.async_refresh())
        self.assertFalse(coordinator.negative_active)
        self.assertEqual(hass.calls, [])
        self.assertEqual(hass.get("select.rs485"), "disable")

        # Tweede uur: laden, uitgesmeerd over dit en het volgende uur.
        at("2026-11-11T14:00:30")
        run(coordinator.async_refresh())
        self.assertTrue(coordinator.negative_active)
        power = hass.calls[0][1]
        self.assertEqual(hass.calls[0][0], "number.laadvermogen")
        self.assertTrue(1500 <= power < 2500)
        self.assertEqual(hass.get("select.rs485"), "enable")
        self.assertIn("2 van 2 negatieve uren", coordinator.data.text)

        # Voorbij het venster: vrijgeven.
        at("2026-11-11T16:00:30")
        run(coordinator.async_refresh())
        self.assertEqual(hass.get("select.rs485"), "disable")

    def test_negatieve_prijs_voorbij_geeft_vrij(self):
        at("2026-11-11T13:10:00")
        hass, coordinator = make(40)
        forecast = [dict(row) for row in FORECAST]
        for row in forecast:
            if row["start_date"].startswith("2026-11-11T13:00"):
                row["price_tax_included"] = {"amount": -250000}
        hass.values["sensor.prijs"] = _State("0", {"forecast": forecast})
        run(coordinator.async_refresh())
        self.assertEqual(hass.get("select.rs485"), "enable")
        at("2026-11-11T14:00:30")
        run(coordinator.async_refresh())
        self.assertEqual(hass.get("select.rs485"), "disable")
        self.assertEqual(hass.get("select.forceer"), "charge")

    def test_negatieve_prijs_uit_doet_niets(self):
        at("2026-11-11T13:10:00")
        hass, coordinator = make(40)
        forecast = [dict(row) for row in FORECAST]
        for row in forecast:
            if row["start_date"].startswith("2026-11-11T13:00"):
                row["price_tax_included"] = {"amount": -250000}
        hass.values["sensor.prijs"] = _State("0", {"forecast": forecast})
        run(coordinator.async_set_negative_enabled(False))
        self.assertEqual(hass.calls, [])
        self.assertFalse(coordinator.negative_active)

    def test_positieve_prijs_laat_handmatig_met_rust(self):
        # Alleen de negatieve-prijsoptie aan: handmatig forceren blijft staan.
        at("2026-11-11T13:10:00")
        hass, coordinator = make(40)
        hass.set("select.rs485", "enable")
        hass.set("select.forceer", "stop")
        run(coordinator.async_refresh())
        self.assertEqual(hass.calls, [])

    def test_stroomschema_voor_de_kaart(self):
        at("2026-11-10T19:40:00")
        hass, coordinator = make(12)
        run(coordinator.async_set_enabled(True))
        flow = coordinator.flow
        self.assertEqual(flow["tijdlijn"][0], {"titel": "Nu", "detail": "Zelf regelen (anti-feed)", "soort": "nu"})
        self.assertEqual(flow["tijdlijn"][1]["titel"], "02:00 – 05:00 · bijladen")
        self.assertEqual(flow["tijdlijn"][1]["soort"], "actie")
        self.assertEqual(flow["tijdlijn"][-1]["titel"], "05:00 · klaar")
        lanes = {lane["titel"]: lane for lane in flow["banen"]}
        self.assertEqual([s["soort"] for s in lanes["Bijladen"]["stappen"]], ["ok", "ok", "actie"])
        self.assertEqual(lanes["Bijladen"]["stappen"][0]["detail"], "23:00 – 07:00")
        self.assertTrue(lanes["Bijladen"]["aan"])
        self.assertEqual(lanes["Bijladen"]["schakelaar"], "switch.prijssturing")
        self.assertEqual(lanes["Negatieve prijs"]["schakelaar"], "switch.negatieve_prijs")
        self.assertEqual(
            [lane["id"] for lane in flow["banen"]],
            ["bijladen", "verkoop", "negatief", "vasthouden", "geen_verlies"],
        )
        overview = flow["overzicht"]
        self.assertEqual(overview["status"], "gepland")
        self.assertEqual(overview["soc"], 12)
        self.assertIn("kostprijs", overview)
        kinds = {row["soort"] for row in flow["prijzen"]}
        self.assertIn("laden", kinds)
        self.assertTrue(all(set(row) == {"start", "prijs", "soort"} for row in flow["prijzen"]))
        self.assertFalse(lanes["Verkoop"]["aan"])
        self.assertEqual(lanes["Verkoop"]["stappen"][-1]["soort"], "eind")
        self.assertEqual([s["soort"] for s in lanes["Negatieve prijs"]["stappen"]], ["stop", "eind"])
        result = flow["resultaat"]
        self.assertEqual([line["titel"] for line in result["regels"]], ["Bijladen", "Verkoop"])
        self.assertGreater(result["regels"][0]["bedrag"], 0.3)
        self.assertIsNone(result["regels"][1]["bedrag"])
        self.assertEqual(result["totaal"], result["regels"][0]["bedrag"])
        self.assertEqual(coordinator.expected_gain, result["totaal"])

    def test_stroomschema_bijladen_uit(self):
        at("2026-11-10T19:40:00")
        hass, coordinator = make(12)
        run(coordinator.async_refresh())
        self.assertEqual(coordinator.flow["tijdlijn"][1]["soort"], "eind")
        self.assertIn("staat uit", coordinator.flow["tijdlijn"][1]["detail"])

    def test_gerealiseerde_opbrengst(self):
        at("2026-11-11T01:59:00")
        hass, coordinator = make(12)
        run(coordinator.async_set_enabled(True))
        # 02:00-05:00: de integratie laadt; de teller loopt 4 kWh op in stappen.
        at("2026-11-11T02:00:20")
        run(coordinator.async_refresh())
        self.assertEqual(hass.get("select.rs485"), "enable")
        geladen = 1837.74
        for minute in range(10, 170, 10):
            at(f"2026-11-11T{2 + minute // 60:02d}:{minute % 60:02d}:00")
            geladen += 0.25
            hass.set("sensor.geladen", round(geladen, 2))
            run(coordinator.async_refresh())
        ledger = coordinator.ledger
        self.assertAlmostEqual(ledger.day_charged_kwh, 4.0, places=2)
        self.assertAlmostEqual(ledger.stock_kwh, 4.0 * (1418.82 / 1837.74), places=2)
        self.assertEqual(round(ledger.day_gain, 2), 0.0)
        # 08:00, prijs ca. 0,55: 1 kWh uit de accu gebruikt.
        at("2026-11-11T08:10:00")
        hass.set("sensor.soc", 80)
        run(coordinator.async_refresh())
        at("2026-11-11T08:20:00")
        hass.set("sensor.ontladen", 1419.82)
        run(coordinator.async_refresh())
        self.assertGreater(ledger.day_gain, 0.03)
        self.assertLess(ledger.day_gain, 0.20)
        result = coordinator.flow["resultaat"]
        self.assertEqual(result["vandaag"], round(ledger.day_gain, 2))
        self.assertEqual(result["week"], round(ledger.week_gain, 2))
        self.assertGreater(result["voorraad_kwh"], 1.5)

    def _met_voorraad(self, kostprijs_totaal=0.92, kwh=2.17):
        hass, coordinator = make(70)
        coordinator.ledger.stock_kwh = kwh
        coordinator.ledger.stock_cost = kostprijs_totaal
        coordinator.ledger.last_charged = 1837.74
        coordinator.ledger.last_discharged = 1418.82
        return hass, coordinator

    def test_vasthouden_onder_de_kostprijs(self):
        # 11 nov 13:00: prijs ca. 0,58; voorraad met kostprijs 0,60 (16:00 kost 0,62).
        at("2026-11-11T13:10:00")
        hass, coordinator = self._met_voorraad(kostprijs_totaal=2.17 * 0.60)
        run(coordinator.async_refresh())
        self.assertTrue(coordinator.hold_active)
        self.assertEqual(hass.calls, [("number.max_ontladen", 0)])
        self.assertEqual(hass.get("select.rs485"), "disable")  # anti-feed blijft aan
        self.assertEqual(coordinator.hold_until.astimezone(TZ).strftime("%H:%M"), "16:00")
        lane = {l["titel"]: l for l in coordinator.flow["banen"]}["Vasthouden"]
        self.assertEqual([s["soort"] for s in lane["stappen"]], ["ok", "ok", "actie"])
        self.assertEqual(coordinator.flow["tijdlijn"][0]["detail"], "Vasthouden: ontladen geblokkeerd")

        # Een andere automatisering (laadpaal) zet het ontlaadvermogen op 150 W:
        # terug naar 0, en 150 W onthouden voor na afloop.
        hass.calls.clear()
        hass.set("number.max_ontladen", 150)
        at("2026-11-11T13:20:00")
        run(coordinator.async_refresh())
        self.assertEqual(hass.calls, [("number.max_ontladen", 0)])

        # 16:00: de prijs komt boven de kostprijs, ontladen wordt vrijgegeven.
        hass.calls.clear()
        at("2026-11-11T16:00:30")
        run(coordinator.async_refresh())
        self.assertFalse(coordinator.hold_active)
        self.assertEqual(hass.calls, [("number.max_ontladen", 150)])

    def test_niet_vasthouden_boven_de_kostprijs_of_zonder_voorraad(self):
        at("2026-11-11T17:10:00")
        hass, coordinator = self._met_voorraad()
        run(coordinator.async_refresh())
        self.assertFalse(coordinator.hold_active)
        self.assertEqual(hass.calls, [])
        at("2026-11-11T13:10:00")
        hass, coordinator = make(70)
        run(coordinator.async_refresh())
        self.assertFalse(coordinator.hold_active)
        self.assertEqual(hass.calls, [])

    def test_vasthouden_uitzetten_geeft_vrij(self):
        at("2026-11-11T13:10:00")
        hass, coordinator = self._met_voorraad(kostprijs_totaal=2.17 * 0.60)
        run(coordinator.async_refresh())
        self.assertEqual(hass.get("number.max_ontladen"), "0")
        run(coordinator.async_set_hold_enabled(False))
        self.assertEqual(hass.get("number.max_ontladen"), "2500")

    def test_lege_accu_laat_de_voorraad_vervallen(self):
        at("2026-11-11T13:10:00")
        hass, coordinator = self._met_voorraad(kostprijs_totaal=2.17 * 0.60)
        hass.set("sensor.soc", 12)
        run(coordinator.async_refresh())
        self.assertEqual(coordinator.ledger.stock_kwh, 0.0)
        self.assertFalse(coordinator.hold_active)
        self.assertEqual(hass.calls, [])

    def test_geen_verlies_dwingt_vasthouden_af(self):
        at("2026-11-11T13:10:00")
        hass, coordinator = self._met_voorraad(kostprijs_totaal=2.17 * 0.60)
        run(coordinator.async_set_hold_enabled(False))
        self.assertFalse(coordinator.hold_active)
        self.assertEqual(hass.get("number.max_ontladen"), "2500")
        run(coordinator.async_set_no_loss_enabled(True))
        self.assertTrue(coordinator.hold_active)
        self.assertEqual(hass.get("number.max_ontladen"), "0")
        lanes = {l["titel"]: l for l in coordinator.flow["banen"]}
        self.assertTrue(lanes["Vasthouden"]["aan"])
        self.assertTrue(lanes["Geen verlies"]["aan"])
        self.assertEqual(lanes["Geen verlies"]["stappen"][-1]["soort"], "actie")
        self.assertEqual(lanes["Geen verlies"]["schakelaar"], "switch.geen_verlies")
        run(coordinator.async_set_no_loss_enabled(False))
        self.assertEqual(hass.get("number.max_ontladen"), "2500")

    def test_geen_verlies_verkoopt_niet_onder_de_kostprijs(self):
        # 10 nov 16:00: verkoopprijs ca. 0,69. Voorraad met kostprijs 0,80.
        at("2026-11-10T16:05:00")
        hass, coordinator = make(95)
        coordinator.ledger.stock_kwh = 2.0
        coordinator.ledger.stock_cost = 1.60
        coordinator.ledger.last_charged = 1837.74
        coordinator.ledger.last_discharged = 1418.82
        run(coordinator.async_set_hold_enabled(False))
        run(coordinator.async_set_no_loss_enabled(True))
        run(coordinator.async_set_sell_enabled(True))
        self.assertEqual(coordinator.sell_plan.status, "verkopen")
        self.assertTrue(coordinator.sell_blocked)
        self.assertNotEqual(hass.get("select.forceer"), "discharge")
        verkoop = {l["titel"]: l for l in coordinator.flow["banen"]}["Verkoop"]
        self.assertEqual(verkoop["stappen"][-1]["detail"], "Tegengehouden door geen verlies")
        # Zonder 'geen verlies' wordt er wel verkocht.
        run(coordinator.async_set_no_loss_enabled(False))
        self.assertEqual(hass.get("select.forceer"), "discharge")


if __name__ == "__main__":
    unittest.main()
