import os
from datetime import datetime, timedelta, timezone
from functools import wraps

import jwt
from bson import ObjectId
from flask import Flask, jsonify, request
from flask_cors import CORS
from pymongo import ASCENDING, DESCENDING, MongoClient, ReturnDocument
from pymongo.errors import DuplicateKeyError
from werkzeug.security import check_password_hash, generate_password_hash


def utc_now():
    return datetime.now(timezone.utc)


def parse_iso_datetime(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def oid_from_str(value):
    try:
        return ObjectId(value)
    except Exception:
        return None


app = Flask(__name__)

frontend_origin = os.getenv("FRONTEND_ORIGIN", "http://localhost:8080")
CORS(
    app,
    resources={
        r"/api/*": {"origins": [frontend_origin, "http://127.0.0.1:5500"]},
        r"/tasks*": {"origins": [frontend_origin, "http://127.0.0.1:5500"]},
    },
)

app.config["SECRET_KEY"] = os.getenv("JWT_SECRET", "change-me-in-production")
app.config["JWT_EXPIRES_HOURS"] = int(os.getenv("JWT_EXPIRES_HOURS", "24"))

mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
mongo_db_name = os.getenv("MONGO_DB", "global_task_manager")

mongo_client = MongoClient(mongo_uri)
db = mongo_client[mongo_db_name]
users_col = db["users"]
tasks_col = db["tasks"]
core_tasks_col = db["core_tasks"]


def ensure_indexes():
    users_col.create_index("email", unique=True)
    tasks_col.create_index([("user_id", ASCENDING), ("created_at", DESCENDING)])
    tasks_col.create_index([("user_id", ASCENDING), ("status", ASCENDING)])
    tasks_col.create_index([("user_id", ASCENDING), ("due_date", ASCENDING)])
    tasks_col.create_index([("user_id", ASCENDING), ("tags", ASCENDING)])
    core_tasks_col.create_index([("createdAt", DESCENDING)])


ensure_indexes()


def serialize_user(user):
    return {
        "id": str(user["_id"]),
        "name": user.get("name", ""),
        "email": user.get("email", ""),
        "created_at": user.get("created_at").isoformat() if user.get("created_at") else None,
    }


def serialize_task(task):
    return {
        "id": str(task["_id"]),
        "user_id": str(task["user_id"]),
        "title": task.get("title", ""),
        "description": task.get("description", ""),
        "status": task.get("status", "todo"),
        "priority": task.get("priority", "medium"),
        "completed": task.get("completed", False),
        "starred": task.get("starred", False),
        "archived": task.get("archived", False),
        "tags": task.get("tags", []),
        "due_date": task.get("due_date").isoformat() if task.get("due_date") else None,
        "created_at": task.get("created_at").isoformat() if task.get("created_at") else None,
        "updated_at": task.get("updated_at").isoformat() if task.get("updated_at") else None,
    }


def serialize_core_task(task):
    return {
        "id": str(task["_id"]),
        "title": task.get("title", ""),
        "completed": bool(task.get("completed", False)),
        "createdAt": task.get("createdAt").isoformat() if task.get("createdAt") else None,
    }


def token_for_user(user):
    expires_at = utc_now() + timedelta(hours=app.config["JWT_EXPIRES_HOURS"])
    payload = {
        "sub": str(user["_id"]),
        "email": user["email"],
        "exp": expires_at,
        "iat": utc_now(),
    }
    return jwt.encode(payload, app.config["SECRET_KEY"], algorithm="HS256")


def get_auth_token():
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    return auth_header.split(" ", 1)[1].strip()


def auth_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        token = get_auth_token()
        if not token:
            return jsonify({"error": "authentication required"}), 401

        try:
            payload = jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "token expired"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "invalid token"}), 401

        user_id = oid_from_str(payload.get("sub"))
        if not user_id:
            return jsonify({"error": "invalid token subject"}), 401

        user = users_col.find_one({"_id": user_id})
        if not user:
            return jsonify({"error": "user not found"}), 401

        request.current_user = user
        return func(*args, **kwargs)

    return wrapper


def normalize_status(value):
    allowed = {"todo", "in_progress", "done"}
    if value in allowed:
        return value
    return "todo"


def normalize_priority(value):
    allowed = {"low", "medium", "high", "critical"}
    if value in allowed:
        return value
    return "medium"


@app.route("/")
def home():
    return jsonify({"status": "Global Task Manager API running", "version": "2.0"})


# Assignment-compatible core endpoints
@app.route("/tasks", methods=["GET"])
def get_core_tasks():
    tasks = list(core_tasks_col.find({}).sort("createdAt", DESCENDING))
    return jsonify([serialize_core_task(task) for task in tasks])


@app.route("/tasks", methods=["POST"])
def create_core_task():
    data = request.get_json() or {}
    title = str(data.get("title", "")).strip()
    if not title:
        return jsonify({"error": "title is required"}), 400

    task_doc = {
        "title": title,
        "completed": False,
        "createdAt": utc_now(),
    }
    result = core_tasks_col.insert_one(task_doc)
    task_doc["_id"] = result.inserted_id
    return jsonify(serialize_core_task(task_doc)), 201


@app.route("/tasks/<task_id>", methods=["PATCH"])
def update_core_task(task_id):
    oid = oid_from_str(task_id)
    if not oid:
        return jsonify({"error": "invalid task id"}), 400

    data = request.get_json() or {}
    updates = {}

    if "completed" in data:
        updates["completed"] = bool(data.get("completed"))

    if "title" in data:
        title = str(data.get("title", "")).strip()
        if not title:
            return jsonify({"error": "title cannot be empty"}), 400
        updates["title"] = title

    if not updates:
        return jsonify({"error": "no valid fields provided"}), 400

    task = core_tasks_col.find_one_and_update(
        {"_id": oid},
        {"$set": updates},
        return_document=ReturnDocument.AFTER,
    )
    if not task:
        return jsonify({"error": "task not found"}), 404

    return jsonify(serialize_core_task(task))


@app.route("/tasks/<task_id>", methods=["DELETE"])
def delete_core_task(task_id):
    oid = oid_from_str(task_id)
    if not oid:
        return jsonify({"error": "invalid task id"}), 400

    result = core_tasks_col.delete_one({"_id": oid})
    if result.deleted_count == 0:
        return jsonify({"error": "task not found"}), 404

    return jsonify({"message": "task deleted"})


@app.route("/api/health", methods=["GET"])
def health():
    db.command("ping")
    return jsonify({"ok": True, "database": "connected"})


@app.route("/api/auth/register", methods=["POST"])
def register():
    data = request.get_json() or {}
    name = str(data.get("name", "")).strip()
    email = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", ""))

    if len(name) < 2:
        return jsonify({"error": "name must be at least 2 characters"}), 400
    if "@" not in email:
        return jsonify({"error": "valid email required"}), 400
    if len(password) < 6:
        return jsonify({"error": "password must be at least 6 characters"}), 400

    user_doc = {
        "name": name,
        "email": email,
        "password_hash": generate_password_hash(password),
        "created_at": utc_now(),
    }

    try:
        result = users_col.insert_one(user_doc)
    except DuplicateKeyError:
        return jsonify({"error": "email already registered"}), 409

    user_doc["_id"] = result.inserted_id
    token = token_for_user(user_doc)

    return jsonify({"token": token, "user": serialize_user(user_doc)}), 201


@app.route("/api/auth/login", methods=["POST"])
def login():
    data = request.get_json() or {}
    email = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", ""))

    user = users_col.find_one({"email": email})
    if not user or not check_password_hash(user.get("password_hash", ""), password):
        return jsonify({"error": "invalid credentials"}), 401

    token = token_for_user(user)
    return jsonify({"token": token, "user": serialize_user(user)})


@app.route("/api/auth/me", methods=["GET"])
@auth_required
def me():
    return jsonify({"user": serialize_user(request.current_user)})


@app.route("/api/tasks", methods=["POST"])
@auth_required
def create_task():
    data = request.get_json() or {}
    title = str(data.get("title", "")).strip()
    if not title:
        return jsonify({"error": "title is required"}), 400

    status = normalize_status(data.get("status", "todo"))
    priority = normalize_priority(data.get("priority", "medium"))
    tags = data.get("tags", [])
    if not isinstance(tags, list):
        tags = []
    tags = [str(tag).strip().lower() for tag in tags if str(tag).strip()]

    due_date = parse_iso_datetime(data.get("due_date"))
    now = utc_now()

    task_doc = {
        "user_id": request.current_user["_id"],
        "title": title,
        "description": str(data.get("description", "")).strip(),
        "status": status,
        "priority": priority,
        "completed": status == "done",
        "starred": bool(data.get("starred", False)),
        "archived": False,
        "tags": tags,
        "due_date": due_date,
        "created_at": now,
        "updated_at": now,
    }

    result = tasks_col.insert_one(task_doc)
    task_doc["_id"] = result.inserted_id
    return jsonify({"task": serialize_task(task_doc)}), 201


@app.route("/api/tasks", methods=["GET"])
@auth_required
def list_tasks():
    user_id = request.current_user["_id"]
    query = {"user_id": user_id}

    status = request.args.get("status")
    priority = request.args.get("priority")
    starred = request.args.get("starred")
    archived = request.args.get("archived")
    search = request.args.get("search")
    tag = request.args.get("tag")
    due_before = parse_iso_datetime(request.args.get("due_before"))
    due_after = parse_iso_datetime(request.args.get("due_after"))

    if status in {"todo", "in_progress", "done"}:
        query["status"] = status
    if priority in {"low", "medium", "high", "critical"}:
        query["priority"] = priority
    if starred in {"true", "false"}:
        query["starred"] = starred == "true"
    if archived in {"true", "false"}:
        query["archived"] = archived == "true"
    else:
        query["archived"] = False

    if tag:
        query["tags"] = str(tag).strip().lower()

    if search:
        escaped = str(search).strip()
        query["$or"] = [
            {"title": {"$regex": escaped, "$options": "i"}},
            {"description": {"$regex": escaped, "$options": "i"}},
            {"tags": {"$regex": escaped, "$options": "i"}},
        ]

    if due_before or due_after:
        due_query = {}
        if due_before:
            due_query["$lte"] = due_before
        if due_after:
            due_query["$gte"] = due_after
        query["due_date"] = due_query

    sort_by = request.args.get("sort_by", "created_at")
    sort_order = request.args.get("sort_order", "desc")
    sort_map = {
        "created_at": "created_at",
        "updated_at": "updated_at",
        "due_date": "due_date",
        "priority": "priority",
        "title": "title",
    }
    sort_field = sort_map.get(sort_by, "created_at")
    direction = ASCENDING if sort_order == "asc" else DESCENDING

    page = max(int(request.args.get("page", 1)), 1)
    limit = max(min(int(request.args.get("limit", 25)), 100), 1)
    skip = (page - 1) * limit

    total = tasks_col.count_documents(query)
    items = list(tasks_col.find(query).sort(sort_field, direction).skip(skip).limit(limit))

    return jsonify(
        {
            "tasks": [serialize_task(task) for task in items],
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "pages": (total + limit - 1) // limit,
            },
        }
    )


@app.route("/api/tasks/<task_id>", methods=["GET"])
@auth_required
def get_task(task_id):
    oid = oid_from_str(task_id)
    if not oid:
        return jsonify({"error": "invalid task id"}), 400

    task = tasks_col.find_one({"_id": oid, "user_id": request.current_user["_id"]})
    if not task:
        return jsonify({"error": "task not found"}), 404

    return jsonify({"task": serialize_task(task)})


@app.route("/api/tasks/<task_id>", methods=["PUT", "PATCH"])
@auth_required
def update_task(task_id):
    oid = oid_from_str(task_id)
    if not oid:
        return jsonify({"error": "invalid task id"}), 400

    data = request.get_json() or {}
    updates = {}

    if "title" in data:
        title = str(data.get("title", "")).strip()
        if not title:
            return jsonify({"error": "title cannot be empty"}), 400
        updates["title"] = title

    if "description" in data:
        updates["description"] = str(data.get("description", "")).strip()

    if "status" in data:
        status = normalize_status(data.get("status"))
        updates["status"] = status
        updates["completed"] = status == "done"

    if "priority" in data:
        updates["priority"] = normalize_priority(data.get("priority"))

    if "starred" in data:
        updates["starred"] = bool(data.get("starred"))

    if "archived" in data:
        updates["archived"] = bool(data.get("archived"))

    if "tags" in data:
        tags = data.get("tags", [])
        if not isinstance(tags, list):
            tags = []
        updates["tags"] = [str(tag).strip().lower() for tag in tags if str(tag).strip()]

    if "due_date" in data:
        if data.get("due_date"):
            parsed = parse_iso_datetime(data.get("due_date"))
            if not parsed:
                return jsonify({"error": "invalid due_date format"}), 400
            updates["due_date"] = parsed
        else:
            updates["due_date"] = None

    if not updates:
        return jsonify({"error": "no valid fields provided"}), 400

    updates["updated_at"] = utc_now()

    task = tasks_col.find_one_and_update(
        {"_id": oid, "user_id": request.current_user["_id"]},
        {"$set": updates},
        return_document=ReturnDocument.AFTER,
    )
    if not task:
        return jsonify({"error": "task not found"}), 404

    return jsonify({"task": serialize_task(task)})


@app.route("/api/tasks/<task_id>/toggle", methods=["PATCH"])
@auth_required
def toggle_task(task_id):
    oid = oid_from_str(task_id)
    if not oid:
        return jsonify({"error": "invalid task id"}), 400

    task = tasks_col.find_one({"_id": oid, "user_id": request.current_user["_id"]})
    if not task:
        return jsonify({"error": "task not found"}), 404

    completed = not task.get("completed", False)
    status = "done" if completed else "in_progress"
    tasks_col.update_one(
        {"_id": oid},
        {
            "$set": {
                "completed": completed,
                "status": status,
                "updated_at": utc_now(),
            }
        },
    )

    updated = tasks_col.find_one({"_id": oid})
    return jsonify({"task": serialize_task(updated)})


@app.route("/api/tasks/<task_id>", methods=["DELETE"])
@auth_required
def delete_task(task_id):
    oid = oid_from_str(task_id)
    if not oid:
        return jsonify({"error": "invalid task id"}), 400

    result = tasks_col.delete_one({"_id": oid, "user_id": request.current_user["_id"]})
    if result.deleted_count == 0:
        return jsonify({"error": "task not found"}), 404

    return jsonify({"message": "task deleted"})


@app.route("/api/tasks/bulk", methods=["PATCH"])
@auth_required
def bulk_update_tasks():
    data = request.get_json() or {}
    ids = data.get("task_ids", [])
    action = data.get("action")

    if not isinstance(ids, list) or not ids:
        return jsonify({"error": "task_ids must be a non-empty list"}), 400

    task_ids = [oid_from_str(task_id) for task_id in ids]
    task_ids = [oid for oid in task_ids if oid]
    if not task_ids:
        return jsonify({"error": "invalid task ids"}), 400

    user_query = {"_id": {"$in": task_ids}, "user_id": request.current_user["_id"]}
    now = utc_now()

    if action == "mark_done":
        update_doc = {"$set": {"status": "done", "completed": True, "updated_at": now}}
    elif action == "archive":
        update_doc = {"$set": {"archived": True, "updated_at": now}}
    elif action == "unarchive":
        update_doc = {"$set": {"archived": False, "updated_at": now}}
    else:
        return jsonify({"error": "unsupported action"}), 400

    result = tasks_col.update_many(user_query, update_doc)
    return jsonify({"updated": result.modified_count})


@app.route("/api/tasks/analytics", methods=["GET"])
@auth_required
def analytics():
    user_id = request.current_user["_id"]
    match = {"user_id": user_id, "archived": False}
    total = tasks_col.count_documents(match)
    done = tasks_col.count_documents({**match, "status": "done"})
    todo = tasks_col.count_documents({**match, "status": "todo"})
    in_progress = tasks_col.count_documents({**match, "status": "in_progress"})
    overdue = tasks_col.count_documents(
        {
            **match,
            "due_date": {"$lt": utc_now()},
            "status": {"$ne": "done"},
        }
    )
    starred = tasks_col.count_documents({**match, "starred": True})

    completion_rate = 0
    if total > 0:
        completion_rate = round((done / total) * 100, 2)

    return jsonify(
        {
            "summary": {
                "total": total,
                "todo": todo,
                "in_progress": in_progress,
                "done": done,
                "overdue": overdue,
                "starred": starred,
                "completion_rate": completion_rate,
            }
        }
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)