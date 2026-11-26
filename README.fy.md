<img src="custom_components/marstek_goedkoop_laden/brand/icon.png" width="96" align="right" alt="">

# Marstek Goedkeap Lade foar Home Assistant

[🇬🇧 English](README.md) · [🇳🇱 Nederlands](README.nl.md) · 🏳️ Frysk · [🇩🇪 Deutsch](README.de.md) · [🇫🇷 Français](README.fr.md) · [🇪🇸 Español](README.es.md) · [🇸🇪 Svenska](README.sv.md) · [🇳🇴 Norsk](README.nb.md)

[![Open your Home Assistant instance and open this repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=rvdwal1991&repository=Marstek-Cheap-Charging-for-HA&category=integration)
[![Open your Home Assistant instance and start setting up the integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=marstek_goedkoop_laden)

Laadt in Marstek Venus-thúsbatterij by yn de goedkeapste oeren fan in dynamysk
stroomkontrakt, sadat er fol is foardat de prizen omheech geane.

It útgongspunt is **selsfoarsjennend wêze**: de batterij bliuwt gewoan sels regelje (anti-feed, nul
op de mjitter). Dizze yntegraasje docht ien ding derby, út it net bylade yn de goedkeapste oeren,
plus in pear opsjonele ekstra's dêromhinne.

**Do hast nedich:**

- in **dynamysk stroomkontrakt** mei oerenprizen. By in fêst taryf is der neat te winnen. Hy is
  boud om de Nederlânske merk en Zonneplan hinne (de prizen foar de oare dei ferskine
  tusken 13:00 en 15:00), mar elke sensor mei in oerenpriislist docht it, sjoch
  [Priissensor](#priissensor);
- in Marstek Venus dy't Home Assistant oer RS485 of Modbus bestjoere kin, sjoch
  [Kompatibiliteit](#kompatibiliteit). **Allinnich de opset mei LilyGO RS485 + ESPHome is op in
  echte accu test.**
- Home Assistant 2026.3 of nijer.

## Wat it docht

| Modus | Standert | Wat it docht |
|---|---|---|
| **Priissturing** | út | Laadt yn de goedkeapste oeren út it net en ferspriedt it fermogen oer dy oeren. |
| **Lade by negative priis** | oan | Laadt as de oerepriis negatyf is en makket it measte fan it finster. |
| **Sinneprognose** | oan | Laadt yn de nacht minder as de sinne de batterij oerdeis fol makket. Hat in sinneprognose yn it Enerzjydashboerd nedich. |
| **Fêsthâlde ûnder kostpriis** | oan | Ûntladt net salang't it net goedkeaper is as wat it byladen foarried kostet. |
| **Gjin ferlies** | út | Strange ferzje fan fêsthâlde: ferkeapet byladen foarried ek nea ûnder de kostpriis. |
| **Ferkeap** | út | Ferkeapet oerskot yn de djoerste oeren. |

Elke modus hat in eigen skeakeler. **Priissturing stiet út nei it ynstallearjen**: stel de yntegraasje yn,
kontrolearje oft de planrigel op de laadplan-sensor goed útsjocht en set him dan oan.

### Haadpunten

- **Dynamyske prizen.** Laadt yn de goedkeapste publisearre oeren, en allinnich safolle as nei it metten rendemint lonet.
- **Negative prizen.** Ferspriedt it laden oer it hiele negative finster, weage nei wat elk oere wurdich is; op winsk foar maksimale winst, sjoch [Lade by in negative priis](#lade-by-in-negative-priis).
- **Sinneprognose.** Brûkt de ferwachting út it Enerzjydashboerd: laadt allinnich wat de sinne net fol makket, lûkt it ferwachte húsferbrûk per oere ôf en leart fan de wiere opbringst hoe betrouber de ferwachting is, sjoch [Sinneprognose](#sinneprognose).
- **Ôfskriuwing.** Mei in oankeappriis telt de slijtaazje per kWh mei yn de opbringst, de ferkeapmarzje en it brekpunt fan *Fêsthâlde ûnder kostpriis*, sjoch [Opbringst](#opbringst).
- **Kostpriis.** Hâldt by wat it foarried yn de batterij kostet hat en ûntladt dat net ûnder dy priis (*Fêsthâlde ûnder kostpriis*, *Gjin ferlies*).
- **Oanslúting.** LilyGO mei ESPHome, in Modbus-hub (Elfin EW11 of de Venus E v3 streekrjocht oer ethernet) of de yntegraasje *Marstek Venus Modbus*, sjoch [Kompatibiliteit](#kompatibiliteit).
- **Kaarten en talen.** Sân dashboardkaarten dy't yn de GUI ynsteld wurde kinne, en acht talen.

## Fluchstart

1. Ynstallearje mei HACS (knop hjirboppe, of foegje dit repository ta as oanpast repository, kategory
   *Integration*), of kopiearje `custom_components/marstek_goedkoop_laden` nei
   `/config/custom_components/`. Start Home Assistant opnij.
2. *Ynstellingen → Apparaten en tsjinsten → Yntegraasje tafoegje → Marstek Goedkoop Laden*.
3. Kies hoe dyn Marstek keppele is, dan de priissensor en de Marstek-entiteiten.
   Wat herkend wurdt, stiet al ynfolle. By Modbus joust do ek de namme fan dyn Modbus-hub op (bygelyks
   `MarstekVenus`) en it slave-adres.
4. Set de skeakeler **Priissturing** oan as it plan goed útsjocht.
5. Foegje kaarten ta: *Dashboerd bewurkje → Kaart tafoegje → sykje op "Marstek"*, sjoch [Dashboardkaarten](#dashboardkaarten).

Teksten (planrigel, stroomskema, kaarten) folgje de opsje *Taal*: Automatysk, Nederlands,
English, Frysk, Deutsch, Français, Español, Svenska of Norsk. Automatysk folget Home Assistant
as dat ien fan dizze is, oars Ingelsk.

## Hoe it laadplan wurket

1. **Betellet bylade út?** In oere is goedkeap genôch as de priis leger is as
   `rendemint × (gemiddelde fan de 6 djoerste oeren yn de 18 oeren dêrnei) − marzje`. It
   rendemint (hinne en wer, laden en ûntladen, sa'n 77 % metten hjir) komt fan de
   enerzjytellers fan de Marstek.
2. **Finster.** It earste blok goedkeape oeren is it laadfinster. Ien of twa oeren dy't
   krekt net goedkeap genôch binne, brekke it blok net; der wurdt allinnich yn de goedkeape
   oeren sels laden.
3. **Laadoeren.** Binnen dat finster kiest er de goedkeapste oeren, krekt safolle as nedich binne
   om fan it hjoeddeistige SoC nei 100 % te kommen. Is it finster te koart om de batterij fol te
   krijen, dan plant er allinnich wat der yn past en seit dat yn de planrigel.
4. **Fermogen ferspriede.** It laadfermogen is de enerzjy dy't noch by moat, dield troch de tiid dy't der
   fan de laadoeren noch oer is. Dat hâldt de belêsting fan de netoansluting leech. It
   fermogen wurdt ûnderweis oanpast.
5. **Klear is klear.** As de laadoeren foarby binne of de batterij fol is, giet de Marstek
   werom nei anti-feed. Hy begjint net opnij yn itselde finster.

Der wurde allinnich **publisearre** prizen brûkt, dus it plan foar de nacht ferskynt sadree't de
prizen fan moarn bekend binne. Foarbyld (10 novimber 2026, batterij op 12 %): goedkeap finster
23:00–07:00, laden om 02:00, 03:00 en 04:00 op sa'n 1900 W foar gemiddeld € 0,37, tsjin
€ 0,55–0,67 oerdeis.

### Lade by in negative priis

As de oerepriis negatyf is, laadt de batterij, los fan it laadplan en ek as de
priissturing út stiet. Der wurdt sjoen nei it hiele **finster** fan opienfolgjende negative oeren:

1. Der wurdt útrekkene hoefolle de batterij noch kwyt kin (SoC oant 100 %).
2. Dy enerzjy wurdt oer de oeren ferdield **nei harren wearde**: hoe negatiever de priis, hoe
   mear der yn dat oere laden wurdt, oant wat in oere oan kin op it maksimale fermogen. Foarbyld:
   −€ 0,03, −€ 0,20 en −€ 0,12 mei 3 kWh te laden jout sa'n 1,9 kWh yn it oere fan −€ 0,20 en
   1,2 kWh yn it oere fan −€ 0,12. It oere fan −€ 0,03 soe ûnder it minimale laadfermogen
   bliuwe, dus dat falt ôf en syn oanpart giet nei de oare twa.
3. Ferspriede hâldt it fermogen leger as in koarte stoat op fol fermogen. In inkeld oere dat de batterij
   net fol krijt, wurdt op fol fermogen laden.

De opsje *Negative priis: ferdieling fan de enerzjy* kin op **Maksimale opbringst** set wurde: it bêste
oere wurdt earst fol makke op fol fermogen, dan it folgjende. Yn it foarbyld jout dat sa'n € 0,55
yn plak fan € 0,52, mei as priis mear stoaten op fol fermogen. It plan wurdt elke
minút opnij berekkene, en in oere dat al yn gebrûk is, krijt in bytsje ekstra romte foardat er ôffalt.

### Sinneprognose

Mei sinnepanielen wurdt de batterij oerdeis fergees fol. As do him yn de nacht fol út it
net laadst, hat it oerskot gjin romte mear en giet it foar lyts of neat nei it net, wat
mear útmakket no't de salderingsregeling (*salderingsregeling*) ophâldt. Dus sjocht de yntegraasje nei
de ferwachte sinne-opbringst:

1. Hy lêst de prognose út it **Enerzjydashboerd** (*Ynstellingen → Dashboerden → Enerzjy → Sinnepanielen → Prognose sinneproduksje*). Forecast.Solar, Solcast, Open-Meteo en oare prognoseyntegraasjes wurkje, sûnder dat der wat ekstra ynsteld hoecht te wurden. Sûnder in prognose dêr feroaret der neat.
2. Hy rekkenet it ferwachte oerskot út: per oere de prognose, kear de betrouberens,
   minus dyn eigen ferbrûk yn dat oere. Prognoses binne faak te rooskleurich, benammen yn de winter.
   Mei *Betrouberens leare fan de werklike produksje* oan fergeliket de yntegraasje de prognose fan elke dei
   mei wat de panielen werklik produsearre hawwe (de produksjeteller út it Enerzjydashboerd) en
   brûkt de mediaan fan de lêste dagen as betrouberens, sadree't er teminsten 3 dagen hat.
   Oant dan, en as it leare út stiet, jildt de ynstelling *Betrouberens fan de sinneprognose* (standert 70 %).
   Dyn eigen ferbrûk yn dat oere: mei in *Sensor foar húsfermogen*
   leart de yntegraasje dyn gemiddelde ferbrûk per oere fan de dei (wurkdagen en wykein
   apart) en brûkt dat, sadat in middei dat it hûs sels opfrettet gjin oerskot oerlit.
   Sûnder de sensor wurdt it fêste *Ferkeapje: gemiddeld eigen ferbrûk* brûkt.
3. Hy laadt yn de nacht mar safolle dat der romte is foar dat oerskot as de sinne opkomt:
   wat dyn eigen ferbrûk oant dan opmakket, plus wat der noch nedich is. Op in sinnige dei kin dat
   in pear kWh wêze yn plak fan in folle batterij, of neat (de planrigel seit dan dat de sinne de
   batterij folt). In bewolkte dei jout in lyts of gjin oerskot, en dan wurdt de batterij fol laden.

De prognose wurdt alle 30 minuten lêzen. Hy ferleget allinnich de te laden hoemannichte; hy
ferpleatst gjin laadoeren en feroaret neat oan ferkeapjen.

### Fêsthâlde en gjin ferlies

Enerzjy dy't út it net laden is hat in kostpriis: de laadpriis dield troch it rendemint. As de
batterij dy enerzjy werom joech yn oeren dy't goedkeaper binne as dat, soe laden jild kostje.
**Fêsthâlde** blokkearret dêrom it ûntladen salang't der byladen foarried yn de batterij sit (sjoch
[Opbringst](#opbringst)) en de oerepriis ûnder de kostpriis fan dat foarried leit. It hûs brûkt dan netstroom,
dy't op dat momint goedkeaper is. Sadree't de priis de kostpriis berikt, of it foarried
opmakke is, nimt de Marstek it wer oer.

Technysk set de yntegraasje it maksimale ûntladefermogen op 0. De Marstek bliuwt yn
anti-feed, dus laden út sinneoerskot giet gewoan troch. As in oare automatisearring dat fermogen
tidens it fêsthâlden set (bygelyks in begrinzer foar in EV-lader), ûnthâldt de yntegraasje dy wearde
en jout se letter werom. De Marstek kin netenerzjy net ûnderskiede fan sinne-enerzjy, dus tidens in
fêsthâlden wurdt de hiele batterij net ûntladen. Fêsthâlde hat de entiteit foar it maksimale ûntladefermogen
nedich.

**Gjin ferlies** is in aparte, strangere skeakeler: fêsthâlde wurdt ôfdwongen, ek as de skeakeler Fêsthâlde út stiet, en
der wurdt neat ûnder de kostpriis ferkocht. Elke boekte kWh bringt dan minstens syn kostpriis op. Wat it
net útslute kin:

- **Stilstân:** as de priis lang ûnder de kostpriis bliuwt, bliuwt de batterij
  blokkearre, ek foar bewarre sinne-enerzjy.
- **Ôfwikend rendemint:** as de batterij minder werom jout as it gemiddelde rendemint, is er leech
  foardat it foarried yn de boeken opmakke is; de rest ferfalt sûnder dat der in ferlies boekt wurdt.
- **Sliten** wurdt net meirekkene, útsein as do in oankeappriis ynstelst (sjoch [Opbringst](#opbringst)).

### Ferkeapje

Ferkeapje hat in eigen skeakeler en is ûnôfhinklik fan laden. Der wurdt allinnich ferkocht wat echt oer is.
In oere wurdt brûkt om te ferkeapjen as dit alles opgiet:

1. **In goedkeap laden komt der oan**: der leit in laadfinster mei publisearre prizen foarút, sadat de kosten
   fan weromlade bekend binne.
2. **De opbringst is dúdlik heger as weromlade**: ferkeappriis ≥ laadpriis dield troch it
   rendemint, plus de ferkeapmarzje (standert € 0,10 per kWh).
3. **Der is oerskot boppe de reserve**: de ûntladegrins fan de Marstek plus it ferwachte eigen
   ferbrûk oant it weromlade, mei in ynstelber minimum (standert 20 %).
4. **It is ien fan de djoerste oeren** foar it laadfinster.

It ferkeapfermogen wurdt oer de keazen oeren ferspraat; oan de reserve hâldt it ferkeapjen op. Yn de winter is
der selden oerskot; de opsje docht benammen wat as de sinne de batterij fol makket en der in
jûnspriispiek is. Hy hat de entiteit foar it twongen ûntladefermogen nedich.

**Nei it ein fan de salderingsregeling** (de Nederlânske *salderingsregeling*, 1 jannewaris 2027) bringt weromlevering
minder op as de oerepriis. Stel dan *Ferkeappriis: faktor* en *ôftrek* yn: ferkeappriis =
oerepriis × faktor − ôftrek. Foar de kale merkpriis by Zonneplan is dat sa'n 0,826
en € 0,108.

## Kompatibiliteit

De yntegraasje stjoert in Marstek Venus oan fia de RS485-bestjoeringsregisters.

| Keppeling | Model | Status |
|---|---|---|
| LilyGO T-CAN485 + ESPHome (RS485) | Venus E v2 | **Test** op echte hardware (de opset wêrop't er boud is) |
| Modbus-hub yn Home Assistant, fia RS485-nei-TCP-converter (Elfin EW11 en fergelykbere) | Venus E v1/v2 | Allinnich test mei neimakke oanroppen |
| Modbus-hub yn Home Assistant, rjochtstreeks fia Ethernet | Venus E v3 | Allinnich test mei neimakke oanroppen |
| Yntegraasje *Marstek Venus Modbus* (ViperRNMC) | Venus E v3 | Allinnich test mei neimakke oanroppen |
| Ien fan hjirboppe | Venus A, Venus D, oare modellen | **Net kontrolearre, net test.** Se soene de bestjoeringsregisters diele, mar dat is net ferifiearre. Stel de accukapasiteit yn by de opsjes (standert 5,12 kWh). |
| Cloud, app of oare yntegraasjes | alle | Net stipe |

- **LilyGO T-CAN485 mei ESPHome** fia RS485, mei de konfiguraasje fan
  [MarstekVenus-LilygoRS485](https://github.com/Superduper1969/MarstekVenus-LilygoRS485). Hy brûkt
  de entiteiten dy't dizze opset leveret: *RS485 Control Mode*, *Forcible Charge/Discharge*,
  *Forcible Charge Power* (ferplicht) en, opsjoneel, *Max. Charge Power*, *Max. Discharge Power*,
  *Forcible Discharge Power*, *Discharging Cutoff Capacity* en de totaaltellers fan laden en
  ûntladen enerzjy.
- **Modbus yn Home Assistant**, mei in Modbus-hub dy't do sels yn
  `configuration.yaml` sette: in Elfin EW11 of in oare RS485-nei-TCP-converter
  ([MarstekVenus-ElfinEW11](https://github.com/Superduper1969/MarstekVenus-ElfinEW11)), of de
  **Venus E v3 rjochtstreeks fia Ethernet** (Modbus TCP, poarte 502, unit 1, EMS V144 of nijer;
  [MarstekVenusV3-modbus-TCP-IP](https://github.com/fonske/MarstekVenusV3-modbus-TCP-IP)). De
  yntegraasje lêst de registersensoren fan dy opset en skriuwt de registers 42000 (RS485-bestjoering),
  42010 (twangmodus), 42020/42021 (twongen laad-/ûntladefermogen) en, as do de sensoren opjefst,
  44002/44003 (maksimaal laad-/ûntladefermogen) mei `modbus.write_register`. Sûnder it maksimale
  ûntladefermogen binne *Fêsthâlde* en *Gjin ferlies* net beskikber. De Venus E v3 hat it
  laadnivo yn register 34002 (skaal 0,1), net yn 32104.
- **De yntegraasje *Marstek Venus Modbus***
  ([ViperRNMC/marstek_venus_modbus](https://github.com/ViperRNMC/marstek_venus_modbus)), dy't ek
  Modbus TCP praat. Kies dit as do him al brûkst: hy leveret de entiteiten (`switch`
  RS485-bestjoering, `select` twangmodus, `number` fermogens). Set dêr earst de skeakeler
  *RS485 control mode* en de select *Force mode* oan, se steane standert út.

### Wat de yntegraasje nei de Marstek stjoert

| Momint | Kommando's |
|---|---|
| Begjin mei laden | laadfermogen sette → twangmodus `charge` → RS485-bestjoering `enable` |
| Tidens it laden | laadfermogen oanpasse (stappen fan 100 W) |
| Klear, of priissturing út | RS485-bestjoering `disable`, twangmodus werom op `charge`, laadfermogen werom op it maksimum |
| Begjin mei ferkeapjen | ûntladefermogen sette → twangmodus `discharge` → RS485-bestjoering `enable` |
| Ferkeapjen klear, of ferkeapjen út | itselde as klear: werom nei de rêststân |

Twongen **ût**laden dat do sels begjinst, wurdt oerlitten. Twongen laden dat do sels
begjinst, wurdt weromset salang't de priissturing oan stiet; set dy earst út as do dat wolst.

## Ynstellingen

Ûnder *Konfigurearje* by de yntegraasje. De opsjes steane yn groepen; de entiteiten steane yn in
ynklapte groep ûnderoan.

### Priissensor

De yntegraasje lêst de prizen út in attribút fan ien sensor (standert `forecast`):

- Zonneplan-oerenprizen: `start_date`, `end_date`, `price_tax_included.amount`
- Zonneplan (âld): `datetime`, `electricity_price`
- Algemien: `start` (of `start_time`, `datetime`) en `price` (of `value`, `prijs`) yn €/kWh

### Opsjes

| Groep | Ynstelling | Standert | Betsjutting |
|---|---|---|---|
| | Taal | Automatysk | Taal fan planrigel, stroomskema en kaarten. |
| Accu | Accukapasiteit | 5,12 kWh | Allinnich brûkt as der gjin kapasiteitssensor ynsteld is. |
| Accu | Rendemint as de tellers ûntbrekke | 0,77 | It rendemint wurdt berekkene út de enerzjytellers fan de Marstek (totaal ûntladen ÷ totaal laden, begrinzge op 70–95 %). Dizze fêste wearde jildt allinnich as dy tellers ûntbrekke. It rendemint fan ien rjochting is de woartel dêrfan. |
| Accu | Oankeappriis accu | € 0 | Foar de ôfskriuwing. 0 set se út. |
| Accu | Libbensdoer accu (syklussen) | 6000 | Ôfskriuwing per kWh = priis ÷ (syklussen × kapasiteit); € 1.500 oer 6.000 syklussen fan 5,12 kWh is sa'n € 0,049 per kWh. |
| Accu | Ûntladegrins | 12 % | Brûkt as der gjin entiteit foar de ûntladegrins ynsteld is. |
| Bylade | Minimale winst per kWh | € 0,02 | Wat laden nei ôftrek fan it laadferlies minstens opbringe moat. Oeren dy't minder as in heale sint boppe de grins lizze telle ek mei, sadat in hast platte nacht net om in fraksje fan in sint opsnipele wurdt. |
| Bylade | Minimaal laadfermogen | 400 W | Legere grins by it ferspriede. |
| Bylade | Attribút mei de prizen | `forecast` | It attribút fan de priissensor mei de oerenprizen. |
| Bylade | Oantal djoerste oeren om mei te fergelykjen | 6 | Mei hoefolle djoere oeren letter op de dei in oere fergelike wurdt. |
| Bylade | Oantal oeren foarút sjen | 18 | Hoe fier foarby in oere sjoen wurdt nei djoere oeren. |
| Bylade | Minimaal oantal bekende oeren foarút | 8 | Oeren mei minder bekende prizen dêrnei wurde negearre. |
| Negative priis | Negative priis: grins | € 0,00 | Ûnder dizze oerepriis laadt de batterij. |
| Negative priis | Negative priis: ferdieling fan de enerzjy | Nei wearde | Nei wearde (leger fermogen) of maksimale opbringst (bêste oeren earst). |
| Sinne | Sinneprognose brûke | Oan | Hâldt by it laden yn de nacht rekken mei de ferwachte sinne-opbringst út it Enerzjydashboerd. |
| Sinne | Betrouberens leare fan de werklike produksje | Oan | Fergelykje de sinneprognose fan elke dei mei wat de panielen werklik produsearre hawwe en brûk de mediaan fan de lêste dagen as betrouberens (fan 3 dagen ôf). |
| Sinne | Betrouberens fan de sinneprognose | 70 % | It part fan de prognose dêr't op rekkene wurdt. Leger is foarsichtiger. |
| Sinne | Sensor foar húsfermogen | gjin | Opsjonele sensor mei it fermogen dat it hiele hûs brûkt (W of kW), sûnder de batterij. In laadpeal ferfoarmet it gemiddelde, lit dy dus fuort as it kin. |
| Ferkeap | Ferkeapje: minimale winst per kWh | € 0,10 | Wat ferkeapje nei weromlade minstens opbringe moat. |
| Ferkeap | Ferkeapje: gemiddeld eigen ferbrûk | 400 W | Bepaalt de reserve oant it weromlade, en is it fêste eigen ferbrûk foar it sinne-oerskot. |
| Ferkeap | Ferkeapje: minimale reserve | 20 % | Ûnder dizze SoC wurdt neat ferkocht. |
| Ferkeap | Ferkeappriis: faktor en ôftrek | 1 en € 0 | Ferkeappriis = oerepriis × faktor − ôftrek. |

It maksimale laadfermogen (de *Max. Charge power* fan de Marstek) bepaalt it oantal laadoeren.
Set it leger en der wurde mear oeren plend en der wurdt rêstiger laden.

## Dashboardkaarten

De yntegraasje leveret sân kaarten mei; der hoecht gjin resource tafoege te wurden. Fernij de
browser nei it ynstallearjen of bywurkjen. Elke kaart is yn te stellen yn de kaarteditor en yn YAML, en
as do `entity` weilitst, wurdt de laadplan-sensor automatysk fûn.

| Kaart | Ynhâld |
|---|---|
| `custom:marstek-goedkoop-laden-card` | Stroomskema: de tiidline fan hjoed en per ûnderdiel (bylade, ferkeap, negative priis, fêsthâlde) hokker kontrôles slagje en op hokker it stopt. |
| `custom:marstek-goedkoop-laden-compact-card` | Itselde yn in pear rigels: de tiidline, per ûnderdiel de útkomst mei de reden, en ien rigel mei de opbringst. |
| `custom:marstek-goedkoop-laden-opbrengst-card` | Allinnich de opbringst: hjoed, dizze wike, foarige wike, dizze moanne, dit jier en de ferwachting fan it hjoeddeistige plan. |
| `custom:marstek-goedkoop-laden-schakelaars-card` | Kompakt: knoppen om de modi oan of út te setten. |
| `custom:marstek-goedkoop-laden-status-card` | Wat der no bart, it laadnivo as balke, de priis no en de folgjende stap. |
| `custom:marstek-goedkoop-laden-prijzen-card` | Priisgrafyk sûnder ekstra kaarten: de oeren mei laden, ferkeapjen en negative prizen markearre, en in line foar no. |
| `custom:marstek-goedkoop-laden-voorraad-card` | It byladen foarried, de kostpriis dêrfan, it rendemint, de ôfskriuwing per kWh en de kapasiteit. |

```yaml
type: custom:marstek-goedkoop-laden-opbrengst-card
entity: sensor.marstek_goedkoop_laden_laadplan   # opsjoneel
title: Opbringst                                 # opsjoneel
tiles: [vandaag, maand, jaar]                    # hokker tegels, yn dizze folchoarder
notes: false                                     # ferberch de taljochting ûnder de kaart
```

| Kaart | Opsje | Standert | Betsjutting |
|---|---|---|---|
| alle | `entity`, `title` | automatysk fûn, gjin | De laadplan-sensor en in titel. |
| stroomskema, kompakt | `show_timeline` | `true` | De tiidline fan hjoed sjen litte. |
| stroomskema, kompakt | `opbrengst` | út, ien rigel | Ek de opbringst sjen litte. |
| stroomskema, kompakt, skeakelers | `lanes` | alle fiif | Hokker ûnderdielen sjen litte: `bijladen`, `verkoop`, `negatief`, `vasthouden`, `geen_verlies`. |
| opbringst | `tiles` | alle seis | Elk fan `vandaag`, `week`, `vorige_week`, `maand`, `jaar`, `verwacht`, yn dizze folchoarder. |
| opbringst | `expected_details`, `notes` | `true` | De rigels per ûnderdiel fan it plan; de taljochting mei foarried, wat der hjoed laden is en de ôfskriuwing. |
| status | `show_soc`, `show_price`, `show_next` | `true` | De SoC-balke, de priis no, de folgjende stap. |
| prizen | `hours_back`, `hours_ahead` | `2`, `0` | Oeren fan it ferline; oeren foarút (0 is oant de lêste bekende priis). |
| prizen | `show_values`, `height` | `false`, `140` | De priis boppe elke balke printsje (oant 24 balken); hichte yn piksels. |
| foarried | `tiles`, `notes` | alle fiif, `true` | `voorraad`, `kostprijs`, `rendement`, `afschrijving`, `capaciteit`; de taljochting ûnder de kaart. |

Yn it stroomskema is grien in slagge kontrôle, read de kontrôle dêr't it op stopt en streekjes in
útkomst dêr't neat bart. Planrigel yn in Markdown-kaart:

```yaml
type: markdown
content: >-
  **Laadplan:** {{ state_attr('sensor.marstek_goedkoop_laden_laadplan', 'tekst') }}
  {% if is_state('switch.marstek_goedkoop_laden_prijssturing', 'off') %}
  · ⚠️ priissturing stiet **út**{% endif %}
```

## Opbringst

Der binne twa soarten opbringst: wat it hjoeddeistige plan nei ferwachting opbringt, en wat der echt
fertsjinne is.

**Ferwachte (skatting foarôf).** Laden: wat de te keapjen enerzjy kostet, tsjin wat se letter
wurdich is (it rendemint kear de gemiddelde priis fan de djoere oeren dêr't it laadoere mei
fergelike is). Ferkeapje: de opbringst fan it oerskot, minus wat weromlade kostet. Tidens in
laden telt allinnich mei wat der noch laden wurde moat.

**Realisearre (hjoed, wike, moanne, jier).**

1. Enerzjy dy't de yntegraasje út it net laadt (laadplan of negative priis) wurdt
   **foarried**: brûkbere kWh = laden kWh × rendemint, mei as kostpriis wat dy enerzjy op dat
   momint kostte.
2. As de batterij dan ûntladt foar eigen ferbrûk, wurdt earst dat foarried brûkt. De winst is
   `ûntladen kWh × (stroompriis op dat momint − kostpriis per brûkbere kWh)`.
3. By ferkeapjen is de winst `ferkochte kWh × ferkeappriis − kostpriis`; foar enerzjy dy't net
   út it foarried komt (sinne-enerzjy) is de kostpriis wat weromlade kostet.
4. **Hjoed** telt sûnt 00:00, **dizze wike** sûnt moandei 00:00, **dizze moanne** sûnt de earste
   en **dit jier** sûnt 1 jannewaris. **Foarige wike** is it definitive bedrach fan de wike derfoar.

Wat noch yn it foarried sit is noch net fertsjinne en telt pas as it brûkt wurdt. Enerzjy dy't de
sinne yn de batterij docht en dy't do letter sels brûkst, telt net mei: de Marstek docht dat ek
sûnder dizze yntegraasje. De bedragen komme fan de enerzjytellers fan de Marstek en de oerepriis
op dat momint; in tellersprong nei in steuring wurdt net boekt.

**Ôfskriuwing.** Stelst do in oankeappriis yn, dan kostet elke kWh dy't de accu ûntladt in bytsje
sliten: priis ÷ (syklussen × kapasiteit). Dat giet ôf fan de realisearre opbringst, telt mei yn de
ferwachte opbringst en yn de beslissingen: in oere is allinnich it laden wurdich as it ek nei de
sliten noch wint, ferkeapje freget de sliten boppe op de ferkeapmarzje, en *Fêsthâlde* en *Gjin ferlies* nimme kostpriis
plus sliten as break-evenpriis. By in priis fan 0 (standert) feroaret der neat.

## Entiteiten

| Entiteit | Ynhâld |
|---|---|
| `switch.*_priissturing` | Oan: it laadplan wurdt útfierd. Út: de Marstek regelet alles sels. |
| `switch.*_lade_by_negative_priis` | Oan (standert): laden as de oerepriis negatyf is. |
| `switch.*_festhalde_under_kostpriis` | Oan (standert): net ûntlade ûnder de kostpriis fan it foarried. |
| `switch.*_gjin_ferlies` | Oan: fêsthâlde ôfdwongen en nea ûnder de kostpriis ferkeapje. |
| `switch.*_ferkeap` | Oan: oerskot wurdt yn de djoerste oeren ferkocht. Ûnôfhinklik fan priissturing. |
| `sensor.*_laadplan` | Steat: `laden`, `gepland`, `klaar`, `vol`, `geen` of `onbekend`. Attributen: `tekst` (lêsbere gearfetting), `laaduren`, `venster`, `stroomschema` (tiidline, kontrôles, prizen en oersjoch foar de kaarten) en mear. |
| `sensor.*_ferkeapplan` | Steat: `verkopen`, `gepland`, `geen` of `onbekend`. Attributen: `verkoopuren`, `overschot_kwh`, `reserve_soc`, `tekst` en mear. |
| `sensor.*_pland_laadfermogen`, `*_enerzjy_om_by_te_laden`, `*_start_bylade`, `*_ein_bylade`, `*_gemiddelde_laadpriis` | It ferspraat laadfermogen yn W, de enerzjy dy't noch laden wurde moat yn kWh, begjin en ein fan de plande bylade, en de gemiddelde priis dêrfan yn €/kWh. |
| `sensor.*_opbringst_hjoed`, `*_opbringst_dizze_wike`, `*_opbringst_foarige_wike`, `*_opbringst_dizze_moanne`, `*_opbringst_dit_jier` | Realisearre opbringst yn euro's (sjoch [Opbringst](#opbringst)). |
| `sensor.*_ferwachte_opbringst` | Rûsde opbringst fan de hjoeddeistige plannen yn euro's; attribút `regels` befettet de útsplitsing. |
| `sensor.*_rendemint` | It brûkte rendemint, yn prosinten. Attribút `bron`: metten of fêst. |

Entiteitsnammen folgje de taal fan Home Assistant op it momint dat de entiteit oanmakke wurdt (yn it Frysk
hjitte se `*_laadplan`, `*_priissturing` ensafuorthinne; yn it Nederlânsk `*_prijssturing`). **Steatwearden en attribútnammen binne
yn elke taal Nederlânsk** (`laden`, `tekst`, …); se steane fêst, sadat automatisearringen bliuwe wurkje.

## Untwikkelje

De rekkenregel sit apart fan Home Assistant yn `planner.py` en hat tests mei
echte prizen. De bestjoeringslogika is test tsjin in nepe Home Assistant:

```bash
python3 -m unittest discover -s tests -v
```

## Wizigingen

Sjoch [CHANGELOG.md](CHANGELOG.md), ynklusyf de brekkende wizigingen.

## Tankwurd

Dizze yntegraasje stiet op it wurk fan de Marstek Venus-mienskip:

- De [Tweakers-forumtried](https://gathering.tweakers.net/forum/list_messages/2282240/0) dêr't dit mienskipswurk besprutsen wurdt, in earefermelding foar elkenien dy't dêr befinings en konfiguraasjes dielt.
- [Superduper1969](https://github.com/Superduper1969) foar de LilyGO RS485- en Elfin EW11-konfiguraasjes dêr't dizze yntegraasje om hinne boud is, en scruysberghs, dy't yn dy konfiguraasjes betanke wurdt.
- [fonske](https://github.com/fonske) foar de Modbus TCP-konfiguraasje fan de Venus E v3.
- [ViperRNMC](https://github.com/ViperRNMC) foar de Marstek Venus Modbus-yntegraasje.

## Lisinsje

Apache 2.0, sjoch [LICENSE](LICENSE).
