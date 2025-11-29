const TOKEN_KEY = "access_token";
const USERNAME_KEY = "username";

document.addEventListener("DOMContentLoaded", () => {

  function getAccessToken() {
    return localStorage.getItem(TOKEN_KEY) || "";
  }

  function getStoredUsername() {
    return localStorage.getItem(USERNAME_KEY) || "";
  }

  function getAuthHeaders() {
    const token = getAccessToken();
    return token ? { Authorization: `Bearer ${token}` } : {};
  }

  function updateSettingsUsernameLabel() {
    const label = document.getElementById("settings-username-value");
    if (!label) return;
    const name = getStoredUsername();
    if (!getAccessToken() || !name) {
      label.textContent = "Not logged in";
    } else {
      label.textContent = name;
    }
  }

  const mainButtons = document.getElementById("settings-main-buttons");
  const panelUsername = document.getElementById("panel-username");
  const panelPassword = document.getElementById("panel-password");

  const btnChangeUsername = document.getElementById("btn-change-username");
  const btnChangePassword = document.getElementById("btn-change-password");
  const btnLogout = document.getElementById("btn-logout");

  const btnSaveUsername = document.getElementById("btn-save-username");
  const btnBackUsername = document.getElementById("btn-back-username");

  const btnSavePassword = document.getElementById("btn-save-password");
  const btnBackPassword = document.getElementById("btn-back-password");

  const inputNewUsername = document.getElementById("new-username");
  const inputCurrPassword = document.getElementById("current-password");
  const inputNewPassword = document.getElementById("new-password");

  if (!mainButtons) {
    return;
  }

  function showMainButtons() {
    mainButtons.style.display = "flex";
    if (panelUsername) panelUsername.style.display = "none";
    if (panelPassword) panelPassword.style.display = "none";
    if (btnLogout) btnLogout.style.display = "inline-flex";
  }

  function showUsernamePanel() {
    mainButtons.style.display = "none";
    if (panelUsername) panelUsername.style.display = "block";
    if (panelPassword) panelPassword.style.display = "none";
    if (btnLogout) btnLogout.style.display = "none";
    if (inputNewUsername) inputNewUsername.value = "";
  }

  function showPasswordPanel() {
    mainButtons.style.display = "none";
    if (panelUsername) panelUsername.style.display = "none";
    if (panelPassword) panelPassword.style.display = "block";
    if (btnLogout) btnLogout.style.display = "none";
    if (inputCurrPassword) inputCurrPassword.value = "";
    if (inputNewPassword) inputNewPassword.value = "";
  }

  btnChangeUsername?.addEventListener("click", showUsernamePanel);
  btnChangePassword?.addEventListener("click", showPasswordPanel);

  btnBackUsername?.addEventListener("click", showMainButtons);
  btnBackPassword?.addEventListener("click", showMainButtons);

  btnLogout?.addEventListener("click", () => {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USERNAME_KEY);
    window.location.href = "/login";
  });

  btnSaveUsername?.addEventListener("click", async () => {
    const newUsername = (inputNewUsername?.value || "").trim();
    if (!newUsername) {
      alert("Please enter a new username.");
      return;
    }

    try {
      const res = await fetch("/auth/change-username", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...getAuthHeaders(),
        },
        body: JSON.stringify({ new_username: newUsername }),
      });

      if (!res.ok) {
        const txt = await res.text();
        alert("Failed to change username: " + txt);
        return;
      }

      const data = await res.json().catch(() => ({}));
      if (data.access_token) {
        localStorage.setItem(TOKEN_KEY, data.access_token);
      }
      localStorage.setItem(USERNAME_KEY, newUsername);

      alert("Username updated.");
      updateSettingsUsernameLabel();
      showMainButtons();
    } catch (err) {
      console.error(err);
      alert("Error while changing username.");
    }
  });

  btnSavePassword?.addEventListener("click", async () => {
    const curr = inputCurrPassword?.value || "";
    const next = inputNewPassword?.value || "";

    if (!curr || !next) {
      alert("Please enter both current and new password.");
      return;
    }

    try {
      const res = await fetch("/auth/change-password", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...getAuthHeaders(),
        },
        body: JSON.stringify({
          current_password: curr,
          new_password: next,
        }),
      });

      if (!res.ok) {
        const txt = await res.text();
        alert("Failed to change password: " + txt);
        return;
      }

      alert("Password changed. Please log in again.");
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(USERNAME_KEY);
      window.location.href = "/login";
    } catch (err) {
      console.error(err);
      alert("Error while changing password.");
    }
  });

  updateSettingsUsernameLabel();
  showMainButtons();
});
