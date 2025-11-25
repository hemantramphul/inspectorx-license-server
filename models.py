# models.py
from flask_sqlalchemy import SQLAlchemy

# Global db instance, to be initialized in app.py
db = SQLAlchemy()


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)


class License(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    license_key = db.Column(db.String(64), unique=True, nullable=False)
    max_devices = db.Column(db.Integer, default=1)
    devices_json = db.Column(db.Text, default="[]")  # JSON list of machine_ids
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
