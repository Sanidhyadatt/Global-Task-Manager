import unittest

from app import app, core_tasks_col


class AssignmentApiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.testing = True
        cls.client = app.test_client()

    def setUp(self):
        core_tasks_col.delete_many({})

    def test_create_list_patch_delete_task(self):
        create_res = self.client.post("/tasks", json={"title": "Assignment task"})
        self.assertEqual(create_res.status_code, 201)
        created = create_res.get_json()

        self.assertIn("id", created)
        self.assertEqual(created["title"], "Assignment task")
        self.assertFalse(created["completed"])
        self.assertIn("createdAt", created)

        list_res = self.client.get("/tasks")
        self.assertEqual(list_res.status_code, 200)
        self.assertEqual(len(list_res.get_json()), 1)

        task_id = created["id"]
        patch_res = self.client.patch(f"/tasks/{task_id}", json={"completed": True})
        self.assertEqual(patch_res.status_code, 200)
        patched = patch_res.get_json()
        self.assertTrue(patched["completed"])

        delete_res = self.client.delete(f"/tasks/{task_id}")
        self.assertEqual(delete_res.status_code, 200)

        list_after_delete = self.client.get("/tasks")
        self.assertEqual(list_after_delete.status_code, 200)
        self.assertEqual(len(list_after_delete.get_json()), 0)

    def test_validation_on_create(self):
        response = self.client.post("/tasks", json={"title": "   "})
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.get_json())


if __name__ == "__main__":
    unittest.main()
