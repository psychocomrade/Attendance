from flask import Flask, render_template, request, redirect, url_for
import sqlite3
from datetime import date

app = Flask(__name__)
DB_FILE = "workers.db"

# --- Database setup ---
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS workers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    role TEXT NOT NULL
                )''')
    c.execute('''CREATE TABLE IF NOT EXISTS attendance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    worker_id INTEGER,
                    att_date TEXT,
                    present INTEGER,
                    overtime INTEGER,
                    ot_hours REAL,
                    FOREIGN KEY(worker_id) REFERENCES workers(id)
                )''')
    conn.commit()
    conn.close()

init_db()

# --- Helpers ---
def get_today():
    return date.today().strftime("%d-%m-%Y")

# --- Routes ---
@app.route("/", methods=["GET", "POST"])
def attendance():
    today = get_today()
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT * FROM workers")
    workers = c.fetchall()
    conn.close()

    if request.method == "POST":
        ot_enabled = True if request.form.get("enable_ot") else False
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        att_date = request.form.get("date")

        for worker_id in request.form.getlist("worker_id"):
            present = 1 if request.form.get(f"present_{worker_id}") else 0
            overtime = 1 if ot_enabled and request.form.get(f"ot_{worker_id}") else 0
            ot_hours = float(request.form.get(f"hours_{worker_id}")) if overtime else 0

            c.execute("INSERT INTO attendance (worker_id, att_date, present, overtime, ot_hours) VALUES (?, ?, ?, ?, ?)",
                      (worker_id, att_date, present, overtime, ot_hours))
        conn.commit()

        # Generate WhatsApp-friendly summary
        c.execute("SELECT w.name, w.role, a.present, a.overtime, a.ot_hours \
                   FROM attendance a JOIN workers w ON a.worker_id = w.id \
                   WHERE a.att_date = ?", (att_date,))
        records = c.fetchall()
        conn.close()

        role_emoji = {
            "Mason": "👷",
            "Helper": "🛠️",
            "JCB Operator": "🚜",
            "JCB Helper": "👨‍🦯",
            "Driver": "🚛",
            "Ajax Operator": "🚚"
        }

        summary = f"📅 Attendance: {att_date}\n"
        for name, role, present, overtime, ot_hours in records:
            if present:
                if overtime:
                    summary += f"{role_emoji.get(role,'👤')} {role}: {name} ✅ OT: {ot_hours}h\n"
                else:
                    summary += f"{role_emoji.get(role,'👤')} {role}: {name} ✅\n"
            else:
                summary += f"{role_emoji.get(role,'👤')} {role}: {name} ❌\n"

        return render_template("summary.html", summary=summary)

    return render_template("attendance.html", workers=workers, today=today)

@app.route("/onboard", methods=["GET", "POST"])
def onboard():
    roles = ["Mason", "Helper", "JCB Operator", "JCB Helper", "Driver", "Ajax Operator"]
    if request.method == "POST":
        name = request.form["name"]
        role = request.form["role"]
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("INSERT INTO workers (name, role) VALUES (?, ?)", (name, role))
        conn.commit()
        conn.close()
        return redirect(url_for("onboard"))

    return render_template("onboard.html", roles=roles)

@app.route("/reset")
def reset_attendance():
    today = get_today()
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM attendance WHERE att_date = ?", (today,))
    conn.commit()
    conn.close()
    return redirect(url_for("attendance"))

@app.route("/delete_worker", methods=["POST"])
def delete_worker():
    worker_id = request.form.get("worker_id")
    if worker_id:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        # Delete attendance records first
        c.execute("DELETE FROM attendance WHERE worker_id = ?", (worker_id,))
        # Then delete worker
        c.execute("DELETE FROM workers WHERE id = ?", (worker_id,))
        conn.commit()
        conn.close()
    return redirect(url_for("attendance"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

