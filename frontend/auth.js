const API_BASE = window.API_URL || "http://127.0.0.1:5000/api";

function showFeedback(message, type = "ok") {
    const feedbackEl = document.getElementById("feedback");
    if (!feedbackEl) {
        return;
    }
    feedbackEl.textContent = message;
    feedbackEl.className = `feedback ${type}`;
}

async function request(path, options = {}) {
    const response = await fetch(`${API_BASE}${path}`, {
        headers: { "Content-Type": "application/json", ...(options.headers || {}) },
        ...options,
    });

    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
        throw new Error(data.error || "Request failed");
    }
    return data;
}

async function checkExistingAuth() {
    const token = localStorage.getItem("gtm_token");
    if (!token) {
        return;
    }

    try {
        await request("/auth/me", {
            headers: { Authorization: `Bearer ${token}` },
        });
        window.location.href = "index.html";
    } catch (_error) {
        localStorage.removeItem("gtm_token");
    }
}

function bindLogin() {
    const loginForm = document.getElementById("loginForm");
    if (!loginForm) {
        return;
    }

    loginForm.addEventListener("submit", async (event) => {
        event.preventDefault();
        const payload = {
            email: document.getElementById("loginEmail").value.trim(),
            password: document.getElementById("loginPassword").value,
        };

        try {
            const data = await request("/auth/login", {
                method: "POST",
                body: JSON.stringify(payload),
            });
            localStorage.setItem("gtm_token", data.token);
            showFeedback("Login successful. Redirecting...");
            window.location.href = "index.html";
        } catch (error) {
            showFeedback(error.message || "Login failed", "warn");
        }
    });
}

function bindRegister() {
    const registerForm = document.getElementById("registerForm");
    if (!registerForm) {
        return;
    }

    registerForm.addEventListener("submit", async (event) => {
        event.preventDefault();
        const payload = {
            name: document.getElementById("registerName").value.trim(),
            email: document.getElementById("registerEmail").value.trim(),
            password: document.getElementById("registerPassword").value,
        };

        try {
            const data = await request("/auth/register", {
                method: "POST",
                body: JSON.stringify(payload),
            });
            localStorage.setItem("gtm_token", data.token);
            showFeedback("Account created. Redirecting...");
            window.location.href = "index.html";
        } catch (error) {
            showFeedback(error.message || "Registration failed", "warn");
        }
    });
}

document.addEventListener("DOMContentLoaded", async () => {
    await checkExistingAuth();
    bindLogin();
    bindRegister();
});
