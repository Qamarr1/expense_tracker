// static/auth.js

const TOKEN_KEY = "access_token";
const USERNAME_KEY = "username";
let mode = "login"; // "login" or "signup"

const form = document.getElementById("auth-form");
const usernameInput = document.getElementById("username");
const passwordInput = document.getElementById("password");
const submitButton = document.getElementById("auth-submit");
const toggleButton = document.getElementById("toggle-mode");
const toggleText = document.getElementById("toggle-text");
const errorBox = document.getElementById("auth-error");
const titleEl = document.querySelector(".auth-title");
const subtitleEl = document.querySelector(".auth-subtitle");

function setMode(newMode) {
  mode = newMode;
  errorBox.style.display = "none";
  errorBox.textContent = "";

  if (mode === "login") {
    titleEl.textContent = "Welcome to MoneyFlow";
    subtitleEl.textContent = "Track your spending. Stay in control.";
    submitButton.textContent = "Log in";
    toggleText.textContent = "Don’t have an account?";
    toggleButton.textContent = "Sign up";
    passwordInput.setAttribute("autocomplete", "current-password");
  } else {
    titleEl.textContent = "Create your account";
    subtitleEl.textContent = "Sign up to start tracking your expenses.";
    submitButton.textContent = "Sign up";
    toggleText.textContent = "Already have an account?";
    toggleButton.textContent = "Log in";
    passwordInput.setAttribute("autocomplete", "new-password");
  }
}

toggleButton.addEventListener("click", () => {
  setMode(mode === "login" ? "signup" : "login");
});

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  errorBox.style.display = "none";
  errorBox.textContent = "";

  const username = usernameInput.value.trim();
  const password = passwordInput.value;

  if (!username || !password) {
    errorBox.textContent = "Please fill in both username and password.";
    errorBox.style.display = "block";
    return;
  }

  const endpoint = mode === "login" ? "/auth/login" : "/auth/register";

  try {
    const res = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });

    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      const msg = data.detail || "Something went wrong.";
      errorBox.textContent = msg;
      errorBox.style.display = "block";
      return;
    }

    const data = await res.json();

    if (mode === "signup") {
      setMode("login");
      errorBox.style.display = "block";
      errorBox.style.color = "#00e0b8";
      errorBox.textContent = "Account created. You can now log in.";
      return;
    }

    if (data.access_token) {
      localStorage.setItem(TOKEN_KEY, data.access_token);
      localStorage.setItem(USERNAME_KEY, username);
    }
    window.location.href = "/dashboard";
  } catch (err) {
    console.error(err);
    errorBox.textContent = "Network error. Please try again.";
    errorBox.style.display = "block";
  }
});

setMode("login");
