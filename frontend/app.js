const API_BASE = (window.AEGIS_API_BASE || "http://localhost:8000").replace(/\/$/, "");
const WS_BASE  = API_BASE.replace(/^http/, "ws");

const incidentListEl = document.getElementById("incident-list");
const detailBoxEl    = document.getElementById("detail-box");
const summaryPillEl  = document.getElementById("summary-pill");
const chatLogEl      = document.getElementById("chat-log");
const chatInputEl    = document.getElementById("chat-input");
const chatSendEl     = document.getElementById("chat-send");
const searchInputEl  = document.getElementById("search-input");
const errorBannerEl  = document.getElementById("error-banner");
const wsDotEl        = document.getElementById("ws-dot");
const wsLabelEl      = document.getElementById("ws-label");

let incidents        = [];
let filteredIncidents = [];
let activeIncidentId = null;
let activeIncident   = null;
let severityFilter   = null;
let statusFilter     = null;
let searchTimer      = null;
let isSearchActive   = false;
let chatLoading      = false;
let ws               = null;
let wsConnected      = false;
let wsRetryTimer     = null;

// ── Utilities ─────────────────────────────────────────────────────────────────

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function relativeTime(dateStr) {
  if (!dateStr) return "";
  const diff = Date.now() - new Date(dateStr).getTime();
  const s = Math.floor(diff / 1000);
  if (s < 60)   return "just now";
  const m = Math.floor(s / 60);
  if (m < 60)   return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24)   return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

function severityClass(sev) {
  if (!sev) return "badge badge-low";
  const s = sev.toLowerCase();
  if (s === "critical")          return "badge badge-critical";
  if (s === "high")              return "badge badge-high";
  if (s === "medium")            return "badge badge-medium";
  return "badge badge-low";
}

function showError(msg) {
  errorBannerEl.textContent = msg;
  errorBannerEl.style.display = "block";
  setTimeout(() => { errorBannerEl.style.display = "none"; }, 5000);
}

// ── WebSocket ─────────────────────────────────────────────────────────────────

function setWsStatus(connected) {
  wsConnected = connected;
  if (wsDotEl) {
    wsDotEl.className = "ws-dot " + (connected ? "connected" : "disconnected");
  }
  if (wsLabelEl) {
    wsLabelEl.textContent = connected ? "LIVE" : "POLLING";
  }
}

function connectWs() {
  if (ws) { try { ws.close(); } catch (_) {} }
  ws = new WebSocket(`${WS_BASE}/ws/incidents`);

  ws.onopen = () => {
    setWsStatus(true);
    clearTimeout(wsRetryTimer);
  };

  ws.onmessage = (ev) => {
    try {
      const msg = JSON.parse(ev.data);
      if (msg.type === "incidents" && Array.isArray(msg.data)) {
        incidents = msg.data;
        applyFilters();
        // Update active incident if it's in the new data
        if (activeIncidentId) {
          const updated = incidents.find((i) => i.id === activeIncidentId);
          if (updated) activeIncident = updated;
        }
      }
    } catch (_) {}
  };

  ws.onerror = () => {
    setWsStatus(false);
  };

  ws.onclose = () => {
    setWsStatus(false);
    wsRetryTimer = setTimeout(connectWs, 8000);
  };
}

// ── Stats ─────────────────────────────────────────────────────────────────────

async function fetchStats() {
  try {
    const res = await fetch(`${API_BASE}/stats`);
    if (!res.ok) return;
    const s = await res.json();
    const byId = {
      "hstat-high":     s.high_open   ?? "—",
      "hstat-med":      s.medium_open ?? "—",
      "hstat-resolved": s.resolved    ?? "—",
      "hstat-total":    s.total       ?? "—",
    };
    for (const [id, val] of Object.entries(byId)) {
      const el = document.getElementById(id);
      if (el) el.textContent = val;
    }
  } catch (_) {}
}

// ── Incidents list ─────────────────────────────────────────────────────────────

async function fetchIncidents() {
  try {
    const res = await fetch(`${API_BASE}/incidents?limit=100`);
    if (!res.ok) throw new Error("Failed to fetch incidents");
    incidents = await res.json();
    applyFilters();
  } catch (err) {
    console.error(err);
    showError("Failed to load incidents.");
    summaryPillEl.textContent = "Failed to load incidents.";
  }
}

function applyFilters() {
  filteredIncidents = incidents.filter((i) => {
    if (severityFilter && (i.severity || "unknown").toLowerCase() !== severityFilter) return false;
    if (statusFilter   && (i.status   || "open").toLowerCase()    !== statusFilter)   return false;
    return true;
  });
  renderIncidents();
}

function renderIncidents() {
  incidentListEl.innerHTML = "";

  if (!filteredIncidents.length) {
    summaryPillEl.textContent = incidents.length
      ? "No incidents match filters"
      : "No incidents found";
    return;
  }

  const total = filteredIncidents.length;
  const bySev = {};
  filteredIncidents.forEach((i) => {
    const s = (i.severity || "unknown").toLowerCase();
    bySev[s] = (bySev[s] || 0) + 1;
  });
  const sevStr = Object.entries(bySev)
    .sort((a, b) => b[1] - a[1])
    .map(([s, n]) => `${n} ${s}`)
    .join(" · ");
  summaryPillEl.textContent = `${total} incident${total !== 1 ? "s" : ""} — ${sevStr}`;

  filteredIncidents.forEach((inc) => {
    const li = document.createElement("li");
    li.className = "incident-item";
    li.dataset.id = inc.id;
    li.dataset.severity = (inc.severity || "unknown").toLowerCase();
    if (inc.id === activeIncidentId) li.classList.add("active");

    const top = document.createElement("div");
    top.className = "inc-top";

    const titleEl = document.createElement("div");
    titleEl.className = "inc-title";
    titleEl.textContent = inc.title || "(no title)";

    const sevBadge = document.createElement("span");
    sevBadge.className = severityClass(inc.severity);
    sevBadge.textContent = (inc.severity || "unknown").toUpperCase();

    top.appendChild(titleEl);
    top.appendChild(sevBadge);

    const foot = document.createElement("div");
    foot.className = "inc-footer";

    const tenantPill = document.createElement("span");
    tenantPill.className = "pill";
    tenantPill.textContent = inc.tenant || "default";

    const statusTag = document.createElement("span");
    statusTag.className = "status-tag";
    statusTag.textContent = (inc.status || "open").toUpperCase();

    const timeTag = document.createElement("span");
    timeTag.className = "inc-time";
    timeTag.textContent = relativeTime(inc.created_at);

    foot.appendChild(tenantPill);
    foot.appendChild(statusTag);
    foot.appendChild(timeTag);

    li.appendChild(top);
    li.appendChild(foot);

    li.addEventListener("click", () => {
      activeIncidentId = inc.id;
      activeIncident   = inc;
      renderIncidents();
      renderIncidentDetail(inc);
    });

    incidentListEl.appendChild(li);
  });
}

// ── Incident detail ────────────────────────────────────────────────────────────

function renderIncidentDetail(inc) {
  if (!inc) {
    detailBoxEl.innerHTML = `<div class="detail-empty">Select an incident to view details</div>`;
    return;
  }

  const sev    = inc.severity   || "unknown";
  const status = inc.status     || "open";
  const tenant = inc.tenant     || "default";
  const source = inc.source     || "—";
  const created = inc.created_at
    ? new Date(inc.created_at).toLocaleString(undefined, { dateStyle: "short", timeStyle: "medium" })
    : "—";
  const rawSafe = escapeHtml(inc.raw_log || "");

  detailBoxEl.innerHTML = `
    <div class="detail-inner">
      <div class="detail-title">${escapeHtml(inc.title || "(no title)")}</div>
      <div class="detail-chips">
        <span class="pill">${escapeHtml(tenant)}</span>
        <span class="${severityClass(sev)}">${sev.toUpperCase()}</span>
        <span class="status-tag">${status.toUpperCase()}</span>
      </div>
      <div class="detail-grid">
        <span class="dg-label">TENANT</span>  <span class="dg-val">${escapeHtml(tenant)}</span>
        <span class="dg-label">CREATED</span> <span class="dg-val">${created}</span>
        <span class="dg-label">SOURCE</span>  <span class="dg-val">${escapeHtml(source)}</span>
        <span class="dg-label">ID</span>      <span class="dg-val">${escapeHtml(inc.id)}</span>
      </div>
      <div class="log-label">RAW LOG</div>
      <div class="log-body">${rawSafe}</div>
    </div>`;

  // Action buttons
  const actions = document.createElement("div");
  actions.className = "detail-actions";
  actions.style.padding = "0 1.1rem 0.75rem";

  if (status !== "acknowledged" && status !== "resolved") {
    const ack = document.createElement("button");
    ack.className = "action-btn";
    ack.textContent = "ACKNOWLEDGE";
    ack.addEventListener("click", () => updateStatus(inc.id, "acknowledged"));
    actions.appendChild(ack);
  }
  if (status !== "resolved") {
    const res = document.createElement("button");
    res.className = "action-btn action-btn-resolve";
    res.textContent = "RESOLVE";
    res.addEventListener("click", () => updateStatus(inc.id, "resolved"));
    actions.appendChild(res);
  }

  // AI Runbook button
  const rbBtn = document.createElement("button");
  rbBtn.className = "action-btn action-btn-ai";
  rbBtn.id = "runbook-btn";
  rbBtn.textContent = "Generate Runbook";
  rbBtn.addEventListener("click", () => generateRunbook(inc.id, rbBtn));
  actions.appendChild(rbBtn);

  if (actions.children.length) detailBoxEl.appendChild(actions);

  // Runbook section (hidden until generated)
  const rbSection = document.createElement("div");
  rbSection.className = "runbook-section";
  rbSection.id = "runbook-section";
  rbSection.style.display = "none";
  rbSection.style.padding = "0 1.1rem 0.75rem";
  rbSection.innerHTML = `
    <div class="runbook-label">AI Runbook</div>
    <div class="runbook-body" id="runbook-body"></div>`;
  detailBoxEl.appendChild(rbSection);

  // Timeline section
  const tlSection = document.createElement("div");
  tlSection.className = "timeline-section";
  tlSection.style.padding = "0 1.1rem 1rem";
  tlSection.innerHTML = `
    <div class="timeline-label">Audit Trail</div>
    <div class="timeline" id="timeline"></div>`;
  detailBoxEl.appendChild(tlSection);

  // Load timeline events
  loadTimeline(inc.id);
}

async function updateStatus(id, status) {
  try {
    const res = await fetch(`${API_BASE}/incidents/${encodeURIComponent(id)}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status }),
    });
    if (!res.ok) throw new Error("Update failed");
    const updated = await res.json();
    const idx = incidents.findIndex((i) => i.id === id);
    if (idx !== -1) incidents[idx] = updated;
    activeIncident = updated;
    applyFilters();
    renderIncidentDetail(updated);
    fetchStats();
  } catch (err) {
    console.error(err);
    showError("Failed to update incident status.");
  }
}

// ── AI Runbook ─────────────────────────────────────────────────────────────────

async function generateRunbook(incidentId, btn) {
  btn.disabled = true;
  btn.textContent = "Generating...";

  try {
    const res = await fetch(`${API_BASE}/incidents/${encodeURIComponent(incidentId)}/runbook`, {
      method: "POST",
    });
    if (!res.ok) throw new Error("Runbook generation failed");
    const data = await res.json();

    const rbSection = document.getElementById("runbook-section");
    const rbBody    = document.getElementById("runbook-body");
    if (rbSection && rbBody) {
      rbBody.textContent = data.runbook || "(no runbook returned)";
      rbSection.style.display = "block";
    }

    btn.textContent = "Regenerate";
    // Reload timeline to show runbook_generated event
    loadTimeline(incidentId);
  } catch (err) {
    console.error(err);
    showError("Failed to generate runbook.");
    btn.textContent = "⚡ AI RUNBOOK";
  } finally {
    btn.disabled = false;
  }
}

// ── Audit timeline ─────────────────────────────────────────────────────────────

async function loadTimeline(incidentId) {
  const tlEl = document.getElementById("timeline");
  if (!tlEl) return;

  try {
    const res = await fetch(`${API_BASE}/incidents/${encodeURIComponent(incidentId)}/events`);
    if (!res.ok) throw new Error("Failed to load events");
    const events = await res.json();

    if (!events.length) {
      tlEl.innerHTML = `<div style="font-size:0.72rem;font-family:var(--mono);color:var(--text-off);padding:0.25rem 0;">No events yet</div>`;
      return;
    }

    tlEl.innerHTML = events.map((ev) => {
      const typeClass = escapeHtml((ev.event_type || "").replace(/[^a-z_]/gi, ""));
      const time = ev.created_at
        ? new Date(ev.created_at).toLocaleTimeString(undefined, { timeStyle: "short" })
        : "";
      const note = escapeHtml(ev.note || "");
      return `
        <div class="tl-item">
          <span class="tl-type ${typeClass}">${escapeHtml(ev.event_type || "")}</span>
          <span class="tl-note">${note}</span>
          <span class="tl-time">${time}</span>
        </div>`;
    }).join("");
  } catch (err) {
    console.error(err);
    if (tlEl) tlEl.innerHTML = `<div style="font-size:0.72rem;font-family:var(--mono);color:var(--text-off);">Failed to load timeline</div>`;
  }
}

// ── Search ─────────────────────────────────────────────────────────────────────

searchInputEl.addEventListener("input", () => {
  clearTimeout(searchTimer);
  const q = searchInputEl.value.trim();
  if (!q) {
    isSearchActive = false;
    fetchIncidents();
    return;
  }
  searchTimer = setTimeout(() => doSearch(q), 350);
});

async function doSearch(q) {
  try {
    isSearchActive = true;
    const res = await fetch(`${API_BASE}/incidents/search?q=${encodeURIComponent(q)}&limit=100`);
    if (!res.ok) throw new Error("Search failed");
    incidents = await res.json();
    applyFilters();
  } catch (err) {
    console.error(err);
    showError("Search failed. Elasticsearch may be unavailable.");
  }
}

// ── Filter pills ───────────────────────────────────────────────────────────────

document.querySelectorAll(".filter-pill").forEach((pill) => {
  pill.addEventListener("click", () => {
    const type  = pill.dataset.type;
    const value = pill.dataset.filter;

    document.querySelectorAll(`.filter-pill[data-type="${type}"]`)
      .forEach((p) => p.classList.remove("active"));
    pill.classList.add("active");

    if (type === "severity") severityFilter = value || null;
    else if (type === "status") statusFilter = value || null;

    applyFilters();
  });
});

// ── Chat ───────────────────────────────────────────────────────────────────────

function appendChatMessage(text, who) {
  const hint = chatLogEl.querySelector(".chat-hint");
  if (hint) chatLogEl.removeChild(hint);

  const div = document.createElement("div");
  div.className = `chat-msg ${who}`;

  const safe = escapeHtml(text).replace(/\n/g, "<br>");
  div.innerHTML = safe;

  chatLogEl.appendChild(div);
  chatLogEl.scrollTop = chatLogEl.scrollHeight;
  return div;
}

async function handleChat() {
  const q = chatInputEl.value.trim();
  if (!q || chatLoading) return;

  chatLoading = true;
  chatSendEl.disabled = true;
  appendChatMessage(q, "user");
  chatInputEl.value = "";

  const thinkingEl = appendChatMessage("thinking…", "bot thinking");

  try {
    const res = await fetch(`${API_BASE}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: q }),
    });
    if (thinkingEl.parentNode) chatLogEl.removeChild(thinkingEl);
    if (!res.ok) throw new Error("Chat request failed");
    const data = await res.json();
    appendChatMessage(data.answer, "bot");
  } catch (err) {
    console.error(err);
    if (thinkingEl.parentNode) chatLogEl.removeChild(thinkingEl);
    appendChatMessage("Sorry, I couldn't get a response. Please try again.", "bot");
  } finally {
    chatLoading = false;
    chatSendEl.disabled = false;
  }
}

chatSendEl.addEventListener("click", handleChat);
chatInputEl.addEventListener("keydown", (e) => {
  if (e.key === "Enter") { e.preventDefault(); handleChat(); }
});

// ── Bootstrap ──────────────────────────────────────────────────────────────────

// Initial data load
fetchIncidents();
fetchStats();

// WebSocket for real-time updates
connectWs();

// Fallback polling: 30s when WS disconnected; stats every 60s
setInterval(() => { if (!wsConnected && !isSearchActive) fetchIncidents(); }, 30_000);
setInterval(fetchStats, 60_000);
