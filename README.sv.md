<img src="custom_components/marstek_goedkoop_laden/brand/icon.png" width="96" align="right" alt="">

# Marstek Goedkoop Laden för Home Assistant

[🇬🇧 English](README.md) · [🇳🇱 Nederlands](README.nl.md) · [🏳️ Frysk](README.fy.md) · [🇩🇪 Deutsch](README.de.md) · [🇫🇷 Français](README.fr.md) · [🇪🇸 Español](README.es.md) · 🇸🇪 Svenska · [🇳🇴 Norsk](README.nb.md)

[![Open your Home Assistant instance and open this repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=rvdwal1991&repository=Marstek-Cheap-Charging-for-HA&category=integration)
[![Open your Home Assistant instance and start setting up the integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=marstek_goedkoop_laden)

Laddar upp ett Marstek Venus-hembatteri från nätet under de billigaste timmarna med ett
elavtal med dynamiska priser, så att det är fullt innan priserna stiger.

Utgångspunkten är **självförsörjning**. Batteriet fortsätter att styra sig självt (anti-feed,
noll på mätaren). Integrationen lägger till en enda sak: laddning från nätet under de
billigaste timmarna. Det finns också ett separat alternativ, avstängt som standard, för att
**sälja överskott** under de dyraste timmarna.

> **Hårdvara och kompatibilitet.** Integrationen styr en Marstek Venus via dess RS485-styrregister.
> Bara den första raden har körts på ett riktigt batteri:
>
> | Anslutning | Modell | Status |
> |---|---|---|
> | LilyGO T-CAN485 + ESPHome (RS485) | Venus E v2 | **Testad** på riktig hårdvara (uppsättningen den byggdes på) |
> | Modbus-hubb i Home Assistant, via RS485-till-TCP-omvandlare (Elfin EW11 och liknande) | Venus E v1/v2 | Testad endast med simulerade anrop |
> | Modbus-hubb i Home Assistant, direkt via Ethernet | Venus E v3 | Testad endast med simulerade anrop |
> | Integrationen *Marstek Venus Modbus* (ViperRNMC) | Venus E v3 | Testad endast med simulerade anrop |
> | Någon av ovanstående | Venus A, Venus D, andra modeller | **Inte kontrollerad, inte testad.** De sägs dela styrregistren, men det är inte verifierat. Ange batterikapaciteten i inställningarna (standard 5,12 kWh). |
> | Moln, app eller andra integrationer | alla | Stöds inte |
>
> Anslutningarna i detalj:
>
> - **LilyGO T-CAN485 med ESPHome** via RS485, med konfigurationen från
>   [MarstekVenus-LilygoRS485](https://github.com/Superduper1969/MarstekVenus-LilygoRS485). Det är
>   uppsättningen som integrationen byggdes på och testades med. Den använder de entiteter som
>   den uppsättningen tillhandahåller: *RS485 Control Mode*, *Forcible Charge/Discharge*,
>   *Forcible Charge Power* (obligatorisk) och, valfritt, *Max. Charge Power*, *Max. Discharge Power*,
>   *Forcible Discharge Power*, *Discharging Cutoff Capacity* samt totalräknarna för laddad och
>   urladdad energi.
> - **Modbus i Home Assistant**, med en Modbus-hubb som du själv definierar i `configuration.yaml`:
>   en Elfin EW11 eller någon annan RS485-till-TCP-omvandlare
>   ([MarstekVenus-ElfinEW11](https://github.com/Superduper1969/MarstekVenus-ElfinEW11)), eller
>   **Venus E v3 direkt via Ethernet** (Modbus TCP, port 502, unit 1, EMS V144 eller nyare;
>   [MarstekVenusV3-modbus-TCP-IP](https://github.com/fonske/MarstekVenusV3-modbus-TCP-IP)).
>   Integrationen läser registersensorerna från den uppsättningen och skriver registren 42000
>   (RS485-styrning), 42010 (tvångsläge), 42020/42021 (tvingad laddnings-/urladdningseffekt) och,
>   om du anger sensorerna, 44002/44003 (maximal laddnings-/urladdningseffekt) med
>   `modbus.write_register`. Med den maximala urladdningseffekten fungerar *Spärr* och *Ingen
>   förlust* också; utan den är de inte tillgängliga. Venus E v3 har sin laddningsnivå i register
>   34002 (skala 0,1), inte i 32104.
> - **Integrationen *Marstek Venus Modbus***
>   ([ViperRNMC/marstek_venus_modbus](https://github.com/ViperRNMC/marstek_venus_modbus)), som
>   också talar Modbus TCP (Ethernet på en Venus E v3, eller en RS485-gateway). Välj den här om du
>   redan använder den integrationen: den levererar entiteterna (`switch` RS485-styrläge, `select`
>   tvångsläge, `number` effekter). Aktivera först strömbrytaren *RS485 control mode* och väljaren
>   *Force mode* där, de är avstängda som standard.
>
> Alternativen Modbus och Marstek Venus Modbus är **nya och hittills bara testade med simulerade
> anrop, inte på riktig hårdvara**.
>
> Andra sätt att ansluta batteriet (moln, andra integrationer) är otestade och fungerar med all
> sannolikhet inte, eftersom de inte erbjuder dessa RS485-styrentiteter.
>
> **Dynamiska elpriser:** den här integrationen är bara meningsfull med ett **elavtal med dynamiska
> priser**, där priset ändras varje timme. Den laddar under de billigaste timmarna och undviker de
> dyra, så med fast tariff finns inget att vinna. Den byggdes kring den nederländska marknaden och
> Zonneplans priser (timpriser, publicerade för nästa dag mellan 13:00 och 15:00). Vilken
> prissensor som helst med en timprislista som attribut fungerar, se
> [Prissensor](#prissensor).
>
> **Språk:** plantexten, flödesschemat och korten följer alternativet *Språk*
> (Automatisk, Nederlands, English, Frysk, Deutsch, Français, Español, Svenska eller Norsk;
> Automatisk följer Home Assistant när det är ett av dessa, annars engelska). Entitetsnamn följer språket i Home Assistant. Tillståndsvärden och attributnamn (`laden`, `tekst`, …) är fasta.

## Vad den gör

1. **Är laddning värd det?** En timme är billig nog om dess pris är lägre än
   `verkningsgrad × (medelvärdet av de 6 dyraste timmarna de närmaste 18 timmarna) − marginal`.
   Verkningsgraden (tur-och-retur för laddning och urladdning, cirka 77 % på min enhet) mäts från
   Marsteks energiräknare.
2. **Fönster.** Det första blocket med billiga timmar är laddfönstret. En eller två timmar som
   precis inte är billiga nog bryter inte blocket; laddning sker bara under de billiga timmarna
   själva.
3. **Laddtimmar.** Inom fönstret väljs de billigaste timmarna, precis så många som behövs för att
   komma från nuvarande SoC till 100 %. Om fönstret är för kort för att fylla batteriet planeras
   bara det som ryms, och det anges i plantexten.
4. **Sprid effekten.** Laddeffekten är den energi som ännu ska tillföras delat med tiden som
   återstår av laddtimmarna. Det håller belastningen på nätanslutningen och husets krets så låg
   som möjligt. Effekten justeras längs vägen.
5. **Klart är klart.** När laddtimmarna är över eller batteriet är fullt går Marstek
   tillbaka till anti-feed. Den startar inte igen i samma fönster och håller inte kvar laddningen.

Bara **publicerade** priser används. Planen för natten visas därför så snart
morgondagens priser är kända (hos Zonneplan mellan 13:00 och 15:00).

Exempel (10 november 2026, batteri på 12 %): billigt fönster 23:00–07:00, laddning kl. 02:00,
03:00 och 04:00 med cirka 1900 W för i snitt € 0,37, mot € 0,55–0,67 under dagen.

## Laddning vid negativt pris

Om timpriset är negativt laddar batteriet från nätet, oavsett laddningsplanen
och även när prisstyrningen är avstängd. Det har en egen brytare, som är **på som standard**.

Den tittar på hela **fönstret** av på varandra följande negativa timmar, inte bara den nuvarande
timmen, och får ut det mesta av det:

1. Den räknar ut hur mycket batteriet fortfarande kan ta emot (SoC till 100 %).
2. Den fördelar energin över timmarna **efter deras värde**: ju mer negativt priset är, desto mer
   laddas under den timmen (upp till vad en timme klarar vid maximal effekt). Exempel: tre
   negativa timmar på −€ 0,03, −€ 0,20 och −€ 0,12 och 3 kWh kvar att ladda. Timmen på −€ 0,20 får
   cirka 1,9 kWh och timmen på −€ 0,12 cirka 1,2 kWh. Timmen på −€ 0,03 skulle hamna under minsta
   laddeffekt, så den faller bort och dess andel går till de andra två.
3. Eftersom energin sprids över timmarna blir effekten lägre än om man laddade med full
   effekt en kort stund. Om batteriet kan ta emot mer än fönstret erbjuder fylls varje timme till
   maximum. En enskild timme som inte kan fylla batteriet laddas med full effekt.
4. Plantexten och flödesschemat visar fönstret, de valda timmarna, effekten och den förväntade
   vinsten (vad du får betalt för att ladda).

Alternativet *Negativt pris: fördelning av energin* växlar mellan två sätt:

- **Fördela efter värde** (standard): som beskrivet ovan, lägre effekt, något mindre
  vinst.
- **Maximal vinst**: timmarna fylls en och en, bästa priset först, var och en med full effekt, och
  resten går till nästa bästa timme. I exemplet tar timmen på −€ 0,20 2,25 kWh med full effekt
  och timmen på −€ 0,12 de återstående 0,8 kWh, vilket ger cirka € 0,55 i stället för € 0,52.
  Priset är fler korta stötar med full effekt.

Så snart priset blir positivt igen eller batteriet är fullt går Marstek tillbaka till
anti-feed. Planen räknas om varje minut; en timme som redan används får lite extra
utrymme innan den faller bort för att den ligger under minsta effekt.

Gränsen går att justera (*Negativt pris: gräns*, standard € 0,00). Priset hämtas från
prissensorn, så hos Zonneplan är det priset inklusive skatter.

## Solprognos

Med solpaneler fylls batteriet gratis under dagen. Om du laddar det fullt från nätet på
natten finns det ingen plats kvar för solöverskottet, som går till nätet för lite eller inga
pengar, vilket spelar större roll nu när nettodebiteringen (*salderingsregeling*) upphör. Därför
tar integrationen hänsyn till det förväntade solutbytet:

1. Den läser prognosen från **Energipanelen** i Home Assistant (*Inställningar → Instrumentpaneler →
   Energi → Solpaneler → Prognos för solproduktion*). Forecast.Solar, Solcast, Open-Meteo och
   andra prognosintegrationer fungerar, och inget extra behöver ställas in. Utan en prognos
   där ändras ingenting.
2. Den räknar ut det förväntade överskottet: per timme prognosen, multiplicerad med
   tillförlitlighetsinställningen (standard 70 %), minus din egen förbrukning (inställningen
   *Försäljning: genomsnittlig egen förbrukning*).
3. Den laddar på natten bara så mycket att det finns plats för det överskottet när solen
   går upp: den energi som din egen förbrukning drar fram till dess, plus det som fortfarande behövs. En
   solig dag kan det vara några kWh i stället för ett fullt batteri, eller ingenting alls (plantexten
   säger då att solen fyller batteriet).
4. En molnig dag ger litet eller inget överskott, och då laddas batteriet fullt som förut.

Det kan stängas av med *Använd solprognosen*. Prognosen läses var 30:e minut. Den
sänker bara mängden som ska laddas; den flyttar inte laddtimmar och ändrar inte försäljningen.

## Spärr under kostnadspris

Energi som laddats från nätet har ett kostnadspris: laddpriset delat med verkningsgraden. Om
batteriet gav tillbaka den energin direkt efter laddningen, under timmar som är billigare än det
kostnadspriset, skulle laddningen kosta pengar. Urladdning blockeras därför så länge:

- det finns laddat lager i batteriet (se *Vinst*), och
- timpriset är lägre än kostnadspriset för det lagret.

Huset använder då nätström, som just då är billigare än det som finns i batteriet.
Så snart priset når kostnadspriset, eller lagret är förbrukat, tar Marstek över
igen. Det här har en egen brytare, som är **på som standard**.

Tekniskt sätter integrationen den maximala urladdningseffekten (*Max. Discharge power*) till 0.
Marstek står kvar i anti-feed, så laddning från solöverskott fortsätter. Om en annan
automation sätter den effekten till ett annat värde under spärren (till exempel en begränsare för en
elbilsladdare) kommer integrationen ihåg det värdet, sätter den till 0 igen och återställer det
ihågkomna värdet efteråt.

Observera: Marstek kan inte skilja nätladdad energi från solenergi. Under en spärr
urladdas därför inte hela batteriet.

## Ingen förlust

En separat brytare (avstängd som standard) som gör integrationen sträng: energi som laddats från
nätet används eller säljs aldrig under sitt kostnadspris.

- **Spärren upprätthålls**, även om brytaren *Spärr* är avstängd.
- **Försäljning under kostnadspris blockeras.** Om det finns laddat lager i batteriet och
  säljpriset är lägre än dess kostnadspris säljs ingenting.

Varje bokförd kWh ger då minst sitt kostnadspris, så en dags vinst kan inte bli lägre än noll.
Det den inte kan utesluta:

- **Stillestånd.** Om priset ligger under kostnadspriset länge förblir batteriet
  blockerat från urladdning, även lagrad solenergi.
- **Avvikande verkningsgrad.** Kostnadspriset använder den genomsnittliga verkningsgraden. Om
  batteriet ger tillbaka mindre än så under en cykel är det tomt innan lagret i böckerna är
  förbrukat; resten förfaller utan att en förlust bokförs.
- **Slitage** på batteriet räknas inte; använd minsta vinst per kWh för det.

Integrationen räknar om direkt när en ny prisperiod börjar, så en spärr
startar aldrig upp till en minut för sent.

## Försäljning (valfritt)

Försäljning har en egen brytare och är oberoende av laddning. Bara det som verkligen blir över
säljs. En timme används för försäljning när allt det här gäller:

1. **En billig laddning är på väg**: ett laddfönster med publicerade priser ligger framför, så
   kostnaden för att ladda om är känd.
2. **Intäkten är tydligt högre än omladdningen**: säljpris ≥ laddpris delat med
   verkningsgraden, plus säljmarginalen (standard € 0,10 per kWh).
3. **Det finns överskott över reserven.** Reserven är Marsteks urladdningsgräns plus
   den förväntade egna förbrukningen fram till omladdningen (genomsnittlig huseffekt × timmar), med
   ett justerbart minimum (standard 20 %).
4. **Det är en av de dyraste timmarna** före laddfönstret.

Precis som vid laddning sprids säljeffekten över de valda timmarna. Vid reserven
upphör försäljningen och Marstek går tillbaka till anti-feed.

På vintern finns det sällan överskott: med ett 5 kWh-batteri tar den egna förbrukningen fram till nästa
laddning oftast hela laddningen. Alternativet gör mest nytta när solen fyller
batteriet och det finns en kvällsprisspik.

**Efter att nettodebiteringen upphör** (den nederländska *salderingsregeling*, 1 januari 2027) ger
inmatning mindre än timpriset. Ange då *Försäljningspris: faktor* och *avdrag*: försäljningspris =
timpris × faktor − avdrag. För det rena marknadspriset hos Zonneplan är det ungefär
0,826 och € 0,108.

## Styrning av Marstek

Integrationen styr batteriet via RS485-gränssnittet (LilyGO T-CAN485 med
ESPHome):

| Tillfälle | Kommandon |
|---|---|
| Starta laddning | sätt laddeffekt → *Forcible charge/discharge* till `charge` → *RS485 Control Mode* till `enable` |
| Under laddning | justera laddeffekten (steg om 100 W) |
| Klart, eller prisstyrning av | *RS485 Control Mode* till `disable`, forcible tillbaka till `charge`, laddeffekt tillbaka till maximum |
| Starta försäljning | sätt urladdningseffekt → forcible till `discharge` → *RS485 Control Mode* till `enable` |
| Försäljning klar, eller försäljning av | samma som klart: tillbaka till viloläget |

Tvingad **ur**laddning som du startar själv lämnas ifred. Tvingad laddning som du startar
själv återställs så länge prisstyrningen är på; stäng av den först om du vill det.

## Entiteter

| Entitet | Innehåll |
|---|---|
| `switch.*_price_control` | På: laddningsplanen genomförs. Av: Marstek styr allt själv. Att stänga av den sätter Marstek tillbaka i anti-feed direkt. |
| `switch.*_charge_at_negative_price` | På (standard): ladda alltid med full effekt när timpriset är negativt. Attribut `nu_actief`. |
| `switch.*_hold_below_cost_price` | På (standard): urladda inte medan timpriset ligger under kostnadspriset för det laddade lagret. Attribut `nu_actief`, `tot`, `voorraad_kwh`, `kostprijs`. |
| `switch.*_no_loss` | På: spärr upprätthålls och sälj aldrig under kostnadspris. Attribut `vasthouden_actief`, `verkoop_tegengehouden`, `voorraad_kwh`, `kostprijs`. |
| `switch.*_selling` | På: överskott säljs under de dyraste timmarna. Oberoende av prisstyrningen. |
| `sensor.*_sell_plan` | Tillstånd: `verkopen`, `gepland`, `geen` eller `onbekend`. Attribut: `verkoopuren`, `vermogen`, `overschot_kwh`, `reserve_soc`, `drempelprijs`, `terugkoopprijs` och `tekst`. |
| `sensor.*_charge_plan` | Tillstånd: `laden`, `gepland`, `klaar`, `vol`, `geen` eller `onbekend`. Attribut: `laaduren`, `venster`, `eind`, `uren_nodig`, `vermogen`, `klaar_tot`, `tekst` (läsbar sammanfattning) och `stroomschema` (tidslinje och kontroller för kortet). |
| `sensor.*_planned_charge_power` | Den utspridda laddeffekten i W. |
| `sensor.*_energy_to_charge` | Energi från nätet som behövs för att fylla på, i kWh. |
| `sensor.*_charge_start` / `*_charge_end` | Start och slut för den planerade laddningen. |
| `sensor.*_gain_today` / `*_gain_this_week` / `*_gain_this_month` | Realiserad vinst i euro sedan 00:00, sedan måndag 00:00 och sedan den första i månaden (se *Vinst*). Attribut: lagret och, för idag, vad som laddades och användes. |
| `sensor.*_gain_this_year` | Realiserad vinst sedan 1 januari. |
| `sensor.*_gain_last_week` | Den slutliga vinsten för föregående vecka. |
| `sensor.*_expected_gain` | Uppskattad vinst för de nuvarande planerna i euro (laddning plus försäljning); attributet `regels` innehåller uppdelningen. |
| `sensor.*_efficiency` | Den använda verkningsgraden, i procent. Attribut `bron`: uppmätt från energiräknarna eller det fasta värdet. |
| `sensor.*_average_charge_price` | Genomsnittligt pris för laddtimmarna i €/kWh. |

Namnen ovan gäller en engelskspråkig installation. Med Home Assistant inställt på svenska heter
de `*_laddningsplan`, `*_prisstyrning` och så vidare, på nederländska `*_laadplan`,
`*_prijssturing`. Tillståndsvärdena och attributnamnen är desamma på alla språk.

## Installation

1. Installera med HACS (knappen ovan, eller lägg till det här arkivet som ett eget arkiv, kategori
   *Integration*), eller kopiera `custom_components/marstek_goedkoop_laden` till
   `/config/custom_components/`. Starta om Home Assistant.
2. Gå till *Inställningar → Enheter och tjänster → Lägg till integration → Marstek Goedkoop Laden*.
3. Välj hur din Marstek är ansluten (*LilyGO RS485 med ESPHome*, *Modbus i Home Assistant* eller *Marstek Venus Modbus-integrationen*),
   därefter prissensorn och Marstek-entiteterna. Det som upptäcks fylls i på förhand. För Modbus
   anger du också namnet på din Modbus-hubb (till exempel `MarstekVenus`) och slavadressen.

Kräver Home Assistant 2026.3 eller nyare.

### Prissensor

Integrationen läser priserna från ett attribut på en sensor (standard `forecast`):

- Zonneplans timpriser: `start_date`, `end_date`, `price_tax_included.amount`
- Zonneplan (gammalt): `datetime`, `electricity_price`
- Generiskt: `start` (eller `start_time`, `datetime`) och `price` (eller `value`, `prijs`) i €/kWh

### Inställningar

Under *Konfigurera* på integrationen:

| Inställning | Standard | Betydelse |
|---|---|---|
| Språk | Automatisk | Språk för plantext, flödesschema och kort: Automatisk, Nederlands, English, Frysk, Deutsch, Français, Español, Svenska eller Norsk. |
| Batteriets inköpspris | € 0 | Används för avskrivning. 0 stänger av avskrivningen. |
| Batteriets livslängd (cykler) | 6000 | Förväntat antal fulla cykler. Avskrivning per kWh = pris ÷ (cykler × kapacitet); till exempel € 1 500 över 6 000 cykler på 5,12 kWh blir cirka € 0,049 per kWh. |
| Använd solprognosen | På | Ta hänsyn till det förväntade solutbytet från Energipanelen vid nattladdning. |
| Solprognosens tillförlitlighet | 70 % | Den del av prognosen som man räknar med. Lägre är försiktigare. |
| Minsta vinst per kWh | € 0,02 | Vad laddningen minst måste ge, efter laddförluster. Timmar som ligger mindre än en halv cent över gränsen räknas ändå, så en nästan platt natt delas inte upp på grund av en bråkdel av en cent. |
| Antal dyraste timmar att jämföra med | 6 | Hur många dyra timmar senare på dagen en timme jämförs med. |
| Antal timmar att se framåt | 18 | Hur långt efter en timme som man letar efter dyra timmar. |
| Minsta antal kända timmar framåt | 8 | Timmar med färre kända priser efter sig räknas inte med. |
| Minsta laddeffekt | 400 W | Nedre gräns vid utspridning. |
| Verkningsgrad när räknarna saknas | 0,77 | Verkningsgraden beräknas från Marsteks energiräknare (total urladdad ÷ total laddad, begränsad till 70–95 %). Det fasta värdet gäller bara när de räknarna saknas. Verkningsgraden för enbart laddning eller enbart urladdning är dess kvadratrot. |
| Batterikapacitet | 5,12 kWh | Används bara när ingen kapacitetssensor är angiven. |
| Negativt pris: gräns | € 0,00 | Under detta timpris laddar batteriet med full effekt. |
| Försäljning: minsta vinst per kWh | € 0,10 | Vad försäljningen minst måste ge efter omladdning. |
| Försäljning: genomsnittlig egen förbrukning | 400 W | Avgör reserven fram till omladdning. |
| Försäljning: minsta reserv | 20 % | Inget säljs under denna SoC. |
| Försäljningspris: faktor och avdrag | 1 och € 0 | Försäljningspris = timpris × faktor − avdrag. |

Den maximala laddeffekten (Marsteks *Max. Charge power*) avgör antalet laddtimmar. Sätt den
lägre så planeras fler timmar och laddningen blir mjukare.

## Instrumentpanel

### Kort från integrationen

Integrationen levererar sju kort; ingen resurs behöver läggas till. Uppdatera webbläsaren
efter installation eller uppdatering. Varje kort kan ställas in i kortredigeraren (den visuella
redigeraren) liksom i YAML, och om du utelämnar `entity` hittas laddningsplanens sensor automatiskt.

| Kort | Innehåll |
|---|---|
| `custom:marstek-goedkoop-laden-card` | Flödesschema: dagens tidslinje och, per del (laddning, försäljning, negativt pris, spärr), vilka kontroller som klaras och var det stannar. |
| `custom:marstek-goedkoop-laden-compact-card` | Samma sak i några få rader: tidslinjen, utfallet per del med skälet, och en rad med vinsten. |
| `custom:marstek-goedkoop-laden-opbrengst-card` | Bara vinsten: idag, denna vecka, förra veckan, denna månad och förväntan för den nuvarande planen. |
| `custom:marstek-goedkoop-laden-schakelaars-card` | Kompakt: knappar för att slå på eller av laddning, försäljning, laddning vid negativt pris, spärr och ingen förlust. |
| `custom:marstek-goedkoop-laden-status-card` | Vad som händer nu, laddningsnivån som en stapel, priset nu och nästa steg. |
| `custom:marstek-goedkoop-laden-prijzen-card` | Prisdiagram utan extra kort: timmarna med laddning, försäljning och negativa priser markerade, och en linje för nu. |
| `custom:marstek-goedkoop-laden-voorraad-card` | Det laddade lagret, dess kostnadspris, verkningsgraden, avskrivningen per kWh och kapaciteten. |

```yaml
type: custom:marstek-goedkoop-laden-card
entity: sensor.marstek_goedkoop_laden_laadplan   # valfritt
title: Prisstyrning                              # valfritt
opbrengst: false                                 # valfritt, se nedan
```

Vinstkortet kan anpassas, i YAML eller i kortredigeraren:

```yaml
type: custom:marstek-goedkoop-laden-opbrengst-card
tiles: [vandaag, maand, jaar]   # valfria av: vandaag, week, vorige_week, maand, jaar, verwacht (i denna ordning)
expected_details: false         # dölj raderna per del av planen (standard: true)
notes: false                    # dölj anteckningen under kortet (standard: true)
```

| Alternativ | Standard | Betydelse |
|---|---|---|
| `tiles` | alla sex | Vilka rutor som visas och i vilken ordning: idag, denna vecka, förra veckan, denna månad, i år, förväntat (plan). |
| `expected_details` | `true` | Raderna med den förväntade vinsten per del (laddning, försäljning). |
| `notes` | `true` | Anteckningen med det laddade lagret, vad som laddades idag och avskrivningen. |

Alternativ för de andra korten (alla finns också i kortredigeraren):

| Kort | Alternativ | Standard | Betydelse |
|---|---|---|---|
| flöde, kompakt | `show_timeline` | `true` | Visa dagens tidslinje. |
| flöde, kompakt, brytare | `lanes` | alla fem | Vilka delar som visas: `bijladen`, `verkoop`, `negatief`, `vasthouden`, `geen_verlies`. |
| status | `show_soc`, `show_price`, `show_next` | `true` | Stapeln för laddningsnivån, priset nu, nästa steg. |
| priser | `hours_back` | `2` | Timmar bakåt i tiden att visa. |
| priser | `hours_ahead` | `0` | Timmar framåt att visa; 0 är till det sista kända priset. |
| priser | `show_values` | `false` | Skriv ut priset ovanför varje stapel (upp till 24 staplar). |
| priser | `height` | `140` | Diagrammets höjd i pixlar. |
| lager | `tiles` | alla fem | `voorraad`, `kostprijs`, `rendement`, `afschrijving`, `capaciteit`. |
| lager | `notes` | `true` | Anteckningen under kortet. |

`opbrengst` avgör om flödeskortet också visar vinsten: avstängt som standard för det vanliga
kortet, en rad som standard för det kompakta kortet. I flödesschemat är grönt en kontroll som
klaras, rött är kontrollen där det stannar och streckat är ett utfall där ingenting händer. Alla
kort läser attributet `stroomschema` på laddningsplanens sensor.

## Vinst

**Avskrivning.** Om du anger ett inköpspris kostar varje kWh som batteriet urladdar lite slitage: pris ÷ (cykler × kapacitet). Det dras från den realiserade vinsten (idag, vecka, månad), räknas med i den förväntade vinsten och används i besluten: en timme är bara värd att ladda om den fortfarande slår slitaget, försäljning kräver slitaget utöver säljmarginalen, och *Spärr* och *Ingen förlust* behandlar kostnadspris plus slitage som break-even-pris. Med ett pris på 0 (standard) ändras ingenting.

Det finns två sorters vinst: vad den nuvarande planen förväntas ge, och vad som faktiskt
har tjänats in.

### Förväntad (uppskattning i förväg)

- **Laddning**: vad energin som ska köpas kostar, mot vad den är värd senare. Det värdet är
  verkningsgraden gånger genomsnittspriset för de dyra timmarna som laddtimmen jämfördes med.
- **Försäljning**: intäkten från överskottet, minus vad omladdningen kostar.

Under en laddning räknas bara det som fortfarande ska laddas.

### Idag och denna vecka (realiserad)

1. Energi som integrationen laddar från nätet (laddningsplan eller negativt pris) blir
   **lager**: användbara kWh = laddade kWh × verkningsgrad, med som kostnadspris vad den energin kostade
   vid det tillfället.
2. Om batteriet sedan urladdar för egen förbrukning används det lagret först. Vinsten är
   `urladdade kWh × (elpris vid det tillfället − kostnadspris per användbar kWh)`.
3. Vid försäljning är vinsten `sålda kWh × säljpris − kostnadspris`; för energi som inte
   kommer från lagret (solenergi) är kostnadspriset vad omladdningen kostar.
4. **Idag** är summan sedan 00:00, **denna vecka** sedan måndag 00:00 och **denna månad** sedan den första i månaden. **Förra veckan** är det slutliga beloppet för veckan före.

Det som fortfarande ligger i lagret är inte intjänat än och räknas först när det används. Energi
som solen lägger i batteriet och som du använder själv senare räknas inte: Marstek
gör det även utan den här integrationen. Beloppen kommer från Marsteks energiräknare
och timpriset vid det tillfället; ett räknarhopp efter ett fel bokförs inte.

### Separata kort

Planrad (Markdown-kort):

```yaml
type: markdown
content: >-
  **Laddningsplan:** {{ state_attr('sensor.marstek_goedkoop_laden_laadplan', 'tekst') }}
  {% if is_state('switch.marstek_goedkoop_laden_prijssturing', 'off') %}
  · ⚠️ prisstyrningen är **av**{% endif %}
```

## Utveckling

Beräkningsregeln ligger separat från Home Assistant i `planner.py` och har tester med
verkliga priser. Styrlogiken testas mot en fejkad Home Assistant
(`tests/test_sturing.py`):

```bash
python3 -m unittest discover -s tests -v
```


## Ändringslogg

Se [CHANGELOG.md](CHANGELOG.md) (engelska), inklusive de brytande ändringarna.

## Licens

Apache 2.0, se [LICENSE](LICENSE).
