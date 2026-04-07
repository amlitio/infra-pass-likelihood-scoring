import { fetchJson, formToJson } from "./api.js";
import { el, setStatus, setText } from "./dom.js";
import { state } from "./state.js";
import { clearSessionUi, setAuthenticatedUi } from "./auth.js";

const STEP_COUNT = 3;
let currentStep = 0;
let editingProjectId = null;

const SIGNAL_MODEL = [
  {
    key: "procedural_stage",
    label: "Procedural stage",
    max: 25,
    recommendation: "Advance formal approvals and milestone visibility so the program is easier to underwrite.",
  },
  {
    key: "sponsor_strength",
    label: "Sponsor strength",
    max: 10,
    recommendation: "Tighten sponsor evidence, track record, and delivery capacity before the next score run.",
  },
  {
    key: "funding_clarity",
    label: "Funding clarity",
    max: 15,
    recommendation: "Document the capital stack, delivery pathway, and committed funding sources.",
  },
  {
    key: "route_specificity",
    label: "Route specificity",
    max: 10,
    recommendation: "Narrow the route footprint and convert route assumptions into mapped evidence.",
  },
  {
    key: "need_case",
    label: "Need case",
    max: 10,
    recommendation: "Strengthen the demand story with quantified system need and timing pressure.",
  },
  {
    key: "row_tractability",
    label: "ROW tractability",
    max: 10,
    recommendation: "Reduce land-path uncertainty by clarifying access strategy and right-of-way constraints.",
  },
  {
    key: "local_plan_alignment",
    label: "Local plan alignment",
    max: 8,
    recommendation: "Tie the project more directly to local plans, agency priorities, and formal policy language.",
  },
  {
    key: "opposition_drag",
    label: "Opposition drag",
    max: 7,
    inverse: true,
    recommendation: "Map likely opposition, stakeholder objections, and mitigation sequencing before diligence advances.",
  },
  {
    key: "land_monetization_fit",
    label: "Land monetization fit",
    max: 19,
    recommendation: "Clarify how land control and monetization increase project momentum or optionality.",
  },
];

const PROJECT_FIELD_LABELS = [
  { key: "sponsor_organization", label: "Sponsor" },
  { key: "sector", label: "Sector" },
  { key: "region", label: "Region" },
];

function clampScore(score) {
  return Math.max(0, Math.min(100, Number(score) || 0));
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function scoreBand(score) {
  if (score >= 85) return "Very high probability";
  if (score >= 70) return "Strong watchlist";
  if (score >= 55) return "Targeted hunting";
  return "Informational";
}

function scoreBandKey(score) {
  if (score >= 85) return "very-high";
  if (score >= 70) return "watchlist";
  if (score >= 55) return "targeted";
  return "informational";
}

function formatDate(value) {
  return value ? new Date(value).toLocaleString() : "Unknown";
}

function relativeTime(value) {
  if (!value) return "Unknown";
  const now = Date.now();
  const deltaMinutes = Math.round((now - new Date(value).getTime()) / 60000);
  if (deltaMinutes <= 1) return "just now";
  if (deltaMinutes < 60) return `${deltaMinutes}m ago`;
  const deltaHours = Math.round(deltaMinutes / 60);
  if (deltaHours < 24) return `${deltaHours}h ago`;
  const deltaDays = Math.round(deltaHours / 24);
  return `${deltaDays}d ago`;
}

function computedPreview(form) {
  const payload = formToJson(form);
  const parts = [
    payload.procedural_stage || 0,
    payload.sponsor_strength || 0,
    payload.funding_clarity || 0,
    payload.route_specificity || 0,
    payload.need_case || 0,
    payload.row_tractability || 0,
    payload.local_plan_alignment || 0,
    payload.land_monetization_fit || 0,
    -(payload.opposition_drag || 0),
  ];
  return clampScore(parts.reduce((sum, value) => sum + value, 0));
}

function projectToPayload(project) {
  return {
    project_id: project.project_id || "",
    project_name: project.project_name || "",
    sponsor_organization: project.sponsor_organization || "",
    sector: project.sector || "",
    region: project.region || "",
    notes: project.notes || "",
    procedural_stage: project.procedural_stage,
    sponsor_strength: project.sponsor_strength,
    funding_clarity: project.funding_clarity,
    route_specificity: project.route_specificity,
    need_case: project.need_case,
    row_tractability: project.row_tractability,
    local_plan_alignment: project.local_plan_alignment,
    opposition_drag: project.opposition_drag,
    land_monetization_fit: project.land_monetization_fit,
  };
}

function describeFilterState(total, visible) {
  const parts = [`Showing ${visible} of ${total} projects`];
  if (state.filters.query) parts.push(`search "${state.filters.query}"`);
  if (state.filters.band !== "all") parts.push(state.filters.band.replace("-", " "));
  return parts.join(" | ");
}

function normalizeSignal(project, signal) {
  const raw = Number(project[signal.key]) || 0;
  const baseline = Math.max(1, signal.max);
  const ratio = signal.inverse ? 1 - raw / baseline : raw / baseline;
  return Math.max(0, Math.min(1, ratio));
}

function deriveInsights(project) {
  const scoredSignals = SIGNAL_MODEL.map((signal) => ({
    ...signal,
    raw: Number(project[signal.key]) || 0,
    normalized: normalizeSignal(project, signal),
  }));
  const strengths = [...scoredSignals].sort((left, right) => right.normalized - left.normalized).slice(0, 3);
  const risks = [...scoredSignals].sort((left, right) => left.normalized - right.normalized).slice(0, 3);
  const recommendations = risks.map((signal, index) => ({
    label: `${index + 1}. ${signal.label}`,
    body: signal.recommendation,
  }));

  const history = [...project.score_history].sort(
    (left, right) => new Date(left.created_at).getTime() - new Date(right.created_at).getTime()
  );
  const baseline = history[0]?.score ?? project.latest_score;
  const latest = history[history.length - 1]?.score ?? project.latest_score;
  const delta = latest - baseline;
  const momentum =
    history.length < 2
      ? "First recorded run in this workspace."
      : delta > 0
        ? `Momentum is improving, up ${delta} points since the first recorded run.`
        : delta < 0
          ? `Momentum has softened by ${Math.abs(delta)} points since the first recorded run.`
          : "Momentum is flat across the recorded history.";

  return { strengths, risks, recommendations, momentum, delta, runCount: history.length };
}

function matchesBand(project, band) {
  return band === "all" || scoreBandKey(project.latest_score) === band;
}

function sortProjects(projects, mode) {
  const sorted = [...projects];
  sorted.sort((left, right) => {
    switch (mode) {
      case "score-asc":
        return left.latest_score - right.latest_score;
      case "updated-desc":
        return new Date(right.updated_at).getTime() - new Date(left.updated_at).getTime();
      case "name-asc":
        return left.project_name.localeCompare(right.project_name);
      case "score-desc":
      default:
        return right.latest_score - left.latest_score;
    }
  });
  return sorted;
}

function getVisibleProjects() {
  const query = state.filters.query.trim().toLowerCase();
  const filtered = state.projects.filter((project) => {
    if (!matchesBand(project, state.filters.band)) {
      return false;
    }
    if (!query) {
      return true;
    }
    const haystack = [
      project.project_name,
      project.project_id,
      project.sponsor_organization,
      project.sector,
      project.region,
      project.notes,
    ]
      .filter(Boolean)
      .join(" ")
      .toLowerCase();
    return haystack.includes(query);
  });
  return sortProjects(filtered, state.filters.sort);
}

function setStep(step) {
  currentStep = Math.max(0, Math.min(STEP_COUNT - 1, step));
  document.querySelectorAll(".step-tab").forEach((tab) => {
    tab.classList.toggle("active", Number(tab.dataset.step) === currentStep);
  });
  document.querySelectorAll(".step-panel").forEach((panel) => {
    panel.classList.toggle("active", Number(panel.dataset.stepPanel) === currentStep);
  });
  el("step-back").classList.toggle("hidden", currentStep === 0);
  el("step-next").classList.toggle("hidden", currentStep === STEP_COUNT - 1);
  el("step-submit").classList.toggle("hidden", currentStep !== STEP_COUNT - 1);
}

function refreshIntakeReview() {
  const form = el("project-form");
  if (!form) return;
  const payload = formToJson(form);
  const preview = computedPreview(form);
  const rows = [
    ["Project", payload.project_name || "Untitled candidate"],
    ["Region", payload.region || "Unknown region"],
    ["Sector", payload.sector || "Unassigned"],
    ["Sponsor", payload.sponsor_organization || "No sponsor added"],
    ["Estimated score", `${preview} | ${scoreBand(preview)}`],
  ];
  el("intake-review").innerHTML = rows
    .map(([label, value]) => `<div class="review-row"><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong></div>`)
    .join("");
}

function buildDistribution(projects) {
  const buckets = [
    { label: "0-54", count: 0 },
    { label: "55-69", count: 0 },
    { label: "70-84", count: 0 },
    { label: "85-100", count: 0 },
  ];
  projects.forEach((project) => {
    const score = project.latest_score;
    if (score >= 85) buckets[3].count += 1;
    else if (score >= 70) buckets[2].count += 1;
    else if (score >= 55) buckets[1].count += 1;
    else buckets[0].count += 1;
  });
  const max = Math.max(1, ...buckets.map((item) => item.count));
  return `
    <div class="chart-grid">
      ${buckets
        .map(
          (bucket) => `
            <div class="chart-card">
              <div class="chart-bar-shell">
                <div class="chart-bar" style="height:${(bucket.count / max) * 100}%"></div>
              </div>
              <div class="chart-value">${bucket.count}</div>
              <div class="chart-axis">${bucket.label}</div>
            </div>
          `
        )
        .join("")}
    </div>
  `;
}

function buildTrend(projects) {
  const series = projects
    .slice(0, 8)
    .map((project) => ({
      name: project.project_name,
      value: project.latest_score,
    }))
    .reverse();
  if (!series.length) {
    return `<div class="empty-state compact">No recent project activity yet.</div>`;
  }
  const max = Math.max(...series.map((item) => item.value), 100);
  const min = Math.min(...series.map((item) => item.value), 0);
  const range = Math.max(1, max - min);
  const points = series
    .map((item, index) => {
      const x = series.length === 1 ? 50 : (index / (series.length - 1)) * 100;
      const y = 100 - (((item.value - min) / range) * 80 + 10);
      return `${x},${y}`;
    })
    .join(" ");
  const latest = series[series.length - 1];
  return `
    <div class="trend-canvas">
      <svg class="trend-svg" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
        <polyline fill="none" stroke="rgba(104,168,255,0.18)" stroke-width="12" points="${points}" />
        <polyline fill="none" stroke="url(#trend-gradient)" stroke-width="3" points="${points}" />
        <defs>
          <linearGradient id="trend-gradient" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stop-color="#68a8ff" />
            <stop offset="100%" stop-color="#59f0d2" />
          </linearGradient>
        </defs>
      </svg>
      <div class="trend-row">
        <div>
          <div class="trend-label">Latest project</div>
          <strong>${escapeHtml(latest.name)}</strong>
        </div>
        <div>
          <div class="trend-label">Current score</div>
          <strong>${latest.value}</strong>
        </div>
      </div>
    </div>
  `;
}

function buildTrendSvg(values, gradientId) {
  const series = values.length ? values : [0];
  const max = Math.max(...series, 100);
  const min = Math.min(...series, 0);
  const range = Math.max(1, max - min);
  const points = series
    .map((value, index) => {
      const x = series.length === 1 ? 50 : (index / (series.length - 1)) * 100;
      const y = 100 - (((value - min) / range) * 80 + 10);
      return `${x},${y}`;
    })
    .join(" ");
  return `
    <svg class="trend-svg" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
      <polyline fill="none" stroke="rgba(104,168,255,0.18)" stroke-width="12" points="${points}" />
      <polyline fill="none" stroke="url(#${gradientId})" stroke-width="3" points="${points}" />
      <defs>
        <linearGradient id="${gradientId}" x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" stop-color="#68a8ff" />
          <stop offset="100%" stop-color="#59f0d2" />
        </linearGradient>
      </defs>
    </svg>
  `;
}

function renderPortfolio(summary, projects) {
  setText("kpi-total", summary.total_projects);
  setText("kpi-average", summary.average_score);
  setText("kpi-priority", summary.high_priority_projects);
  el("score-distribution").innerHTML = buildDistribution(projects);
  el("score-trend").innerHTML = buildTrend(projects);
}

function renderMemberList() {
  const container = el("member-list");
  if (!state.members.length) {
    container.innerHTML = '<p class="empty-mini">No teammates added yet.</p>';
    return;
  }
  container.innerHTML = state.members
    .map(
      (member) => `
        <article class="team-card">
          <div class="team-card-head">
            <strong>${escapeHtml(member.full_name)}</strong>
            <span class="team-role">${escapeHtml(member.role)}</span>
          </div>
          <div class="team-meta">
            <span>${escapeHtml(member.email)}</span>
            <span>Joined ${relativeTime(member.created_at)}</span>
          </div>
        </article>
      `
    )
    .join("");
}

async function handleSessionRevoke(sessionId) {
  setStatus("session-status", "Revoking session...");
  try {
    await fetchJson("/v1/auth/sessions/revoke", {
      method: "POST",
      body: JSON.stringify({ session_id: Number(sessionId) }),
    });
    setStatus("session-status", "Session revoked.");
    await refreshWorkspace();
  } catch (error) {
    setStatus("session-status", error.message, "error");
  }
}

function renderSessionList() {
  const container = el("session-list");
  if (!state.sessions.length) {
    container.innerHTML = '<p class="empty-mini">No active sessions recorded.</p>';
    return;
  }
  container.innerHTML = state.sessions
    .map(
      (session) => `
        <article class="team-card ${session.current ? "current-session" : ""}">
          <div class="team-card-head">
            <strong>${session.current ? "Current session" : "Managed session"}</strong>
            <div class="team-actions">
              <span class="team-role">${relativeTime(session.last_seen_at)}</span>
              ${
                session.current
                  ? ""
                  : `<button type="button" class="ghost-button session-revoke-button" data-session-id="${session.id}">Revoke</button>`
              }
            </div>
          </div>
          <div class="team-meta">
            <span>${escapeHtml(session.user_agent || "Browser session")}</span>
            <span>Expires ${formatDate(session.expires_at)}</span>
          </div>
        </article>
      `
    )
    .join("");
  container.querySelectorAll(".session-revoke-button").forEach((button) => {
    button.addEventListener("click", () => handleSessionRevoke(button.dataset.sessionId));
  });
}

function renderOperationalPanels() {
  renderMemberList();
  renderSessionList();
  const isAdmin = state.user?.role === "admin";
  el("member-form").classList.toggle("hidden", !isAdmin);
}

function renderProjects(projects, onSelect) {
  const container = el("project-list");
  const visible = getVisibleProjects();
  setText("project-list-meta", describeFilterState(projects.length, visible.length));
  if (!visible.length) {
    container.innerHTML =
      projects.length > 0
        ? '<p class="empty-state compact">No projects match the current filters.</p>'
        : '<p class="empty-state compact">No projects yet for this organization.</p>';
    return;
  }
  container.innerHTML = visible
    .map((project) => {
      const band = scoreBandKey(project.latest_score);
      return `
        <article class="project-row ${project.id === state.selectedProjectId ? "active" : ""}" data-project-id="${project.id}">
          <div class="project-row-head">
            <span class="project-name">${escapeHtml(project.project_name)}</span>
            <span class="score-pill ${band}">${project.latest_score}</span>
          </div>
          <div class="project-submeta">
            <span>${escapeHtml(project.sponsor_organization || "No sponsor set")}</span>
            <span>Updated ${relativeTime(project.updated_at)}</span>
          </div>
          <div class="project-meta">
            <span>${escapeHtml(project.sector || "Unassigned sector")}</span>
            <span>${escapeHtml(project.region || "Unknown region")}</span>
            <span class="score-chip">${escapeHtml(scoreBand(project.latest_score))}</span>
            <span>${escapeHtml(project.project_id || "No external ID")}</span>
          </div>
        </article>
      `;
    })
    .join("");
  container.querySelectorAll(".project-row").forEach((row) => {
    row.addEventListener("click", () => onSelect(Number(row.dataset.projectId)));
  });
}

function profileGrid(project) {
  return PROJECT_FIELD_LABELS.map(
    (item) => `
      <div class="profile-row">
        <span>${item.label}</span>
        <strong>${escapeHtml(project[item.key] || `No ${item.label.toLowerCase()} set`)}</strong>
      </div>
    `
  ).join("");
}

function projectEditForm(project) {
  const payload = projectToPayload(project);
  return `
    <form id="detail-edit-form" class="detail-form">
      <div class="field-row">
        <label>Project name<input name="project_name" value="${escapeHtml(payload.project_name)}" required></label>
        <label>Project ID<input name="project_id" value="${escapeHtml(payload.project_id)}"></label>
      </div>
      <div class="field-row">
        <label>Sponsor<input name="sponsor_organization" value="${escapeHtml(payload.sponsor_organization)}"></label>
        <label>Sector<input name="sector" value="${escapeHtml(payload.sector)}"></label>
      </div>
      <div class="field-row">
        <label>Region<input name="region" value="${escapeHtml(payload.region)}"></label>
        <label>Notes<textarea name="notes" rows="4">${escapeHtml(payload.notes)}</textarea></label>
      </div>
      <div class="signal-grid">
        ${SIGNAL_MODEL.map(
          (signal) => `
            <label>${signal.label}<input type="number" name="${signal.key}" min="0" max="${signal.max}" value="${payload[signal.key]}" required></label>
          `
        ).join("")}
      </div>
      <div class="detail-form-actions">
        <button type="submit">Save changes</button>
        <button type="button" id="cancel-edit-button" class="secondary-button">Cancel</button>
      </div>
      <p class="status" id="detail-status"></p>
    </form>
  `;
}

function detailActionCards(project, insights) {
  const strengths = insights.strengths
    .map((signal) => `<span class="chip positive">${escapeHtml(signal.label)} ${signal.raw}/${signal.max}</span>`)
    .join("");
  const risks = insights.risks
    .map((signal) => `<span class="chip risk">${escapeHtml(signal.label)} ${signal.raw}/${signal.max}</span>`)
    .join("");
  const actions = insights.recommendations
    .map(
      (item) => `
        <div class="action-row">
          <strong>${escapeHtml(item.label)}</strong>
          <p>${escapeHtml(item.body)}</p>
        </div>
      `
    )
    .join("");

  return `
    <div class="insight-card">
      <p class="eyebrow">Analyst brief</p>
      <p class="lede">The current score sits in the <strong>${escapeHtml(
        scoreBand(project.latest_score).toLowerCase()
      )}</strong> band. The fastest way to move this project is to preserve leading signals while tightening the weakest diligence inputs.</p>
    </div>
    <div class="insight-card">
      <p class="eyebrow">Leading signals</p>
      <div class="chip-list">${strengths}</div>
    </div>
    <div class="insight-card">
      <p class="eyebrow">Primary risks</p>
      <div class="chip-list">${risks}</div>
    </div>
    <div class="insight-card">
      <p class="eyebrow">Recommended next actions</p>
      <div class="action-list">${actions}</div>
    </div>
  `;
}

function renderDetail(project) {
  const detail = el("project-detail");
  const editing = editingProjectId === project.id;
  const historyValues = project.score_history.map((entry) => entry.score).reverse();
  const breakdown = Object.entries(project.latest_breakdown)
    .map(
      ([name, value]) => `
        <div class="breakdown-item">
          <span>${escapeHtml(name.replaceAll("_", " "))}</span>
          <strong>${value}</strong>
        </div>
      `
    )
    .join("");
  const history = project.score_history
    .map(
      (entry) => `
        <div class="history-row">
          <div class="history-title">
            <strong>${entry.score}</strong>
            <span>${formatDate(entry.created_at)}</span>
          </div>
          <span>${escapeHtml(entry.interpretation)}</span>
          <span>${escapeHtml(entry.triggered_by)}</span>
        </div>
      `
    )
    .join("");
  const insights = deriveInsights(project);
  const scoreDeltaLabel =
    insights.runCount < 2
      ? "New"
      : insights.delta > 0
        ? `+${insights.delta}`
        : `${insights.delta}`;

  detail.innerHTML = `
    <div class="detail-top">
      <div class="detail-head">
        <div>
          <p class="eyebrow">${escapeHtml(project.project_id || "Portfolio project")}</p>
          <h3>${escapeHtml(project.project_name)}</h3>
          <p class="lede">${escapeHtml(
            project.notes || "No notes recorded. Add context in the intake form to sharpen the analyst readout."
          )}</p>
        </div>
      </div>
      <div class="score-copy">
        <div class="score-number">${project.latest_score}</div>
        <div>${escapeHtml(project.latest_interpretation)}</div>
        <div class="score-delta">${escapeHtml(scoreDeltaLabel)} since baseline</div>
      </div>
    </div>

    <div class="project-meta">
      <span>${escapeHtml(project.sponsor_organization || "No sponsor")}</span>
      <span>${escapeHtml(project.sector || "No sector")}</span>
      <span>${escapeHtml(project.region || "No region")}</span>
      <span class="signal-badge">History ${project.score_history.length} runs</span>
    </div>

    <div class="detail-grid">
      <div class="summary-stack">
        <div class="summary-card">
          <div class="card-header">
            <div>
              <p class="eyebrow">Current rationale</p>
              <p class="detail-note">${escapeHtml(insights.momentum)}</p>
            </div>
            <button id="toggle-edit-button" type="button" class="secondary-button">${editing ? "Close editor" : "Edit project"}</button>
          </div>
          <div class="metric-grid">
            <div class="metric-cell">
              <div class="metric-label">Latest score</div>
              <div class="big-metric">${project.latest_score}</div>
            </div>
            <div class="metric-cell">
              <div class="metric-label">Priority band</div>
              <div class="big-metric">${escapeHtml(scoreBand(project.latest_score))}</div>
            </div>
            <div class="metric-cell">
              <div class="metric-label">Last updated</div>
              <div class="big-metric">${escapeHtml(relativeTime(project.updated_at))}</div>
            </div>
          </div>
          <div class="profile-grid">${profileGrid(project)}</div>
          ${editing ? projectEditForm(project) : '<div class="breakdown-grid">' + breakdown + "</div>"}
        </div>

        <div class="summary-card">
          <div class="history-title">
            <div>
              <p class="eyebrow">Score history</p>
              <p class="detail-note">Each recorded run remains auditable from the same project record.</p>
            </div>
            <button id="rescore-button" type="button">Record rescore</button>
          </div>
          <div class="history-chart">
            ${buildTrendSvg(historyValues, "detail-gradient")}
          </div>
          <div class="history-list">${history}</div>
        </div>
      </div>

      <div class="insight-stack">
        ${detailActionCards(project, insights)}
      </div>
    </div>
  `;

  el("toggle-edit-button").addEventListener("click", () => {
    editingProjectId = editing ? null : project.id;
    renderDetail(project);
  });

  el("rescore-button").addEventListener("click", async () => {
    await fetchJson(`/v1/projects/${project.id}/rescore`, { method: "POST" });
    editingProjectId = null;
    await refreshWorkspace(project.id);
    setStatus("project-status", `Recorded a new score run for ${project.project_name}.`);
  });

  if (editing) {
    el("cancel-edit-button").addEventListener("click", () => {
      editingProjectId = null;
      renderDetail(project);
    });
    el("detail-edit-form").addEventListener("submit", async (event) => {
      event.preventDefault();
      setStatus("detail-status", "Saving project...");
      try {
        await fetchJson(`/v1/projects/${project.id}`, {
          method: "PUT",
          body: JSON.stringify(formToJson(event.target)),
        });
        editingProjectId = null;
        await refreshWorkspace(project.id);
        setStatus("project-status", `Saved updates to ${project.project_name}.`);
      } catch (error) {
        setStatus("detail-status", error.message, "error");
      }
    });
  }
}

function rerenderProjectList() {
  renderProjects(state.projects, (id) => loadProjectDetail(id, refreshWorkspace));
}

export function updateProjectFilters(patch) {
  state.filters = { ...state.filters, ...patch };
  const visible = getVisibleProjects();
  if (!visible.length) {
    state.selectedProjectId = null;
    editingProjectId = null;
    rerenderProjectList();
    setText("project-detail", "No projects match the current filters.");
    return;
  }
  if (!visible.some((project) => project.id === state.selectedProjectId)) {
    editingProjectId = null;
    loadProjectDetail(visible[0].id, refreshWorkspace).catch(() => {
      setText("project-detail", "Unable to load the selected project.");
    });
    return;
  }
  rerenderProjectList();
}

export async function loadProjectDetail(projectId) {
  if (state.selectedProjectId !== projectId) {
    editingProjectId = null;
  }
  state.selectedProjectId = projectId;
  const project = await fetchJson(`/v1/projects/${projectId}`);
  renderDetail(project);
  rerenderProjectList();
}

export async function refreshWorkspace(preferredProjectId = state.selectedProjectId) {
  try {
    const [me, org, summary, projects, members, sessions] = await Promise.all([
      fetchJson("/v1/auth/me"),
      fetchJson("/v1/organizations/me"),
      fetchJson("/v1/portfolio"),
      fetchJson("/v1/projects"),
      fetchJson("/v1/organizations/me/users"),
      fetchJson("/v1/auth/sessions"),
    ]);
    state.user = me;
    state.organization = org;
    state.projects = projects;
    state.members = members;
    state.sessions = sessions;
    setAuthenticatedUi();
    renderPortfolio(summary, projects);
    renderOperationalPanels();
    rerenderProjectList();

    const selectedProjectId = preferredProjectId ?? state.selectedProjectId;
    if (selectedProjectId) {
      const selected = projects.find((project) => project.id === selectedProjectId);
      if (selected) {
        await loadProjectDetail(selectedProjectId);
        return;
      }
    }

    const visible = getVisibleProjects();
    if (visible.length) {
      await loadProjectDetail(visible[0].id);
    } else if (projects.length) {
      state.selectedProjectId = projects[0].id;
      await loadProjectDetail(projects[0].id);
    } else {
      editingProjectId = null;
      setText("project-detail", "No projects yet for this organization.");
    }
  } catch (error) {
    editingProjectId = null;
    clearSessionUi();
    setStatus("login-status", error.message, "error");
  }
}

export function initializeWorkspaceUi() {
  setStep(0);
  document.querySelectorAll(".step-tab").forEach((tab) => {
    tab.addEventListener("click", () => setStep(Number(tab.dataset.step)));
  });
  el("step-back").addEventListener("click", () => setStep(currentStep - 1));
  el("step-next").addEventListener("click", () => {
    refreshIntakeReview();
    setStep(currentStep + 1);
  });
  el("project-form").addEventListener("input", refreshIntakeReview);
  refreshIntakeReview();
}

export async function handleProjectSubmit(event) {
  event.preventDefault();
  setStatus("project-status", "Creating project...");
  try {
    const project = await fetchJson("/v1/projects", {
      method: "POST",
      body: JSON.stringify(formToJson(event.target)),
    });
    setStatus("project-status", `Saved ${project.project_name} with score ${project.latest_score}.`);
    event.target.reset();
    refreshIntakeReview();
    setStep(0);
    state.selectedProjectId = project.id;
    editingProjectId = null;
    await refreshWorkspace(project.id);
  } catch (error) {
    setStatus("project-status", error.message, "error");
  }
}

export async function handleMemberSubmit(event) {
  event.preventDefault();
  setStatus("member-status", "Adding member...");
  try {
    const member = await fetchJson("/v1/organizations/me/users", {
      method: "POST",
      body: JSON.stringify(formToJson(event.target)),
    });
    setStatus("member-status", `Added ${member.full_name}.`);
    event.target.reset();
    await refreshWorkspace();
  } catch (error) {
    setStatus("member-status", error.message, "error");
  }
}

export async function handleImportSubmit(event) {
  event.preventDefault();
  setStatus("import-status", "Importing portfolio...");
  try {
    const result = await fetchJson("/v1/imports/csv", {
      method: "POST",
      body: JSON.stringify(formToJson(event.target)),
    });
    setStatus("import-status", `Imported ${result.created_projects} projects from ${result.filename}.`);
    state.selectedProjectId = result.results[0]?.id || null;
    editingProjectId = null;
    await refreshWorkspace(state.selectedProjectId);
  } catch (error) {
    setStatus("import-status", error.message, "error");
  }
}
