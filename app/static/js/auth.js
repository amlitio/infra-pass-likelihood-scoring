import { fetchJson, formToJson } from "./api.js";
import { el, setStatus, setText } from "./dom.js";
import { state } from "./state.js";

export function setAuthenticatedUi() {
  setText("session-user", `${state.user.full_name} | ${state.user.role}`);
  setText("kpi-org", state.organization.name);
  el("auth-grid").classList.add("hidden");
  el("workspace-grid").classList.remove("hidden");
  el("lower-grid").classList.remove("hidden");
}

export function clearSessionUi() {
  state.user = null;
  state.organization = null;
  state.projects = [];
  state.selectedProjectId = null;
  setText("session-user", "Not signed in");
  setText("kpi-org", "None");
  el("auth-grid").classList.remove("hidden");
  el("workspace-grid").classList.add("hidden");
  el("lower-grid").classList.add("hidden");
  el("project-list").innerHTML = "";
  setText("project-detail", "Sign in to inspect project history.");
}

export async function handleRegister(event, onAuthenticated) {
  event.preventDefault();
  const status = el("register-status");
  setStatus("register-status", "Creating organization...");
  try {
    const authPayload = await fetchJson("/v1/auth/register", {
      method: "POST",
      body: JSON.stringify(formToJson(event.target)),
    });
    state.user = authPayload.user;
    state.organization = authPayload.organization;
    setAuthenticatedUi();
    setStatus("register-status", `Registered ${authPayload.organization.name}.`);
    event.target.reset();
    await onAuthenticated();
  } catch (error) {
    setStatus("register-status", error.message, "error");
  }
}

export async function handleLogin(event, onAuthenticated) {
  event.preventDefault();
  const status = el("login-status");
  setStatus("login-status", "Signing in...");
  try {
    const authPayload = await fetchJson("/v1/auth/login", {
      method: "POST",
      body: JSON.stringify(formToJson(event.target)),
    });
    state.user = authPayload.user;
    state.organization = authPayload.organization;
    setAuthenticatedUi();
    setStatus("login-status", `Signed in to ${authPayload.organization.name}.`);
    event.target.reset();
    await onAuthenticated();
  } catch (error) {
    setStatus("login-status", error.message, "error");
  }
}

export async function handleLogout() {
  await fetchJson("/v1/auth/logout", { method: "POST" });
  clearSessionUi();
  setText("login-status", "Signed out.");
}
