from flask import Flask, request, jsonify
from flask_cors import CORS
import json, os

app = Flask(__name__)
CORS(app)

FILE = "tasks.json"


def load_tasks():
    if not os.path.exists(FILE):
        return []
    try:
        with open(FILE, "r") as f:
            return json.load(f)
    except:
        return []


def save_tasks(tasks):
    with open(FILE, "w") as f:
        json.dump(tasks, f, indent=4)


@app.route("/")
def home():
    return jsonify({"status": "TaskFlow API running 🚀"})


@app.route("/tasks", methods=["GET"])
def get_tasks():
    return jsonify(load_tasks())


@app.route("/tasks", methods=["POST"])
def add_task():
    data = request.get_json()

    if not data or not data.get("title") or not data.get("title").strip():
        return jsonify({"error": "title required"}), 400

    tasks = load_tasks()

    new_id = 1
    if tasks:
        new_id = max(t["id"] for t in tasks) + 1

    new_task = {
        "id": new_id,
        "title": data["title"].strip(),
        "completed": False
    }

    tasks.append(new_task)
    save_tasks(tasks)

    return jsonify(new_task), 201


@app.route("/tasks/<int:id>", methods=["PUT"])
def update_task(id):
    data = request.get_json() or {}
    tasks = load_tasks()

    for t in tasks:
        if t["id"] == id:
            if "title" in data and str(data["title"]).strip():
                t["title"] = str(data["title"]).strip()
            if "completed" in data:
                t["completed"] = bool(data["completed"])
            save_tasks(tasks)
            return jsonify(t)

    return jsonify({"error": "not found"}), 404


@app.route("/tasks/<int:id>", methods=["DELETE"])
def delete_task(id):
    tasks = load_tasks()
    original_len = len(tasks)
    tasks = [t for t in tasks if t["id"] != id]
    
    if len(tasks) == original_len:
        return jsonify({"error": "not found"}), 404
        
    save_tasks(tasks)
    return jsonify({"message": "deleted"})


# IMPORTANT FOR DEPLOY
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)