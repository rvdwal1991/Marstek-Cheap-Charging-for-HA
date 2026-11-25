/*
 * Marstek Goedkoop Laden - dashboardkaarten
 *
 * Alle kaarten lezen het attribuut `stroomschema` van de laadplan-sensor.
 *
 *   type: custom:marstek-goedkoop-laden-card            stroomschema (tijdlijn + controles)
 *   type: custom:marstek-goedkoop-laden-compact-card    hetzelfde, compact
 *   type: custom:marstek-goedkoop-laden-opbrengst-card  alleen de opbrengsten
 *   type: custom:marstek-goedkoop-laden-schakelaars-card  de schakelaars van de modi
 *
 * Opties voor alle kaarten:
 *   entity: sensor.marstek_goedkoop_laden_laadplan   (optioneel)
 *   title: Prijssturing                              (optioneel)
 * Extra voor de eerste twee:
 *   opbrengst: true | false   toon ook de opbrengst (standaard: uit bij de
 *                             gewone kaart, één regel bij de compacte kaart)
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
`;

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (c) => (
    { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]
  ));
}

// Taal van Home Assistant: Nederlands blijft Nederlands, al het andere wordt Engels.
let LANG = (typeof navigator !== "undefined" && navigator.language) || "nl";
const EN = {
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
};
function t(nl) {
  return LANG.toLowerCase().startsWith("nl") ? nl : (EN[nl] ?? nl);
}

function number(value, digits) {
  const text = Number(value || 0).toFixed(digits);
  return LANG.toLowerCase().startsWith("nl") ? text.replace(".", ",") : text;
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

class MarstekBaseCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._config = {};
    this._signature = null;
  }

  static getStubConfig() {
    return { entity: DEFAULT_ENTITY };
  }

  setConfig(config) {
    this._config = { entity: DEFAULT_ENTITY, ...(config || {}) };
    this._signature = null;
    if (this._hass) this._render();
  }

  set hass(hass) {
    this._hass = hass;
    LANG = (hass && (hass.language || (hass.locale && hass.locale.language))) || "nl";
    const shown = hass && hass.states && this._config && hass.states[this._config.entity];
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
    const state = this._hass && this._hass.states[this._config.entity];
    const flow = state && state.attributes && state.attributes.stroomschema;
    const clock = this._clock();
    const signature = JSON.stringify([this._config, flow || (state ? "geen" : "weg"), clock, LANG]);
    if (signature === this._signature) return;
    this._signature = signature;

    let body;
    if (!state) {
      body = `<div class="empty">${t("Entiteit")} ${escapeHtml(this._config.entity)} ${t("niet gevonden.")}</div>`;
    } else if (!flow || !Array.isArray(flow.tijdlijn)) {
      body = `<div class="empty">${t("Nog geen gegevens beschikbaar.")}</div>`;
    } else {
      body = this._body(flow, clock);
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
    const lanes = (flow.banen || []).map((lane) => `
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
    return `
      <div class="head"><ha-icon icon="mdi:clock-outline"></ha-icon><span>${t("Vandaag")}</span></div>
      ${renderSteps(this._timeline(flow, clock))}
      ${result}
      <div class="divider"></div>
      <div class="lanes">${lanes}</div>`;
  }

  _compact(flow, clock) {
    const timeline = this._timeline(flow, clock).map((item) => {
      const kind = ICONS[item.soort] ? item.soort : "eind";
      return `
        <div class="crow ${kind}">
          <div class="pip"></div>
          <div class="main"><b>${escapeHtml(item.titel)}</b> · ${escapeHtml(item.detail)}</div>
          <div></div>
        </div>`;
    }).join("");
    const lanes = (flow.banen || []).map((lane) => {
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
    return `${timeline}<div class="divider"></div>${lanes}${gain ? `<div class="divider"></div>${gain}` : ""}`;
  }
}

class MarstekGoedkoopLadenCompactCard extends MarstekGoedkoopLadenCard {
  setConfig(config) {
    super.setConfig({ ...(config || {}), compact: true });
  }
}

class MarstekGoedkoopLadenOpbrengstCard extends MarstekBaseCard {
  getCardSize() {
    return 4;
  }

  _body(flow) {
    const result = flow.resultaat;
    if (!result) return `<div class="empty">${t("Nog geen opbrengst beschikbaar.")}</div>`;
    const tile = (label, value) => `
      <div class="tile"><small>${label}</small><b class="${tone(value)}">${formatEuro(value || 0)}</b></div>`;
    const stock = result.voorraad_kwh > 0.005
      ? (LANG.toLowerCase().startsWith("nl")
          ? `Nog in de accu: ${number(result.voorraad_kwh, 1)} kWh bijgeladen stroom`
            + (result.voorraad_prijs != null ? ` (kostprijs € ${number(result.voorraad_prijs, 2)} per kWh)` : "")
          : `Still in the battery: ${number(result.voorraad_kwh, 1)} kWh of charged energy`
            + (result.voorraad_prijs != null ? ` (cost price € ${number(result.voorraad_prijs, 2)} per kWh)` : ""))
        + `. ${t("Dat telt pas mee als het wordt gebruikt.")}`
      : t("Er zit geen bijgeladen stroom meer in de accu.");
    const today = result.geladen_kwh > 0.005
      ? (LANG.toLowerCase().startsWith("nl")
          ? `Vandaag bijgeladen: ${number(result.geladen_kwh, 1)} kWh voor € ${number(result.laadkosten, 2)}`
            + `, waarvan ${number(result.gebruikt_kwh, 1)} kWh gebruikt. `
          : `Charged today: ${number(result.geladen_kwh, 1)} kWh for € ${number(result.laadkosten, 2)}`
            + `, of which ${number(result.gebruikt_kwh, 1)} kWh used. `)
      : "";
    const wear = result.afschrijving > 0.005
      ? (LANG.toLowerCase().startsWith("nl")
          ? `Afschrijving van de accu is meegerekend: € ${number(result.afschrijving, 2)}. `
          : `Battery depreciation is included: € ${number(result.afschrijving, 2)}. `)
      : "";
    return `
      <div class="tiles">
        ${tile(t("Vandaag"), result.vandaag)}
        ${tile(t("Deze week"), result.week)}
        ${result.vorige_week == null ? "" : tile(t("Vorige week"), result.vorige_week)}
        ${tile(t("Deze maand"), result.maand)}
        ${tile(t("Verwacht (plan)"), result.totaal)}
      </div>
      <div class="head"><ha-icon icon="mdi:cash-multiple"></ha-icon><span>${t("Verwachte opbrengst van dit plan (schatting)")}</span></div>
      <div class="rows">${renderExpectedRows(result)}</div>
      <div class="note">${escapeHtml(today + wear + stock)}</div>`;
  }
}

class MarstekGoedkoopLadenSchakelaarsCard extends MarstekBaseCard {
  getCardSize() {
    return 1;
  }

  _cardClass() {
    return "compact";
  }

  _body(flow) {
    const chips = (flow.banen || []).map((lane, index) => `
      <button class="chip ${lane.aan ? "on" : ""}" data-index="${index}" ${lane.schakelaar ? "" : "disabled"}
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
    const state = this._hass && this._hass.states[this._config.entity];
    const lanes = (state && state.attributes.stroomschema && state.attributes.stroomschema.banen) || [];
    this.shadowRoot.querySelectorAll(".chip").forEach((chip) => {
      chip.addEventListener("click", () => {
        const lane = lanes[Number(chip.dataset.index)];
        if (!lane || !lane.schakelaar || !this._hass) return;
        this._hass.callService("switch", lane.aan ? "turn_off" : "turn_on", { entity_id: lane.schakelaar });
      });
    });
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
];

window.customCards = window.customCards || [];
for (const [type, cls, name, description] of CARDS) {
  if (!customElements.get(type)) customElements.define(type, cls);
  if (!window.customCards.some((card) => card.type === type)) {
    window.customCards.push({ type, name, description });
  }
}
