# licence.py

from email.mime.text import MIMEText
import os
import secrets
import smtplib  

SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")
SMTP_FROM = os.getenv("SMTP_FROM", SMTP_USER)


def send_license_email(to_email: str, license_key: str):
    """
    Send the license key to the user by email using company SMTP.
    """
    if not (SMTP_HOST and SMTP_USER and SMTP_PASS):
        print("SMTP not configured properly, skipping email.")
        return

    subject = "Votre clé de licence InspectorX"
    body = f"""Bonjour {to_email},

            Merci pour votre inscription à InspectorX.

            Voici votre clé de licence :

                {license_key}

            Vous pouvez l'utiliser dans l'application InspectorX pour activer votre licence
            sur votre machine.

            Cordialement,
            L'équipe Lynxdrone
            """

    msg = MIMEText(body, _charset="utf-8")
    msg["Subject"] = subject
    msg["From"] = SMTP_FROM
    msg["To"] = to_email

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)
        print(f"License email sent to {to_email}")
    except Exception as e:
        # Don't crash registration if email fails
        print(f"Error sending license email to {to_email}: {e}")


# Generate a license key in the format XXXX-XXXX-XXXX
def generate_license_key():
    parts = [secrets.token_hex(2).upper() for _ in range(3)]
    key = "-".join(parts)
    return key
