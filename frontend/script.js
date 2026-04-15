const API = "http://127.0.0.1:5000";

let globalTasks = [];
let currentFilter = 'all';

document.addEventListener("DOMContentLoaded", () => {
    loadTasks();

    const titleInput = document.getElementById("title");
    titleInput.addEventListener("keypress", (e) => {
        if (e.key === "Enter") {
            e.preventDefault();
            addTask();
        }
    });

    const addBtn = document.getElementById("addBtn");
    addBtn.addEventListener("click", addTask);

    const searchInput = document.getElementById("search");
    searchInput.addEventListener("input", renderTasks);

    const filterBtns = document.querySelectorAll(".filter-btn");
    filterBtns.forEach(btn => {
        btn.addEventListener("click", () => {
            document.querySelector(".filter-btn.active").classList.remove("active");
            btn.classList.add("active");
            currentFilter = btn.dataset.filter;
            renderTasks();
        });
    });
});

function showError(msg) {
    const errorEl = document.getElementById("error-msg");
    if (!msg) {
        errorEl.style.display = "none";
        return;
    }
    errorEl.innerText = msg;
    errorEl.style.display = "block";
    setTimeout(() => {
        errorEl.style.display = "none";
    }, 4000);
}

async function loadTasks() {
    try {
        const response = await fetch(`${API}/tasks`);
        if (!response.ok) throw new Error("Failed to load tasks");
        const tasks = await response.json();
        globalTasks = tasks;
        renderTasks();
    } catch (err) {
        showError("Could not connect to the server.");
    }
}

function renderTasks() {
    const list = document.getElementById("list");
    list.innerHTML = "";

    const query = document.getElementById("search").value.toLowerCase();
    
    // Filter
    let filteredTasks = globalTasks.filter(t => {
        const matchesQuery = !query || t.title.toLowerCase().includes(query);
        const matchesFilter = currentFilter === 'all' 
                            || (currentFilter === 'active' && !t.completed) 
                            || (currentFilter === 'completed' && t.completed);
        return matchesQuery && matchesFilter;
    });

    // Stats
    const stats = document.getElementById("stats");
    const completed = globalTasks.filter(t => t.completed).length;
    stats.innerText = `${completed} / ${globalTasks.length} completed`;

    if (filteredTasks.length === 0) {
        list.innerHTML = `<div class="empty-state">No tasks to display here 🚀</div>`;
        return;
    }

    filteredTasks.forEach((t, index) => {
        const div = document.createElement("div");
        div.className = "task";
        div.style.animationDelay = `${index * 0.05}s`;

        div.innerHTML = `
            <div class="task-content" onclick="toggle(${t.id}, ${t.completed})">
                <div class="checkbox ${t.completed ? 'checked' : ''}">
                    <svg viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" stroke-width="3" fill="none" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>
                </div>
                <p class="${t.completed ? 'done' : ''}">${t.title}</p>
            </div>
            <div class="actions">
                <button class="btn-icon btn-edit" onclick="event.stopPropagation(); editTask(${t.id})" aria-label="Edit Task">
                    <svg viewBox="0 0 24 24" width="18" height="18" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"><polygon points="16 3 21 8 8 21 3 21 3 16 16 3"></polygon></svg>
                </button>
                <button class="btn-icon btn-delete" onclick="event.stopPropagation(); removeTask(${t.id})" aria-label="Delete Task">
                    <svg viewBox="0 0 24 24" width="18" height="18" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path><line x1="10" y1="11" x2="10" y2="17"></line><line x1="14" y1="11" x2="14" y2="17"></line></svg>
                </button>
            </div>
        `;

        list.appendChild(div);
    });
}

async function addTask() {
    showError("");
    const titleInput = document.getElementById("title");
    const title = titleInput.value.trim();

    if (!title) {
        showError("Please enter a task title!");
        titleInput.focus();
        return;
    }

    try {
        const response = await fetch(`${API}/tasks`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ title })
        });

        if (!response.ok) {
            const data = await response.json();
            throw new Error(data.error || "Failed to add task");
        }

        titleInput.value = "";
        await loadTasks();
    } catch (err) {
        showError(err.message);
    }
}

async function removeTask(id) {
    // Optimistic remove for flawless feel
    globalTasks = globalTasks.filter(t => t.id !== id);
    renderTasks();
    
    try {
        await fetch(`${API}/tasks/${id}`, { method: "DELETE" });
    } catch (err) {
        showError("Failed to delete task.");
        loadTasks(); // rollback on failure
    }
}

async function toggle(id, status) {
    // Optimistic UI
    const task = globalTasks.find(t => t.id === id);
    if(task) task.completed = !status;
    renderTasks();

    try {
        await fetch(`${API}/tasks/${id}`, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ completed: !status })
        });
    } catch (err) {
        showError("Failed to update task.");
        loadTasks(); // rollback on failure
    }
}

async function editTask(id) {
    const task = globalTasks.find(t => t.id === id);
    if (!task) return;

    const newTitle = prompt("Edit task:", task.title);
    if (newTitle !== null && newTitle.trim() !== "" && newTitle.trim() !== task.title) {
        // Optimistic update
        const oldTitle = task.title;
        task.title = newTitle.trim();
        renderTasks();

        try {
            const response = await fetch(`${API}/tasks/${id}`, {
                method: "PUT",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ title: task.title })
            });

            if (!response.ok) {
                const data = await response.json();
                throw new Error(data.error || "Failed to edit task");
            }
        } catch (err) {
            showError("Failed to edit task.");
            task.title = oldTitle; // rollback
            renderTasks();
        }
    }
}