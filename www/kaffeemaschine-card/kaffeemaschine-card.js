/**
 * kaffeemaschine-card.js
 * Lovelace Custom Card for Kaffeemaschine MQTT Statistics
 *
 * Usage:
 *   type: custom:kaffeemaschine-card
 *   entity: sensor.kaffeemaschine_timeline
 *   title: "☕ Meine Kaffeemaschine"
 */

const DRINK_ICONS = {
  Espresso: "☕",
  Kaffee: "☕",
  Cappuccino: "🍵",
  "Latte Macchiato": "🥛",
  Americano: "☕",
  Heißwasser: "💧",
  Dampf: "💨",
};

function getDrinkIcon(name) {
  return DRINK_ICONS[name] || "☕";
}

function formatDateTime(isoString) {
  if (!isoString) return "";
  try {
    const d = new Date(isoString);
    const date = d.toLocaleDateString("de-DE", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
    });
    const time = d.toLocaleTimeString("de-DE", {
      hour: "2-digit",
      minute: "2-digit",
    });
    return `${date} ${time}`;
  } catch {
    return isoString;
  }
}

class KaffeeMaschineCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
  }

  setConfig(config) {
    if (!config.entity) {
      throw new Error("Bitte 'entity' in der Kartenkonfiguration angeben.");
    }
    this._config = config;
    this.render();
  }

  set hass(hass) {
    this._hass = hass;
    this.render();
  }

  render() {
    if (!this._config || !this._hass) return;

    const entityId = this._config.entity;
    const title = this._config.title || "☕ Kaffeemaschine";
    const stateObj = this._hass.states[entityId];

    // Resolve sibling sensor entity IDs by replacing the trailing segment
    const baseId = entityId.replace(/_timeline$/, "");
    const heuteId = baseId + "_bezuege_heute";
    const gesamtId = baseId + "_bezuege_gesamt";
    const lieblingId = baseId + "_lieblingsgetraenk";

    const heuteState = this._hass.states[heuteId];
    const gesamtState = this._hass.states[gesamtId];
    const lieblingState = this._hass.states[lieblingId];

    const bezuegeHeute = heuteState ? heuteState.state : "–";
    const bezuegeGesamt = gesamtState ? gesamtState.state : "–";
    const liebling = lieblingState ? lieblingState.state : "–";

    const entries =
      stateObj && stateObj.attributes && stateObj.attributes.entries
        ? stateObj.attributes.entries
        : [];

    const last10 = [...entries].reverse().slice(0, 10);

    const timelineRows = last10
      .map(
        (e) => `
      <div class="timeline-entry">
        <span class="drink-icon">${getDrinkIcon(e.getraenk)}</span>
        <div class="drink-info">
          <span class="drink-name">${e.getraenk || "Unbekannt"}</span>
          <span class="drink-time">${formatDateTime(e.zeitstempel)}</span>
        </div>
        <div class="drink-meta">
          ${e.menge_ml != null ? `<span class="badge">${e.menge_ml} ml</span>` : ""}
          ${e.staerke ? `<span class="badge">${e.staerke}</span>` : ""}
        </div>
      </div>
    `
      )
      .join("");

    const noEntries =
      last10.length === 0
        ? `<div class="no-entries">Noch keine Getränke aufgezeichnet.</div>`
        : "";

    this.shadowRoot.innerHTML = `
      <style>
        :host {
          display: block;
          font-family: var(--paper-font-body1_-_font-family, sans-serif);
        }
        ha-card {
          padding: 16px;
          background: var(--card-background-color, #fff);
          border-radius: var(--ha-card-border-radius, 12px);
          box-shadow: var(--ha-card-box-shadow, 0 2px 8px rgba(0,0,0,0.1));
        }
        .card-title {
          font-size: 1.2rem;
          font-weight: bold;
          margin-bottom: 12px;
          color: var(--primary-text-color, #212121);
        }
        .stats-row {
          display: flex;
          gap: 12px;
          margin-bottom: 16px;
          flex-wrap: wrap;
        }
        .stat-box {
          flex: 1;
          min-width: 80px;
          background: var(--secondary-background-color, #f5f5f5);
          border-radius: 8px;
          padding: 10px 8px;
          text-align: center;
        }
        .stat-value {
          font-size: 1.5rem;
          font-weight: bold;
          color: var(--primary-color, #03a9f4);
        }
        .stat-label {
          font-size: 0.75rem;
          color: var(--secondary-text-color, #757575);
          margin-top: 2px;
        }
        .section-label {
          font-size: 0.85rem;
          font-weight: 600;
          color: var(--secondary-text-color, #757575);
          text-transform: uppercase;
          letter-spacing: 0.05em;
          margin-bottom: 8px;
        }
        .timeline-entry {
          display: flex;
          align-items: center;
          gap: 10px;
          padding: 8px 4px;
          border-bottom: 1px solid var(--divider-color, #e0e0e0);
        }
        .timeline-entry:last-child {
          border-bottom: none;
        }
        .drink-icon {
          font-size: 1.6rem;
          width: 32px;
          text-align: center;
        }
        .drink-info {
          flex: 1;
          display: flex;
          flex-direction: column;
        }
        .drink-name {
          font-weight: 600;
          color: var(--primary-text-color, #212121);
        }
        .drink-time {
          font-size: 0.78rem;
          color: var(--secondary-text-color, #757575);
        }
        .drink-meta {
          display: flex;
          flex-direction: column;
          align-items: flex-end;
          gap: 3px;
        }
        .badge {
          background: var(--primary-color, #03a9f4);
          color: #fff;
          border-radius: 10px;
          padding: 2px 7px;
          font-size: 0.72rem;
          white-space: nowrap;
        }
        .no-entries {
          text-align: center;
          color: var(--secondary-text-color, #757575);
          padding: 16px;
        }
      </style>
      <ha-card>
        <div class="card-title">${title}</div>
        <div class="stats-row">
          <div class="stat-box">
            <div class="stat-value">${bezuegeHeute}</div>
            <div class="stat-label">Heute</div>
          </div>
          <div class="stat-box">
            <div class="stat-value">${bezuegeGesamt}</div>
            <div class="stat-label">Gesamt</div>
          </div>
          <div class="stat-box">
            <div class="stat-value">${getDrinkIcon(liebling)}</div>
            <div class="stat-label">${liebling}</div>
          </div>
        </div>
        <div class="section-label">Letzte Bezüge</div>
        ${timelineRows}
        ${noEntries}
      </ha-card>
    `;
  }

  getCardSize() {
    return 4;
  }

  static getConfigElement() {
    return document.createElement("kaffeemaschine-card-editor");
  }

  static getStubConfig() {
    return {
      entity: "sensor.kaffeemaschine_timeline",
      title: "☕ Meine Kaffeemaschine",
    };
  }
}

customElements.define("kaffeemaschine-card", KaffeeMaschineCard);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "kaffeemaschine-card",
  name: "Kaffeemaschine Card",
  description: "Zeigt Kaffeemaschinen-Statistiken und die Getränke-Timeline an.",
});
