# Task Manager Assignment Solution

This repository contains a full stack Task Manager built to satisfy the technical assignment requirements with additional production-style capabilities.

## Submission Note

This submission is intentionally structured to prioritize clarity, correctness, and sensible trade-offs for a small feature build.
Core assignment requirements are implemented first, and additional capabilities are layered without breaking the required API contract.

## Assignment Coverage Checklist

### Core Frontend
- Display list of tasks: Yes
- Form to add new task: Yes
- Mark task as completed: Yes
- Delete task: Yes
- Loading and error states: Yes

### Core Backend
- Simple REST API: Yes
- Basic validation: Yes
- Clear JSON responses: Yes
- Clean structure: Yes

### Required Endpoints
- GET /tasks: implemented
- POST /tasks: implemented
- PATCH /tasks/:id: implemented
- DELETE /tasks/:id: implemented

### Required Data Model
- id: Yes
- title: Yes
- completed: Yes
- createdAt: Yes

## Additional Features
- Filter tasks by completed/incomplete
- Edit existing task title
- Persistent storage using MongoDB
- Backend tests
- Docker setup

## Extra Portfolio Features
Additional advanced APIs are available under /api for authentication and richer task workflows. These are not required by the assignment, but show deeper backend skills.

## Tech Stack
- Frontend: HTML, CSS, Vanilla JavaScript
- Backend: Flask (Python)
- Database: MongoDB
- Containerization: Docker + Docker Compose

## Run With Docker

1. Start all services

   docker compose up --build

2. Open frontend

   http://localhost:8080
   http://localhost:8080/login.html
   http://localhost:8080/signup.html

3. Backend endpoints

   http://localhost:5000/tasks

4. Stop services

   docker compose down

## Run Locally (Without Docker)

### Backend

1. Create venv

   python3 -m venv .venv
   source .venv/bin/activate

2. Install dependencies

   pip install -r backend/requirements.txt

3. Start MongoDB (port 27017)

4. Run backend

   cd backend
   python app.py

### Frontend

1. Serve static frontend

   cd frontend
   python3 -m http.server 8080

2. Open

   http://localhost:8080
   http://localhost:8080/login.html
   http://localhost:8080/signup.html

## Tests

Run tests locally:

cd backend
python -m unittest -v

Or in Docker:

docker compose exec -T backend python -m unittest -v

## Assumptions and Trade-offs
- MongoDB is used for persistence even though database was optional, to strengthen the submission.
- Required endpoints are public and intentionally simple to align with assignment expectations.
- Advanced authenticated APIs are kept under /api to avoid interfering with the core evaluation flow.

## Final Checklist
- README with setup and run instructions: Included
- Short note describing assumptions and trade-offs: Included
- Working solution focused on clarity and correctness: Included
