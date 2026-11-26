<img src="custom_components/marstek_goedkoop_laden/brand/icon.png" width="96" align="right" alt="">

# Marstek Goedkoop Laden voor Home Assistant

[🇬🇧 English](README.md) · 🇳🇱 Nederlands · [🏳️ Frysk](README.fy.md) · [🇩🇪 Deutsch](README.de.md) · [🇫🇷 Français](README.fr.md) · [🇪🇸 Español](README.es.md) · [🇸🇪 Svenska](README.sv.md) · [🇳🇴 Norsk](README.nb.md)

[![Open your Home Assistant instance and open this repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=rvdwal1991&repository=Marstek-Cheap-Charging-for-HA&category=integration)
[![Open your Home Assistant instance and start setting up the integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=marstek_goedkoop_laden)

Laadt een Marstek Venus-thuisbatterij bij in de goedkoopste uren van een dynamisch
stroomcontract, zodat hij vol is voordat de stroom duur wordt.

**Hardware en compatibiliteit.** De integratie stuurt een Marstek Venus aan via de RS485-besturingsregisters.
Alleen de eerste rij is op een echte accu gedraaid:

| Koppeling | Model | Status |
|---|---|---|
| LilyGO T-CAN485 + ESPHome (RS485) | Venus E v2 | **Getest** op echte hardware (de opzet waarop hij is gebouwd) |
| Modbus-hub in Home Assistant, via RS485-naar-TCP-converter (Elfin EW11 en vergelijkbaar) | Venus E v1/v2 | Alleen getest met nagebootste aanroepen |
| Modbus-hub in Home Assistant, rechtstreeks via Ethernet | Venus E v3 | Alleen getest met nagebootste aanroepen |
| Integratie *Marstek Venus Modbus* (ViperRNMC) | Venus E v3 | Alleen getest met nagebootste aanroepen |
| Een van bovenstaande | Venus A, Venus D, andere modellen | **Niet gecontroleerd, niet getest.** Ze zouden de besturingsregisters delen, maar dat is niet geverifieerd. Stel de accucapaciteit in bij de opties (standaard 5,12 kWh). |
| Cloud, app of andere integraties | alle | Niet ondersteund |

De koppelingen in detail:

- **LilyGO T-CAN485 met ESPHome** via RS485, met de configuratie van
  [MarstekVenus-LilygoRS485](https://github.com/Superduper1969/MarstekVenus-LilygoRS485). Dit is de
  opzet waarop de integratie is gebouwd en waarmee hij is getest. Hij gebruikt de entiteiten die
  deze opzet levert: *RS485 Control Mode*, *Forcible Charge/Discharge*, *Forcible Charge Power*
  (verplicht) en, optioneel, *Max. Charge Power*, *Max. Discharge Power*, *Forcible Discharge
  Power*, *Discharging Cutoff Capacity* en de totaaltellers van geladen en ontladen energie.
- **Modbus in Home Assistant**, met een Modbus-hub die je zelf in `configuration.yaml` zet: een
  Elfin EW11 of andere RS485-naar-TCP-converter
  ([MarstekVenus-ElfinEW11](https://github.com/Superduper1969/MarstekVenus-ElfinEW11)), of de
  **Venus E v3 rechtstreeks via Ethernet** (Modbus TCP, poort 502, unit 1, EMS V144 of nieuwer;
  [MarstekVenusV3-modbus-TCP-IP](https://github.com/fonske/MarstekVenusV3-modbus-TCP-IP)). De
  integratie leest de registersensoren van die opzet en schrijft de registers 42000
  (RS485-besturing), 42010 (forceermodus), 42020/42021 (geforceerd laad-/ontlaadvermogen) en, als je
  de sensoren opgeeft, 44002/44003 (maximaal laad-/ontlaadvermogen) met `modbus.write_register`. Met
  het maximale ontlaadvermogen werken *Vasthouden* en *Geen verlies* ook, zonder niet. De Venus E v3
  heeft de laadtoestand in register 34002 (schaal 0,1), niet in 32104.
- **De integratie *Marstek Venus Modbus***
  ([ViperRNMC/marstek_venus_modbus](https://github.com/ViperRNMC/marstek_venus_modbus)), die ook
  Modbus TCP spreekt (Ethernet bij een Venus E v3, of een RS485-gateway). Kies dit als je die
  integratie al gebruikt: zij levert de entiteiten (`switch` RS485-besturing, `select` forceermodus,
  `number` vermogens). Zet daar eerst de schakelaar *RS485 control mode* en de select *Force mode*
  aan, ze staan standaard uit.

De opties Modbus en Marstek Venus Modbus zijn **nieuw en tot nu toe alleen getest met nagebootste
aanroepen, niet op echte hardware**.

Andere manieren om de accu te koppelen (cloud, andere integraties) zijn niet getest en werken
vermoedelijk niet, omdat ze deze RS485-besturing niet bieden.

**Dynamische energieprijzen:** deze integratie heeft alleen zin met een **dynamisch stroomcontract**,
waarbij de prijs elk uur verandert. Hij laadt in de goedkoopste uren en mijdt de dure, dus bij een
vast tarief valt er niets te winnen. Hij is gebouwd rond de Nederlandse markt en de prijzen van
Zonneplan (uurprijzen, voor de volgende dag gepubliceerd tussen 13:00 en 15:00). Elke prijssensor
met een uurprijslijst als attribuut volstaat, zie [Prijssensor](#prijssensor).

Planregel, stroomschema en kaarten volgen de optie *Taal* (Automatisch, Nederlands, English, Frysk, Deutsch, Français, Español, Svenska of Norsk;
automatisch volgt Home Assistant als dat een van deze is, anders Engels). Entiteitsnamen volgen
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

Is de uurprijs negatief, dan laadt de accu uit het net, los van het laadplan en ook als de
prijssturing uit staat. Dit heeft een eigen schakelaar die **standaard aan** staat.

Er wordt gekeken naar het hele **venster** met opeenvolgende negatieve uren, niet alleen naar het
huidige uur, en daar wordt het meeste uit gehaald:

1. Hij rekent uit hoeveel de accu nog kan opnemen (SoC tot 100 %).
2. Hij verdeelt die energie over de uren **naar hun waarde**: hoe negatiever de prijs, hoe meer er
   in dat uur geladen wordt (tot wat een uur aankan op het maximale vermogen). Voorbeeld: drie
   negatieve uren van −€ 0,03, −€ 0,20 en −€ 0,12 en nog 3 kWh te laden. Het uur van −€ 0,20 krijgt
   ongeveer 1,9 kWh en het uur van −€ 0,12 ongeveer 1,2 kWh. Het uur van −€ 0,03 zou onder het
   minimale laadvermogen blijven en valt af; zijn deel gaat naar de andere twee.
3. Doordat de energie over de uren is verdeeld, blijft het vermogen lager dan kort op vol vermogen
   laden. Kan de accu meer opnemen dan het venster biedt, dan wordt elk uur tot het maximum gevuld.
   Een enkel uur dat de accu niet kan vullen, wordt op vol vermogen geladen.
4. De planregel en het stroomschema tonen het venster, de gekozen uren, het vermogen en de
   verwachte opbrengst (wat je krijgt om te laden).

De optie *Negatieve prijs: verdeling van de energie* schakelt tussen twee manieren:

- **Naar waarde verdelen** (standaard): zoals hierboven beschreven, lager vermogen, iets minder
  opbrengst.
- **Maximale opbrengst**: de uren worden een voor een gevuld, de beste prijs eerst, elk op vol
  vermogen, en de rest gaat naar het volgende beste uur. In het voorbeeld neemt het uur van −€ 0,20
  2,25 kWh op vol vermogen en het uur van −€ 0,12 de resterende 0,8 kWh, wat ongeveer € 0,55
  oplevert in plaats van € 0,52. De prijs is meer korte stoten op vol vermogen.

Zodra de prijs weer positief is of de accu vol is, gaat de Marstek terug naar anti-feed. Het plan
wordt elke minuut opnieuw berekend; een uur dat al in gebruik is krijgt iets extra speling
voordat het afvalt omdat het onder het minimale vermogen blijft.

De grens is instelbaar (*Negatieve prijs: grens*, standaard € 0,00). Er wordt gekeken naar de
prijs uit de prijssensor, bij Zonneplan dus de prijs inclusief belastingen.

## Zonneverwachting

Met zonnepanelen wordt de accu overdag gratis gevuld. Laad je hem 's nachts vol uit het net, dan
is er geen ruimte meer voor het zonne-overschot en gaat dat voor weinig of niets naar het net,
wat nu de salderingsregeling stopt zwaarder weegt. Daarom houdt de integratie rekening met de
verwachte zonne-opbrengst:

1. Hij leest de verwachting uit het **Energie-dashboard** van Home Assistant (*Instellingen →
   Dashboards → Energie → Zonnepanelen → Zonne-opbrengstverwachting*). Forecast.Solar, Solcast,
   Open-Meteo en andere verwachtingsintegraties werken, en er hoeft niets extra te worden
   ingesteld. Staat daar geen verwachting, dan verandert er niets.
2. Hij rekent het verwachte overschot uit: per uur de verwachting, vermenigvuldigd met de
   betrouwbaarheid (standaard 70 %), min je eigen verbruik (de instelling *Verkoop: gemiddeld
   eigen verbruik*).
3. Hij laadt 's nachts alleen zoveel bij dat er bij zonsopkomst ruimte is voor dat overschot: de
   energie die je eigen verbruik tot dan opmaakt, plus wat er nog bij moet. Op een zonnige dag is
   dat een paar kWh in plaats van een volle accu, of niets (de planregel zegt dan dat de zon de
   accu bijvult).
4. Een bewolkte dag geeft weinig of geen overschot, en dan wordt de accu vol geladen zoals
   voorheen.

Dit kan uit met *Zonneverwachting gebruiken*. De verwachting wordt elke 30 minuten gelezen. Hij
verlaagt alleen de hoeveelheid die wordt bijgeladen; hij verschuift geen laaduren en verandert
niets aan verkopen.

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
3. Kies hoe je Marstek is gekoppeld (*LilyGO RS485 met ESPHome*, *Modbus in Home Assistant* of *Marstek Venus Modbus-integratie*) en
   daarna de prijssensor en de entiteiten van de Marstek. Wat herkend wordt, staat al ingevuld. Bij
   Modbus vul je ook de naam van je Modbus-hub in (bijvoorbeeld `MarstekVenus`) en het slaveadres.

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
| Taal | Automatisch | Taal van planregel, stroomschema en kaarten: Automatisch, Nederlands, English, Frysk, Deutsch, Français, Español, Svenska of Norsk. |
| Aanschafprijs accu | € 0 | Voor de afschrijving. 0 zet de afschrijving uit. |
| Levensduur accu (cycli) | 6000 | Verwacht aantal volledige cycli. Afschrijving per kWh = prijs ÷ (cycli × capaciteit); bijvoorbeeld € 1.500 over 6.000 cycli van 5,12 kWh is ongeveer € 0,049 per kWh. |
| Zonneverwachting gebruiken | Aan | Houd bij het bijladen 's nachts rekening met de verwachte zonne-opbrengst uit het Energie-dashboard. |
| Betrouwbaarheid zonneverwachting | 70 % | Het deel van de verwachting waarop je rekent. Lager is voorzichtiger. |
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

De integratie levert zeven kaarten mee; er hoeft geen resource te worden toegevoegd. Ververs de
browser na het installeren of bijwerken. Elke kaart is in te stellen in de kaarteditor (de
visuele editor) en in YAML, en laat je `entity` weg dan wordt de laadplan-sensor zelf gevonden.

| Kaart | Inhoud |
|---|---|
| `custom:marstek-goedkoop-laden-card` | Stroomschema: de tijdlijn van vandaag en per onderdeel (bijladen, verkoop, negatieve prijs, vasthouden) welke controles slagen en op welke het stopt. |
| `custom:marstek-goedkoop-laden-compact-card` | Hetzelfde in een paar regels: de tijdlijn, per onderdeel de uitkomst met de reden, en één regel met de opbrengst. |
| `custom:marstek-goedkoop-laden-opbrengst-card` | Alleen de opbrengst: vandaag, deze week, vorige week, deze maand en de verwachting van het huidige plan. |
| `custom:marstek-goedkoop-laden-schakelaars-card` | Compact: knoppen om bijladen, verkoop, laden bij negatieve prijs, vasthouden en geen verlies aan of uit te zetten. |
| `custom:marstek-goedkoop-laden-status-card` | Wat er nu gebeurt, de laadtoestand als balk, de prijs nu en de volgende stap. |
| `custom:marstek-goedkoop-laden-prijzen-card` | Prijsgrafiek zonder extra kaarten: de uren met bijladen, verkoop en negatieve prijzen gemarkeerd, en een lijn voor nu. |
| `custom:marstek-goedkoop-laden-voorraad-card` | De bijgeladen voorraad, de kostprijs, het rendement, de afschrijving per kWh en de capaciteit. |

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

Opties van de andere kaarten (allemaal ook in de kaarteditor):

| Kaart | Optie | Standaard | Betekenis |
|---|---|---|---|
| stroomschema, compact | `show_timeline` | `true` | De tijdlijn van vandaag tonen. |
| stroomschema, compact, schakelaars | `lanes` | alle vijf | Welke onderdelen: `bijladen`, `verkoop`, `negatief`, `vasthouden`, `geen_verlies`. |
| status | `show_soc`, `show_price`, `show_next` | `true` | De laadtoestandbalk, de prijs nu, de volgende stap. |
| prijzen | `hours_back` | `2` | Aantal uren terug. |
| prijzen | `hours_ahead` | `0` | Aantal uren vooruit; 0 is tot de laatste bekende prijs. |
| prijzen | `show_values` | `false` | De prijs boven elke staaf tonen (tot 24 staven). |
| prijzen | `height` | `140` | Hoogte van de grafiek in pixels. |
| voorraad | `tiles` | alle vijf | `voorraad`, `kostprijs`, `rendement`, `afschrijving`, `capaciteit`. |
| voorraad | `notes` | `true` | De toelichting onder de kaart. |

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
