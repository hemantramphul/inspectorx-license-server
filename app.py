# app.py
from flask import Flask, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import json

from models import db, User, License  

app = Flask(__name__)

# SQLite file in the same folder
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///licenses.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize db with this app
db.init_app(app)

with app.app_context():
    db.create_all()

@app.post("/api/register")
def register():
    # `silent=True` -> don't raise if JSON is missing
    data = request.get_json(silent=True) or {}

    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify(ok=False, error="MISSING_FIELDS"), 400

    if User.query.filter_by(email=email).first():
        return jsonify(ok=False, error="EMAIL_EXISTS"), 400

    user = User(
        email=email,
        password_hash=generate_password_hash(password),
    )
    db.session.add(user)
    db.session.commit()
    return jsonify(ok=True)


@app.post("/api/login")
def login():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")

    user = User.query.filter_by(email=email).first()
    if not user or not check_password_hash(user.password_hash, password):
        return jsonify(ok=False, error="INVALID_CREDENTIALS"), 400

    return jsonify(ok=True, user_id=user.id)


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
        lic.user_id = user.id

    db.session.commit()

    return jsonify(ok=True, message="LICENSE_ACTIVATED")


@app.get("/api/licenses/status")
def license_status():
    license_key = request.args.get("license_key")
    machine_id = request.args.get("machine_id")

    lic = License.query.filter_by(license_key=license_key).first()
    if not lic:
        return jsonify(ok=False, error="INVALID_LICENSE"), 400

    devices = json.loads(lic.devices_json or "[]")
    return jsonify(ok=True, active=(machine_id in devices))


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


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
