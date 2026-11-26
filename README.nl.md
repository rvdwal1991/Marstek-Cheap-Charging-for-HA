<img src="custom_components/marstek_goedkoop_laden/brand/icon.png" width="96" align="right" alt="">

# Marstek Goedkoop Laden voor Home Assistant

🇳🇱 Nederlands · [🇬🇧 English](README.md)

[![Open your Home Assistant instance and open this repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=rvdwal1991&repository=Marstek-Cheap-Charging-for-HA&category=integration)
[![Open your Home Assistant instance and start setting up the integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=marstek_goedkoop_laden)

Laadt een Marstek Venus-thuisbatterij bij in de goedkoopste uren van een dynamisch
stroomcontract, zodat hij vol is voordat de stroom duur wordt.

**Hardware: alleen getest met de LilyGO RS485.** Deze integratie is gebouwd op, en alleen getest
met, een Marstek Venus (5,12 kWh) die via RS485 wordt aangestuurd door een **LilyGO T-CAN485 met
ESPHome**. Hij gebruikt de entiteiten die deze opzet levert: *RS485 Control Mode*, *Forcible
Charge/Discharge*, *Forcible Charge Power* (verplicht) en, optioneel, *Max. Charge Power*,
*Max. Discharge Power*, *Forcible Discharge Power*, *Discharging Cutoff Capacity* en de
totaaltellers van geladen en ontladen energie. Andere manieren om de accu te koppelen (cloud,
Modbus TCP, andere integraties) zijn niet getest en werken vermoedelijk niet, omdat ze deze
RS485-besturing niet bieden.

Planregel, stroomschema en kaarten volgen de optie *Taal* (Automatisch, Nederlands of English;
automatisch volgt Home Assistant: Nederlands bij Nederlands, anders Engels). Entiteitsnamen volgen
de taal van Home Assistant. Statuswaarden en attribuutnamen
(`laden`, `tekst`, …) staan vast.

Het uitgangspunt is **zelfvoorzienend zijn**. De batterij blijft gewoon zelf regelen
(anti-feed, nul op de meter). Deze integratie doet maar één ding erbij: op de goedkoopste
uren uit het net bijladen. Daarnaast is er een aparte, standaard uitgeschakelde optie om
**overschot te verkopen** in de duurste uren.

## Wat hij doet

1. **Loont bijladen?** Een uur is goedkoop genoeg als de prijs lager is dan
   `rendement × (gemiddelde van de 6 duurste uren in de 18 uur erna) − marge`.
   Het rendement (laden en weer ontladen, bij mij ongeveer 77 %) komt uit de energietellers
   van de Marstek.
2. **Venster.** Het eerste blok goedkope uren is het laadvenster. Een of twee uren die net niet
   goedkoop genoeg zijn, onderbreken het blok niet; geladen wordt alleen in de goedkope uren zelf.
3. **Laaduren.** Binnen dat venster kiest hij de goedkoopste uren, precies zoveel als nodig
   is om van de huidige SoC naar 100 % te komen.
   Is het venster te kort om vol te komen, dan plant hij alleen wat erin past en zegt de
   planregel dat.
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

## Vasthouden onder de kostprijs

Bijgeladen stroom heeft een kostprijs: de laadprijs gedeeld door het rendement. Zou de accu die
stroom direct na het laden weer afgeven in uren die goedkoper zijn dan die kostprijs, dan kost
het bijladen geld. Daarom wordt het ontladen tegengehouden zolang:

- er bijgeladen voorraad in de accu zit (zie *Opbrengst*), en
- de uurprijs lager is dan de kostprijs van die voorraad.

Het huis gebruikt dan stroom uit het net, die op dat moment goedkoper is dan wat er in de accu
zit. Zodra de prijs op of boven de kostprijs komt, of de voorraad op is, regelt de Marstek weer
zelf. Dit heeft een eigen schakelaar die **standaard aan** staat.

Technisch zet de integratie het maximale ontlaadvermogen (*Max. Discharge power*) op 0. De
Marstek blijft in anti-feed, dus laden uit zonne-overschot gaat gewoon door. Zet een andere
automatisering dat vermogen tijdens het vasthouden op een andere waarde (bijvoorbeeld een
begrenzer voor de laadpaal), dan onthoudt de integratie die waarde, zet het weer op 0 en
herstelt de onthouden waarde na afloop.

Let op: de Marstek kan geen onderscheid maken tussen bijgeladen stroom en zonnestroom. Tijdens
het vasthouden wordt dus de hele accu niet ontladen.

## Geen verlies

Een aparte schakelaar (standaard uit) die de integratie strikt maakt: bijgeladen stroom wordt
nooit onder de kostprijs gebruikt of verkocht.

- **Vasthouden wordt afgedwongen**, ook als de schakelaar *Vasthouden* uit staat.
- **Verkopen onder de kostprijs wordt tegengehouden.** Zit er bijgeladen voorraad in de accu
  en is de verkoopprijs lager dan de kostprijs daarvan, dan wordt er niet verkocht.

Elke geboekte kWh levert dan minstens de kostprijs op, dus de opbrengst van een dag kan niet
onder nul komen. Wat het niet kan uitsluiten:

- **Stilstand.** Komt de prijs lang niet boven de kostprijs, dan blijft de accu zolang
  geblokkeerd voor ontladen, ook voor opgeslagen zonnestroom.
- **Afwijkend rendement.** De kostprijs rekent met het gemiddelde rendement. Levert de accu in
  een cyclus minder dan dat, dan is de accu leeg voordat de voorraad in de boeken op is; die
  rest vervalt dan zonder dat er verlies wordt geboekt.
- **Slijtage** van de accu telt niet mee; gebruik daarvoor de minimale winst per kWh.

De integratie rekent direct opnieuw zodra een nieuw prijsvak begint, zodat het vasthouden niet
tot een minuut te laat ingaat.

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
| `switch.*_vasthouden` | Aan (standaard): niet ontladen zolang de uurprijs onder de kostprijs van de bijgeladen voorraad ligt. Attributen `nu_actief`, `tot`, `voorraad_kwh`, `kostprijs`. |
| `switch.*_geen_verlies` | Aan: vasthouden afgedwongen en nooit verkopen onder de kostprijs. Attributen `vasthouden_actief`, `verkoop_tegengehouden`, `voorraad_kwh`, `kostprijs`. |
| `switch.*_verkoop` | Aan: overschot wordt in de duurste uren verkocht. Staat los van de prijssturing. |
| `sensor.*_verkoopplan` | Status: `verkopen`, `gepland`, `geen` of `onbekend`. Attributen: `verkoopuren`, `vermogen`, `overschot_kwh`, `reserve_soc`, `drempelprijs`, `terugkoopprijs` en `tekst`. |
| `sensor.*_laadplan` | Status: `laden`, `gepland`, `klaar`, `vol`, `geen` of `onbekend`. Attributen: `laaduren`, `venster`, `eind`, `uren_nodig`, `vermogen`, `klaar_tot`, `tekst` (leesbare samenvatting) en `stroomschema` (tijdlijn en controles voor de kaart). |
| `sensor.*_gepland_laadvermogen` | Het uitgesmeerde laadvermogen in W. |
| `sensor.*_bij_te_laden` | Energie uit het net die nodig is om vol te komen, in kWh. |
| `sensor.*_start_bijladen` / `*_einde_bijladen` | Begin en einde van de geplande laadbeurt. |
| `sensor.*_opbrengst_vandaag` / `*_opbrengst_deze_week` / `*_opbrengst_deze_maand` | Gerealiseerde opbrengst in euro sinds 00:00, sinds maandag 00:00 en sinds de eerste van de maand (zie *Opbrengst*). Attributen: de voorraad en, bij vandaag, wat er is bijgeladen en gebruikt. |
| `sensor.*_opbrengst_dit_jaar` | Gerealiseerde opbrengst sinds 1 januari. |
| `sensor.*_opbrengst_vorige_week` | Het eindbedrag van de week daarvoor. |
| `sensor.*_verwachte_opbrengst` | Geschatte opbrengst van de huidige plannen in euro (bijladen plus verkoop); attribuut `regels` met de uitsplitsing. |
| `sensor.*_rendement` | Het rendement waarmee wordt gerekend, in procent. Attribuut `bron`: gemeten uit de energietellers of de vaste waarde. |
| `sensor.*_gemiddelde_laadprijs` | Gemiddelde prijs van de laaduren in €/kWh. |

De namen hierboven horen bij een Nederlandstalige installatie. Staat de systeemtaal van Home
Assistant op Engels, dan heten ze `*_charge_plan`, `*_price_control` enzovoort, en zijn ook de
planregel, het stroomschema en de kaarten Engels.

## Installatie

1. Installeer met HACS (knop bovenaan, of voeg deze repo toe als aangepaste repository, categorie
   *Integratie*), of kopieer `custom_components/marstek_goedkoop_laden` naar
   `/config/custom_components/`. Herstart Home Assistant.
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
| Taal | Automatisch | Taal van planregel, stroomschema en kaarten: Automatisch, Nederlands of English. |
| Aanschafprijs accu | € 0 | Voor de afschrijving. 0 zet de afschrijving uit. |
| Levensduur accu (cycli) | 6000 | Verwacht aantal volledige cycli. Afschrijving per kWh = prijs ÷ (cycli × capaciteit); bijvoorbeeld € 1.500 over 6.000 cycli van 5,12 kWh is ongeveer € 0,049 per kWh. |
| Minimale winst per kWh | € 0,02 | Wat bijladen na aftrek van het laadverlies minstens moet opleveren. Uren die minder dan een halve cent boven de grens liggen tellen ook mee, zodat een bijna vlakke nacht niet om een fractie van een cent wordt versnipperd. |
| Aantal duurste uren | 6 | Met hoeveel dure uren erna een uur wordt vergeleken. |
| Uren vooruit kijken | 18 | Hoe ver na een uur naar dure uren wordt gezocht. |
| Minimaal bekende uren vooruit | 8 | Uren met minder bekende prijzen erna tellen niet mee. |
| Minimaal laadvermogen | 400 W | Ondergrens bij het uitsmeren. |
| Rendement als de tellers ontbreken | 0,77 | Het rendement wordt berekend uit de energietellers van de Marstek (totaal ontladen ÷ totaal geladen, begrensd op 70–95 %). Deze vaste waarde geldt alleen als die tellers ontbreken. Het rendement van alleen laden of alleen ontladen is de wortel daarvan. |
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

De integratie levert vier kaarten mee; er hoeft geen resource te worden toegevoegd. Ververs de
browser na het installeren of bijwerken.

| Kaart | Inhoud |
|---|---|
| `custom:marstek-goedkoop-laden-card` | Stroomschema: de tijdlijn van vandaag en per onderdeel (bijladen, verkoop, negatieve prijs, vasthouden) welke controles slagen en op welke het stopt. |
| `custom:marstek-goedkoop-laden-compact-card` | Hetzelfde in een paar regels: de tijdlijn, per onderdeel de uitkomst met de reden, en één regel met de opbrengst. |
| `custom:marstek-goedkoop-laden-opbrengst-card` | Alleen de opbrengst: vandaag, deze week, vorige week, deze maand en de verwachting van het huidige plan. |
| `custom:marstek-goedkoop-laden-schakelaars-card` | Compact: knoppen om bijladen, verkoop, laden bij negatieve prijs, vasthouden en geen verlies aan of uit te zetten. |

```yaml
type: custom:marstek-goedkoop-laden-card
entity: sensor.marstek_goedkoop_laden_laadplan   # optioneel
title: Prijssturing                              # optioneel
opbrengst: false                                 # optioneel, zie hieronder
```

De opbrengstkaart is aan te passen, in YAML of in de kaarteditor:

```yaml
type: custom:marstek-goedkoop-laden-opbrengst-card
tiles: [vandaag, maand, jaar]   # kies uit: vandaag, week, vorige_week, maand, jaar, verwacht (in deze volgorde)
expected_details: false         # verberg de regels per onderdeel van het plan (standaard: true)
notes: false                    # verberg de toelichting onder de kaart (standaard: true)
```

| Optie | Standaard | Betekenis |
|---|---|---|
| `tiles` | alle zes | Welke tegels en in welke volgorde: vandaag, deze week, vorige week, deze maand, dit jaar, verwacht (plan). |
| `expected_details` | `true` | De regels met de verwachte opbrengst per onderdeel (bijladen, verkoop). |
| `notes` | `true` | De toelichting met de bijgeladen voorraad, wat er vandaag is bijgeladen en de afschrijving. |

`opbrengst` bepaalt of de stroomschemakaart ook de opbrengst toont: standaard uit bij de gewone
kaart, standaard één regel bij de compacte kaart. In het stroomschema is groen een geslaagde
controle, rood de controle waarop het stopt en gestreept een uitkomst waarbij niets gebeurt.
Alle kaarten lezen het attribuut `stroomschema` van de laadplan-sensor.

## Opbrengst

**Afschrijving.** Stel je een aanschafprijs in, dan kost elke kWh die de accu ontlaadt een beetje slijtage: prijs ÷ (cycli × capaciteit). Dat gaat af van de gerealiseerde opbrengst (vandaag, week, maand), telt mee in de verwachte opbrengst en in de beslissingen: een uur is alleen laadwaardig als het ook na de slijtage nog wint, verkopen vraagt de slijtage bovenop de verkoopmarge, en *Vasthouden* en *Geen verlies* nemen kostprijs plus slijtage als break-evenprijs. Bij een prijs van 0 (standaard) verandert er niets.

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
4. **Vandaag** is de som sinds 00:00, **deze week** sinds maandag 00:00 en **deze maand** sinds de eerste van de maand. **Vorige week** is het eindbedrag van de week daarvoor.

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


## Wijzigingen

Zie [CHANGELOG.md](CHANGELOG.md) (Engels), inclusief de breaking changes.

## Licentie

Apache 2.0, zie [LICENSE](LICENSE).
