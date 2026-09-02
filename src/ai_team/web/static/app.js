const $ = (sel) => document.querySelector(sel);

async function api(path, options = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ? JSON.stringify(body.detail) : JSON.stringify(body);
    } catch (_) {}
    throw new Error(`${res.status}: ${detail}`);
  }
  if (res.status === 204) return null;
  return res.json();
}

function table(headers, rows, rowHtml) {
  if (!rows.length) return '<p class="muted">Không có dữ liệu.</p>';
  const head = headers.map((h) => `<th>${h}</th>`).join("");
  const body = rows.map(rowHtml).join("");
  return `<table><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table>`;
}

function fmtCost(v) {
  return `$${Number(v || 0).toFixed(6)}`;
}

function setTab(name) {
  document.querySelectorAll(".tab").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.tab === name);
  });
  document.querySelectorAll(".panel").forEach((panel) => {
    panel.classList.toggle("active", panel.id === `panel-${name}`);
  });
}

document.querySelectorAll(".tab").forEach((btn) => {
  btn.addEventListener("click", () => setTab(btn.dataset.tab));
});

async function loadDashboard() {
  const [project, agents, sessions, decisions, dashboard, routing] = await Promise.all([
    api("/projects"),
    api("/agents"),
    api("/sessions"),
    api("/decisions"),
    api("/dashboard"),
    api("/routing/preview?prompt=Add%20authentication"),
  ]);

  $("#project-path").textContent = project.current;
  $("#header-stats").innerHTML = [
    `<span class="pill">Sessions: ${dashboard.sessions}</span>`,
    `<span class="pill">Cost: ${fmtCost(dashboard.cost_usd)}</span>`,
    `<span class="pill">Pending approvals: ${dashboard.pending_approvals}</span>`,
  ].join("");

  $("#agents-table").innerHTML = table(
    ["Role", "Provider", "Model"],
    agents,
    (a) => `<tr><td>${a.role}</td><td>${a.provider}</td><td>${a.model}</td></tr>`,
  );

  $("#routing-preview").textContent = JSON.stringify(routing, null, 2);

  $("#sessions-table").innerHTML = table(
    ["ID", "Kind", "Status", "Started"],
    sessions,
    (s) =>
      `<tr><td><a href="#" data-session="${s.id}">${s.id}</a></td><td>${s.kind}</td><td>${s.status}</td><td>${s.started_at || ""}</td></tr>`,
  );

  $("#decisions-list").innerHTML = decisions.length
    ? decisions
        .map(
          (d) =>
            `<div class="item"><strong>${d.decision}</strong><div class="muted">${d.reason || ""}</div></div>`,
        )
        .join("")
    : '<p class="muted">Chưa có decision.</p>';

  $("#cost-summary").innerHTML = [
    metric("Sessions", dashboard.sessions),
    metric("Trace events", dashboard.events),
    metric("Tokens in", dashboard.tokens_in),
    metric("Tokens out", dashboard.tokens_out),
    metric("Total cost", fmtCost(dashboard.cost_usd)),
    metric("Pending approvals", dashboard.pending_approvals),
  ].join("");
}

function metric(label, value) {
  return `<div class="metric"><div class="label">${label}</div><div class="value">${value}</div></div>`;
}

async function loadTasks() {
  const tasks = await api("/tasks");
  $("#tasks-table").innerHTML = table(
    ["Key", "Status", "Title", "Actions"],
    tasks,
    (t) =>
      `<tr>
        <td>${t.task_key}</td>
        <td>${t.status}</td>
        <td>${t.title}</td>
        <td>
          <button class="secondary" data-run="plan" data-key="${t.task_key}">Plan</button>
          <button class="secondary" data-run="implement" data-key="${t.task_key}">Implement</button>
        </td>
      </tr>`,
  );
}

async function loadApprovals() {
  const rows = await api("/approvals?status=pending");
  $("#approvals-table").innerHTML = table(
    ["ID", "Action", "Risk", "By", "Actions"],
    rows,
    (a) =>
      `<tr>
        <td>${a.id}</td>
        <td class="mono">${a.action}</td>
        <td>${a.risk_level}</td>
        <td>${a.requested_by || ""}</td>
        <td>
          <button data-approve="${a.id}" data-approved="true">Approve</button>
          <button class="danger" data-approve="${a.id}" data-approved="false">Deny</button>
        </td>
      </tr>`,
  );
}

async function loadSessionCosts() {
  const sessions = await api("/sessions");
  const costs = await Promise.all(
    sessions.slice(0, 20).map(async (s) => {
      try {
        const cost = await api(`/sessions/${s.id}/cost`);
        return { ...s, ...cost };
      } catch {
        return { ...s, cost_usd: 0, tokens_in: 0, tokens_out: 0 };
      }
    }),
  );
  $("#session-costs").innerHTML = table(
    ["ID", "Kind", "Status", "Tokens", "Cost"],
    costs,
    (s) =>
      `<tr><td>${s.id}</td><td>${s.kind}</td><td>${s.status}</td><td>${s.tokens_in}+${s.tokens_out}</td><td>${fmtCost(s.cost_usd)}</td></tr>`,
  );
}

function appendChat(role, body) {
  const el = document.createElement("div");
  el.className = `msg ${role}`;
  el.innerHTML = `<div class="role">${role}</div><div class="body"></div>`;
  el.querySelector(".body").textContent = body;
  $("#chat-log").appendChild(el);
  $("#chat-log").scrollTop = $("#chat-log").scrollHeight;
}

async function streamSession(sessionId, onEvent) {
  const source = new EventSource(`/sessions/${sessionId}/events`);
  return new Promise((resolve, reject) => {
    source.onmessage = (ev) => {
      const data = JSON.parse(ev.data);
      onEvent(data);
      if (data.type === "done") {
        source.close();
        resolve(data);
      }
    };
    source.onerror = () => {
      source.close();
      reject(new Error("SSE stream closed"));
    };
  });
}

$("#task-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const title = $("#task-title").value.trim();
  const description = $("#task-desc").value.trim();
  if (!title) return;
  await api("/tasks", { method: "POST", body: JSON.stringify({ title, description }) });
  $("#task-title").value = "";
  $("#task-desc").value = "";
  await loadTasks();
});

$("#tasks-table").addEventListener("click", async (e) => {
  const btn = e.target.closest("button[data-run]");
  if (!btn) return;
  const taskKey = btn.dataset.key;
  const command = btn.dataset.run;
  const yes = true;
  appendChat("system", `Running ${command} on ${taskKey}…`);
  try {
    const result = await api(`/tasks/${taskKey}/run`, {
      method: "POST",
      body: JSON.stringify({ command, prompt: taskKey, yes }),
    });
    appendChat("assistant", result.summary || JSON.stringify(result, null, 2));
    await loadDashboard();
    await loadTasks();
  } catch (err) {
    appendChat("system", String(err));
  }
});

$("#chat-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const message = $("#chat-input").value.trim();
  if (!message) return;
  const mode = $("#chat-mode").value;
  const yes = $("#chat-yes").checked;
  appendChat("user", message);
  $("#chat-input").value = "";
  $("#chat-stream").textContent = "";
  try {
    const started = await api("/chat", {
      method: "POST",
      body: JSON.stringify({ mode, message, yes }),
    });
    await streamSession(started.session_id, (ev) => {
      $("#chat-stream").textContent += `${ev.type}: ${ev.summary || ""}\n`;
      if (ev.type === "result") {
        appendChat("assistant", ev.summary || JSON.stringify(ev.payload, null, 2));
      }
    });
    await loadDashboard();
  } catch (err) {
    appendChat("system", String(err));
  }
});

$("#approvals-table").addEventListener("click", async (e) => {
  const btn = e.target.closest("button[data-approve]");
  if (!btn) return;
  const id = btn.dataset.approve;
  const approved = btn.dataset.approved === "true";
  await api(`/approvals/${id}`, {
    method: "POST",
    body: JSON.stringify({ approved, reason: approved ? "approved via UI" : "denied via UI" }),
  });
  await loadApprovals();
  await loadDashboard();
});

$("#refresh-approvals").addEventListener("click", loadApprovals);

document.querySelector('[data-tab="cost"]').addEventListener("click", loadSessionCosts);

async function boot() {
  await loadDashboard();
  await loadTasks();
  await loadApprovals();
}

boot().catch((err) => {
  $("#project-path").textContent = `Lỗi: ${err.message}`;
});
