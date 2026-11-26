<img src="custom_components/marstek_goedkoop_laden/brand/icon.png" width="96" align="right" alt="">

# Marstek Goedkeap Lade foar Home Assistant

[🇬🇧 English](README.md) · [🇳🇱 Nederlands](README.nl.md) · 🏳️ Frysk · [🇩🇪 Deutsch](README.de.md) · [🇫🇷 Français](README.fr.md) · [🇪🇸 Español](README.es.md) · [🇸🇪 Svenska](README.sv.md) · [🇳🇴 Norsk](README.nb.md)

[![Open your Home Assistant instance and open this repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=rvdwal1991&repository=Marstek-Cheap-Charging-for-HA&category=integration)
[![Open your Home Assistant instance and start setting up the integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=marstek_goedkoop_laden)

Laadt in Marstek Venus-thúsbatterij by yn de goedkeapste oeren fan in dynamysk
stroomkontrakt, sadat er fol is foardat de stroom djoer wurdt.

It útgongspunt is **selsfoarsjennend wêze**. De batterij bliuwt gewoan sels regelje (anti-feed,
nul op de mjitter). Dizze yntegraasje docht mar ien ding derby: yn de goedkeapste oeren út it
net bylade. Dêrneist is der in aparte opsje, standert útsetten, om yn de djoerste oeren
**oerskot te ferkeapjen**.

> **Hardware en kompatibiliteit.** De yntegraasje stjoert in Marstek Venus oan fia de RS485-bestjoeringsregisters.
> Allinnich de earste rige is op in echte accu draaid:
>
> | Keppeling | Model | Status |
> |---|---|---|
> | LilyGO T-CAN485 + ESPHome (RS485) | Venus E v2 | **Test** op echte hardware (de opset wêrop't er boud is) |
> | Modbus-hub yn Home Assistant, fia RS485-nei-TCP-converter (Elfin EW11 en fergelykbere) | Venus E v1/v2 | Allinnich test mei neimakke oanroppen |
> | Modbus-hub yn Home Assistant, rjochtstreeks fia Ethernet | Venus E v3 | Allinnich test mei neimakke oanroppen |
> | Yntegraasje *Marstek Venus Modbus* (ViperRNMC) | Venus E v3 | Allinnich test mei neimakke oanroppen |
> | Ien fan hjirboppe | Venus A, Venus D, oare modellen | **Net kontrolearre, net test.** Se soene de bestjoeringsregisters diele, mar dat is net ferifiearre. Stel de accukapasiteit yn by de opsjes (standert 5,12 kWh). |
> | Cloud, app of oare yntegraasjes | alle | Net stipe |
>
> De keppelingen yn detail:
>
> - **LilyGO T-CAN485 mei ESPHome** fia RS485, mei de konfiguraasje fan
>   [MarstekVenus-LilygoRS485](https://github.com/Superduper1969/MarstekVenus-LilygoRS485). Dit is de
>   opset wêrop't de yntegraasje boud is en wêrmei't er test is. Hy brûkt de entiteiten dy't
>   dizze opset leveret: *RS485 Control Mode*, *Forcible Charge/Discharge*, *Forcible Charge Power*
>   (ferplicht) en, opsjoneel, *Max. Charge Power*, *Max. Discharge Power*, *Forcible Discharge
>   Power*, *Discharging Cutoff Capacity* en de totaaltellers fan laden en ûntladen enerzjy.
> - **Modbus yn Home Assistant**, mei in Modbus-hub dy't do sels yn `configuration.yaml` sette:
>   in Elfin EW11 of in oare RS485-nei-TCP-converter
>   ([MarstekVenus-ElfinEW11](https://github.com/Superduper1969/MarstekVenus-ElfinEW11)), of de
>   **Venus E v3 rjochtstreeks fia Ethernet** (Modbus TCP, poarte 502, unit 1, EMS V144 of nijer;
>   [MarstekVenusV3-modbus-TCP-IP](https://github.com/fonske/MarstekVenusV3-modbus-TCP-IP)). De
>   yntegraasje lêst de registersensoren fan dy opset en skriuwt de registers 42000 (RS485-bestjoering),
>   42010 (twangmodus), 42020/42021 (twongen laad-/ûntladefermogen) en, as do de sensoren opjefst,
>   44002/44003 (maksimaal laad-/ûntladefermogen) mei `modbus.write_register`. Mei it maksimale
>   ûntladefermogen wurkje *Fêsthâlde* en *Gjin ferlies* ek, sûnder net. De Venus E v3 hat it
>   laadnivo yn register 34002 (skaal 0,1), net yn 32104.
> - **De yntegraasje *Marstek Venus Modbus***
>   ([ViperRNMC/marstek_venus_modbus](https://github.com/ViperRNMC/marstek_venus_modbus)), dy't ek
>   Modbus TCP praat (Ethernet by in Venus E v3, of in RS485-gateway). Kies dit as do dy
>   yntegraasje al brûkst: sy leveret de entiteiten (`switch` RS485-bestjoering, `select` twangmodus,
>   `number` fermogens). Set dêr earst de skeakeler *RS485 control mode* en de select *Force mode*
>   oan, se steane standert út.
>
> De opsjes Modbus en Marstek Venus Modbus binne **nij en oant no ta allinnich test mei neimakke
> oanroppen, net op echte hardware**.
>
> Oare manieren om de accu te keppeljen (cloud, oare yntegraasjes) binne net test en wurkje
> wierskynlik net, omdat se dizze RS485-bestjoering net bean.
>
> **Dynamyske enerzjyprizen:** dizze yntegraasje hat allinnich sin mei in **dynamysk stroomkontrakt**,
> dêr't de priis alle oere feroaret. Hy laadt yn de goedkeapste oeren en mijt de djoere, dus by in
> fêst taryf is der neat te winnen. Hy is boud om de Nederlânske merk en de prizen fan
> Zonneplan hinne (oerenprizen, foar de oare dei publisearre tusken 13:00 en 15:00). Eltse priissensor
> mei in oerenpriislist as attribút is genôch, sjoch [Priissensor](#priissensor).
>
> **Taal:** de planrigel, it stroomskema en de kaarten folgje de opsje *Taal* (Automatysk,
> Nederlands, English, Frysk, Deutsch, Français, Español, Svenska of Norsk;
> automatysk folget Home Assistant as dat ien fan dizze is, oars Ingelsk). Entiteitsnammen folgje de taal fan Home Assistant. Steatwearden en attribútnammen (`laden`, `tekst`, …) steane fêst.

## Wat er docht

1. **Betellet bylade út?** In oere is goedkeap genôch as de priis leger is as
   `rendemint × (gemiddelde fan de 6 djoerste oeren yn de 18 oeren dêrnei) − marzje`.
   It rendemint (hinne en wer, laden en ûntladen, sa'n 77 % by myn apparaat) wurdt metten
   út de enerzjytellers fan de Marstek.
2. **Finster.** It earste blok goedkeape oeren is it laadfinster. Ien of twa oeren dy't
   krekt net goedkeap genôch binne, brekke it blok net; der wurdt allinnich yn de goedkeape
   oeren sels laden.
3. **Laadoeren.** Binnen dat finster kiest er de goedkeapste oeren, krekt safolle as nedich binne
   om fan it hjoeddeistige SoC nei 100 % te kommen. Is it finster te koart om de batterij fol te
   krijen, dan plant er allinnich wat der yn past en seit dat yn de planrigel.
4. **Fermogen ferspriede.** It laadfermogen is de enerzjy dy't noch by moat, dield troch de tiid dy't der
   fan de laadoeren noch oer is. Dat hâldt de belêsting fan de netoansluting en de groep yn
   it hûs sa leech mooglik. It fermogen wurdt ûnderweis oanpast.
5. **Klear is klear.** As de laadoeren foarby binne of de batterij fol is, giet de Marstek
   werom nei anti-feed. Hy begjint net opnij yn itselde finster en hâldt de lading net fêst.

Der wurde allinnich **publisearre** prizen brûkt. It plan foar de nacht ferskynt dus sadree't
de prizen fan moarn bekend binne (by Zonneplan tusken 13:00 en 15:00).

Foarbyld (10 novimber 2026, batterij op 12 %): goedkeap finster 23:00–07:00, laden om 02:00,
03:00 en 04:00 op sa'n 1900 W foar gemiddeld € 0,37, tsjin € 0,55–0,67 oerdeis.

## Lade by in negative priis

As de oerepriis negatyf is, laadt de batterij út it net, los fan it laadplan
en ek as de priissturing út stiet. Dit hat in eigen skeakeler, **standert oan**.

Der wurdt sjoen nei it hiele **finster** fan opienfolgjende negative oeren, net allinnich nei it hjoeddeistige oere, en
dêr wurdt it measte fan makke:

1. Der wurdt útrekkene hoefolle de batterij noch kwyt kin (SoC oant 100 %).
2. Dy enerzjy wurdt oer de oeren ferdield **nei harren wearde**: hoe negatiever de priis, hoe mear
   der yn dat oere laden wurdt (oant wat in oere oan kin op it maksimale fermogen). Foarbyld: trije
   negative oeren fan −€ 0,03, −€ 0,20 en −€ 0,12 en noch 3 kWh te laden. It oere fan −€ 0,20 krijt
   sa'n 1,9 kWh en it oere fan −€ 0,12 sa'n 1,2 kWh. It oere fan −€ 0,03 soe ûnder it minimale
   laadfermogen bliuwe, dus dat falt ôf en syn oanpart giet nei de oare twa.
3. Omdat de enerzjy oer de oeren ferspraat wurdt, bliuwt it fermogen leger as in koart skoftke op
   fol fermogen laden. Kin de batterij mear oan as it finster biedt, dan wurdt eltse oere
   oant it maksimum fol. In inkeld oere dat de batterij net fol krijt, wurdt op fol fermogen laden.
4. De planrigel en it stroomskema litte it finster, de keazen oeren, it fermogen en de ferwachte
   opbringst sjen (wat dy betelle wurdt om te laden).

De opsje *Negative priis: ferdieling fan de enerzjy* wikselet tusken twa manieren:

- **Nei wearde ferdiele** (standert): sa't hjirboppe beskreaun, leger fermogen, wat minder opbringst.
- **Maksimale opbringst**: de oeren wurde ien foar ien fol makke, bêste priis earst, elk op fol
  fermogen, en de rest giet nei it folgjende bêste oere. Yn it foarbyld nimt it oere fan −€ 0,20
  2,25 kWh op fol fermogen op en it oere fan −€ 0,12 de oerbleaune 0,8 kWh, wat sa'n € 0,55
  opbringt yn plak fan € 0,52. De priis is mear koarte stoaten op fol fermogen.

Sadree't de priis wer posityf wurdt of de batterij fol is, giet de Marstek werom nei
anti-feed. It plan wurdt elke minút opnij berekkene; in oere dat al yn gebrûk wie, krijt in bytsje ekstra
romte foardat er ôffalt omdat er ûnder it minimale fermogen sit.

De grins is ynstelber (*Negative priis: grins*, standert € 0,00). De priis komt fan de
priissensor, dus by Zonneplan is dat de priis ynklusyf belesting.

## Sinneprognose

Mei sinnepanielen wurdt de batterij oerdeis fergees fol. As do him yn de nacht fol út it net
laadst, hat it sinne-oerskot gjin romte mear en giet it foar lyts of neat nei it net,
wat mear útmakket no't de salderingsregeling (*salderingsregeling*) ophâldt. Dus
hâldt de yntegraasje rekken mei de ferwachte sinne-opbringst:

1. Hy lêst de prognose út it **Enerzjydashboerd** fan Home Assistant (*Ynstellingen → Dashboerden →
   Enerzjy → Sinnepanielen → Prognose sinneproduksje*). Forecast.Solar, Solcast, Open-Meteo en
   oare prognoseyntegraasjes wurkje, en der hoecht neat ekstra ynsteld te wurden. Sûnder in prognose
   dêr feroaret der neat.
2. Hy rekkenet it ferwachte oerskot út: per oere de prognose, kear de ynstelling foar
   betrouberens (standert 70 %), minus dyn eigen ferbrûk (de ynstelling *Ferkeapje: gemiddeld eigen
   ferbrûk*).
3. Hy laadt yn de nacht mar safolle dat der romte is foar dat oerskot as de sinne
   opkomt: de enerzjy dy't dyn eigen ferbrûk oant dan opmakket, plus wat der noch nedich is. Op in
   sinnige dei kin dat in pear kWh wêze yn plak fan in folle batterij, of hielendal neat (de planrigel
   seit dan dat de sinne de batterij folt).
4. In bewolkte dei jout in lyts of gjin oerskot, en dan wurdt de batterij lykas earder fol laden.

Dit kin útset wurde mei *Sinneprognose brûke*. De prognose wurdt alle 30 minuten lêzen. Hy
ferleget allinnich de te laden hoemannichte; hy ferpleatst gjin laadoeren en feroaret neat oan ferkeapjen.

## Fêsthâlde ûnder de kostpriis

Enerzjy dy't út it net laden is hat in kostpriis: de laadpriis dield troch it rendemint. As
de batterij dy enerzjy fuortdaliks nei it laden werom joech, yn oeren dy't goedkeaper binne as dy
kostpriis, dan soe laden jild kostje. Ûntlade wurdt dêrom blokkearre salang't:

- der byladen foarried yn de batterij sit (sjoch *Opbringst*), en
- de oerepriis leger is as de kostpriis fan dat foarried.

It hûs brûkt dan netstroom, dy't op dat momint goedkeaper is as wat der yn de batterij sit.
Sadree't de priis de kostpriis berikt, of it foarried opmakke is, nimt de Marstek it wer oer.
Dit hat in eigen skeakeler, **standert oan**.

Technysk set de yntegraasje it maksimale ûntladefermogen (*Max. Discharge power*) op 0.
De Marstek bliuwt yn anti-feed, dus laden út sinneoerskot giet gewoan troch. As in oare
automatisearring dat fermogen tidens it fêsthâlden op in oare wearde set (bygelyks in begrinzer foar in
EV-lader), ûnthâldt de yntegraasje dy wearde, set it wer op 0 en jout letter de
ûnthâlden wearde werom.

Let op: de Marstek kin enerzjy út it net net ûnderskiede fan sinne-enerzjy. Tidens it fêsthâlden
wurdt de hiele batterij dus net ûntladen.

## Gjin ferlies

In aparte skeakeler (standert út) dy't de yntegraasje strang makket: enerzjy dy't út it net
laden is wurdt nea ûnder de kostpriis brûkt of ferkocht.

- **Fêsthâlde wurdt ôfdwongen**, ek as de skeakeler *Fêsthâlde* út stiet.
- **Ferkeapje ûnder de kostpriis wurdt blokkearre.** As der byladen foarried yn de batterij sit en de
  ferkeappriis leger is as de kostpriis dêrfan, wurdt der neat ferkocht.

Elke boekte kWh bringt dan minstens syn kostpriis op, sadat de winst fan in dei net ûnder nul kin.
Wat it net útslute kin:

- **Stilstân.** As de priis lang ûnder de kostpriis bliuwt, bliuwt de batterij
  blokkearre foar ûntlade, ek foar bewarre sinne-enerzjy.
- **Ôfwikend rendemint.** De kostpriis brûkt it gemiddelde rendemint. As de batterij yn in syklus
  minder werom jout, is er leech foardat it foarried yn de boeken opmakke is; de rest
  ferfalt sûnder dat der in ferlies boekt wurdt.
- **Sliten** fan de batterij wurdt net meirekkene; brûk dêrfoar de minimale winst per kWh.

De yntegraasje rekkenet fuortdaliks opnij as in nije priisperioade begjint, sadat in fêsthâlden
nea oant in minút te let ynset.

## Ferkeapje (opsjoneel)

Ferkeapje hat in eigen skeakeler en is ûnôfhinklik fan laden. Der wurdt allinnich ferkocht wat echt oer is. In oere wurdt
brûkt om te ferkeapjen as dit alles opgiet:

1. **In goedkeap laden komt der oan**: der leit in laadfinster mei publisearre prizen foarút, sadat de kosten
   fan weromlade bekend binne.
2. **De opbringst is dúdlik heger as weromlade**: ferkeappriis ≥ laadpriis dield troch it
   rendemint, plus de ferkeapmarzje (standert € 0,10 per kWh).
3. **Der is oerskot boppe de reserve.** De reserve is de ûntladegrins fan de Marstek plus
   it ferwachte eigen ferbrûk oant it weromlade (gemiddeld húsfermogen × oeren), mei in
   ynstelber minimum (standert 20 %).
4. **It is ien fan de djoerste oeren** foar it laadfinster.

Lykas by it laden wurdt it ferkeapfermogen oer de keazen oeren ferspraat. Oan de reserve
hâldt it ferkeapjen op en giet de Marstek werom nei anti-feed.

Yn de winter is der selden oerskot: mei in batterij fan 5 kWh slokt it eigen ferbrûk oant de folgjende
lading meastal de hiele lading op. De opsje docht benammen wat as de sinne de batterij
fol makket en der in jûnspriispiek is.

**Nei it ein fan de salderingsregeling** (de Nederlânske *salderingsregeling*, 1 jannewaris 2027) bringt weromlevering
minder op as de oerepriis. Stel dan *Ferkeappriis: faktor* en *ôftrek* yn: ferkeappriis =
oerepriis × faktor − ôftrek. Foar de kale merkpriis by Zonneplan is dat sa'n
0,826 en € 0,108.

## Oanstjoering fan de Marstek

De yntegraasje stjoert de batterij oan fia de RS485-ynterface (LilyGO T-CAN485 mei
ESPHome):

| Momint | Kommando's |
|---|---|
| Begjin mei laden | laadfermogen sette → *Forcible charge/discharge* op `charge` → *RS485 Control Mode* op `enable` |
| Tidens it laden | laadfermogen oanpasse (stappen fan 100 W) |
| Klear, of priissturing út | *RS485 Control Mode* op `disable`, forcible werom op `charge`, laadfermogen werom op it maksimum |
| Begjin mei ferkeapjen | ûntladefermogen sette → forcible op `discharge` → *RS485 Control Mode* op `enable` |
| Ferkeapjen klear, of ferkeapjen út | itselde as klear: werom nei de rêststân |

Twongen **ût**laden dat do sels begjinst, wurdt oerlitten. Twongen laden dat do sels
begjinst, wurdt weromset salang't de priissturing oan stiet; set dy earst út as do dat wolst.

## Entiteiten

| Entiteit | Ynhâld |
|---|---|
| `switch.*_price_control` | Oan: it laadplan wurdt útfierd. Út: de Marstek regelet alles sels. Útsette set de Marstek fuortdaliks werom yn anti-feed. |
| `switch.*_charge_at_negative_price` | Oan (standert): altyd op fol fermogen laden as de oerepriis negatyf is. Attribút `nu_actief`. |
| `switch.*_hold_below_cost_price` | Oan (standert): net ûntlade salang't de oerepriis ûnder de kostpriis fan it byladen foarried leit. Attributen `nu_actief`, `tot`, `voorraad_kwh`, `kostprijs`. |
| `switch.*_no_loss` | Oan: fêsthâlde ôfdwongen en nea ûnder de kostpriis ferkeapje. Attributen `vasthouden_actief`, `verkoop_tegengehouden`, `voorraad_kwh`, `kostprijs`. |
| `switch.*_selling` | Oan: oerskot wurdt yn de djoerste oeren ferkocht. Ûnôfhinklik fan priissturing. |
| `sensor.*_sell_plan` | Steat: `verkopen`, `gepland`, `geen` of `onbekend`. Attributen: `verkoopuren`, `vermogen`, `overschot_kwh`, `reserve_soc`, `drempelprijs`, `terugkoopprijs` en `tekst`. |
| `sensor.*_charge_plan` | Steat: `laden`, `gepland`, `klaar`, `vol`, `geen` of `onbekend`. Attributen: `laaduren`, `venster`, `eind`, `uren_nodig`, `vermogen`, `klaar_tot`, `tekst` (lêsbere gearfetting) en `stroomschema` (tiidline en kontrôles foar de kaart). |
| `sensor.*_planned_charge_power` | It ferspraat laadfermogen yn W. |
| `sensor.*_energy_to_charge` | Enerzjy út it net dy't nedich is om fol te kommen, yn kWh. |
| `sensor.*_charge_start` / `*_charge_end` | Begjin en ein fan de plande bylade. |
| `sensor.*_gain_today` / `*_gain_this_week` / `*_gain_this_month` | Realisearre opbringst yn euro's sûnt 00:00, sûnt moandei 00:00 en sûnt de earste fan de moanne (sjoch *Opbringst*). Attributen: it foarried en, foar hjoed, wat der laden en brûkt is. |
| `sensor.*_gain_this_year` | Realisearre opbringst sûnt 1 jannewaris. |
| `sensor.*_gain_last_week` | De definitive opbringst fan de foarige wike. |
| `sensor.*_expected_gain` | Rûsde opbringst fan de hjoeddeistige plannen yn euro's (laden plus ferkeapjen); attribút `regels` befettet de útsplitsing. |
| `sensor.*_efficiency` | It brûkte rendemint, yn prosinten. Attribút `bron`: metten út de enerzjytellers of de fêste wearde. |
| `sensor.*_average_charge_price` | Gemiddelde priis fan de laadoeren yn €/kWh. |

De nammen hjirboppe hearre by in Ingelsktalige ynstallaasje. Stiet Home Assistant op Nederlânsk, dan
hjitte se `*_laadplan`, `*_prijssturing` ensafuorthinne. De steatwearden en attribútnammen
binne yn beide talen itselde.

## Ynstallaasje

1. Ynstallearje mei HACS (knop hjirboppe, of foegje dit repository ta as oanpast repository, kategory
   *Integration*), of kopiearje `custom_components/marstek_goedkoop_laden` nei
   `/config/custom_components/`. Start Home Assistant opnij.
2. Gean nei *Ynstellingen → Apparaten en tsjinsten → Yntegraasje tafoegje → Marstek Goedkoop Laden*.
3. Kies hoe dyn Marstek keppele is (*LilyGO RS485 mei ESPHome*, *Modbus yn Home Assistant* of *Marstek Venus Modbus-yntegraasje*),
   dan de priissensor en de Marstek-entiteiten. Wat herkend wurdt, stiet al ynfolle. By Modbus
   joust do ek de namme fan dyn Modbus-hub op (bygelyks `MarstekVenus`) en it slave-adres.

Fereasket Home Assistant 2026.3 of nijer.

### Priissensor

De yntegraasje lêst de prizen út in attribút fan ien sensor (standert `forecast`):

- Zonneplan-oerenprizen: `start_date`, `end_date`, `price_tax_included.amount`
- Zonneplan (âld): `datetime`, `electricity_price`
- Algemien: `start` (of `start_time`, `datetime`) en `price` (of `value`, `prijs`) yn €/kWh

### Ynstellingen

Ûnder *Konfigurearje* by de yntegraasje:

| Ynstelling | Standert | Betsjutting |
|---|---|---|
| Taal | Automatysk | Taal fan planrigel, stroomskema en kaarten: Automatysk, Nederlands, English, Frysk, Deutsch, Français, Español, Svenska of Norsk. |
| Oankeappriis accu | € 0 | Foar de ôfskriuwing. 0 set de ôfskriuwing út. |
| Libbensdoer accu (syklussen) | 6000 | Ferwachte oantal folsleine syklussen. Ôfskriuwing per kWh = priis ÷ (syklussen × kapasiteit); bygelyks € 1.500 oer 6.000 syklussen fan 5,12 kWh is sa'n € 0,049 per kWh. |
| Sinneprognose brûke | Oan | Hâld by it laden yn de nacht rekken mei de ferwachte sinne-opbringst út it Enerzjydashboerd. |
| Betrouberens fan de sinneprognose | 70 % | It part fan de prognose dêr't op rekkene wurdt. Leger is foarsichtiger. |
| Minimale winst per kWh | € 0,02 | Wat laden nei ôftrek fan it laadferlies minstens opbringe moat. Oeren dy't minder as in heale sint boppe de grins lizze telle ek mei, sadat in hast platte nacht net om in fraksje fan in sint opsnipele wurdt. |
| Oantal djoerste oeren om mei te fergelykjen | 6 | Mei hoefolle djoere oeren letter op de dei in oere fergelike wurdt. |
| Oantal oeren foarút sjen | 18 | Hoe fier foarby in oere sjoen wurdt nei djoere oeren. |
| Minimaal oantal bekende oeren foarút | 8 | Oeren mei minder bekende prizen dêrnei wurde negearre. |
| Minimaal laadfermogen | 400 W | Legere grins by it ferspriede. |
| Rendemint as de tellers ûntbrekke | 0,77 | It rendemint wurdt berekkene út de enerzjytellers fan de Marstek (totaal ûntladen ÷ totaal laden, begrinzge op 70–95 %). Dizze fêste wearde jildt allinnich as dy tellers ûntbrekke. It rendemint fan allinnich laden of allinnich ûntlade is de woartel dêrfan. |
| Accukapasiteit | 5,12 kWh | Allinnich brûkt as der gjin kapasiteitssensor ynsteld is. |
| Negative priis: grins | € 0,00 | Ûnder dizze oerepriis laadt de batterij op fol fermogen. |
| Ferkeapje: minimale winst per kWh | € 0,10 | Wat ferkeapje nei weromlade minstens opbringe moat. |
| Ferkeapje: gemiddeld eigen ferbrûk | 400 W | Bepaalt de reserve oant it weromlade. |
| Ferkeapje: minimale reserve | 20 % | Ûnder dizze SoC wurdt neat ferkocht. |
| Ferkeappriis: faktor en ôftrek | 1 en € 0 | Ferkeappriis = oerepriis × faktor − ôftrek. |

It maksimale laadfermogen (de *Max. Charge power* fan de Marstek) bepaalt it oantal laadoeren.
Set it leger en der wurde mear oeren plend en der wurdt rêstiger laden.

## Dashboard

### Kaarten fan de yntegraasje

De yntegraasje leveret sân kaarten mei; der hoecht gjin resource tafoege te wurden. Fernij de
browser nei it ynstallearjen of bywurkjen. Elke kaart is yn te stellen yn de kaarteditor (de
fisuele editor) en yn YAML, en as do `entity` weilitst, wurdt de laadplan-sensor automatysk fûn.

| Kaart | Ynhâld |
|---|---|
| `custom:marstek-goedkoop-laden-card` | Stroomskema: de tiidline fan hjoed en per ûnderdiel (bylade, ferkeap, negative priis, fêsthâlde) hokker kontrôles slagje en op hokker it stopt. |
| `custom:marstek-goedkoop-laden-compact-card` | Itselde yn in pear rigels: de tiidline, per ûnderdiel de útkomst mei de reden, en ien rigel mei de opbringst. |
| `custom:marstek-goedkoop-laden-opbrengst-card` | Allinnich de opbringst: hjoed, dizze wike, foarige wike, dizze moanne en de ferwachting fan it hjoeddeistige plan. |
| `custom:marstek-goedkoop-laden-schakelaars-card` | Kompakt: knoppen om bylade, ferkeap, lade by negative priis, fêsthâlde en gjin ferlies oan of út te setten. |
| `custom:marstek-goedkoop-laden-status-card` | Wat der no bart, it laadnivo as balke, de priis no en de folgjende stap. |
| `custom:marstek-goedkoop-laden-prijzen-card` | Priisgrafyk sûnder ekstra kaarten: de oeren mei laden, ferkeapjen en negative prizen markearre, en in line foar no. |
| `custom:marstek-goedkoop-laden-voorraad-card` | It byladen foarried, de kostpriis dêrfan, it rendemint, de ôfskriuwing per kWh en de kapasiteit. |

```yaml
type: custom:marstek-goedkoop-laden-card
entity: sensor.marstek_goedkoop_laden_laadplan   # opsjoneel
title: Priissturing                              # opsjoneel
opbrengst: false                                 # opsjoneel, sjoch hjirûnder
```

De opbringstkaart is oan te passen, yn YAML of yn de kaarteditor:

```yaml
type: custom:marstek-goedkoop-laden-opbrengst-card
tiles: [vandaag, maand, jaar]   # kies út: vandaag, week, vorige_week, maand, jaar, verwacht (yn dizze folchoarder)
expected_details: false         # ferberch de rigels per ûnderdiel fan it plan (standert: true)
notes: false                    # ferberch de taljochting ûnder de kaart (standert: true)
```

| Opsje | Standert | Betsjutting |
|---|---|---|
| `tiles` | alle seis | Hokker tegels en yn hokker folchoarder: hjoed, dizze wike, foarige wike, dizze moanne, dit jier, ferwachte (plan). |
| `expected_details` | `true` | De rigels mei de ferwachte opbringst per ûnderdiel (laden, ferkeapjen). |
| `notes` | `true` | De taljochting mei it byladen foarried, wat der hjoed laden is en de ôfskriuwing. |

Opsjes fan de oare kaarten (se steane ek allegearre yn de kaarteditor):

| Kaart | Opsje | Standert | Betsjutting |
|---|---|---|---|
| stroomskema, kompakt | `show_timeline` | `true` | De tiidline fan hjoed sjen litte. |
| stroomskema, kompakt, skeakelers | `lanes` | alle fiif | Hokker ûnderdielen sjen litte: `bijladen`, `verkoop`, `negatief`, `vasthouden`, `geen_verlies`. |
| status | `show_soc`, `show_price`, `show_next` | `true` | De SoC-balke, de priis no, de folgjende stap. |
| prizen | `hours_back` | `2` | Oeren fan it ferline om sjen te litten. |
| prizen | `hours_ahead` | `0` | Oeren foarút om sjen te litten; 0 is oant de lêste bekende priis. |
| prizen | `show_values` | `false` | De priis boppe elke balke printsje (oant 24 balken). |
| prizen | `height` | `140` | Hichte fan de grafyk yn piksels. |
| foarried | `tiles` | alle fiif | `voorraad`, `kostprijs`, `rendement`, `afschrijving`, `capaciteit`. |
| foarried | `notes` | `true` | De taljochting ûnder de kaart. |

`opbrengst` bepaalt oft de stroomskemakaart ek de opbringst toant: standert út by de gewoane
kaart, standert ien rigel by de kompakte kaart. Yn it stroomskema is grien in slagge
kontrôle, read de kontrôle dêr't it op stopt en streekjes in útkomst dêr't neat bart.
Alle kaarten lêze it attribút `stroomschema` fan de laadplan-sensor.

## Opbringst

**Ôfskriuwing.** Stelst do in oankeappriis yn, dan kostet elke kWh dy't de accu ûntladt in bytsje sliten: priis ÷ (syklussen × kapasiteit). Dat giet ôf fan de realisearre opbringst (hjoed, wike, moanne), telt mei yn de ferwachte opbringst en yn de beslissingen: in oere is allinnich it laden wurdich as it ek nei de sliten noch wint, ferkeapje freget de sliten boppe op de ferkeapmarzje, en *Fêsthâlde* en *Gjin ferlies* nimme kostpriis plus sliten as break-evenpriis. By in priis fan 0 (standert) feroaret der neat.

Der binne twa soarten opbringst: wat it hjoeddeistige plan nei ferwachting opbringt, en wat der echt
fertsjinne is.

### Ferwachte (skatting foarôf)

- **Laden**: wat de te keapjen enerzjy kostet, tsjin wat se letter wurdich is. Dy wearde is it
  rendemint kear de gemiddelde priis fan de djoere oeren dêr't it laadoere mei fergelike is.
- **Ferkeapje**: de opbringst fan it oerskot, minus wat weromlade kostet.

Tidens in laden telt allinnich mei wat der noch laden wurde moat.

### Hjoed en dizze wike (realisearre)

1. Enerzjy dy't de yntegraasje út it net laadt (laadplan of negative priis) wurdt
   **foarried**: brûkbere kWh = laden kWh × rendemint, mei as kostpriis wat dy enerzjy op dat
   momint kostte.
2. As de batterij dan ûntladt foar eigen ferbrûk, wurdt earst dat foarried brûkt. De winst is
   `ûntladen kWh × (stroompriis op dat momint − kostpriis per brûkbere kWh)`.
3. By ferkeapjen is de winst `ferkochte kWh × ferkeappriis − kostpriis`; foar enerzjy dy't net
   út it foarried komt (sinne-enerzjy) is de kostpriis wat weromlade kostet.
4. **Hjoed** is de som sûnt 00:00, **dizze wike** sûnt moandei 00:00 en **dizze moanne** sûnt de earste fan de moanne. **Foarige wike** is it definitive bedrach fan de wike derfoar.

Wat noch yn it foarried sit is noch net fertsjinne en telt pas as it brûkt wurdt. Enerzjy
dy't de sinne yn de batterij docht en dy't do letter sels brûkst, telt net mei: de Marstek docht
dat ek sûnder dizze yntegraasje. De bedragen komme fan de enerzjytellers fan de Marstek
en de oerepriis op dat momint; in tellersprong nei in steuring wurdt net boekt.

### Losse kaarten

Planrigel (Markdown-kaart):

```yaml
type: markdown
content: >-
  **Laadplan:** {{ state_attr('sensor.marstek_goedkoop_laden_laadplan', 'tekst') }}
  {% if is_state('switch.marstek_goedkoop_laden_prijssturing', 'off') %}
  · ⚠️ priissturing stiet **út**{% endif %}
```

De priiskaart hjirboppe docht itselde sûnder ekstra kaarten. As alternatyf, in grafyk mei [apexcharts-card](https://github.com/RomRider/apexcharts-card): de Zonneplan-prizen
fan hjoed en moarn, grien = laden, blau = rest fan it goedkeape finster, grys = oerich.
Werhelje de rige trije kear mei `'laden'`, `'venster'` en `'rest'` op de plak fan `KIES`:

```yaml
type: custom:apexcharts-card
graph_span: 48h
span:
  start: day
now:
  show: true
  label: no
stacked: true
series:
  - entity: sensor.zonneplan_current_hourly_electricity_tariff
    name: Bylade
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

## Untwikkelje

De rekkenregel sit apart fan Home Assistant yn `planner.py` en hat tests mei
echte prizen. De bestjoeringslogika is test tsjin in nepe Home Assistant
(`tests/test_sturing.py`):

```bash
python3 -m unittest discover -s tests -v
```


## Wizigingen

Sjoch [CHANGELOG.md](CHANGELOG.md), ynklusyf de brekkende wizigingen.

## Lisinsje

Apache 2.0, sjoch [LICENSE](LICENSE).
