import { el, setStatus } from "./dom.js";
import { clearSessionUi, handleLogin, handleLogout, handleRegister } from "./auth.js";
import {
  handleImportSubmit,
  handleMemberSubmit,
  handleProjectSubmit,
  initializeWorkspaceUi,
  refreshWorkspace,
  updateProjectFilters,
} from "./workspace.js";

initializeWorkspaceUi();
el("register-form").addEventListener("submit", (event) => handleRegister(event, refreshWorkspace));
el("login-form").addEventListener("submit", (event) => handleLogin(event, refreshWorkspace));
el("project-form").addEventListener("submit", handleProjectSubmit);
el("member-form").addEventListener("submit", handleMemberSubmit);
el("import-form").addEventListener("submit", handleImportSubmit);
el("project-search").addEventListener("input", (event) => {
  updateProjectFilters({ query: event.target.value });
});
el("project-band").addEventListener("change", (event) => {
  updateProjectFilters({ band: event.target.value });
});
el("project-sort").addEventListener("change", (event) => {
  updateProjectFilters({ sort: event.target.value });
});
el("logout-button").addEventListener("click", async () => {
  try {
    await handleLogout();
  } catch (error) {
    clearSessionUi();
    setStatus("login-status", error.message, "error");
  }
});

refreshWorkspace();
