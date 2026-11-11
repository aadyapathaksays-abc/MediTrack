"""MediTrack - Flask backend. Run with: python app.py"""
import sqlite3
from datetime import date, datetime, timedelta
from flask import Flask, g, jsonify, request

app = Flask(__name__, static_folder="static", static_url_path="/static")
DB = "meditrack.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS profiles(
  id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS medicines(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  profile_id INTEGER NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
  name TEXT NOT NULL, dosage TEXT NOT NULL, frequency INTEGER NOT NULL,
  times TEXT NOT NULL,              -- e.g. "09:00,21:00"
  start_date TEXT NOT NULL, end_date TEXT NOT NULL, instructions TEXT DEFAULT '');
CREATE TABLE IF NOT EXISTS doses(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  medicine_id INTEGER NOT NULL REFERENCES medicines(id) ON DELETE CASCADE,
  profile_id INTEGER NOT NULL, date TEXT NOT NULL, time TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'upcoming',   -- upcoming | taken | skipped | missed
  confirmed_at TEXT,
  UNIQUE(medicine_id, date, time));          -- prevents duplicate doses
"""


def db():
    if "db" not in g:
        g.db = sqlite3.connect(DB)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys=ON")
    return g.db


@app.teardown_appcontext
def close_db(_):
    conn = g.pop("db", None)
    if conn:
        conn.close()


def init_db():
    conn = sqlite3.connect(DB)
    conn.executescript(SCHEMA)
    if not conn.execute("SELECT 1 FROM profiles").fetchone():
        conn.execute("INSERT INTO profiles(name) VALUES('Me')")
    conn.commit()
    conn.close()


def sync_doses():
    """Create dose records from each medicine's schedule (start date up to today),
    then flag overdue upcoming doses as missed."""
    conn = db()
    today = date.today()
    for m in conn.execute("SELECT * FROM medicines").fetchall():
        day, last = date.fromisoformat(m["start_date"]), min(date.fromisoformat(m["end_date"]), today)
        while day <= last:
            for t in m["times"].split(","):
                conn.execute("INSERT OR IGNORE INTO doses(medicine_id,profile_id,date,time) VALUES(?,?,?,?)",
                             (m["id"], m["profile_id"], day.isoformat(), t))
            day += timedelta(days=1)
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    conn.execute("UPDATE doses SET status='missed' WHERE status='upcoming' AND date||' '||time < ?", (now,))
    conn.commit()


@app.before_request
def before():
    if request.path.startswith("/api"):
        sync_doses()


@app.route("/")
def index():
    return app.send_static_file("index.html")


# ---------- Profiles ----------
@app.get("/api/profiles")
def profiles():
    rows = db().execute("""SELECT p.id, p.name,
      (SELECT COUNT(*) FROM doses d WHERE d.profile_id=p.id AND d.status='taken') AS taken,
      (SELECT COUNT(*) FROM doses d WHERE d.profile_id=p.id AND d.status='upcoming') AS pending,
      (SELECT COUNT(*) FROM doses d WHERE d.profile_id=p.id AND d.status='missed') AS missed
      FROM profiles p ORDER BY p.id""").fetchall()
    return jsonify([dict(r) for r in rows])


@app.post("/api/profiles")
def add_profile():
    name = (request.json.get("name") or "").strip()
    if not name:
        return jsonify(error="Enter a name for the profile."), 400
    cur = db().execute("INSERT INTO profiles(name) VALUES(?)", (name,))
    db().commit()
    return jsonify(id=cur.lastrowid), 201


# ---------- Medicines ----------
def read_medicine(data):
    """Validate form data. Returns (values, error)."""
    name, dosage = (data.get("name") or "").strip(), (data.get("dosage") or "").strip()
    times, start, end = data.get("times") or [], data.get("start_date"), data.get("end_date")
    freq = int(data.get("frequency") or 0)
    if not name or not dosage:
        return None, "Medicine name and dosage are required."
    if freq not in (1, 2, 3) or len(times) != freq or len(set(times)) != freq or not all(times):
        return None, "Enter a different time for each dose."
    if not start or not end or end < start:
        return None, "The end date must be on or after the start date."
    return (name, dosage, freq, ",".join(sorted(times)), start, end, (data.get("instructions") or "").strip()), None


def med_json(r):
    d = dict(r)
    d["times"] = d["times"].split(",")
    return d


@app.get("/api/medicines")
def medicines():
    rows = db().execute("SELECT * FROM medicines WHERE profile_id=? ORDER BY name", (request.args["profile"],))
    return jsonify([med_json(r) for r in rows])


@app.post("/api/medicines")
def add_medicine():
    vals, err = read_medicine(request.json)
    if err:
        return jsonify(error=err), 400
    db().execute("""INSERT INTO medicines(profile_id,name,dosage,frequency,times,start_date,end_date,instructions)
                    VALUES(?,?,?,?,?,?,?,?)""", (request.json["profile_id"],) + vals)
    db().commit()
    return jsonify(ok=True), 201


@app.put("/api/medicines/<int:mid>")
def edit_medicine(mid):
    vals, err = read_medicine(request.json)
    if err:
        return jsonify(error=err), 400
    conn = db()
    conn.execute("""UPDATE medicines SET name=?,dosage=?,frequency=?,times=?,start_date=?,end_date=?,instructions=?
                    WHERE id=?""", vals + (mid,))
    # Re-plan: drop unconfirmed doses so they are regenerated from the new schedule.
    # Taken/skipped records are kept as history.
    conn.execute("DELETE FROM doses WHERE medicine_id=? AND status IN ('upcoming','missed')", (mid,))
    conn.commit()
    return jsonify(ok=True)


@app.delete("/api/medicines/<int:mid>")
def delete_medicine(mid):
    db().execute("DELETE FROM medicines WHERE id=?", (mid,))  # doses removed by CASCADE
    db().commit()
    return jsonify(ok=True)


# ---------- Doses ----------
@app.get("/api/doses")
def doses():
    a = request.args
    rows = db().execute("""SELECT d.id,d.date,d.time,d.status,d.confirmed_at,m.name,m.dosage,m.instructions
        FROM doses d JOIN medicines m ON m.id=d.medicine_id
        WHERE d.profile_id=? AND d.date BETWEEN ? AND ? ORDER BY d.date,d.time,m.name""",
                       (a["profile"], a["start"], a["end"]))
    return jsonify([dict(r) for r in rows])


@app.post("/api/doses/<int:did>")
def mark_dose(did):
    status = request.json.get("status")
    if status not in ("taken", "skipped"):
        return jsonify(error="Status must be taken or skipped."), 400
    db().execute("UPDATE doses SET status=?, confirmed_at=? WHERE id=?",
                 (status, datetime.now().isoformat(timespec="seconds"), did))
    db().commit()
    return jsonify(ok=True)


# ---------- Dashboard ----------
@app.get("/api/dashboard")
def dashboard():
    pid, today = request.args["profile"], date.today()
    conn = db()
    active = conn.execute("SELECT COUNT(*) FROM medicines WHERE profile_id=? AND start_date<=? AND end_date>=?",
                          (pid, today.isoformat(), today.isoformat())).fetchone()[0]
    todays = conn.execute("""SELECT d.id,d.time,d.status,m.name,m.dosage FROM doses d JOIN medicines m ON m.id=d.medicine_id
                             WHERE d.profile_id=? AND d.date=? ORDER BY d.time""", (pid, today.isoformat())).fetchall()
    week = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        r = conn.execute("SELECT COUNT(*), SUM(status='taken') FROM doses WHERE profile_id=? AND date=?",
                         (pid, day.isoformat())).fetchone()
        week.append({"date": day.isoformat(), "label": day.strftime("%a"), "total": r[0], "taken": r[1] or 0})
    total, taken = sum(w["total"] for w in week), sum(w["taken"] for w in week)
    for w in week:
        w["pct"] = round(w["taken"] / w["total"] * 100) if w["total"] else 0
    return jsonify(active=active, today_total=len(todays),
                   today_done=sum(r["status"] == "taken" for r in todays),
                   today_pending=sum(r["status"] == "upcoming" for r in todays),
                   upcoming=[dict(r) for r in todays if r["status"] == "upcoming"],
                   adherence=round(taken / total * 100) if total else 0, week=week)


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
