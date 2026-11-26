<img src="custom_components/marstek_goedkoop_laden/brand/icon.png" width="96" align="right" alt="">

# Marstek Goedkoop Laden voor Home Assistant

[🇬🇧 English](README.md) · 🇳🇱 Nederlands · [🏳️ Frysk](README.fy.md) · [🇩🇪 Deutsch](README.de.md) · [🇫🇷 Français](README.fr.md) · [🇪🇸 Español](README.es.md) · [🇸🇪 Svenska](README.sv.md) · [🇳🇴 Norsk](README.nb.md)

[![Open your Home Assistant instance and open this repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=rvdwal1991&repository=Marstek-Cheap-Charging-for-HA&category=integration)
[![Open your Home Assistant instance and start setting up the integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=marstek_goedkoop_laden)

Laadt een Marstek Venus-thuisbatterij bij in de goedkoopste uren van een dynamisch
stroomcontract, zodat hij vol is voordat de stroom duur wordt.

Het uitgangspunt is **zelfvoorzienend zijn**: de batterij blijft gewoon zelf regelen (anti-feed,
nul op de meter). Deze integratie doet één ding erbij, uit het net bijladen in de goedkoopste
uren, plus een paar optionele extra's eromheen.

**Je hebt nodig:**

- een **dynamisch stroomcontract** met uurprijzen. Bij een vast tarief valt er niets te winnen.
  Hij is gebouwd rond de Nederlandse markt en Zonneplan (de prijzen voor de volgende dag komen
  tussen 13:00 en 15:00), maar elke sensor met een uurprijslijst volstaat, zie
  [Prijssensor](#prijssensor);
- een Marstek Venus die Home Assistant kan aansturen via RS485 of Modbus, zie
  [Compatibiliteit](#compatibiliteit). **Alleen de opzet met LilyGO RS485 + ESPHome is op een
  echte accu getest.**
- Home Assistant 2026.3 of nieuwer.

## Wat hij doet

| Modus | Standaard | Wat het doet |
|---|---|---|
| **Prijssturing** | uit | Laadt uit het net in de goedkoopste uren en spreidt het vermogen over die uren. |
| **Laden bij negatieve prijs** | aan | Laadt als de uurprijs negatief is en haalt het meeste uit het venster. |
| **Zonneverwachting** | aan | Laadt 's nachts minder bij als de zon de accu overdag vult. Vraagt een zonneverwachting in het Energie-dashboard. |
| **Vasthouden onder kostprijs** | aan | Ontlaadt niet zolang het net goedkoper is dan wat de bijgeladen stroom kostte. |
| **Geen verlies** | uit | Strenge versie van vasthouden: verkoopt bijgeladen voorraad ook nooit onder de kostprijs. |
| **Verkopen** | uit | Verkoopt overschot in de duurste uren. |

Elke modus heeft een eigen schakelaar. **Prijssturing staat na de installatie uit**: stel de
integratie in, controleer of de planregel op de laadplan-sensor klopt en zet hem dan aan.

### Kernpunten

- **Dynamische prijzen.** Laadt in de goedkoopste gepubliceerde uren, en alleen zoveel als na het gemeten rendement loont.
- **Negatieve prijzen.** Spreidt het laden over het hele negatieve venster, gewogen naar wat elk uur waard is; desgewenst voor maximale winst, zie [Laden bij een negatieve prijs](#laden-bij-een-negatieve-prijs).
- **Zonneverwachting.** Gebruikt de verwachting uit het Energie-dashboard: laadt alleen wat de zon niet vult, trekt het verwachte huisverbruik per uur af en leert aan de werkelijke opbrengst hoe betrouwbaar de verwachting is, zie [Zonneverwachting](#zonneverwachting).
- **Afschrijving.** Met een aanschafprijs telt de slijtage per kWh mee in de opbrengst, de verkoopmarge en het break-evenpunt van *Vasthouden onder kostprijs*, zie [Opbrengst](#opbrengst).
- **Kostprijs.** Houdt bij wat de voorraad in de accu kostte en ontlaadt die niet onder die prijs (*Vasthouden onder kostprijs*, *Geen verlies*).
- **Aansluiting.** LilyGO met ESPHome, een Modbus-hub (Elfin EW11 of de Venus E v3 rechtstreeks via ethernet) of de integratie *Marstek Venus Modbus*, zie [Compatibiliteit](#compatibiliteit).
- **Kaarten en talen.** Zeven dashboardkaarten die je in de GUI instelt, en acht talen.

## Snelstart

1. Installeer met HACS (knop hierboven, of voeg deze repository toe als aangepaste repository,
   categorie *Integratie*), of kopieer `custom_components/marstek_goedkoop_laden` naar
   `/config/custom_components/`. Herstart Home Assistant.
2. *Instellingen → Apparaten en diensten → Integratie toevoegen → Marstek Goedkoop Laden*.
3. Kies hoe je Marstek is gekoppeld, daarna de prijssensor en de entiteiten van de Marstek. Wat
   herkend wordt, staat al ingevuld. Bij Modbus vul je ook de naam van je Modbus-hub in
   (bijvoorbeeld `MarstekVenus`) en het slaveadres.
4. Zet de schakelaar **Prijssturing** aan als het plan klopt.
5. Voeg kaarten toe: *Dashboard bewerken → Kaart toevoegen → zoek "Marstek"*, zie
   [Dashboardkaarten](#dashboardkaarten).

Teksten (planregel, stroomschema, kaarten) volgen de optie *Taal*: Automatisch, Nederlands,
English, Frysk, Deutsch, Français, Español, Svenska of Norsk. Automatisch volgt Home Assistant
als dat een van deze is, anders Engels.

## Hoe het laadplan werkt

1. **Loont bijladen?** Een uur is goedkoop genoeg als de prijs lager is dan
   `rendement × (gemiddelde van de 6 duurste uren in de 18 uur erna) − marge`. Het rendement
   (laden en weer ontladen, hier ongeveer 77 % gemeten) komt uit de energietellers van de Marstek.
2. **Venster.** Het eerste blok goedkope uren is het laadvenster. Een of twee uren die net niet
   goedkoop genoeg zijn, onderbreken het blok niet; geladen wordt alleen in de goedkope uren zelf.
3. **Laaduren.** Binnen dat venster kiest hij de goedkoopste uren, precies zoveel als nodig om van
   de huidige SoC naar 100 % te komen. Is het venster te kort om vol te komen, dan plant hij alleen
   wat past en zegt dat in de planregel.
4. **Vermogen spreiden.** Het laadvermogen is de nog bij te laden energie gedeeld door de tijd die
   in de laaduren over is. Zo blijft de belasting van de aansluiting laag. Het vermogen wordt
   onderweg bijgesteld.
5. **Klaar is klaar.** Zijn de laaduren voorbij of is de accu vol, dan gaat de Marstek terug naar
   anti-feed. In hetzelfde venster start hij niet opnieuw.

Er worden alleen **gepubliceerde** prijzen gebruikt, dus het plan voor de nacht verschijnt zodra de
prijzen van morgen bekend zijn. Voorbeeld (10 november 2026, accu op 12 %): goedkoop venster
23:00–07:00, laden om 02:00, 03:00 en 04:00 op ongeveer 1900 W voor gemiddeld € 0,37, tegenover
€ 0,55–0,67 overdag.

### Laden bij een negatieve prijs

Is de uurprijs negatief, dan laadt de accu, los van het laadplan en ook als de prijssturing uit
staat. Er wordt gekeken naar het hele **venster** met opeenvolgende negatieve uren:

1. Hij rekent uit hoeveel de accu nog kan opnemen (SoC tot 100 %).
2. Hij verdeelt die energie over de uren **naar hun waarde**: hoe negatiever de prijs, hoe meer er
   in dat uur geladen wordt, tot wat een uur aankan op het maximale vermogen. Voorbeeld: −€ 0,03,
   −€ 0,20 en −€ 0,12 met 3 kWh te laden geeft ongeveer 1,9 kWh in het uur van −€ 0,20 en 1,2 kWh
   in het uur van −€ 0,12. Het uur van −€ 0,03 zou onder het minimale laadvermogen blijven en valt
   af; zijn deel gaat naar de andere twee.
3. Door het spreiden blijft het vermogen lager dan een korte stoot op vol vermogen. Een enkel uur
   dat de accu niet kan vullen, wordt op vol vermogen geladen.

De optie *Negatieve prijs: verdeling van de energie* kan op **Maximale opbrengst** staan: het
beste uur wordt eerst op vol vermogen gevuld, daarna het volgende. In het voorbeeld levert dat
ongeveer € 0,55 op in plaats van € 0,52, met meer stoten op vol vermogen als prijs. Het plan wordt
elke minuut opnieuw berekend; een uur dat al in gebruik is krijgt iets extra speling voordat het
afvalt.

### Zonneverwachting

Met zonnepanelen wordt de accu overdag gratis gevuld. Laad je hem 's nachts vol uit het net, dan is
er geen ruimte meer voor het overschot en gaat dat voor weinig of niets naar het net, wat nu de
salderingsregeling stopt zwaarder weegt. Daarom kijkt de integratie naar de verwachte
zonne-opbrengst:

1. Hij leest de verwachting uit het **Energie-dashboard** (*Instellingen → Dashboards → Energie →
   Zonnepanelen → Zonne-opbrengstverwachting*). Forecast.Solar, Solcast, Open-Meteo en andere
   verwachtingsintegraties werken, zonder iets extra in te stellen. Staat daar geen verwachting,
   dan verandert er niets.
2. Hij rekent het verwachte overschot uit: per uur de verwachting, vermenigvuldigd met de
   betrouwbaarheid, min je eigen verbruik in dat uur. Verwachtingen zijn vaak te rooskleurig,
   zeker in de winter. Staat *Betrouwbaarheid leren van de werkelijke opbrengst* aan, dan vergelijkt
   de integratie per dag de verwachting met wat de panelen echt leverden (de opbrengstteller uit het
   Energie-dashboard) en gebruikt de mediaan van de laatste dagen als betrouwbaarheid, zodra er
   minstens 3 dagen zijn. Tot dan, en als leren uit staat, geldt de instelling *Betrouwbaarheid
   zonneverwachting* (standaard 70 %). Je eigen verbruik in dat uur: Met een *Huisverbruiksensor*
   leert de integratie je gemiddelde verbruik per uur van de dag (werkdagen en weekend apart) en
   gebruikt dat, zodat een middag die het huis zelf opmaakt geen overschot oplevert. Zonder de
   sensor geldt het vaste *Verkoop: gemiddeld eigen verbruik*.
3. Hij laadt 's nachts alleen zoveel bij dat er bij zonsopkomst ruimte is voor dat overschot: wat je
   eigen verbruik tot dan opmaakt, plus wat er nog bij moet. Op een zonnige dag is dat een paar kWh
   in plaats van een volle accu, of niets (de planregel zegt dan dat de zon de accu bijvult). Een
   bewolkte dag geeft weinig of geen overschot, en dan wordt de accu vol geladen.

De verwachting wordt elke 30 minuten gelezen. Hij verlaagt alleen de hoeveelheid die wordt
bijgeladen; hij verschuift geen laaduren en verandert niets aan verkopen.

### Vasthouden en geen verlies

Uit het net bijgeladen energie heeft een kostprijs: de laadprijs gedeeld door het rendement. Gaf de
batterij die energie terug in uren die goedkoper zijn dan dat, dan kostte bijladen geld.
**Vasthouden** blokkeert daarom het ontladen zolang er bijgeladen voorraad in de accu zit (zie
[Opbrengst](#opbrengst)) en de uurprijs onder de kostprijs van die voorraad ligt. Het huis gebruikt
dan netstroom, die op dat moment goedkoper is. Zodra de prijs de kostprijs bereikt, of de voorraad
op is, neemt de Marstek het weer over.

Technisch zet de integratie het maximale ontlaadvermogen op 0. De Marstek blijft in anti-feed, dus
laden uit zonne-overschot gaat gewoon door. Zet een andere automation dat vermogen tijdens het
vasthouden op een andere waarde (bijvoorbeeld een begrenzer voor een laadpaal), dan onthoudt de
integratie die waarde en zet hem er daarna terug. De Marstek kan netstroom niet van zonnestroom
onderscheiden, dus tijdens vasthouden wordt de hele accu niet ontladen. Vasthouden vraagt de
entiteit voor het maximale ontlaadvermogen.

**Geen verlies** is een aparte, strengere schakelaar: vasthouden wordt afgedwongen, ook als die
schakelaar uit staat, en er wordt niets onder de kostprijs verkocht. Elke geboekte kWh levert dan
minstens zijn kostprijs op. Wat het niet kan uitsluiten:

- **Stilstand:** blijft de prijs lang onder de kostprijs, dan blijft de accu geblokkeerd, ook voor
  opgeslagen zonnestroom.
- **Afwijkend rendement:** geeft de accu minder terug dan het gemiddelde rendement, dan is hij leeg
  voordat de voorraad in de boeken op is; de rest vervalt zonder een verlies te boeken.
- **Slijtage** telt niet mee, tenzij je een aanschafprijs instelt (zie [Opbrengst](#opbrengst)).

### Verkopen

Verkopen heeft een eigen schakelaar en staat los van bijladen. Er wordt alleen verkocht wat echt
overblijft. Een uur wordt gebruikt om te verkopen als dit allemaal geldt:

1. **Een goedkope lading komt eraan**: er ligt een laadvenster met gepubliceerde prijzen in het
   verschiet, dus de kosten van terugladen zijn bekend.
2. **De opbrengst ligt duidelijk boven terugladen**: verkoopprijs ≥ laadprijs gedeeld door het
   rendement, plus de verkoopmarge (standaard € 0,10 per kWh).
3. **Er is overschot boven de reserve**: de ontlaadgrens van de Marstek plus het verwachte eigen
   verbruik tot het terugladen, met een instelbaar minimum (standaard 20 %).
4. **Het is een van de duurste uren** vóór het laadvenster.

Het verkoopvermogen wordt over de gekozen uren gespreid; bij de reserve stopt het verkopen. In de
winter is er zelden overschot; de optie doet vooral iets als de zon de accu vult en er 's avonds
een prijspiek is. Hij vraagt de entiteit voor het geforceerde ontlaadvermogen.

**Na het einde van de salderingsregeling** (1 januari 2027) levert terugleveren minder op dan de
uurprijs. Stel dan *Verkoopprijs: factor* en *aftrek* in: verkoopprijs = uurprijs × factor −
aftrek. Voor de kale marktprijs bij Zonneplan is dat ongeveer 0,826 en € 0,108.

## Compatibiliteit

De integratie stuurt een Marstek Venus aan via de RS485-besturingsregisters.

| Koppeling | Model | Status |
|---|---|---|
| LilyGO T-CAN485 + ESPHome (RS485) | Venus E v2 | **Getest** op echte hardware (de opzet waarop hij is gebouwd) |
| Modbus-hub in Home Assistant, via RS485-naar-TCP-converter (Elfin EW11 en vergelijkbaar) | Venus E v1/v2 | Alleen getest met nagebootste aanroepen |
| Modbus-hub in Home Assistant, rechtstreeks via Ethernet | Venus E v3 | Alleen getest met nagebootste aanroepen |
| Integratie *Marstek Venus Modbus* (ViperRNMC) | Venus E v3 | Alleen getest met nagebootste aanroepen |
| Een van bovenstaande | Venus A, Venus D, andere modellen | **Niet gecontroleerd, niet getest.** Ze zouden de besturingsregisters delen, maar dat is niet geverifieerd. Stel de accucapaciteit in bij de opties (standaard 5,12 kWh). |
| Cloud, app of andere integraties | alle | Niet ondersteund |

- **LilyGO T-CAN485 met ESPHome** via RS485, met de configuratie van
  [MarstekVenus-LilygoRS485](https://github.com/Superduper1969/MarstekVenus-LilygoRS485). Hij
  gebruikt de entiteiten die deze opzet levert: *RS485 Control Mode*, *Forcible
  Charge/Discharge*, *Forcible Charge Power* (verplicht) en, optioneel, *Max. Charge Power*,
  *Max. Discharge Power*, *Forcible Discharge Power*, *Discharging Cutoff Capacity* en de
  totaaltellers van geladen en ontladen energie.
- **Modbus in Home Assistant**, met een Modbus-hub die je zelf in `configuration.yaml` zet: een
  Elfin EW11 of andere RS485-naar-TCP-converter
  ([MarstekVenus-ElfinEW11](https://github.com/Superduper1969/MarstekVenus-ElfinEW11)), of de
  **Venus E v3 rechtstreeks via Ethernet** (Modbus TCP, poort 502, unit 1, EMS V144 of nieuwer;
  [MarstekVenusV3-modbus-TCP-IP](https://github.com/fonske/MarstekVenusV3-modbus-TCP-IP)). De
  integratie leest de registersensoren van die opzet en schrijft de registers 42000
  (RS485-besturing), 42010 (forceermodus), 42020/42021 (geforceerd laad-/ontlaadvermogen) en, als
  je de sensoren opgeeft, 44002/44003 (maximaal laad-/ontlaadvermogen) met
  `modbus.write_register`. Zonder het maximale ontlaadvermogen zijn *Vasthouden* en *Geen verlies*
  niet beschikbaar. De Venus E v3 heeft de laadtoestand in register 34002 (schaal 0,1), niet in
  32104.
- **De integratie *Marstek Venus Modbus***
  ([ViperRNMC/marstek_venus_modbus](https://github.com/ViperRNMC/marstek_venus_modbus)), die ook
  Modbus TCP spreekt. Kies dit als je die al gebruikt: zij levert de entiteiten (`switch`
  RS485-besturing, `select` forceermodus, `number` vermogens). Zet daar eerst de schakelaar
  *RS485 control mode* en de select *Force mode* aan, ze staan standaard uit.

### Wat de integratie naar de Marstek stuurt

| Moment | Commando's |
|---|---|
| Bijladen starten | laadvermogen zetten → forceermodus `charge` → RS485-besturing `enable` |
| Tijdens het laden | laadvermogen bijstellen (stappen van 100 W) |
| Klaar, of prijssturing uit | RS485-besturing `disable`, forceermodus terug naar `charge`, laadvermogen terug naar het maximum |
| Verkopen starten | ontlaadvermogen zetten → forceermodus `discharge` → RS485-besturing `enable` |
| Verkopen klaar, of verkoop uit | zelfde als klaar: terug naar de rusttoestand |

Zelf gestart geforceerd **ont**laden blijft met rust. Zelf gestart geforceerd laden wordt
teruggezet zolang de prijssturing aan staat; zet die eerst uit als je dat wilt.

## Instellingen

Onder *Configureren* bij de integratie. De opties staan in groepen; de entiteiten staan in een
ingeklapte groep onderaan.

### Prijssensor

De integratie leest de prijzen uit een attribuut van één sensor (standaard `forecast`):

- Zonneplan-uurprijzen: `start_date`, `end_date`, `price_tax_included.amount`
- Zonneplan (oud): `datetime`, `electricity_price`
- Algemeen: `start` (of `start_time`, `datetime`) en `price` (of `value`, `prijs`) in €/kWh

### Opties

| Groep | Instelling | Standaard | Betekenis |
|---|---|---|---|
| | Taal | Automatisch | Taal van planregel, stroomschema en kaarten. |
| Accu | Accucapaciteit | 5,12 kWh | Alleen gebruikt als er geen capaciteitssensor is ingevuld. |
| Accu | Rendement als de tellers ontbreken | 0,77 | Het rendement wordt berekend uit de energietellers van de Marstek (totaal ontladen ÷ totaal geladen, begrensd op 70–95 %). Deze vaste waarde geldt alleen als die tellers ontbreken. Het enkelvoudige rendement is de wortel ervan. |
| Accu | Aanschafprijs accu | € 0 | Voor de afschrijving. 0 zet haar uit. |
| Accu | Levensduur accu (cycli) | 6000 | Afschrijving per kWh = prijs ÷ (cycli × capaciteit); € 1.500 over 6.000 cycli van 5,12 kWh is ongeveer € 0,049 per kWh. |
| Accu | Ontlaadgrens | 12 % | Gebruikt als er geen ontlaadgrens-entiteit is ingesteld. |
| Bijladen | Minimale winst per kWh | € 0,02 | Wat bijladen na aftrek van het laadverlies minstens moet opleveren. Uren die minder dan een halve cent boven de grens liggen tellen ook mee, zodat een bijna vlakke nacht niet om een fractie van een cent wordt versnipperd. |
| Bijladen | Minimaal laadvermogen | 400 W | Ondergrens bij het spreiden. |
| Bijladen | Attribuut met de prijzen | `forecast` | Het attribuut van de prijssensor met de uurprijzen. |
| Bijladen | Aantal duurste uren om mee te vergelijken | 6 | Met hoeveel dure uren later een uur wordt vergeleken. |
| Bijladen | Aantal uren vooruit kijken | 18 | Hoe ver na een uur wordt gezocht naar dure uren. |
| Bijladen | Minimaal aantal bekende uren vooruit | 8 | Uren met minder bekende prijzen erna worden genegeerd. |
| Negatieve prijs | Negatieve prijs: grens | € 0,00 | Onder deze uurprijs laadt de accu. |
| Negatieve prijs | Negatieve prijs: verdeling van de energie | Naar waarde | Naar waarde (lager vermogen) of maximale opbrengst (beste uren eerst). |
| Zon | Zonneverwachting gebruiken | Aan | Houd bij het bijladen 's nachts rekening met de verwachte zonne-opbrengst uit het Energie-dashboard. |
| Zon | Betrouwbaarheid leren van de werkelijke opbrengst | Aan | Vergelijk per dag de zonneverwachting met wat de panelen echt leverden en gebruik de mediaan van de laatste dagen als betrouwbaarheid (vanaf 3 dagen). |
| Zon | Betrouwbaarheid zonneverwachting | 70 % | Het deel van de verwachting waarop je rekent. Lager is voorzichtiger. |
| Zon | Huisverbruiksensor | geen | Optionele sensor met het vermogen dat het hele huis verbruikt (W of kW), zonder de accu. Een laadpaal vertekent het gemiddelde, laat die er dus zo mogelijk buiten. |
| Verkoop | Verkoop: minimale winst per kWh | € 0,10 | Wat verkopen na terugladen minstens moet opleveren. |
| Verkoop | Verkoop: gemiddeld eigen verbruik | 400 W | Bepaalt de reserve tot het terugladen, en is het vaste eigen verbruik voor het zonne-overschot. |
| Verkoop | Verkoop: minimale reserve | 20 % | Onder deze SoC wordt niets verkocht. |
| Verkoop | Verkoopprijs: factor en aftrek | 1 en € 0 | Verkoopprijs = uurprijs × factor − aftrek. |

Het maximale laadvermogen (*Max. Charge power* van de Marstek) bepaalt het aantal laaduren. Zet
je dat lager, dan plant hij meer uren en laadt hij rustiger.

## Dashboardkaarten

De integratie levert zeven kaarten mee; er hoeft geen resource te worden toegevoegd. Ververs de
browser na het installeren of bijwerken. Elke kaart is in te stellen in de kaarteditor en in YAML,
en laat je `entity` weg dan wordt de laadplan-sensor zelf gevonden.

| Kaart | Inhoud |
|---|---|
| `custom:marstek-goedkoop-laden-card` | Stroomschema: de tijdlijn van vandaag en per onderdeel (bijladen, verkoop, negatieve prijs, vasthouden) welke controles slagen en op welke het stopt. |
| `custom:marstek-goedkoop-laden-compact-card` | Hetzelfde in een paar regels: de tijdlijn, per onderdeel de uitkomst met de reden, en één regel met de opbrengst. |
| `custom:marstek-goedkoop-laden-opbrengst-card` | Alleen de opbrengst: vandaag, deze week, vorige week, deze maand, dit jaar en de verwachting van het huidige plan. |
| `custom:marstek-goedkoop-laden-schakelaars-card` | Compact: knoppen om de modi aan of uit te zetten. |
| `custom:marstek-goedkoop-laden-status-card` | Wat er nu gebeurt, de laadtoestand als balk, de prijs nu en de volgende stap. |
| `custom:marstek-goedkoop-laden-prijzen-card` | Prijsgrafiek zonder extra kaarten: de uren met bijladen, verkoop en negatieve prijzen gemarkeerd, en een lijn voor nu. |
| `custom:marstek-goedkoop-laden-voorraad-card` | De bijgeladen voorraad, de kostprijs, het rendement, de afschrijving per kWh en de capaciteit. |

```yaml
type: custom:marstek-goedkoop-laden-opbrengst-card
entity: sensor.marstek_goedkoop_laden_laadplan   # optioneel
title: Opbrengst                                 # optioneel
tiles: [vandaag, maand, jaar]                    # welke tegels, in deze volgorde
notes: false                                     # verberg de toelichting onder de kaart
```

| Kaart | Optie | Standaard | Betekenis |
|---|---|---|---|
| alle | `entity`, `title` | automatisch gevonden, geen | De laadplan-sensor en een titel. |
| stroomschema, compact | `show_timeline` | `true` | De tijdlijn van vandaag tonen. |
| stroomschema, compact | `opbrengst` | uit, één regel | Ook de opbrengst tonen. |
| stroomschema, compact, schakelaars | `lanes` | alle vijf | Welke onderdelen: `bijladen`, `verkoop`, `negatief`, `vasthouden`, `geen_verlies`. |
| opbrengst | `tiles` | alle zes | Kies uit `vandaag`, `week`, `vorige_week`, `maand`, `jaar`, `verwacht`, in deze volgorde. |
| opbrengst | `expected_details`, `notes` | `true` | De regels per onderdeel van het plan; de toelichting met voorraad, wat er vandaag is bijgeladen en de afschrijving. |
| status | `show_soc`, `show_price`, `show_next` | `true` | De laadtoestandbalk, de prijs nu, de volgende stap. |
| prijzen | `hours_back`, `hours_ahead` | `2`, `0` | Aantal uren terug; aantal uren vooruit (0 is tot de laatste bekende prijs). |
| prijzen | `show_values`, `height` | `false`, `140` | De prijs boven elke staaf tonen (tot 24 staven); hoogte in pixels. |
| voorraad | `tiles`, `notes` | alle vijf, `true` | `voorraad`, `kostprijs`, `rendement`, `afschrijving`, `capaciteit`; de toelichting onder de kaart. |

In het stroomschema is groen een geslaagde controle, rood de controle waarop het stopt en
gestreept een uitkomst waarbij niets gebeurt. Planregel in een Markdown-kaart:

```yaml
type: markdown
content: >-
  **Laadplan:** {{ state_attr('sensor.marstek_goedkoop_laden_laadplan', 'tekst') }}
  {% if is_state('switch.marstek_goedkoop_laden_prijssturing', 'off') %}
  · ⚠️ prijssturing staat **uit**{% endif %}
```

## Opbrengst

Er zijn twee soorten opbrengst: wat het huidige plan naar verwachting oplevert, en wat er echt is
verdiend.

**Verwacht (schatting vooraf).** Bijladen: wat de in te kopen energie kost, tegenover wat ze later
waard is (het rendement maal de gemiddelde prijs van de dure uren waarmee het laaduur is
vergeleken). Verkopen: de opbrengst van het overschot, min wat terugladen kost. Tijdens een
lading telt alleen wat nog moet worden bijgeladen.

**Gerealiseerd (vandaag, week, maand, jaar).**

1. Energie die de integratie uit het net laadt (laadplan of negatieve prijs) wordt **voorraad**:
   bruikbare kWh = geladen kWh × rendement, met als kostprijs wat die energie op dat moment kostte.
2. Ontlaadt de batterij daarna voor eigen verbruik, dan wordt die voorraad eerst gebruikt. De
   winst is `ontladen kWh × (stroomprijs op dat moment − kostprijs per bruikbare kWh)`.
3. Bij verkopen is de winst `verkochte kWh × verkoopprijs − kostprijs`; voor energie die niet uit
   de voorraad komt (zonne-energie) is de kostprijs wat terugladen kost.
4. **Vandaag** telt vanaf 00:00, **deze week** vanaf maandag 00:00, **deze maand** vanaf de eerste
   en **dit jaar** vanaf 1 januari. **Vorige week** is het eindbedrag van de week ervoor.

Wat nog in de voorraad zit, is nog niet verdiend en telt pas mee als het wordt gebruikt. Energie
die de zon in de accu stopt en die je later zelf gebruikt, telt niet mee: dat doet de Marstek ook
zonder deze integratie. De bedragen komen uit de energietellers van de Marstek en de uurprijs op
dat moment; een tellersprong na een storing wordt niet geboekt.

**Afschrijving.** Stel je een aanschafprijs in, dan kost elke kWh die de accu ontlaadt een beetje
slijtage: prijs ÷ (cycli × capaciteit). Dat gaat af van de gerealiseerde opbrengst, telt mee in de
verwachte opbrengst en in de beslissingen: een uur is alleen laadwaardig als het ook na de
slijtage nog wint, verkopen vraagt de slijtage bovenop de verkoopmarge, en *Vasthouden* en *Geen
verlies* nemen kostprijs plus slijtage als break-evenprijs. Bij een prijs van 0 (standaard)
verandert er niets.

## Entiteiten

| Entiteit | Inhoud |
|---|---|
| `switch.*_prijssturing` | Aan: het laadplan wordt uitgevoerd. Uit: de Marstek regelt alles zelf. |
| `switch.*_laden_bij_negatieve_prijs` | Aan (standaard): laden als de uurprijs negatief is. |
| `switch.*_vasthouden` | Aan (standaard): niet ontladen onder de kostprijs van de voorraad. |
| `switch.*_geen_verlies` | Aan: vasthouden afgedwongen en nooit verkopen onder de kostprijs. |
| `switch.*_verkoop` | Aan: overschot wordt in de duurste uren verkocht. Staat los van de prijssturing. |
| `sensor.*_laadplan` | Status: `laden`, `gepland`, `klaar`, `vol`, `geen` of `onbekend`. Attributen: `tekst` (leesbare samenvatting), `laaduren`, `venster`, `stroomschema` (tijdlijn, controles, prijzen en overzicht voor de kaarten) en meer. |
| `sensor.*_verkoopplan` | Status: `verkopen`, `gepland`, `geen` of `onbekend`. Attributen: `verkoopuren`, `overschot_kwh`, `reserve_soc`, `tekst` en meer. |
| `sensor.*_gepland_laadvermogen`, `*_bij_te_laden`, `*_start_bijladen`, `*_einde_bijladen`, `*_gemiddelde_laadprijs` | Het gespreide laadvermogen in W, de nog te laden energie in kWh, begin en einde van de geplande lading en de gemiddelde prijs in €/kWh. |
| `sensor.*_opbrengst_vandaag`, `*_opbrengst_deze_week`, `*_opbrengst_vorige_week`, `*_opbrengst_deze_maand`, `*_opbrengst_dit_jaar` | Gerealiseerde opbrengst in euro (zie [Opbrengst](#opbrengst)). |
| `sensor.*_verwachte_opbrengst` | Geschatte opbrengst van de huidige plannen in euro; attribuut `regels` bevat de uitsplitsing. |
| `sensor.*_rendement` | Het gebruikte rendement in procent. Attribuut `bron`: gemeten of vast. |

Entiteitsnamen volgen de taal van Home Assistant op het moment dat de entiteit wordt aangemaakt
(bij een Engelse installatie heten ze `*_charge_plan`, `*_price_control` enzovoort). **Statuswaarden
en attribuutnamen zijn in elke taal Nederlands** (`laden`, `tekst`, …); ze staan vast zodat
automations blijven werken.

## Ontwikkelen

De rekenregel staat los van Home Assistant in `planner.py` en heeft tests met echte prijzen. De
sturing wordt getest tegen een nagebootst Home Assistant:

```bash
python3 -m unittest discover -s tests -v
```

## Wijzigingen

Zie [CHANGELOG.md](CHANGELOG.md), met de breaking changes.

## Dankwoord

Deze integratie staat op het werk van de Marstek Venus-community:

- Het [Tweakers-forumtopic](https://gathering.tweakers.net/forum/list_messages/2282240/0) waar dit werk uit de community wordt besproken, een eervolle vermelding voor iedereen daar die bevindingen en configuraties deelt.
- [Superduper1969](https://github.com/Superduper1969) voor de configuraties voor de LilyGO RS485 en Elfin EW11 waaromheen deze integratie is gebouwd, en scruysberghs, die in die configuraties wordt bedankt.
- [fonske](https://github.com/fonske) voor de Modbus TCP-configuratie van de Venus E v3.
- [ViperRNMC](https://github.com/ViperRNMC) voor de integratie Marstek Venus Modbus.

## Licentie

Apache 2.0, zie [LICENSE](LICENSE).
