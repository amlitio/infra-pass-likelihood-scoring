import { fetchJson, formToJson } from "./api.js";
import { el, setText } from "./dom.js";
import { state } from "./state.js";
import { clearSessionUi, setAuthenticatedUi } from "./auth.js";

function renderPortfolio(summary) {
  setText("kpi-total", summary.total_projects);
  setText("kpi-average", summary.average_score);
  setText("kpi-priority", summary.high_priority_projects);
}

function renderProjects(projects, onSelect) {
  const container = el("project-list");
  if (!projects.length) {
    container.innerHTML = '<p class="empty-state">No projects yet for this organization.</p>';
    return;
  }
  container.innerHTML = projects.map((project) => `
    <article class="project-row ${project.id === state.selectedProjectId ? "active" : ""}" data-project-id="${project.id}">
      <span class="project-name">${project.project_name}</span>
      <div class="project-meta">
        <span>${project.sector || "Unassigned sector"}</span>
        <span>${project.region || "Unknown region"}</span>
        <span>Score ${project.latest_score}</span>
        <span>${project.latest_interpretation}</span>
      </div>
    </article>
  `).join("");
  for (const row of container.querySelectorAll(".project-row")) {
    row.addEventListener("click", () => onSelect(Number(row.dataset.projectId)));
  }
}

function renderDetail(project, onRescore) {
  const detail = el("project-detail");
  const breakdown = Object.entries(project.latest_breakdown).map(([name, value]) => `
    <div class="breakdown-item">
      <span>${name.replaceAll("_", " ")}</span>
      <strong>${value}</strong>
    </div>
  `).join("");
  const history = project.score_history.map((entry) => `
    <div class="history-row">
      <span>${new Date(entry.created_at).toLocaleString()}</span>
      <strong>${entry.score}</strong>
      <span>${entry.interpretation}</span>
      <span>${entry.triggered_by}</span>
    </div>
  `).join("");
  detail.innerHTML = `
    <div class="detail-head">
      <div>
        <p class="eyebrow">${project.project_id || "Portfolio project"}</p>
        <h3>${project.project_name}</h3>
        <p class="lede">${project.notes || "No notes recorded."}</p>
      </div>
      <div>
        <div class="score-number">${project.latest_score}</div>
        <div>${project.latest_interpretation}</div>
      </div>
    </div>
    <div class="project-meta">
      <span>${project.sponsor_organization || "No sponsor"}</span>
      <span>${project.sector || "No sector"}</span>
      <span>${project.region || "No region"}</span>
    </div>
    <button id="rescore-button" type="button">Record rescore</button>
    <div class="breakdown-grid">${breakdown}</div>
    <div>
      <p class="eyebrow">Score history</p>
      <div class="history-list">${history}</div>
    </div>
  `;
  el("rescore-button").addEventListener("click", onRescore);
}

export async function loadProjectDetail(projectId, refreshWorkspace) {
  state.selectedProjectId = projectId;
  const project = await fetchJson(`/v1/projects/${projectId}`);
  renderDetail(project, async () => {
    await fetchJson(`/v1/projects/${project.id}/rescore`, { method: "POST" });
    await refreshWorkspace(project.id);
  });
  renderProjects(state.projects, (id) => loadProjectDetail(id, refreshWorkspace));
}

export async function refreshWorkspace() {
  try {
    const [me, org, summary, projects] = await Promise.all([
      fetchJson("/v1/auth/me"),
      fetchJson("/v1/organizations/me"),
      fetchJson("/v1/portfolio"),
      fetchJson("/v1/projects"),
    ]);
    state.user = me;
    state.organization = org;
    state.projects = projects;
    setAuthenticatedUi();
    renderPortfolio(summary);
    renderProjects(projects, (id) => loadProjectDetail(id, refreshWorkspace));
    if (state.selectedProjectId) {
      const selected = projects.find((project) => project.id === state.selectedProjectId);
      if (selected) {
        await loadProjectDetail(state.selectedProjectId, refreshWorkspace);
        return;
      }
    }
    if (projects.length) {
      await loadProjectDetail(projects[0].id, refreshWorkspace);
    } else {
      setText("project-detail", "No projects yet for this organization.");
    }
  } catch (error) {
    clearSessionUi();
    setText("login-status", error.message);
  }
}

export async function handleProjectSubmit(event) {
  event.preventDefault();
  const status = el("project-status");
  status.textContent = "Creating project...";
  try {
    const project = await fetchJson("/v1/projects", {
      method: "POST",
      body: JSON.stringify(formToJson(event.target)),
    });
    status.textContent = `Saved ${project.project_name} with score ${project.latest_score}.`;
    event.target.reset();
    state.selectedProjectId = project.id;
    await refreshWorkspace();
  } catch (error) {
    status.textContent = error.message;
  }
}

export async function handleMemberSubmit(event) {
  event.preventDefault();
  const status = el("member-status");
  status.textContent = "Adding member...";
  try {
    const member = await fetchJson("/v1/organizations/me/users", {
      method: "POST",
      body: JSON.stringify(formToJson(event.target)),
    });
    status.textContent = `Added ${member.full_name}.`;
    event.target.reset();
  } catch (error) {
    status.textContent = error.message;
  }
}

export async function handleImportSubmit(event) {
  event.preventDefault();
  const status = el("import-status");
  status.textContent = "Importing portfolio...";
  try {
    const result = await fetchJson("/v1/imports/csv", {
      method: "POST",
      body: JSON.stringify(formToJson(event.target)),
    });
    status.textContent = `Imported ${result.created_projects} projects from ${result.filename}.`;
    state.selectedProjectId = result.results[0]?.id || null;
    await refreshWorkspace();
  } catch (error) {
    status.textContent = error.message;
  }
}
