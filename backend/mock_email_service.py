import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from typing import Optional
import os
from dotenv import load_dotenv
from database import db_session
import sqlite3

load_dotenv() 

SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")

from email.message import EmailMessage
import smtplib
import os

# Get database path from environment or use default
import config
INS_DB_PATH = os.getenv("MOCK_INSURANCE_DB_PATH") or os.path.join(config.BASE_DIR, "mock_insurance.db")


def _resolve_recipient_email(to_email: str | None = None, user_id: str | None = None, insurance_username: str | None = None) -> str | None:
    if to_email:
        return to_email
    if user_id:
        row = db_session.get_user(user_id)
        # Expecting get_user to return a row with email at index 2 based on schema (user_id, username, password, name, email, created_at)
        if row and len(row) >= 5:
            return row[4]
    if insurance_username:
        try:
            conn = sqlite3.connect(INS_DB_PATH, check_same_thread=False)
            cur = conn.cursor()
            # Determine if email column exists
            cols = {r[1] for r in cur.execute("PRAGMA table_info(insurance_users)").fetchall()}
            if "email" in cols:
                cur.execute("SELECT email FROM insurance_users WHERE username = ?", (insurance_username,))
                r = cur.fetchone()
                if r and r[0]:
                    return r[0]
        except Exception:
            pass
        finally:
            try:
                conn.close()
            except Exception:
                pass
    return None


def send_email(to_email: str | None, subject: str, body: str, attachment_path: str, *, user_id: str | None = None, insurance_username: str | None = None):
    smtp_server = os.getenv('SMTP_SERVER')
    smtp_port = int(os.getenv('SMTP_PORT', 587))
    smtp_username = os.getenv('SMTP_USERNAME')
    smtp_password = os.getenv('SMTP_PASSWORD')

    recipient = _resolve_recipient_email(to_email, user_id, insurance_username)

    if not recipient:
        print("Error sending email: recipient email not found (user_id=", user_id, ", insurance_username=", insurance_username, ")")
        return

    if not all([smtp_server, smtp_username, smtp_password]):
        return

    try:
        msg = EmailMessage()
        msg['Subject'] = subject
        msg['From'] = smtp_username
        msg['To'] = recipient
        msg.set_content(body)

        # Correct way: Read the local file directly
        with open(attachment_path, 'rb') as f:
            file_data = f.read()
            file_name = os.path.basename(attachment_path)

        msg.add_attachment(file_data, maintype='application', subtype='pdf', filename=file_name)

        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_username, smtp_password)
            server.send_message(msg)
            print(f"Email sent successfully to your provided mail")
            
    except smtplib.SMTPAuthenticationError as e:
        print(f"SMTP Authentication Error: {e}")
    except Exception as e:
        print(f"Error sending email: {e}")

