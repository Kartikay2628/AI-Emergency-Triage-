"""SQLAlchemy models for users, doctors, and patients."""

from __future__ import annotations

import json

from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # admin | nurse
    full_name: Mapped[str] = mapped_column(String(120), default="")


class Doctor(Base):
    __tablename__ = "doctors"

    id: Mapped[str] = mapped_column(String(16), primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    specialty: Mapped[str] = mapped_column(String(80), nullable=False)
    room: Mapped[str] = mapped_column(String(40), default="")
    booked: Mapped[bool] = mapped_column(Boolean, default=False)
    free_at: Mapped[str | None] = mapped_column(String(32), nullable=True)
    patient_id: Mapped[str | None] = mapped_column(String(16), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "specialty": self.specialty,
            "room": self.room,
            "booked": self.booked,
            "free_at": self.free_at,
            "patient_id": self.patient_id,
        }


class Patient(Base):
    __tablename__ = "patients"

    id: Mapped[str] = mapped_column(String(16), primary_key=True)
    owner: Mapped[str] = mapped_column(String(80), default="")
    name: Mapped[str] = mapped_column(String(120), default="Unknown")
    age: Mapped[int] = mapped_column(Integer, default=0)
    sex: Mapped[str] = mapped_column(String(32), default="Not specified")
    phone: Mapped[str] = mapped_column(String(40), default="")
    arrival: Mapped[str] = mapped_column(String(40), default="Walk-in")
    consciousness: Mapped[str] = mapped_column(String(40), default="Alert")
    pain: Mapped[int] = mapped_column(Integer, default=0)
    duration: Mapped[str] = mapped_column(String(80), default="")
    symptoms_json: Mapped[str] = mapped_column(Text, default="[]")
    notes: Mapped[str] = mapped_column(Text, default="")
    allergies: Mapped[str] = mapped_column(Text, default="None")
    history: Mapped[str] = mapped_column(Text, default="None")
    pregnancy: Mapped[bool] = mapped_column(Boolean, default=False)
    heart_rate: Mapped[str] = mapped_column(String(16), default="")
    systolic_bp: Mapped[str] = mapped_column(String(16), default="")
    diastolic_bp: Mapped[str] = mapped_column(String(16), default="")
    temperature: Mapped[str] = mapped_column(String(16), default="")
    spo2: Mapped[str] = mapped_column(String(16), default="")
    resp_rate: Mapped[str] = mapped_column(String(16), default="")
    status: Mapped[str] = mapped_column(String(24), default="review")
    created_at: Mapped[str | None] = mapped_column(String(32), nullable=True)
    completed_at: Mapped[str | None] = mapped_column(String(32), nullable=True)
    removed_at: Mapped[str | None] = mapped_column(String(32), nullable=True)
    care_start: Mapped[str | None] = mapped_column(String(32), nullable=True)
    free_at: Mapped[str | None] = mapped_column(String(32), nullable=True)
    ai_priority: Mapped[int | None] = mapped_column(Integer, nullable=True)
    priority: Mapped[int | None] = mapped_column(Integer, nullable=True)
    priority_label: Mapped[str | None] = mapped_column(String(40), nullable=True)
    target_wait: Mapped[str | None] = mapped_column(String(80), nullable=True)
    est_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    specialty: Mapped[str | None] = mapped_column(String(80), nullable=True)
    ai_reasons_json: Mapped[str] = mapped_column(Text, default="[]")
    ai_summary: Mapped[str] = mapped_column(Text, default="")
    review_notes: Mapped[str] = mapped_column(Text, default="")
    reviewed: Mapped[bool] = mapped_column(Boolean, default=False)
    reviewed_by: Mapped[str] = mapped_column(String(80), default="")
    doctor_id: Mapped[str | None] = mapped_column(String(16), nullable=True)
    doctor_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    room: Mapped[str | None] = mapped_column(String(40), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "owner": self.owner,
            "name": self.name,
            "age": self.age,
            "sex": self.sex,
            "phone": self.phone,
            "arrival": self.arrival,
            "consciousness": self.consciousness,
            "pain": self.pain,
            "duration": self.duration,
            "symptoms": json.loads(self.symptoms_json or "[]"),
            "notes": self.notes,
            "allergies": self.allergies,
            "history": self.history,
            "pregnancy": self.pregnancy,
            "heart_rate": self.heart_rate,
            "systolic_bp": self.systolic_bp,
            "diastolic_bp": self.diastolic_bp,
            "temperature": self.temperature,
            "spo2": self.spo2,
            "resp_rate": self.resp_rate,
            "status": self.status,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "removed_at": self.removed_at,
            "care_start": self.care_start,
            "free_at": self.free_at,
            "ai_priority": self.ai_priority,
            "priority": self.priority,
            "priority_label": self.priority_label,
            "target_wait": self.target_wait,
            "est_minutes": self.est_minutes,
            "specialty": self.specialty,
            "ai_reasons": json.loads(self.ai_reasons_json or "[]"),
            "ai_summary": self.ai_summary,
            "review_notes": self.review_notes,
            "reviewed": self.reviewed,
            "reviewed_by": self.reviewed_by,
            "doctor_id": self.doctor_id,
            "doctor_name": self.doctor_name,
            "room": self.room,
        }
