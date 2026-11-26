<img src="custom_components/marstek_goedkoop_laden/brand/icon.png" width="96" align="right" alt="">

# Marstek Günstig Laden für Home Assistant

[🇬🇧 English](README.md) · [🇳🇱 Nederlands](README.nl.md) · [🏳️ Frysk](README.fy.md) · 🇩🇪 Deutsch · [🇫🇷 Français](README.fr.md) · [🇪🇸 Español](README.es.md) · [🇸🇪 Svenska](README.sv.md) · [🇳🇴 Norsk](README.nb.md)

[![Open your Home Assistant instance and open this repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=rvdwal1991&repository=Marstek-Cheap-Charging-for-HA&category=integration)
[![Open your Home Assistant instance and start setting up the integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=marstek_goedkoop_laden)

Lädt einen Marstek-Venus-Heimspeicher in den günstigsten Stunden eines dynamischen
Stromvertrags aus dem Netz nach, sodass er voll ist, bevor die Preise steigen.

Ausgangspunkt ist die **Eigenversorgung**. Der Speicher regelt sich weiterhin selbst (anti-feed,
null am Zähler). Diese Integration fügt genau eine Sache hinzu: Laden aus dem Netz in den
günstigsten Stunden. Dazu gibt es eine eigene, standardmäßig ausgeschaltete Option, um
**Überschuss zu verkaufen**, und zwar in den teuersten Stunden.

> **Hardware und Kompatibilität.** Die Integration steuert eine Marstek Venus über ihre RS485-Steuerregister.
> Nur die erste Zeile wurde an einem echten Speicher getestet:
>
> | Anbindung | Modell | Status |
> |---|---|---|
> | LilyGO T-CAN485 + ESPHome (RS485) | Venus E v2 | **Getestet** an echter Hardware (der Aufbau, auf dem sie entwickelt wurde) |
> | Modbus-Hub in Home Assistant, über RS485-zu-TCP-Wandler (Elfin EW11 und ähnliche) | Venus E v1/v2 | Nur mit simulierten Aufrufen getestet |
> | Modbus-Hub in Home Assistant, direkt über Ethernet | Venus E v3 | Nur mit simulierten Aufrufen getestet |
> | Integration *Marstek Venus Modbus* (ViperRNMC) | Venus E v3 | Nur mit simulierten Aufrufen getestet |
> | Eine der obigen | Venus A, Venus D, andere Modelle | **Nicht geprüft, nicht getestet.** Sie sollen dieselben Steuerregister haben, das ist aber unbestätigt. Stelle die Akkukapazität in den Optionen ein (Standard 5,12 kWh). |
> | Cloud, App oder andere Integrationen | beliebig | Nicht unterstützt |
>
> Die Anbindungen im Detail:
>
> - **LilyGO T-CAN485 mit ESPHome** über RS485, mit der Konfiguration
>   [MarstekVenus-LilygoRS485](https://github.com/Superduper1969/MarstekVenus-LilygoRS485).
>   Das ist der Aufbau, auf dem die Integration entwickelt und getestet wurde. Sie nutzt die
>   Entitäten, die dieser Aufbau bereitstellt: *RS485 Control Mode*, *Forcible Charge/Discharge*,
>   *Forcible Charge Power* (erforderlich) und optional *Max. Charge Power*, *Max. Discharge Power*,
>   *Forcible Discharge Power*, *Discharging Cutoff Capacity* sowie die Zähler für die insgesamt
>   geladene und entladene Energie.
> - **Modbus in Home Assistant**, mit einem Modbus-Hub, den du selbst in der `configuration.yaml` definierst:
>   ein Elfin EW11 oder ein anderer RS485-zu-TCP-Wandler
>   ([MarstekVenus-ElfinEW11](https://github.com/Superduper1969/MarstekVenus-ElfinEW11)) oder der
>   **Venus E v3 direkt über Ethernet** (Modbus TCP, Port 502, Unit 1, EMS V144 oder neuer;
>   [MarstekVenusV3-modbus-TCP-IP](https://github.com/fonske/MarstekVenusV3-modbus-TCP-IP)). Die
>   Integration liest die Registersensoren dieses Aufbaus und schreibt mit `modbus.write_register` die Register 42000
>   (RS485-Steuerung), 42010 (Force-Modus), 42020/42021 (erzwungene Lade-/Entladeleistung) und, wenn du die Sensoren angibst,
>   44002/44003 (maximale Lade-/Entladeleistung). Mit der maximalen
>   Entladeleistung funktionieren auch *Halten* und *Kein Verlust*; ohne sie sind sie nicht verfügbar. Die
>   Venus E v3 hält ihren Ladestand im Register 34002 (Skalierung 0,1), nicht in 32104.
> - **Die Integration *Marstek Venus Modbus***
>   ([ViperRNMC/marstek_venus_modbus](https://github.com/ViperRNMC/marstek_venus_modbus)), die
>   ebenfalls Modbus TCP spricht (Ethernet bei einer Venus E v3 oder ein RS485-Gateway). Wähle sie, wenn du
>   diese Integration ohnehin nutzt: Sie liefert die Entitäten (`switch` RS485-Steuermodus, `select`
>   Force-Modus, `number` Leistungen). Aktiviere dort zuerst den Schalter *RS485 control mode* und die Auswahl *Force mode*,
>   sie sind standardmäßig deaktiviert.
>
> Die Optionen Modbus und Marstek Venus Modbus sind **neu und bisher nur mit simulierten
> Aufrufen getestet, nicht an echter Hardware**.
>
> Andere Wege, den Speicher anzubinden (Cloud, andere Integrationen), sind ungetestet und
> funktionieren höchstwahrscheinlich nicht, weil sie diese RS485-Steuerentitäten nicht anbieten.
>
> **Dynamische Strompreise:** Diese Integration ist nur mit einem **dynamischen
> Stromvertrag** sinnvoll, bei dem sich der Preis jede Stunde ändert. Sie lädt in den günstigsten Stunden und meidet
> die teuren, bei einem Festpreis ist also nichts zu gewinnen. Sie wurde für den
> niederländischen Markt und die Preise von Zonneplan entwickelt (Stundenpreise, für den nächsten Tag zwischen 13:00 und
> 15:00 Uhr veröffentlicht). Jeder Preissensor mit einer Stundenpreisliste als Attribut funktioniert, siehe
> [Preissensor](#preissensor).
>
> **Sprache:** Der Plantext, das Flussdiagramm und die Karten folgen der Option *Sprache*
> (Automatisch, Nederlands, English, Frysk, Deutsch, Français, Español, Svenska oder Norsk;
> Automatisch folgt Home Assistant, wenn dessen Sprache dazugehört, sonst Englisch). Entitätsnamen folgen der Sprache von Home Assistant. Statuswerte und Attributnamen (`laden`, `tekst`, …) sind fest.

## Was sie tut

1. **Lohnt sich das Laden?** Eine Stunde ist günstig genug, wenn ihr Preis niedriger ist als
   `Wirkungsgrad × (Mittelwert der 6 teuersten Stunden der nächsten 18 Stunden) − Marge`.
   Der Wirkungsgrad (Round-Trip aus Laden und Entladen, bei meinem Gerät etwa 77 %) wird aus
   den Energiezählern der Marstek gemessen.
2. **Fenster.** Der erste Block günstiger Stunden ist das Ladefenster. Eine oder zwei Stunden, die
   knapp nicht günstig genug sind, unterbrechen den Block nicht; geladen wird aber nur in den günstigen Stunden
   selbst.
3. **Ladestunden.** Innerhalb dieses Fensters wählt sie die günstigsten Stunden, genau so viele wie nötig,
   um vom aktuellen SoC auf 100 % zu kommen. Ist das Fenster zu kurz, um den Akku zu füllen, plant sie
   nur, was hineinpasst, und sagt das im Plantext.
4. **Leistung verteilen.** Die Ladeleistung ist die noch einzuladende Energie geteilt durch die verbleibende Zeit
   in den Ladestunden. So bleibt die Last auf dem Netzanschluss und dem Hausstromkreis so gering
   wie möglich. Die Leistung wird unterwegs angepasst.
5. **Fertig ist fertig.** Sind die Ladestunden vorbei oder ist der Akku voll, geht die Marstek
   zurück in den anti-feed-Betrieb. Im selben Fenster startet sie nicht erneut und hält die Ladung nicht.

Es werden nur **veröffentlichte** Preise verwendet. Der Plan für die Nacht erscheint daher, sobald
die Preise für morgen bekannt sind (bei Zonneplan zwischen 13:00 und 15:00 Uhr).

Beispiel (10. November 2026, Akku bei 12 %): günstiges Fenster 23:00–07:00 Uhr, Laden um 02:00,
03:00 und 04:00 Uhr mit etwa 1900 W zu durchschnittlich € 0,37, gegenüber € 0,55–0,67 tagsüber.

## Laden bei negativem Preis

Ist der Stundenpreis negativ, lädt der Akku aus dem Netz, unabhängig vom Ladeplan
und auch bei ausgeschalteter Preissteuerung. Dafür gibt es einen eigenen Schalter, **standardmäßig an**.

Betrachtet wird das ganze **Fenster** aufeinanderfolgender negativer Stunden, nicht nur die aktuelle Stunde,
und es wird das Beste daraus gemacht:

1. Sie berechnet, wie viel der Akku noch aufnehmen kann (SoC bis 100 %).
2. Sie verteilt diese Energie **nach dem Wert** auf die Stunden: Je negativer der Preis, desto mehr
   wird in dieser Stunde geladen (bis zu dem, was eine Stunde bei maximaler Leistung aufnehmen kann). Beispiel: drei
   negative Stunden mit −€ 0,03, −€ 0,20 und −€ 0,12 und noch 3 kWh zu laden. Die Stunde mit −€ 0,20 bekommt
   etwa 1,9 kWh und die Stunde mit −€ 0,12 etwa 1,2 kWh. Die Stunde mit −€ 0,03 läge unter der minimalen
   Ladeleistung, fällt daher weg, und ihr Anteil geht an die anderen beiden.
3. Weil die Energie auf die Stunden verteilt wird, bleibt die Leistung niedriger, als wenn kurz mit voller
   Leistung geladen würde. Kann der Akku mehr aufnehmen, als das Fenster bietet, wird jede Stunde
   bis zum Maximum gefüllt. Eine einzelne Stunde, die den Akku nicht füllen kann, wird mit voller Leistung geladen.
4. Der Plantext und das Flussdiagramm zeigen das Fenster, die gewählten Stunden, die Leistung und den erwarteten
   Gewinn (was du fürs Laden bezahlt bekommst).

Die Option *Negativer Preis: Aufteilung der Energie* schaltet zwischen zwei Arten um:

- **Nach Wert verteilen** (Standard): wie oben beschrieben, geringere Leistung, etwas weniger Gewinn.
- **Maximaler Ertrag**: Die Stunden werden nacheinander gefüllt, der beste Preis zuerst, jeweils mit voller Leistung, und der
  Rest geht an die nächstbeste Stunde. Im Beispiel nimmt die Stunde mit −€ 0,20 2,25 kWh mit voller Leistung auf
  und die Stunde mit −€ 0,12 die restlichen 0,8 kWh, was etwa € 0,55 statt € 0,52 einbringt. Der Preis dafür sind
  mehr kurze Phasen mit voller Leistung.

Sobald der Preis wieder positiv wird oder der Akku voll ist, geht die Marstek zurück in den
anti-feed-Betrieb. Der Plan wird jede Minute neu berechnet; eine Stunde, die bereits in Gebrauch war, bekommt etwas zusätzlichen
Spielraum, bevor sie wegen Unterschreitung der Mindestleistung ausscheidet.

Die Grenze ist einstellbar (*Negativer Preis: Grenze*, Standard € 0,00). Der Preis stammt vom
Preissensor, bei Zonneplan ist das also der Preis inklusive Steuern.

## Solarprognose

Mit Solarmodulen wird der Akku tagsüber kostenlos gefüllt. Lädst du ihn nachts voll aus dem
Netz, bleibt für den Solarüberschuss kein Platz mehr, und er geht für wenig oder gar kein Geld ins Netz,
was jetzt wichtiger wird, da die Netto-Messung (*salderingsregeling*) ausläuft. Deshalb
berücksichtigt die Integration den erwarteten Solarertrag:

1. Sie liest die Prognose aus dem **Energie-Dashboard** von Home Assistant (*Einstellungen → Dashboards →
   Energie → Solarmodule → Solarproduktionsprognose*). Forecast.Solar, Solcast, Open-Meteo und
   andere Prognose-Integrationen funktionieren, und es ist nichts Zusätzliches einzurichten. Ohne Prognose
   dort ändert sich nichts.
2. Sie berechnet den erwarteten Überschuss: je Stunde die Prognose, multipliziert mit der Einstellung
   für die Zuverlässigkeit (Standard 70 %), minus deinen Eigenverbrauch (die Einstellung *Verkauf: durchschnittlicher Eigenverbrauch*).
3. Sie lädt nachts nur so viel, dass bis zum Sonnenaufgang Platz für diesen Überschuss bleibt: die Energie, die dein
   Eigenverbrauch bis dahin aufzehrt, plus das, was noch gebraucht wird. An einem
   sonnigen Tag können das ein paar kWh statt eines vollen Akkus sein oder gar nichts (der Plantext
   sagt dann, dass die Sonne den Akku füllt).
4. Ein bewölkter Tag ergibt einen kleinen oder keinen Überschuss, und dann wird der Akku wie bisher voll geladen.

Mit *Solarprognose verwenden* lässt sich das ausschalten. Die Prognose wird alle 30 Minuten gelesen. Sie
verringert nur die Lademenge; Ladestunden verschiebt sie nicht, und am Verkaufen ändert sie nichts.

## Halten unter Einstandspreis

Aus dem Netz geladene Energie hat einen Einstandspreis: den Ladepreis geteilt durch den Wirkungsgrad. Würde
der Akku diese Energie direkt nach dem Laden in Stunden wieder abgeben, die günstiger sind als dieser
Einstandspreis, würde das Laden Geld kosten. Das Entladen wird daher gesperrt, solange:

- sich nachgeladener Vorrat im Akku befindet (siehe *Ertrag*), und
- der Stundenpreis niedriger ist als der Einstandspreis dieses Vorrats.

Das Haus bezieht dann Netzstrom, der in diesem Moment günstiger ist als das, was im Akku steckt.
Sobald der Preis den Einstandspreis erreicht oder der Vorrat aufgebraucht ist, übernimmt die Marstek wieder.
Dafür gibt es einen eigenen Schalter, **standardmäßig an**.

Technisch setzt die Integration die maximale Entladeleistung (*Max. Discharge power*) auf 0.
Die Marstek bleibt im anti-feed-Betrieb, das Laden aus Solarüberschuss läuft also weiter. Setzt eine andere
Automatisierung diese Leistung während des Haltens auf einen anderen Wert (zum Beispiel ein Limiter für eine
Wallbox), merkt sich die Integration diesen Wert, setzt ihn wieder auf 0 und stellt
danach den gemerkten Wert wieder her.

Hinweis: Die Marstek kann aus dem Netz geladene Energie nicht von Solarenergie unterscheiden. Während eines Haltens wird
daher der ganze Akku nicht entladen.

## Kein Verlust

Ein separater Schalter (standardmäßig aus), der die Integration streng macht: Aus dem Netz geladene Energie wird
nie unter ihrem Einstandspreis verwendet oder verkauft.

- **Halten wird erzwungen**, auch wenn der Schalter *Halten* aus ist.
- **Verkaufen unter Einstandspreis wird blockiert.** Befindet sich nachgeladener Vorrat im Akku und
  liegt der Verkaufspreis unter dessen Einstandspreis, wird nichts verkauft.

Jede gebuchte kWh bringt dann mindestens ihren Einstandspreis ein, der Tagesertrag kann also nicht unter null fallen.
Was sich nicht ausschließen lässt:

- **Stillstand.** Bleibt der Preis lange unter dem Einstandspreis, bleibt der Akku
  für das Entladen gesperrt, auch für gespeicherte Solarenergie.
- **Abweichender Wirkungsgrad.** Der Einstandspreis nutzt den durchschnittlichen Wirkungsgrad. Gibt der Akku
  in einem Zyklus weniger zurück, ist er leer, bevor der Vorrat in den Büchern aufgebraucht ist; der Rest
  verfällt, ohne einen Verlust zu buchen.
- **Verschleiß** des Akkus wird nicht mitgezählt; nutze dafür den Mindestgewinn pro kWh.

Die Integration rechnet sofort neu, wenn ein neuer Preiszeitraum beginnt, sodass ein Halten nie
bis zu einer Minute zu spät beginnt.

## Verkaufen (optional)

Das Verkaufen hat einen eigenen Schalter und ist unabhängig vom Laden. Verkauft wird nur, was wirklich übrig ist. Eine Stunde wird zum Verkaufen genutzt, wenn all dies zutrifft:

1. **Eine günstige Ladung steht an**: Ein Ladefenster mit veröffentlichten Preisen liegt voraus, die Kosten
   des Wiederaufladens sind also bekannt.
2. **Der Erlös liegt deutlich über dem Wiederaufladen**: Verkaufspreis ≥ Ladepreis geteilt durch den
   Wirkungsgrad, plus die Verkaufsmarge (Standard € 0,10 pro kWh).
3. **Es gibt Überschuss über der Reserve.** Die Reserve ist die Entladegrenze der Marstek plus
   der erwartete Eigenverbrauch bis zum Wiederaufladen (durchschnittliche Hausleistung × Stunden), mit einem
   einstellbaren Minimum (Standard 20 %).
4. **Es ist eine der teuersten Stunden** vor dem Ladefenster.

Wie beim Laden wird die Verkaufsleistung auf die gewählten Stunden verteilt. Bei der Reserve hört das Verkaufen
auf, und die Marstek geht zurück in den anti-feed-Betrieb.

Im Winter gibt es selten einen Überschuss: Bei einem 5-kWh-Akku verbraucht der Eigenverbrauch bis zur nächsten
Ladung meist die ganze Ladung. Die Option bringt vor allem dann etwas, wenn die Sonne den Akku
füllt und es abends eine Preisspitze gibt.

**Nach dem Ende der Netto-Messung** (der niederländischen *salderingsregeling*, 1. Januar 2027) bringt Einspeisen
weniger als der Stundenpreis. Stelle dann *Verkaufspreis: Faktor* und *Abzug* ein: Verkaufspreis =
Stundenpreis × Faktor − Abzug. Für den reinen Marktpreis bei Zonneplan sind das etwa
0,826 und € 0,108.

## Die Marstek steuern

Die Integration steuert den Akku über die RS485-Schnittstelle (LilyGO T-CAN485 mit
ESPHome):

| Moment | Befehle |
|---|---|
| Laden starten | Ladeleistung setzen → *Forcible charge/discharge* auf `charge` → *RS485 Control Mode* auf `enable` |
| Beim Laden | Ladeleistung anpassen (Schritte von 100 W) |
| Fertig oder Preissteuerung aus | *RS485 Control Mode* auf `disable`, Forcible zurück auf `charge`, Ladeleistung zurück auf das Maximum |
| Verkaufen starten | Entladeleistung setzen → Forcible auf `discharge` → *RS485 Control Mode* auf `enable` |
| Verkaufen beendet oder Verkauf aus | wie „fertig“: zurück in den Ruhezustand |

Erzwungenes **Ent**laden, das du selbst startest, bleibt unangetastet. Erzwungenes Laden, das du
selbst startest, wird zurückgesetzt, solange die Preissteuerung an ist; schalte sie zuerst aus, wenn du das möchtest.

## Entitäten

| Entität | Inhalt |
|---|---|
| `switch.*_price_control` | An: Der Ladeplan wird ausgeführt. Aus: Die Marstek regelt alles selbst. Ausschalten setzt die Marstek sofort zurück in den anti-feed-Betrieb. |
| `switch.*_charge_at_negative_price` | An (Standard): immer mit voller Leistung laden, wenn der Stundenpreis negativ ist. Attribut `nu_actief`. |
| `switch.*_hold_below_cost_price` | An (Standard): nicht entladen, solange der Stundenpreis unter dem Einstandspreis des geladenen Vorrats liegt. Attribute `nu_actief`, `tot`, `voorraad_kwh`, `kostprijs`. |
| `switch.*_no_loss` | An: Halten erzwungen und nie unter Einstandspreis verkaufen. Attribute `vasthouden_actief`, `verkoop_tegengehouden`, `voorraad_kwh`, `kostprijs`. |
| `switch.*_selling` | An: Überschuss wird in den teuersten Stunden verkauft. Unabhängig von der Preissteuerung. |
| `sensor.*_sell_plan` | Zustand: `verkopen`, `gepland`, `geen` oder `onbekend`. Attribute: `verkoopuren`, `vermogen`, `overschot_kwh`, `reserve_soc`, `drempelprijs`, `terugkoopprijs` und `tekst`. |
| `sensor.*_charge_plan` | Zustand: `laden`, `gepland`, `klaar`, `vol`, `geen` oder `onbekend`. Attribute: `laaduren`, `venster`, `eind`, `uren_nodig`, `vermogen`, `klaar_tot`, `tekst` (lesbare Zusammenfassung) und `stroomschema` (Zeitleiste und Prüfungen für die Karte). |
| `sensor.*_planned_charge_power` | Die verteilte Ladeleistung in W. |
| `sensor.*_energy_to_charge` | Zum Füllen nötige Energie aus dem Netz in kWh. |
| `sensor.*_charge_start` / `*_charge_end` | Beginn und Ende der geplanten Ladung. |
| `sensor.*_gain_today` / `*_gain_this_week` / `*_gain_this_month` | Realisierter Ertrag in Euro seit 00:00 Uhr, seit Montag 00:00 Uhr und seit dem Monatsersten (siehe *Ertrag*). Attribute: der Vorrat und, für heute, was geladen und genutzt wurde. |
| `sensor.*_gain_this_year` | Realisierter Ertrag seit dem 1. Januar. |
| `sensor.*_gain_last_week` | Der endgültige Ertrag der Vorwoche. |
| `sensor.*_expected_gain` | Geschätzter Ertrag der aktuellen Pläne in Euro (Laden plus Verkaufen); das Attribut `regels` enthält die Aufschlüsselung. |
| `sensor.*_efficiency` | Der verwendete Wirkungsgrad in Prozent. Attribut `bron`: aus den Energiezählern gemessen oder der feste Wert. |
| `sensor.*_average_charge_price` | Durchschnittspreis der Ladestunden in €/kWh. |

Die Namen oben gelten für eine englische Installation. Ist Home Assistant auf Deutsch eingestellt, heißen sie
`*_ladeplan`, `*_preissteuerung` und so weiter. Die Statuswerte und Attributnamen sind
in beiden Sprachen gleich.

## Installation

1. Installiere über HACS (Button oben, oder füge dieses Repository als benutzerdefiniertes Repository hinzu, Kategorie
   *Integration*) oder kopiere `custom_components/marstek_goedkoop_laden` nach
   `/config/custom_components/`. Starte Home Assistant neu.
2. Gehe zu *Einstellungen → Geräte & Dienste → Integration hinzufügen → Marstek Goedkoop Laden*.
3. Wähle, wie deine Marstek angebunden ist (*LilyGO RS485 mit ESPHome*, *Modbus in Home Assistant* oder *Marstek Venus Modbus-Integration*),
   dann den Preissensor und die Marstek-Entitäten. Was erkannt wird, ist bereits vorausgefüllt. Bei Modbus gibst du
   außerdem den Namen deines Modbus-Hubs (zum Beispiel `MarstekVenus`) und die Slave-Adresse an.

Erfordert Home Assistant 2026.3 oder neuer.

### Preissensor

Die Integration liest die Preise aus einem Attribut eines Sensors (Standard `forecast`):

- Zonneplan-Stundenpreise: `start_date`, `end_date`, `price_tax_included.amount`
- Zonneplan (alt): `datetime`, `electricity_price`
- Allgemein: `start` (oder `start_time`, `datetime`) und `price` (oder `value`, `prijs`) in €/kWh

### Einstellungen

Unter *Konfigurieren* bei der Integration:

| Einstellung | Standard | Bedeutung |
|---|---|---|
| Sprache | Automatisch | Sprache von Plantext, Flussdiagramm und Karten: Automatisch, Nederlands, English, Frysk, Deutsch, Français, Español, Svenska oder Norsk. |
| Anschaffungspreis des Akkus | € 0 | Für die Abschreibung. 0 schaltet die Abschreibung aus. |
| Lebensdauer des Akkus (Zyklen) | 6000 | Erwartete Anzahl voller Zyklen. Abschreibung pro kWh = Preis ÷ (Zyklen × Kapazität); zum Beispiel sind € 1.500 über 6.000 Zyklen à 5,12 kWh etwa € 0,049 pro kWh. |
| Solarprognose verwenden | An | Berücksichtigt beim nächtlichen Laden den erwarteten Solarertrag aus dem Energie-Dashboard. |
| Zuverlässigkeit der Solarprognose | 70 % | Der Teil der Prognose, auf den gezählt wird. Niedriger ist vorsichtiger. |
| Mindestgewinn pro kWh | € 0,02 | Was das Laden nach Abzug der Ladeverluste mindestens einbringen muss. Stunden, die weniger als einen halben Cent über der Grenze liegen, zählen trotzdem, damit eine fast flache Nacht nicht wegen eines Bruchteils eines Cents zerstückelt wird. |
| Anzahl der teuersten Stunden | 6 | Mit wie vielen späteren teuren Stunden eine Stunde verglichen wird. |
| Stunden Vorausschau | 18 | Wie weit hinter einer Stunde nach teuren Stunden gesucht wird. |
| Mindestanzahl bekannter Stunden im Voraus | 8 | Stunden, nach denen weniger Preise bekannt sind, werden ignoriert. |
| Minimale Ladeleistung | 400 W | Untergrenze beim Verteilen. |
| Wirkungsgrad, wenn die Zähler fehlen | 0,77 | Der Wirkungsgrad wird aus den Energiezählern der Marstek berechnet (gesamt entladen ÷ gesamt geladen, begrenzt auf 70–95 %). Dieser feste Wert gilt nur, wenn diese Zähler fehlen. Der Wirkungsgrad nur für das Laden oder nur für das Entladen ist dessen Quadratwurzel. |
| Akkukapazität | 5,12 kWh | Wird nur verwendet, wenn kein Kapazitätssensor gesetzt ist. |
| Negativer Preis: Grenze | € 0,00 | Unter diesem Stundenpreis lädt der Akku mit voller Leistung. |
| Verkauf: Mindestgewinn pro kWh | € 0,10 | Was das Verkaufen nach dem Wiederaufladen mindestens einbringen muss. |
| Verkauf: durchschnittlicher Eigenverbrauch | 400 W | Bestimmt die Reserve bis zum Wiederaufladen. |
| Verkauf: Mindestreserve | 20 % | Unter diesem SoC wird nichts verkauft. |
| Verkaufspreis: Faktor und Abzug | 1 und € 0 | Verkaufspreis = Stundenpreis × Faktor − Abzug. |

Die maximale Ladeleistung (die *Max. Charge power* der Marstek) bestimmt die Anzahl der Ladestunden.
Stellst du sie niedriger ein, plant sie mehr Stunden und lädt sanfter.

## Dashboard

### Karten der Integration

Die Integration liefert sieben Karten mit; es muss keine Ressource hinzugefügt werden. Aktualisiere den Browser
nach der Installation oder dem Update. Jede Karte lässt sich im Karteneditor (dem visuellen Editor) ebenso wie
in YAML einrichten, und wenn du `entity` weglässt, wird der Ladeplan-Sensor automatisch gefunden.

| Karte | Inhalt |
|---|---|
| `custom:marstek-goedkoop-laden-card` | Flussdiagramm: die Zeitleiste von heute und, je Teil (Laden, Verkaufen, negativer Preis, Halten), welche Prüfungen bestanden werden und wo es endet. |
| `custom:marstek-goedkoop-laden-compact-card` | Dasselbe in wenigen Zeilen: die Zeitleiste, das Ergebnis je Teil mit dem Grund und eine Zeile mit dem Ertrag. |
| `custom:marstek-goedkoop-laden-opbrengst-card` | Nur der Ertrag: heute, diese Woche, letzte Woche, dieser Monat und die Erwartung des aktuellen Plans. |
| `custom:marstek-goedkoop-laden-schakelaars-card` | Kompakt: Schaltflächen, um Laden, Verkaufen, Laden bei negativem Preis, Halten und Kein Verlust ein- oder auszuschalten. |
| `custom:marstek-goedkoop-laden-status-card` | Was gerade passiert, der Ladestand als Balken, der Preis jetzt und der nächste Schritt. |
| `custom:marstek-goedkoop-laden-prijzen-card` | Preisdiagramm ohne zusätzliche Karten: die Stunden mit Laden, Verkaufen und negativen Preisen markiert, dazu eine Linie für jetzt. |
| `custom:marstek-goedkoop-laden-voorraad-card` | Der geladene Vorrat, sein Einstandspreis, der Wirkungsgrad, die Abschreibung pro kWh und die Kapazität. |

```yaml
type: custom:marstek-goedkoop-laden-card
entity: sensor.marstek_goedkoop_laden_laadplan   # optional
title: Price control                             # optional
opbrengst: false                                 # optional, see below
```

Die Ertragskarte lässt sich anpassen, in YAML oder im Karteneditor:

```yaml
type: custom:marstek-goedkoop-laden-opbrengst-card
tiles: [vandaag, maand, jaar]   # any of: vandaag, week, vorige_week, maand, jaar, verwacht (in this order)
expected_details: false         # hide the lines per part of the plan (default: true)
notes: false                    # hide the note below the card (default: true)
```

| Option | Standard | Bedeutung |
|---|---|---|
| `tiles` | alle sechs | Welche Kacheln in welcher Reihenfolge angezeigt werden: heute, diese Woche, letzte Woche, dieser Monat, dieses Jahr, erwartet (Plan). |
| `expected_details` | `true` | Die Zeilen mit dem erwarteten Ertrag je Teil (Laden, Verkaufen). |
| `notes` | `true` | Der Hinweis mit dem geladenen Vorrat, dem heute Geladenen und der Abschreibung. |

Optionen der anderen Karten (alle auch im Karteneditor):

| Karte | Option | Standard | Bedeutung |
|---|---|---|---|
| Fluss, kompakt | `show_timeline` | `true` | Die Zeitleiste von heute anzeigen. |
| Fluss, kompakt, Schalter | `lanes` | alle fünf | Welche Teile angezeigt werden: `bijladen`, `verkoop`, `negatief`, `vasthouden`, `geen_verlies`. |
| Status | `show_soc`, `show_price`, `show_next` | `true` | Der Ladestand-Balken, der Preis jetzt, der nächste Schritt. |
| Preise | `hours_back` | `2` | Wie viele Stunden der Vergangenheit angezeigt werden. |
| Preise | `hours_ahead` | `0` | Wie viele Stunden im Voraus angezeigt werden; 0 reicht bis zum letzten bekannten Preis. |
| Preise | `show_values` | `false` | Den Preis über jedem Balken ausgeben (bis zu 24 Balken). |
| Preise | `height` | `140` | Höhe des Diagramms in Pixel. |
| Vorrat | `tiles` | alle fünf | `voorraad`, `kostprijs`, `rendement`, `afschrijving`, `capaciteit`. |
| Vorrat | `notes` | `true` | Der Hinweis unter der Karte. |

`opbrengst` legt fest, ob die Flusskarte auch den Ertrag zeigt: bei der normalen
Karte standardmäßig aus, bei der kompakten Karte standardmäßig eine Zeile. Im Flussdiagramm ist Grün eine
bestandene Prüfung, Rot die Prüfung, an der es endet, und gestrichelt ein Ergebnis, bei dem nichts passiert. Alle
Karten lesen das Attribut `stroomschema` des Ladeplan-Sensors.

## Ertrag

**Abschreibung.** Wenn du einen Anschaffungspreis einstellst, kostet jede kWh, die der Akku entlädt, ein wenig Verschleiß: Preis ÷ (Zyklen × Kapazität). Sie wird vom realisierten Ertrag abgezogen (heute, Woche, Monat), im erwarteten Ertrag berücksichtigt und in den Entscheidungen verwendet: Eine Stunde lohnt sich zum Laden nur, wenn sie den Verschleiß noch übertrifft, das Verkaufen braucht den Verschleiß zusätzlich zur Verkaufsmarge, und *Halten* und *Kein Verlust* behandeln Einstandspreis plus Verschleiß als Break-even-Preis. Bei einem Preis von 0 (Standard) ändert sich nichts.

Es gibt zwei Arten von Ertrag: was der aktuelle Plan voraussichtlich einbringt und was tatsächlich
verdient wurde.

### Erwartet (Schätzung im Voraus)

- **Laden**: was die einzukaufende Energie kostet, im Vergleich zu dem, was sie später wert ist. Dieser Wert ist der
  Wirkungsgrad mal der Durchschnittspreis der teuren Stunden, mit denen die Ladestunde verglichen wurde.
- **Verkaufen**: der Erlös des Überschusses, abzüglich der Kosten des Wiederaufladens.

Während einer Ladung zählt nur, was noch zu laden ist.

### Heute und diese Woche (realisiert)

1. Energie, die die Integration aus dem Netz lädt (Ladeplan oder negativer Preis), wird zum
   **Vorrat**: nutzbare kWh = geladene kWh × Wirkungsgrad, mit dem Einstandspreis, den diese Energie
   in dem Moment gekostet hat.
2. Entlädt der Akku danach für den Eigenverbrauch, wird dieser Vorrat zuerst verwendet. Der Ertrag ist
   `entladene kWh × (Strompreis in dem Moment − Einstandspreis pro nutzbarer kWh)`.
3. Beim Verkaufen ist der Ertrag `verkaufte kWh × Verkaufspreis − Einstandspreis`; für Energie, die nicht
   aus dem Vorrat stammt (Solarenergie), ist der Einstandspreis das, was das Wiederaufladen kostet.
4. **Heute** ist die Summe seit 00:00 Uhr, **diese Woche** seit Montag 00:00 Uhr und **dieser Monat** seit dem Monatsersten. **Letzte Woche** ist der Endbetrag der Vorwoche.

Was noch im Vorrat steckt, ist noch nicht verdient und zählt erst, wenn es verwendet wird. Energie,
die die Sonne in den Akku lädt und die du später selbst nutzt, zählt nicht: Das macht die Marstek
auch ohne diese Integration. Die Beträge stammen aus den Energiezählern der Marstek und dem
Stundenpreis in dem Moment; ein Zählersprung nach einer Störung wird nicht gebucht.

### Einzelne Karten

Planzeile (Markdown-Karte):

```yaml
type: markdown
content: >-
  **Charge plan:** {{ state_attr('sensor.marstek_goedkoop_laden_laadplan', 'tekst') }}
  {% if is_state('switch.marstek_goedkoop_laden_prijssturing', 'off') %}
  · ⚠️ price control is **off**{% endif %}
```

## Entwicklung

Die Rechenregel liegt getrennt von Home Assistant in `planner.py` und hat Tests mit
echten Preisen. Die Steuerlogik wird gegen ein simuliertes Home Assistant getestet
(`tests/test_sturing.py`):

```bash
python3 -m unittest discover -s tests -v
```


## Changelog

Siehe [CHANGELOG.md](CHANGELOG.md), einschließlich der Breaking Changes.

## Lizenz

Apache 2.0, siehe [LICENSE](LICENSE).
