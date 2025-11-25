# InspectorX License Server

A lightweight **API-only** Flask service to manage user registration and software license activation.

This project is designed to be used by desktop apps like **InspectorX** (Electron, Python, etc.) to enforce rules such as:

- One license key → limited number of machines (e.g. 1 PC per license)
- License activation per machine using a **machine ID**
- Simple admin endpoints to list users and license activations

---

## Features

- User registration (`/api/register`)
- User login (`/api/login`)
- License activation per machine (`/api/licenses/activate`)
- License status check (`/api/licenses/status`)
- Admin endpoints to list:
  - all users + their licenses (`/api/admin/registrations`)
  - flat list of licenses + email (`/api/admin/licenses`)
- Uses **SQLite** (file-based DB) via SQLAlchemy
- API-only (JSON), no frontend

---

## Tech Stack

- **Python** 3.8+
- **Flask** (web framework)
- **Flask-SQLAlchemy** (ORM)
- **Werkzeug** (password hashing)
- **SQLite** (default database)

---

## Project Structure

```text
inspectorx-license-server/
  app.py                    # Flask app & routes
  models.py                 # SQLAlchemy models (User, License)
  requirements.txt
  instance/licenses.db      # SQLite database (auto-created)
  .venv/                    # Python virtual environment (optional, local)
```
