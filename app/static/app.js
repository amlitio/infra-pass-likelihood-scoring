const state = {
  selectedProjectId: null,
  projects: [],
};

function formToJson(form) {
  const data = new FormData(form);
  const json = Object.fromEntries(data.entries());
  const numericFields = [
    "procedural_stage",
    "sponsor_strength",
    "funding_clarity",
    "route_specificity",
    "need_case",
    "row_tractability",
    "local_plan_alignment",
    "opposition_drag",
    "land_monetization_fit",
  ];
  for (const field of numericFields) {
    if (json[field] !== undefined) {
      json[field] = Number(json[field]);
    }
  }
  return json;
}

async function fetchJson(url, options) {
  const response = await fetch(url, options);
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.detail || "Request failed");
  }
  return payload;
}

function renderPortfolio(summary) {
  document.getElementById("kpi-total").textContent = summary.total_projects;
  document.getElementById("kpi-average").textContent = summary.average_score;
  document.getElementById("kpi-priority").textContent = summary.high_priority_projects;
  document.getElementById("kpi-recent").textContent = summary.recent_scores;
}

function renderProjects(projects) {
  const container = document.getElementById("project-list");
  if (!projects.length) {
    container.innerHTML = '<p class="empty-state">No projects yet. Create one or import a CSV to populate the portfolio.</p>';
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
    row.addEventListener("click", () => loadProjectDetail(Number(row.dataset.projectId)));
  }
}

function renderDetail(project) {
  const detail = document.getElementById("project-detail");
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

  document.getElementById("rescore-button").addEventListener("click", async () => {
    await fetchJson(`/v1/projects/${project.id}/rescore`, { method: "POST" });
    await refreshWorkspace(project.id);
  });
}

async function loadProjectDetail(projectId) {
  state.selectedProjectId = projectId;
  const project = await fetchJson(`/v1/projects/${projectId}`);
  renderDetail(project);
  renderProjects(state.projects);
}

async function refreshWorkspace(selectedProjectId = state.selectedProjectId) {
  const [summary, projects] = await Promise.all([
    fetchJson("/v1/portfolio"),
    fetchJson("/v1/projects"),
  ]);
  state.projects = projects;
  renderPortfolio(summary);
  renderProjects(projects);
  if (selectedProjectId) {
    const selected = projects.find((project) => project.id === selectedProjectId);
    if (selected) {
      await loadProjectDetail(selectedProjectId);
      return;
    }
  }
  if (projects.length) {
    await loadProjectDetail(projects[0].id);
  }
}

async function handleProjectSubmit(event) {
  event.preventDefault();
  const status = document.getElementById("project-status");
  status.textContent = "Creating project...";
  try {
    const payload = formToJson(event.target);
    const project = await fetchJson("/v1/projects", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    event.target.reset();
    status.textContent = `Saved ${project.project_name} with score ${project.latest_score}.`;
    await refreshWorkspace(project.id);
  } catch (error) {
    status.textContent = error.message;
  }
}

async function handleImportSubmit(event) {
  event.preventDefault();
  const status = document.getElementById("import-status");
  status.textContent = "Importing portfolio...";
  try {
    const payload = formToJson(event.target);
    const result = await fetchJson("/v1/imports/csv", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    status.textContent = `Imported ${result.created_projects} projects from ${result.filename}.`;
    await refreshWorkspace(result.results[0]?.id || null);
  } catch (error) {
    status.textContent = error.message;
  }
}

document.getElementById("project-form").addEventListener("submit", handleProjectSubmit);
document.getElementById("import-form").addEventListener("submit", handleImportSubmit);
refreshWorkspace();
