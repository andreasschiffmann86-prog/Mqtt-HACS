/**
 * Kaffeemaschine Card – Custom Lovelace Card für Home Assistant
 * Zeigt die Timeline der letzten Getränkebezüge und Statistiken an.
 *
 * Konfiguration:
 *   type: custom:kaffeemaschine-card
 *   entity: sensor.kaffeemaschine_timeline
 *   title: Kaffeemaschine          (optional)
 *   max_entries: 10                (optional, Standard: 10)
 */

const GETRAENK_ICONS = {
  Espresso: "☕",
  Kaffee: "☕",
  Cappuccino: "🍵",
  "Latte Macchiato": "🥛",
  Americano: "☕",
  Heisswasser: "💧",
  Dampf: "♨️",
};

function getraenkIcon(name) {
  return GETRAENK_ICONS[name] || "☕";
}

function formatZeitstempel(iso) {
  if (!iso) return "";
  try {
    const d = new Date(iso);
    return d.toLocaleString("de-DE", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

class KaffeemaschineCard extends HTMLElement {
  set hass(hass) {
    if (!this.config) return;

    const entityId = this.config.entity;
    const stateObj = hass.states[entityId];

    if (!stateObj) {
      this._renderError(`Entity "${entityId}" nicht gefunden.`);
      return;
    }

    const attrs = stateObj.attributes || {};
    const timeline = attrs.timeline || [];
    const title = this.config.title || "Kaffeemaschine";
    const maxEntries = this.config.max_entries || 10;
    const entries = timeline.slice(0, maxEntries);

    // Statistiken berechnen
    const heute = new Date().toISOString().slice(0, 10);
    const bezuegeHeute = timeline.filter(
      (e) => e.zeitstempel && e.zeitstempel.startsWith(heute)
    ).length;
    const bezuegeGesamt = stateObj.state;

    // Lieblingsgetränk ermitteln
    const zaehler = {};
    timeline.forEach((e) => {
      if (e.getraenk) zaehler[e.getraenk] = (zaehler[e.getraenk] || 0) + 1;
    });
    let liebling = null;
    let max = 0;
    Object.entries(zaehler).forEach(([g, n]) => {
      if (n > max) { max = n; liebling = g; }
    });

    this.shadowRoot.innerHTML = `
      <style>
        :host {
          display: block;
          font-family: var(--primary-font-family, Roboto, sans-serif);
        }
        .card {
          background: var(--card-background-color, #fff);
          border-radius: var(--ha-card-border-radius, 12px);
          box-shadow: var(--ha-card-box-shadow, 0 2px 6px rgba(0,0,0,.15));
          overflow: hidden;
        }
        .header {
          background: var(--primary-color, #03a9f4);
          color: #fff;
          padding: 14px 16px 10px;
          font-size: 1.1rem;
          font-weight: 600;
          display: flex;
          align-items: center;
          gap: 8px;
        }
        .header .icon { font-size: 1.4rem; }
        .stats {
          display: flex;
          gap: 0;
          border-bottom: 1px solid var(--divider-color, #e0e0e0);
        }
        .stat {
          flex: 1;
          padding: 10px 8px;
          text-align: center;
          border-right: 1px solid var(--divider-color, #e0e0e0);
        }
        .stat:last-child { border-right: none; }
        .stat-value {
          font-size: 1.3rem;
          font-weight: 700;
          color: var(--primary-color, #03a9f4);
        }
        .stat-label {
          font-size: 0.7rem;
          color: var(--secondary-text-color, #727272);
          margin-top: 2px;
        }
        .timeline {
          padding: 8px 0;
        }
        .entry {
          display: flex;
          align-items: center;
          padding: 8px 16px;
          border-bottom: 1px solid var(--divider-color, #f0f0f0);
          gap: 12px;
        }
        .entry:last-child { border-bottom: none; }
        .entry-icon {
          font-size: 1.6rem;
          width: 36px;
          text-align: center;
          flex-shrink: 0;
        }
        .entry-info { flex: 1; }
        .entry-name {
          font-weight: 600;
          font-size: 0.95rem;
          color: var(--primary-text-color, #212121);
        }
        .entry-meta {
          font-size: 0.75rem;
          color: var(--secondary-text-color, #727272);
          margin-top: 2px;
        }
        .entry-time {
          font-size: 0.75rem;
          color: var(--secondary-text-color, #727272);
          white-space: nowrap;
          flex-shrink: 0;
        }
        .empty {
          padding: 24px;
          text-align: center;
          color: var(--secondary-text-color, #727272);
          font-style: italic;
        }
        .error {
          padding: 16px;
          color: var(--error-color, red);
        }
      </style>
      <div class="card">
        <div class="header">
          <span class="icon">☕</span>
          <span>${title}</span>
        </div>
        <div class="stats">
          <div class="stat">
            <div class="stat-value">${bezuegeHeute}</div>
            <div class="stat-label">Heute</div>
          </div>
          <div class="stat">
            <div class="stat-value">${bezuegeGesamt}</div>
            <div class="stat-label">Gesamt</div>
          </div>
          <div class="stat">
            <div class="stat-value">${liebling ? getraenkIcon(liebling) : "–"}</div>
            <div class="stat-label">${liebling || "Kein Favorit"}</div>
          </div>
        </div>
        <div class="timeline">
          ${
            entries.length === 0
              ? '<div class="empty">Noch keine Bezüge vorhanden.</div>'
              : entries
                  .map(
                    (e) => `
            <div class="entry">
              <div class="entry-icon">${getraenkIcon(e.getraenk)}</div>
              <div class="entry-info">
                <div class="entry-name">${e.getraenk || "Unbekannt"}</div>
                <div class="entry-meta">${
                  [
                    e.menge_ml != null ? `${e.menge_ml} ml` : null,
                    e.temperatur != null ? `${e.temperatur}°C` : null,
                    e.staerke || null,
                  ]
                    .filter(Boolean)
                    .join(" · ")
                }</div>
              </div>
              <div class="entry-time">${formatZeitstempel(e.zeitstempel)}</div>
            </div>`
                  )
                  .join("")
          }
        </div>
      </div>
    `;
  }

  setConfig(config) {
    if (!config.entity) {
      throw new Error(
        'Bitte "entity" in der Konfiguration angeben (z.B. sensor.kaffeemaschine_timeline).'
      );
    }
    this.config = config;
    if (!this.shadowRoot) {
      this.attachShadow({ mode: "open" });
    }
  }

  _renderError(msg) {
    this.shadowRoot.innerHTML = `
      <div class="card">
        <div class="error">⚠️ ${msg}</div>
      </div>`;
  }

  getCardSize() {
    return 4;
  }

  static getConfigElement() {
    // Einfacher Editor kann hier ergänzt werden
    return null;
  }

  static getStubConfig() {
    return {
      entity: "sensor.kaffeemaschine_timeline",
      title: "Kaffeemaschine",
      max_entries: 10,
    };
  }
}

customElements.define("kaffeemaschine-card", KaffeemaschineCard);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "kaffeemaschine-card",
  name: "Kaffeemaschine Card",
  description:
    "Zeigt die Timeline der Kaffeemaschinen-Bezüge und Statistiken an.",
  preview: true,
});
