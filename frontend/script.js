const API_BASE = window.API_URL || "http://127.0.0.1:5000";

let allTasks = [];
let filterValue = "all";

const taskListEl = document.getElementById("taskList");
const loadingEl = document.getElementById("loading");
const errorStateEl = document.getElementById("errorState");
const emptyStateEl = document.getElementById("emptyState");
const feedbackEl = document.getElementById("feedback");

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

function filteredTasks() {
    if (filterValue === "completed") {
        return allTasks.filter((task) => task.completed);
    }
    if (filterValue === "active") {
        return allTasks.filter((task) => !task.completed);
    }
    return allTasks;
}

function taskItem(task) {
    const created = task.createdAt ? new Date(task.createdAt).toLocaleString() : "";
    return `
        <li class="task ${task.completed ? "done" : ""}">
            <div class="task-main">
                <input type="checkbox" data-action="toggle" data-id="${task.id}" ${task.completed ? "checked" : ""}>
                <span class="title">${task.title}</span>
            </div>
            <div class="task-actions">
                <button data-action="edit" data-id="${task.id}" class="ghost">Edit</button>
                <button data-action="delete" data-id="${task.id}" class="danger">Delete</button>
            </div>
            <small>Created: ${created}</small>
        </li>
    `;
}

function renderTasks() {
    const visibleTasks = filteredTasks();
    taskListEl.innerHTML = visibleTasks.map(taskItem).join("");
    emptyStateEl.classList.toggle("hide", visibleTasks.length !== 0);
}

async function loadTasks() {
    setLoading(true);
    showError("");
    try {
        const tasks = await request("/tasks");
        allTasks = tasks;
        renderTasks();
    } catch (error) {
        showError(error.message || "Could not load tasks");
    } finally {
        setLoading(false);
    }
}

async function addTask(title) {
    await request("/tasks", {
        method: "POST",
        body: JSON.stringify({ title }),
    });
    showFeedback("Task created");
    await loadTasks();
}

async function updateTask(taskId, payload) {
    await request(`/tasks/${taskId}`, {
        method: "PATCH",
        body: JSON.stringify(payload),
    });
    await loadTasks();
}

async function deleteTask(taskId) {
    await request(`/tasks/${taskId}`, { method: "DELETE" });
    showFeedback("Task deleted");
    await loadTasks();
}

async function handleTaskAction(event) {
    const action = event.target.dataset.action;
    const taskId = event.target.dataset.id;
    if (!action || !taskId) {
        return;
    }

    const task = allTasks.find((item) => item.id === taskId);
    if (!task) {
        return;
    }

    try {
        showError("");
        if (action === "toggle") {
            await updateTask(taskId, { completed: !task.completed });
            return;
        }

        if (action === "edit") {
            const nextTitle = prompt("Edit task title", task.title);
            if (!nextTitle || !nextTitle.trim()) {
                return;
            }
            await updateTask(taskId, { title: nextTitle.trim() });
            showFeedback("Task updated");
            return;
        }

        if (action === "delete") {
            await deleteTask(taskId);
        }
    } catch (error) {
        showError(error.message || "Action failed");
    }
}

async function handleAddTask(event) {
    event.preventDefault();
    const input = document.getElementById("taskTitle");
    const title = input.value.trim();
    if (!title) {
        showError("Task title is required");
        return;
    }

    try {
        showError("");
        await addTask(title);
        input.value = "";
        input.focus();
    } catch (error) {
        showError(error.message || "Could not create task");
    }
}

function bootstrap() {
    document.getElementById("taskForm").addEventListener("submit", handleAddTask);
    document.getElementById("taskList").addEventListener("click", handleTaskAction);
    document.getElementById("filterSelect").addEventListener("change", (event) => {
        filterValue = event.target.value;
        renderTasks();
    });

    loadTasks();
}

document.addEventListener("DOMContentLoaded", bootstrap);