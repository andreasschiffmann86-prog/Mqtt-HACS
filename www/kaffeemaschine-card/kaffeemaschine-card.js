/**
 * Kaffeemaschine Card – Custom Lovelace Card für Home Assistant
 * Zeigt die Timeline der letzten Getränkebezüge und Statistiken an.
 *
 * Konfiguration:
 *   type: custom:kaffeemaschine-card
 *   entity: sensor.kaffeemaschine_timeline
 *   alert_entity: sensor.kaffeemaschine_alert_timeline
 *   title: Kaffeemaschine          (optional)
 *   max_entries: 10                (optional, Standard: 10)
 */ 

const GETRAENK_ICONS = {
  Espresso: "☕",
  Kaffee: "☕",
  Cappuccino: "🍵",
  "Latte Macchiato": "🥛",
  Americano: "☕",
  Heißwasser: "💧",
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

function calcDuration(isoStart, isoEnd) {
  if (!isoStart || isoStart === "null" || isoStart === "undefined") return "?";
  try {
    // Python speichert 6-stellige Mikrosekunden (z.B. .040000+00:00)
    // JS-Date unterstützt nur 3 Stellen – kürzen auf Millisekunden
    const sanitized = isoStart.replace(/(\.[0-9]{3})[0-9]+/, "$1");
    const start = new Date(sanitized);
    if (isNaN(start.getTime())) return "?";
    const endRaw = isoEnd ? isoEnd.replace(/(\.[0-9]{3})[0-9]+/, "$1") : null;
    const end = endRaw ? new Date(endRaw) : new Date();
    if (isNaN(end.getTime())) return "?";
    const sec = Math.max(0, Math.floor((end - start) / 1000));
    const h = Math.floor(sec / 3600);
    const m = Math.floor((sec % 3600) / 60);
    const s = sec % 60;
    if (h > 0) return `${h}h ${m}m`;
    if (m > 0) return `${m}m ${s}s`;
    return `${s}s`;
  } catch {
    return "?";
  }
}

class KaffeemaschineCard extends HTMLElement {
  constructor() {
    super();
    this._alertTimer = null;
    this._chartPeriod = "today"; // today | week | all
  }

  disconnectedCallback() {
    if (this._alertTimer) {
      clearInterval(this._alertTimer);
      this._alertTimer = null;
    }
  }

  _startAlertTimer() {
    if (this._alertTimer) clearInterval(this._alertTimer);
    this._alertTimer = setInterval(() => {
      const spans = this.shadowRoot
        ? this.shadowRoot.querySelectorAll(".alert-duration[data-raise-time]")
        : [];
      if (spans.length === 0) {
        clearInterval(this._alertTimer);
        this._alertTimer = null;
        return;
      }
      spans.forEach((span) => {
        span.textContent = calcDuration(span.dataset.raiseTime);
      });
    }, 1000);
  }

  set hass(hass) {
    if (!this.config) return;

    // Alert-Only-Modus: eigenständige Alert-Card ohne Getränke-Timeline
    if (this.config.alert_only) {
      this._renderAlertOnly(hass);
      return;
    }

    // Chart-Only-Modus: Balkendarstellung der Getränke
    if (this.config.chart_only) {
      this._renderChartOnly(hass);
      return;
    }

    const entityId = this.config.entity;
    const stateObj = hass.states[entityId];

    // Online-Status ermitteln
    const onlineEntityId = this.config.online_entity;
    const onlineObj = onlineEntityId ? hass.states[onlineEntityId] : null;
    if (onlineEntityId && !onlineObj) {
      console.warn(
        `[kaffeemaschine-card] online_entity "${onlineEntityId}" nicht in hass.states gefunden. Verfügbare binary_sensors:`,
        Object.keys(hass.states).filter(k => k.startsWith("binary_sensor.")).join(", ")
      );
    }
    const isOnline = onlineObj ? (onlineObj.state === "on") : null;

    if (!stateObj) {
      this._renderError(`Entity "${entityId}" nicht gefunden.`);
      return;
    }

    const attrs = stateObj.attributes || {};
    const timeline = attrs.timeline || [];
    const title = this.config.title || "Kaffeemaschine";
    const maxEntries = this.config.max_entries || 10;
    const entries = timeline.slice(0, maxEntries);

    // Timer stoppen (wird nach dem Render neu gestartet)
    if (this._alertTimer) {
      clearInterval(this._alertTimer);
      this._alertTimer = null;
    }

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
        .online-indicator {
          display: inline-flex;
          align-items: center;
          gap: 5px;
          margin-left: auto;
          font-size: 0.75rem;
          font-weight: 400;
          opacity: 0.95;
        }
        .online-dot {
          width: 10px;
          height: 10px;
          border-radius: 50%;
          display: inline-block;
          box-shadow: 0 0 4px rgba(0,0,0,.25);
        }
        .online-dot.on {
          background: #4caf50;
          box-shadow: 0 0 6px #4caf50aa;
        }
        .online-dot.off {
          background: #f44336;
          box-shadow: 0 0 6px #f44336aa;
        }
        .online-dot.unknown {
          background: #9e9e9e;
        }
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
        .entry-details {
          font-size: 0.7rem;
          color: var(--secondary-text-color, #999);
          margin-top: 1px;
        }
        .entry-status {
          display: inline-block;
          font-size: 0.65rem;
          font-weight: 600;
          padding: 1px 6px;
          border-radius: 8px;
          margin-left: 4px;
        }
        .status-ok {
          background: #e8f5e9;
          color: #2e7d32;
        }
        .status-canceled {
          background: #fbe9e7;
          color: #c62828;
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
        /* Alert-Styles */
        .alerts-section {
          border-top: 2px solid var(--divider-color, #e0e0e0);
        }
        .alerts-header {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 8px 16px 4px;
          font-size: 0.8rem;
          font-weight: 700;
          text-transform: uppercase;
          letter-spacing: 0.05em;
          color: var(--secondary-text-color, #727272);
        }
        .alert-open {
          display: flex;
          align-items: flex-start;
          gap: 12px;
          padding: 10px 16px;
          border-bottom: 1px solid var(--divider-color, #f0f0f0);
          background: #fff3e0;
          animation: alertPulse 2s ease-in-out infinite;
        }
        @keyframes alertPulse {
          0%, 100% { background: #fff3e0; }
          50% { background: #ffe0b2; }
        }
        .alert-closed {
          display: flex;
          align-items: flex-start;
          gap: 12px;
          padding: 8px 16px;
          border-bottom: 1px solid var(--divider-color, #f0f0f0);
          opacity: 0.65;
        }
        .alert-icon {
          font-size: 1.4rem;
          flex-shrink: 0;
          margin-top: 1px;
        }
        .alert-info { flex: 1; }
        .alert-title-open {
          font-weight: 700;
          font-size: 0.9rem;
          color: #e65100;
        }
        .alert-title-closed {
          font-weight: 600;
          font-size: 0.85rem;
          color: var(--primary-text-color, #212121);
          text-decoration: line-through;
        }
        .alert-meta {
          font-size: 0.72rem;
          color: var(--secondary-text-color, #727272);
          margin-top: 2px;
        }
        .alert-since {
          display: inline-block;
          background: #ff5722;
          color: #fff;
          font-size: 0.7rem;
          font-weight: 700;
          padding: 2px 8px;
          border-radius: 10px;
          white-space: nowrap;
          margin-top: 4px;
        }
        .alert-duration-label {
          font-size: 0.7rem;
          color: var(--secondary-text-color, #9e9e9e);
          font-style: italic;
          margin-top: 3px;
        }
        .no-alerts {
          padding: 10px 16px;
          font-size: 0.8rem;
          color: #4caf50;
          display: flex;
          align-items: center;
          gap: 6px;
        }
      </style>
      <div class="card">
        <div class="header">
          <span class="icon">☕</span>
          <span>${title}</span>
          ${isOnline !== null ? `
            <span class="online-indicator">
              <span class="online-dot ${isOnline ? 'on' : 'off'}"></span>
              ${isOnline ? 'Online' : 'Offline'}
            </span>
          ` : ''}
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
                    (e) => {
                      const meta = [
                        e.menge_ml != null ? `${e.menge_ml} ml` : null,
                        e.temperatur != null ? `${e.temperatur}°C` : null,
                        e.staerke || null,
                      ].filter(Boolean).join(" · ");

                      const details = [
                        e.cup_size != null ? `Größe ${e.cup_size}` : null,
                        e.is_double === true ? "Doppelt" : null,
                        e.strokes != null ? `${e.strokes}x Brühung` : null,
                        e.cycle_time != null ? `${(e.cycle_time / 1000).toFixed(0)}s Zyklus` : null,
                        e.extraction_time != null && e.extraction_time > 0 ? `${(e.extraction_time / 1000).toFixed(0)}s Extraktion` : null,
                      ].filter(Boolean).join(" · ");

                      const statusClass = e.canceled === true ? "status-canceled" : e.canceled === false ? "status-ok" : "";
                      const statusText = e.canceled === true ? "Abgebrochen" : e.canceled === false ? "✓" : "";
                      const statusHtml = statusText ? `<span class="entry-status ${statusClass}">${statusText}</span>` : "";

                      return `
            <div class="entry">
              <div class="entry-icon">${getraenkIcon(e.getraenk)}</div>
              <div class="entry-info">
                <div class="entry-name">${e.getraenk || "Unbekannt"}${statusHtml}</div>
                ${meta ? `<div class="entry-meta">${meta}</div>` : ""}
                ${details ? `<div class="entry-details">${details}</div>` : ""}
              </div>
              <div class="entry-time">${formatZeitstempel(e.zeitstempel)}</div>
            </div>`;
                    }
                  )
                  .join("")
          }
        </div>
      </div>
    `;
  }

  _renderChartOnly(hass) {
    const entityId = this.config.entity;
    if (!entityId) {
      this._renderError('Bitte "entity" in der Konfiguration angeben.');
      return;
    }
    const stateObj = hass.states[entityId];
    if (!stateObj) {
      this._renderError(`Entity "${entityId}" nicht gefunden.`);
      return;
    }
    const timeline = stateObj.attributes.timeline || [];
    const title = this.config.title || "📊 Getränke";
    const period = this._chartPeriod || "today";

    const now = new Date();
    const heute = now.toISOString().slice(0, 10);
    // Montag dieser Woche (ISO)
    const wochenstart = new Date(now);
    wochenstart.setDate(now.getDate() - ((now.getDay() + 6) % 7));
    wochenstart.setHours(0, 0, 0, 0);

    const FARBEN = {
      "Espresso":        "#6d4c41",
      "Kaffee":          "#8d6e63",
      "Cappuccino":      "#a1887f",
      "Latte Macchiato": "#d4a77a",
      "Americano":       "#4e342e",
      "Heißwasser":      "#0288d1",
      "Dampf":           "#78909c",
    };
    const farbe = name => FARBEN[name] || "#03a9f4";

    // Einträge für gewählte Periode filtern
    const filtered = timeline.filter(e => {
      if (!e.getraenk || !e.zeitstempel) return false;
      if (period === "today") return e.zeitstempel.startsWith(heute);
      if (period === "week")  return new Date(e.zeitstempel) >= wochenstart;
      return true; // all
    });

    // Zählen
    const zaehler = {};
    filtered.forEach(e => {
      zaehler[e.getraenk] = (zaehler[e.getraenk] || 0) + 1;
    });
    const drinks = Object.keys(zaehler).sort((a, b) => zaehler[b] - zaehler[a]);
    const maxVal = Math.max(1, ...drinks.map(d => zaehler[d]));

    // Perioden-Label
    const periodLabels = { today: "Heute", week: "Diese Woche", all: "Gesamt" };
    const total = drinks.reduce((s, d) => s + zaehler[d], 0);

    this.shadowRoot.innerHTML = `
      <style>
        :host { display: block; font-family: var(--primary-font-family, Roboto, sans-serif); }
        .card {
          background: var(--card-background-color, #fff);
          border-radius: var(--ha-card-border-radius, 12px);
          box-shadow: var(--ha-card-box-shadow, 0 2px 6px rgba(0,0,0,.15));
          overflow: hidden;
        }
        .header {
          background: var(--primary-color, #03a9f4);
          color: #fff;
          padding: 11px 16px;
          font-size: 1rem;
          font-weight: 600;
          display: flex;
          align-items: center;
          gap: 8px;
        }
        .header-total {
          margin-left: auto;
          font-size: 0.8rem;
          font-weight: 400;
          opacity: 0.9;
        }
        .period-tabs {
          display: flex;
          border-bottom: 2px solid var(--divider-color, #e0e0e0);
        }
        .tab {
          flex: 1;
          padding: 8px 4px;
          text-align: center;
          font-size: 0.78rem;
          font-weight: 600;
          cursor: pointer;
          color: var(--secondary-text-color, #727272);
          border-bottom: 3px solid transparent;
          margin-bottom: -2px;
          transition: color 0.15s, border-color 0.15s;
          user-select: none;
        }
        .tab.active {
          color: var(--primary-color, #03a9f4);
          border-bottom-color: var(--primary-color, #03a9f4);
        }
        .tab:hover:not(.active) { color: var(--primary-text-color, #212121); }
        .rows { padding: 12px 16px 14px; }
        .drink-row {
          display: grid;
          grid-template-columns: 28px 1fr auto;
          align-items: center;
          gap: 8px;
          margin-bottom: 11px;
        }
        .drink-row:last-child { margin-bottom: 0; }
        .drink-icon { text-align: center; font-size: 1.25rem; }
        .bar-wrap { display: flex; flex-direction: column; gap: 2px; }
        .drink-name {
          font-size: 0.78rem;
          font-weight: 600;
          color: var(--primary-text-color, #212121);
          margin-bottom: 3px;
        }
        .bar-track {
          height: 14px;
          background: var(--divider-color, #eeeeee);
          border-radius: 7px;
          overflow: hidden;
        }
        .bar-fill {
          height: 100%;
          border-radius: 7px;
          transition: width 0.35s ease;
        }
        .bar-count {
          font-size: 0.82rem;
          font-weight: 700;
          min-width: 22px;
          text-align: right;
        }
        .empty {
          padding: 22px 16px;
          text-align: center;
          color: var(--secondary-text-color, #727272);
          font-style: italic;
          font-size: 0.85rem;
        }
        .error { padding: 16px; color: var(--error-color, red); }
      </style>
      <div class="card">
        <div class="header">
          <span>${title}</span>
          <span class="header-total">${total} Bezüge</span>
        </div>
        <div class="period-tabs">
          <div class="tab${period === 'today' ? ' active' : ''}" data-period="today">Heute</div>
          <div class="tab${period === 'week'  ? ' active' : ''}" data-period="week">Diese Woche</div>
          <div class="tab${period === 'all'   ? ' active' : ''}" data-period="all">Gesamt</div>
        </div>
        ${drinks.length === 0
          ? `<div class="empty">Keine Bezüge für ${periodLabels[period]}.</div>`
          : `<div class="rows">${drinks.map(name => {
              const n = zaehler[name];
              const pct = Math.round((n / maxVal) * 100);
              const f = farbe(name);
              return `
                <div class="drink-row">
                  <div class="drink-icon">${getraenkIcon(name)}</div>
                  <div class="bar-wrap">
                    <div class="drink-name">${name}</div>
                    <div class="bar-track">
                      <div class="bar-fill" style="width:${pct}%;background:${f}"></div>
                    </div>
                  </div>
                  <span class="bar-count" style="color:${f}">${n}</span>
                </div>`;
            }).join("")}</div>`
        }
      </div>
    `;

    // Tab-Klick-Handler
    this.shadowRoot.querySelectorAll(".tab").forEach(tab => {
      tab.addEventListener("click", () => {
        this._chartPeriod = tab.dataset.period;
        this._renderChartOnly(hass);
      });
    });
  }

  _renderAlertOnly(hass) {
    const alertEntityId = this.config.alert_entity;
    if (!alertEntityId) {
      this._renderError('Bitte "alert_entity" in der Konfiguration angeben.');
      return;
    }
    const alertObj = hass.states[alertEntityId];
    const alertAttrs = alertObj ? (alertObj.attributes || {}) : {};
    const openAlerts = alertAttrs.open_alerts || [];
    const allAlerts = alertAttrs.all_alerts || [];
    const closedAlerts = allAlerts.filter(a => a.status === "geschlossen").slice(0, 5);
    const title = this.config.title || "⚠️ Alerts";

    // Online-Status
    const onlineEntityId = this.config.online_entity;
    const onlineObj = onlineEntityId ? hass.states[onlineEntityId] : null;
    const isOnline = onlineObj ? (onlineObj.state === "on") : null;
    const isOffline = isOnline === false;

    // Headerfarbe: grau wenn offline, rot wenn Alerts, sonst grün
    const headerBg = isOffline ? "#757575" : (openAlerts.length > 0 ? "#e65100" : "#388e3c");
    const headerIcon = isOffline ? "🔌" : (openAlerts.length > 0 ? "🚨" : "✅");
    const headerBadge = isOffline ? "Offline" : (openAlerts.length > 0 ? `${openAlerts.length} offen` : "OK");

    // Timer stoppen
    if (this._alertTimer) {
      clearInterval(this._alertTimer);
      this._alertTimer = null;
    }

    this.shadowRoot.innerHTML = `
      <style>
        :host { display: block; font-family: var(--primary-font-family, Roboto, sans-serif); }
        .card {
          background: var(--card-background-color, #fff);
          border-radius: var(--ha-card-border-radius, 12px);
          box-shadow: var(--ha-card-box-shadow, 0 2px 6px rgba(0,0,0,.15));
          overflow: hidden;
          ${isOffline ? "opacity: 0.65; filter: grayscale(0.4);" : ""}
        }
        .header {
          background: ${headerBg};
          color: #fff;
          padding: 12px 16px;
          font-size: 1rem;
          font-weight: 600;
          display: flex;
          align-items: center;
          gap: 8px;
        }
        .badge {
          margin-left: auto;
          background: rgba(255,255,255,0.25);
          border-radius: 12px;
          padding: 2px 10px;
          font-size: 0.85rem;
          font-weight: 700;
        }
        .offline-notice {
          display: flex;
          align-items: center;
          gap: 10px;
          padding: 12px 16px;
          font-size: 0.85rem;
          color: var(--secondary-text-color, #727272);
          border-bottom: 1px solid var(--divider-color, #e0e0e0);
          font-style: italic;
        }
        .alert-open {
          display: flex;
          align-items: flex-start;
          gap: 12px;
          padding: 12px 16px;
          border-bottom: 1px solid var(--divider-color, #f0f0f0);
          background: #fff3e0;
          animation: alertPulse 2s ease-in-out infinite;
        }
        @keyframes alertPulse {
          0%, 100% { background: #fff3e0; }
          50% { background: #ffe0b2; }
        }
        .alert-closed {
          display: flex;
          align-items: flex-start;
          gap: 12px;
          padding: 10px 16px;
          border-bottom: 1px solid var(--divider-color, #f0f0f0);
          opacity: 0.6;
        }
        .alert-icon { font-size: 1.4rem; flex-shrink: 0; margin-top: 1px; }
        .alert-info { flex: 1; }
        .alert-title-open { font-weight: 700; font-size: 0.9rem; color: #e65100; }
        .alert-title-closed {
          font-weight: 600;
          font-size: 0.85rem;
          color: var(--primary-text-color, #212121);
          text-decoration: line-through;
        }
        .alert-meta { font-size: 0.72rem; color: var(--secondary-text-color, #727272); margin-top: 2px; }
        .alert-since {
          display: inline-block;
          background: #ff5722;
          color: #fff;
          font-size: 0.7rem;
          font-weight: 700;
          padding: 2px 8px;
          border-radius: 10px;
          white-space: nowrap;
          margin-top: 4px;
        }
        .section-label {
          padding: 6px 16px 4px;
          font-size: 0.72rem;
          font-weight: 700;
          text-transform: uppercase;
          letter-spacing: 0.05em;
          color: var(--secondary-text-color, #9e9e9e);
          background: var(--secondary-background-color, #f5f5f5);
          border-bottom: 1px solid var(--divider-color, #e0e0e0);
        }
        .no-alerts {
          padding: 14px 16px;
          font-size: 0.85rem;
          color: #388e3c;
          display: flex;
          align-items: center;
          gap: 8px;
        }
        .error { padding: 16px; color: var(--error-color, red); }
      </style>
      <div class="card">
        <div class="header">
          <span>${headerIcon}</span>
          <span>${title}</span>
          <span class="badge">${headerBadge}</span>
        </div>
        ${isOffline ? `
          <div class="offline-notice">
            🔌 Keine Verbindung zur Maschine – Statusdaten werden nicht aktualisiert
          </div>
        ` : ""}
        ${!isOffline ? (
          openAlerts.length === 0
            ? '<div class="no-alerts">✅ Keine offenen Alerts \u2013 alle Systeme in Ordnung</div>'
            : `
              <div class="section-label">Offene Alerts</div>
              ${openAlerts.map(a => `
                <div class="alert-open">
                  <div class="alert-icon">🚨</div>
                  <div class="alert-info">
                    <div class="alert-title-open">${a.description || "Unbekannter Fehler"} (Code ${a.errorCode ?? "?"})</div>
                    <div class="alert-meta">
                      ${a.category ? `Kategorie: ${a.category}` : ""}
                      ${a.severity ? ` · ${a.severity}` : ""}
                      ${a.storeId ? ` · 📍 ${a.storeId}` : ""}
                    </div>
                    <div class="alert-meta">Geöffnet: ${formatZeitstempel(a.raiseTime)}</div>
                    <span class="alert-since">⚡ OFFEN seit <span class="alert-duration" data-raise-time="${a.raiseTime}">${calcDuration(a.raiseTime)}</span></span>
                  </div>
                </div>`).join("")}
            `
        ) : ""}
        ${closedAlerts.length > 0 ? `
          <div class="section-label">Letzte geschlossene Alerts</div>
          ${closedAlerts.map(a => `
            <div class="alert-closed">
              <div class="alert-icon">✅</div>
              <div class="alert-info">
                <div class="alert-title-closed">${a.description || "Unbekannter Fehler"} (Code ${a.errorCode ?? "?"})</div>
                <div class="alert-meta">⏱️ Dauer: ${calcDuration(a.raiseTime, a.clearTime)}</div>
                <div class="alert-meta">${formatZeitstempel(a.raiseTime)} → ${formatZeitstempel(a.clearTime)}</div>
              </div>
            </div>`).join("")}
        ` : ""}
      </div>
    `;

    if (!isOffline && openAlerts.length > 0) {
      this._startAlertTimer();
    }
  }

  setConfig(config) {
    if (!config.alert_only && !config.chart_only && !config.entity) {
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
      alert_entity: "sensor.kaffeemaschine_alert_timeline",
      online_entity: "binary_sensor.konnektivitat",
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
