from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
from datetime import date, datetime
from pathlib import Path

app = Flask(__name__)
app.secret_key = "change-this-secret-before-deployment"
DB = Path(__file__).with_name("meditrack.db")

def connect():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with connect() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS medicines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                dosage TEXT NOT NULL,
                instructions TEXT DEFAULT '',
                time TEXT NOT NULL,
                start_date TEXT NOT NULL,
                end_date TEXT DEFAULT ''
            )
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS dose_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                medicine_id INTEGER,
                status TEXT NOT NULL,
                date TEXT NOT NULL,
                FOREIGN KEY (medicine_id) REFERENCES medicines (id)
            )
        """)

@app.route("/")
def index():
    with connect() as db:
        medicines = db.execute("SELECT * FROM medicines").fetchall()
    return render_template("index.html", medicines=medicines)

@app.route("/add", methods=["POST"])
def add_medicine():
    name = request.form.get("name")
    dosage = request.form.get("dosage")
    instructions = request.form.get("instructions", "")
    time = request.form.get("time")
    start_date = request.form.get("start_date", str(date.today()))
    end_date = request.form.get("end_date", "")
    
    with connect() as db:
        db.execute(
            "INSERT INTO medicines (name, dosage, instructions, time, start_date, end_date) VALUES (?, ?, ?, ?, ?, ?)",
            (name, dosage, instructions, time, start_date, end_date)
        )
        db.commit()
    flash("Medicine added successfully!", "success")
    return redirect(url_for("index"))

@app.route("/log/<int:medicine_id>/<status>")
def log_dose(medicine_id, status):
    # your database logic here
    return redirect(url_for("index"))

if __name__ == "__main__":
    with app.app_context():
        init_db()
    app.run(debug=True)
