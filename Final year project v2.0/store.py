"""Hospital state stored in the connected SQL database."""

from __future__ import annotations

from datetime import datetime, timedelta
from uuid import uuid4

from db import init_engine, patient_from_dict, session_scope
from models import Doctor, Patient
from triage_engine import PRIORITIES, assess

init_engine()

SPECIALTIES = [
    "Emergency",
    "Cardiology",
    "Neurology",
    "Orthopedics",
    "General Surgery",
    "Pediatrics",
    "Obstetrics",
    "Internal Medicine",
]


def now() -> datetime:
    return datetime.now().replace(microsecond=0)


def iso(dt: datetime | None) -> str | None:
    return dt.isoformat(sep=" ", timespec="minutes") if dt else None


def parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


class Hospital:
    def _refresh_doctors(self) -> None:
        t = now()
        with session_scope() as session:
            changed = False
            for doc in session.query(Doctor).all():
                free_at = parse_dt(doc.free_at)
                if doc.booked and free_at and free_at <= t:
                    pid = doc.patient_id
                    doc.booked = False
                    doc.free_at = None
                    doc.patient_id = None
                    if pid:
                        patient = session.get(Patient, pid)
                        if patient and patient.status == "in_care":
                            patient.status = "completed"
                            patient.completed_at = iso(t)
                    changed = True
            if changed:
                self._fill_waitlist(session)

    def snapshot(self) -> dict:
        self._refresh_doctors()
        with session_scope() as session:
            doctors = [d.to_dict() for d in session.query(Doctor).order_by(Doctor.specialty, Doctor.name)]
            patients = [p.to_dict() for p in session.query(Patient).all()]
        pending = [p for p in patients if p["status"] == "review"]
        waiting = sorted(
            [p for p in patients if p["status"] == "waiting"],
            key=lambda p: (p["priority"] or 9, p["created_at"] or ""),
        )
        in_care = [p for p in patients if p["status"] == "in_care"]
        discharged = sorted(
            [p for p in patients if p["status"] == "completed"],
            key=lambda p: p.get("completed_at") or "",
            reverse=True,
        )
        addable = [p for p in patients if p["status"] in {"rejected", "removed"} and p.get("priority")]
        return {
            "doctors": doctors,
            "pending": pending,
            "waiting": waiting,
            "in_care": in_care,
            "discharged": discharged,
            "addable": addable,
            "specialties": SPECIALTIES,
            "counts": {
                "review": len(pending),
                "waiting": len(waiting),
                "in_care": len(in_care),
                "discharged": len(discharged),
                "free_doctors": sum(1 for d in doctors if not d["booked"]),
            },
        }

    def records(self, kind: str) -> list[dict]:
        data = self.snapshot()
        if kind == "in_care":
            return data["in_care"]
        if kind == "discharged":
            return data["discharged"]
        return data["in_care"] + data["discharged"]

    def intake(self, form: dict) -> dict:
        symptoms = form.get("symptoms") or []
        if isinstance(symptoms, str):
            symptoms = [symptoms]
        record = {
            "id": str(uuid4())[:8].upper(),
            "name": (form.get("name") or "Unknown").strip(),
            "age": int(form.get("age") or 0),
            "sex": form.get("sex") or "Not specified",
            "phone": (form.get("phone") or "").strip(),
            "arrival": form.get("arrival") or "Walk-in",
            "consciousness": form.get("consciousness") or "Alert",
            "pain": int(form.get("pain") or 0),
            "duration": (form.get("duration") or "").strip(),
            "symptoms": symptoms,
            "notes": (form.get("notes") or "").strip(),
            "allergies": (form.get("allergies") or "None").strip() or "None",
            "history": (form.get("history") or "None").strip() or "None",
            "pregnancy": bool(form.get("pregnancy")),
            "heart_rate": form.get("heart_rate") or "",
            "systolic_bp": form.get("systolic_bp") or "",
            "diastolic_bp": form.get("diastolic_bp") or "",
            "temperature": form.get("temperature") or "",
            "spo2": form.get("spo2") or "",
            "resp_rate": form.get("resp_rate") or "",
            "status": "review",
            "created_at": iso(now()),
            "ai_priority": None,
            "priority": None,
            "priority_label": None,
            "review_notes": "",
            "reviewed": False,
            "reviewed_by": "",
            "doctor_id": None,
            "doctor_name": None,
            "free_at": None,
        }
        result = assess(record)
        record.update(
            {
                "ai_priority": result["priority"],
                "priority": result["priority"],
                "priority_label": result["priority_label"],
                "target_wait": result["target_wait"],
                "est_minutes": result["est_minutes"],
                "specialty": result["specialty"],
                "ai_reasons": result["reasons"],
                "ai_summary": result["summary"],
            }
        )
        with session_scope() as session:
            session.add(patient_from_dict(record))
        return record

    def review(self, patient_id: str, priority: int, notes: str, approve: bool, reviewed_by: str = "") -> dict | None:
        with session_scope() as session:
            patient = session.get(Patient, patient_id)
            if not patient or patient.status != "review":
                return None
            priority = int(priority)
            meta = PRIORITIES[priority]
            patient.priority = priority
            patient.priority_label = meta["label"]
            patient.target_wait = meta["wait"]
            patient.est_minutes = meta["minutes"]
            patient.review_notes = notes.strip()
            patient.reviewed = True
            patient.reviewed_by = reviewed_by
            if not approve:
                patient.status = "rejected"
                return patient.to_dict()
            patient.status = "waiting"
            self._place_on_waitlist(session, patient)
            return patient.to_dict()

    def remove_patient(self, patient_id: str) -> bool:
        with session_scope() as session:
            patient = session.get(Patient, patient_id)
            if not patient:
                return False
            self._release_doctor(session, patient_id)
            if patient.status in {"waiting", "review", "in_care"}:
                patient.status = "removed"
                patient.removed_at = iso(now())
                patient.doctor_id = None
                patient.doctor_name = None
                self._fill_waitlist(session)
                return True
            return False

    def restore_to_waitlist(self, patient_id: str) -> dict | None:
        with session_scope() as session:
            patient = session.get(Patient, patient_id)
            if not patient:
                return None
            if patient.status in {"waiting", "in_care"}:
                return patient.to_dict()
            if not patient.priority:
                return None
            patient.status = "waiting"
            patient.reviewed = True
            self._place_on_waitlist(session, patient)
            return patient.to_dict()

    def complete_care(self, patient_id: str) -> bool:
        with session_scope() as session:
            patient = session.get(Patient, patient_id)
            if not patient:
                return False
            self._release_doctor(session, patient_id)
            patient.status = "completed"
            patient.completed_at = iso(now())
            self._fill_waitlist(session)
            return True

    def add_doctor(self, name: str, specialty: str, room: str) -> dict:
        doctor = {
            "id": str(uuid4())[:8].upper(),
            "name": name.strip(),
            "specialty": (specialty or "Emergency").strip(),
            "room": (room or "").strip(),
            "booked": False,
            "free_at": None,
            "patient_id": None,
        }
        with session_scope() as session:
            session.add(Doctor(**doctor))
        return doctor

    def remove_doctor(self, doctor_id: str) -> str | None:
        with session_scope() as session:
            doctor = session.get(Doctor, doctor_id)
            if not doctor:
                return "Doctor not found."
            if doctor.booked:
                return "This doctor is with a patient. Mark the visit done first."
            session.delete(doctor)
            return None

    def _candidates(self, session, specialty: str) -> list[Doctor]:
        match = session.query(Doctor).filter(Doctor.specialty == specialty).all()
        if match:
            return match
        emergency = session.query(Doctor).filter(Doctor.specialty == "Emergency").all()
        return emergency or session.query(Doctor).all()

    def _book(self, doctor: Doctor, patient: Patient, start: datetime) -> None:
        minutes = int(patient.est_minutes or 30)
        free_at = start + timedelta(minutes=minutes)
        doctor.booked = True
        doctor.free_at = iso(free_at)
        doctor.patient_id = patient.id
        patient.doctor_id = doctor.id
        patient.doctor_name = doctor.name
        patient.room = doctor.room
        patient.free_at = iso(free_at)
        patient.care_start = iso(start)
        patient.status = "in_care"

    def _queue_behind(self, session, patient: Patient) -> None:
        candidates = self._candidates(session, patient.specialty or "Emergency")
        if not candidates:
            patient.status = "waiting"
            return
        doctor = min(
            candidates,
            key=lambda d: parse_dt(d.free_at) or now() + timedelta(hours=12),
        )
        start = parse_dt(doctor.free_at) or now()
        minutes = int(patient.est_minutes or 30)
        patient.doctor_id = doctor.id
        patient.doctor_name = doctor.name
        patient.room = doctor.room
        patient.care_start = iso(start)
        patient.free_at = iso(start + timedelta(minutes=minutes))
        patient.status = "waiting"

    def _place_on_waitlist(self, session, patient: Patient) -> None:
        specialty = patient.specialty or "Emergency"
        free = [d for d in self._candidates(session, specialty) if not d.booked]
        if free:
            self._book(free[0], patient, now())
        else:
            self._queue_behind(session, patient)

    def _fill_waitlist(self, session) -> None:
        waiting = (
            session.query(Patient)
            .filter(Patient.status == "waiting")
            .order_by(Patient.priority, Patient.created_at)
            .all()
        )
        for patient in waiting:
            specialty = patient.specialty or "Emergency"
            free = [d for d in self._candidates(session, specialty) if not d.booked]
            if not free:
                self._queue_behind(session, patient)
                continue
            self._book(free[0], patient, now())

    def _release_doctor(self, session, patient_id: str) -> None:
        for doc in session.query(Doctor).filter(Doctor.patient_id == patient_id):
            doc.booked = False
            doc.free_at = None
            doc.patient_id = None


hospital = Hospital()
