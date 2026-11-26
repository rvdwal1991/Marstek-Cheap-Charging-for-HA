<img src="custom_components/marstek_goedkoop_laden/brand/icon.png" width="96" align="right" alt="">

# Marstek Billig Lading for Home Assistant

[🇬🇧 English](README.md) · [🇳🇱 Nederlands](README.nl.md) · [🏳️ Frysk](README.fy.md) · [🇩🇪 Deutsch](README.de.md) · [🇫🇷 Français](README.fr.md) · [🇪🇸 Español](README.es.md) · [🇸🇪 Svenska](README.sv.md) · 🇳🇴 Norsk

[![Open your Home Assistant instance and open this repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=rvdwal1991&repository=Marstek-Cheap-Charging-for-HA&category=integration)
[![Open your Home Assistant instance and start setting up the integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=marstek_goedkoop_laden)

Lader opp et Marstek Venus-hjemmebatteri fra nettet i de billigste timene av en dynamisk
strømavtale, slik at det er fullt før prisene går opp.

Utgangspunktet er **selvforsyning**. Batteriet fortsetter å regulere seg selv (anti-feed,
null på måleren). Denne integrasjonen legger til én ting: lading fra nettet i de billigste
timene. Dessuten finnes det et eget valg, avslått som standard, for å **selge overskudd** i de
dyreste timene.

> **Maskinvare og kompatibilitet.** Integrasjonen styrer et Marstek Venus via RS485-kontrollregistrene.
> Bare den første raden er kjørt på et ekte batteri:
>
> | Tilkobling | Modell | Status |
> |---|---|---|
> | LilyGO T-CAN485 + ESPHome (RS485) | Venus E v2 | **Testet** på ekte maskinvare (oppsettet den er bygget på) |
> | Modbus-hub i Home Assistant, via RS485-til-TCP-omformer (Elfin EW11 og lignende) | Venus E v1/v2 | Bare testet med simulerte kall |
> | Modbus-hub i Home Assistant, direkte over Ethernet | Venus E v3 | Bare testet med simulerte kall |
> | Integrasjonen *Marstek Venus Modbus* (ViperRNMC) | Venus E v3 | Bare testet med simulerte kall |
> | Hvilken som helst av de over | Venus A, Venus D, andre modeller | **Ikke kontrollert, ikke testet.** De skal visstnok dele kontrollregistrene, men det er ikke bekreftet. Sett batterikapasiteten i innstillingene (standard 5,12 kWh). |
> | Sky, app eller andre integrasjoner | alle | Støttes ikke |
>
> Tilkoblingene i detalj:
>
> - **LilyGO T-CAN485 med ESPHome** over RS485, med konfigurasjonen
>   [MarstekVenus-LilygoRS485](https://github.com/Superduper1969/MarstekVenus-LilygoRS485).
>   Dette er oppsettet integrasjonen er bygget på og testet med. Den bruker entitetene dette
>   oppsettet tilbyr: *RS485 Control Mode*, *Forcible Charge/Discharge*,
>   *Forcible Charge Power* (påkrevd) og eventuelt *Max. Charge Power*, *Max. Discharge Power*,
>   *Forcible Discharge Power*, *Discharging Cutoff Capacity* og tellerne for total ladet/utladet
>   energi.
> - **Modbus i Home Assistant**, med en Modbus-hub du selv definerer i `configuration.yaml`:
>   en Elfin EW11 eller en annen RS485-til-TCP-omformer
>   ([MarstekVenus-ElfinEW11](https://github.com/Superduper1969/MarstekVenus-ElfinEW11)), eller
>   **Venus E v3 rett over Ethernet** (Modbus TCP, port 502, unit 1, EMS V144 eller nyere;
>   [MarstekVenusV3-modbus-TCP-IP](https://github.com/fonske/MarstekVenusV3-modbus-TCP-IP)).
>   Integrasjonen leser registersensorene i det oppsettet og skriver registrene 42000 (RS485-styring),
>   42010 (tvangsmodus), 42020/42021 (tvungen lade-/utladeeffekt) og, hvis du oppgir sensorene,
>   44002/44003 (maksimal lade-/utladeeffekt) med `modbus.write_register`. Med maksimal
>   utladeeffekt fungerer *Tilbakehold* og *Ingen tap* også; uten den er de ikke tilgjengelige.
>   Venus E v3 har ladenivået (SoC) i register 34002 (skala 0,1), ikke i 32104.
> - **Integrasjonen *Marstek Venus Modbus***
>   ([ViperRNMC/marstek_venus_modbus](https://github.com/ViperRNMC/marstek_venus_modbus)), som
>   også snakker Modbus TCP (Ethernet på en Venus E v3, eller en RS485-gateway). Velg denne hvis du
>   allerede bruker den integrasjonen: den leverer entitetene (`switch` for RS485-styring, `select`
>   for tvangsmodus, `number` for effektene). Slå først på bryteren *RS485 control mode* og velgeren
>   *Force mode* der, de er avslått som standard.
>
> Valgene Modbus og Marstek Venus Modbus er **nye og hittil bare testet med simulerte
> kall, ikke på ekte maskinvare**.
>
> Andre måter å koble til batteriet på (sky, andre integrasjoner) er utestet og fungerer mest
> sannsynlig ikke, fordi de ikke tilbyr disse RS485-kontrollentitetene.
>
> **Dynamiske strømpriser:** denne integrasjonen gir bare mening med en **dynamisk
> strømavtale**, der prisen endrer seg hver time. Den lader i de billigste timene og unngår
> de dyre, så med fast pris er det ingenting å tjene. Den er bygget rundt det
> nederlandske markedet og Zonneplan-priser (timepriser, publisert for neste dag mellom 13:00 og
> 15:00). Enhver prissensor med en timeprisliste som attributt fungerer, se
> [Prissensor](#prissensor).
>
> **Språk:** plantekst, flytskjema og kort følger valget *Språk*
> (Automatisk, Nederlands, English, Frysk, Deutsch, Français, Español, Svenska eller Norsk;
> Automatisk følger Home Assistant når det er ett av disse, ellers engelsk). Entitetsnavn følger språket i Home Assistant. Tilstandsverdier og attributtnavn (`laden`, `tekst`, …) er faste.

## Hva den gjør

1. **Er lading lønnsomt?** En time er billig nok hvis prisen er lavere enn
   `virkningsgrad × (gjennomsnittet av de 6 dyreste timene de neste 18 timene) − margin`.
   Virkningsgraden (tur-retur ved lading og utlading, rundt 77 % på min enhet) måles ut fra
   energitellerne til Marstek.
2. **Vindu.** Den første blokken med billige timer er ladevinduet. Én eller to timer som
   ikke er helt billige nok bryter ikke blokken; lading skjer bare i de billige timene
   selv.
3. **Ladetimer.** Innenfor vinduet velger den de billigste timene, akkurat så mange som trengs
   for å komme fra gjeldende SoC til 100 %. Er vinduet for kort til å fylle batteriet, planlegger den
   bare det som får plass og sier fra om det i plantekst.
4. **Fordel effekten.** Ladeeffekten er energien som ennå skal tilføres delt på tiden som er igjen
   i ladetimene. Det holder belastningen på nettilkoblingen og husets krets så lav som
   mulig. Effekten justeres underveis.
5. **Ferdig er ferdig.** Når ladetimene er over eller batteriet er fullt, går Marstek
   tilbake til anti-feed. Den starter ikke igjen i samme vindu og holder ikke ladningen.

Bare **publiserte** priser brukes. Planen for natten dukker derfor opp så snart
morgendagens priser er kjent (hos Zonneplan mellom 13:00 og 15:00).

Eksempel (10. november 2026, batteri på 12 %): billig vindu 23:00–07:00, lading kl. 02:00,
03:00 og 04:00 med omtrent 1900 W til gjennomsnittlig € 0,37, mot € 0,55–0,67 på dagtid.

## Lading ved negativ pris

Hvis timeprisen er negativ, lader batteriet fra nettet, uavhengig av ladeplanen
og selv når prisstyringen er av. Dette har sin egen bryter, **på som standard**.

Den ser på hele **vinduet** med sammenhengende negative timer, ikke bare gjeldende time, og
henter ut mest mulig av det:

1. Den regner ut hvor mye batteriet fortsatt kan ta imot (SoC til 100 %).
2. Den fordeler energien over timene **etter verdi**: jo mer negativ prisen er, desto mer
   lades i den timen (opp til det en time tåler ved maksimal effekt). Eksempel: tre
   negative timer på −€ 0,03, −€ 0,20 og −€ 0,12 og 3 kWh igjen å lade. Timen på −€ 0,20 får
   omtrent 1,9 kWh og timen på −€ 0,12 omtrent 1,2 kWh. Timen på −€ 0,03 ville ligge under
   minste ladeeffekt og faller derfor bort; andelen går til de to andre.
3. Fordi energien er spredt over timene, blir effekten lavere enn om man lader med full
   effekt en kort stund. Kan batteriet ta imot mer enn vinduet byr på, fylles hver time til maksimum.
   En enkelt time som ikke kan fylle batteriet, lades med full effekt.
4. Plateksten og flytskjemaet viser vinduet, de valgte timene, effekten og den forventede
   gevinsten (det du får betalt for å lade).

Valget *Negativ pris: hvordan energien fordeles* veksler mellom to måter:

- **Fordel etter verdi** (standard): som beskrevet over, lavere effekt, litt mindre gevinst.
- **Maksimal gevinst**: timene fylles én etter én, beste pris først, hver med full effekt, og
  resten går til den nest beste timen. I eksemplet tar timen på −€ 0,20 2,25 kWh med full effekt
  og timen på −€ 0,12 de resterende 0,8 kWh, som gir omtrent € 0,55 i stedet for € 0,52. Prisen er
  flere korte støt med full effekt.

Så snart prisen blir positiv igjen eller batteriet er fullt, går Marstek tilbake til
anti-feed. Planen beregnes på nytt hvert minutt; en time som allerede var i bruk får litt ekstra
slingringsmonn før den faller bort for å ligge under minsteeffekten.

Grensen kan justeres (*Negativ pris: grense*, standard € 0,00). Prisen hentes fra
prissensoren, så hos Zonneplan er det prisen inkludert avgifter.

## Solprognose

Med solceller fylles batteriet gratis om dagen. Hvis du lader det fullt fra nettet om natten, har
solenergien ingen plass igjen og går til nettet for lite eller ingenting, noe som betyr mer
nå som nettmålingsordningen (*salderingsregeling*) avsluttes. Derfor tar integrasjonen
hensyn til forventet solproduksjon:

1. Den leser prognosen fra **Energi-dashbordet** i Home Assistant (*Innstillinger → Dashbord →
   Energi → Solcellepaneler → Prognose for solproduksjon*). Forecast.Solar, Solcast, Open-Meteo og
   andre prognoseintegrasjoner fungerer, og ingenting ekstra må settes opp. Uten en prognose
   der endrer ingenting seg.
2. Den regner ut forventet overskudd: per time prognosen, multiplisert med innstillingen for
   pålitelighet (standard 70 %), minus ditt eget forbruk i den timen. Med en *Husforbruk-sensor*
   lærer integrasjonen ditt gjennomsnittlige forbruk per time på døgnet (hverdager og helger
   hver for seg) og bruker det, slik at en middag som huset selv spiser opp ikke gir noe
   overskudd; uten sensoren brukes det faste *Salg: gjennomsnittlig eget forbruk*.
3. Den lader om natten bare så mye at det er plass til dette overskuddet når solen
   står opp: energien det egne forbruket bruker fram til da, pluss det som fortsatt trengs. På en
   solrik dag kan det være noen få kWh i stedet for et fullt batteri, eller ingenting
   (planteksten sier da at solen fyller batteriet).
4. En skyet dag gir lite eller ikke noe overskudd, og da lades batteriet fullt som før.

Dette kan slås av med *Bruk solprognosen*. Prognosen leses hvert 30. minutt. Den
reduserer bare mengden som skal lades; den flytter ikke ladetimer og endrer ikke salg.

## Tilbakehold under kostpris

Strøm som er ladet fra nettet har en kostpris: ladeprisen delt på virkningsgraden. Hvis
batteriet ga den energien tilbake rett etter lading, i timer som er billigere enn den
kostprisen, ville lading koste penger. Utlading blokkeres derfor så lenge:

- det finnes ladet beholdning i batteriet (se *Gevinst*), og
- timeprisen er lavere enn kostprisen på den beholdningen.

Huset bruker da nettstrøm, som i øyeblikket er billigere enn det som ligger i batteriet.
Så snart prisen når kostprisen, eller beholdningen er brukt opp, tar Marstek over
igjen. Dette har sin egen bryter, **på som standard**.

Teknisk sett setter integrasjonen maksimal utladeeffekt (*Max. Discharge power*) til 0.
Marstek blir stående i anti-feed, så lading fra solcelleoverskudd fortsetter. Hvis en annen
automasjon setter denne effekten til en annen verdi under tilbakeholdet (for eksempel en begrenser for en
elbillader), husker integrasjonen den verdien, setter den til 0 igjen og gjenoppretter den
huskede verdien etterpå.

Merk: Marstek kan ikke skille nettladet energi fra solenergi. Under et tilbakehold utlades
derfor ikke hele batteriet.

## Ingen tap

En egen bryter (av som standard) som gjør integrasjonen streng: energi som er ladet fra
nettet brukes eller selges aldri under kostprisen.

- **Tilbakehold håndheves**, selv om bryteren *Tilbakehold* er av.
- **Salg under kostpris blokkeres.** Hvis det finnes ladet beholdning i batteriet og
  salgsprisen er lavere enn kostprisen, selges ingenting.

Hver bokførte kWh gir da minst kostprisen, så dagens gevinst ikke kan havne under null.
Det den ikke kan utelukke:

- **Stillstand.** Hvis prisen blir under kostprisen i lang tid, forblir batteriet
  blokkert for utlading, også for lagret solenergi.
- **Avvikende virkningsgrad.** Kostprisen bruker gjennomsnittlig virkningsgrad. Gir batteriet
  mindre tilbake enn det i en syklus, er det tomt før beholdningen i bøkene er brukt opp; resten
  forfaller uten at det bokføres tap.
- **Slitasje** på batteriet regnes ikke med; bruk minste gevinst per kWh til det.

Integrasjonen beregner umiddelbart på nytt når en ny prisperiode starter, så et tilbakehold
aldri starter opptil et minutt for sent.

## Salg (valgfritt)

Salg har sin egen bryter og er uavhengig av lading. Bare det som virkelig er til overs
selges. En time brukes til salg når alt dette stemmer:

1. **En billig lading er på vei**: et ladevindu med publiserte priser ligger foran, så kostnaden
   ved å lade opp igjen er kjent.
2. **Inntekten er tydelig høyere enn ved å lade opp igjen**: salgspris ≥ ladepris delt på
   virkningsgraden, pluss salgsmarginen (standard € 0,10 per kWh).
3. **Det finnes overskudd over reserven.** Reserven er utladegrensen til Marstek pluss
   forventet eget forbruk fram til neste lading (gjennomsnittlig husforbruk i W × timer), med et
   justerbart minimum (standard 20 %).
4. **Det er en av de dyreste timene** før ladevinduet.

Som ved lading fordeles salgseffekten over de valgte timene. Ved reserven stopper salget
og Marstek går tilbake til anti-feed.

Om vinteren er det sjelden overskudd: med et batteri på 5 kWh tar eget forbruk fram til neste
lading som regel hele ladningen. Valget gjør mest når solen fyller
batteriet og det er en pristopp om kvelden.

**Etter at nettmålingsordningen avsluttes** (den nederlandske *salderingsregeling*, 1. januar 2027) gir
innmating mindre enn timeprisen. Sett da *Salgspris: faktor* og *fradrag*: salgspris =
timepris × faktor − fradrag. For den rene markedsprisen hos Zonneplan er det omtrent
0,826 og € 0,108.

## Styring av Marstek

Integrasjonen styrer batteriet via RS485-grensesnittet (LilyGO T-CAN485 med
ESPHome):

| Tidspunkt | Kommandoer |
|---|---|
| Start lading | sett ladeeffekt → *Forcible charge/discharge* til `charge` → *RS485 Control Mode* til `enable` |
| Under lading | juster ladeeffekt (trinn på 100 W) |
| Ferdig, eller prisstyring av | *RS485 Control Mode* til `disable`, forcible tilbake til `charge`, ladeeffekt tilbake til maksimum |
| Start salg | sett utladeeffekt → forcible til `discharge` → *RS485 Control Mode* til `enable` |
| Salg ferdig, eller salg av | som ferdig: tilbake til hviletilstanden |

Tvungen **ut**lading du starter selv, blir latt i fred. Tvungen lading du starter
selv, tilbakestilles så lenge prisstyringen er på; slå den av først hvis du vil det.

## Entiteter

| Entitet | Innhold |
|---|---|
| `switch.*_prisstyring` | På: ladeplanen gjennomføres. Av: Marstek regulerer alt selv. Å slå den av setter Marstek tilbake i anti-feed umiddelbart. |
| `switch.*_lad_ved_negativ_pris` | På (standard): lad alltid med full effekt når timeprisen er negativ. Attributt `nu_actief`. |
| `switch.*_tilbakehold_under_kostpris` | På (standard): ikke utlad så lenge timeprisen er under kostprisen på den ladede beholdningen. Attributter `nu_actief`, `tot`, `voorraad_kwh`, `kostprijs`. |
| `switch.*_ingen_tap` | På: tilbakehold håndheves og aldri salg under kostpris. Attributter `vasthouden_actief`, `verkoop_tegengehouden`, `voorraad_kwh`, `kostprijs`. |
| `switch.*_salg` | På: overskudd selges i de dyreste timene. Uavhengig av prisstyringen. |
| `sensor.*_salgsplan` | Tilstand: `verkopen`, `gepland`, `geen` eller `onbekend`. Attributter: `verkoopuren`, `vermogen`, `overschot_kwh`, `reserve_soc`, `drempelprijs`, `terugkoopprijs` og `tekst`. |
| `sensor.*_ladeplan` | Tilstand: `laden`, `gepland`, `klaar`, `vol`, `geen` eller `onbekend`. Attributter: `laaduren`, `venster`, `eind`, `uren_nodig`, `vermogen`, `klaar_tot`, `tekst` (lesbart sammendrag) og `stroomschema` (tidslinje og kontroller til kortet). |
| `sensor.*_planlagt_ladeeffekt` | Den fordelte ladeeffekten i W. |
| `sensor.*_energi_a_lade` | Energi fra nettet som trengs for å bli full, i kWh. |
| `sensor.*_ladestart` / `*_ladeslutt` | Start og slutt på den planlagte ladingen. |
| `sensor.*_gevinst_i_dag` / `*_gevinst_denne_uken` / `*_gevinst_denne_maneden` | Realisert gevinst i euro siden 00:00, siden mandag 00:00 og siden den første i måneden (se *Gevinst*). Attributter: beholdningen og, for i dag, hva som er ladet og brukt. |
| `sensor.*_gevinst_i_ar` | Realisert gevinst siden 1. januar. |
| `sensor.*_gevinst_forrige_uke` | Sluttbeløpet for forrige uke. |
| `sensor.*_forventet_gevinst` | Anslått gevinst for gjeldende planer i euro (lading pluss salg); attributtet `regels` inneholder oppdelingen. |
| `sensor.*_virkningsgrad` | Virkningsgraden som brukes, i prosent. Attributt `bron`: målt fra energitellerne eller den faste verdien. |
| `sensor.*_gjennomsnittlig_ladepris` | Gjennomsnittspris for ladetimene i €/kWh. |

Navnene over gjelder en norsk installasjon. Står Home Assistant på engelsk, heter de
`*_charge_plan`, `*_price_control` og så videre. Tilstandsverdiene og attributtnavnene er
de samme på begge språk.

## Installasjon

1. Installer med HACS (knappen over, eller legg til dette depotet som egendefinert depot, kategori
   *Integration*), eller kopier `custom_components/marstek_goedkoop_laden` til
   `/config/custom_components/`. Start Home Assistant på nytt.
2. Gå til *Innstillinger → Enheter og tjenester → Legg til integrasjon → Marstek Goedkoop Laden*.
3. Velg hvordan Marstek er koblet til (*LilyGO RS485 med ESPHome*, *Modbus i Home Assistant* eller *Marstek Venus Modbus-integrasjon*),
   deretter prissensoren og Marstek-entitetene. Det som oppdages, er ferdig utfylt. For Modbus oppgir du
   også navnet på Modbus-huben din (for eksempel `MarstekVenus`) og slaveadressen.

Krever Home Assistant 2026.3 eller nyere.

### Prissensor

Integrasjonen leser prisene fra et attributt på én sensor (standard `forecast`):

- Zonneplan-timepriser: `start_date`, `end_date`, `price_tax_included.amount`
- Zonneplan (gammel): `datetime`, `electricity_price`
- Generisk: `start` (eller `start_time`, `datetime`) og `price` (eller `value`, `prijs`) i €/kWh

### Innstillinger

Under *Konfigurer* på integrasjonen:

| Innstilling | Standard | Betydning |
|---|---|---|
| Språk | Automatisk | Språk for plantekst, flytskjema og kort: Automatisk, Nederlands, English, Frysk, Deutsch, Français, Español, Svenska eller Norsk. |
| Kjøpspris for batteriet | € 0 | Brukes til avskrivning. 0 slår av avskrivning. |
| Batteriets levetid (sykluser) | 6000 | Forventet antall fulle sykluser. Avskrivning per kWh = pris ÷ (sykluser × kapasitet); for eksempel er € 1500 over 6000 sykluser på 5,12 kWh omtrent € 0,049 per kWh. |
| Bruk solprognosen | På | Ta hensyn til forventet solproduksjon fra Energi-dashbordet ved lading om natten. |
| Pålitelighet for solprognosen | 70 % | Den delen av prognosen det skal regnes med. Lavere er mer forsiktig. |
| Husforbruk-sensor | ingen | Valgfri sensor med effekten hele huset bruker (W eller kW), uten batteriet. Integrasjonen lærer gjennomsnittet per time på døgnet, for hverdager og helger, og bruker det til solcelleoverskuddet i stedet for det faste egne forbruket. En billader skjever gjennomsnittet, så utelat den hvis du kan. |
| Minste gevinst per kWh | € 0,02 | Hva lading minst må gi, etter ladetap. Timer som ligger mindre enn en halv cent over grensen teller likevel med, så en nesten flat natt ikke deles opp for en brøkdel av en cent. |
| Antall dyreste timer | 6 | Hvor mange dyre timer senere en time sammenlignes med. |
| Timer å se fremover | 18 | Hvor langt etter en time det letes etter dyre timer. |
| Minste antall kjente timer fremover | 8 | Timer med færre kjente priser etter seg blir ignorert. |
| Minste ladeeffekt | 400 W | Nedre grense ved fordeling. |
| Virkningsgrad når tellerne mangler | 0,77 | Virkningsgraden beregnes ut fra energitellerne til Marstek (total utladet ÷ total ladet, begrenset til 70–95 %). Denne faste verdien gjelder bare når tellerne mangler. Virkningsgraden for bare lading eller bare utlading er kvadratroten av den. |
| Batterikapasitet | 5,12 kWh | Brukes bare når ingen kapasitetssensor er satt. |
| Negativ pris: grense | € 0,00 | Under denne timeprisen lader batteriet med full effekt. |
| Salg: minste gevinst per kWh | € 0,10 | Hva salg minst må gi etter gjenlading. |
| Salg: gjennomsnittlig eget forbruk | 400 W | Bestemmer reserven fram til gjenlading. |
| Salg: minste reserve | 20 % | Under dette SoC-nivået selges ingenting. |
| Salgspris: faktor og fradrag | 1 og € 0 | Salgspris = timepris × faktor − fradrag. |

Maksimal ladeeffekt (*Max. Charge power* hos Marstek) bestemmer antall ladetimer.
Sett den lavere, så planlegger den flere timer og lader roligere.

## Dashbord

### Kort fra integrasjonen

Integrasjonen leverer sju kort; ingen ressurs trenger å legges til. Last nettleseren på nytt
etter installasjon eller oppdatering. Hvert kort kan settes opp i kortredigereren (den visuelle
redigereren) så vel som i YAML, og når du utelater `entity`, finnes ladeplan-sensoren automatisk.

| Kort | Innhold |
|---|---|
| `custom:marstek-goedkoop-laden-card` | Flytskjema: dagens tidslinje og, per del (lading, salg, negativ pris, tilbakehold), hvilke kontroller som består og hvor det stopper. |
| `custom:marstek-goedkoop-laden-compact-card` | Det samme i noen få linjer: tidslinjen, utfallet per del med begrunnelse, og én linje med gevinsten. |
| `custom:marstek-goedkoop-laden-opbrengst-card` | Bare gevinst: i dag, denne uken, forrige uke, denne måneden og forventningen for gjeldende plan. |
| `custom:marstek-goedkoop-laden-schakelaars-card` | Kompakt: knapper for å slå lading, salg, lading ved negativ pris, tilbakehold og ingen tap av eller på. |
| `custom:marstek-goedkoop-laden-status-card` | Hva som skjer nå, ladenivået (SoC) som en søyle, prisen nå og neste trinn. |
| `custom:marstek-goedkoop-laden-prijzen-card` | Prisdiagram uten ekstra kort: timene med lading, salg og negative priser markert, og en linje for nå. |
| `custom:marstek-goedkoop-laden-voorraad-card` | Den ladede beholdningen, kostprisen, virkningsgraden, avskrivningen per kWh og kapasiteten. |

```yaml
type: custom:marstek-goedkoop-laden-card
entity: sensor.marstek_goedkoop_laden_laadplan   # valgfritt
title: Prisstyring                               # valgfritt
opbrengst: false                                 # valgfritt, se under
```

Gevinstkortet kan tilpasses, i YAML eller i kortredigereren:

```yaml
type: custom:marstek-goedkoop-laden-opbrengst-card
tiles: [vandaag, maand, jaar]   # velg blant: vandaag, week, vorige_week, maand, jaar, verwacht (i denne rekkefølgen)
expected_details: false         # skjul linjene per del av planen (standard: true)
notes: false                    # skjul merknaden under kortet (standard: true)
```

| Valg | Standard | Betydning |
|---|---|---|
| `tiles` | alle seks | Hvilke fliser som vises og i hvilken rekkefølge: i dag, denne uken, forrige uke, denne måneden, i år, forventet (plan). |
| `expected_details` | `true` | Linjene med forventet gevinst per del (lading, salg). |
| `notes` | `true` | Merknaden med ladet beholdning, hva som er ladet i dag og avskrivningen. |

Valg for de andre kortene (alle finnes også i kortredigereren):

| Kort | Valg | Standard | Betydning |
|---|---|---|---|
| flyt, kompakt | `show_timeline` | `true` | Vis dagens tidslinje. |
| flyt, kompakt, brytere | `lanes` | alle fem | Hvilke deler som vises: `bijladen`, `verkoop`, `negatief`, `vasthouden`, `geen_verlies`. |
| status | `show_soc`, `show_price`, `show_next` | `true` | Ladenivå-søylen, prisen nå, neste trinn. |
| priser | `hours_back` | `2` | Timer av fortiden som vises. |
| priser | `hours_ahead` | `0` | Timer fremover som vises; 0 er til siste kjente pris. |
| priser | `show_values` | `false` | Skriv prisen over hver søyle (opptil 24 søyler). |
| priser | `height` | `140` | Høyden på diagrammet i piksler. |
| beholdning | `tiles` | alle fem | `voorraad`, `kostprijs`, `rendement`, `afschrijving`, `capaciteit`. |
| beholdning | `notes` | `true` | Merknaden under kortet. |

`opbrengst` avgjør om flytkortet også viser gevinsten: av som standard for det vanlige
kortet, én linje som standard for det kompakte kortet. I flytskjemaet er grønt en kontroll som
består, rødt er kontrollen der det stopper, og stiplet er et utfall der ingenting skjer. Alle
kortene leser attributtet `stroomschema` på ladeplan-sensoren.

## Gevinst

**Avskrivning.** Hvis du setter en kjøpspris, koster hver kWh batteriet utlader litt slitasje: pris ÷ (sykluser × kapasitet). Det trekkes fra den realiserte gevinsten (i dag, uke, måned), regnes med i den forventede gevinsten, og brukes i beslutningene: en time er bare verdt å lade hvis den fortsatt slår slitasjen, salg trenger slitasjen oppå salgsmarginen, og *Tilbakehold* og *Ingen tap* behandler kostpris pluss slitasje som break-even-pris. Med pris 0 (standard) endrer ingenting seg.

Det finnes to slags gevinst: hva gjeldende plan forventes å tjene, og det som faktisk
er tjent.

### Forventet (anslag på forhånd)

- **Lading**: hva energien som skal kjøpes koster, mot hva den er verdt senere. Verdien er
  virkningsgraden ganger gjennomsnittsprisen for de dyre timene ladetimen ble
  sammenlignet med.
- **Salg**: inntekten fra overskuddet, minus hva gjenlading koster.

Under en lading teller bare det som fortsatt skal lades.

### I dag og denne uken (realisert)

1. Energi integrasjonen lader fra nettet (ladeplan eller negativ pris) blir til
   **beholdning**: brukbare kWh = ladede kWh × virkningsgrad, med som kostpris det den energien kostet
   i øyeblikket.
2. Hvis batteriet deretter utlades til eget forbruk, brukes den beholdningen først. Gevinsten er
   `utladede kWh × (strømpris i øyeblikket − kostpris per brukbare kWh)`.
3. Ved salg er gevinsten `solgte kWh × salgspris − kostpris`; for energi som ikke
   kommer fra beholdningen (solenergi) er kostprisen det gjenlading koster.
4. **I dag** er summen siden 00:00, **denne uken** siden mandag 00:00 og **denne måneden** siden den første i måneden. **Forrige uke** er sluttbeløpet for uken før.

Det som fortsatt ligger i beholdningen er ikke tjent ennå og teller først når det brukes. Energi
som solen legger i batteriet og som du bruker selv senere, teller ikke: Marstek
gjør det også uten denne integrasjonen. Beløpene kommer fra energitellerne til Marstek
og timeprisen i øyeblikket; et hopp i telleren etter en feil bokføres ikke.

### Separate kort

Planlinje (Markdown-kort):

```yaml
type: markdown
content: >-
  **Ladeplan:** {{ state_attr('sensor.marstek_goedkoop_laden_laadplan', 'tekst') }}
  {% if is_state('switch.marstek_goedkoop_laden_prijssturing', 'off') %}
  · ⚠️ prisstyringen er **av**{% endif %}
```

## Utvikling

Beregningsregelen ligger atskilt fra Home Assistant i `planner.py` og har tester med
ekte priser. Styringslogikken er testet mot et falsk Home Assistant
(`tests/test_sturing.py`):

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
