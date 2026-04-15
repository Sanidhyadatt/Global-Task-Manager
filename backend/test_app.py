import unittest
import json
import os
from app import app, FILE


class TaskAPITest(unittest.TestCase):

    def setUp(self):
        app.testing = True
        self.client = app.test_client()

        # 🔥 reset test database before each test
        if os.path.exists(FILE):
            os.remove(FILE)
            
        with open(FILE, "w") as f:
            json.dump([], f)

    def tearDown(self):
        # clean DB after tests
        if os.path.exists(FILE):
            os.remove(FILE)

    # ---------- GET TEST ----------
    def test_get_tasks(self):
        response = self.client.get("/tasks")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.is_json, True)

    # ---------- POST TEST ----------
    def test_add_task(self):
        response = self.client.post(
            "/tasks",
            json={"title": "Test Task"}
        )

        self.assertEqual(response.status_code, 201)

        data = json.loads(response.data)

        self.assertIn("title", data)
        self.assertEqual(data["title"], "Test Task")

    # ---------- UPDATE TEST ----------
    def test_update_task(self):
        # create task first
        res = self.client.post("/tasks", json={"title": "Old Task"})
        task = json.loads(res.data)

        task_id = task["id"]

        # update it
        response = self.client.put(
            f"/tasks/{task_id}",
            json={"title": "Updated Task", "completed": True}
        )

        self.assertEqual(response.status_code, 200)

    # ---------- DELETE TEST ----------
    def test_delete_task(self):
        res = self.client.post("/tasks", json={"title": "Delete Me"})
        task = json.loads(res.data)

        task_id = task["id"]

        response = self.client.delete(f"/tasks/{task_id}")
        self.assertEqual(response.status_code, 200)


if __name__ == "__main__":
    unittest.main()