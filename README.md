<img src="custom_components/marstek_goedkoop_laden/brand/icon.png" width="96" align="right" alt="">

# Marstek Goedkoop Laden voor Home Assistant

Laadt een Marstek Venus-thuisbatterij bij in de goedkoopste uren van een dynamisch
stroomcontract, zodat hij vol is voordat de stroom duur wordt.

Het uitgangspunt is **zelfvoorzienend zijn**. De batterij blijft gewoon zelf regelen
(anti-feed, nul op de meter). Deze integratie doet maar één ding erbij: op de goedkoopste
uren uit het net bijladen. Daarnaast is er een aparte, standaard uitgeschakelde optie om
**overschot te verkopen** in de duurste uren.

## Wat hij doet

1. **Loont bijladen?** Een uur is goedkoop genoeg als de prijs lager is dan
   `rendement × (gemiddelde van de 6 duurste uren in de 18 uur erna) − marge`.
   Het rendement (laden en weer ontladen, bij mij ongeveer 77 %) komt uit de energietellers
   van de Marstek.
2. **Venster.** Het eerste aaneengesloten blok goedkope uren is het laadvenster.
3. **Laaduren.** Binnen dat venster kiest hij de goedkoopste uren, precies zoveel als nodig
   is om van de huidige SoC naar 100 % te komen.
4. **Vermogen uitsmeren.** Het laadvermogen is de nog bij te laden energie gedeeld door de
   resterende tijd in de laaduren. Zo worden het net en de groep in huis niet zwaarder belast
   dan nodig. Onderweg wordt het vermogen steeds bijgesteld.
5. **Klaar is klaar.** Zijn de laaduren voorbij of is de accu vol, dan gaat de Marstek terug
   naar anti-feed. In hetzelfde venster start hij niet opnieuw en hij houdt de lading niet vast.

Er wordt alleen gerekend met **gepubliceerde** prijzen. Het plan voor de nacht ontstaat dus
zodra de prijzen van morgen bekend zijn (bij Zonneplan tussen 13:00 en 15:00).

Voorbeeld (10 november 2026, accu op 12 %): goedkoop venster 23:00–07:00, bijladen om 02:00,
03:00 en 04:00 op ongeveer 1900 W voor gemiddeld € 0,37, daarna overdag € 0,55–0,67.

## Laden bij een negatieve prijs

Is de uurprijs negatief, dan laadt de accu altijd op vol vermogen tot hij vol is, los van het
laadplan en ook als de prijssturing uit staat. Dit heeft een eigen schakelaar die **standaard
aan** staat. Zodra de prijs weer positief is of de accu vol is, gaat de Marstek terug naar
anti-feed.

De grens is instelbaar (*Negatieve prijs: grens*, standaard € 0,00). Er wordt gekeken naar de
prijs uit de prijssensor, bij Zonneplan dus de prijs inclusief belastingen.

## Verkopen (optioneel)

Verkopen heeft een eigen schakelaar en staat los van het bijladen. Er wordt alleen verkocht
wat echt over is. In een uur wordt verkocht als dit allemaal geldt:

1. **Er komt een goedkope laadbeurt aan**: er ligt een laadvenster met gepubliceerde prijzen
   in het verschiet, dus bekend is wat terugladen kost.
2. **De opbrengst is duidelijk hoger dan terugladen**: verkoopprijs ≥ laadprijs gedeeld door
   het rendement, plus de verkoopmarge (standaard € 0,10 per kWh).
3. **Er is overschot boven de reserve**. De reserve is de ontlaadgrens van de Marstek plus het
   verwachte eigen verbruik tot het terugladen (gemiddeld huisverbruik × uren), met een
   instelbaar minimum (standaard 20 %).
4. **Het is een van de duurste uren** tot het laadvenster.

Het verkoopvermogen wordt net als bij laden uitgesmeerd over de gekozen uren. Op de reserve
stopt de verkoop en gaat de Marstek terug naar anti-feed.

In de winter is er zelden overschot: met een accu van 5 kWh vraagt het eigen verbruik tot de
volgende laadbeurt meestal de hele lading. De optie doet vooral iets als de zon de accu vult
en er 's avonds een prijspiek is.

**Na het einde van de salderingsregeling** (1 januari 2027) levert terugleveren minder op dan
de uurprijs. Stel dan *Verkoopprijs: factor* en *aftrek* in: verkoopprijs = uurprijs × factor −
aftrek. Voor de kale marktprijs bij Zonneplan is dat ongeveer 0,826 en € 0,108.

## Aansturing van de Marstek

De integratie stuurt via de RS485-besturing (LilyGO T-CAN485 met ESPHome):

| Moment | Opdrachten |
|---|---|
| Start bijladen | laadvermogen instellen → *Forcible charge/discharge* op `charge` → *RS485 Control Mode* op `enable` |
| Tijdens bijladen | laadvermogen bijstellen (stappen van 100 W) |
| Klaar, of prijssturing uit | *RS485 Control Mode* op `disable`, forceren terug op `charge`, laadvermogen terug naar het maximum |
| Start verkopen | ontlaadvermogen instellen → forceren op `discharge` → *RS485 Control Mode* op `enable` |
| Verkoop klaar, of verkoop uit | zelfde als bij klaar: terug naar de rusttoestand |

Forceer-**ont**laden dat je zelf start blijft ongemoeid. Forceer-laden dat je zelf start wordt
teruggezet zolang de prijssturing aan staat; zet daarvoor de schakelaar uit.

## Entiteiten

| Entiteit | Inhoud |
|---|---|
| `switch.*_prijssturing` | Aan: het laadplan wordt uitgevoerd. Uit: de Marstek regelt alles zelf. Uitzetten zet de Marstek direct terug op anti-feed. |
| `switch.*_laden_bij_negatieve_prijs` | Aan (standaard): bij een negatieve uurprijs altijd laden op vol vermogen. Attribuut `nu_actief`. |
| `switch.*_verkoop` | Aan: overschot wordt in de duurste uren verkocht. Staat los van de prijssturing. |
| `sensor.*_verkoopplan` | Status: `verkopen`, `gepland`, `geen` of `onbekend`. Attributen: `verkoopuren`, `vermogen`, `overschot_kwh`, `reserve_soc`, `drempelprijs`, `terugkoopprijs` en `tekst`. |
| `sensor.*_laadplan` | Status: `laden`, `gepland`, `klaar`, `vol`, `geen` of `onbekend`. Attributen: `laaduren`, `venster`, `eind`, `uren_nodig`, `vermogen`, `klaar_tot`, `tekst` (leesbare samenvatting) en `stroomschema` (tijdlijn en controles voor de kaart). |
| `sensor.*_gepland_laadvermogen` | Het uitgesmeerde laadvermogen in W. |
| `sensor.*_bij_te_laden` | Energie uit het net die nodig is om vol te komen, in kWh. |
| `sensor.*_start_bijladen` / `*_einde_bijladen` | Begin en einde van de geplande laadbeurt. |
| `sensor.*_opbrengst_vandaag` / `*_opbrengst_deze_week` | Gerealiseerde opbrengst in euro sinds 00:00 en sinds maandag 00:00 (zie *Opbrengst*). Attributen: de voorraad en, bij vandaag, wat er is bijgeladen en gebruikt. |
| `sensor.*_verwachte_opbrengst` | Geschatte opbrengst van de huidige plannen in euro (bijladen plus verkoop); attribuut `regels` met de uitsplitsing. |
| `sensor.*_gemiddelde_laadprijs` | Gemiddelde prijs van de laaduren in €/kWh. |

De namen hierboven horen bij een Nederlandstalige installatie. Staat de systeemtaal van Home
Assistant op Engels, dan heten ze `*_charge_plan`, `*_price_control` enzovoort; hernoem ze dan
naar wens.

## Installatie

1. Kopieer `custom_components/marstek_goedkoop_laden` naar `/config/custom_components/`
   (of voeg deze repo toe als aangepaste repository in HACS) en herstart Home Assistant.
2. Ga naar *Instellingen → Apparaten en diensten → Integratie toevoegen → Marstek Goedkoop Laden*.
3. Kies de prijssensor en de entiteiten van de Marstek. Wat herkend wordt, staat al ingevuld.

Vereist: Home Assistant 2026.3 of nieuwer.

### Prijssensor

De integratie leest de prijzen uit een attribuut van één sensor (standaard `forecast`):

- Zonneplan-uurprijzen: `start_date`, `end_date`, `price_tax_included.amount`
- Zonneplan (oud): `datetime`, `electricity_price`
- Algemeen: `start` (of `start_time`, `datetime`) en `price` (of `value`, `prijs`) in €/kWh

### Instellingen

Via *Configureren* op de integratie:

| Instelling | Standaard | Betekenis |
|---|---|---|
| Minimale winst per kWh | € 0,02 | Wat bijladen na aftrek van het laadverlies minstens moet opleveren. |
| Aantal duurste uren | 6 | Met hoeveel dure uren erna een uur wordt vergeleken. |
| Uren vooruit kijken | 18 | Hoe ver na een uur naar dure uren wordt gezocht. |
| Minimaal bekende uren vooruit | 8 | Uren met minder bekende prijzen erna tellen niet mee. |
| Minimaal laadvermogen | 400 W | Ondergrens bij het uitsmeren. |
| Rendement | 0,77 | Alleen gebruikt als de energietellers niet zijn ingevuld. |
| Accucapaciteit | 5,12 kWh | Alleen gebruikt als er geen capaciteitssensor is ingevuld. |
| Negatieve prijs: grens | € 0,00 | Onder deze uurprijs wordt op vol vermogen geladen. |
| Verkoop: minimale winst per kWh | € 0,10 | Wat verkopen na terugladen minstens moet opleveren. |
| Verkoop: gemiddeld eigen verbruik | 400 W | Bepaalt de reserve tot het terugladen. |
| Verkoop: minimale reserve | 20 % | Onder deze SoC wordt nooit verkocht. |
| Verkoopprijs: factor en aftrek | 1 en € 0 | Verkoopprijs = uurprijs × factor − aftrek. |

Het maximale laadvermogen (de *Max. Charge power* van de Marstek) bepaalt het aantal laaduren.
Zet je dat lager, dan plant hij meer uren en laadt hij rustiger.

## Dashboard

### Kaarten van de integratie

De integratie levert drie kaarten mee; er hoeft geen resource te worden toegevoegd. Ververs de
browser na het installeren of bijwerken.

| Kaart | Inhoud |
|---|---|
| `custom:marstek-goedkoop-laden-card` | Stroomschema: de tijdlijn van vandaag en per onderdeel (bijladen, verkoop, negatieve prijs) welke controles slagen en op welke het stopt. |
| `custom:marstek-goedkoop-laden-compact-card` | Hetzelfde in een paar regels: de tijdlijn, per onderdeel de uitkomst met de reden, en één regel met de opbrengst. |
| `custom:marstek-goedkoop-laden-opbrengst-card` | Alleen de opbrengst: vandaag, deze week en de verwachting van het huidige plan. |

```yaml
type: custom:marstek-goedkoop-laden-card
entity: sensor.marstek_goedkoop_laden_laadplan   # optioneel
title: Prijssturing                              # optioneel
opbrengst: false                                 # optioneel, zie hieronder
```

`opbrengst` bepaalt of de stroomschemakaart ook de opbrengst toont: standaard uit bij de gewone
kaart, standaard één regel bij de compacte kaart. In het stroomschema is groen een geslaagde
controle, rood de controle waarop het stopt en gestreept een uitkomst waarbij niets gebeurt.
Alle kaarten lezen het attribuut `stroomschema` van de laadplan-sensor.

## Opbrengst

Er zijn twee soorten opbrengst: wat het huidige plan naar verwachting oplevert, en wat er
werkelijk is verdiend.

### Verwacht (schatting vooraf)

- **Bijladen**: wat de in te kopen stroom kost, tegenover wat die later waard is. Die waarde
  is het rendement maal de gemiddelde prijs van de dure uren waarmee het laaduur is vergeleken.
- **Verkoop**: de opbrengst van het overschot, min wat terugladen kost.

Tijdens een laadbeurt telt alleen wat nog geladen moet worden.

### Vandaag en deze week (gerealiseerd)

1. Stroom die de integratie uit het net bijlaadt (laadplan of negatieve prijs) wordt een
   **voorraad**: bruikbare kWh = geladen kWh × rendement, met als kostprijs wat die stroom op
   dat moment kostte.
2. Ontlaadt de accu daarna voor eigen verbruik, dan wordt eerst die voorraad opgebruikt. De
   opbrengst is `ontladen kWh × (stroomprijs op dat moment − kostprijs per bruikbare kWh)`.
3. Bij verkoop is de opbrengst `verkochte kWh × verkoopprijs − kostprijs`; voor stroom die niet
   uit de voorraad komt (zonnestroom) is de kostprijs wat terugladen kost.
4. **Vandaag** is de som sinds 00:00, **deze week** sinds maandag 00:00.

Wat nog in de voorraad zit, is nog niet verdiend en telt pas mee als het wordt gebruikt. Stroom
die de zon in de accu stopt en die je later zelf gebruikt telt niet mee: dat doet de Marstek
ook zonder deze integratie. De bedragen komen uit de energietellers van de Marstek en de
uurprijs van dat moment; een tellersprong na een storing wordt niet geboekt.

### Losse kaarten

Planregel (Markdown-kaart):

```yaml
type: markdown
content: >-
  **Laadplan:** {{ state_attr('sensor.marstek_goedkoop_laden_laadplan', 'tekst') }}
  {% if is_state('switch.marstek_goedkoop_laden_prijssturing', 'off') %}
  · ⚠️ prijssturing staat **uit**{% endif %}
```

Grafiek met [apexcharts-card](https://github.com/RomRider/apexcharts-card): de Zonneplan-prijzen
van vandaag en morgen, groen = bijladen, blauw = rest van het goedkope venster, grijs = overig.
Herhaal de reeks drie keer met `'laden'`, `'venster'` en `'rest'` op de plek van `KIES`:

```yaml
type: custom:apexcharts-card
graph_span: 48h
span:
  start: day
now:
  show: true
  label: nu
stacked: true
series:
  - entity: sensor.zonneplan_current_hourly_electricity_tariff
    name: Bijladen
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

## Ontwikkelen

De rekenregel staat los van Home Assistant in `planner.py` en heeft tests met echte prijzen.
De aansturing wordt getest tegen een nagebootst Home Assistant (`tests/test_sturing.py`):

```bash
python3 -m unittest discover -s tests -v
```

Het icoon wordt getekend door `tools/maak_icoon.py` (alleen de standaardbibliotheek).

## Licentie

Apache 2.0, zie [LICENSE](LICENSE).
