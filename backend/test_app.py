import uuid
import unittest

from app import app, tasks_col, users_col


class TaskAPITest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.testing = True
        cls.client = app.test_client()

    def setUp(self):
        users_col.delete_many({})
        tasks_col.delete_many({})

        email = f"test-{uuid.uuid4().hex[:10]}@example.com"
        register_res = self.client.post(
            "/api/auth/register",
            json={
                "name": "Test User",
                "email": email,
                "password": "pass1234",
            },
        )
        self.assertEqual(register_res.status_code, 201)
        register_data = register_res.get_json()
        self.token = register_data["token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}

    def test_health(self):
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json().get("ok"))

    def test_auth_me(self):
        response = self.client.get("/api/auth/me", headers=self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertIn("user", response.get_json())

    def test_create_and_list_task(self):
        create_response = self.client.post(
            "/api/tasks",
            headers=self.headers,
            json={
                "title": "Prepare internship project",
                "description": "Finalize MongoDB and Docker integration",
                "status": "in_progress",
                "priority": "high",
                "tags": ["internship", "backend"],
            },
        )

        self.assertEqual(create_response.status_code, 201)
        created_task = create_response.get_json().get("task")
        self.assertEqual(created_task["title"], "Prepare internship project")

        list_response = self.client.get("/api/tasks", headers=self.headers)
        self.assertEqual(list_response.status_code, 200)
        payload = list_response.get_json()
        self.assertGreaterEqual(len(payload.get("tasks", [])), 1)

    def test_toggle_and_delete_task(self):
        create_response = self.client.post(
            "/api/tasks",
            headers=self.headers,
            json={"title": "Delete target"},
        )
        task_id = create_response.get_json()["task"]["id"]

        toggle_response = self.client.patch(
            f"/api/tasks/{task_id}/toggle",
            headers=self.headers,
        )
        self.assertEqual(toggle_response.status_code, 200)
        self.assertTrue(toggle_response.get_json()["task"]["completed"])

        delete_response = self.client.delete(
            f"/api/tasks/{task_id}",
            headers=self.headers,
        )
        self.assertEqual(delete_response.status_code, 200)


if __name__ == "__main__":
    unittest.main()