<img src="custom_components/marstek_goedkoop_laden/brand/icon.png" width="96" align="right" alt="">

# Marstek Goedkoop Laden för Home Assistant

[🇬🇧 English](README.md) · [🇳🇱 Nederlands](README.nl.md) · [🏳️ Frysk](README.fy.md) · [🇩🇪 Deutsch](README.de.md) · [🇫🇷 Français](README.fr.md) · [🇪🇸 Español](README.es.md) · 🇸🇪 Svenska · [🇳🇴 Norsk](README.nb.md)

[![Open your Home Assistant instance and open this repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=rvdwal1991&repository=Marstek-Cheap-Charging-for-HA&category=integration)
[![Open your Home Assistant instance and start setting up the integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=marstek_goedkoop_laden)

Laddar upp ett Marstek Venus-hembatteri från nätet under de billigaste timmarna med ett
elavtal med dynamiska priser, så att det är fullt innan priserna stiger.

Utgångspunkten är **självförsörjning**: batteriet fortsätter att styra sig självt (anti-feed, noll
på mätaren). Integrationen lägger till en enda sak, laddning från nätet under de billigaste
timmarna, plus några valfria extrafunktioner runt omkring.

**Du behöver:**

- ett **elavtal med dynamiska priser** med timpriser. Med fast tariff finns inget att vinna.
  Det byggdes kring den nederländska marknaden och Zonneplan (priserna för nästa dag publiceras
  mellan 13:00 och 15:00), men vilken sensor som helst med en timprislista fungerar, se
  [Prissensor](#prissensor);
- en Marstek Venus som Home Assistant kan styra via RS485 eller Modbus, se
  [Kompatibilitet](#kompatibilitet). **Bara uppsättningen LilyGO RS485 + ESPHome har testats på
  ett riktigt batteri.**
- Home Assistant 2026.3 eller nyare.

## Vad den gör

| Läge | Standard | Vad det gör |
|---|---|---|
| **Prisstyrning** | av | Laddar från nätet under de billigaste timmarna och sprider effekten över dem. |
| **Ladda vid negativt pris** | på | Laddar när timpriset är negativt och får ut det mesta av fönstret. |
| **Solprognos** | på | Laddar mindre på natten när solen kommer att fylla batteriet under dagen. Kräver en solprognos i Energipanelen. |
| **Spärr under kostnadspris** | på | Urladdar inte så länge nätet är billigare än vad det laddade lagret kostade. |
| **Ingen förlust** | av | Strikt version av spärren: säljer heller aldrig laddat lager under kostnadspris. |
| **Försäljning** | av | Säljer överskott under de dyraste timmarna. |

Varje läge har en egen brytare. **Prisstyrning är avstängd efter installationen**: ställ in
integrationen, kontrollera att plantexten på laddningsplanens sensor ser rätt ut och slå sedan på den.

## Snabbstart

1. Installera med HACS (knappen ovan, eller lägg till det här arkivet som ett eget arkiv, kategori
   *Integration*), eller kopiera `custom_components/marstek_goedkoop_laden` till
   `/config/custom_components/`. Starta om Home Assistant.
2. *Inställningar → Enheter och tjänster → Lägg till integration → Marstek Goedkoop Laden*.
3. Välj hur din Marstek är ansluten, därefter prissensorn och Marstek-entiteterna.
   Det som upptäcks fylls i på förhand. För Modbus anger du också namnet på din Modbus-hubb (till
   exempel `MarstekVenus`) och slavadressen.
4. Slå på brytaren **Prisstyrning** när planen ser rätt ut.
5. Lägg till kort: *Redigera instrumentpanel → Lägg till kort → sök "Marstek"*, se [Instrumentpanelskort](#instrumentpanelskort).

Texterna (planrad, flödesschema, kort) följer alternativet *Språk*: Automatisk, Nederlands,
English, Frysk, Deutsch, Français, Español, Svenska eller Norsk. Automatisk följer Home Assistant
när det är ett av dessa, annars engelska.

## Så fungerar laddningsplanen

1. **Är laddning värd det?** En timme är billig nog om dess pris är lägre än
   `verkningsgrad × (medelvärdet av de 6 dyraste timmarna de närmaste 18 timmarna) − marginal`.
   Verkningsgraden (tur-och-retur för laddning och urladdning, cirka 77 % uppmätt här) kommer från
   Marsteks energiräknare.
2. **Fönster.** Det första blocket med billiga timmar är laddfönstret. En eller två timmar som
   precis inte är billiga nog bryter inte blocket; laddning sker bara under de billiga timmarna
   själva.
3. **Laddtimmar.** Inom fönstret väljs de billigaste timmarna, precis så många som behövs för att
   komma från nuvarande SoC till 100 %. Om fönstret är för kort för att fylla batteriet planeras
   bara det som ryms, och det anges i plantexten.
4. **Sprid effekten.** Laddeffekten är den energi som ännu ska tillföras delat med tiden som
   återstår av laddtimmarna. Det håller belastningen på nätanslutningen låg. Effekten justeras
   längs vägen.
5. **Klart är klart.** När laddtimmarna är över eller batteriet är fullt går Marstek
   tillbaka till anti-feed. Den startar inte igen i samma fönster.

Bara **publicerade** priser används, så planen för natten visas så snart morgondagens
priser är kända. Exempel (10 november 2026, batteri på 12 %): billigt fönster 23:00–07:00,
laddning kl. 02:00, 03:00 och 04:00 med cirka 1900 W för i snitt € 0,37, mot € 0,55–0,67
under dagen.

### Laddning vid negativt pris

Om timpriset är negativt laddar batteriet, oavsett laddningsplanen och även när
prisstyrningen är avstängd. Den tittar på hela **fönstret** av på varandra följande negativa timmar:

1. Den räknar ut hur mycket batteriet fortfarande kan ta emot (SoC till 100 %).
2. Den fördelar energin över timmarna **efter deras värde**: ju mer negativt priset är, desto
   mer laddas under den timmen, upp till vad en timme klarar vid maximal effekt. Exempel:
   −€ 0,03, −€ 0,20 och −€ 0,12 med 3 kWh att ladda ger cirka 1,9 kWh under timmen på −€ 0,20 och
   1,2 kWh under timmen på −€ 0,12. Timmen på −€ 0,03 skulle hamna under minsta laddeffekt, så den
   faller bort och dess andel går till de andra två.
3. Spridningen håller effekten lägre än en kort stöt med full effekt. En enskild timme som inte
   kan fylla batteriet laddas med full effekt.

Alternativet *Negativt pris: fördelning av energin* kan sättas till **Maximal vinst**: den bästa
timmen fylls först med full effekt, sedan nästa. I exemplet ger det cirka € 0,55
i stället för € 0,52, till priset av fler stötar med full effekt. Planen räknas om varje
minut, och en timme som redan används får lite extra utrymme innan den faller bort.

### Solprognos

Med solpaneler fylls batteriet gratis under dagen. Om du laddar det fullt från
nätet på natten finns det ingen plats kvar för överskottet, som går till nätet för lite eller inga pengar, vilket
spelar större roll nu när nettodebiteringen (*salderingsregeling*) upphör. Därför tittar integrationen på
det förväntade solutbytet:

1. Den läser prognosen från **Energipanelen** (*Inställningar → Instrumentpaneler → Energi →
   Solpaneler → Prognos för solproduktion*). Forecast.Solar, Solcast, Open-Meteo och andra
   prognosintegrationer fungerar, utan något extra att ställa in. Utan en prognos där ändras ingenting.
2. Den räknar ut det förväntade överskottet: per timme prognosen, multiplicerad med
   tillförlitligheten, minus din egen förbrukning under den timmen. Prognoser är ofta för
   rosiga, särskilt på vintern. Med *Lär in tillförlitligheten från den faktiska produktionen* på
   jämför integrationen varje dags prognos med vad panelerna verkligen producerade (produktionsräknaren
   från Energipanelen) och använder medianen av de senaste dagarna som tillförlitlighet, när det finns
   minst 3 dagar. Tills dess, och när inlärningen är avstängd, gäller inställningen
   *Solprognosens tillförlitlighet* (standard 70 %). Din egen förbrukning under den timmen: Med en
   *Huseffektsensor* lär sig integrationen din genomsnittliga förbrukning per timme på dygnet (vardagar
   och helger separat) och använder den, så en middag som huset äter upp själv lämnar inget överskott.
   Utan sensorn används den fasta *Försäljning: genomsnittlig egen förbrukning*.
3. Den laddar på natten bara så mycket att det finns plats för det överskottet när solen går upp:
   det som din egen förbrukning drar fram till dess, plus det som fortfarande behövs. En solig dag kan
   det vara några kWh i stället för ett fullt batteri, eller ingenting (plantexten säger då att solen
   fyller batteriet). En molnig dag ger litet eller inget överskott, och batteriet laddas fullt.

Prognosen läses var 30:e minut. Den sänker bara mängden som ska laddas; den flyttar inte
laddtimmar och ändrar inte försäljningen.

### Spärr och ingen förlust

Energi som laddats från nätet har ett kostnadspris: laddpriset delat med verkningsgraden. Om
batteriet gav tillbaka den energin under timmar som är billigare än så skulle laddningen kosta pengar.
**Spärren** blockerar därför urladdning så länge det finns laddat lager i batteriet (se
[Vinst](#vinst)) och timpriset ligger under kostnadspriset för det lagret. Huset använder då nätström,
som just då är billigare. Så snart priset når kostnadspriset, eller lagret är förbrukat, tar Marstek över
igen.

Tekniskt sätter integrationen den maximala urladdningseffekten till 0. Marstek står kvar i
anti-feed, så laddning från solöverskott fortsätter. Om en annan automation sätter den effekten
under spärren (till exempel en begränsare för en elbilsladdare) kommer integrationen ihåg det värdet
och återställer det efteråt. Marstek kan inte skilja nätenergi från solenergi, så under en
spärr urladdas inte hela batteriet. Spärren kräver entiteten för den maximala urladdningseffekten.

**Ingen förlust** är en separat, strängare brytare: spärren upprätthålls även om brytaren Spärr är avstängd, och
inget säljs under kostnadspriset. Varje bokförd kWh ger då minst sitt kostnadspris. Det den
inte kan utesluta:

- **Stillestånd:** om priset ligger under kostnadspriset länge förblir batteriet
  blockerat, även lagrad solenergi.
- **Avvikande verkningsgrad:** om batteriet ger tillbaka mindre än den genomsnittliga verkningsgraden är det tomt
  innan lagret i böckerna är förbrukat; resten förfaller utan att en förlust bokförs.
- **Slitage** räknas inte om du inte anger ett inköpspris (se [Vinst](#vinst)).

### Försäljning

Försäljning har en egen brytare och är oberoende av laddning. Bara det som verkligen blir över
säljs. En timme används för försäljning när allt det här gäller:

1. **En billig laddning är på väg**: ett laddfönster med publicerade priser ligger framför, så
   kostnaden för att ladda om är känd.
2. **Intäkten är tydligt högre än omladdningen**: säljpris ≥ laddpris delat med
   verkningsgraden, plus säljmarginalen (standard € 0,10 per kWh).
3. **Det finns överskott över reserven**: Marsteks urladdningsgräns plus den förväntade egna
   förbrukningen fram till omladdningen, med ett justerbart minimum (standard 20 %).
4. **Det är en av de dyraste timmarna** före laddfönstret.

Säljeffekten sprids över de valda timmarna; vid reserven upphör försäljningen. På vintern finns det
sällan överskott; alternativet gör mest nytta när solen fyller batteriet och det finns
en kvällsprisspik. Det kräver entiteten för den tvingade urladdningseffekten.

**Efter att nettodebiteringen upphör** (den nederländska *salderingsregeling*, 1 januari 2027) ger
inmatning mindre än timpriset. Ange då *Försäljningspris: faktor* och *avdrag*: försäljningspris =
timpris × faktor − avdrag. För det rena marknadspriset hos Zonneplan är det ungefär 0,826
och € 0,108.

## Kompatibilitet

Integrationen styr en Marstek Venus via dess RS485-styrregister.

| Anslutning | Modell | Status |
|---|---|---|
| LilyGO T-CAN485 + ESPHome (RS485) | Venus E v2 | **Testad** på riktig hårdvara (uppsättningen den byggdes på) |
| Modbus-hubb i Home Assistant, via RS485-till-TCP-omvandlare (Elfin EW11 och liknande) | Venus E v1/v2 | Testad endast med simulerade anrop |
| Modbus-hubb i Home Assistant, direkt via Ethernet | Venus E v3 | Testad endast med simulerade anrop |
| Integrationen *Marstek Venus Modbus* (ViperRNMC) | Venus E v3 | Testad endast med simulerade anrop |
| Någon av ovanstående | Venus A, Venus D, andra modeller | **Inte kontrollerad, inte testad.** De sägs dela styrregistren, men det är inte verifierat. Ange batterikapaciteten i inställningarna (standard 5,12 kWh). |
| Moln, app eller andra integrationer | alla | Stöds inte |

- **LilyGO T-CAN485 med ESPHome** via RS485, med konfigurationen från
  [MarstekVenus-LilygoRS485](https://github.com/Superduper1969/MarstekVenus-LilygoRS485). Den
  använder de entiteter som den uppsättningen tillhandahåller: *RS485 Control Mode*, *Forcible
  Charge/Discharge*, *Forcible Charge Power* (obligatorisk) och, valfritt, *Max. Charge Power*,
  *Max. Discharge Power*, *Forcible Discharge Power*, *Discharging Cutoff Capacity* samt
  totalräknarna för laddad och urladdad energi.
- **Modbus i Home Assistant**, med en Modbus-hubb som du själv definierar i
  `configuration.yaml`: en Elfin EW11 eller någon annan RS485-till-TCP-omvandlare
  ([MarstekVenus-ElfinEW11](https://github.com/Superduper1969/MarstekVenus-ElfinEW11)), eller
  **Venus E v3 direkt via Ethernet** (Modbus TCP, port 502, unit 1, EMS V144 eller nyare;
  [MarstekVenusV3-modbus-TCP-IP](https://github.com/fonske/MarstekVenusV3-modbus-TCP-IP)).
  Integrationen läser registersensorerna från den uppsättningen och skriver registren 42000
  (RS485-styrning), 42010 (tvångsläge), 42020/42021 (tvingad laddnings-/urladdningseffekt) och,
  om du anger sensorerna, 44002/44003 (maximal laddnings-/urladdningseffekt) med
  `modbus.write_register`. Utan den maximala urladdningseffekten är *Spärr* och *Ingen förlust*
  inte tillgängliga. Venus E v3 har sin laddningsnivå i register 34002 (skala 0,1), inte i 32104.
- **Integrationen *Marstek Venus Modbus***
  ([ViperRNMC/marstek_venus_modbus](https://github.com/ViperRNMC/marstek_venus_modbus)), som
  också talar Modbus TCP. Välj den här om du redan använder den: den levererar entiteterna (`switch`
  RS485-styrläge, `select` tvångsläge, `number` effekter). Aktivera först strömbrytaren
  *RS485 control mode* och väljaren *Force mode* där, de är avstängda som standard.

### Vad integrationen skickar till Marstek

| Tillfälle | Kommandon |
|---|---|
| Starta laddning | sätt laddeffekt → tvångsläge `charge` → RS485-styrning `enable` |
| Under laddning | justera laddeffekten (steg om 100 W) |
| Klart, eller prisstyrning av | RS485-styrning `disable`, tvångsläge tillbaka till `charge`, laddeffekt tillbaka till maximum |
| Starta försäljning | sätt urladdningseffekt → tvångsläge `discharge` → RS485-styrning `enable` |
| Försäljning klar, eller försäljning av | samma som klart: tillbaka till viloläget |

Tvingad **ur**laddning som du startar själv lämnas ifred. Tvingad laddning som du startar
själv återställs så länge prisstyrningen är på; stäng av den först om du vill det.

## Inställningar

Under *Konfigurera* på integrationen. Alternativen finns i grupper; entiteterna ligger i en
hopfälld grupp längst ned.

### Prissensor

Integrationen läser priserna från ett attribut på en sensor (standard `forecast`):

- Zonneplans timpriser: `start_date`, `end_date`, `price_tax_included.amount`
- Zonneplan (gammalt): `datetime`, `electricity_price`
- Generiskt: `start` (eller `start_time`, `datetime`) och `price` (eller `value`, `prijs`) i €/kWh

### Alternativ

| Grupp | Inställning | Standard | Betydelse |
|---|---|---|---|
| | Språk | Automatisk | Språk för plantext, flödesschema och kort. |
| Batteri | Batterikapacitet | 5,12 kWh | Används bara när ingen kapacitetssensor är angiven. |
| Batteri | Verkningsgrad när räknarna saknas | 0,77 | Verkningsgraden beräknas från Marsteks energiräknare (total urladdad ÷ total laddad, begränsad till 70–95 %). Det fasta värdet gäller bara när de räknarna saknas. Verkningsgraden för en riktning är dess kvadratrot. |
| Batteri | Batteriets inköpspris | € 0 | Används för avskrivning. 0 stänger av den. |
| Batteri | Batteriets livslängd (cykler) | 6000 | Avskrivning per kWh = pris ÷ (cykler × kapacitet); € 1 500 över 6 000 cykler på 5,12 kWh blir cirka € 0,049 per kWh. |
| Batteri | Urladdningsgräns | 12 % | Används när ingen entitet för urladdningsgräns är angiven. |
| Laddning | Minsta vinst per kWh | € 0,02 | Vad laddningen minst måste ge, efter laddförluster. Timmar som ligger mindre än en halv cent över gränsen räknas ändå, så en nästan platt natt delas inte upp på grund av en bråkdel av en cent. |
| Laddning | Minsta laddeffekt | 400 W | Nedre gräns vid utspridning. |
| Laddning | Attribut med priserna | `forecast` | Attributet på prissensorn med timpriserna. |
| Laddning | Antal dyraste timmar att jämföra med | 6 | Hur många dyra timmar senare på dagen en timme jämförs med. |
| Laddning | Antal timmar att se framåt | 18 | Hur långt efter en timme som man letar efter dyra timmar. |
| Laddning | Minsta antal kända timmar framåt | 8 | Timmar med färre kända priser efter sig räknas inte med. |
| Negativt pris | Negativt pris: gräns | € 0,00 | Under detta timpris laddar batteriet. |
| Negativt pris | Negativt pris: fördelning av energin | Efter värde | Efter värde (lägre effekt) eller maximal vinst (bästa timmarna först). |
| Sol | Använd solprognosen | På | Ta hänsyn till det förväntade solutbytet från Energipanelen vid nattladdning. |
| Sol | Lär in tillförlitligheten från den faktiska produktionen | På | Jämför varje dags solprognos med vad panelerna verkligen producerade och använd medianen av de senaste dagarna som tillförlitlighet (från 3 dagar). |
| Sol | Solprognosens tillförlitlighet | 70 % | Den del av prognosen som man räknar med. Lägre är försiktigare. |
| Sol | Huseffektsensor | ingen | Valfri sensor med den effekt som hela huset använder (W eller kW), utan batteriet. En elbilsladdare snedvrider genomsnittet, så lämna den utanför om du kan. |
| Försäljning | Försäljning: minsta vinst per kWh | € 0,10 | Vad försäljningen minst måste ge efter omladdning. |
| Försäljning | Försäljning: genomsnittlig egen förbrukning | 400 W | Avgör reserven fram till omladdning, och är den fasta egna förbrukningen för solöverskottet. |
| Försäljning | Försäljning: minsta reserv | 20 % | Inget säljs under denna SoC. |
| Försäljning | Försäljningspris: faktor och avdrag | 1 och € 0 | Försäljningspris = timpris × faktor − avdrag. |

Den maximala laddeffekten (Marsteks *Max. Charge power*) avgör antalet laddtimmar. Sätt den
lägre så planeras fler timmar och laddningen blir mjukare.

## Instrumentpanelskort

Integrationen levererar sju kort; ingen resurs behöver läggas till. Uppdatera webbläsaren
efter installation eller uppdatering. Varje kort kan ställas in i kortredigeraren liksom i YAML, och
om du utelämnar `entity` hittas laddningsplanens sensor automatiskt.

| Kort | Innehåll |
|---|---|
| `custom:marstek-goedkoop-laden-card` | Flödesschema: dagens tidslinje och, per del (laddning, försäljning, negativt pris, spärr), vilka kontroller som klaras och var det stannar. |
| `custom:marstek-goedkoop-laden-compact-card` | Samma sak i några få rader: tidslinjen, utfallet per del med skälet, och en rad med vinsten. |
| `custom:marstek-goedkoop-laden-opbrengst-card` | Bara vinsten: idag, denna vecka, förra veckan, denna månad, i år och förväntan för den nuvarande planen. |
| `custom:marstek-goedkoop-laden-schakelaars-card` | Kompakt: knappar för att slå på eller av lägena. |
| `custom:marstek-goedkoop-laden-status-card` | Vad som händer nu, laddningsnivån som en stapel, priset nu och nästa steg. |
| `custom:marstek-goedkoop-laden-prijzen-card` | Prisdiagram utan extra kort: timmarna med laddning, försäljning och negativa priser markerade, och en linje för nu. |
| `custom:marstek-goedkoop-laden-voorraad-card` | Det laddade lagret, dess kostnadspris, verkningsgraden, avskrivningen per kWh och kapaciteten. |

```yaml
type: custom:marstek-goedkoop-laden-opbrengst-card
entity: sensor.marstek_goedkoop_laden_laadplan   # valfritt
title: Vinst                                     # valfritt
tiles: [vandaag, maand, jaar]                    # vilka rutor, i denna ordning
notes: false                                     # dölj anteckningen under kortet
```

| Kort | Alternativ | Standard | Betydelse |
|---|---|---|---|
| alla | `entity`, `title` | hittas automatiskt, ingen | Laddningsplanens sensor och en rubrik. |
| flöde, kompakt | `show_timeline` | `true` | Visa dagens tidslinje. |
| flöde, kompakt | `opbrengst` | av, en rad | Visa också vinsten. |
| flöde, kompakt, brytare | `lanes` | alla fem | Vilka delar som visas: `bijladen`, `verkoop`, `negatief`, `vasthouden`, `geen_verlies`. |
| vinst | `tiles` | alla sex | Valfria av `vandaag`, `week`, `vorige_week`, `maand`, `jaar`, `verwacht`, i denna ordning. |
| vinst | `expected_details`, `notes` | `true` | Raderna per del av planen; anteckningen med lager, dagens laddning och avskrivning. |
| status | `show_soc`, `show_price`, `show_next` | `true` | Stapeln för laddningsnivån, priset nu, nästa steg. |
| priser | `hours_back`, `hours_ahead` | `2`, `0` | Timmar bakåt i tiden; timmar framåt (0 är till det sista kända priset). |
| priser | `show_values`, `height` | `false`, `140` | Skriv ut priset ovanför varje stapel (upp till 24 staplar); höjd i pixlar. |
| lager | `tiles`, `notes` | alla fem, `true` | `voorraad`, `kostprijs`, `rendement`, `afschrijving`, `capaciteit`; anteckningen under kortet. |

I flödesschemat är grönt en kontroll som klaras, rött är kontrollen där det stannar och streckat är
ett utfall där ingenting händer. Planrad i ett Markdown-kort:

```yaml
type: markdown
content: >-
  **Laddningsplan:** {{ state_attr('sensor.marstek_goedkoop_laden_laadplan', 'tekst') }}
  {% if is_state('switch.marstek_goedkoop_laden_prijssturing', 'off') %}
  · ⚠️ prisstyrningen är **av**{% endif %}
```

## Vinst

Det finns två sorters vinst: vad den nuvarande planen förväntas ge, och vad som faktiskt
har tjänats in.

**Förväntad (uppskattning i förväg).** Laddning: vad energin som ska köpas kostar, mot vad den är
värd senare (verkningsgraden gånger genomsnittspriset för de dyra timmarna som laddtimmen jämfördes
med). Försäljning: intäkten från överskottet, minus vad omladdningen kostar. Under en
laddning räknas bara det som fortfarande ska laddas.

**Realiserad (idag, vecka, månad, år).**

1. Energi som integrationen laddar från nätet (laddningsplan eller negativt pris) blir
   **lager**: användbara kWh = laddade kWh × verkningsgrad, med som kostnadspris vad den energin kostade
   vid det tillfället.
2. Om batteriet sedan urladdar för egen förbrukning används det lagret först. Vinsten är
   `urladdade kWh × (elpris vid det tillfället − kostnadspris per användbar kWh)`.
3. Vid försäljning är vinsten `sålda kWh × säljpris − kostnadspris`; för energi som inte kommer
   från lagret (solenergi) är kostnadspriset vad omladdningen kostar.
4. **Idag** räknas sedan 00:00, **denna vecka** sedan måndag 00:00, **denna månad** sedan den första
   och **i år** sedan 1 januari. **Förra veckan** är det slutliga beloppet för veckan före.

Det som fortfarande ligger i lagret är inte intjänat än och räknas först när det används. Energi som
solen lägger i batteriet och som du använder själv senare räknas inte: Marstek gör det även
utan den här integrationen. Beloppen kommer från Marsteks energiräknare och timpriset
vid det tillfället; ett räknarhopp efter ett fel bokförs inte.

**Avskrivning.** Om du anger ett inköpspris kostar varje kWh som batteriet urladdar lite
slitage: pris ÷ (cykler × kapacitet). Det dras från den realiserade vinsten, räknas med i den
förväntade vinsten och används i besluten: en timme är bara värd att ladda om den fortfarande slår
slitaget, försäljning kräver slitaget utöver säljmarginalen, och *Spärr* och *Ingen förlust* behandlar kostnadspris
plus slitage som break-even-pris. Med ett pris på 0 (standard) ändras ingenting.

## Entiteter

| Entitet | Innehåll |
|---|---|
| `switch.*_prisstyrning` | På: laddningsplanen genomförs. Av: Marstek styr allt själv. |
| `switch.*_ladda_vid_negativt_pris` | På (standard): ladda när timpriset är negativt. |
| `switch.*_sparr_under_kostnadspris` | På (standard): urladda inte under lagrets kostnadspris. |
| `switch.*_ingen_forlust` | På: spärr upprätthålls och sälj aldrig under kostnadspris. |
| `switch.*_forsaljning` | På: överskott säljs under de dyraste timmarna. Oberoende av prisstyrningen. |
| `sensor.*_laddningsplan` | Tillstånd: `laden`, `gepland`, `klaar`, `vol`, `geen` eller `onbekend`. Attribut: `tekst` (läsbar sammanfattning), `laaduren`, `venster`, `stroomschema` (tidslinje, kontroller, priser och översikt för korten) med mera. |
| `sensor.*_saljplan` | Tillstånd: `verkopen`, `gepland`, `geen` eller `onbekend`. Attribut: `verkoopuren`, `overschot_kwh`, `reserve_soc`, `tekst` med mera. |
| `sensor.*_planerad_laddeffekt`, `*_energi_att_ladda`, `*_laddstart`, `*_laddslut`, `*_genomsnittligt_laddpris` | Den utspridda laddeffekten i W, energin som fortfarande ska laddas i kWh, start och slut för den planerade laddningen, och dess genomsnittspris i €/kWh. |
| `sensor.*_vinst_idag`, `*_vinst_denna_vecka`, `*_vinst_forra_veckan`, `*_vinst_denna_manad`, `*_vinst_i_ar` | Realiserad vinst i euro (se [Vinst](#vinst)). |
| `sensor.*_forvantad_vinst` | Uppskattad vinst för de nuvarande planerna i euro; attributet `regels` innehåller uppdelningen. |
| `sensor.*_verkningsgrad` | Den använda verkningsgraden, i procent. Attribut `bron`: uppmätt eller fast. |

Entitetsnamn följer språket i Home Assistant när entiteten skapas (med svenska heter de
`*_laddningsplan`, `*_prisstyrning` och så vidare). **Tillståndsvärden och attributnamn är
nederländska på alla språk** (`laden`, `tekst`, …); de är fasta så att automationer fortsätter fungera.

## Utveckling

Beräkningsregeln ligger separat från Home Assistant i `planner.py` och har tester med
verkliga priser. Styrlogiken testas mot en fejkad Home Assistant:

```bash
python3 -m unittest discover -s tests -v
```

## Ändringslogg

Se [CHANGELOG.md](CHANGELOG.md), inklusive de brytande ändringarna.

## Tack

Den här integrationen bygger på arbetet från Marstek Venus-communityn:

- [Tweakers-forumtråden](https://gathering.tweakers.net/forum/list_messages/2282240/0) där det här community-arbetet diskuteras, ett hedersomnämnande till alla där som delar resultat och konfigurationer.
- [Superduper1969](https://github.com/Superduper1969) för LilyGO RS485- och Elfin EW11-konfigurationerna som den här integrationen är byggd kring, och scruysberghs, som tackas i de konfigurationerna.
- [fonske](https://github.com/fonske) för Modbus TCP-konfigurationen för Venus E v3.
- [ViperRNMC](https://github.com/ViperRNMC) för integrationen Marstek Venus Modbus.

## Licens

Apache 2.0, se [LICENSE](LICENSE).
