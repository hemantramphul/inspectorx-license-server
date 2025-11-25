from flask import Flask, request, jsonify, Response, render_template
from werkzeug.security import generate_password_hash, check_password_hash
import json

from license import generate_license_key, send_license_email
from models import Client, db, User, License  
import os
from dotenv import load_dotenv
load_dotenv()

APP_SECRET_KEY = os.getenv("APP_SECRET_KEY")

app = Flask(__name__)

# SQLite file in the same folder
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///licenses.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize db with this app
db.init_app(app)

# Create DB tables on startup
with app.app_context():
    db.create_all()


@app.get("/")
def home():
    # At first load, we don't show any clients until secret is submitted
    return render_template("clients.html", clients=[])


@app.get("/admin/clients")
def admin_list_clients():
    # Same as home for GET: no list until valid secret posted
    return render_template("clients.html", clients=[])


@app.post("/admin/clients")
def admin_create_or_list_clients():
    email = (request.form.get("email") or "").strip()
    name = (request.form.get("name") or "").strip()
    secret = (request.form.get("secret") or "").strip()

    # 1) Check secret key
    if not APP_SECRET_KEY or secret != APP_SECRET_KEY:
        return render_template("clients.html", clients=[])

    # 2) If email is empty: just show list (no creation)
    if not email:
        clients = Client.query.order_by(Client.id.desc()).all()
        return render_template("clients.html", clients=clients)

    # 3) If email is provided: create client + license key
    client = Client.query.filter_by(email=email).first()
    if not client:
        # generate license key
        license_key = generate_license_key()

        client = Client(
            email=email,
            name=name,
            license_key=license_key,
            is_active=True,
        )
        db.session.add(client)
        db.session.commit()

        # create License entry tied to this client (user_id None for now)
        lic = License(
            license_key=license_key,
            max_devices=1,
            devices_json="[]",
            user_id=None,
            client_id=client.id,
        )
        db.session.add(lic)
        db.session.commit()

        # send license email (optional, best-effort only)
        try:
            send_license_email(email, license_key)
        except Exception as e:
            print("Error sending license email at client creation:", e)

    # Reload list
    clients = Client.query.order_by(Client.id.desc()).all()
    return render_template("clients.html", clients=clients)

# Create Client
@app.post("/api/admin/clients")
def create_client():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip()
    name = (data.get("name") or "").strip()

    if not email:
        return jsonify(ok=False, error="MISSING_EMAIL"), 400

    client = Client.query.filter_by(email=email).first()
    if client:
        return jsonify(ok=False, error="CLIENT_EXISTS"), 400

    license_key = generate_license_key()

    client = Client(
        email=email,
        name=name,
        license_key=license_key,
        is_active=True,
    )
    db.session.add(client)
    db.session.commit()

    lic = License(
        license_key=license_key,
        max_devices=1,
        devices_json="[]",
        user_id=None,
        client_id=client.id,
    )
    db.session.add(lic)
    db.session.commit()

    try:
        send_license_email(email, license_key)
        email_sent = True
    except Exception as e:
        print("Error sending license email:", e)
        email_sent = False

    return jsonify(
        ok=True,
        message="CLIENT_CREATED",
        email=email,
        license_key=license_key,
        email_sent=email_sent,
    )

# Registration 
@app.post("/api/register")
def register():
    data = request.get_json(silent=True) or {}

    email = data.get("email")
    password = data.get("password")
    license_key = data.get("license_key")

    if not email or not password or not license_key:
        return jsonify(ok=False, error="MISSING_FIELDS"), 400

    # 1) Check if this email + license_key is a valid client
    client = Client.query.filter_by(
        email=email,
        license_key=license_key,
        is_active=True
    ).first()

    if not client:
        return jsonify(ok=False, error="CLIENT_OR_LICENSE_INVALID"), 403

    # 2) Check if user already exists
    if User.query.filter_by(email=email).first():
        return jsonify(ok=False, error="EMAIL_EXISTS"), 400

    # 3) Find existing license for this license_key
    lic = License.query.filter_by(license_key=license_key).first()
    if not lic:
        return jsonify(ok=False, error="LICENSE_NOT_FOUND"), 500

    # (optional) Check if this license is already linked to another user
    if lic.user_id is not None:
        return jsonify(ok=False, error="LICENSE_ALREADY_USED"), 400

    # 4) Create user
    user = User(
        email=email,
        password_hash=generate_password_hash(password),
    )
    db.session.add(user)
    db.session.commit()

    # 5) Attach license to this user
    lic.user_id = user.id
    db.session.commit()

    # 6) Return license key and info
    return jsonify(
        ok=True,
        email=email,
        license_key=license_key,
        max_devices=lic.max_devices
    )

# Login
@app.post("/api/login")
def login():
    data = request.get_json(silent=True) or {}
    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify(ok=False, error="MISSING_FIELDS"), 400

    user = User.query.filter_by(email=email).first()
    if not user or not check_password_hash(user.password_hash, password):
        return jsonify(ok=False, error="INVALID_CREDENTIALS"), 400

    return jsonify(ok=True, user_id=user.id)

# Create License
@app.post("/api/admin/licenses")
def create_license():
    data = request.get_json(silent=True) or {}
    license_key = data.get("license_key")
    max_devices = data.get("max_devices", 1)

    if not license_key:
        return jsonify(ok=False, error="MISSING_LICENSE_KEY"), 400

    # Check if already exists
    existing = License.query.filter_by(license_key=license_key).first()
    if existing:
        return jsonify(ok=False, error="LICENSE_EXISTS"), 400

    lic = License(
        license_key=license_key,
        max_devices=max_devices,
        devices_json="[]",
        user_id=None,  # will be linked on first activation
    )
    db.session.add(lic)
    db.session.commit()

    return jsonify(ok=True, message="LICENSE_CREATED")

# License Activation
@app.post("/api/licenses/activate")
def activate_license():
    data = request.get_json()
    license_key = data.get("license_key")
    machine_id = data.get("machine_id")
    email = data.get("email")

    if not license_key or not machine_id or not email:
        return jsonify(ok=False, error="MISSING_FIELDS"), 400

    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify(ok=False, error="UNKNOWN_USER"), 400

    lic = License.query.filter_by(license_key=license_key).first()
    if not lic:
        return jsonify(ok=False, error="INVALID_LICENSE"), 400

    devices = json.loads(lic.devices_json or "[]")

    if machine_id in devices:
        return jsonify(ok=True, message="ALREADY_ACTIVATED")

    if len(devices) >= lic.max_devices:
        return jsonify(ok=False, error="MAX_DEVICES_REACHED"), 400

    devices.append(machine_id)
    lic.devices_json = json.dumps(devices)

    if lic.user_id is None:
        # allow binding if license has no user yet
        lic.user_id = user.id
    elif lic.user_id != user.id:
        return jsonify(ok=False, error="LICENSE_NOT_OWNED_BY_USER"), 403

    db.session.commit()

    return jsonify(ok=True, message="LICENSE_ACTIVATED")

# License Status
@app.get("/api/licenses/status")
def license_status():
    license_key = request.args.get("license_key")
    machine_id = request.args.get("machine_id")

    lic = License.query.filter_by(license_key=license_key).first()
    if not lic:
        return jsonify(ok=False, error="INVALID_LICENSE"), 400

    devices = json.loads(lic.devices_json or "[]")
    return jsonify(ok=True, active=(machine_id in devices))

# List all licenses
@app.get("/api/admin/licenses")
def list_licenses():
    """
    Return flat list of all licenses with their owner email.
    """
    entries = (
        db.session.query(User.email, License.license_key, License.max_devices, License.devices_json)
        .join(License, License.user_id == User.id, isouter=True)
        .all()
    )

    data = []
    for email, license_key, max_devices, devices_json in entries:
        if license_key is None:
            # user has no license, skip or include with null
            continue

        data.append({
            "email": email,
            "license_key": license_key,
            "max_devices": max_devices,
            "devices": json.loads(devices_json or "[]"),
        })

    return jsonify(ok=True, data=data)

# Delete user and their licenses
@app.delete("/api/admin/users")
def delete_user():
    """
    Delete a registered user and all their licenses.
    Body: { "email": "user@example.com" }
    """
    data = request.get_json(silent=True) or {}
    email = data.get("email")

    if not email:
        return jsonify(ok=False, error="MISSING_EMAIL"), 400

    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify(ok=False, error="USER_NOT_FOUND"), 404

    # Delete all licenses for this user
    License.query.filter_by(user_id=user.id).delete()

    # Delete the user
    db.session.delete(user)
    db.session.commit()

    return jsonify(ok=True, message=f"User {email} and their licenses deleted")

# Run the app
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
