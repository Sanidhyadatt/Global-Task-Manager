const API_BASE = window.API_URL || "http://127.0.0.1:5000/api";

let token = localStorage.getItem("gtm_token") || "";
let currentTasks = [];
let editingTaskId = null;

const state = {
    search: "",
    status: "",
    priority: "",
    sort_by: "created_at",
    sort_order: "desc",
};

const taskListEl = document.getElementById("taskList");
const loadingEl = document.getElementById("loading");
const errorStateEl = document.getElementById("errorState");
const emptyStateEl = document.getElementById("emptyState");
const feedbackEl = document.getElementById("feedback");
const statsEl = document.getElementById("stats");
const editModalEl = document.getElementById("editModal");

function toDatetimeLocalValue(isoString) {
    if (!isoString) {
        return "";
    }
    const date = new Date(isoString);
    if (Number.isNaN(date.getTime())) {
        return "";
    }
    const offsetMs = date.getTimezoneOffset() * 60000;
    return new Date(date.getTime() - offsetMs).toISOString().slice(0, 16);
}

function showFeedback(message, type = "ok") {
    feedbackEl.textContent = message;
    feedbackEl.className = `feedback ${type}`;
    setTimeout(() => {
        feedbackEl.className = "feedback hide";
    }, 2200);
}

function setLoading(value) {
    loadingEl.classList.toggle("hide", !value);
}

function showError(message) {
    errorStateEl.textContent = message;
    errorStateEl.classList.toggle("hide", !message);
}

function parseTags(raw) {
    return raw
        .split(",")
        .map((tag) => tag.trim().toLowerCase())
        .filter(Boolean);
}

async function request(path, options = {}) {
    const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
    if (token) {
        headers.Authorization = `Bearer ${token}`;
    }

    const response = await fetch(`${API_BASE}${path}`, {
        ...options,
        headers,
    });

    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
        throw new Error(data.error || "Request failed");
    }

    return data;
}

function queryStringFromState() {
    const params = new URLSearchParams();
    Object.entries(state).forEach(([key, value]) => {
        if (value) {
            params.set(key, value);
        }
    });
    params.set("limit", "100");
    return params.toString();
}

function taskCard(task) {
    const dueText = task.due_date ? new Date(task.due_date).toLocaleString() : "No due date";
    const tagsText = (task.tags || []).join(", ");
    return `
        <li class="task ${task.completed ? "done" : ""}">
            <div class="task-main">
                <input type="checkbox" data-action="toggle" data-id="${task.id}" ${task.completed ? "checked" : ""}>
                <div>
                    <span class="title">${task.title}</span>
                    <p class="task-desc">${task.description || "No description"}</p>
                </div>
            </div>
            <div class="task-meta">
                <span class="chip">${task.status}</span>
                <span class="chip">${task.priority}</span>
                <span class="chip">${dueText}</span>
                ${tagsText ? `<span class="chip">${tagsText}</span>` : ""}
            </div>
            <div class="task-actions">
                <button data-action="edit" data-id="${task.id}" class="ghost">Edit</button>
                <button data-action="star" data-id="${task.id}" class="ghost">${task.starred ? "Unstar" : "Star"}</button>
                <button data-action="delete" data-id="${task.id}" class="danger">Delete</button>
            </div>
        </li>
    `;
}

function renderTasks(tasks) {
    currentTasks = tasks;
    taskListEl.innerHTML = tasks.map(taskCard).join("");
    emptyStateEl.classList.toggle("hide", tasks.length !== 0);
}

function renderStats(summary) {
    statsEl.innerHTML = `
        <span>Total: <strong>${summary.total ?? 0}</strong></span>
        <span>Done: <strong>${summary.done ?? 0}</strong></span>
        <span>In Progress: <strong>${summary.in_progress ?? 0}</strong></span>
        <span>Overdue: <strong>${summary.overdue ?? 0}</strong></span>
        <span>Completion: <strong>${summary.completion_rate ?? 0}%</strong></span>
    `;
}

async function refreshTasks() {
    setLoading(true);
    showError("");
    try {
        const [taskData, analyticsData] = await Promise.all([
            request(`/tasks?${queryStringFromState()}`),
            request("/tasks/analytics"),
        ]);
        renderTasks(taskData.tasks || []);
        renderStats(analyticsData.summary || {});
    } catch (error) {
        showError(error.message || "Could not load tasks");
    } finally {
        setLoading(false);
    }
}

function getTask(taskId) {
    return currentTasks.find((item) => item.id === taskId);
}

function openEditModal(task) {
    editingTaskId = task.id;
    document.getElementById("editTaskName").value = task.title || "";
    document.getElementById("editTaskDescription").value = task.description || "";
    document.getElementById("editTaskStatus").value = task.status || "todo";
    document.getElementById("editTaskPriority").value = task.priority || "medium";
    document.getElementById("editTaskDueDate").value = toDatetimeLocalValue(task.due_date);
    document.getElementById("editTaskTags").value = (task.tags || []).join(", ");
    editModalEl.classList.remove("hide");
    editModalEl.setAttribute("aria-hidden", "false");
}

function closeEditModal() {
    editingTaskId = null;
    document.getElementById("editTaskForm").reset();
    editModalEl.classList.add("hide");
    editModalEl.setAttribute("aria-hidden", "true");
}

async function handleEditSubmit(event) {
    event.preventDefault();
    if (!editingTaskId) {
        return;
    }

    const dueRaw = document.getElementById("editTaskDueDate").value;
    const payload = {
        title: document.getElementById("editTaskName").value.trim(),
        description: document.getElementById("editTaskDescription").value.trim(),
        status: document.getElementById("editTaskStatus").value,
        priority: document.getElementById("editTaskPriority").value,
        due_date: dueRaw ? new Date(dueRaw).toISOString() : null,
        tags: parseTags(document.getElementById("editTaskTags").value),
    };

    if (!payload.title) {
        showError("Task title is required");
        return;
    }

    try {
        await request(`/tasks/${editingTaskId}`, {
            method: "PATCH",
            body: JSON.stringify(payload),
        });
        closeEditModal();
        showFeedback("Task updated");
        await refreshTasks();
    } catch (error) {
        showError(error.message || "Could not update task");
    }
}

async function handleTaskAction(event) {
    const action = event.target.dataset.action;
    const taskId = event.target.dataset.id;
    if (!action || !taskId) {
        return;
    }

    const task = getTask(taskId);
    if (!task) {
        return;
    }

    try {
        if (action === "toggle") {
            await request(`/tasks/${taskId}/toggle`, { method: "PATCH" });
        } else if (action === "delete") {
            await request(`/tasks/${taskId}`, { method: "DELETE" });
            showFeedback("Task deleted");
        } else if (action === "star") {
            await request(`/tasks/${taskId}`, {
                method: "PATCH",
                body: JSON.stringify({ starred: !task.starred }),
            });
        } else if (action === "edit") {
            openEditModal(task);
            return;
        }

        await refreshTasks();
    } catch (error) {
        showError(error.message || "Task action failed");
    }
}

async function handleAddTask(event) {
    event.preventDefault();
    const title = document.getElementById("taskTitle").value.trim();
    if (!title) {
        showError("Task title is required");
        return;
    }

    const dueRaw = document.getElementById("taskDueDate").value;
    const payload = {
        title,
        description: document.getElementById("taskDescription").value.trim(),
        status: document.getElementById("taskStatus").value,
        priority: document.getElementById("taskPriority").value,
        tags: parseTags(document.getElementById("taskTags").value),
        due_date: dueRaw ? new Date(dueRaw).toISOString() : null,
    };

    try {
        await request("/tasks", {
            method: "POST",
            body: JSON.stringify(payload),
        });
        showFeedback("Task created");
        document.getElementById("taskForm").reset();
        await refreshTasks();
    } catch (error) {
        showError(error.message || "Could not create task");
    }
}

function bindFilters() {
    document.getElementById("searchInput").addEventListener("input", async (event) => {
        state.search = event.target.value.trim();
        await refreshTasks();
    });

    document.getElementById("statusFilter").addEventListener("change", async (event) => {
        state.status = event.target.value;
        await refreshTasks();
    });

    document.getElementById("priorityFilter").addEventListener("change", async (event) => {
        state.priority = event.target.value;
        await refreshTasks();
    });

    document.getElementById("sortBy").addEventListener("change", async (event) => {
        state.sort_by = event.target.value;
        await refreshTasks();
    });

    document.getElementById("sortOrder").addEventListener("change", async (event) => {
        state.sort_order = event.target.value;
        await refreshTasks();
    });
}

async function handleLogout() {
    token = "";
    localStorage.removeItem("gtm_token");
    window.location.href = "login.html";
}

async function bootstrap() {
    if (!token) {
        window.location.href = "login.html";
        return;
    }

    try {
        await request("/auth/me");
    } catch (_error) {
        localStorage.removeItem("gtm_token");
        window.location.href = "login.html";
        return;
    }

    document.getElementById("logoutBtn").addEventListener("click", handleLogout);
    document.getElementById("taskForm").addEventListener("submit", handleAddTask);
    document.getElementById("taskList").addEventListener("click", handleTaskAction);
    document.getElementById("editTaskForm").addEventListener("submit", handleEditSubmit);
    document.getElementById("closeEditModal").addEventListener("click", closeEditModal);
    document.getElementById("cancelEdit").addEventListener("click", closeEditModal);
    editModalEl.addEventListener("click", (event) => {
        if (event.target === editModalEl) {
            closeEditModal();
        }
    });
    bindFilters();
    await refreshTasks();
}

document.addEventListener("DOMContentLoaded", bootstrap);
