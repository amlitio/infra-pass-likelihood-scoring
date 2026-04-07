import { el, setStatus } from "./dom.js";
import { clearSessionUi, handleLogin, handleLogout, handleRegister } from "./auth.js";
import { handleImportSubmit, handleMemberSubmit, handleProjectSubmit, refreshWorkspace } from "./workspace.js";

el("register-form").addEventListener("submit", (event) => handleRegister(event, refreshWorkspace));
el("login-form").addEventListener("submit", (event) => handleLogin(event, refreshWorkspace));
el("project-form").addEventListener("submit", handleProjectSubmit);
el("member-form").addEventListener("submit", handleMemberSubmit);
el("import-form").addEventListener("submit", handleImportSubmit);
el("logout-button").addEventListener("click", async () => {
  try {
    await handleLogout();
  } catch (error) {
    clearSessionUi();
    setStatus("login-status", error.message, "error");
  }
});

refreshWorkspace();
