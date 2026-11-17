"""Rule-based emergency triage (ESI-inspired)."""

from __future__ import annotations

PRIORITIES = {
    1: {"label": "Critical", "wait": "Immediate", "minutes": 45},
    2: {"label": "High", "wait": "Within 10 minutes", "minutes": 40},
    3: {"label": "Medium", "wait": "Within 30 minutes", "minutes": 30},
    4: {"label": "Low", "wait": "Within 60 minutes", "minutes": 20},
    5: {"label": "Minimal", "wait": "When possible", "minutes": 15},
}

SYMPTOM_SPECIALTY = {
    "chest pain": "Cardiology",
    "heart palpitations": "Cardiology",
    "shortness of breath": "Emergency",
    "stroke signs": "Neurology",
    "seizure": "Neurology",
    "severe headache": "Neurology",
    "confusion": "Neurology",
    "fracture / fall": "Orthopedics",
    "joint or bone pain": "Orthopedics",
    "abdominal pain": "General Surgery",
    "bleeding": "Emergency",
    "trauma / accident": "General Surgery",
    "allergic reaction": "Emergency",
    "fever": "Internal Medicine",
    "vomiting": "Internal Medicine",
    "pregnancy / labour": "Obstetrics",
    "wound / cut": "Emergency",
    "burns": "Emergency",
    "cough / cold": "Internal Medicine",
    "back pain": "Orthopedics",
}


def suggest_specialty(age: int, symptoms: list[str], pregnancy: bool) -> str:
    if pregnancy or "pregnancy / labour" in symptoms:
        return "Obstetrics"
    if age < 16:
        return "Pediatrics"
    for symptom in symptoms:
        if symptom in SYMPTOM_SPECIALTY:
            return SYMPTOM_SPECIALTY[symptom]
    return "Emergency"


def assess(payload: dict) -> dict:
    reasons: list[str] = []
    level = 5

    age = int(payload.get("age") or 0)
    hr = _num(payload.get("heart_rate"))
    sys_bp = _num(payload.get("systolic_bp"))
    dia_bp = _num(payload.get("diastolic_bp"))
    temp = _num(payload.get("temperature"))
    spo2 = _num(payload.get("spo2"))
    rr = _num(payload.get("resp_rate"))
    pain = int(payload.get("pain") or 0)
    consciousness = payload.get("consciousness") or "Alert"
    symptoms = payload.get("symptoms") or []
    pregnancy = bool(payload.get("pregnancy"))
    arrival = payload.get("arrival") or "Walk-in"

    def raise_to(new_level: int, reason: str) -> None:
        nonlocal level
        if new_level > level:
            return
        if new_level < level:
            level = new_level
        reasons.append(reason)

    if consciousness == "Unresponsive":
        raise_to(1, "Patient is unresponsive - life-saving intervention may be needed.")
    if "uncontrolled bleeding" in symptoms or (
        "bleeding" in symptoms and pain >= 8
    ):
        raise_to(1, "Severe or uncontrolled bleeding.")
    if spo2 is not None and spo2 < 90:
        raise_to(1, f"Oxygen saturation is critically low ({spo2}%).")
    if sys_bp is not None and sys_bp < 80:
        raise_to(1, f"Blood pressure is dangerously low ({sys_bp} mmHg).")
    if hr is not None and (hr < 40 or hr > 160):
        raise_to(1, f"Heart rate is life-threatening ({hr} bpm).")
    if "stroke signs" in symptoms:
        raise_to(1, "Possible stroke (FAST signs) - time-critical.")
    if "chest pain" in symptoms and (spo2 is not None and spo2 < 94 or pain >= 7):
        raise_to(1, "Chest pain with low oxygen or severe pain - possible heart emergency.")

    if consciousness == "Confused":
        raise_to(2, "Altered mental status.")
    if "chest pain" in symptoms:
        raise_to(2, "Chest pain needs urgent cardiac assessment.")
    if "seizure" in symptoms:
        raise_to(2, "Seizure activity.")
    if "shortness of breath" in symptoms:
        raise_to(2, "Difficulty breathing.")
    if "allergic reaction" in symptoms:
        raise_to(2, "Allergic reaction can worsen quickly.")
    if "trauma / accident" in symptoms:
        raise_to(2, "Trauma / accident.")
    if spo2 is not None and spo2 < 94:
        raise_to(2, f"Oxygen saturation is low ({spo2}%).")
    if sys_bp is not None and sys_bp >= 180:
        raise_to(2, f"Very high blood pressure ({sys_bp} mmHg).")
    if temp is not None and temp >= 40:
        raise_to(2, f"Very high fever ({temp}°C).")
    if age < 3 and temp is not None and temp >= 38.5:
        raise_to(2, "Young child with significant fever.")
    if pregnancy and ("bleeding" in symptoms or "abdominal pain" in symptoms):
        raise_to(2, "Pregnancy with bleeding or abdominal pain.")
    if pain >= 8:
        raise_to(2, f"Severe pain score ({pain}/10).")
    if arrival == "Ambulance":
        raise_to(2, "Arrived by ambulance.")

    if "abdominal pain" in symptoms:
        raise_to(3, "Abdominal pain needs same-day assessment.")
    if "fracture / fall" in symptoms or "joint or bone pain" in symptoms:
        raise_to(3, "Possible fracture or musculoskeletal injury.")
    if "severe headache" in symptoms:
        raise_to(3, "Severe headache.")
    if "fever" in symptoms or (temp is not None and temp >= 38.5):
        raise_to(3, "Fever.")
    if pain >= 5:
        raise_to(3, f"Moderate pain ({pain}/10).")
    if hr is not None and (hr > 120 or hr < 50):
        raise_to(3, f"Abnormal heart rate ({hr} bpm).")
    if rr is not None and (rr > 24 or rr < 10):
        raise_to(3, f"Abnormal breathing rate ({rr}/min).")
    if dia_bp is not None and dia_bp >= 110:
        raise_to(3, "High diastolic blood pressure.")

    if pain >= 3 or symptoms:
        raise_to(4, "Symptoms present but not immediately life-threatening.")

    if not reasons:
        reasons.append("Stable appearance with mild or no red-flag symptoms.")

    meta = PRIORITIES[level]
    specialty = suggest_specialty(age, symptoms, pregnancy)
    return {
        "priority": level,
        "priority_label": meta["label"],
        "target_wait": meta["wait"],
        "est_minutes": meta["minutes"],
        "specialty": specialty,
        "reasons": reasons[:6],
        "summary": (
            f"{meta['label']} priority. Suggested department: {specialty}. "
            f"Target start: {meta['wait']}."
        ),
    }


def _num(value):
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
