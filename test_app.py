import os
import tempfile

_test_dir = tempfile.TemporaryDirectory()
os.environ["TODO_DB_PATH"] = os.path.join(
    _test_dir.name, "test_todos.db"
)

from app import app, get_db

app.config["TESTING"] = True


def test_home_page():
    with app.test_client() as client:
        response = client.get("/")
        assert response.status_code == 200
        assert b"My Todo List" in response.data


def test_add_task():
    with app.test_client() as client:
        response = client.post(
            "/add",
            data={"task": "Learn Jenkins"},
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b"Learn Jenkins" in response.data


def test_complete_task():
    with app.test_client() as client:
        client.post("/add", data={"task": "Test deployment"})

        with get_db() as conn:
            task_id = conn.execute(
                "SELECT id FROM todos WHERE task = ?",
                ("Test deployment",),
            ).fetchone()["id"]

        response = client.post(
            f"/toggle/{task_id}", follow_redirects=True
        )
        assert response.status_code == 200

        with get_db() as conn:
            task = conn.execute(
                "SELECT completed FROM todos WHERE id = ?",
                (task_id,),
            ).fetchone()
            assert task["completed"] == 1


def test_delete_task():
    with app.test_client() as client:
        client.post("/add", data={"task": "Delete me"})

        with get_db() as conn:
            task_id = conn.execute(
                "SELECT id FROM todos WHERE task = ?",
                ("Delete me",),
            ).fetchone()["id"]

        response = client.post(
            f"/delete/{task_id}", follow_redirects=True
        )
        assert response.status_code == 200
        assert b"Delete me" not in response.data
