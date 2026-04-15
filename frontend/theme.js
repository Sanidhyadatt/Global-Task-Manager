const THEME_STORAGE_KEY = "gtm_theme";

function getSystemTheme() {
    return window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

function getStoredTheme() {
    return localStorage.getItem(THEME_STORAGE_KEY) || getSystemTheme();
}

function applyTheme(theme) {
    document.documentElement.dataset.theme = theme;
    document.documentElement.style.colorScheme = theme;
    const themeButton = document.getElementById("themeToggle");
    if (themeButton) {
        themeButton.textContent = theme === "dark" ? "Light mode" : "Dark mode";
    }
}

function toggleTheme() {
    const currentTheme = document.documentElement.dataset.theme || getStoredTheme();
    const nextTheme = currentTheme === "dark" ? "light" : "dark";
    localStorage.setItem(THEME_STORAGE_KEY, nextTheme);
    applyTheme(nextTheme);
}

document.addEventListener("DOMContentLoaded", () => {
    applyTheme(getStoredTheme());
    const themeButton = document.getElementById("themeToggle");
    if (themeButton) {
        themeButton.addEventListener("click", toggleTheme);
    }
});