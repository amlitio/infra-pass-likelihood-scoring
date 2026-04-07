const state = {
  token: localStorage.getItem("iplp_token"),
  selectedProjectId: null,
  projects: [],
  user: null,
  organization: null,
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
    if (json[field] !== undefined && json[field] !== "") {
      json[field] = Number(json[field]);
    }
  }
  return json;
}

async function fetchJson(url, options = {}) {
  const headers = new Headers(options.headers || {});
  if (state.token) {
    headers.set("Authorization", `Bearer ${state.token}`);
  }
  if (!headers.has("Content-Type") && options.body) {
    headers.set("Content-Type", "application/json");
  }
  const response = await fetch(url, { ...options, headers });
  const raw = await response.text();
  let payload;
  try {
    payload = raw ? JSON.parse(raw) : {};
  } catch {
    payload = { detail: raw || "Request failed" };
  }
  if (!response.ok) {
    throw new Error(payload.detail || "Request failed");
  }
  return payload;
}

function persistSession(authPayload) {
  state.token = authPayload.access_token;
  state.user = authPayload.user;
  state.organization = authPayload.organization;
  localStorage.setItem("iplp_token", state.token);
  document.getElementById("session-user").textContent = `${state.user.full_name} | ${state.user.role}`;
  document.getElementById("kpi-org").textContent = state.organization.name;
  document.getElementById("workspace-grid").classList.remove("hidden");
  document.getElementById("lower-grid").classList.remove("hidden");
}

function clearSession() {
  state.token = null;
  state.user = null;
  state.organization = null;
  state.projects = [];
  state.selectedProjectId = null;
  localStorage.removeItem("iplp_token");
  document.getElementById("session-user").textContent = "Not signed in";
  document.getElementById("kpi-org").textContent = "None";
  document.getElementById("workspace-grid").classList.add("hidden");
  document.getElementById("lower-grid").classList.add("hidden");
  document.getElementById("project-list").innerHTML = "";
  document.getElementById("project-detail").textContent = "Sign in to inspect project history.";
}

function renderPortfolio(summary) {
  document.getElementById("kpi-total").textContent = summary.total_projects;
  document.getElementById("kpi-average").textContent = summary.average_score;
  document.getElementById("kpi-priority").textContent = summary.high_priority_projects;
}

function renderProjects(projects) {
  const container = document.getElementById("project-list");
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
  if (!state.token) {
    clearSession();
    return;
  }
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
    document.getElementById("session-user").textContent = `${me.full_name} | ${me.role}`;
    document.getElementById("kpi-org").textContent = org.name;
    document.getElementById("workspace-grid").classList.remove("hidden");
    document.getElementById("lower-grid").classList.remove("hidden");
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
    } else {
      document.getElementById("project-detail").textContent = "No projects yet for this organization.";
    }
  } catch (error) {
    clearSession();
    document.getElementById("login-status").textContent = error.message;
  }
}

async function handleRegister(event) {
  event.preventDefault();
  const status = document.getElementById("register-status");
  status.textContent = "Creating organization...";
  try {
    const authPayload = await fetchJson("/v1/auth/register", {
      method: "POST",
      body: JSON.stringify(formToJson(event.target)),
    });
    persistSession(authPayload);
    status.textContent = `Registered ${authPayload.organization.name}.`;
    event.target.reset();
    await refreshWorkspace();
  } catch (error) {
    status.textContent = error.message;
  }
}

async function handleLogin(event) {
  event.preventDefault();
  const status = document.getElementById("login-status");
  status.textContent = "Signing in...";
  try {
    const authPayload = await fetchJson("/v1/auth/login", {
      method: "POST",
      body: JSON.stringify(formToJson(event.target)),
    });
    persistSession(authPayload);
    status.textContent = `Signed in to ${authPayload.organization.name}.`;
    event.target.reset();
    await refreshWorkspace();
  } catch (error) {
    status.textContent = error.message;
  }
}

async function handleProjectSubmit(event) {
  event.preventDefault();
  const status = document.getElementById("project-status");
  status.textContent = "Creating project...";
  try {
    const project = await fetchJson("/v1/projects", {
      method: "POST",
      body: JSON.stringify(formToJson(event.target)),
    });
    status.textContent = `Saved ${project.project_name} with score ${project.latest_score}.`;
    event.target.reset();
    await refreshWorkspace(project.id);
  } catch (error) {
    status.textContent = error.message;
  }
}

async function handleMemberSubmit(event) {
  event.preventDefault();
  const status = document.getElementById("member-status");
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

async function handleImportSubmit(event) {
  event.preventDefault();
  const status = document.getElementById("import-status");
  status.textContent = "Importing portfolio...";
  try {
    const result = await fetchJson("/v1/imports/csv", {
      method: "POST",
      body: JSON.stringify(formToJson(event.target)),
    });
    status.textContent = `Imported ${result.created_projects} projects from ${result.filename}.`;
    await refreshWorkspace(result.results[0]?.id || null);
  } catch (error) {
    status.textContent = error.message;
  }
}

document.getElementById("register-form").addEventListener("submit", handleRegister);
document.getElementById("login-form").addEventListener("submit", handleLogin);
document.getElementById("project-form").addEventListener("submit", handleProjectSubmit);
document.getElementById("member-form").addEventListener("submit", handleMemberSubmit);
document.getElementById("import-form").addEventListener("submit", handleImportSubmit);
document.getElementById("logout-button").addEventListener("click", () => {
  clearSession();
  document.getElementById("login-status").textContent = "Signed out.";
});

refreshWorkspace();
