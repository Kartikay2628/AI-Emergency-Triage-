"""Database engine, sessions, and connection switching."""

from __future__ import annotations

import json
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from werkzeug.security import generate_password_hash

from models import Base, Doctor, User

SEED_DOCTORS = [
    {"name": "Dr. Meera Sharma", "specialty": "Emergency", "room": "ER-1"},
    {"name": "Dr. Arjun Patel", "specialty": "Emergency", "room": "ER-2"},
    {"name": "Dr. Sarah Khan", "specialty": "Cardiology", "room": "C-1"},
    {"name": "Dr. Rohan Iyer", "specialty": "Neurology", "room": "N-1"},
    {"name": "Dr. Priya Nair", "specialty": "Orthopedics", "room": "OT-1"},
    {"name": "Dr. James Okonkwo", "specialty": "General Surgery", "room": "S-1"},
    {"name": "Dr. Ananya Gupta", "specialty": "Pediatrics", "room": "P-1"},
    {"name": "Dr. Leila Rahman", "specialty": "Obstetrics", "room": "L-1"},
    {"name": "Dr. Vikram Joshi", "specialty": "Internal Medicine", "room": "IM-1"},
]

ROOT = Path(__file__).resolve().parent
CONFIG_FILE = ROOT / "db_config.json"
JSON_STATE = ROOT / "hospital_state.json"
DEFAULT_URL = f"sqlite:///{(ROOT / 'hospital.db').as_posix()}"

engine: Engine | None = None
SessionLocal: sessionmaker[Session] | None = None


def load_url() -> str:
    if CONFIG_FILE.exists():
        data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        return data.get("database_url") or DEFAULT_URL
    return DEFAULT_URL


def save_url(url: str) -> None:
    CONFIG_FILE.write_text(json.dumps({"database_url": url}, indent=2), encoding="utf-8")


def init_engine(url: str | None = None) -> Engine:
    global engine, SessionLocal
    url = url or load_url()
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    engine = create_engine(url, future=True, connect_args=connect_args)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    Base.metadata.create_all(engine)
    _seed(engine)
    save_url(url)
    return engine


def get_session() -> Session:
    if SessionLocal is None:
        init_engine()
    assert SessionLocal is not None
    return SessionLocal()


@contextmanager
def session_scope():
    session = get_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def current_url() -> str:
    if engine is not None:
        return str(engine.url)
    return load_url()


def test_url(url: str) -> str | None:
    """Return None if the URL works, otherwise an error message."""
    try:
        connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
        test_engine = create_engine(url, future=True, connect_args=connect_args)
        with test_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        test_engine.dispose()
        return None
    except Exception as exc:
        return str(exc)


def switch_database(url: str, copy_data: bool = False) -> None:
    from sqlalchemy.orm import sessionmaker as make_session

    old_engine = engine
    snapshot = None
    if copy_data and old_engine is not None:
        OldSession = make_session(bind=old_engine, expire_on_commit=False)
        snapshot = _dump(OldSession())

    init_engine(url)

    if snapshot:
        _restore(snapshot)


def _seed(bind: Engine) -> None:
    from models import Patient

    Session = sessionmaker(bind=bind, expire_on_commit=False)
    session = Session()
    try:
        if session.query(User).count() == 0:
            session.add(
                User(
                    username="admin",
                    password_hash=generate_password_hash("admin123"),
                    role="admin",
                    full_name="Hospital Admin",
                )
            )
            session.add(
                User(
                    username="nurse",
                    password_hash=generate_password_hash("nurse123"),
                    role="nurse",
                    full_name="Charge Nurse",
                )
            )
        _ensure_admin(session)
        if session.query(Doctor).count() == 0:
            imported = _import_json_state(session)
            if not imported:
                for item in SEED_DOCTORS:
                    session.add(
                        Doctor(
                            id=str(uuid4())[:8].upper(),
                            name=item["name"],
                            specialty=item["specialty"],
                            room=item["room"],
                            booked=False,
                        )
                    )
        elif session.query(Patient).count() == 0:
            _import_json_state(session, doctors=False)
        session.commit()
    finally:
        session.close()


def _ensure_admin(session: Session) -> None:
    if session.query(User).filter_by(username="admin").first():
        return
    session.add(
        User(
            username="admin",
            password_hash=generate_password_hash("admin123"),
            role="admin",
            full_name="Hospital Admin",
        )
    )


def _import_json_state(session: Session, doctors: bool = True, patients: bool = True) -> bool:
    if not JSON_STATE.exists():
        return False
    data = json.loads(JSON_STATE.read_text(encoding="utf-8"))
    doctor_rows = data.get("doctors") or []
    patient_rows = data.get("patients") or []
    if not doctor_rows and not patient_rows:
        return False
    if doctors:
        for row in doctor_rows:
            session.add(
                Doctor(
                    id=str(row.get("id") or str(uuid4())[:8]),
                    name=row["name"],
                    specialty=row.get("specialty") or "Emergency",
                    room=row.get("room") or "",
                    booked=bool(row.get("booked")),
                    free_at=row.get("free_at"),
                    patient_id=row.get("patient_id"),
                )
            )
    if patients:
        for row in patient_rows:
            session.add(patient_from_dict(row))
    return True


def _dump(session: Session) -> dict:
    from models import Patient

    data = {
        "users": [
            {
                "username": u.username,
                "password_hash": u.password_hash,
                "role": u.role,
                "full_name": u.full_name,
            }
            for u in session.query(User).all()
        ],
        "doctors": [d.to_dict() for d in session.query(Doctor).all()],
        "patients": [p.to_dict() for p in session.query(Patient).all()],
    }
    session.close()
    return data


def _restore(snapshot: dict) -> None:
    from models import Patient

    session = get_session()
    try:
        if session.query(User).count() == 0:
            for row in snapshot.get("users", []):
                session.add(User(**row))
        if session.query(Doctor).count() == 0:
            for row in snapshot.get("doctors", []):
                allowed = {c.key for c in inspect(Doctor).mapper.column_attrs}
                session.add(Doctor(**{k: v for k, v in row.items() if k in allowed}))
        if session.query(Patient).count() == 0:
            for row in snapshot.get("patients", []):
                session.add(patient_from_dict(row))
        session.commit()
    finally:
        session.close()


def patient_from_dict(row: dict) -> "Patient":
    from models import Patient

    payload = dict(row)
    payload["symptoms_json"] = json.dumps(payload.pop("symptoms", []))
    payload["ai_reasons_json"] = json.dumps(payload.pop("ai_reasons", []))
    allowed = {c.key for c in inspect(Patient).mapper.column_attrs}
    return Patient(**{k: v for k, v in payload.items() if k in allowed})


def apply_patient_dict(patient, row: dict) -> None:
    payload = dict(row)
    if "symptoms" in payload:
        payload["symptoms_json"] = json.dumps(payload.pop("symptoms") or [])
    if "ai_reasons" in payload:
        payload["ai_reasons_json"] = json.dumps(payload.pop("ai_reasons") or [])
    allowed = {c.key for c in inspect(patient.__class__).mapper.column_attrs}
    for key, value in payload.items():
        if key in allowed:
            setattr(patient, key, value)
