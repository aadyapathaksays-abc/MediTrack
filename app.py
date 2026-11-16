from datetime import date
from flask import Flask, flash, redirect, render_template, request, url_for
from pathlib import Path
import sqlite3

app = Flask(__name__)
app.secret_key = "your_secret_key_here"  # Required for flashing messages

# Database setup using absolute path
DB_PATH = Path(__file__).parent / "meditrack.db"


def connect():
  conn = sqlite3.connect(DB_PATH)
  conn.row_factory = sqlite3.Row
  return conn


def init_db():
  with connect() as db:
    db.execute("""
            CREATE TABLE IF NOT EXISTS medicines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                dosage TEXT NOT NULL,
                instructions TEXT,
                time TEXT NOT NULL,
                start_date TEXT NOT NULL,
                end_date TEXT
            )
        """)
    db.execute("""
            CREATE TABLE IF NOT EXISTS dose_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                medicine_id INTEGER NOT NULL,
                status TEXT NOT NULL,
                log_date TEXT NOT NULL,
                FOREIGN KEY (medicine_id) REFERENCES medicines (id)
            )
        """)
    db.commit()


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
        "INSERT INTO medicines (name, dosage, instructions, time, start_date,"
        " end_date) VALUES (?, ?, ?, ?, ?, ?)",
        (name, dosage, instructions, time, start_date, end_date),
    )
    db.commit()
  flash("Medicine added successfully!", "success")
  return redirect(url_for("index"))


@app.route("/log/<int:medicine_id>/<status>")
def log_dose(medicine_id, status):
  today_str = str(date.today())
  with connect() as db:
    db.execute(
        "INSERT INTO dose_logs (medicine_id, status, log_date) VALUES (?, ?,"
        " ?)",
        (medicine_id, status, today_str),
    )
    db.commit()
  flash(f"Dose marked as {status}!", "success")
  return redirect(url_for("index"))


if __name__ == "__main__":
  with app.app_context():
    init_db()
  app.run(debug=True)