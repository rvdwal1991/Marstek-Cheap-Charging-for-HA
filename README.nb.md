<img src="custom_components/marstek_goedkoop_laden/brand/icon.png" width="96" align="right" alt="">

# Marstek Billig Lading for Home Assistant

[🇬🇧 English](README.md) · [🇳🇱 Nederlands](README.nl.md) · [🏳️ Frysk](README.fy.md) · [🇩🇪 Deutsch](README.de.md) · [🇫🇷 Français](README.fr.md) · [🇪🇸 Español](README.es.md) · [🇸🇪 Svenska](README.sv.md) · 🇳🇴 Norsk

[![Open your Home Assistant instance and open this repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=rvdwal1991&repository=Marstek-Cheap-Charging-for-HA&category=integration)
[![Open your Home Assistant instance and start setting up the integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=marstek_goedkoop_laden)

Lader opp et Marstek Venus-hjemmebatteri fra nettet i de billigste timene av en dynamisk
strømavtale, slik at det er fullt før prisene går opp.

Utgangspunktet er **selvforsyning**: batteriet fortsetter å regulere seg selv (anti-feed, null
på måleren). Denne integrasjonen legger til én ting, lading fra nettet i de billigste timene,
pluss noen valgfrie tillegg rundt det.

**Du trenger:**

- en **dynamisk strømavtale** med timepriser. Med fast pris er det ingenting å tjene. Den er
  bygget rundt det nederlandske markedet og Zonneplan (prisene for neste dag kommer
  mellom 13:00 og 15:00), men enhver sensor med en timeprisliste fungerer, se
  [Prissensor](#prissensor);
- et Marstek Venus som Home Assistant kan styre over RS485 eller Modbus, se
  [Kompatibilitet](#kompatibilitet). **Bare oppsettet med LilyGO RS485 + ESPHome er testet på et
  ekte batteri.**
- Home Assistant 2026.3 eller nyere.

## Hva den gjør

| Modus | Standard | Hva den gjør |
|---|---|---|
| **Prisstyring** | av | Lader fra nettet i de billigste timene og fordeler effekten over dem. |
| **Lad ved negativ pris** | på | Lader når timeprisen er negativ, og henter ut mest mulig av vinduet. |
| **Solprognose** | på | Lader mindre om natten når solen fyller batteriet i løpet av dagen. Krever en solprognose i Energi-dashbordet. |
| **Tilbakehold under kostpris** | på | Utlader ikke så lenge nettet er billigere enn det den ladede beholdningen kostet. |
| **Ingen tap** | av | Streng versjon av tilbakehold: selger heller aldri ladet beholdning under kostpris. |
| **Salg** | av | Selger overskudd i de dyreste timene. |

Hver modus har sin egen bryter. **Prisstyring er av etter installasjon**: sett opp integrasjonen,
kontroller at planteksten på ladeplan-sensoren ser riktig ut, og slå den deretter på.

## Hurtigstart

1. Installer med HACS (knappen over, eller legg til dette depotet som egendefinert depot, kategori
   *Integration*), eller kopier `custom_components/marstek_goedkoop_laden` til
   `/config/custom_components/`. Start Home Assistant på nytt.
2. *Innstillinger → Enheter og tjenester → Legg til integrasjon → Marstek Goedkoop Laden*.
3. Velg hvordan Marstek er koblet til, deretter prissensoren og Marstek-entitetene.
   Det som oppdages, er ferdig utfylt. For Modbus oppgir du også navnet på Modbus-huben din (for
   eksempel `MarstekVenus`) og slaveadressen.
4. Slå på bryteren **Prisstyring** når planen ser riktig ut.
5. Legg til kort: *Rediger dashbord → Legg til kort → søk etter «Marstek»*, se [Dashbordkort](#dashbordkort).

Tekstene (planlinje, flytskjema, kort) følger valget *Språk*: Automatisk, Nederlands,
English, Frysk, Deutsch, Français, Español, Svenska eller Norsk. Automatisk følger Home Assistant
når det er ett av disse, ellers engelsk.

## Slik fungerer ladeplanen

1. **Er lading lønnsomt?** En time er billig nok hvis prisen er lavere enn
   `virkningsgrad × (gjennomsnittet av de 6 dyreste timene de neste 18 timene) − margin`. Virkningsgraden
   (tur-retur ved lading og utlading, rundt 77 % målt her) kommer fra
   energitellerne til Marstek.
2. **Vindu.** Den første blokken med billige timer er ladevinduet. Én eller to timer som
   ikke er helt billige nok bryter ikke blokken; lading skjer bare i de billige timene
   selv.
3. **Ladetimer.** Innenfor vinduet velger den de billigste timene, akkurat så mange som trengs
   for å komme fra gjeldende SoC til 100 %. Er vinduet for kort til å fylle batteriet, planlegger den
   bare det som får plass og sier fra om det i planteksten.
4. **Fordel effekten.** Ladeeffekten er energien som ennå skal tilføres delt på tiden som er igjen
   i ladetimene. Det holder belastningen på nettilkoblingen lav. Effekten justeres
   underveis.
5. **Ferdig er ferdig.** Når ladetimene er over eller batteriet er fullt, går Marstek
   tilbake til anti-feed. Den starter ikke igjen i samme vindu.

Bare **publiserte** priser brukes, så planen for natten dukker opp så snart morgendagens
priser er kjent. Eksempel (10. november 2026, batteri på 12 %): billig vindu 23:00–07:00,
lading kl. 02:00, 03:00 og 04:00 med omtrent 1900 W til gjennomsnittlig € 0,37, mot € 0,55–0,67
på dagtid.

### Lading ved negativ pris

Hvis timeprisen er negativ, lader batteriet, uavhengig av ladeplanen og selv
når prisstyringen er av. Den ser på hele **vinduet** med sammenhengende negative timer:

1. Den regner ut hvor mye batteriet fortsatt kan ta imot (SoC til 100 %).
2. Den fordeler energien over timene **etter verdi**: jo mer negativ prisen er, desto
   mer lades i den timen, opp til det en time tåler ved maksimal effekt. Eksempel:
   −€ 0,03, −€ 0,20 og −€ 0,12 med 3 kWh å lade gir omtrent 1,9 kWh i timen på −€ 0,20 og
   1,2 kWh i timen på −€ 0,12. Timen på −€ 0,03 ville ligge under minste ladeeffekt, så den
   faller bort og andelen går til de to andre.
3. Fordelingen holder effekten lavere enn et kort støt med full effekt. En enkelt time som ikke kan
   fylle batteriet, lades med full effekt.

Valget *Negativ pris: hvordan energien fordeles* kan settes til **Maksimal gevinst**: den beste
timen fylles først med full effekt, deretter den neste. I eksemplet gir det omtrent € 0,55
i stedet for € 0,52, til prisen av flere støt med full effekt. Planen beregnes på nytt hvert
minutt, og en time som allerede er i bruk får litt ekstra slingringsmonn før den faller bort.

### Solprognose

Med solceller fylles batteriet gratis om dagen. Hvis du lader det fullt fra
nettet om natten, har overskuddet ingen plass igjen og går til nettet for lite eller ingenting, noe som
betyr mer nå som nettmålingsordningen (*salderingsregeling*) avsluttes. Derfor ser integrasjonen på
forventet solproduksjon:

1. Den leser prognosen fra **Energi-dashbordet** (*Innstillinger → Dashbord → Energi → Solcellepaneler →
   Prognose for solproduksjon*). Forecast.Solar, Solcast, Open-Meteo og andre prognoseintegrasjoner
   fungerer, uten at noe ekstra må settes opp. Uten en prognose der endrer ingenting seg.
2. Den regner ut forventet overskudd: per time prognosen, multiplisert med påliteligheten,
   minus ditt eget forbruk i den timen. Prognoser er ofte for rosenrøde, særlig om vinteren.
   Med *Lær påliteligheten fra faktisk produksjon* på sammenligner integrasjonen hver dags
   prognose med det panelene faktisk produserte (produksjonstelleren fra Energi-dashbordet)
   og bruker medianen av de siste dagene som pålitelighet, så snart den har minst 3 dager.
   Fram til da, og når læring er av, gjelder innstillingen *Pålitelighet for solprognosen*
   (standard 70 %). Ditt eget forbruk i den timen: med en *Husforbruk-sensor*
   lærer integrasjonen ditt gjennomsnittlige forbruk per time på døgnet (hverdager og helger
   hver for seg) og bruker det, slik at en middag som huset selv spiser opp ikke gir noe overskudd.
   Uten sensoren brukes det faste *Salg: gjennomsnittlig eget forbruk*.
3. Den lader om natten bare så mye at det er plass til dette overskuddet når solen står opp:
   det som ditt eget forbruk bruker fram til da, pluss det som fortsatt trengs. På en solrik dag kan det
   være noen få kWh i stedet for et fullt batteri, eller ingenting (planteksten sier da at solen
   fyller batteriet). En skyet dag gir lite eller ikke noe overskudd, og batteriet lades fullt.

Prognosen leses hvert 30. minutt. Den reduserer bare mengden som skal lades; den flytter
ikke ladetimer og endrer ikke salg.

### Tilbakehold og ingen tap

Strøm som er ladet fra nettet har en kostpris: ladeprisen delt på virkningsgraden. Hvis
batteriet ga den energien tilbake i timer som er billigere enn det, ville lading koste penger.
**Tilbakehold** blokkerer derfor utlading så lenge det finnes ladet beholdning i batteriet (se
[Gevinst](#gevinst)) og timeprisen er under kostprisen på den beholdningen. Huset bruker da nettstrøm,
som i øyeblikket er billigere. Så snart prisen når kostprisen, eller beholdningen er brukt opp,
tar Marstek over igjen.

Teknisk sett setter integrasjonen maksimal utladeeffekt til 0. Marstek blir stående i
anti-feed, så lading fra solcelleoverskudd fortsetter. Hvis en annen automasjon setter denne effekten
under tilbakeholdet (for eksempel en begrenser for en elbillader), husker integrasjonen den verdien
og gjenoppretter den etterpå. Marstek kan ikke skille nettstrøm fra solenergi, så under et
tilbakehold utlades ikke hele batteriet. Tilbakehold krever entiteten for maksimal utladeeffekt.

**Ingen tap** er en egen, strengere bryter: tilbakehold håndheves selv om bryteren Tilbakehold er av,
og ingenting selges under kostprisen. Hver bokførte kWh gir da minst kostprisen. Det den
ikke kan utelukke:

- **Stillstand:** hvis prisen blir under kostprisen i lang tid, forblir batteriet
  blokkert, også for lagret solenergi.
- **Avvikende virkningsgrad:** gir batteriet mindre tilbake enn gjennomsnittlig virkningsgrad, er det tomt
  før beholdningen i bøkene er brukt opp; resten forfaller uten at det bokføres tap.
- **Slitasje** regnes ikke med med mindre du setter en kjøpspris (se [Gevinst](#gevinst)).

### Salg

Salg har sin egen bryter og er uavhengig av lading. Bare det som virkelig er til overs
selges. En time brukes til salg når alt dette stemmer:

1. **En billig lading er på vei**: et ladevindu med publiserte priser ligger foran, så kostnaden
   ved å lade opp igjen er kjent.
2. **Inntekten er tydelig høyere enn ved å lade opp igjen**: salgspris ≥ ladepris delt på
   virkningsgraden, pluss salgsmarginen (standard € 0,10 per kWh).
3. **Det finnes overskudd over reserven**: utladegrensen til Marstek pluss forventet eget
   forbruk fram til gjenlading, med et justerbart minimum (standard 20 %).
4. **Det er en av de dyreste timene** før ladevinduet.

Salgseffekten fordeles over de valgte timene; ved reserven stopper salget. Om vinteren er det sjelden
overskudd; valget gjør mest når solen fyller batteriet og det er en pristopp om
kvelden. Det krever entiteten for tvungen utladeeffekt.

**Etter at nettmålingsordningen avsluttes** (den nederlandske *salderingsregeling*, 1. januar 2027) gir
innmating mindre enn timeprisen. Sett da *Salgspris: faktor* og *fradrag*: salgspris =
timepris × faktor − fradrag. For den rene markedsprisen hos Zonneplan er det omtrent 0,826
og € 0,108.

## Kompatibilitet

Integrasjonen styrer et Marstek Venus via RS485-kontrollregistrene.

| Tilkobling | Modell | Status |
|---|---|---|
| LilyGO T-CAN485 + ESPHome (RS485) | Venus E v2 | **Testet** på ekte maskinvare (oppsettet den er bygget på) |
| Modbus-hub i Home Assistant, via RS485-til-TCP-omformer (Elfin EW11 og lignende) | Venus E v1/v2 | Bare testet med simulerte kall |
| Modbus-hub i Home Assistant, direkte over Ethernet | Venus E v3 | Bare testet med simulerte kall |
| Integrasjonen *Marstek Venus Modbus* (ViperRNMC) | Venus E v3 | Bare testet med simulerte kall |
| Hvilken som helst av de over | Venus A, Venus D, andre modeller | **Ikke kontrollert, ikke testet.** De skal visstnok dele kontrollregistrene, men det er ikke bekreftet. Sett batterikapasiteten i innstillingene (standard 5,12 kWh). |
| Sky, app eller andre integrasjoner | alle | Støttes ikke |

- **LilyGO T-CAN485 med ESPHome** over RS485, med konfigurasjonen
  [MarstekVenus-LilygoRS485](https://github.com/Superduper1969/MarstekVenus-LilygoRS485).
  Den bruker entitetene dette oppsettet tilbyr: *RS485 Control Mode*, *Forcible
  Charge/Discharge*, *Forcible Charge Power* (påkrevd) og eventuelt *Max. Charge Power*,
  *Max. Discharge Power*, *Forcible Discharge Power*, *Discharging Cutoff Capacity* og tellerne for
  total ladet/utladet energi.
- **Modbus i Home Assistant**, med en Modbus-hub du selv definerer i
  `configuration.yaml`: en Elfin EW11 eller en annen RS485-til-TCP-omformer
  ([MarstekVenus-ElfinEW11](https://github.com/Superduper1969/MarstekVenus-ElfinEW11)), eller
  **Venus E v3 rett over Ethernet** (Modbus TCP, port 502, unit 1, EMS V144 eller nyere;
  [MarstekVenusV3-modbus-TCP-IP](https://github.com/fonske/MarstekVenusV3-modbus-TCP-IP)).
  Integrasjonen leser registersensorene i det oppsettet og skriver registrene 42000 (RS485-styring),
  42010 (tvangsmodus), 42020/42021 (tvungen lade-/utladeeffekt) og, hvis du oppgir sensorene,
  44002/44003 (maksimal lade-/utladeeffekt) med `modbus.write_register`. Uten maksimal
  utladeeffekt er *Tilbakehold* og *Ingen tap* ikke tilgjengelige. Venus E v3 har ladenivået (SoC)
  i register 34002 (skala 0,1), ikke i 32104.
- **Integrasjonen *Marstek Venus Modbus***
  ([ViperRNMC/marstek_venus_modbus](https://github.com/ViperRNMC/marstek_venus_modbus)), som
  også snakker Modbus TCP. Velg denne hvis du allerede bruker den: den leverer entitetene (`switch`
  for RS485-styring, `select` for tvangsmodus, `number` for effektene). Slå først på bryteren
  *RS485 control mode* og velgeren *Force mode* der, de er avslått som standard.

### Hva integrasjonen sender til Marstek

| Tidspunkt | Kommandoer |
|---|---|
| Start lading | sett ladeeffekt → tvangsmodus `charge` → RS485-styring `enable` |
| Under lading | juster ladeeffekt (trinn på 100 W) |
| Ferdig, eller prisstyring av | RS485-styring `disable`, tvangsmodus tilbake til `charge`, ladeeffekt tilbake til maksimum |
| Start salg | sett utladeeffekt → tvangsmodus `discharge` → RS485-styring `enable` |
| Salg ferdig, eller salg av | som ferdig: tilbake til hviletilstanden |

Tvungen **ut**lading du starter selv, blir latt i fred. Tvungen lading du starter
selv, tilbakestilles så lenge prisstyringen er på; slå den av først hvis du vil det.

## Innstillinger

Under *Konfigurer* på integrasjonen. Valgene er delt i grupper; entitetene ligger i en
sammenfoldet gruppe nederst.

### Prissensor

Integrasjonen leser prisene fra et attributt på én sensor (standard `forecast`):

- Zonneplan-timepriser: `start_date`, `end_date`, `price_tax_included.amount`
- Zonneplan (gammel): `datetime`, `electricity_price`
- Generisk: `start` (eller `start_time`, `datetime`) og `price` (eller `value`, `prijs`) i €/kWh

### Valg

| Gruppe | Innstilling | Standard | Betydning |
|---|---|---|---|
| | Språk | Automatisk | Språk for plantekst, flytskjema og kort. |
| Batteri | Batterikapasitet | 5,12 kWh | Brukes bare når ingen kapasitetssensor er satt. |
| Batteri | Virkningsgrad når tellerne mangler | 0,77 | Virkningsgraden beregnes ut fra energitellerne til Marstek (total utladet ÷ total ladet, begrenset til 70–95 %). Denne faste verdien gjelder bare når tellerne mangler. Virkningsgraden én vei er kvadratroten av den. |
| Batteri | Kjøpspris for batteriet | € 0 | Brukes til avskrivning. 0 slår den av. |
| Batteri | Batteriets levetid (sykluser) | 6000 | Avskrivning per kWh = pris ÷ (sykluser × kapasitet); € 1500 over 6000 sykluser på 5,12 kWh er omtrent € 0,049 per kWh. |
| Batteri | Utladegrense | 12 % | Brukes når ingen entitet for utladegrense er satt. |
| Lading | Minste gevinst per kWh | € 0,02 | Hva lading minst må gi, etter ladetap. Timer som ligger mindre enn en halv cent over grensen teller likevel med, så en nesten flat natt ikke deles opp for en brøkdel av en cent. |
| Lading | Minste ladeeffekt | 400 W | Nedre grense ved fordeling. |
| Lading | Attributt med prisene | `forecast` | Attributtet på prissensoren som inneholder timeprisene. |
| Lading | Antall dyreste timer å sammenligne med | 6 | Hvor mange dyre timer senere en time sammenlignes med. |
| Lading | Timer å se fremover | 18 | Hvor langt etter en time det letes etter dyre timer. |
| Lading | Minste antall kjente timer fremover | 8 | Timer med færre kjente priser etter seg blir ignorert. |
| Negativ pris | Negativ pris: grense | € 0,00 | Under denne timeprisen lader batteriet. |
| Negativ pris | Negativ pris: hvordan energien fordeles | Etter verdi | Etter verdi (lavere effekt) eller maksimal gevinst (beste timer først). |
| Sol | Bruk solprognosen | På | Ta hensyn til forventet solproduksjon fra Energi-dashbordet ved lading om natten. |
| Sol | Lær påliteligheten fra faktisk produksjon | På | Sammenlign hver dags solprognose med det panelene faktisk produserte og bruk medianen av de siste dagene som pålitelighet (fra 3 dager). |
| Sol | Pålitelighet for solprognosen | 70 % | Den delen av prognosen det skal regnes med. Lavere er mer forsiktig. |
| Sol | Husforbruk-sensor | ingen | Valgfri sensor med effekten hele huset bruker (W eller kW), uten batteriet. En billader skjever gjennomsnittet, så utelat den hvis du kan. |
| Salg | Salg: minste gevinst per kWh | € 0,10 | Hva salg minst må gi etter gjenlading. |
| Salg | Salg: gjennomsnittlig eget forbruk | 400 W | Bestemmer reserven fram til gjenlading, og er det faste egne forbruket for solcelleoverskuddet. |
| Salg | Salg: minste reserve | 20 % | Under dette SoC-nivået selges ingenting. |
| Salg | Salgspris: faktor og fradrag | 1 og € 0 | Salgspris = timepris × faktor − fradrag. |

Maksimal ladeeffekt (*Max. Charge power* hos Marstek) bestemmer antall ladetimer.
Sett den lavere, så planlegger den flere timer og lader roligere.

## Dashbordkort

Integrasjonen leverer sju kort; ingen ressurs trenger å legges til. Last nettleseren på nytt
etter installasjon eller oppdatering. Hvert kort kan settes opp i kortredigereren så vel som i YAML, og når
du utelater `entity`, finnes ladeplan-sensoren automatisk.

| Kort | Innhold |
|---|---|
| `custom:marstek-goedkoop-laden-card` | Flytskjema: dagens tidslinje og, per del (lading, salg, negativ pris, tilbakehold), hvilke kontroller som består og hvor det stopper. |
| `custom:marstek-goedkoop-laden-compact-card` | Det samme i noen få linjer: tidslinjen, utfallet per del med begrunnelse, og én linje med gevinsten. |
| `custom:marstek-goedkoop-laden-opbrengst-card` | Bare gevinst: i dag, denne uken, forrige uke, denne måneden, i år og forventningen for gjeldende plan. |
| `custom:marstek-goedkoop-laden-schakelaars-card` | Kompakt: knapper for å slå modusene av eller på. |
| `custom:marstek-goedkoop-laden-status-card` | Hva som skjer nå, ladenivået som en søyle, prisen nå og neste trinn. |
| `custom:marstek-goedkoop-laden-prijzen-card` | Prisdiagram uten ekstra kort: timene med lading, salg og negative priser markert, og en linje for nå. |
| `custom:marstek-goedkoop-laden-voorraad-card` | Den ladede beholdningen, kostprisen, virkningsgraden, avskrivningen per kWh og kapasiteten. |

```yaml
type: custom:marstek-goedkoop-laden-opbrengst-card
entity: sensor.marstek_goedkoop_laden_laadplan   # valgfritt
title: Gevinst                                   # valgfritt
tiles: [vandaag, maand, jaar]                    # hvilke fliser, i denne rekkefølgen
notes: false                                     # skjul merknaden under kortet
```

| Kort | Valg | Standard | Betydning |
|---|---|---|---|
| alle | `entity`, `title` | finnes automatisk, ingen | Ladeplan-sensoren og en tittel. |
| flyt, kompakt | `show_timeline` | `true` | Vis dagens tidslinje. |
| flyt, kompakt | `opbrengst` | av, én linje | Vis også gevinsten. |
| flyt, kompakt, brytere | `lanes` | alle fem | Hvilke deler som vises: `bijladen`, `verkoop`, `negatief`, `vasthouden`, `geen_verlies`. |
| gevinst | `tiles` | alle seks | Hvilke som helst av `vandaag`, `week`, `vorige_week`, `maand`, `jaar`, `verwacht`, i denne rekkefølgen. |
| gevinst | `expected_details`, `notes` | `true` | Linjene per del av planen; merknaden med beholdning, dagens lading og avskrivning. |
| status | `show_soc`, `show_price`, `show_next` | `true` | Ladenivå-søylen, prisen nå, neste trinn. |
| priser | `hours_back`, `hours_ahead` | `2`, `0` | Timer av fortiden; timer fremover (0 er til siste kjente pris). |
| priser | `show_values`, `height` | `false`, `140` | Skriv prisen over hver søyle (opptil 24 søyler); høyde i piksler. |
| beholdning | `tiles`, `notes` | alle fem, `true` | `voorraad`, `kostprijs`, `rendement`, `afschrijving`, `capaciteit`; merknaden under kortet. |

I flytskjemaet er grønt en kontroll som består, rødt er kontrollen der det stopper, og stiplet er et
utfall der ingenting skjer. Planlinje i et Markdown-kort:

```yaml
type: markdown
content: >-
  **Ladeplan:** {{ state_attr('sensor.marstek_goedkoop_laden_laadplan', 'tekst') }}
  {% if is_state('switch.marstek_goedkoop_laden_prijssturing', 'off') %}
  · ⚠️ prisstyringen er **av**{% endif %}
```

## Gevinst

Det finnes to slags gevinst: hva gjeldende plan forventes å tjene, og det som faktisk
er tjent.

**Forventet (anslag på forhånd).** Lading: hva energien som skal kjøpes koster, mot hva den er
verdt senere (virkningsgraden ganger gjennomsnittsprisen for de dyre timene ladetimen ble
sammenlignet med). Salg: inntekten fra overskuddet, minus hva gjenlading koster. Under en
lading teller bare det som fortsatt skal lades.

**Realisert (i dag, uke, måned, år).**

1. Energi integrasjonen lader fra nettet (ladeplan eller negativ pris) blir til
   **beholdning**: brukbare kWh = ladede kWh × virkningsgrad, med som kostpris det den energien kostet
   i øyeblikket.
2. Hvis batteriet deretter utlades til eget forbruk, brukes den beholdningen først. Gevinsten er
   `utladede kWh × (strømpris i øyeblikket − kostpris per brukbare kWh)`.
3. Ved salg er gevinsten `solgte kWh × salgspris − kostpris`; for energi som ikke kommer
   fra beholdningen (solenergi) er kostprisen det gjenlading koster.
4. **I dag** teller siden 00:00, **denne uken** siden mandag 00:00, **denne måneden** siden den første
   og **i år** siden 1. januar. **Forrige uke** er sluttbeløpet for uken før.

Det som fortsatt ligger i beholdningen er ikke tjent ennå og teller først når det brukes. Energi som
solen legger i batteriet og som du bruker selv senere, teller ikke: Marstek gjør det også
uten denne integrasjonen. Beløpene kommer fra energitellerne til Marstek og timeprisen
i øyeblikket; et hopp i telleren etter en feil bokføres ikke.

**Avskrivning.** Hvis du setter en kjøpspris, koster hver kWh batteriet utlader litt
slitasje: pris ÷ (sykluser × kapasitet). Det trekkes fra den realiserte gevinsten, regnes med i den
forventede gevinsten og brukes i beslutningene: en time er bare verdt å lade hvis den fortsatt slår
slitasjen, salg trenger slitasjen oppå salgsmarginen, og *Tilbakehold* og *Ingen tap* behandler kostpris
pluss slitasje som break-even-pris. Med pris 0 (standard) endrer ingenting seg.

## Entiteter

| Entitet | Innhold |
|---|---|
| `switch.*_prisstyring` | På: ladeplanen gjennomføres. Av: Marstek regulerer alt selv. |
| `switch.*_lad_ved_negativ_pris` | På (standard): lad når timeprisen er negativ. |
| `switch.*_tilbakehold_under_kostpris` | På (standard): ikke utlad under kostprisen på beholdningen. |
| `switch.*_ingen_tap` | På: tilbakehold håndheves og aldri salg under kostpris. |
| `switch.*_salg` | På: overskudd selges i de dyreste timene. Uavhengig av prisstyringen. |
| `sensor.*_ladeplan` | Tilstand: `laden`, `gepland`, `klaar`, `vol`, `geen` eller `onbekend`. Attributter: `tekst` (lesbart sammendrag), `laaduren`, `venster`, `stroomschema` (tidslinje, kontroller, priser og oversikt til kortene) og flere. |
| `sensor.*_salgsplan` | Tilstand: `verkopen`, `gepland`, `geen` eller `onbekend`. Attributter: `verkoopuren`, `overschot_kwh`, `reserve_soc`, `tekst` og flere. |
| `sensor.*_planlagt_ladeeffekt`, `*_energi_a_lade`, `*_ladestart`, `*_ladeslutt`, `*_gjennomsnittlig_ladepris` | Den fordelte ladeeffekten i W, energien som fortsatt skal lades i kWh, start og slutt på den planlagte ladingen, og gjennomsnittsprisen for den i €/kWh. |
| `sensor.*_gevinst_i_dag`, `*_gevinst_denne_uken`, `*_gevinst_forrige_uke`, `*_gevinst_denne_maneden`, `*_gevinst_i_ar` | Realisert gevinst i euro (se [Gevinst](#gevinst)). |
| `sensor.*_forventet_gevinst` | Anslått gevinst for gjeldende planer i euro; attributtet `regels` inneholder oppdelingen. |
| `sensor.*_virkningsgrad` | Virkningsgraden som brukes, i prosent. Attributt `bron`: målt eller fast. |

Entitetsnavn følger språket i Home Assistant når entiteten opprettes (med nederlandsk heter de
`*_laadplan`, `*_prijssturing` og så videre). **Tilstandsverdier og attributtnavn er nederlandske på
alle språk** (`laden`, `tekst`, …); de er faste slik at automasjoner fortsetter å fungere.

## Utvikling

Beregningsregelen ligger atskilt fra Home Assistant i `planner.py` og har tester med
ekte priser. Styringslogikken er testet mot et falsk Home Assistant:

```bash
python3 -m unittest discover -s tests -v
```

## Endringslogg

Se [CHANGELOG.md](CHANGELOG.md), inkludert de brytende endringene.

## Takk

Denne integrasjonen bygger på arbeidet til Marstek Venus-miljøet:

- [Tweakers-forumtråden](https://gathering.tweakers.net/forum/list_messages/2282240/0) der dette fellesskapsarbeidet diskuteres, en hederlig omtale til alle der som deler funn og konfigurasjoner.
- [Superduper1969](https://github.com/Superduper1969) for LilyGO RS485- og Elfin EW11-konfigurasjonene denne integrasjonen er bygget rundt, og scruysberghs, som det takkes i disse konfigurasjonene.
- [fonske](https://github.com/fonske) for Modbus TCP-konfigurasjonen til Venus E v3.
- [ViperRNMC](https://github.com/ViperRNMC) for integrasjonen Marstek Venus Modbus.

## Lisens

Apache 2.0, se [LICENSE](LICENSE).
