
from flask import Flask, render_template, request, redirect, url_for
import sqlite3
import os

app = Flask(__name__)

DB_PATH = os.environ.get("TODO_DB_PATH", "/app/data/todos.db")


def get_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS todos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task TEXT NOT NULL,
                completed INTEGER NOT NULL DEFAULT 0
            )
        """)


@app.route("/")
def index():
    with get_db() as conn:
        todos = conn.execute(
            "SELECT * FROM todos ORDER BY id DESC"
        ).fetchall()
    return render_template("index.html", todos=todos)


@app.route("/add", methods=["POST"])
def add():
    task = request.form.get("task", "").strip()
    if task:
        with get_db() as conn:
            conn.execute(
                "INSERT INTO todos (task) VALUES (?)", (task,)
            )
    return redirect(url_for("index"))


@app.route("/toggle/<int:todo_id>", methods=["POST"])
def toggle(todo_id):
    with get_db() as conn:
        conn.execute("""
            UPDATE todos
            SET completed = CASE WHEN completed = 0 THEN 1 ELSE 0 END
            WHERE id = ?
        """, (todo_id,))
    return redirect(url_for("index"))


@app.route("/delete/<int:todo_id>", methods=["POST"])
def delete(todo_id):
    with get_db() as conn:
        conn.execute("DELETE FROM todos WHERE id = ?", (todo_id,))
    return redirect(url_for("index"))


init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

