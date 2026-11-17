# AI Emergency Triage System

A Flask-based emergency triage and hospital workflow application designed to streamline patient intake, priority assessment, doctor assignment, and record management in a clinical setting.

## Overview

This project simulates a hospital emergency department workflow where patients are registered, assessed for urgency, and routed to the appropriate department. It combines a rule-based triage engine with a simple front-end dashboard for nurses, administrators, and clinical staff.

The application supports:
- Patient intake with symptoms and vital details
- AI-inspired emergency priority scoring
- Specialty/department assignment
- Nurse approval and manual overrides
- Doctor and room management
- Waitlist and discharge tracking
- Patient record export to CSV and Excel
- Optional connection to a personal database

## Features

- Emergency patient registration
- Triage priority levels from Critical to Minimal
- Department recommendation based on symptoms and patient profile
- Real-time review workflow for staff members
- Patient tracking for in-care and discharged records
- Exportable healthcare records
- Admin database configuration for switching database backends
- SQLite-based default storage for quick local deployment

## Tech Stack

- Python
- Flask
- SQLAlchemy
- SQLite / MySQL / PostgreSQL support
- OpenPyXL
- HTML, CSS, and Jinja templates

## Project Structure

```text
AI-Emergency-Triage-
├── README.md
├── Final year project v2.0/
│   ├── app.py
│   ├── db.py
│   ├── db_config.json
│   ├── hospital.db
│   ├── hospital_state.json
│   ├── models.py
│   ├── requirements.txt
│   ├── secret.key
│   ├── store.py
│   ├── triage_engine.py
│   ├── static/
│   └── templates/
└── .gitignore
```

## Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/Kartikay2628/AI-Emergency-Triage-.git
cd AI-Emergency-Triage-
```

### 2. Create a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate
```

On Windows:

```bash
.venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r "Final year project v2.0/requirements.txt"
```

### 4. Run the application

```bash
python "Final year project v2.0/app.py"
```

Then open the app in your browser:

```text
http://localhost:5000
```

## How It Works

1. A patient is entered through the intake form.
2. Symptoms, age, vitals, and emergency context are processed.
3. The triage engine calculates a priority score and suggests the right specialty.
4. A nurse or admin reviews and approves or overrides the recommendation.
5. The patient is entered into the waitlist or moved through care and discharge workflow.

## Default Database

The project uses a local SQLite database by default (`hospital.db`). An admin can also connect to a custom database URL through the settings screen in the application.

## Usage Notes

- This project is ideal for demonstration, educational projects, and prototype hospital workflow simulation.
- The triage rules are rule-based and can be expanded with a more advanced ML or clinical decision model in future iterations.
- The UI supports multiple views such as intake, review, waitlist, doctors, records, and settings.

## License

This project does not currently declare a specific license in the repository.

## Contributing

Contributions, bug fixes, and feature improvements are welcome. You can fork the repository and submit a pull request with your changes.

## Contact

Repository owner: Kartikay2628

Project URL: https://github.com/Kartikay2628/AI-Emergency-Triage-
