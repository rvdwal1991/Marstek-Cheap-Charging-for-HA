/*
 * Marstek Goedkoop Laden - dashboardkaarten
 *
 * Alle kaarten lezen het attribuut `stroomschema` van de laadplan-sensor en zijn in de
 * visuele editor in te stellen (ook in YAML). De entiteit wordt zelf gevonden als je hem
 * niet opgeeft.
 *
 *   type: custom:marstek-goedkoop-laden-card              stroomschema (tijdlijn + controles)
 *   type: custom:marstek-goedkoop-laden-compact-card      hetzelfde, compact
 *   type: custom:marstek-goedkoop-laden-opbrengst-card    de opbrengsten
 *   type: custom:marstek-goedkoop-laden-schakelaars-card  de schakelaars van de modi
 *   type: custom:marstek-goedkoop-laden-status-card       wat er nu gebeurt, SoC, prijs, volgende stap
 *   type: custom:marstek-goedkoop-laden-prijzen-card      prijsgrafiek met laad- en verkooptijden
 *   type: custom:marstek-goedkoop-laden-voorraad-card     bijgeladen voorraad, kostprijs, rendement
 *
 * Opties voor alle kaarten:
 *   entity: sensor.marstek_goedkoop_laden_laadplan   (optioneel, wordt gezocht)
 *   title: Prijssturing                              (optioneel)
 * Stroomschema en compact:
 *   opbrengst: true | false      toon ook de opbrengst
 *   show_timeline: true | false  de tijdlijn van vandaag (standaard: aan)
 *   lanes: [bijladen, verkoop, negatief, vasthouden, geen_verlies]   welke onderdelen (standaard: alle)
 * Schakelaars:
 *   lanes: zoals hierboven
 * Opbrengst:
 *   tiles: [vandaag, week, vorige_week, maand, jaar, verwacht]
 *   expected_details: true | false   regels per onderdeel van het plan (standaard: aan)
 *   notes: true | false              toelichting onder de kaart (standaard: aan)
 * Status:
 *   show_soc, show_price, show_next: true | false (standaard: aan)
 * Prijzen:
 *   hours_back: 2 (uren terug), hours_ahead: 0 (uren vooruit, 0 = tot de laatste bekende prijs)
 *   show_values: true | false, height: 140 (pixels)
 * Voorraad:
 *   tiles: [voorraad, kostprijs, rendement, afschrijving, capaciteit]
 */
const DEFAULT_ENTITY = "sensor.marstek_goedkoop_laden_laadplan";

const ICONS = {
  nu: "mdi:circle-medium",
  ok: "mdi:check",
  stop: "mdi:close",
  actie: "mdi:flash",
  eind: "mdi:minus",
  wacht: "mdi:clock-outline",
};

const STYLE = `
  :host { display: block; }
  ha-card { padding: 16px; }
  ha-card.compact { padding: 12px 14px; }
  .title { font-size: 16px; font-weight: 500; margin: 0 0 12px; color: var(--primary-text-color); }
  .compact .title { font-size: 14px; margin-bottom: 8px; }
  .head { display: flex; align-items: center; gap: 6px; font-size: 12px; margin: 0 0 8px;
          color: var(--secondary-text-color); }
  .head ha-icon { --mdc-icon-size: 16px; }
  .head .off { opacity: 0.7; }
  .step { display: grid; grid-template-columns: 24px minmax(0, 1fr); column-gap: 10px; }
  .rail { display: flex; flex-direction: column; align-items: center; }
  .dot { width: 22px; height: 22px; border-radius: 50%; box-sizing: border-box; flex: none;
         display: flex; align-items: center; justify-content: center;
         border: 1px solid var(--divider-color); color: var(--secondary-text-color);
         background: var(--card-background-color, transparent); }
  .dot ha-icon { --mdc-icon-size: 14px; display: flex; }
  .line { flex: 1; min-height: 12px; margin: 2px 0; border-left: 2px solid var(--divider-color); }
  .text { padding-bottom: 10px; min-width: 0; }
  .step:last-child .text { padding-bottom: 0; }
  .text b { display: block; font-weight: 500; font-size: 14px; line-height: 22px;
            color: var(--primary-text-color); }
  .text span { display: block; font-size: 12px; line-height: 16px; color: var(--secondary-text-color); }
  .ok .dot, .actie .dot { color: var(--success-color, #43a047); border-color: var(--success-color, #43a047);
            background: color-mix(in srgb, var(--success-color, #43a047) 16%, transparent); }
  .stop .dot { color: var(--error-color, #db4437); border-color: var(--error-color, #db4437);
            background: color-mix(in srgb, var(--error-color, #db4437) 16%, transparent); }
  .stop .text b { color: var(--error-color, #db4437); }
  .wacht .dot { color: var(--warning-color, #ffa600); border-color: var(--warning-color, #ffa600);
            background: color-mix(in srgb, var(--warning-color, #ffa600) 16%, transparent); }
  .wacht .text b { color: var(--primary-text-color); }
  .stop .line, .eind .line, .wacht .line { border-left-style: dashed; }
  .eind .dot { border-style: dashed; }
  .eind .text b { color: var(--secondary-text-color); }
  .nu .dot { border: 2px solid var(--primary-color); color: var(--primary-color); }
  .divider { border-top: 1px solid var(--divider-color); margin: 14px 0; }
  .compact .divider { margin: 8px 0; }
  .lanes { display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 16px; }
  .lane.uit .step { opacity: 0.55; }
  .empty { font-size: 14px; color: var(--secondary-text-color); }

  .crow { display: grid; grid-template-columns: 18px minmax(0, 1fr) auto; column-gap: 8px;
          align-items: center; min-height: 24px; font-size: 13px; }
  .crow .pip { width: 10px; height: 10px; border-radius: 50%; box-sizing: border-box; justify-self: center;
               border: 1px solid var(--divider-color); }
  .crow.nu .pip { border: 2px solid var(--primary-color); }
  .crow.actie .pip, .crow.ok .pip { background: var(--success-color, #43a047); border-color: var(--success-color, #43a047); }
  .crow.wacht .pip { background: var(--warning-color, #ffa600); border-color: var(--warning-color, #ffa600); }
  .crow.stop .pip { background: var(--error-color, #db4437); border-color: var(--error-color, #db4437); }
  .crow.eind .pip { border-style: dashed; }
  .crow ha-icon { --mdc-icon-size: 16px; color: var(--secondary-text-color); justify-self: center; display: flex; }
  .crow .main { min-width: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
                color: var(--secondary-text-color); }
  .crow .main b { font-weight: 500; color: var(--primary-text-color); }
  .crow .out { white-space: nowrap; font-weight: 500; color: var(--secondary-text-color); }
  .crow .out.actie { color: var(--success-color, #43a047); }
  .crow.uit { opacity: 0.6; }

  .result { display: grid; grid-template-columns: auto minmax(0, 1fr); column-gap: 16px; align-items: center; }
  .total { font-size: 24px; font-weight: 500; line-height: 1.2; white-space: nowrap; color: var(--primary-text-color); }
  .plus { color: var(--success-color, #43a047) !important; }
  .min { color: var(--error-color, #db4437) !important; }
  .total small { display: block; font-size: 12px; font-weight: 400; color: var(--secondary-text-color); }
  .rows { display: flex; flex-direction: column; gap: 6px; min-width: 0; }
  .row { display: grid; grid-template-columns: minmax(0, 1fr) auto; column-gap: 8px; font-size: 12px;
         line-height: 16px; color: var(--secondary-text-color); }
  .row b { font-weight: 500; font-size: 13px; color: var(--primary-text-color); }
  .amount { font-size: 13px; font-weight: 500; white-space: nowrap; color: var(--primary-text-color); }
  .tiles { display: grid; grid-template-columns: repeat(auto-fit, minmax(96px, 1fr)); gap: 8px; margin-bottom: 14px; }
  .tile { border: 1px solid var(--divider-color); border-radius: 10px; padding: 10px 12px; min-width: 0; }
  .tile small { display: block; font-size: 12px; color: var(--secondary-text-color); white-space: nowrap;
                overflow: hidden; text-overflow: ellipsis; }
  .tile b { display: block; font-size: 20px; font-weight: 500; line-height: 1.3; white-space: nowrap;
            color: var(--primary-text-color); }
  .note { font-size: 12px; line-height: 16px; color: var(--secondary-text-color); margin-top: 12px; }
  .chips { display: grid; grid-template-columns: repeat(auto-fit, minmax(96px, 1fr)); gap: 8px; }
  .chip { display: flex; align-items: center; gap: 8px; min-width: 0; padding: 8px 10px; cursor: pointer;
          font: inherit; text-align: left; border-radius: 10px; border: 1px solid var(--divider-color);
          background: transparent; color: var(--secondary-text-color); }
  .chip ha-icon { --mdc-icon-size: 20px; display: flex; flex: none; }
  .chip .label { min-width: 0; }
  .chip b { display: block; font-size: 13px; font-weight: 500; line-height: 16px;
            overflow-wrap: anywhere; color: var(--primary-text-color); }
  .chip small { display: block; font-size: 11px; line-height: 14px; }
  .chip.on { border-color: var(--primary-color); color: var(--primary-color);
             background: color-mix(in srgb, var(--primary-color) 14%, transparent); }
  .chip.on small { color: var(--primary-color); }
  .chip:disabled { opacity: 0.5; cursor: default; }
  .chip:focus-visible { outline: 2px solid var(--primary-color); outline-offset: 2px; }

  .status { display: grid; grid-template-columns: 44px minmax(0, 1fr); column-gap: 12px; align-items: center; }
  .status .badge { width: 44px; height: 44px; border-radius: 50%; display: flex; align-items: center;
                   justify-content: center; border: 1px solid var(--divider-color); color: var(--secondary-text-color); }
  .status .badge ha-icon { --mdc-icon-size: 26px; display: flex; }
  .status.actie .badge, .status.ok .badge { color: var(--success-color, #43a047); border-color: var(--success-color, #43a047);
            background: color-mix(in srgb, var(--success-color, #43a047) 16%, transparent); }
  .status b { display: block; font-size: 16px; font-weight: 500; line-height: 22px; color: var(--primary-text-color); }
  .status span { display: block; font-size: 12px; line-height: 16px; color: var(--secondary-text-color); }
  .meter { margin-top: 14px; }
  .meter .top { display: flex; justify-content: space-between; font-size: 12px; color: var(--secondary-text-color); margin-bottom: 4px; }
  .meter .top b { font-weight: 500; color: var(--primary-text-color); font-size: 13px; }
  .bar { height: 8px; border-radius: 4px; background: var(--divider-color); overflow: hidden; }
  .bar i { display: block; height: 100%; border-radius: 4px; background: var(--primary-color); }
  .facts { display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 8px; margin-top: 14px; }
  .fact { font-size: 12px; color: var(--secondary-text-color); min-width: 0; }
  .fact b { display: block; font-size: 15px; font-weight: 500; color: var(--primary-text-color); overflow-wrap: anywhere; }
  .chart svg { display: block; width: 100%; height: auto; touch-action: pan-y; user-select: none;
               -webkit-user-select: none; -webkit-tap-highlight-color: transparent; cursor: pointer; }
  .chart .hit { fill: transparent; }
  .chart .sel { fill: none; stroke: var(--primary-text-color); stroke-width: 2; rx: 3; }
  .chart .detail { display: flex; flex-wrap: wrap; align-items: baseline; gap: 4px 10px; min-height: 28px;
                   margin: 0 0 6px; }
  .chart .detail b { font-size: 18px; font-weight: 500; color: var(--primary-text-color); }
  .chart .detail span { font-size: 13px; color: var(--secondary-text-color); }
  .chart .b { fill: var(--secondary-text-color); opacity: 0.35; }
  .chart .b.laden { fill: var(--success-color, #43a047); opacity: 1; }
  .chart .b.verkoop { fill: var(--warning-color, #ffa600); opacity: 1; }
  .chart .b.negatief { fill: var(--info-color, #039be5); opacity: 1; }
  .chart .b.negatief_venster { fill: var(--info-color, #039be5); opacity: 0.45; }
  .chart text { fill: var(--secondary-text-color); font-size: 11px; }
  .chart .zero { stroke: var(--divider-color); stroke-width: 1; }
  .chart .now { stroke: var(--primary-color); stroke-width: 1.5; stroke-dasharray: 3 3; }
  .legend { display: flex; flex-wrap: wrap; gap: 12px; margin-top: 8px; font-size: 12px; color: var(--secondary-text-color); }
  .legend i { display: inline-block; width: 10px; height: 10px; border-radius: 2px; margin-right: 5px; vertical-align: -1px; }
`;

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (c) => (
    { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]
  ));
}

// Taal: de keuze in de integratie, anders die van Home Assistant. Nederlands is de brontaal;
// de teksten voor andere talen staan in TEXTS (gegenereerd uit i18n_langs/*.json door
// scripts/build_card_texts.py, niet met de hand aanpassen).
let LANG = (typeof navigator !== "undefined" && navigator.language) || "nl";
// <texts:begin>
const TEXTS = {
  "de": {
    "Marstek Goedkoop Laden (opbrengst)": "Marstek Günstig Laden (Ertrag)",
    "Marstek Goedkoop Laden (schakelaars)": "Marstek Günstig Laden (Schalter)",
    "Marstek Goedkoop Laden": "Marstek Günstig Laden",
    "Marstek Goedkoop Laden (compact)": "Marstek Günstig Laden (kompakt)",
    "Staat uit": "Aus",
    "Zet de schakelaar aan om dit te gebruiken": "Schalter einschalten, um dies zu nutzen",
    "Verwachte opbrengst van dit plan (schatting)": "Erwarteter Ertrag dieses Plans (Schätzung)",
    "totaal": "gesamt",
    "Vandaag": "Heute",
    "week": "Woche",
    "verwacht": "erwartet",
    "Deze week": "Diese Woche",
    "Vorige week": "Letzte Woche",
    "Opbrengst": "Ertrag",
    "Deze maand": "Dieser Monat",
    "Dit jaar": "Dieses Jahr",
    "Tegels": "Kacheln",
    "Regels per onderdeel van het plan": "Zeilen je Planteil",
    "Toelichting onder de kaart": "Hinweis unter der Karte",
    "Titel": "Titel",
    "maand": "Monat",
    "Verwacht (plan)": "Erwartet (Plan)",
    "niet gevonden.": "nicht gefunden.",
    "Entiteit": "Entität",
    "Nog geen gegevens beschikbaar.": "Noch keine Daten verfügbar.",
    "Nog geen opbrengst beschikbaar.": "Noch kein Ertrag verfügbar.",
    "Nu": "Jetzt",
    "aan": "an",
    "uit": "aus",
    "Aan": "An",
    "Uit": "Aus",
    "Dat telt pas mee als het wordt gebruikt.": "Das zählt erst, wenn es genutzt wird.",
    "Er zit geen bijgeladen stroom meer in de accu.": "Im Akku ist kein geladener Strom mehr.",
    "Tijdlijn en controles van het laadplan als stroomschema.": "Zeitleiste und Prüfungen des Ladeplans als Flussdiagramm.",
    "Het stroomschema in een paar regels.": "Das Flussdiagramm in wenigen Zeilen.",
    "Opbrengst van vandaag, deze week en het huidige plan.": "Ertrag von heute, dieser Woche und des aktuellen Plans.",
    "De schakelaars voor bijladen, verkoop en negatieve prijs.": "Die Schalter für Laden, Verkauf und negativen Preis.",
    "Nog in de accu: {kwh} kWh bijgeladen stroom": "Noch im Akku: {kwh} kWh geladener Strom",
    " (kostprijs € {price} per kWh)": " (Einstandspreis € {price} pro kWh)",
    "Vandaag bijgeladen: {kwh} kWh voor € {cost}, waarvan {used} kWh gebruikt. ": "Heute geladen: {kwh} kWh für € {cost}, davon {used} kWh genutzt. ",
    "Afschrijving van de accu is meegerekend: € {wear}. ": "Die Abschreibung des Akkus ist eingerechnet: € {wear}. ",
    "Afschrijving per kWh": "Abschreibung pro kWh",
    "Bijgeladen voorraad, kostprijs, rendement en afschrijving.": "Geladener Vorrat, Einstandspreis, Wirkungsgrad und Abschreibung.",
    "Bijladen": "Laden",
    "Boven de kostprijs levert gebruiken of verkopen winst op, eronder verlies.": "Über dem Einstandspreis bringt Nutzen oder Verkaufen Gewinn, darunter Verlust.",
    "Capaciteit": "Kapazität",
    "Geen plan": "Kein Plan",
    "Geen prijzen beschikbaar.": "Keine Preise verfügbar.",
    "Geen verlies": "Kein Verlust",
    "Gepland": "Geplant",
    "Hoogte (pixels)": "Höhe (Pixel)",
    "Klaar": "Fertig",
    "Kostprijs": "Einstandspreis",
    "Laadtoestand": "Ladestand",
    "Laadtoestand tonen": "Ladestand anzeigen",
    "Laden": "Laden",
    "Marstek Goedkoop Laden (prijzen)": "Marstek Günstig Laden (Preise)",
    "Marstek Goedkoop Laden (status)": "Marstek Günstig Laden (Status)",
    "Marstek Goedkoop Laden (voorraad)": "Marstek Günstig Laden (Vorrat)",
    "Negatieve prijs": "Negativer Preis",
    "Onbekend": "Unbekannt",
    "Onderdelen": "Teile",
    "Opbrengst tonen": "Ertrag anzeigen",
    "Prijs nu": "Preis jetzt",
    "Prijs nu tonen": "Preis jetzt anzeigen",
    "Prijsgrafiek met de uren waarin wordt bijgeladen of verkocht.": "Preisdiagramm mit den Stunden, in denen geladen oder verkauft wird.",
    "Prijzen bij de staven tonen": "Preise an den Balken anzeigen",
    "Prijzen per uur in € per kWh": "Preise pro Stunde in € pro kWh",
    "Rendement": "Wirkungsgrad",
    "Tijdlijn van vandaag tonen": "Zeitleiste von heute anzeigen",
    "Uren terug": "Stunden zurück",
    "Uren vooruit (0 = tot de laatste bekende prijs)": "Stunden voraus (0 = bis zum letzten bekannten Preis)",
    "Vasthouden": "Halten",
    "Verkoop": "Verkauf",
    "Vol": "Voll",
    "Volgende stap": "Nächster Schritt",
    "Volgende stap tonen": "Nächsten Schritt anzeigen",
    "Voorraad": "Vorrat",
    "Wat er nu gebeurt, de laadtoestand, de prijs en de volgende stap.": "Was gerade passiert, der Ladestand, der Preis und der nächste Schritt."
  },
  "en": {
    "Marstek Goedkoop Laden (opbrengst)": "Marstek Cheap Charging (gain)",
    "Marstek Goedkoop Laden (schakelaars)": "Marstek Cheap Charging (switches)",
    "Marstek Goedkoop Laden": "Marstek Cheap Charging",
    "Marstek Goedkoop Laden (compact)": "Marstek Cheap Charging (compact)",
    "Staat uit": "Off",
    "Zet de schakelaar aan om dit te gebruiken": "Turn the switch on to use this",
    "Verwachte opbrengst van dit plan (schatting)": "Expected gain of this plan (estimate)",
    "totaal": "total",
    "Vandaag": "Today",
    "week": "week",
    "verwacht": "expected",
    "Deze week": "This week",
    "Vorige week": "Last week",
    "Opbrengst": "Gain",
    "Deze maand": "This month",
    "Dit jaar": "This year",
    "Tegels": "Tiles",
    "Regels per onderdeel van het plan": "Lines per part of the plan",
    "Toelichting onder de kaart": "Note below the card",
    "Titel": "Title",
    "maand": "month",
    "Verwacht (plan)": "Expected (plan)",
    "niet gevonden.": "not found.",
    "Entiteit": "Entity",
    "Nog geen gegevens beschikbaar.": "No data available yet.",
    "Nog geen opbrengst beschikbaar.": "No gain available yet.",
    "Nu": "Now",
    "aan": "on",
    "uit": "off",
    "Aan": "On",
    "Uit": "Off",
    "Dat telt pas mee als het wordt gebruikt.": "That only counts once it is used.",
    "Er zit geen bijgeladen stroom meer in de accu.": "There is no charged energy left in the battery.",
    "Tijdlijn en controles van het laadplan als stroomschema.": "Timeline and checks of the charge plan as a flow chart.",
    "Het stroomschema in een paar regels.": "The flow chart in a few lines.",
    "Opbrengst van vandaag, deze week en het huidige plan.": "Gain of today, this week and the current plan.",
    "De schakelaars voor bijladen, verkoop en negatieve prijs.": "The switches for charging, selling and negative price.",
    "Nog in de accu: {kwh} kWh bijgeladen stroom": "Still in the battery: {kwh} kWh of charged energy",
    " (kostprijs € {price} per kWh)": " (cost price € {price} per kWh)",
    "Vandaag bijgeladen: {kwh} kWh voor € {cost}, waarvan {used} kWh gebruikt. ": "Charged today: {kwh} kWh for € {cost}, of which {used} kWh used. ",
    "Afschrijving van de accu is meegerekend: € {wear}. ": "Battery depreciation is included: € {wear}. ",
    "Afschrijving per kWh": "Depreciation per kWh",
    "Bijgeladen voorraad, kostprijs, rendement en afschrijving.": "Charged stock, cost price, efficiency and depreciation.",
    "Bijladen": "Charging",
    "Boven de kostprijs levert gebruiken of verkopen winst op, eronder verlies.": "Above the cost price, using or selling earns money; below it, it loses money.",
    "Capaciteit": "Capacity",
    "Geen plan": "No plan",
    "Geen prijzen beschikbaar.": "No prices available.",
    "Geen verlies": "No loss",
    "Gepland": "Planned",
    "Hoogte (pixels)": "Height (pixels)",
    "Klaar": "Done",
    "Kostprijs": "Cost price",
    "Laadtoestand": "State of charge",
    "Laadtoestand tonen": "Show state of charge",
    "Laden": "Charging",
    "Marstek Goedkoop Laden (prijzen)": "Marstek Cheap Charging (prices)",
    "Marstek Goedkoop Laden (status)": "Marstek Cheap Charging (status)",
    "Marstek Goedkoop Laden (voorraad)": "Marstek Cheap Charging (stock)",
    "Negatieve prijs": "Negative price",
    "Onbekend": "Unknown",
    "Onderdelen": "Parts",
    "Opbrengst tonen": "Show gain",
    "Prijs nu": "Price now",
    "Prijs nu tonen": "Show price now",
    "Prijsgrafiek met de uren waarin wordt bijgeladen of verkocht.": "Price chart with the hours in which it charges or sells.",
    "Prijzen bij de staven tonen": "Show prices on the bars",
    "Prijzen per uur in € per kWh": "Prices per hour in € per kWh",
    "Rendement": "Efficiency",
    "Tijdlijn van vandaag tonen": "Show today's timeline",
    "Uren terug": "Hours back",
    "Uren vooruit (0 = tot de laatste bekende prijs)": "Hours ahead (0 = up to the last known price)",
    "Vasthouden": "Hold",
    "Verkoop": "Selling",
    "Vol": "Full",
    "Volgende stap": "Next step",
    "Volgende stap tonen": "Show next step",
    "Voorraad": "Stock",
    "Wat er nu gebeurt, de laadtoestand, de prijs en de volgende stap.": "What is happening now, the state of charge, the price and the next step."
  },
  "es": {
    "Marstek Goedkoop Laden (opbrengst)": "Marstek Carga Barata (beneficio)",
    "Marstek Goedkoop Laden (schakelaars)": "Marstek Carga Barata (interruptores)",
    "Marstek Goedkoop Laden": "Marstek Carga Barata",
    "Marstek Goedkoop Laden (compact)": "Marstek Carga Barata (compacta)",
    "Staat uit": "Desactivado",
    "Zet de schakelaar aan om dit te gebruiken": "Activa el interruptor para usar esto",
    "Verwachte opbrengst van dit plan (schatting)": "Beneficio esperado de este plan (estimación)",
    "totaal": "total",
    "Vandaag": "Hoy",
    "week": "semana",
    "verwacht": "esperado",
    "Deze week": "Esta semana",
    "Vorige week": "Semana pasada",
    "Opbrengst": "Beneficio",
    "Deze maand": "Este mes",
    "Dit jaar": "Este año",
    "Tegels": "Mosaicos",
    "Regels per onderdeel van het plan": "Líneas por parte del plan",
    "Toelichting onder de kaart": "Nota bajo la tarjeta",
    "Titel": "Título",
    "maand": "mes",
    "Verwacht (plan)": "Esperado (plan)",
    "niet gevonden.": "no encontrada.",
    "Entiteit": "Entidad",
    "Nog geen gegevens beschikbaar.": "Aún no hay datos disponibles.",
    "Nog geen opbrengst beschikbaar.": "Aún no hay beneficio disponible.",
    "Nu": "Ahora",
    "aan": "activado",
    "uit": "desactivado",
    "Aan": "Activado",
    "Uit": "Desactivado",
    "Dat telt pas mee als het wordt gebruikt.": "Eso solo cuenta cuando se usa.",
    "Er zit geen bijgeladen stroom meer in de accu.": "Ya no queda energía cargada en la batería.",
    "Tijdlijn en controles van het laadplan als stroomschema.": "Cronología y comprobaciones del plan de carga como diagrama de flujo.",
    "Het stroomschema in een paar regels.": "El diagrama de flujo en pocas líneas.",
    "Opbrengst van vandaag, deze week en het huidige plan.": "Beneficio de hoy, de esta semana y del plan actual.",
    "De schakelaars voor bijladen, verkoop en negatieve prijs.": "Los interruptores de carga, venta y precio negativo.",
    "Nog in de accu: {kwh} kWh bijgeladen stroom": "Aún en la batería: {kwh} kWh de energía cargada",
    " (kostprijs € {price} per kWh)": " (precio de coste € {price} por kWh)",
    "Vandaag bijgeladen: {kwh} kWh voor € {cost}, waarvan {used} kWh gebruikt. ": "Cargado hoy: {kwh} kWh por € {cost}, de los cuales {used} kWh usados. ",
    "Afschrijving van de accu is meegerekend: € {wear}. ": "Se ha incluido la amortización de la batería: € {wear}. ",
    "Afschrijving per kWh": "Amortización por kWh",
    "Bijgeladen voorraad, kostprijs, rendement en afschrijving.": "Existencias cargadas, precio de coste, rendimiento y amortización.",
    "Bijladen": "Carga",
    "Boven de kostprijs levert gebruiken of verkopen winst op, eronder verlies.": "Por encima del precio de coste, usar o vender da beneficio; por debajo, pérdida.",
    "Capaciteit": "Capacidad",
    "Geen plan": "Sin plan",
    "Geen prijzen beschikbaar.": "No hay precios disponibles.",
    "Geen verlies": "Sin pérdidas",
    "Gepland": "Planificado",
    "Hoogte (pixels)": "Altura (píxeles)",
    "Klaar": "Listo",
    "Kostprijs": "Precio de coste",
    "Laadtoestand": "Nivel de carga",
    "Laadtoestand tonen": "Mostrar nivel de carga",
    "Laden": "Cargando",
    "Marstek Goedkoop Laden (prijzen)": "Marstek Carga Barata (precios)",
    "Marstek Goedkoop Laden (status)": "Marstek Carga Barata (estado)",
    "Marstek Goedkoop Laden (voorraad)": "Marstek Carga Barata (existencias)",
    "Negatieve prijs": "Precio negativo",
    "Onbekend": "Desconocido",
    "Onderdelen": "Partes",
    "Opbrengst tonen": "Mostrar beneficio",
    "Prijs nu": "Precio actual",
    "Prijs nu tonen": "Mostrar precio actual",
    "Prijsgrafiek met de uren waarin wordt bijgeladen of verkocht.": "Gráfico de precios con las horas en las que se carga o se vende.",
    "Prijzen bij de staven tonen": "Mostrar precios sobre las barras",
    "Prijzen per uur in € per kWh": "Precios por hora en € por kWh",
    "Rendement": "Rendimiento",
    "Tijdlijn van vandaag tonen": "Mostrar la cronología de hoy",
    "Uren terug": "Horas atrás",
    "Uren vooruit (0 = tot de laatste bekende prijs)": "Horas por delante (0 = hasta el último precio conocido)",
    "Vasthouden": "Retener",
    "Verkoop": "Venta",
    "Vol": "Llena",
    "Volgende stap": "Siguiente paso",
    "Volgende stap tonen": "Mostrar siguiente paso",
    "Voorraad": "Existencias",
    "Wat er nu gebeurt, de laadtoestand, de prijs en de volgende stap.": "Qué pasa ahora, el nivel de carga, el precio y el siguiente paso."
  },
  "fr": {
    "Marstek Goedkoop Laden (opbrengst)": "Marstek Charge économique (gain)",
    "Marstek Goedkoop Laden (schakelaars)": "Marstek Charge économique (interrupteurs)",
    "Marstek Goedkoop Laden": "Marstek Charge économique",
    "Marstek Goedkoop Laden (compact)": "Marstek Charge économique (compact)",
    "Staat uit": "Désactivé",
    "Zet de schakelaar aan om dit te gebruiken": "Activez l'interrupteur pour l'utiliser",
    "Verwachte opbrengst van dit plan (schatting)": "Gain attendu de ce plan (estimation)",
    "totaal": "total",
    "Vandaag": "Aujourd'hui",
    "week": "semaine",
    "verwacht": "attendu",
    "Deze week": "Cette semaine",
    "Vorige week": "Semaine dernière",
    "Opbrengst": "Gain",
    "Deze maand": "Ce mois-ci",
    "Dit jaar": "Cette année",
    "Tegels": "Tuiles",
    "Regels per onderdeel van het plan": "Lignes par partie du plan",
    "Toelichting onder de kaart": "Note sous la carte",
    "Titel": "Titre",
    "maand": "mois",
    "Verwacht (plan)": "Attendu (plan)",
    "niet gevonden.": "introuvable.",
    "Entiteit": "Entité",
    "Nog geen gegevens beschikbaar.": "Aucune donnée disponible pour l'instant.",
    "Nog geen opbrengst beschikbaar.": "Aucun gain disponible pour l'instant.",
    "Nu": "Maintenant",
    "aan": "activé",
    "uit": "désactivé",
    "Aan": "Activé",
    "Uit": "Désactivé",
    "Dat telt pas mee als het wordt gebruikt.": "Cela ne compte qu'une fois utilisé.",
    "Er zit geen bijgeladen stroom meer in de accu.": "Il ne reste plus d'énergie chargée dans la batterie.",
    "Tijdlijn en controles van het laadplan als stroomschema.": "Chronologie et contrôles du plan de charge sous forme de schéma de flux.",
    "Het stroomschema in een paar regels.": "Le schéma de flux en quelques lignes.",
    "Opbrengst van vandaag, deze week en het huidige plan.": "Gain d'aujourd'hui, de cette semaine et du plan actuel.",
    "De schakelaars voor bijladen, verkoop en negatieve prijs.": "Les interrupteurs pour la charge, la vente et le prix négatif.",
    "Nog in de accu: {kwh} kWh bijgeladen stroom": "Encore dans la batterie : {kwh} kWh d'énergie chargée",
    " (kostprijs € {price} per kWh)": " (prix de revient € {price} par kWh)",
    "Vandaag bijgeladen: {kwh} kWh voor € {cost}, waarvan {used} kWh gebruikt. ": "Chargé aujourd'hui : {kwh} kWh pour € {cost}, dont {used} kWh utilisés. ",
    "Afschrijving van de accu is meegerekend: € {wear}. ": "L'amortissement de la batterie est inclus : € {wear}. ",
    "Afschrijving per kWh": "Amortissement par kWh",
    "Bijgeladen voorraad, kostprijs, rendement en afschrijving.": "Stock chargé, prix de revient, rendement et amortissement.",
    "Bijladen": "Charge",
    "Boven de kostprijs levert gebruiken of verkopen winst op, eronder verlies.": "Au-dessus du prix de revient, utiliser ou vendre rapporte ; en dessous, cela fait perdre de l'argent.",
    "Capaciteit": "Capacité",
    "Geen plan": "Pas de plan",
    "Geen prijzen beschikbaar.": "Aucun prix disponible.",
    "Geen verlies": "Sans perte",
    "Gepland": "Planifié",
    "Hoogte (pixels)": "Hauteur (pixels)",
    "Klaar": "Terminé",
    "Kostprijs": "Prix de revient",
    "Laadtoestand": "Niveau de charge",
    "Laadtoestand tonen": "Afficher le niveau de charge",
    "Laden": "Charge",
    "Marstek Goedkoop Laden (prijzen)": "Marstek Charge économique (prix)",
    "Marstek Goedkoop Laden (status)": "Marstek Charge économique (état)",
    "Marstek Goedkoop Laden (voorraad)": "Marstek Charge économique (stock)",
    "Negatieve prijs": "Prix négatif",
    "Onbekend": "Inconnu",
    "Onderdelen": "Parties",
    "Opbrengst tonen": "Afficher le gain",
    "Prijs nu": "Prix actuel",
    "Prijs nu tonen": "Afficher le prix actuel",
    "Prijsgrafiek met de uren waarin wordt bijgeladen of verkocht.": "Graphique des prix avec les heures de charge ou de vente.",
    "Prijzen bij de staven tonen": "Afficher les prix sur les barres",
    "Prijzen per uur in € per kWh": "Prix par heure en € par kWh",
    "Rendement": "Rendement",
    "Tijdlijn van vandaag tonen": "Afficher la chronologie du jour",
    "Uren terug": "Heures passées",
    "Uren vooruit (0 = tot de laatste bekende prijs)": "Heures à venir (0 = jusqu'au dernier prix connu)",
    "Vasthouden": "Maintien",
    "Verkoop": "Vente",
    "Vol": "Pleine",
    "Volgende stap": "Étape suivante",
    "Volgende stap tonen": "Afficher l'étape suivante",
    "Voorraad": "Stock",
    "Wat er nu gebeurt, de laadtoestand, de prijs en de volgende stap.": "Ce qui se passe maintenant, le niveau de charge, le prix et l'étape suivante."
  },
  "fy": {
    "Marstek Goedkoop Laden (opbrengst)": "Marstek Goedkeap Lade (opbringst)",
    "Marstek Goedkoop Laden (schakelaars)": "Marstek Goedkeap Lade (skeakelers)",
    "Marstek Goedkoop Laden": "Marstek Goedkeap Lade",
    "Marstek Goedkoop Laden (compact)": "Marstek Goedkeap Lade (kompakt)",
    "Staat uit": "Stiet út",
    "Zet de schakelaar aan om dit te gebruiken": "Set de skeakeler oan om dit te brûken",
    "Verwachte opbrengst van dit plan (schatting)": "Ferwachte opbringst fan dit plan (skatting)",
    "totaal": "totaal",
    "Vandaag": "Hjoed",
    "week": "wike",
    "verwacht": "ferwachte",
    "Deze week": "Dizze wike",
    "Vorige week": "Foarige wike",
    "Opbrengst": "Opbringst",
    "Deze maand": "Dizze moanne",
    "Dit jaar": "Dit jier",
    "Tegels": "Tegels",
    "Regels per onderdeel van het plan": "Rigels per ûnderdiel fan it plan",
    "Toelichting onder de kaart": "Taljochting ûnder de kaart",
    "Titel": "Titel",
    "maand": "moanne",
    "Verwacht (plan)": "Ferwachte (plan)",
    "niet gevonden.": "net fûn.",
    "Entiteit": "Entiteit",
    "Nog geen gegevens beschikbaar.": "Noch gjin gegevens beskikber.",
    "Nog geen opbrengst beschikbaar.": "Noch gjin opbringst beskikber.",
    "Nu": "No",
    "aan": "oan",
    "uit": "út",
    "Aan": "Oan",
    "Uit": "Út",
    "Dat telt pas mee als het wordt gebruikt.": "Dat telt pas mei as it brûkt wurdt.",
    "Er zit geen bijgeladen stroom meer in de accu.": "Der sit gjin byladen stroom mear yn de accu.",
    "Tijdlijn en controles van het laadplan als stroomschema.": "Tiidline en kontrôles fan it laadplan as stroomskema.",
    "Het stroomschema in een paar regels.": "It stroomskema yn in pear rigels.",
    "Opbrengst van vandaag, deze week en het huidige plan.": "Opbringst fan hjoed, dizze wike en it hjoeddeistige plan.",
    "De schakelaars voor bijladen, verkoop en negatieve prijs.": "De skeakelers foar bylade, ferkeap en negative priis.",
    "Nog in de accu: {kwh} kWh bijgeladen stroom": "Noch yn de accu: {kwh} kWh byladen stroom",
    " (kostprijs € {price} per kWh)": " (kostpriis € {price} per kWh)",
    "Vandaag bijgeladen: {kwh} kWh voor € {cost}, waarvan {used} kWh gebruikt. ": "Hjoed byladen: {kwh} kWh foar € {cost}, wêrfan {used} kWh brûkt. ",
    "Afschrijving van de accu is meegerekend: € {wear}. ": "Ôfskriuwing fan de accu is meirekkene: € {wear}. ",
    "Afschrijving per kWh": "Ôfskriuwing per kWh",
    "Bijgeladen voorraad, kostprijs, rendement en afschrijving.": "Byladen foarried, kostpriis, rendemint en ôfskriuwing.",
    "Bijladen": "Bylade",
    "Boven de kostprijs levert gebruiken of verkopen winst op, eronder verlies.": "Boppe de kostpriis jout brûke of ferkeapje winst, dêrûnder ferlies.",
    "Capaciteit": "Kapasiteit",
    "Geen plan": "Gjin plan",
    "Geen prijzen beschikbaar.": "Gjin prizen beskikber.",
    "Geen verlies": "Gjin ferlies",
    "Gepland": "Pland",
    "Hoogte (pixels)": "Hichte (piksels)",
    "Klaar": "Klear",
    "Kostprijs": "Kostpriis",
    "Laadtoestand": "Laadnivo",
    "Laadtoestand tonen": "Laadnivo sjen litte",
    "Laden": "Lade",
    "Marstek Goedkoop Laden (prijzen)": "Marstek Goedkeap Lade (prizen)",
    "Marstek Goedkoop Laden (status)": "Marstek Goedkeap Lade (status)",
    "Marstek Goedkoop Laden (voorraad)": "Marstek Goedkeap Lade (foarried)",
    "Negatieve prijs": "Negative priis",
    "Onbekend": "Ûnbekend",
    "Onderdelen": "Ûnderdielen",
    "Opbrengst tonen": "Opbringst sjen litte",
    "Prijs nu": "Priis no",
    "Prijs nu tonen": "Priis no sjen litte",
    "Prijsgrafiek met de uren waarin wordt bijgeladen of verkocht.": "Priisgrafyk mei de oeren dêr't yn byladen of ferkocht wurdt.",
    "Prijzen bij de staven tonen": "Prizen by de balken sjen litte",
    "Prijzen per uur in € per kWh": "Prizen per oere yn € per kWh",
    "Rendement": "Rendemint",
    "Tijdlijn van vandaag tonen": "Tiidline fan hjoed sjen litte",
    "Uren terug": "Oeren werom",
    "Uren vooruit (0 = tot de laatste bekende prijs)": "Oeren foarút (0 = oant de lêste bekende priis)",
    "Vasthouden": "Fêsthâlde",
    "Verkoop": "Ferkeap",
    "Vol": "Fol",
    "Volgende stap": "Folgjende stap",
    "Volgende stap tonen": "Folgjende stap sjen litte",
    "Voorraad": "Foarried",
    "Wat er nu gebeurt, de laadtoestand, de prijs en de volgende stap.": "Wat der no bart, it laadnivo, de priis en de folgjende stap."
  },
  "nb": {
    "Marstek Goedkoop Laden (opbrengst)": "Marstek Billig Lading (gevinst)",
    "Marstek Goedkoop Laden (schakelaars)": "Marstek Billig Lading (brytere)",
    "Marstek Goedkoop Laden": "Marstek Billig Lading",
    "Marstek Goedkoop Laden (compact)": "Marstek Billig Lading (kompakt)",
    "Staat uit": "Av",
    "Zet de schakelaar aan om dit te gebruiken": "Slå på bryteren for å bruke dette",
    "Verwachte opbrengst van dit plan (schatting)": "Forventet gevinst for denne planen (estimat)",
    "totaal": "totalt",
    "Vandaag": "I dag",
    "week": "uke",
    "verwacht": "forventet",
    "Deze week": "Denne uken",
    "Vorige week": "Forrige uke",
    "Opbrengst": "Gevinst",
    "Deze maand": "Denne måneden",
    "Dit jaar": "I år",
    "Tegels": "Fliser",
    "Regels per onderdeel van het plan": "Linjer per del av planen",
    "Toelichting onder de kaart": "Merknad under kortet",
    "Titel": "Tittel",
    "maand": "måned",
    "Verwacht (plan)": "Forventet (plan)",
    "niet gevonden.": "ikke funnet.",
    "Entiteit": "Entitet",
    "Nog geen gegevens beschikbaar.": "Ingen data tilgjengelig ennå.",
    "Nog geen opbrengst beschikbaar.": "Ingen gevinst tilgjengelig ennå.",
    "Nu": "Nå",
    "aan": "på",
    "uit": "av",
    "Aan": "På",
    "Uit": "Av",
    "Dat telt pas mee als het wordt gebruikt.": "Det teller først med når det brukes.",
    "Er zit geen bijgeladen stroom meer in de accu.": "Det er ikke mer ladet strøm igjen i batteriet.",
    "Tijdlijn en controles van het laadplan als stroomschema.": "Tidslinje og kontroller for ladeplanen som flytskjema.",
    "Het stroomschema in een paar regels.": "Flytskjemaet i noen få linjer.",
    "Opbrengst van vandaag, deze week en het huidige plan.": "Gevinst i dag, denne uken og for gjeldende plan.",
    "De schakelaars voor bijladen, verkoop en negatieve prijs.": "Bryterne for lading, salg og negativ pris.",
    "Nog in de accu: {kwh} kWh bijgeladen stroom": "Fortsatt i batteriet: {kwh} kWh ladet strøm",
    " (kostprijs € {price} per kWh)": " (kostpris € {price} per kWh)",
    "Vandaag bijgeladen: {kwh} kWh voor € {cost}, waarvan {used} kWh gebruikt. ": "Ladet i dag: {kwh} kWh for € {cost}, hvorav {used} kWh brukt. ",
    "Afschrijving van de accu is meegerekend: € {wear}. ": "Avskrivning av batteriet er medregnet: € {wear}. ",
    "Afschrijving per kWh": "Avskrivning per kWh",
    "Bijgeladen voorraad, kostprijs, rendement en afschrijving.": "Ladet beholdning, kostpris, virkningsgrad og avskrivning.",
    "Bijladen": "Lading",
    "Boven de kostprijs levert gebruiken of verkopen winst op, eronder verlies.": "Over kostprisen gir bruk eller salg gevinst, under kostprisen gir det tap.",
    "Capaciteit": "Kapasitet",
    "Geen plan": "Ingen plan",
    "Geen prijzen beschikbaar.": "Ingen priser tilgjengelig.",
    "Geen verlies": "Ingen tap",
    "Gepland": "Planlagt",
    "Hoogte (pixels)": "Høyde (piksler)",
    "Klaar": "Ferdig",
    "Kostprijs": "Kostpris",
    "Laadtoestand": "Ladenivå",
    "Laadtoestand tonen": "Vis ladenivå",
    "Laden": "Lader",
    "Marstek Goedkoop Laden (prijzen)": "Marstek Billig Lading (priser)",
    "Marstek Goedkoop Laden (status)": "Marstek Billig Lading (status)",
    "Marstek Goedkoop Laden (voorraad)": "Marstek Billig Lading (beholdning)",
    "Negatieve prijs": "Negativ pris",
    "Onbekend": "Ukjent",
    "Onderdelen": "Deler",
    "Opbrengst tonen": "Vis gevinst",
    "Prijs nu": "Pris nå",
    "Prijs nu tonen": "Vis pris nå",
    "Prijsgrafiek met de uren waarin wordt bijgeladen of verkocht.": "Prisdiagram med timene det lades eller selges i.",
    "Prijzen bij de staven tonen": "Vis priser ved søylene",
    "Prijzen per uur in € per kWh": "Priser per time i € per kWh",
    "Rendement": "Virkningsgrad",
    "Tijdlijn van vandaag tonen": "Vis dagens tidslinje",
    "Uren terug": "Timer tilbake",
    "Uren vooruit (0 = tot de laatste bekende prijs)": "Timer fremover (0 = til siste kjente pris)",
    "Vasthouden": "Tilbakehold",
    "Verkoop": "Salg",
    "Vol": "Full",
    "Volgende stap": "Neste trinn",
    "Volgende stap tonen": "Vis neste trinn",
    "Voorraad": "Beholdning",
    "Wat er nu gebeurt, de laadtoestand, de prijs en de volgende stap.": "Hva som skjer nå, ladenivået, prisen og neste trinn."
  },
  "sv": {
    "Marstek Goedkoop Laden (opbrengst)": "Marstek Goedkoop Laden (vinst)",
    "Marstek Goedkoop Laden (schakelaars)": "Marstek Goedkoop Laden (brytare)",
    "Marstek Goedkoop Laden": "Marstek Goedkoop Laden",
    "Marstek Goedkoop Laden (compact)": "Marstek Goedkoop Laden (kompakt)",
    "Staat uit": "Avstängd",
    "Zet de schakelaar aan om dit te gebruiken": "Slå på brytaren för att använda detta",
    "Verwachte opbrengst van dit plan (schatting)": "Förväntad vinst för denna plan (uppskattning)",
    "totaal": "totalt",
    "Vandaag": "Idag",
    "week": "vecka",
    "verwacht": "förväntat",
    "Deze week": "Denna vecka",
    "Vorige week": "Förra veckan",
    "Opbrengst": "Vinst",
    "Deze maand": "Denna månad",
    "Dit jaar": "I år",
    "Tegels": "Rutor",
    "Regels per onderdeel van het plan": "Rader per del av planen",
    "Toelichting onder de kaart": "Förklaring under kortet",
    "Titel": "Rubrik",
    "maand": "månad",
    "Verwacht (plan)": "Förväntat (plan)",
    "niet gevonden.": "hittades inte.",
    "Entiteit": "Entitet",
    "Nog geen gegevens beschikbaar.": "Inga data tillgängliga än.",
    "Nog geen opbrengst beschikbaar.": "Ingen vinst tillgänglig än.",
    "Nu": "Nu",
    "aan": "på",
    "uit": "av",
    "Aan": "På",
    "Uit": "Av",
    "Dat telt pas mee als het wordt gebruikt.": "Det räknas först när det används.",
    "Er zit geen bijgeladen stroom meer in de accu.": "Det finns ingen laddad el kvar i batteriet.",
    "Tijdlijn en controles van het laadplan als stroomschema.": "Laddningsplanens tidslinje och kontroller som flödesschema.",
    "Het stroomschema in een paar regels.": "Flödesschemat i några få rader.",
    "Opbrengst van vandaag, deze week en het huidige plan.": "Vinst för idag, denna vecka och den aktuella planen.",
    "De schakelaars voor bijladen, verkoop en negatieve prijs.": "Brytarna för laddning, försäljning och negativt pris.",
    "Nog in de accu: {kwh} kWh bijgeladen stroom": "Kvar i batteriet: {kwh} kWh laddad el",
    " (kostprijs € {price} per kWh)": " (kostnadspris € {price} per kWh)",
    "Vandaag bijgeladen: {kwh} kWh voor € {cost}, waarvan {used} kWh gebruikt. ": "Laddat idag: {kwh} kWh för € {cost}, varav {used} kWh använt. ",
    "Afschrijving van de accu is meegerekend: € {wear}. ": "Batteriets avskrivning är inräknad: € {wear}. ",
    "Afschrijving per kWh": "Avskrivning per kWh",
    "Bijgeladen voorraad, kostprijs, rendement en afschrijving.": "Laddat lager, kostnadspris, verkningsgrad och avskrivning.",
    "Bijladen": "Laddning",
    "Boven de kostprijs levert gebruiken of verkopen winst op, eronder verlies.": "Över kostnadspriset ger användning eller försäljning vinst, under det förlust.",
    "Capaciteit": "Kapacitet",
    "Geen plan": "Ingen plan",
    "Geen prijzen beschikbaar.": "Inga priser tillgängliga.",
    "Geen verlies": "Ingen förlust",
    "Gepland": "Planerad",
    "Hoogte (pixels)": "Höjd (pixlar)",
    "Klaar": "Klar",
    "Kostprijs": "Kostnadspris",
    "Laadtoestand": "Laddningsnivå",
    "Laadtoestand tonen": "Visa laddningsnivå",
    "Laden": "Laddar",
    "Marstek Goedkoop Laden (prijzen)": "Marstek Goedkoop Laden (priser)",
    "Marstek Goedkoop Laden (status)": "Marstek Goedkoop Laden (status)",
    "Marstek Goedkoop Laden (voorraad)": "Marstek Goedkoop Laden (lager)",
    "Negatieve prijs": "Negativt pris",
    "Onbekend": "Okänd",
    "Onderdelen": "Delar",
    "Opbrengst tonen": "Visa vinst",
    "Prijs nu": "Pris nu",
    "Prijs nu tonen": "Visa pris nu",
    "Prijsgrafiek met de uren waarin wordt bijgeladen of verkocht.": "Prisdiagram med timmarna då det laddas eller säljs.",
    "Prijzen bij de staven tonen": "Visa priser vid staplarna",
    "Prijzen per uur in € per kWh": "Priser per timme i € per kWh",
    "Rendement": "Verkningsgrad",
    "Tijdlijn van vandaag tonen": "Visa dagens tidslinje",
    "Uren terug": "Timmar bakåt",
    "Uren vooruit (0 = tot de laatste bekende prijs)": "Timmar framåt (0 = till det sista kända priset)",
    "Vasthouden": "Spärr",
    "Verkoop": "Försäljning",
    "Vol": "Fullt",
    "Volgende stap": "Nästa steg",
    "Volgende stap tonen": "Visa nästa steg",
    "Voorraad": "Lager",
    "Wat er nu gebeurt, de laadtoestand, de prijs en de volgende stap.": "Vad som händer nu, laddningsnivån, priset och nästa steg."
  }
};
// <texts:end>
function langCode() {
  const code = String(LANG || "nl").toLowerCase().replace("_", "-");
  for (let candidate of [code, code.split("-")[0]]) {
    if (candidate === "no" || candidate === "nn") candidate = "nb";
    if (candidate === "nl" || TEXTS[candidate]) return candidate;
  }
  return "en";
}
function t(nl, vars) {
  const code = langCode();
  let text = code === "nl" ? nl : ((TEXTS[code] || TEXTS.en || {})[nl] ?? nl);
  if (vars) for (const key of Object.keys(vars)) text = text.split("{" + key + "}").join(vars[key]);
  return text;
}

function number(value, digits) {
  const text = Number(value || 0).toFixed(digits);
  return langCode() === "en" ? text : text.replace(".", ",");
}

function formatEuro(value) {
  const sign = value > 0.004 ? "+ " : value < -0.004 ? "− " : "";
  return `${sign}€ ${number(Math.abs(value || 0), 2)}`;
}

function tone(value) {
  return value > 0.004 ? "plus" : value < -0.004 ? "min" : "";
}

function renderSteps(steps) {
  return steps.map((item, index) => {
    const kind = ICONS[item.soort] ? item.soort : "eind";
    const last = index === steps.length - 1;
    return `
      <div class="step ${kind}">
        <div class="rail">
          <div class="dot"><ha-icon icon="${ICONS[kind]}"></ha-icon></div>
          ${last ? "" : '<div class="line"></div>'}
        </div>
        <div class="text"><b>${escapeHtml(item.titel)}</b><span>${escapeHtml(item.detail)}</span></div>
      </div>`;
  }).join("");
}

function laneSteps(lane) {
  return lane.aan
    ? lane.stappen || []
    : [{ titel: t("Staat uit"), detail: t("Zet de schakelaar aan om dit te gebruiken"), soort: "eind" }];
}

function renderExpectedRows(result) {
  return (result.regels || []).map((line) => `
    <div class="row">
      <div><b>${escapeHtml(line.titel)}</b><br>${escapeHtml(line.detail)}</div>
      <div class="amount ${line.bedrag == null ? "" : tone(line.bedrag)}">${line.bedrag == null ? "–" : formatEuro(line.bedrag)}</div>
    </div>`).join("");
}

function renderExpected(result) {
  if (!result || !Array.isArray(result.regels)) return "";
  return `
    <div class="head"><ha-icon icon="mdi:cash-check"></ha-icon><span>${t("Opbrengst")}</span></div>
    <div class="tiles">
      <div class="tile"><small>${t("Vandaag")}</small><b class="${tone(result.vandaag)}">${formatEuro(result.vandaag || 0)}</b></div>
      <div class="tile"><small>${t("Deze week")}</small><b class="${tone(result.week)}">${formatEuro(result.week || 0)}</b></div>
      ${result.vorige_week == null ? "" : `<div class="tile"><small>${t("Vorige week")}</small><b class="${tone(result.vorige_week)}">${formatEuro(result.vorige_week)}</b></div>`}
      <div class="tile"><small>${t("Deze maand")}</small><b class="${tone(result.maand)}">${formatEuro(result.maand || 0)}</b></div>
      <div class="tile"><small>${t("Dit jaar")}</small><b class="${tone(result.jaar)}">${formatEuro(result.jaar || 0)}</b></div>
    </div>
    <div class="head"><ha-icon icon="mdi:cash-multiple"></ha-icon><span>${t("Verwachte opbrengst van dit plan (schatting)")}</span></div>
    <div class="result">
      <div class="total ${tone(result.totaal)}">${formatEuro(result.totaal)}<small>${t("totaal")}</small></div>
      <div class="rows">${renderExpectedRows(result)}</div>
    </div>`;
}

function renderGainLine(result) {
  if (!result) return "";
  const part = (label, value) => `${label} <b class="${tone(value)}">${formatEuro(value || 0)}</b>`;
  return `
    <div class="crow">
      <ha-icon icon="mdi:cash-multiple"></ha-icon>
      <div class="main">${part(t("Vandaag"), result.vandaag)} · ${part(t("week"), result.week)} · ${part(t("maand"), result.maand)} · ${part(t("verwacht"), result.totaal)}</div>
      <div></div>
    </div>`;
}

const LANE_IDS = ["bijladen", "verkoop", "negatief", "vasthouden", "geen_verlies"];
const LANE_LABELS = {
  bijladen: "Bijladen", verkoop: "Verkoop", negatief: "Negatieve prijs",
  vasthouden: "Vasthouden", geen_verlies: "Geen verlies",
};

// De laadplan-sensor: de opgegeven entiteit, anders de eerste sensor met een stroomschema.
function findEntity(hass, wanted) {
  if (!hass || !hass.states) return wanted;
  if (wanted && hass.states[wanted]) return wanted;
  const found = Object.keys(hass.states).find((id) => (
    id.startsWith("sensor.") && hass.states[id].attributes && hass.states[id].attributes.stroomschema
  ));
  return found || wanted || DEFAULT_ENTITY;
}

function pickLanes(flow, cfg) {
  const all = flow.banen || [];
  return Array.isArray(cfg.lanes) && cfg.lanes.length ? all.filter((lane) => cfg.lanes.includes(lane.id)) : all;
}

// Instellingen in de visuele editor.
const FIELD_LABELS = {
  entity: "Entiteit", title: "Titel", opbrengst: "Opbrengst tonen",
  show_timeline: "Tijdlijn van vandaag tonen", lanes: "Onderdelen", tiles: "Tegels",
  expected_details: "Regels per onderdeel van het plan", notes: "Toelichting onder de kaart",
  show_soc: "Laadtoestand tonen", show_price: "Prijs nu tonen", show_next: "Volgende stap tonen",
  hours_back: "Uren terug", hours_ahead: "Uren vooruit (0 = tot de laatste bekende prijs)",
  show_values: "Prijzen bij de staven tonen", height: "Hoogte (pixels)",
};
const FIELD = {
  entity: { name: "entity", selector: { entity: { domain: "sensor", integration: "marstek_goedkoop_laden" } } },
  title: { name: "title", selector: { text: {} } },
  lanes: () => ({
    name: "lanes",
    selector: { select: { multiple: true, mode: "list", options: LANE_IDS.map((id) => ({ value: id, label: t(LANE_LABELS[id]) })) } },
  }),
  bool: (name) => ({ name, selector: { boolean: {} } }),
  number: (name, min, max) => ({ name, selector: { number: { min, max, mode: "box" } } }),
  tiles: (keys, labels) => () => ({
    name: "tiles",
    selector: { select: { multiple: true, mode: "list", options: keys.map((key) => ({ value: key, label: t(labels[key]) })) } },
  }),
};
function configForm(fields) {
  return {
    schema: fields.map((field) => (typeof field === "function" ? field() : field)),
    computeLabel: (schema) => t(FIELD_LABELS[schema.name] || schema.name),
  };
}

class MarstekBaseCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._config = {};
    this._signature = null;
  }

  static getStubConfig(hass) {
    return { entity: findEntity(hass, DEFAULT_ENTITY) };
  }

  static getConfigForm() {
    return configForm([FIELD.entity, FIELD.title]);
  }

  setConfig(config) {
    this._config = { ...(config || {}) };
    this._signature = null;
    if (this._hass) this._render();
  }

  set hass(hass) {
    this._hass = hass;
    LANG = (hass && (hass.language || (hass.locale && hass.locale.language))) || "nl";
    const shown = hass && hass.states && hass.states[findEntity(hass, this._config.entity)];
    const chosen = shown && shown.attributes && shown.attributes.stroomschema && shown.attributes.stroomschema.taal;
    if (chosen) LANG = chosen;
    this._render();
  }

  getGridOptions() {
    return { columns: 12, min_columns: 6 };
  }

  _clock() {
    const now = new Date();
    return `${String(now.getHours()).padStart(2, "0")}:${String(now.getMinutes()).padStart(2, "0")}`;
  }

  _render() {
    this._entityId = findEntity(this._hass, this._config.entity);
    const state = this._hass && this._hass.states[this._entityId];
    const flow = state && state.attributes && state.attributes.stroomschema;
    const clock = this._clock();
    const signature = JSON.stringify([this._config, flow || (state ? "geen" : "weg"), clock, LANG]);
    if (signature === this._signature) return;
    this._signature = signature;

    let body;
    if (!state) {
      body = `<div class="empty">${t("Entiteit")} ${escapeHtml(this._entityId)} ${t("niet gevonden.")}</div>`;
    } else if (!flow || !Array.isArray(flow.tijdlijn)) {
      body = `<div class="empty">${t("Nog geen gegevens beschikbaar.")}</div>`;
    } else {
      body = this._body(flow, clock, state);
    }
    const title = this._config.title ? `<div class="title">${escapeHtml(this._config.title)}</div>` : "";
    this.shadowRoot.innerHTML = `<style>${STYLE}</style><ha-card class="${this._cardClass()}">${title}${body}</ha-card>`;
  }

  _cardClass() {
    return "";
  }

  _timeline(flow, clock) {
    return flow.tijdlijn.map((item) => (
      item.soort === "nu" ? { ...item, titel: `${t("Nu")} · ${clock}` } : item
    ));
  }
}

class MarstekGoedkoopLadenCard extends MarstekBaseCard {
  static getConfigForm() {
    return configForm([FIELD.entity, FIELD.title, FIELD.bool("show_timeline"), FIELD.lanes, FIELD.bool("opbrengst")]);
  }

  getCardSize() {
    return this._config.compact ? 3 : 6;
  }

  _cardClass() {
    return this._config.compact ? "compact" : "";
  }

  _body(flow, clock) {
    return this._config.compact ? this._compact(flow, clock) : this._full(flow, clock);
  }

  _full(flow, clock) {
    const lanes = pickLanes(flow, this._config).map((lane) => `
      <div class="lane ${lane.aan ? "aan" : "uit"}">
        <div class="head">
          <ha-icon icon="${escapeHtml(lane.icoon || "mdi:help-circle-outline")}"></ha-icon>
          <span>${escapeHtml(lane.titel)} · ${lane.aan ? t("aan") : `<span class="off">${t("uit")}</span>`}</span>
        </div>
        ${renderSteps(laneSteps(lane))}
      </div>`).join("");
    const result = this._config.opbrengst === true && flow.resultaat
      ? `<div class="divider"></div>${renderExpected(flow.resultaat)}`
      : "";
    const timeline = this._config.show_timeline === false ? "" : `
      <div class="head"><ha-icon icon="mdi:clock-outline"></ha-icon><span>${t("Vandaag")}</span></div>
      ${renderSteps(this._timeline(flow, clock))}`;
    const divider = timeline || result ? '<div class="divider"></div>' : "";
    return `${timeline}${result}${divider}<div class="lanes">${lanes}</div>`;
  }

  _compact(flow, clock) {
    const timeline = this._config.show_timeline === false ? "" : this._timeline(flow, clock).map((item) => {
      const kind = ICONS[item.soort] ? item.soort : "eind";
      return `
        <div class="crow ${kind}">
          <div class="pip"></div>
          <div class="main"><b>${escapeHtml(item.titel)}</b> · ${escapeHtml(item.detail)}</div>
          <div></div>
        </div>`;
    }).join("");
    const lanes = pickLanes(flow, this._config).map((lane) => {
      const steps = laneSteps(lane);
      const last = steps[steps.length - 1] || { titel: "", detail: "", soort: "eind" };
      const stop = steps.find((item) => item.soort === "stop");
      const reason = !lane.aan ? "" : stop ? `${stop.titel} (${stop.detail})` : last.detail;
      return `
        <div class="crow ${lane.aan ? "" : "uit"}">
          <ha-icon icon="${escapeHtml(lane.icoon || "mdi:help-circle-outline")}"></ha-icon>
          <div class="main"><b>${escapeHtml(lane.titel)}</b>${reason ? ` · ${escapeHtml(reason)}` : ""}</div>
          <div class="out ${last.soort === "actie" ? "actie" : ""}">${escapeHtml(lane.aan ? last.titel : t("Uit"))}</div>
        </div>`;
    }).join("");
    const gain = this._config.opbrengst === false ? "" : renderGainLine(flow.resultaat);
    return `${timeline}${timeline ? '<div class="divider"></div>' : ""}${lanes}${gain ? `<div class="divider"></div>${gain}` : ""}`;
  }
}

class MarstekGoedkoopLadenCompactCard extends MarstekGoedkoopLadenCard {
  static getConfigForm() {
    return configForm([FIELD.entity, FIELD.title, FIELD.bool("show_timeline"), FIELD.lanes, FIELD.bool("opbrengst")]);
  }

  setConfig(config) {
    super.setConfig({ ...(config || {}), compact: true });
  }
}

const TILE_KEYS = ["vandaag", "week", "vorige_week", "maand", "jaar", "verwacht"];
const TILE_LABELS = {
  vandaag: "Vandaag", week: "Deze week", vorige_week: "Vorige week",
  maand: "Deze maand", jaar: "Dit jaar", verwacht: "Verwacht (plan)",
};

class MarstekGoedkoopLadenOpbrengstCard extends MarstekBaseCard {
  getCardSize() {
    return 4;
  }

  _body(flow) {
    const result = flow.resultaat;
    if (!result) return `<div class="empty">${t("Nog geen opbrengst beschikbaar.")}</div>`;
    const tile = (label, value) => `
      <div class="tile"><small>${label}</small><b class="${tone(value)}">${formatEuro(value || 0)}</b></div>`;
    const cfg = this._config;
    const wanted = Array.isArray(cfg.tiles) ? cfg.tiles : TILE_KEYS;
    const values = {
      vandaag: result.vandaag, week: result.week, vorige_week: result.vorige_week,
      maand: result.maand, jaar: result.jaar, verwacht: result.totaal,
    };
    const tiles = wanted
      .filter((key) => TILE_LABELS[key] && values[key] != null)
      .map((key) => tile(t(TILE_LABELS[key]), values[key]))
      .join("");
    const stock = result.voorraad_kwh > 0.005
      ? t("Nog in de accu: {kwh} kWh bijgeladen stroom", { kwh: number(result.voorraad_kwh, 1) })
        + (result.voorraad_prijs != null ? t(" (kostprijs € {price} per kWh)", { price: number(result.voorraad_prijs, 2) }) : "")
        + `. ${t("Dat telt pas mee als het wordt gebruikt.")}`
      : t("Er zit geen bijgeladen stroom meer in de accu.");
    const today = result.geladen_kwh > 0.005
      ? t("Vandaag bijgeladen: {kwh} kWh voor € {cost}, waarvan {used} kWh gebruikt. ", {
          kwh: number(result.geladen_kwh, 1), cost: number(result.laadkosten, 2), used: number(result.gebruikt_kwh, 1),
        })
      : "";
    const wear = result.afschrijving > 0.005
      ? t("Afschrijving van de accu is meegerekend: € {wear}. ", { wear: number(result.afschrijving, 2) })
      : "";
    const details = cfg.expected_details === false ? "" : `
      <div class="head"><ha-icon icon="mdi:cash-multiple"></ha-icon><span>${t("Verwachte opbrengst van dit plan (schatting)")}</span></div>
      <div class="rows">${renderExpectedRows(result)}</div>`;
    const note = cfg.notes === false ? "" : `<div class="note">${escapeHtml(today + wear + stock)}</div>`;
    return `${tiles ? `<div class="tiles">${tiles}</div>` : ""}${details}${note}`;
  }

  static getConfigForm() {
    return configForm([
      FIELD.entity, FIELD.title, FIELD.tiles(TILE_KEYS, TILE_LABELS),
      FIELD.bool("expected_details"), FIELD.bool("notes"),
    ]);
  }
}

class MarstekGoedkoopLadenSchakelaarsCard extends MarstekBaseCard {
  static getConfigForm() {
    return configForm([FIELD.entity, FIELD.title, FIELD.lanes]);
  }

  getCardSize() {
    return 1;
  }

  _cardClass() {
    return "compact";
  }

  _body(flow) {
    const chips = pickLanes(flow, this._config).map((lane) => `
      <button class="chip ${lane.aan ? "on" : ""}" data-id="${escapeHtml(lane.id)}" ${lane.schakelaar ? "" : "disabled"}
              aria-pressed="${lane.aan ? "true" : "false"}"
              aria-label="${escapeHtml(lane.titel)}: ${lane.aan ? t("aan") : t("uit")}">
        <ha-icon icon="${escapeHtml(lane.icoon || "mdi:toggle-switch-outline")}"></ha-icon>
        <span class="label"><b>${escapeHtml(lane.titel)}</b><small>${lane.aan ? t("Aan") : t("Uit")}</small></span>
      </button>`).join("");
    return `<div class="chips">${chips}</div>`;
  }

  _render() {
    const before = this._signature;
    super._render();
    if (this._signature === before) return;
    const state = this._hass && this._hass.states[this._entityId];
    const lanes = (state && state.attributes.stroomschema && state.attributes.stroomschema.banen) || [];
    this.shadowRoot.querySelectorAll(".chip").forEach((chip) => {
      chip.addEventListener("click", () => {
        const lane = lanes.find((item) => item.id === chip.dataset.id);
        if (!lane || !lane.schakelaar || !this._hass) return;
        this._hass.callService("switch", lane.aan ? "turn_off" : "turn_on", { entity_id: lane.schakelaar });
      });
    });
  }
}

const STATUS = {
  laden: { icon: "mdi:battery-charging", label: "Laden", tone: "actie" },
  gepland: { icon: "mdi:battery-clock-outline", label: "Gepland", tone: "ok" },
  klaar: { icon: "mdi:battery-check-outline", label: "Klaar", tone: "ok" },
  vol: { icon: "mdi:battery", label: "Vol", tone: "ok" },
  geen: { icon: "mdi:battery-outline", label: "Geen plan", tone: "eind" },
  onbekend: { icon: "mdi:battery-unknown", label: "Onbekend", tone: "eind" },
};

class MarstekGoedkoopLadenStatusCard extends MarstekBaseCard {
  static getConfigForm() {
    return configForm([
      FIELD.entity, FIELD.title, FIELD.bool("show_soc"), FIELD.bool("show_price"), FIELD.bool("show_next"),
    ]);
  }

  getCardSize() {
    return 3;
  }

  _cardClass() {
    return "compact";
  }

  _body(flow, clock, state) {
    const o = flow.overzicht;
    if (!o) return `<div class="empty">${t("Nog geen gegevens beschikbaar.")}</div>`;
    const cfg = this._config;
    const info = STATUS[o.status] || STATUS.onbekend;
    let html = `
      <div class="status ${info.tone}">
        <div class="badge"><ha-icon icon="${info.icon}"></ha-icon></div>
        <div><b>${escapeHtml(o.bezig)}</b><span>${escapeHtml(t(info.label))}${o.laadvermogen_w && o.status === "laden" ? ` · ${o.laadvermogen_w} W` : ""}</span></div>
      </div>`;
    if (cfg.show_soc !== false && o.soc != null) {
      const stored = o.capaciteit_kwh ? ` · ${number(o.capaciteit_kwh * o.soc / 100, 1)} kWh` : "";
      html += `
        <div class="meter">
          <div class="top"><span>${t("Laadtoestand")}</span><b>${number(o.soc, 0)} %${stored}</b></div>
          <div class="bar"><i style="width:${Math.max(0, Math.min(100, o.soc))}%"></i></div>
        </div>`;
    }
    const facts = [];
    if (cfg.show_price !== false && o.prijs_nu != null) {
      facts.push(`<div class="fact">${t("Prijs nu")}<b class="${o.prijs_nu < 0 ? "plus" : ""}">€ ${number(o.prijs_nu, 3)}/kWh</b></div>`);
    }
    const next = (flow.tijdlijn || []).find((item) => item.soort !== "nu");
    if (cfg.show_next !== false && next) {
      facts.push(`<div class="fact">${t("Volgende stap")}<b>${escapeHtml(next.titel)}</b>${escapeHtml(next.detail)}</div>`);
    }
    if (facts.length) html += `<div class="facts">${facts.join("")}</div>`;
    return html;
  }
}

function hourLabel(date) {
  return `${String(date.getHours()).padStart(2, "0")}`;
}

class MarstekGoedkoopLadenPrijzenCard extends MarstekBaseCard {
  static getConfigForm() {
    return configForm([
      FIELD.entity, FIELD.title, FIELD.number("hours_back", 0, 12), FIELD.number("hours_ahead", 0, 72),
      FIELD.bool("show_values"), FIELD.number("height", 80, 400),
    ]);
  }

  constructor() {
    super();
    this._selected = null; // begin van het aangeraakte uur (ms); null = het huidige uur
    this._width = 0;
  }

  connectedCallback() {
    if (typeof ResizeObserver === "undefined") return;
    this._observer = new ResizeObserver(() => {
      const width = Math.round(this.clientWidth);
      if (width && Math.abs(width - this._width) >= 8) {
        this._width = width;
        this._signature = null;
        if (this._hass) this._render();
      }
    });
    this._observer.observe(this);
  }

  disconnectedCallback() {
    if (this._observer) this._observer.disconnect();
  }

  getCardSize() {
    return 3;
  }

  _rows(flow) {
    const cfg = this._config;
    const HOUR = 3600e3;
    const back = cfg.hours_back === "" || cfg.hours_back == null || !Number.isFinite(Number(cfg.hours_back))
      ? 2 : Number(cfg.hours_back);
    const ahead = Number(cfg.hours_ahead) > 0 ? Number(cfg.hours_ahead) : Infinity;
    const now = Date.now();
    return (flow.prijzen || [])
      .map((row) => ({ ...row, time: new Date(row.start) }))
      .filter((row) => row.time.getTime() + HOUR > now - back * HOUR && row.time.getTime() <= now + ahead * HOUR);
  }

  _body(flow) {
    const cfg = this._config;
    const HOUR = 3600e3;
    const now = Date.now();
    const rows = this._rows(flow);
    if (!rows.length) return `<div class="empty">${t("Geen prijzen beschikbaar.")}</div>`;

    // Teken op de echte breedte van de kaart, zodat tekst leesbaar blijft op een telefoon.
    const W = Math.max(260, (this._width || this.clientWidth || 560) - 32);
    const left = 34, top = 16;
    const H = Math.max(80, Number(cfg.height) || 150);
    const values = rows.map((row) => row.prijs);
    const high = Math.max(0, ...values), low = Math.min(0, ...values);
    const span = (high - low) || 1;
    const bw = (W - left) / rows.length;
    const gap = Math.min(3, bw * 0.15);
    const every = Math.max(1, Math.ceil(26 / bw));
    const showValues = cfg.show_values === true && bw >= 30;
    const bottom = showValues && low < 0 ? 30 : 20;
    const y = (value) => top + ((high - value) / span) * (H - top - bottom);
    const labels = {
      laden: t("Bijladen"), verkoop: t("Verkoop"), negatief: t("Negatieve prijs"), negatief_venster: t("Negatieve prijs"),
    };

    const current = rows.findIndex((row) => row.time.getTime() <= now && now < row.time.getTime() + HOUR);
    let chosen = rows.findIndex((row) => row.time.getTime() === this._selected);
    if (chosen < 0) chosen = current >= 0 ? current : 0;

    let bars = "", axis = "", marks = "", hits = "";
    rows.forEach((row, i) => {
      const x = left + i * bw;
      const y0 = y(0), y1 = y(row.prijs);
      const barTop = Math.min(y0, y1), barHeight = Math.max(2, Math.abs(y0 - y1));
      bars += `<rect class="b ${row.soort || ""}" x="${(x + gap / 2).toFixed(1)}" y="${barTop.toFixed(1)}" width="${Math.max(1, bw - gap).toFixed(1)}" height="${barHeight.toFixed(1)}" rx="2"/>`;
      // De hele kolom is aan te raken, ook als de staaf zelf laag is.
      hits += `<rect class="hit" data-i="${i}" x="${x.toFixed(1)}" y="0" width="${bw.toFixed(1)}" height="${H}"/>`;
      if (i % every === 0) axis += `<text x="${(x + bw / 2).toFixed(1)}" y="${H - 4}" text-anchor="middle">${hourLabel(row.time)}</text>`;
      if (showValues) {
        const labelY = row.prijs >= 0 ? barTop - 3 : barTop + barHeight + 11;
        marks += `<text x="${(x + bw / 2).toFixed(1)}" y="${labelY.toFixed(1)}" text-anchor="middle">${number(row.prijs, 2)}</text>`;
      }
    });
    const nowLine = current < 0 ? "" : (() => {
      const x = left + (current + (now - rows[current].time.getTime()) / HOUR) * bw;
      return `<line class="now" x1="${x.toFixed(1)}" y1="${top - 6}" x2="${x.toFixed(1)}" y2="${H - bottom}"/>`;
    })();
    const selX = left + chosen * bw;
    const selected = `<rect class="sel" x="${(selX + 0.5).toFixed(1)}" y="${top - 6}" width="${(bw - 1).toFixed(1)}" height="${(H - bottom - top + 6).toFixed(1)}"/>`;
    const scale = `
      <text x="${left - 5}" y="${(y(high) + 4).toFixed(1)}" text-anchor="end">${number(high, 2)}</text>
      ${low < 0 ? `<text x="${left - 5}" y="${(H - bottom).toFixed(1)}" text-anchor="end">${number(low, 2)}</text>` : ""}
      <text x="${left - 5}" y="${(y(0) + 4).toFixed(1)}" text-anchor="end">0</text>`;
    const kinds = ["laden", "verkoop", "negatief"].filter((kind) => rows.some((row) => row.soort === kind || (kind === "negatief" && row.soort === "negatief_venster")));
    const swatch = { laden: "var(--success-color, #43a047)", verkoop: "var(--warning-color, #ffa600)", negatief: "var(--info-color, #039be5)" };
    const legend = kinds.map((kind) => `<span><i style="background:${swatch[kind]}"></i>${labels[kind]}</span>`).join("")
      + (current >= 0 ? `<span><i style="background:var(--primary-color)"></i>${t("Nu")}</span>` : "");

    // Wat je aanraakt (of het huidige uur) staat in tekst boven de grafiek.
    const pick = rows[chosen];
    const isNow = chosen === current;
    const what = labels[pick.soort] ? `<span>${labels[pick.soort]}</span>` : "";
    const detail = `
      <div class="detail" aria-live="polite">
        <b>€ ${number(pick.prijs, 3)}/kWh</b>
        <span>${hourLabel(pick.time)}:00 – ${hourLabel(new Date(pick.time.getTime() + HOUR))}:00${isNow ? ` · ${t("Nu")}` : ""}</span>
        ${what}
      </div>`;
    return `
      <div class="chart">
        ${detail}
        <svg viewBox="0 0 ${W.toFixed(0)} ${H}" role="img" aria-label="${t("Prijzen per uur in € per kWh")}">
          <line class="zero" x1="${left}" y1="${y(0).toFixed(1)}" x2="${W}" y2="${y(0).toFixed(1)}"/>
          ${scale}${bars}${marks}${nowLine}${selected}${axis}${hits}
        </svg>
        ${legend ? `<div class="legend">${legend}</div>` : ""}
      </div>`;
  }

  _render() {
    const before = this._signature;
    super._render();
    if (this._signature === before) return;
    const svg = this.shadowRoot.querySelector(".chart svg");
    const state = this._hass && this._hass.states[this._entityId];
    const flow = state && state.attributes.stroomschema;
    if (!svg || !flow) return;
    const rows = this._rows(flow);
    const pick = (event) => {
      const rect = svg.getBoundingClientRect();
      const left = 34 * (rect.width / svg.viewBox.baseVal.width);
      const fraction = (event.clientX - rect.left - left) / (rect.width - left);
      const index = Math.min(rows.length - 1, Math.max(0, Math.floor(fraction * rows.length)));
      const start = rows[index] && rows[index].time.getTime();
      if (start && start !== this._selected) {
        this._selected = start;
        this._signature = null;
        this._render();
      }
    };
    // Aanraken of slepen kiest een uur; vertikaal scrollen blijft werken (touch-action: pan-y).
    svg.addEventListener("pointerdown", pick);
    svg.addEventListener("pointermove", (event) => {
      if (event.pointerType !== "mouse" || event.buttons) pick(event);
    });
  }
}

const STOCK_KEYS = ["voorraad", "kostprijs", "rendement", "afschrijving", "capaciteit"];
const STOCK_LABELS = {
  voorraad: "Voorraad", kostprijs: "Kostprijs", rendement: "Rendement",
  afschrijving: "Afschrijving per kWh", capaciteit: "Capaciteit",
};

class MarstekGoedkoopLadenVoorraadCard extends MarstekBaseCard {
  static getConfigForm() {
    return configForm([FIELD.entity, FIELD.title, FIELD.tiles(STOCK_KEYS, STOCK_LABELS), FIELD.bool("notes")]);
  }

  getCardSize() {
    return 3;
  }

  _body(flow) {
    const o = flow.overzicht, r = flow.resultaat;
    if (!o || !r) return `<div class="empty">${t("Nog geen gegevens beschikbaar.")}</div>`;
    const values = {
      voorraad: `${number(r.voorraad_kwh || 0, 1)} kWh`,
      kostprijs: o.kostprijs != null ? `€ ${number(o.kostprijs, 3)}` : "–",
      rendement: `${number((o.rendement || 0) * 100, 0)} %`,
      afschrijving: `€ ${number(o.afschrijving_per_kwh || 0, 3)}`,
      capaciteit: `${number(o.capaciteit_kwh || 0, 2)} kWh`,
    };
    const wanted = Array.isArray(this._config.tiles) ? this._config.tiles : STOCK_KEYS;
    const tiles = wanted.filter((key) => STOCK_LABELS[key])
      .map((key) => `<div class="tile"><small>${t(STOCK_LABELS[key])}</small><b>${values[key]}</b></div>`).join("");
    const note = this._config.notes === false ? "" : `<div class="note">${escapeHtml(t("Boven de kostprijs levert gebruiken of verkopen winst op, eronder verlies."))}</div>`;
    return `<div class="tiles">${tiles}</div>${note}`;
  }
}

const CARDS = [
  ["marstek-goedkoop-laden-card", MarstekGoedkoopLadenCard, t("Marstek Goedkoop Laden"),
    t("Tijdlijn en controles van het laadplan als stroomschema.")],
  ["marstek-goedkoop-laden-compact-card", MarstekGoedkoopLadenCompactCard, t("Marstek Goedkoop Laden (compact)"),
    t("Het stroomschema in een paar regels.")],
  ["marstek-goedkoop-laden-opbrengst-card", MarstekGoedkoopLadenOpbrengstCard, t("Marstek Goedkoop Laden (opbrengst)"),
    t("Opbrengst van vandaag, deze week en het huidige plan.")],
  ["marstek-goedkoop-laden-schakelaars-card", MarstekGoedkoopLadenSchakelaarsCard, t("Marstek Goedkoop Laden (schakelaars)"),
    t("De schakelaars voor bijladen, verkoop en negatieve prijs.")],
  ["marstek-goedkoop-laden-status-card", MarstekGoedkoopLadenStatusCard, t("Marstek Goedkoop Laden (status)"),
    t("Wat er nu gebeurt, de laadtoestand, de prijs en de volgende stap.")],
  ["marstek-goedkoop-laden-prijzen-card", MarstekGoedkoopLadenPrijzenCard, t("Marstek Goedkoop Laden (prijzen)"),
    t("Prijsgrafiek met de uren waarin wordt bijgeladen of verkocht.")],
  ["marstek-goedkoop-laden-voorraad-card", MarstekGoedkoopLadenVoorraadCard, t("Marstek Goedkoop Laden (voorraad)"),
    t("Bijgeladen voorraad, kostprijs, rendement en afschrijving.")],
];

window.customCards = window.customCards || [];
for (const [type, cls, name, description] of CARDS) {
  if (!customElements.get(type)) customElements.define(type, cls);
  if (!window.customCards.some((card) => card.type === type)) {
    window.customCards.push({ type, name, description, preview: true });
  }
}
