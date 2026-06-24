from flask import Flask, render_template, request, redirect, session, flash, url_for
from werkzeug.utils import secure_filename
import sqlite3
import os
import base64
import uuid
from datetime import datetime

app = Flask(__name__)

app.secret_key = "CHANGE_THIS_SECRET_KEY"

# Upload Folder
UPLOAD_FOLDER = "static/uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

CAPTURE_FOLDER = "static/captures"

os.makedirs(CAPTURE_FOLDER, exist_ok=True)

DOCUMENT_FOLDER = "static/documents"

os.makedirs(DOCUMENT_FOLDER, exist_ok=True)


# -----------------------------
# DATABASE
# -----------------------------
def get_db():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn


def init_db():

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users(

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        name TEXT NOT NULL,
        mobile TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,

        photo TEXT,
        live_photo TEXT,

        roll_number TEXT,
        registration_number TEXT,

        exam_slip TEXT,
        affidavit TEXT,

        status TEXT DEFAULT 'Pending',

        created_at TEXT

    )
    """)

    conn.commit()
    conn.close()


init_db()


# -----------------------------
# HOME
# -----------------------------
@app.route("/")
def home():
    return redirect("/login")


# -----------------------------
# REGISTER
# -----------------------------
@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form["name"]
        mobile = request.form["mobile"]
        email = request.form["email"]
        password = request.form["password"]

        conn = get_db()
        cur = conn.cursor()

        try:

            cur.execute("""
            INSERT INTO users
            (
                name,
                mobile,
                email,
                password,
                created_at
            )
            VALUES (?,?,?,?,?)
            """,
            (
                name,
                mobile,
                email,
                password,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ))

            conn.commit()

            flash("Registration Successful")
            return redirect("/login")

        except Exception as e:

            flash("Email or Mobile already exists")

        finally:
            conn.close()

    return render_template("register.html")


# -----------------------------
# LOGIN
# -----------------------------
@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        # Admin Login
        if email == "admin@admin.com" and password == "admin123":

            session["admin"] = True
            return redirect("/admin")

        conn = get_db()
        cur = conn.cursor()

        cur.execute("""
        SELECT * FROM users
        WHERE email=? AND password=?
        """, (email, password))

        user = cur.fetchone()

        conn.close()

        if user:

            session["user_id"] = user["id"]
            return redirect("/dashboard")

        flash("Invalid Email or Password")

    return render_template("login.html")


# -----------------------------
# DASHBOARD
# -----------------------------
@app.route("/dashboard")
def dashboard():

    if "user_id" not in session:
        return redirect("/login")

    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        "SELECT * FROM users WHERE id=?",
        (session["user_id"],)
    )

    user = cur.fetchone()

    conn.close()

    return render_template(
        "dashboard.html",
        user=user
    )


# -----------------------------
# PHOTO UPLOAD
# -----------------------------
@app.route("/upload_photo", methods=["POST"])
def upload_photo():

    if "user_id" not in session:
        return redirect("/login")

    photo = request.files["photo"]

    if photo.filename == "":
        flash("Select Photo")
        return redirect("/dashboard")

    filename = secure_filename(photo.filename)

    filepath = os.path.join(
        app.config["UPLOAD_FOLDER"],
        filename
    )

    photo.save(filepath)

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
    UPDATE users
    SET photo=?
    WHERE id=?
    """,
    (
        filename,
        session["user_id"]
    ))

    conn.commit()
    conn.close()

    flash("Photo Uploaded Successfully")

    return redirect("/dashboard")


@app.route("/save_capture", methods=["POST"])
def save_capture():

    if "user_id" not in session:
        return {"status":"error"}

    image_data = request.form["image"]

    image_data = image_data.split(",")[1]

    image_bytes = base64.b64decode(image_data)

    filename = str(uuid.uuid4()) + ".png"

    filepath = os.path.join(
        CAPTURE_FOLDER,
        filename
    )

    with open(filepath, "wb") as f:
        f.write(image_bytes)

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
    UPDATE users
    SET live_photo=?
    WHERE id=?
    """,
    (
        filename,
        session["user_id"]
    ))

    conn.commit()
    conn.close()

    return {"status":"success"}

@app.route("/save_exam_details", methods=["POST"])
def save_exam_details():

    if "user_id" not in session:
        return redirect("/login")

    roll_number = request.form["roll_number"]
    registration_number = request.form["registration_number"]

    exam_file = ""

    if "exam_slip" in request.files:

        file = request.files["exam_slip"]

        if file.filename != "":

            exam_file = secure_filename(file.filename)

            file.save(
                os.path.join(
                    DOCUMENT_FOLDER,
                    exam_file
                )
            )

    conn = get_db()
    cur = conn.cursor()

    if exam_file:

        cur.execute("""
        UPDATE users
        SET
        roll_number=?,
        regulation=?,
        exam_slip=?
        WHERE id=?
        """,
        (
            roll_number,
            regulation,
            exam_file,
            session["user_id"]
        ))

    else:

        cur.execute("""
        UPDATE users
        SET
        roll_number=?,
        regulation=?
        WHERE id=?
        """,
        (
            roll_number,
            regulation,
            session["user_id"]
        ))

    conn.commit()
    conn.close()

    flash("Details Saved Successfully")

    return redirect("/dashboard")

affidavit_file = ""

if "affidavit" in request.files:

    file = request.files["affidavit"]

    if file.filename != "":

        affidavit_file = secure_filename(file.filename)

        file.save(
            os.path.join(
                DOCUMENT_FOLDER,
                affidavit_file
            )
        )

# -----------------------------
# ADMIN PANEL
# -----------------------------
@app.route("/admin")
def admin():

    if "admin" not in session:
        return redirect("/login")

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
    SELECT * FROM users
    ORDER BY id DESC
    """)

    users = cur.fetchall()

    conn.close()

    return render_template(
        "admin.html",
        users=users
    )


    
@app.route("/approve_user/<int:user_id>")
def approve_user(user_id):

    if "admin" not in session:
        return redirect("/login")

    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        "UPDATE users SET status=? WHERE id=?",
        ("Approved", user_id)
    )

    conn.commit()
    conn.close()

    flash("User Approved Successfully")

    return redirect("/admin")


# -----------------------------
# DELETE USER
# -----------------------------
@app.route("/delete_user/<int:user_id>")
def delete_user(user_id):

    if "admin" not in session:
        return redirect("/login")

    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        "DELETE FROM users WHERE id=?",
        (user_id,)
    )

    conn.commit()
    conn.close()

    return redirect("/admin")

@app.route("/reject_user/<int:user_id>")
def reject_user(user_id):

    if "admin" not in session:
        return redirect("/login")

    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        "UPDATE users SET status=? WHERE id=?",
        ("Rejected", user_id)
    )

    conn.commit()
    conn.close()

    flash("User Rejected Successfully")

    return redirect("/admin")


# -----------------------------
# LOGOUT
# -----------------------------
@app.route("/logout")
def logout():

    session.clear()

    return redirect("/login")


# -----------------------------
# RUN
# -----------------------------
if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=8080,
        debug=True
    )
