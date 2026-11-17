# AI Emergency Triage System

> A final-year project prototype for digital patient intake, rule-based emergency prioritisation, and hospital workflow management.

[![Python](https://img.shields.io/badge/Python-3.x-blue?logo=python&logoColor=white)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.0.3-black?logo=flask)](https://flask.palletsprojects.com/)

## Project Abstract

The **AI Emergency Triage System** is a web application prototype intended to demonstrate how digital tools can support emergency department intake and patient flow. It collects patient details, symptoms, and vital signs, then applies a transparent, rule-based triage engine to suggest an urgency level and a relevant department. Clinical staff can review the suggestion, approve or override it, manage the waitlist and doctors, track care through discharge, and export records.

The triage logic is **rule-based and ESI-inspired**; it is not a trained machine-learning model and has not been clinically validated. The application is an academic demonstration, not a medical device or a substitute for professional judgement.

## Problem Statement

Emergency care teams need to gather patient information and organise cases by urgency while maintaining a clear view of patients awaiting care. This project explores a small-scale software workflow for collecting intake information, presenting an explainable priority suggestion, and supporting staff review and patient tracking.

## Project Objectives

- Build a browser-based patient intake and emergency workflow prototype.
- Generate a priority suggestion from symptoms and selected vital signs.
- Provide an explanation for the suggestion and recommend a specialty.
- Keep clinical staff in control through review and manual override.
- Support waitlist, doctor, in-care, and discharged-record management.
- Demonstrate relational database access and record export.

## Key Features

- **Patient intake:** Capture demographics, symptoms, arrival details, and vital signs.
- **Rule-based triage:** Suggest one of five levels, from Critical to Minimal, and show assessment reasons.
- **Specialty recommendation:** Map patient information and symptoms to a suggested department.
- **Staff review:** Nurse and admin accounts can approve or decline intake and override the suggested priority with notes.
- **Patient flow:** Manage the waitlist, doctor assignments, active care, and discharged records.
- **Record export:** Export records to CSV or Excel (`.xlsx`).
- **Database configuration:** Use the included local database by default or configure a supported database connection through the admin settings.
- **Role-aware views:** Separate staff workflows from the public intake experience.

## System Workflow

1. A patient or staff member submits the intake form.
2. The triage engine evaluates the entered symptoms and available patient observations.
3. The application displays a suggested priority, rationale, and department.
4. A nurse or admin reviews the case and may confirm or change the suggested priority.
5. Approved patients can be managed through the waitlist, care, and discharge workflow.
6. Staff can review records and export them for demonstration or reporting purposes.

## Technology Stack

| Area | Technologies |
| --- | --- |
| Backend | Python, Flask |
| Data access | SQLAlchemy |
| Database options | SQLite by default; MySQL and PostgreSQL drivers included |
| Frontend | HTML, CSS, Jinja templates |
| Spreadsheet export | OpenPyXL |

## Repository Structure

```text
.
├── README.md
└── Final year project v2.0/
    ├── app.py                 # Flask routes and application workflow
    ├── db.py                  # Database setup and connection helpers
    ├── db_config.json         # Database configuration
    ├── hospital.db            # Included local database
    ├── hospital_state.json    # Hospital state data
    ├── models.py              # SQLAlchemy models
    ├── requirements.txt       # Python dependencies
    ├── store.py               # Hospital workflow and data operations
    ├── triage_engine.py       # Rule-based priority and specialty suggestions
    ├── static/                # CSS and other static assets
    └── templates/             # Jinja HTML templates
```

## Run Locally

### Prerequisites

- Python 3
- `pip`
- Git

### Installation

```bash
git clone https://github.com/Kartikay2628/AI-Emergency-Triage-.git
cd AI-Emergency-Triage-
python -m venv .venv
```

Activate the virtual environment:

```bash
# macOS / Linux
source .venv/bin/activate

# Windows PowerShell
.venv\Scripts\Activate.ps1
```

Install the project dependencies and start the application:

```bash
pip install -r "Final year project v2.0/requirements.txt"
python "Final year project v2.0/app.py"
```

Open <http://localhost:5000> in a browser.

## Triage Levels

The rule engine returns one of five application priority levels:

| Level | Label | Example target shown by the app |
| --- | --- | --- |
| 1 | Critical | Immediate |
| 2 | High | Within 10 minutes |
| 3 | Medium | Within 30 minutes |
| 4 | Low | Within 60 minutes |
| 5 | Minimal | When possible |

These labels and targets describe the prototype's configured rules. They are **not clinical guidance or guaranteed treatment times**.

## Academic Scope and Limitations

This project demonstrates a full-stack workflow and an explainable, rule-based approach to triage prioritisation. Its outputs depend on the input provided and the rules implemented in `triage_engine.py`. The rules are not a validated clinical protocol, and the application has not been assessed for clinical safety, accuracy, accessibility, privacy, or production readiness. It should only be used with synthetic or otherwise authorised data in a controlled demonstration.

## Security and Data Handling

- Do not use this prototype to store real patient information or deploy it as a clinical service.
- The repository contains local application/database artifacts. Review them before sharing or using real data.
- Configure a unique, protected Flask secret key and database credentials for any local testing; never publish secrets or credentials.
- The application starts with Flask's debug mode enabled in `app.py`. Debug mode is for local development only and must not be used in a publicly accessible deployment.

## Future Work

Possible extensions for a future project iteration include automated tests, improved validation and audit logging, configurable triage rules reviewed by qualified clinicians, accessibility improvements, and a deployment configuration suitable for a security and privacy review.

## License

No license is currently specified in this repository. Contact the repository owner before reusing or distributing the project.

## Author and Repository

- **Repository:** [Kartikay2628/AI-Emergency-Triage-](https://github.com/Kartikay2628/AI-Emergency-Triage-)
