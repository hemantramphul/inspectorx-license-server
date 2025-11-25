# InspectorX License Server

**InspectorX license server** to manage:

- Client onboarding by Lynxdrone admins
- User registration (email + password + license key)
- Per-machine license activation for desktop apps like **InspectorX**

It is designed to be called from desktop apps and to enforce rules such as:

- **One license key → limited number of machines** (e.g. 1 PC per license)
- **Activation per machine** using a unique machine ID
- **Central control** of which clients are allowed to register

## Features

### Admin side

- **Admin UI** at `/` and `/admin/clients`:
  - Protected by a **secret key** (`APP_SECRET_KEY`)
  - Form to **add a client** (email, name, secret)
  - Auto-generates a **license key** and stores it in the DB
  - Shows a table with all clients + their license keys
- JSON admin APIs:
  - `POST /api/admin/clients` → create a client + license (for programmatic use)
  - `GET  /api/admin/licenses` → flat list of licenses + email + devices
  - `DELETE /api/admin/users` → delete a user and all their licenses
- Optional: sends the license key by email when a client is created (SMTP config).

### Client / User side

- **Registration** (`POST /api/register`)
  - Requires: `email`, `password`, `license_key`
  - Checks that `(email, license_key)` exists in `Client` table and is active
  - Creates a `User` and binds the **existing** license to this user
- **Login** (`POST /api/login`)
- **License activation** (`POST /api/licenses/activate`)
  - Requires: `email`, `license_key`, `machine_id`
  - Links the license to specific machines (up to `max_devices`)
- **License status check** (`GET /api/licenses/status`)
  - Query params: `license_key`, `machine_id`
  - Returns whether the license is active on that machine

## Tech Stack

- **Python** 3.8+
- **Flask** – web framework
- **Flask-SQLAlchemy** – ORM
- **Werkzeug** – password hashing
- **SQLite** – file-based DB
- **python-dotenv** – load local `.env`
- Optional: SMTP (company mail server) to send license keys

## Project Structure

```text
inspectorx-license-server/
  app.py                  # Flask app & routes (admin + API)
  models.py               # SQLAlchemy models (Client, User, License)
  license.py              # Helpers: generate_license_key, send_license_email
  templates/
    clients.html          # Minimal admin UI to create/list clients
  requirements.txt
  instance/licenses.db    # SQLite database (auto-created in project root)
  .env                    # Local env vars (not committed)
  .venv/                  # Python virtual environment (local only, optional)
```
