from functools import wraps
from io import BytesIO, StringIO
import csv
import os
from pathlib import Path

from flask import Flask, redirect, render_template, request, send_file, session, url_for
from openpyxl import Workbook
from werkzeug.security import check_password_hash

from db import current_url, get_session, switch_database, test_url
from models import User
from store import SPECIALTIES, hospital
from triage_engine import PRIORITIES

ROOT = Path(__file__).resolve().parent
SECRET_FILE = ROOT / "secret.key"
if SECRET_FILE.exists():
    secret = SECRET_FILE.read_text(encoding="utf-8").strip()
else:
    secret = os.urandom(24).hex()
    SECRET_FILE.write_text(secret, encoding="utf-8")

app = Flask(__name__)
app.secret_key = secret

SYMPTOMS = [
    "chest pain",
    "shortness of breath",
    "stroke signs",
    "seizure",
    "severe headache",
    "confusion",
    "bleeding",
    "uncontrolled bleeding",
    "trauma / accident",
    "fracture / fall",
    "joint or bone pain",
    "abdominal pain",
    "allergic reaction",
    "fever",
    "vomiting",
    "pregnancy / labour",
    "wound / cut",
    "burns",
    "cough / cold",
    "back pain",
    "heart palpitations",
]

EXPORT_COLUMNS = [
    ("id", "Patient ID"),
    ("name", "Name"),
    ("age", "Age"),
    ("sex", "Sex"),
    ("phone", "Phone"),
    ("status", "Status"),
    ("priority", "Priority"),
    ("priority_label", "Priority label"),
    ("ai_priority", "AI priority"),
    ("specialty", "Department"),
    ("doctor_name", "Doctor"),
    ("room", "Room"),
    ("arrival", "Arrival"),
    ("symptoms", "Symptoms"),
    ("created_at", "Registered"),
    ("care_start", "Care started"),
    ("completed_at", "Discharged"),
    ("review_notes", "Review notes"),
    ("reviewed_by", "Reviewed by"),
]


def current_user() -> dict | None:
    return session.get("user")


def is_staff() -> bool:
    user = current_user()
    return bool(user and user.get("role") in {"nurse", "admin"})


def is_admin() -> bool:
    user = current_user()
    return bool(user and user.get("role") == "admin")


def can_override() -> bool:
    return is_staff()


@app.context_processor
def inject_auth():
    return {
        "user": current_user(),
        "is_staff": is_staff(),
        "is_admin": is_admin(),
        "can_override": can_override(),
        "db_url": current_url(),
        "specialties": SPECIALTIES,
    }


def staff_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not is_staff():
            return redirect(
                url_for(
                    "login",
                    next=request.path,
                    msg="Nurse or admin login is required.",
                    kind="warn",
                )
            )
        return fn(*args, **kwargs)

    return wrapper


def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not is_admin():
            return redirect(
                url_for(
                    "login",
                    next=request.path,
                    msg="Admin login is required for this action.",
                    kind="warn",
                )
            )
        return fn(*args, **kwargs)

    return wrapper


def _home(**kwargs):
    kwargs.setdefault("view", request.args.get("view", "intake"))
    return redirect(url_for("home", **kwargs))


@app.route("/")
def home():
    view = request.args.get("view", "intake")
    if view in {"review", "waitlist", "doctors", "records"} and not is_staff():
        return redirect(
            url_for(
                "login",
                next=f"/?view={view}",
                msg="Sign in as nurse or admin to continue.",
                kind="warn",
            )
        )
    if view == "settings" and not is_admin():
        if is_staff():
            return redirect(
                url_for(
                    "home",
                    view="records",
                    msg="Only an admin can connect a personal database.",
                    kind="warn",
                )
            )
        return redirect(
            url_for("login", next="/?view=settings", msg="Admin login is required.", kind="warn")
        )
    flash = request.args.get("msg")
    kind = request.args.get("kind", "ok")
    return render_template(
        "index.html",
        view=view,
        data=hospital.snapshot(),
        symptoms=SYMPTOMS,
        priorities=PRIORITIES,
        flash=flash,
        kind=kind,
    )


@app.route("/login", methods=["GET", "POST"])
def login():
    flash = request.args.get("msg")
    kind = request.args.get("kind", "ok")
    nxt = request.values.get("next") or "/?view=review"
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""
        db = get_session()
        try:
            account = db.query(User).filter_by(username=username).first()
        finally:
            db.close()
        if not account or not check_password_hash(account.password_hash, password):
            return render_template(
                "login.html",
                flash="Wrong username or password.",
                kind="err",
                next=nxt,
            )
        session["user"] = {
            "username": account.username,
            "role": account.role,
            "full_name": account.full_name,
        }
        target = nxt if nxt.startswith("/") else url_for("home", view="review")
        return redirect(target)
    return render_template("login.html", flash=flash, kind=kind, next=nxt)


@app.get("/logout")
def logout():
    session.clear()
    return _home(view="intake", msg="Signed out.", kind="ok")


@app.post("/intake")
def intake():
    form = request.form.to_dict()
    form["symptoms"] = request.form.getlist("symptoms")
    form["pregnancy"] = request.form.get("pregnancy") == "on"
    patient = hospital.intake(form)
    return _home(
        view="review" if is_staff() else "intake",
        msg=f"AI triage complete for {patient['name']} ({patient['id']}). A nurse must confirm priority.",
        kind="ok",
    )


@app.post("/review/<patient_id>")
@staff_required
def review(patient_id: str):
    if not can_override():
        return _home(view="review", msg="Only a logged-in nurse or admin can override AI triage.", kind="err")
    action = request.form.get("action")
    approve = action == "approve"
    user = current_user() or {}
    patient = hospital.review(
        patient_id,
        int(request.form.get("priority") or 3),
        request.form.get("review_notes") or "",
        approve,
        reviewed_by=user.get("username") or "",
    )
    if not patient:
        return _home(view="review", msg="Patient not found or already processed.", kind="err")
    override = patient.get("ai_priority") and patient.get("priority") != patient.get("ai_priority")
    if approve:
        assigned = patient.get("doctor_name") or "the next available doctor"
        extra = " AI suggestion was overridden." if override else ""
        return _home(
            view="waitlist",
            msg=f"{patient['name']} added to waitlist as {patient['priority_label']}. Assigned to {assigned}.{extra}",
            kind="ok",
        )
    return _home(view="review", msg=f"{patient['name']} was not approved for the waitlist.", kind="warn")


@app.post("/remove/<patient_id>")
@staff_required
def remove(patient_id: str):
    ok = hospital.remove_patient(patient_id)
    msg = "Patient removed from the list." if ok else "Could not remove this patient."
    return _home(view="waitlist", msg=msg, kind="ok" if ok else "err")


@app.post("/complete/<patient_id>")
@staff_required
def complete(patient_id: str):
    ok = hospital.complete_care(patient_id)
    msg = "Visit completed. Patient moved to discharged records." if ok else "Could not complete this visit."
    return _home(view="records", msg=msg, kind="ok" if ok else "err")


@app.post("/waitlist/add/<patient_id>")
@staff_required
def add_to_waitlist(patient_id: str):
    patient = hospital.restore_to_waitlist(patient_id)
    if not patient:
        return _home(view="waitlist", msg="Patient must be triaged before adding.", kind="err")
    return _home(view="waitlist", msg=f"{patient['name']} is on the waitlist.", kind="ok")


@app.post("/doctors/add")
@staff_required
def add_doctor():
    name = (request.form.get("name") or "").strip()
    specialty = (request.form.get("specialty") or "").strip()
    room = (request.form.get("room") or "").strip()
    if not name:
        return _home(view="doctors", msg="Doctor name is required.", kind="err")
    doctor = hospital.add_doctor(name, specialty, room)
    return _home(view="doctors", msg=f"{doctor['name']} added to the doctor list.", kind="ok")


@app.post("/doctors/remove/<doctor_id>")
@staff_required
def remove_doctor(doctor_id: str):
    err = hospital.remove_doctor(doctor_id)
    if err:
        return _home(view="doctors", msg=err, kind="err")
    return _home(view="doctors", msg="Doctor removed.", kind="ok")


@app.post("/settings/database")
@admin_required
def connect_database():
    url = (request.form.get("database_url") or "").strip()
    copy_data = request.form.get("copy_data") == "on"
    if not url:
        return _home(view="settings", msg="Enter a database URL.", kind="err")
    error = test_url(url)
    if error:
        return _home(view="settings", msg=f"Could not connect: {error}", kind="err")
    try:
        switch_database(url, copy_data=copy_data)
    except Exception as exc:
        return _home(view="settings", msg=f"Connected but setup failed: {exc}", kind="err")
    return _home(view="settings", msg="Personal database connected. New records will be saved there.", kind="ok")


@app.get("/export/<kind>.<fmt>")
@staff_required
def export_records(kind: str, fmt: str):
    if kind not in {"in_care", "discharged", "all"}:
        return _home(view="records", msg="Unknown export type.", kind="err")
    if fmt not in {"csv", "xlsx"}:
        return _home(view="records", msg="Use csv or xlsx.", kind="err")
    rows = hospital.records(kind)
    filename = f"patients_{kind}.{fmt}"
    if fmt == "csv":
        buf = StringIO()
        writer = csv.writer(buf)
        writer.writerow([label for _, label in EXPORT_COLUMNS])
        for row in rows:
            writer.writerow([_cell(row, key) for key, _ in EXPORT_COLUMNS])
        data = BytesIO(buf.getvalue().encode("utf-8-sig"))
        data.seek(0)
        return send_file(data, as_attachment=True, download_name=filename, mimetype="text/csv")
    book = Workbook()
    sheet = book.active
    sheet.title = kind
    sheet.append([label for _, label in EXPORT_COLUMNS])
    for row in rows:
        sheet.append([_cell(row, key) for key, _ in EXPORT_COLUMNS])
    out = BytesIO()
    book.save(out)
    out.seek(0)
    return send_file(
        out,
        as_attachment=True,
        download_name=filename,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


def _cell(row: dict, key: str):
    value = row.get(key)
    if key == "status":
        return {"in_care": "In treatment", "completed": "Discharged"}.get(value, value or "")
    if isinstance(value, list):
        return ", ".join(str(v) for v in value)
    if value is None:
        return ""
    return value


if __name__ == "__main__":
    app.run(debug=True, port=5000)
