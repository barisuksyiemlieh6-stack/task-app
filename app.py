from flask import Flask, render_template, request, redirect, session, url_for
import psycopg2
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)
app.secret_key = "your_secret_key_here"

def get_db_connection():
    conn = psycopg2.connect(
        host="localhost",
        port="5432",
        database="todo_list",
        user="postgres",
        password="post"   # ← CHANGE to your PostgreSQL password!
    )
    return conn

def create_tables():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_details (
            id SERIAL PRIMARY KEY,
            fullname VARCHAR(100) NOT NULL,
            email VARCHAR(100) UNIQUE NOT NULL,
            password VARCHAR(255) NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS todos (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES user_details(id),
            title VARCHAR(200) NOT NULL,
            description TEXT,
            status VARCHAR(20) DEFAULT 'Pending',
            created_date DATE DEFAULT CURRENT_DATE,
            due_date DATE
        )
    """)
    conn.commit()
    cursor.close()
    conn.close()
    print("Tables created successfully!")

@app.route("/")
def home():
    return render_template("index.html")   # Homepage

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        fullname = request.form["fullname"]
        email = request.form["email"]
        password = request.form["password"]
        confirm = request.form["confirm_password"]
        if password != confirm:
            return "Passwords do not match!"
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM user_details WHERE email = %s", (email,))
        if cursor.fetchone():
            cursor.close()
            conn.close()
            return "Email already registered!"
        hashed = generate_password_hash(password)
        cursor.execute(
            "INSERT INTO user_details (fullname, email, password) VALUES (%s, %s, %s)",
            (fullname, email, hashed)
        )
        conn.commit()
        cursor.close()
        conn.close()
        return redirect(url_for("login") + "?success=1")
    return render_template("Register.html")   # ← Your filename

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM user_details WHERE email = %s", (email,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        if user and check_password_hash(user[3], password):
            session["user_id"] = user[0]
            session["fullname"] = user[1]
            session["email"] = user[2]
            return redirect(url_for("dashboard"))
        return "Invalid email or password!"
    return render_template("Login.html")   # ← Your filename

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM todos WHERE user_id = %s AND status = 'Pending'", (session["user_id"],))
    pending = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM todos WHERE user_id = %s AND status = 'Complete'", (session["user_id"],))
    completed = cursor.fetchone()[0]
    cursor.execute(
        "SELECT id, title, description, status, due_date FROM todos WHERE user_id = %s ORDER BY created_date DESC",
        (session["user_id"],)
    )
    todos = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template(
        "Dashboard.html",   # ← Your filename
        fullname=session["fullname"],
        pending_count=pending,
        completed_count=completed,
        todos=todos
    )

@app.route("/add_todo", methods=["GET", "POST"])
def add_todo():
    if "user_id" not in session:
        return redirect(url_for("login"))
    if request.method == "POST":
        title = request.form["title"]
        description = request.form.get("description", "")
        due_date = request.form.get("due_date") or None
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO todos (user_id, title, description, due_date) VALUES (%s, %s, %s, %s)",
            (session["user_id"], title, description, due_date)
        )
        conn.commit()
        cursor.close()
        conn.close()
        return redirect(url_for("dashboard"))
    return render_template("Add_Task.html")   # ← Your filename

@app.route("/edit_todo/<int:id>", methods=["GET", "POST"])
def edit_todo(id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, title, description, status, due_date FROM todos WHERE id = %s AND user_id = %s",
        (id, session["user_id"])
    )
    todo = cursor.fetchone()
    if not todo:
        cursor.close()
        conn.close()
        return "Todo not found!"
    if request.method == "POST":
        title = request.form["title"]
        description = request.form.get("description", "")
        status = request.form["status"]
        due_date = request.form.get("due_date") or None
        cursor.execute(
            "UPDATE todos SET title = %s, description = %s, status = %s, due_date = %s WHERE id = %s AND user_id = %s",
            (title, description, status, due_date, id, session["user_id"])
        )
        conn.commit()
        cursor.close()
        conn.close()
        return redirect(url_for("dashboard"))
    cursor.close()
    conn.close()
    return render_template("Edit_Task.html", todo=todo)   # ← Your filename

@app.route("/delete_todo/<int:id>")
def delete_todo(id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM todos WHERE id = %s AND user_id = %s",
        (id, session["user_id"])
    )
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for("dashboard"))

@app.route("/toggle_todo/<int:id>")
def toggle_todo(id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT status FROM todos WHERE id = %s AND user_id = %s",
        (id, session["user_id"])
    )
    row = cursor.fetchone()
    if row:
        new_status = "Complete" if row[0] == "Pending" else "Pending"
        cursor.execute(
            "UPDATE todos SET status = %s WHERE id = %s AND user_id = %s",
            (new_status, id, session["user_id"])
        )
        conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for("dashboard"))

if __name__ == "__main__":
    create_tables()
    app.run(debug=True)