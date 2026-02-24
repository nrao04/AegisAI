const API_BASE = (window.AEGIS_API_BASE || "http://localhost:8000").replace(
  /\/$/,
  ""
);

const incidentListEl = document.getElementById("incident-list");
const detailBoxEl = document.getElementById("detail-box");
const summaryPillEl = document.getElementById("summary-pill");
const chatLogEl = document.getElementById("chat-log");
const chatInputEl = document.getElementById("chat-input");
const chatSendEl = document.getElementById("chat-send");

let incidents = [];
let activeIncidentId = null;

function severityClass(sev) {
  if (!sev) return "";
  const s = sev.toLowerCase();
  if (s === "high" || s === "critical") return "badge badge-high";
  if (s === "medium") return "badge badge-medium";
  return "badge badge-low";
}

async function fetchIncidents() {
  try {
    const res = await fetch(`${API_BASE}/incidents?limit=50`);
    if (!res.ok) throw new Error("Failed to fetch incidents");
    incidents = await res.json();
    renderIncidents();
  } catch (err) {
    console.error(err);
    summaryPillEl.textContent = "Failed to load incidents.";
  }
}

function renderIncidents() {
  incidentListEl.innerHTML = "";
  if (!incidents.length) {
    summaryPillEl.textContent = "No incidents found.";
    return;
  }

  const total = incidents.length;
  const bySeverity = {};
  incidents.forEach((i) => {
    const sev = (i.severity || "unknown").toLowerCase();
    bySeverity[sev] = (bySeverity[sev] || 0) + 1;
  });

  const sevParts = Object.entries(bySeverity)
    .sort((a, b) => b[1] - a[1])
    .map(([sev, count]) => `${count} ${sev}`)
    .join(", ");

  summaryPillEl.textContent = `${total} incident(s) – ${sevParts}`;

  incidents.forEach((inc) => {
    const li = document.createElement("li");
    li.className = "incident-item";
    li.dataset.id = inc.id;
    if (inc.id === activeIncidentId) li.classList.add("active");

    const left = document.createElement("div");
    left.className = "incident-title";
    left.textContent = inc.title || "(no title)";

    const right = document.createElement("div");
    right.className = "incident-meta";
    const sev = document.createElement("span");
    sev.className = severityClass(inc.severity);
    sev.textContent = inc.severity || "unknown";
    const status = document.createElement("span");
    status.textContent = inc.status || "open";

    right.appendChild(sev);
    right.appendChild(status);
    li.appendChild(left);
    li.appendChild(right);

    li.addEventListener("click", () => {
      activeIncidentId = inc.id;
      renderIncidents();
      renderIncidentDetail(inc);
    });

    incidentListEl.appendChild(li);
  });
}

function renderIncidentDetail(inc) {
  if (!inc) {
    detailBoxEl.textContent = "Select an incident to see details here.";
    return;
  }
  const created = inc.created_at || "";
  const title = inc.title || "(no title)";
  const sev = inc.severity || "unknown";
  const status = inc.status || "open";
  const raw = inc.raw_log || "";

  detailBoxEl.innerHTML = `
    <div class="detail-header">
      <h3>${title}</h3>
      <div class="detail-meta">
        <span class="badge ${severityClass(sev)}">${sev}</span>
        <span>${status}</span>
      </div>
    </div>
    <div class="detail-meta">Created at: ${created}</div>
    <hr style="border-color:#111827;margin:0.5rem 0;" />
    <div>${raw.replace(/</g, "&lt;").replace(/>/g, "&gt;")}</div>
  `;
}

function appendChatMessage(text, who) {
  const div = document.createElement("div");
  div.className = `chat-msg ${who}`;
  div.textContent = text;
  chatLogEl.appendChild(div);
  chatLogEl.scrollTop = chatLogEl.scrollHeight;
}

async function handleChat() {
  const q = chatInputEl.value.trim();
  if (!q) return;
  appendChatMessage(q, "user");
  chatInputEl.value = "";

  // For now, mimic the chatbot's "what's broken" behavior client-side.
  if (q.toLowerCase().includes("what's broken") || q.toLowerCase().includes("whats broken")) {
    if (!incidents.length) {
      await fetchIncidents();
    }
    if (!incidents.length) {
      appendChatMessage("No recent incidents found.", "bot");
      return;
    }
    const total = incidents.length;
    const bySeverity = {};
    const byStatus = {};
    incidents.forEach((i) => {
      const sev = (i.severity || "unknown").toLowerCase();
      const status = (i.status || "open").toLowerCase();
      bySeverity[sev] = (bySeverity[sev] || 0) + 1;
      byStatus[status] = (byStatus[status] || 0) + 1;
    });
    const sevParts = Object.entries(bySeverity)
      .sort((a, b) => b[1] - a[1])
      .map(([sev, count]) => `${count} ${sev}`)
      .join(", ");
    const statusParts = Object.entries(byStatus)
      .sort((a, b) => b[1] - a[1])
      .map(([status, count]) => `${count} ${status}`)
      .join(", ");

    let summary = `I see ${total} recent incident(s).\nBy severity: ${sevParts}.\nBy status: ${statusParts}.`;
    const examples = incidents.slice(0, 3);
    if (examples.length) {
      summary += "\nExamples:\n" + examples
        .map(
          (i) =>
            `- [${i.severity || "unknown"}/${i.status || "open"}] ${
              i.title || "(no title)"
            }`
        )
        .join("\n");
    }
    appendChatMessage(summary, "bot");
  } else {
    appendChatMessage(
      "I can summarize recent incidents. Try asking: \"what's broken right now?\"",
      "bot"
    );
  }
}

chatSendEl.addEventListener("click", handleChat);
chatInputEl.addEventListener("keydown", (e) => {
  if (e.key === "Enter") {
    e.preventDefault();
    handleChat();
  }
});

fetchIncidents();

