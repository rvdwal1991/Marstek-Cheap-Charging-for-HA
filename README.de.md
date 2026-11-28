<img src="custom_components/marstek_goedkoop_laden/brand/icon.png" width="96" align="right" alt="">

# Marstek Günstig Laden für Home Assistant

[🇬🇧 English](README.md) · [🇳🇱 Nederlands](README.nl.md) · [🏳️ Frysk](README.fy.md) · 🇩🇪 Deutsch · [🇫🇷 Français](README.fr.md) · [🇪🇸 Español](README.es.md) · [🇸🇪 Svenska](README.sv.md) · [🇳🇴 Norsk](README.nb.md)

[![Open your Home Assistant instance and open this repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=rvdwal1991&repository=Marstek-Cheap-Charging-for-HA&category=integration)
[![Open your Home Assistant instance and start setting up the integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=marstek_goedkoop_laden)

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz/docs/faq/custom_repositories)
[![Validate](https://github.com/rvdwal1991/Marstek-Cheap-Charging-for-HA/actions/workflows/validate.yml/badge.svg)](https://github.com/rvdwal1991/Marstek-Cheap-Charging-for-HA/actions/workflows/validate.yml)

Lädt einen Marstek-Venus-Heimspeicher in den günstigsten Stunden eines dynamischen
Stromvertrags aus dem Netz nach, sodass er voll ist, bevor die Preise steigen.

Ausgangspunkt ist die **Eigenversorgung**: Der Speicher regelt sich weiterhin selbst (anti-feed,
null am Zähler). Diese Integration fügt eine Sache hinzu, nämlich das Laden aus dem Netz in den
günstigsten Stunden, dazu ein paar optionale Extras drumherum.

**Du brauchst:**

- einen **dynamischen Stromvertrag** mit Stundenpreisen. Bei einem Festpreis ist nichts zu
  gewinnen. Die Integration wurde für den niederländischen Markt und Zonneplan entwickelt (die Preise für
  den nächsten Tag erscheinen zwischen 13:00 und 15:00 Uhr), aber jeder Sensor mit einer
  Stundenpreisliste funktioniert, siehe [Preissensor](#preissensor);
- eine Marstek Venus, die Home Assistant über RS485 oder Modbus steuern kann, siehe
  [Kompatibilität](#kompatibilität). **Nur der Aufbau LilyGO RS485 + ESPHome wurde an einem
  echten Speicher getestet.**
- Home Assistant 2026.3 oder neuer.

## Was sie tut

| Modus | Standard | Was er tut |
|---|---|---|
| **Preissteuerung** | aus | Lädt in den günstigsten Stunden aus dem Netz und verteilt die Leistung auf diese Stunden. |
| **Laden bei negativem Preis** | an | Lädt, wenn der Stundenpreis negativ ist, und holt das Beste aus dem Fenster heraus. |
| **Solarprognose** | an | Lädt nachts weniger, wenn die Sonne den Akku tagsüber füllen wird. Erfordert eine Solarprognose im Energie-Dashboard. |
| **Halten unter Einstandspreis** | an | Entlädt nicht, solange das Netz günstiger ist, als der geladene Vorrat gekostet hat. |
| **Kein Verlust** | aus | Strenge Variante von Halten: Verkauft außerdem nie geladenen Vorrat unter dem Einstandspreis. |
| **Verkauf** | aus | Verkauft Überschuss in den teuersten Stunden. |

Jeder Modus hat einen eigenen Schalter. **Die Preissteuerung ist nach der Installation aus**: Richte die Integration ein,
prüfe, ob der Plantext des Ladeplan-Sensors stimmig aussieht, und schalte sie dann ein.

### Das Wichtigste

- **Dynamische Preise.** Lädt in den günstigsten veröffentlichten Stunden, und nur so viel, wie es sich nach dem gemessenen Wirkungsgrad lohnt.
- **Negative Preise.** Verteilt das Laden auf das gesamte negative Fenster, gewichtet nach dem Wert jeder Stunde; auf Wunsch für maximalen Gewinn, siehe [Laden bei negativem Preis](#laden-bei-negativem-preis).
- **Solarprognose.** Nutzt die Prognose aus dem Energie-Dashboard: lädt nur, was die Sonne nicht füllt, zieht den erwarteten Hausverbrauch pro Stunde ab und lernt anhand der tatsächlichen Erzeugung, wie zuverlässig die Prognose ist, siehe [Solarprognose](#solarprognose).
- **Abschreibung.** Mit einem Anschaffungspreis zählt der Verschleiß pro kWh im Ertrag, in der Verkaufsmarge und in der Gewinnschwelle von *Halten unter Einstandspreis* mit, siehe [Ertrag](#ertrag).
- **Einstandspreis.** Verfolgt, was der Vorrat im Akku gekostet hat, und entlädt ihn nicht unter diesem Preis (*Halten unter Einstandspreis*, *Kein Verlust*).
- **Anschluss.** LilyGO mit ESPHome, ein Modbus-Hub (Elfin EW11 oder die Venus E v3 direkt über Ethernet) oder die Integration *Marstek Venus Modbus*, siehe [Kompatibilität](#kompatibilität).
- **Karten und Sprachen.** Sieben Dashboard-Karten, die in der GUI eingestellt werden, und acht Sprachen.

## Schnellstart

1. Installiere über HACS (Button oben, oder füge dieses Repository als benutzerdefiniertes Repository hinzu, Kategorie
   *Integration*) oder kopiere `custom_components/marstek_goedkoop_laden` nach
   `/config/custom_components/`. Starte Home Assistant neu.
2. *Einstellungen → Geräte & Dienste → Integration hinzufügen → Marstek Goedkoop Laden*.
3. Wähle, wie deine Marstek angebunden ist, dann den Preissensor und die Marstek-Entitäten.
   Was erkannt wird, ist bereits vorausgefüllt. Bei Modbus gibst du außerdem den Namen deines Modbus-Hubs (zum
   Beispiel `MarstekVenus`) und die Slave-Adresse an.
4. Schalte den Schalter **Preissteuerung** ein, wenn der Plan stimmig aussieht.
5. Füge Karten hinzu: *Dashboard bearbeiten → Karte hinzufügen → nach „Marstek“ suchen*, siehe [Dashboard-Karten](#dashboard-karten).

Die Texte (Planzeile, Flussdiagramm, Karten) folgen der Option *Sprache*: Automatisch, Nederlands,
English, Frysk, Deutsch, Français, Español, Svenska oder Norsk. Automatisch folgt Home Assistant,
wenn dessen Sprache dazugehört, sonst Englisch.

## So funktioniert der Ladeplan

1. **Lohnt sich das Laden?** Eine Stunde ist günstig genug, wenn ihr Preis niedriger ist als
   `Wirkungsgrad × (Mittelwert der 6 teuersten Stunden der nächsten 18 Stunden) − Marge`. Der
   Wirkungsgrad (Round-Trip aus Laden und Entladen, hier gemessen etwa 77 %) stammt aus den
   Energiezählern der Marstek.
2. **Fenster.** Der erste Block günstiger Stunden ist das Ladefenster. Eine oder zwei Stunden, die
   knapp nicht günstig genug sind, unterbrechen den Block nicht; geladen wird aber nur in den günstigen Stunden
   selbst.
3. **Ladestunden.** Innerhalb dieses Fensters wählt sie die günstigsten Stunden, genau so viele wie nötig,
   um vom aktuellen SoC auf 100 % zu kommen. Ist das Fenster zu kurz, um den Akku zu füllen, plant sie
   nur, was hineinpasst, und sagt das im Plantext.
4. **Leistung verteilen.** Die Ladeleistung ist die noch einzuladende Energie geteilt durch die verbleibende Zeit
   in den Ladestunden. So bleibt die Last auf dem Netzanschluss gering. Die Leistung wird
   unterwegs angepasst.
5. **Fertig ist fertig.** Sind die Ladestunden vorbei oder ist der Akku voll, geht die Marstek zurück
   in den anti-feed-Betrieb. Im selben Fenster startet sie nicht erneut.

Es werden nur **veröffentlichte** Preise verwendet, der Plan für die Nacht erscheint also, sobald die Preise
für morgen bekannt sind. Beispiel (10. November 2026, Akku bei 12 %): günstiges Fenster 23:00–07:00 Uhr,
Laden um 02:00, 03:00 und 04:00 Uhr mit etwa 1900 W zu durchschnittlich € 0,37, gegenüber € 0,55–0,67
tagsüber.

### Laden bei negativem Preis

Ist der Stundenpreis negativ, lädt der Akku, unabhängig vom Ladeplan und auch
bei ausgeschalteter Preissteuerung. Betrachtet wird das ganze **Fenster** aufeinanderfolgender negativer Stunden:

1. Sie berechnet, wie viel der Akku noch aufnehmen kann (SoC bis 100 %).
2. Sie verteilt diese Energie **nach dem Wert** auf die Stunden: Je negativer der Preis, desto
   mehr wird in dieser Stunde geladen, bis zu dem, was eine Stunde bei maximaler Leistung aufnehmen kann. Beispiel:
   −€ 0,03, −€ 0,20 und −€ 0,12 bei 3 kWh zu laden ergibt etwa 1,9 kWh in der Stunde mit −€ 0,20 und
   1,2 kWh in der Stunde mit −€ 0,12. Die Stunde mit −€ 0,03 läge unter der minimalen Ladeleistung, fällt daher
   weg, und ihr Anteil geht an die anderen beiden.
3. Das Verteilen hält die Leistung niedriger als ein kurzer Stoß mit voller Leistung. Eine einzelne Stunde, die den Akku
   nicht füllen kann, wird mit voller Leistung geladen.

Die Option *Negativer Preis: Aufteilung der Energie* lässt sich auf **Maximaler Ertrag** stellen: Die beste
Stunde wird zuerst mit voller Leistung gefüllt, dann die nächste. Im Beispiel bringt das etwa € 0,55
statt € 0,52 ein, auf Kosten von mehr Stößen mit voller Leistung. Der Plan wird jede
Minute neu berechnet, und eine Stunde, die bereits in Gebrauch ist, bekommt etwas zusätzlichen Spielraum, bevor sie ausscheidet.

### Solarprognose

Mit Solarmodulen füllt sich der Akku tagsüber kostenlos. Lädst du ihn nachts voll aus dem
Netz, bleibt für den Überschuss kein Platz mehr, und er geht für wenig oder gar kein Geld ins Netz, was
jetzt wichtiger wird, da die Netto-Messung (*salderingsregeling*) ausläuft. Deshalb betrachtet die Integration
den erwarteten Solarertrag:

1. Sie liest die Prognose aus dem **Energie-Dashboard** (*Einstellungen → Dashboards → Energie → Solarmodule →
   Solarproduktionsprognose*). Forecast.Solar, Solcast, Open-Meteo und andere Prognose-Integrationen
   funktionieren, ohne dass etwas Zusätzliches einzurichten ist. Ohne Prognose dort ändert sich nichts.
2. Sie berechnet den erwarteten Überschuss: je Stunde die Prognose, multipliziert mit der Zuverlässigkeit,
   minus deinen Eigenverbrauch in dieser Stunde. Prognosen sind oft zu optimistisch, besonders im Winter.
   Ist *Zuverlässigkeit aus der tatsächlichen Erzeugung lernen* an, vergleicht die Integration die Prognose
   jedes Tages mit dem, was die Module tatsächlich erzeugt haben (der Erzeugungszähler aus dem Energie-Dashboard),
   und nutzt ab mindestens 3 Tagen den Median der letzten Tage als Zuverlässigkeit.
   Bis dahin und bei ausgeschaltetem Lernen gilt die Einstellung *Zuverlässigkeit der Solarprognose* (Standard 70 %).
   Dein Eigenverbrauch in dieser Stunde: Mit einem *Hausleistungssensor*
   lernt die Integration deinen durchschnittlichen Verbrauch je Stunde des Tages (Werktage und Wochenenden
   getrennt) und nutzt ihn, sodass ein Mittag, den das Haus selbst aufzehrt, keinen Überschuss lässt.
   Ohne den Sensor gilt der feste *Verkauf: durchschnittlicher Eigenverbrauch*.
3. Sie lädt nachts nur so viel, dass beim Sonnenaufgang Platz für diesen Überschuss bleibt:
   was dein Eigenverbrauch bis dahin aufzehrt, plus das, was noch gebraucht wird. An einem sonnigen Tag können das
   ein paar kWh statt eines vollen Akkus sein oder gar nichts (der Plantext sagt dann, dass die Sonne den Akku
   füllt). Ein bewölkter Tag ergibt wenig oder keinen Überschuss, und der Akku wird voll geladen.

Die Prognose wird alle 30 Minuten gelesen. Sie verringert nur die Lademenge; Ladestunden verschiebt sie
nicht, und am Verkaufen ändert sie nichts.

### Halten und Kein Verlust

Aus dem Netz geladene Energie hat einen Einstandspreis: den Ladepreis geteilt durch den Wirkungsgrad. Gäbe der
Akku diese Energie in Stunden wieder ab, die günstiger sind, würde das Laden Geld kosten.
**Halten** sperrt daher das Entladen, solange sich geladener Vorrat im Akku befindet (siehe
[Ertrag](#ertrag)) und der Stundenpreis unter dem Einstandspreis dieses Vorrats liegt. Das Haus bezieht dann Netzstrom, der in diesem Moment günstiger ist. Sobald der Preis den Einstandspreis erreicht oder der Vorrat
aufgebraucht ist, übernimmt die Marstek wieder.

Technisch setzt die Integration die maximale Entladeleistung auf 0. Die Marstek bleibt im
anti-feed-Betrieb, das Laden aus Solarüberschuss läuft also weiter. Setzt eine andere Automatisierung diese Leistung
während des Haltens (zum Beispiel ein Limiter für eine Wallbox), merkt sich die Integration diesen Wert
und stellt ihn danach wieder her. Die Marstek kann Netzenergie nicht von Solarenergie unterscheiden, daher wird während eines
Haltens der ganze Akku nicht entladen. Halten braucht die Entität für die maximale
Entladeleistung.

**Kein Verlust** ist ein separater, strengerer Schalter: Halten wird auch bei ausgeschaltetem Schalter Halten erzwungen,
und unter dem Einstandspreis wird nichts verkauft. Jede gebuchte kWh bringt dann mindestens ihren Einstandspreis ein. Was sich
nicht ausschließen lässt:

- **Stillstand:** Bleibt der Preis lange unter dem Einstandspreis, bleibt der Akku
  gesperrt, auch für gespeicherte Solarenergie.
- **Abweichender Wirkungsgrad:** Gibt der Akku weniger zurück als der durchschnittliche Wirkungsgrad, ist er leer,
  bevor der Vorrat in den Büchern aufgebraucht ist; der Rest verfällt, ohne einen Verlust zu buchen.
- **Verschleiß** wird nicht mitgezählt, außer du stellst einen Anschaffungspreis ein (siehe [Ertrag](#ertrag)).

### Verkaufen

Das Verkaufen hat einen eigenen Schalter und ist unabhängig vom Laden. Verkauft wird nur, was wirklich übrig ist.
Eine Stunde wird zum Verkaufen genutzt, wenn all dies zutrifft:

1. **Eine günstige Ladung steht an**: Ein Ladefenster mit veröffentlichten Preisen liegt voraus, die Kosten
   des Wiederaufladens sind also bekannt.
2. **Der Erlös liegt deutlich über dem Wiederaufladen**: Verkaufspreis ≥ Ladepreis geteilt durch den
   Wirkungsgrad, plus die Verkaufsmarge (Standard € 0,10 pro kWh).
3. **Es gibt Überschuss über der Reserve**: die Entladegrenze der Marstek plus der erwartete
   Eigenverbrauch bis zum Wiederaufladen, mit einem einstellbaren Minimum (Standard 20 %).
4. **Es ist eine der teuersten Stunden** vor dem Ladefenster.

Die Verkaufsleistung wird auf die gewählten Stunden verteilt; bei der Reserve hört das Verkaufen auf. Im Winter gibt es
selten einen Überschuss; die Option bringt vor allem dann etwas, wenn die Sonne den Akku füllt und es
abends eine Preisspitze gibt. Sie braucht die Entität für die erzwungene Entladeleistung.

**Nach dem Ende der Netto-Messung** (der niederländischen *salderingsregeling*, 1. Januar 2027) bringt Einspeisen
weniger als der Stundenpreis. Stelle dann *Verkaufspreis: Faktor* und *Abzug* ein: Verkaufspreis =
Stundenpreis × Faktor − Abzug. Für den reinen Marktpreis bei Zonneplan sind das etwa 0,826
und € 0,108.

## Kompatibilität

Die Integration steuert eine Marstek Venus über ihre RS485-Steuerregister.

| Anbindung | Modell | Status |
|---|---|---|
| LilyGO T-CAN485 + ESPHome (RS485) | Venus E v2 | **Getestet** an echter Hardware (der Aufbau, auf dem sie entwickelt wurde) |
| Modbus-Hub in Home Assistant, über RS485-zu-TCP-Wandler (Elfin EW11 und ähnliche) | Venus E v1/v2 | Nur mit simulierten Aufrufen getestet |
| Modbus-Hub in Home Assistant, direkt über Ethernet | Venus E v3 | Nur mit simulierten Aufrufen getestet |
| Integration *Marstek Venus Modbus* (ViperRNMC) | Venus E v3 | Nur mit simulierten Aufrufen getestet |
| Eine der obigen | Venus A, Venus D, andere Modelle | **Nicht geprüft, nicht getestet.** Sie sollen dieselben Steuerregister haben, das ist aber unbestätigt. Stelle die Akkukapazität in den Optionen ein (Standard 5,12 kWh). |
| Cloud, App oder andere Integrationen | beliebig | Nicht unterstützt |

- **LilyGO T-CAN485 mit ESPHome** über RS485, mit der Konfiguration
  [MarstekVenus-LilygoRS485](https://github.com/Superduper1969/MarstekVenus-LilygoRS485).
  Sie nutzt die Entitäten, die dieser Aufbau bereitstellt: *RS485 Control Mode*, *Forcible
  Charge/Discharge*, *Forcible Charge Power* (erforderlich) und optional *Max. Charge Power*,
  *Max. Discharge Power*, *Forcible Discharge Power*, *Discharging Cutoff Capacity* sowie die Zähler für die insgesamt
  geladene und entladene Energie.
- **Modbus in Home Assistant**, mit einem Modbus-Hub, den du selbst in der
  `configuration.yaml` definierst: ein Elfin EW11 oder ein anderer RS485-zu-TCP-Wandler
  ([MarstekVenus-ElfinEW11](https://github.com/Superduper1969/MarstekVenus-ElfinEW11)) oder der
  **Venus E v3 direkt über Ethernet** (Modbus TCP, Port 502, Unit 1, EMS V144 oder neuer;
  [MarstekVenusV3-modbus-TCP-IP](https://github.com/fonske/MarstekVenusV3-modbus-TCP-IP)). Die
  Integration liest die Registersensoren dieses Aufbaus und schreibt mit `modbus.write_register` die Register 42000 (RS485-Steuerung),
  42010 (Force-Modus), 42020/42021 (erzwungene Lade-/Entladeleistung) und, wenn du die Sensoren angibst,
  44002/44003 (maximale Lade-/Entladeleistung). Ohne die maximale
  Entladeleistung sind *Halten* und *Kein Verlust* nicht verfügbar. Die Venus E v3 hält ihren Ladestand
  im Register 34002 (Skalierung 0,1), nicht in 32104.
- **Die Integration *Marstek Venus Modbus***
  ([ViperRNMC/marstek_venus_modbus](https://github.com/ViperRNMC/marstek_venus_modbus)), die
  ebenfalls Modbus TCP spricht. Wähle sie, wenn du sie ohnehin nutzt: Sie liefert die Entitäten (`switch`
  RS485-Steuermodus, `select` Force-Modus, `number` Leistungen). Aktiviere dort zuerst den Schalter *RS485 control mode*
  und die Auswahl *Force mode*, sie sind standardmäßig deaktiviert.

### Was die Integration an die Marstek sendet

| Moment | Befehle |
|---|---|
| Laden starten | Ladeleistung setzen → Force-Modus `charge` → RS485-Steuerung `enable` |
| Beim Laden | Ladeleistung anpassen (Schritte von 100 W) |
| Fertig oder Preissteuerung aus | RS485-Steuerung `disable`, Force-Modus zurück auf `charge`, Ladeleistung zurück auf das Maximum |
| Verkaufen starten | Entladeleistung setzen → Force-Modus `discharge` → RS485-Steuerung `enable` |
| Verkaufen beendet oder Verkauf aus | wie „fertig“: zurück in den Ruhezustand |

Erzwungenes **Ent**laden, das du selbst startest, bleibt unangetastet. Erzwungenes Laden, das du
selbst startest, wird zurückgesetzt, solange die Preissteuerung an ist; schalte sie zuerst aus, wenn du das möchtest.

## Einstellungen

Unter *Konfigurieren* bei der Integration. Die Optionen sind in Gruppen geordnet; die Entitäten liegen in einer
eingeklappten Gruppe ganz unten.

### Preissensor

Die Integration liest die Preise aus einem Attribut eines Sensors (Standard `forecast`):

- Zonneplan-Stundenpreise: `start_date`, `end_date`, `price_tax_included.amount`
- Zonneplan (alt): `datetime`, `electricity_price`
- Allgemein: `start` (oder `start_time`, `datetime`) und `price` (oder `value`, `prijs`) in €/kWh

### Optionen

| Gruppe | Einstellung | Standard | Bedeutung |
|---|---|---|---|
| | Sprache | Automatisch | Sprache von Plantext, Flussdiagramm und Karten. |
| Akku | Akkukapazität | 5,12 kWh | Wird nur verwendet, wenn kein Kapazitätssensor gesetzt ist. |
| Akku | Wirkungsgrad, wenn die Zähler fehlen | 0,77 | Der Wirkungsgrad wird aus den Energiezählern der Marstek berechnet (gesamt entladen ÷ gesamt geladen, begrenzt auf 70–95 %). Dieser feste Wert gilt nur, wenn diese Zähler fehlen. Der Wirkungsgrad in nur einer Richtung ist dessen Quadratwurzel. |
| Akku | Anschaffungspreis des Akkus | € 0 | Für die Abschreibung. 0 schaltet sie aus. |
| Akku | Lebensdauer des Akkus (Zyklen) | 6000 | Abschreibung pro kWh = Preis ÷ (Zyklen × Kapazität); € 1.500 über 6.000 Zyklen à 5,12 kWh sind etwa € 0,049 pro kWh. |
| Akku | Entladegrenze | 12 % | Wird verwendet, wenn keine Entität für die Entladegrenze gesetzt ist. |
| Laden | Mindestgewinn pro kWh | € 0,02 | Was das Laden nach Abzug der Ladeverluste mindestens einbringen muss. Stunden, die weniger als einen halben Cent über der Grenze liegen, zählen trotzdem, damit eine fast flache Nacht nicht wegen eines Bruchteils eines Cents zerstückelt wird. |
| Laden | Minimale Ladeleistung | 400 W | Untergrenze beim Verteilen. |
| Laden | Attribut mit den Preisen | `forecast` | Das Attribut des Preissensors mit den Stundenpreisen. |
| Laden | Anzahl der teuersten Stunden zum Vergleich | 6 | Mit wie vielen späteren teuren Stunden eine Stunde verglichen wird. |
| Laden | Stunden Vorausschau | 18 | Wie weit hinter einer Stunde nach teuren Stunden gesucht wird. |
| Laden | Mindestanzahl bekannter Stunden im Voraus | 8 | Stunden, nach denen weniger Preise bekannt sind, werden ignoriert. |
| Negativer Preis | Negativer Preis: Grenze | € 0,00 | Unter diesem Stundenpreis lädt der Akku. |
| Negativer Preis | Negativer Preis: Aufteilung der Energie | Nach Wert | Nach Wert verteilen (geringere Leistung) oder Maximaler Ertrag (beste Stunden zuerst). |
| Solar | Solarprognose verwenden | An | Berücksichtigt beim nächtlichen Laden den erwarteten Solarertrag aus dem Energie-Dashboard. |
| Solar | Zuverlässigkeit aus der tatsächlichen Erzeugung lernen | An | Vergleicht die Solarprognose jedes Tages mit dem, was die Module tatsächlich erzeugt haben, und nutzt den Median der letzten Tage als Zuverlässigkeit (ab 3 Tagen). |
| Solar | Zuverlässigkeit der Solarprognose | 70 % | Der Teil der Prognose, auf den gezählt wird. Niedriger ist vorsichtiger. |
| Solar | Hausleistungssensor | keiner | Optionaler Sensor mit der Leistung, die das ganze Haus verbraucht (W oder kW), ohne den Akku. Eine Wallbox verfälscht den Durchschnitt, lass sie daher nach Möglichkeit weg. |
| Verkauf | Verkauf: Mindestgewinn pro kWh | € 0,10 | Was das Verkaufen nach dem Wiederaufladen mindestens einbringen muss. |
| Verkauf | Verkauf: durchschnittlicher Eigenverbrauch | 400 W | Bestimmt die Reserve bis zum Wiederaufladen und ist der feste Eigenverbrauch für den Solarüberschuss. |
| Verkauf | Verkauf: Mindestreserve | 20 % | Unter diesem SoC wird nichts verkauft. |
| Verkauf | Verkaufspreis: Faktor und Abzug | 1 und € 0 | Verkaufspreis = Stundenpreis × Faktor − Abzug. |

Die maximale Ladeleistung (die *Max. Charge power* der Marstek) bestimmt die Anzahl der Ladestunden.
Stellst du sie niedriger ein, plant sie mehr Stunden und lädt sanfter.

## Dashboard-Karten

Die Integration liefert sieben Karten mit; es muss keine Ressource hinzugefügt werden. Aktualisiere den Browser
nach der Installation oder dem Update. Jede Karte lässt sich im Karteneditor ebenso wie in YAML einrichten, und wenn
du `entity` weglässt, wird der Ladeplan-Sensor automatisch gefunden.

| Karte | Inhalt |
|---|---|
| `custom:marstek-goedkoop-laden-card` | Flussdiagramm: die Zeitleiste von heute und, je Teil (Laden, Verkaufen, negativer Preis, Halten), welche Prüfungen bestanden werden und wo es endet. |
| `custom:marstek-goedkoop-laden-compact-card` | Dasselbe in wenigen Zeilen: die Zeitleiste, das Ergebnis je Teil mit dem Grund und eine Zeile mit dem Ertrag. |
| `custom:marstek-goedkoop-laden-opbrengst-card` | Nur der Ertrag: heute, diese Woche, letzte Woche, dieser Monat, dieses Jahr und die Erwartung des aktuellen Plans. |
| `custom:marstek-goedkoop-laden-schakelaars-card` | Kompakt: Schaltflächen, um die Modi ein- oder auszuschalten. |
| `custom:marstek-goedkoop-laden-status-card` | Was gerade passiert, der Ladestand als Balken, der Preis jetzt und der nächste Schritt. |
| `custom:marstek-goedkoop-laden-prijzen-card` | Preisdiagramm ohne zusätzliche Karten: die Stunden mit Laden, Verkaufen und negativen Preisen markiert, dazu eine Linie für jetzt. |
| `custom:marstek-goedkoop-laden-voorraad-card` | Der geladene Vorrat, sein Einstandspreis, der Wirkungsgrad, die Abschreibung pro kWh und die Kapazität. |

```yaml
type: custom:marstek-goedkoop-laden-opbrengst-card
entity: sensor.marstek_goedkoop_laden_laadplan   # optional
title: Ertrag                                    # optional
tiles: [vandaag, maand, jaar]                    # welche Kacheln, in dieser Reihenfolge
notes: false                                     # Hinweis unter der Karte ausblenden
```

| Karte | Option | Standard | Bedeutung |
|---|---|---|---|
| alle | `entity`, `title` | automatisch gefunden, keiner | Der Ladeplan-Sensor und ein Titel. |
| Fluss, kompakt | `show_timeline` | `true` | Die Zeitleiste von heute anzeigen. |
| Fluss, kompakt | `opbrengst` | aus, eine Zeile | Auch den Ertrag anzeigen. |
| Fluss, kompakt, Schalter | `lanes` | alle fünf | Welche Teile angezeigt werden: `bijladen`, `verkoop`, `negatief`, `vasthouden`, `geen_verlies`. |
| Ertrag | `tiles` | alle sechs | Beliebige aus `vandaag`, `week`, `vorige_week`, `maand`, `jaar`, `verwacht`, in dieser Reihenfolge. |
| Ertrag | `expected_details`, `notes` | `true` | Die Zeilen je Planteil; der Hinweis mit Vorrat, heutiger Ladung und Abschreibung. |
| Status | `show_soc`, `show_price`, `show_next` | `true` | Der Ladestand-Balken, der Preis jetzt, der nächste Schritt. |
| Preise | `hours_back`, `hours_ahead` | `2`, `0` | Stunden der Vergangenheit; Stunden im Voraus (0 reicht bis zum letzten bekannten Preis). |
| Preise | `show_values`, `height` | `false`, `140` | Den Preis über jedem Balken ausgeben (bis zu 24 Balken); Höhe in Pixel. |
| Vorrat | `tiles`, `notes` | alle fünf, `true` | `voorraad`, `kostprijs`, `rendement`, `afschrijving`, `capaciteit`; der Hinweis unter der Karte. |

Im Flussdiagramm ist Grün eine bestandene Prüfung, Rot die Prüfung, an der es endet, und gestrichelt ein
Ergebnis, bei dem nichts passiert. Planzeile in einer Markdown-Karte:

```yaml
type: markdown
content: >-
  **Ladeplan:** {{ state_attr('sensor.marstek_goedkoop_laden_laadplan', 'tekst') }}
  {% if is_state('switch.marstek_goedkoop_laden_prijssturing', 'off') %}
  · ⚠️ Preissteuerung ist **aus**{% endif %}
```

## Ertrag

Es gibt zwei Arten von Ertrag: was der aktuelle Plan voraussichtlich einbringt und was tatsächlich
verdient wurde.

**Erwartet (Schätzung im Voraus).** Laden: was die einzukaufende Energie kostet, im Vergleich zu dem, was sie später
wert ist (der Wirkungsgrad mal der Durchschnittspreis der teuren Stunden, mit denen die Ladestunde
verglichen wurde). Verkaufen: der Erlös des Überschusses, abzüglich der Kosten des Wiederaufladens. Während einer
Ladung zählt nur, was noch zu laden ist.

**Realisiert (heute, Woche, Monat, Jahr).**

1. Energie, die die Integration aus dem Netz lädt (Ladeplan oder negativer Preis), wird zum
   **Vorrat**: nutzbare kWh = geladene kWh × Wirkungsgrad, mit dem Einstandspreis, den diese Energie
   in dem Moment gekostet hat.
2. Entlädt der Akku danach für den Eigenverbrauch, wird dieser Vorrat zuerst verwendet. Der Ertrag ist
   `entladene kWh × (Strompreis in dem Moment − Einstandspreis pro nutzbarer kWh)`.
3. Beim Verkaufen ist der Ertrag `verkaufte kWh × Verkaufspreis − Einstandspreis`; für Energie, die nicht
   aus dem Vorrat stammt (Solarenergie), ist der Einstandspreis das, was das Wiederaufladen kostet.
4. **Heute** zählt seit 00:00 Uhr, **diese Woche** seit Montag 00:00 Uhr, **dieser Monat** seit dem Ersten
   und **dieses Jahr** seit dem 1. Januar. **Letzte Woche** ist der Endbetrag der Vorwoche.

Was noch im Vorrat steckt, ist noch nicht verdient und zählt erst, wenn es verwendet wird. Energie, die
die Sonne in den Akku lädt und die du später selbst nutzt, zählt nicht: Das macht die Marstek auch ohne
diese Integration. Die Beträge stammen aus den Energiezählern der Marstek und dem Stundenpreis
in dem Moment; ein Zählersprung nach einer Störung wird nicht gebucht.

**Abschreibung.** Wenn du einen Anschaffungspreis einstellst, kostet jede kWh, die der Akku entlädt, ein wenig
Verschleiß: Preis ÷ (Zyklen × Kapazität). Sie wird vom realisierten Ertrag abgezogen, im
erwarteten Ertrag berücksichtigt und in den Entscheidungen verwendet: Eine Stunde lohnt sich zum Laden nur, wenn sie den
Verschleiß noch übertrifft, das Verkaufen braucht den Verschleiß zusätzlich zur Verkaufsmarge, und *Halten* und *Kein Verlust*
behandeln Einstandspreis plus Verschleiß als Break-even-Preis. Bei einem Preis von 0 (Standard) ändert sich nichts.

## Entitäten

| Entität | Inhalt |
|---|---|
| `switch.*_preissteuerung` | An: Der Ladeplan wird ausgeführt. Aus: Die Marstek regelt alles selbst. |
| `switch.*_laden_bei_negativem_preis` | An (Standard): laden, wenn der Stundenpreis negativ ist. |
| `switch.*_halten_unter_einstandspreis` | An (Standard): nicht unter dem Einstandspreis des Vorrats entladen. |
| `switch.*_kein_verlust` | An: Halten erzwungen und nie unter Einstandspreis verkaufen. |
| `switch.*_verkauf` | An: Überschuss wird in den teuersten Stunden verkauft. Unabhängig von der Preissteuerung. |
| `sensor.*_ladeplan` | Zustand: `laden`, `gepland`, `klaar`, `vol`, `geen` oder `onbekend`. Attribute: `tekst` (lesbare Zusammenfassung), `laaduren`, `venster`, `stroomschema` (Zeitleiste, Prüfungen, Preise und Übersicht für die Karten) und weitere. |
| `sensor.*_verkaufsplan` | Zustand: `verkopen`, `gepland`, `geen` oder `onbekend`. Attribute: `verkoopuren`, `overschot_kwh`, `reserve_soc`, `tekst` und weitere. |
| `sensor.*_geplante_ladeleistung`, `*_noch_zu_laden`, `*_ladebeginn`, `*_ladeende`, `*_durchschnittlicher_ladepreis` | Die verteilte Ladeleistung in W, die noch zu ladende Energie in kWh, Beginn und Ende der geplanten Ladung und ihr Durchschnittspreis in €/kWh. |
| `sensor.*_ertrag_heute`, `*_ertrag_diese_woche`, `*_ertrag_letzte_woche`, `*_ertrag_diesen_monat`, `*_ertrag_dieses_jahr` | Realisierter Ertrag in Euro (siehe [Ertrag](#ertrag)). |
| `sensor.*_erwarteter_ertrag` | Geschätzter Ertrag der aktuellen Pläne in Euro; das Attribut `regels` enthält die Aufschlüsselung. |
| `sensor.*_wirkungsgrad` | Der verwendete Wirkungsgrad in Prozent. Attribut `bron`: gemessen oder fest. |

Entitätsnamen folgen der Sprache von Home Assistant, wenn die Entität angelegt wird (mit Englisch heißen sie
`*_charge_plan`, `*_price_control` und so weiter). **Statuswerte und Attributnamen sind in
jeder Sprache niederländisch** (`laden`, `tekst`, …); sie sind fest, damit Automatisierungen weiter funktionieren.

## Entwicklung

Die Rechenregel liegt getrennt von Home Assistant in `planner.py` und hat Tests mit
echten Preisen. Die Steuerlogik wird gegen ein simuliertes Home Assistant getestet:

```bash
python3 -m unittest discover -s tests -v
```

## Changelog

Siehe [CHANGELOG.md](CHANGELOG.md), einschließlich der Breaking Changes.

## Danksagung

Diese Integration baut auf der Arbeit der Marstek-Venus-Community auf:

- Der [Tweakers-Forenthread](https://gathering.tweakers.net/forum/list_messages/2282240/0), in dem diese Community-Arbeit besprochen wird, eine lobende Erwähnung für alle dort, die Erkenntnisse und Konfigurationen teilen.
- [Superduper1969](https://github.com/Superduper1969) für die Konfigurationen für LilyGO RS485 und Elfin EW11, um die diese Integration herum gebaut ist, und scruysberghs, dem in diesen Konfigurationen gedankt wird.
- [fonske](https://github.com/fonske) für die Modbus-TCP-Konfiguration der Venus E v3.
- [ViperRNMC](https://github.com/ViperRNMC) für die Integration Marstek Venus Modbus.

## Lizenz

Apache 2.0, siehe [LICENSE](LICENSE).
