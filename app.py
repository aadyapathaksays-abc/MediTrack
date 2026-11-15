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
                end_date TEXT DEFAULT '',
                stock INTEGER NOT NULL DEFAULT 0,
                active INTEGER NOT NULL DEFAULT 1
            )
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS dose_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                medicine_id INTEGER NOT NULL,
                dose_date TEXT NOT NULL,
                dose_time TEXT NOT NULL,
                status TEXT NOT NULL,
                logged_at TEXT NOT NULL,
                FOREIGN KEY(medicine_id) REFERENCES medicines(id)
            )
        """)

@app.route("/")
def index():
    today = date.today().isoformat()
    with connect() as db:
        medicines = db.execute(
            "SELECT * FROM medicines WHERE active=1 ORDER BY time"
        ).fetchall()
        logs = db.execute("""
            SELECT l.*, m.name, m.dosage FROM dose_logs l
            JOIN medicines m ON m.id=l.medicine_id
            WHERE l.dose_date=? ORDER BY l.logged_at DESC
        """, (today,)).fetchall()
        taken_ids = {r["medicine_id"] for r in db.execute(
            "SELECT medicine_id FROM dose_logs WHERE dose_date=? AND status='Taken'",
            (today,)
        ).fetchall()}
        total = len(medicines)
        taken = len(taken_ids)
        low_stock = [m for m in medicines if m["stock"] <= 5]
    return render_template("index.html", medicines=medicines, logs=logs,
                           taken_ids=taken_ids, total=total, taken=taken,
                           low_stock=low_stock, today=date.today().strftime("%A, %d %B %Y"))

@app.route("/add", methods=["POST"])
def add_medicine():
    name = request.form.get("name", "").strip()
    dosage = request.form.get("dosage", "").strip()
    time = request.form.get("time", "").strip()
    start_date = request.form.get("start_date", "").strip()
    stock = request.form.get("stock", "0").strip()
    instructions = request.form.get("instructions", "").strip()
    end_date = request.form.get("end_date", "").strip()
    if not all([name, dosage, time, start_date]):
        flash("Please complete all required fields.", "error")
        return redirect(url_for("index"))
    try:
        stock_value = max(0, int(stock))
    except ValueError:
        flash("Stock must be a whole number.", "error")
        return redirect(url_for("index"))
    with connect() as db:
        db.execute("""
            INSERT INTO medicines(name,dosage,instructions,time,start_date,end_date,stock)
            VALUES(?,?,?,?,?,?,?)
        """, (name, dosage, instructions, time, start_date, end_date, stock_value))
    flash(f"{name} added to your schedule.", "success")
    return redirect(url_for("index"))

@app.route("/dose/<int:medicine_id>/<status>", methods=["POST"])
def log_dose(medicine_id, status):
    if status not in ("Taken", "Skipped"):
        flash("Invalid dose status.", "error")
        return redirect(url_for("index"))
    today = date.today().isoformat()
    now = datetime.now().strftime("%H:%M")
    with connect() as db:
        med = db.execute("SELECT * FROM medicines WHERE id=? AND active=1",
                         (medicine_id,)).fetchone()
        if not med:
            flash("Medicine not found.", "error")
            return redirect(url_for("index"))
        existing = db.execute("""
            SELECT id FROM dose_logs WHERE medicine_id=? AND dose_date=?
        """, (medicine_id, today)).fetchone()
        if existing:
            db.execute("UPDATE dose_logs SET status=?, dose_time=?, logged_at=? WHERE id=?",
                       (status, now, datetime.now().isoformat(timespec="seconds"), existing["id"]))
        else:
            db.execute("""
                INSERT INTO dose_logs(medicine_id,dose_date,dose_time,status,logged_at)
                VALUES(?,?,?,?,?)
            """, (medicine_id, today, now, status, datetime.now().isoformat(timespec="seconds")))
        if status == "Taken" and med["stock"] > 0:
            db.execute("UPDATE medicines SET stock=stock-1 WHERE id=?", (medicine_id,))
    flash(f"Dose marked as {status.lower()}.", "success")
    return redirect(url_for("index"))

@app.route("/delete/<int:medicine_id>", methods=["POST"])
def delete_medicine(medicine_id):
    with connect() as db:
        db.execute("UPDATE medicines SET active=0 WHERE id=?", (medicine_id,))
    flash("Medicine removed from your active schedule.", "success")
    return redirect(url_for("index"))

@app.route("/history")
def history():
    with connect() as db:
        logs = db.execute("""
            SELECT l.*, m.name, m.dosage FROM dose_logs l
            JOIN medicines m ON m.id=l.medicine_id
            ORDER BY l.dose_date DESC, l.logged_at DESC LIMIT 100
        """).fetchall()
    return render_template("history.html", logs=logs)

@app.route("/health")
def health():
    return {"status": "ok", "app": "MediTrack"}

# Ensures tables are created immediately when Gunicorn imports app on Render
init_db()

if __name__ == "__main__":
    app.run(debug=True)