from fastapi import APIRouter, FastAPI
from fastapi.responses import HTMLResponse


def init_web_interfaces(app: FastAPI) -> None:
    """Mount a lightweight read-only web console for manual overview checks."""
    router = APIRouter()

    @router.get("/", response_class=HTMLResponse, include_in_schema=False)
    def overview_console() -> HTMLResponse:
        return HTMLResponse(_build_overview_console_html())

    app.include_router(router)


def _build_overview_console_html() -> str:
    """Return a lightweight read-only console for the aggregated user overview."""
    return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>VitalAI Overview Console</title>
  <style>
    :root {
      --paper: #f6f1e8;
      --ink: #1c2421;
      --muted: #5f6a64;
      --panel: rgba(255, 252, 245, 0.84);
      --line: rgba(28, 36, 33, 0.14);
      --accent: #1f6f5f;
      --accent-soft: #d5ebe5;
      --warn: #a44a3f;
      --warm: #c07a2b;
      --shadow: 0 20px 60px rgba(30, 45, 39, 0.12);
      --radius: 22px;
      --serif: "Iowan Old Style", "Palatino Linotype", "Book Antiqua", Georgia, serif;
      --sans: "Trebuchet MS", "Segoe UI", sans-serif;
    }

    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: var(--sans);
      color: var(--ink);
      background:
        radial-gradient(circle at top left, rgba(31,111,95,0.16), transparent 32%),
        radial-gradient(circle at top right, rgba(192,122,43,0.18), transparent 24%),
        linear-gradient(180deg, #fbf7f0 0%, var(--paper) 100%);
      min-height: 100vh;
    }

    .shell {
      width: min(1180px, calc(100vw - 32px));
      margin: 0 auto;
      padding: 28px 0 40px;
    }

    .hero {
      display: grid;
      grid-template-columns: 1.2fr 0.8fr;
      gap: 18px;
      align-items: stretch;
      margin-bottom: 18px;
    }

    .hero-card, .panel {
      background: var(--panel);
      backdrop-filter: blur(10px);
      border: 1px solid var(--line);
      border-radius: var(--radius);
      box-shadow: var(--shadow);
    }

    .hero-card {
      padding: 28px;
      position: relative;
      overflow: hidden;
    }

    .hero-card::after {
      content: "";
      position: absolute;
      inset: auto -80px -80px auto;
      width: 220px;
      height: 220px;
      border-radius: 50%;
      background: radial-gradient(circle, rgba(31,111,95,0.18), transparent 70%);
    }

    .eyebrow {
      font-size: 12px;
      letter-spacing: 0.24em;
      text-transform: uppercase;
      color: var(--muted);
      margin-bottom: 10px;
    }

    h1 {
      margin: 0;
      font-family: var(--serif);
      font-size: clamp(36px, 5vw, 62px);
      line-height: 0.95;
      letter-spacing: -0.04em;
    }

    .lead {
      max-width: 60ch;
      color: var(--muted);
      font-size: 15px;
      line-height: 1.6;
      margin-top: 14px;
    }

    .hero-side {
      padding: 22px;
      display: flex;
      flex-direction: column;
      gap: 12px;
      justify-content: space-between;
    }

    .hint {
      padding: 12px 14px;
      border-radius: 16px;
      background: rgba(31,111,95,0.08);
      border: 1px solid rgba(31,111,95,0.14);
      color: var(--ink);
      font-size: 14px;
      line-height: 1.5;
    }

    .toolbar {
      display: grid;
      grid-template-columns: 1.4fr 0.6fr 0.8fr auto;
      gap: 12px;
      padding: 16px;
      margin-bottom: 18px;
    }

    label {
      display: block;
      font-size: 12px;
      color: var(--muted);
      text-transform: uppercase;
      letter-spacing: 0.16em;
      margin-bottom: 8px;
    }

    input {
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 12px 14px;
      font: inherit;
      color: var(--ink);
      background: rgba(255,255,255,0.75);
      outline: none;
    }

    input:focus {
      border-color: var(--accent);
      box-shadow: 0 0 0 3px rgba(31,111,95,0.14);
    }

    button {
      align-self: end;
      border: 0;
      border-radius: 16px;
      background: linear-gradient(135deg, var(--accent), #255046);
      color: white;
      padding: 13px 18px;
      font: inherit;
      font-weight: 600;
      cursor: pointer;
      min-width: 120px;
    }

    button:hover { filter: brightness(1.03); }

    .grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 18px;
    }

    .panel { padding: 18px; }

    .panel h2 {
      margin: 0 0 12px;
      font-family: var(--serif);
      font-size: 28px;
      letter-spacing: -0.03em;
    }

    .subtle {
      color: var(--muted);
      font-size: 14px;
      margin-bottom: 14px;
    }

    .summary-strip {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 10px;
      margin-bottom: 14px;
    }

    .metric {
      padding: 14px;
      border-radius: 16px;
      background: rgba(255,255,255,0.7);
      border: 1px solid var(--line);
    }

    .metric strong {
      display: block;
      font-size: 28px;
      font-family: var(--serif);
      line-height: 1;
      margin-bottom: 4px;
    }

    .metric span {
      color: var(--muted);
      font-size: 13px;
    }

    .list {
      display: grid;
      gap: 10px;
    }

    .item {
      padding: 12px 14px;
      border-radius: 16px;
      border: 1px solid var(--line);
      background: rgba(255,255,255,0.68);
    }

    .item-top {
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: baseline;
      margin-bottom: 6px;
    }

    .badge {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 5px 10px;
      border-radius: 999px;
      background: var(--accent-soft);
      color: var(--accent);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }

    .badge.warn {
      background: rgba(164,74,63,0.12);
      color: var(--warn);
    }

    .badge.warm {
      background: rgba(192,122,43,0.15);
      color: var(--warm);
    }

    .mono {
      color: var(--muted);
      font-size: 12px;
      word-break: break-all;
    }

    .empty {
      padding: 18px;
      border-radius: 16px;
      border: 1px dashed var(--line);
      color: var(--muted);
      background: rgba(255,255,255,0.42);
    }

    .status {
      margin-top: 12px;
      padding: 12px 14px;
      border-radius: 14px;
      border: 1px solid var(--line);
      color: var(--muted);
      background: rgba(255,255,255,0.6);
      min-height: 48px;
    }

    @media (max-width: 940px) {
      .hero, .grid { grid-template-columns: 1fr; }
      .toolbar { grid-template-columns: 1fr; }
      .summary-strip { grid-template-columns: 1fr 1fr; }
      button { width: 100%; }
    }
  </style>
</head>
<body>
  <main class="shell">
    <section class="hero">
      <article class="hero-card">
        <div class="eyebrow">VitalAI Manual Console</div>
        <h1>User Overview</h1>
        <p class="lead">
          A lightweight read-only console for manual triage. It pulls the existing
          <code>/vitalai/users/{user_id}/overview</code> API and turns it into one page that is easier
          to scan than raw JSON.
        </p>
      </article>
      <aside class="hero-card hero-side">
        <div class="hint">Best for smoke checks, demo walkthroughs, and quickly sanity-checking one user after writing a few typed-flow records.</div>
        <div class="hint">This page does not add any new business behavior. It only reads the overview API and renders existing snapshots, timeline items, and attention hints.</div>
      </aside>
    </section>

    <section class="panel toolbar">
      <div>
        <label for="user-id">User ID</label>
        <input id="user-id" value="elder-http-overview-smoke" />
      </div>
      <div>
        <label for="history-limit">History Limit</label>
        <input id="history-limit" type="number" min="1" max="20" value="3" />
      </div>
      <div>
        <label for="memory-key">Memory Key</label>
        <input id="memory-key" value="" placeholder="optional" />
      </div>
      <button id="load-btn" type="button">Load Overview</button>
    </section>

    <section class="panel" id="summary-panel">
      <h2>Overview Snapshot</h2>
      <div class="subtle">Waiting for a user overview request.</div>
      <div class="summary-strip" id="summary-strip"></div>
      <div class="status" id="status-box">Enter a user id and load the current overview.</div>
    </section>

    <section class="grid">
      <article class="panel">
        <h2>Attention</h2>
        <div class="subtle" id="attention-summary">No overview loaded yet.</div>
        <div class="list" id="attention-list"></div>
      </article>
      <article class="panel">
        <h2>Recent Activity</h2>
        <div class="subtle" id="activity-meta">No overview loaded yet.</div>
        <div class="list" id="activity-list"></div>
      </article>
      <article class="panel">
        <h2>Snapshots</h2>
        <div class="list" id="snapshot-list"></div>
      </article>
      <article class="panel">
        <h2>Raw Response</h2>
        <div class="subtle">Useful when we need exact JSON while still staying in one page.</div>
        <pre id="raw-json" class="item mono" style="white-space: pre-wrap;"></pre>
      </article>
    </section>
  </main>

  <script>
    const userIdInput = document.getElementById("user-id");
    const historyLimitInput = document.getElementById("history-limit");
    const memoryKeyInput = document.getElementById("memory-key");
    const loadBtn = document.getElementById("load-btn");
    const summaryStrip = document.getElementById("summary-strip");
    const statusBox = document.getElementById("status-box");
    const attentionSummary = document.getElementById("attention-summary");
    const attentionList = document.getElementById("attention-list");
    const activityMeta = document.getElementById("activity-meta");
    const activityList = document.getElementById("activity-list");
    const snapshotList = document.getElementById("snapshot-list");
    const rawJson = document.getElementById("raw-json");

    function escapeHtml(value) {
      return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#39;");
    }

    function renderEmpty(container, message) {
      container.innerHTML = `<div class="empty">${escapeHtml(message)}</div>`;
    }

    function renderMetrics(data) {
      const overview = data.overview || {};
      const profile = overview.profile_memory || {};
      const health = overview.health || {};
      const daily = overview.daily_life || {};
      const mental = overview.mental_care || {};
      summaryStrip.innerHTML = [
        ["Profile Memory", profile.memory_count ?? 0],
        ["Health Alerts", health.alert_count ?? 0],
        ["Daily-Life", daily.checkin_count ?? 0],
        ["Mental-Care", mental.checkin_count ?? 0],
      ].map(([label, value]) => `
        <div class="metric">
          <strong>${escapeHtml(value)}</strong>
          <span>${escapeHtml(label)}</span>
        </div>
      `).join("");
    }

    function badgeClass(value) {
      const normalized = String(value).toLowerCase();
      if (["critical", "high", "warn"].includes(normalized)) return "badge warn";
      if (["medium", "normal"].includes(normalized)) return "badge warm";
      return "badge";
    }

    function renderAttention(data) {
      attentionSummary.textContent = data.attention_summary || "No attention summary.";
      const items = Array.isArray(data.attention_items) ? data.attention_items : [];
      if (!items.length) {
        renderEmpty(attentionList, "No immediate attention items.");
        return;
      }
      attentionList.innerHTML = items.map((item) => `
        <div class="item">
          <div class="item-top">
            <span class="${badgeClass(item.severity)}">${escapeHtml(item.domain)} · ${escapeHtml(item.severity)}</span>
            <span class="mono">${escapeHtml(item.item_id)}</span>
          </div>
          <div>${escapeHtml(item.summary)}</div>
        </div>
      `).join("");
    }

    function renderActivity(data) {
      const items = Array.isArray(data.recent_activity) ? data.recent_activity : [];
      activityMeta.textContent = data.latest_activity_at
        ? `Latest activity at ${data.latest_activity_at}`
        : "No recent activity in this overview.";
      if (!items.length) {
        renderEmpty(activityList, "No recent activity found.");
        return;
      }
      activityList.innerHTML = items.map((item) => `
        <div class="item">
          <div class="item-top">
            <span class="badge">${escapeHtml(item.domain)}</span>
            <span class="mono">${escapeHtml(item.occurred_at)}</span>
          </div>
          <div>${escapeHtml(item.summary)}</div>
        </div>
      `).join("");
    }

    function renderSnapshots(data) {
      const overview = data.overview || {};
      const blocks = [
        ["Profile Memory", overview.profile_memory?.readable_summary, overview.profile_memory?.entries?.length ?? 0],
        ["Health", overview.health?.readable_summary, overview.health?.entries?.length ?? 0],
        ["Daily-Life", overview.daily_life?.readable_summary, overview.daily_life?.entries?.length ?? 0],
        ["Mental-Care", overview.mental_care?.readable_summary, overview.mental_care?.entries?.length ?? 0],
      ];
      snapshotList.innerHTML = blocks.map(([title, summary, count]) => `
        <div class="item">
          <div class="item-top">
            <strong>${escapeHtml(title)}</strong>
            <span class="mono">${escapeHtml(count)} entr${count === 1 ? "y" : "ies"}</span>
          </div>
          <div>${escapeHtml(summary || "No summary available.")}</div>
        </div>
      `).join("");
    }

    async function loadOverview() {
      const userId = userIdInput.value.trim();
      const historyLimit = historyLimitInput.value.trim() || "3";
      const memoryKey = memoryKeyInput.value.trim();

      if (!userId) {
        statusBox.textContent = "User id is required.";
        return;
      }

      loadBtn.disabled = true;
      statusBox.textContent = "Loading overview...";

      try {
        const params = new URLSearchParams({ history_limit: historyLimit });
        if (memoryKey) params.set("memory_key", memoryKey);
        const response = await fetch(`/vitalai/users/${encodeURIComponent(userId)}/overview?${params.toString()}`);
        const data = await response.json();
        rawJson.textContent = JSON.stringify(data, null, 2);
        renderMetrics(data);
        renderAttention(data);
        renderActivity(data);
        renderSnapshots(data);
        statusBox.textContent = data.accepted
          ? `Loaded overview for ${userId}.`
          : `Overview request returned accepted=false for ${userId}.`;
      } catch (error) {
        statusBox.textContent = `Failed to load overview: ${error}`;
        rawJson.textContent = "";
        renderEmpty(attentionList, "No attention data due to request failure.");
        renderEmpty(activityList, "No activity data due to request failure.");
        renderEmpty(snapshotList, "No snapshot data due to request failure.");
      } finally {
        loadBtn.disabled = false;
      }
    }

    loadBtn.addEventListener("click", loadOverview);
  </script>
</body>
</html>"""
