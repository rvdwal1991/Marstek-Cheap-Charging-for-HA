/*
 * Marstek Goedkoop Laden - stroomschemakaart
 *
 * Toont de tijdlijn van vandaag en per onderdeel (bijladen, verkoop, negatieve
 * prijs) de controles die tot de uitkomst leiden. Leest alles uit het attribuut
 * `stroomschema` van de laadplan-sensor.
 *
 *   type: custom:marstek-goedkoop-laden-card
 *   entity: sensor.marstek_goedkoop_laden_laadplan   (optioneel)
 *   title: Prijssturing                              (optioneel)
 */
const DEFAULT_ENTITY = "sensor.marstek_goedkoop_laden_laadplan";

const ICONS = {
  nu: "mdi:circle-medium",
  ok: "mdi:check",
  stop: "mdi:close",
  actie: "mdi:flash",
  eind: "mdi:minus",
};

const STYLE = `
  :host { display: block; }
  ha-card { padding: 16px; }
  .title { font-size: 16px; font-weight: 500; margin: 0 0 12px; color: var(--primary-text-color); }
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
  .stop .line, .eind .line { border-left-style: dashed; }
  .eind .dot { border-style: dashed; }
  .eind .text b { color: var(--secondary-text-color); }
  .nu .dot { border: 2px solid var(--primary-color); color: var(--primary-color); }
  .divider { border-top: 1px solid var(--divider-color); margin: 14px 0; }
  .lanes { display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 16px; }
  .lane.uit .step { opacity: 0.55; }
  .empty { font-size: 14px; color: var(--secondary-text-color); }
  .result { display: grid; grid-template-columns: auto minmax(0, 1fr); column-gap: 16px; align-items: center; }
  .total { font-size: 24px; font-weight: 500; line-height: 1.2; white-space: nowrap; color: var(--primary-text-color); }
  .total.plus, .amount.plus { color: var(--success-color, #43a047); }
  .total.min, .amount.min { color: var(--error-color, #db4437); }
  .total small { display: block; font-size: 12px; font-weight: 400; color: var(--secondary-text-color); }
  .rows { display: flex; flex-direction: column; gap: 6px; min-width: 0; }
  .row { display: grid; grid-template-columns: minmax(0, 1fr) auto; column-gap: 8px; font-size: 12px;
         line-height: 16px; color: var(--secondary-text-color); }
  .row b { font-weight: 500; font-size: 13px; color: var(--primary-text-color); }
  .amount { font-size: 13px; font-weight: 500; white-space: nowrap; color: var(--primary-text-color); }
`;

function formatEuro(value) {
  const sign = value > 0.004 ? "+ " : value < -0.004 ? "− " : "";
  return `${sign}€ ${Math.abs(value).toFixed(2).replace(".", ",")}`;
}

function tone(value) {
  return value > 0.004 ? "plus" : value < -0.004 ? "min" : "";
}

function renderResult(result) {
  if (!result || !Array.isArray(result.regels)) return "";
  const rows = result.regels.map((line) => `
    <div class="row">
      <div><b>${escapeHtml(line.titel)}</b><br>${escapeHtml(line.detail)}</div>
      <div class="amount ${line.bedrag == null ? "" : tone(line.bedrag)}">${line.bedrag == null ? "–" : formatEuro(line.bedrag)}</div>
    </div>`).join("");
  return `
    <div class="divider"></div>
    <div class="head"><ha-icon icon="mdi:cash-multiple"></ha-icon><span>Verwachte opbrengst van dit plan (schatting)</span></div>
    <div class="result">
      <div class="total ${tone(result.totaal)}">${formatEuro(result.totaal)}<small>totaal</small></div>
      <div class="rows">${rows}</div>
    </div>`;
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (c) => (
    { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]
  ));
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

class MarstekGoedkoopLadenCard extends HTMLElement {
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
    this._render();
  }

  getCardSize() {
    return 6;
  }

  getGridOptions() {
    return { columns: 12, min_columns: 6 };
  }

  _render() {
    const state = this._hass && this._hass.states[this._config.entity];
    const flow = state && state.attributes && state.attributes.stroomschema;
    const now = new Date();
    const clock = `${String(now.getHours()).padStart(2, "0")}:${String(now.getMinutes()).padStart(2, "0")}`;
    const signature = JSON.stringify([this._config, flow || (state ? "geen" : "weg"), clock]);
    if (signature === this._signature) return;
    this._signature = signature;

    let body;
    if (!state) {
      body = `<div class="empty">Entiteit ${escapeHtml(this._config.entity)} niet gevonden.</div>`;
    } else if (!flow || !Array.isArray(flow.tijdlijn)) {
      body = '<div class="empty">Nog geen stroomschema beschikbaar.</div>';
    } else {
      const timeline = flow.tijdlijn.map((item) => (
        item.soort === "nu" ? { ...item, titel: `Nu · ${clock}` } : item
      ));
      const lanes = (flow.banen || []).map((lane) => {
        const steps = lane.aan
          ? lane.stappen || []
          : [{ titel: "Staat uit", detail: "Zet de schakelaar aan om dit te gebruiken", soort: "eind" }];
        return `
          <div class="lane ${lane.aan ? "aan" : "uit"}">
            <div class="head">
              <ha-icon icon="${escapeHtml(lane.icoon || "mdi:help-circle-outline")}"></ha-icon>
              <span>${escapeHtml(lane.titel)} · ${lane.aan ? "aan" : '<span class="off">uit</span>'}</span>
            </div>
            ${renderSteps(steps)}
          </div>`;
      }).join("");
      body = `
        <div class="head"><ha-icon icon="mdi:clock-outline"></ha-icon><span>Vandaag</span></div>
        ${renderSteps(timeline)}
        ${renderResult(flow.resultaat)}
        <div class="divider"></div>
        <div class="lanes">${lanes}</div>`;
    }

    const title = this._config.title ? `<div class="title">${escapeHtml(this._config.title)}</div>` : "";
    this.shadowRoot.innerHTML = `<style>${STYLE}</style><ha-card>${title}${body}</ha-card>`;
  }
}

if (!customElements.get("marstek-goedkoop-laden-card")) {
  customElements.define("marstek-goedkoop-laden-card", MarstekGoedkoopLadenCard);
}
window.customCards = window.customCards || [];
if (!window.customCards.some((card) => card.type === "marstek-goedkoop-laden-card")) {
  window.customCards.push({
    type: "marstek-goedkoop-laden-card",
    name: "Marstek Goedkoop Laden",
    description: "Tijdlijn en controles van het laadplan als stroomschema.",
  });
}
