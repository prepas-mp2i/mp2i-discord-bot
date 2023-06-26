from email.message import EmailMessage
import smtplib
import ssl
import logging
import os
import random
import re

from mp2i import STATIC_DIR

logger = logging.getLogger(__name__)

__SMTP_SERVER = os.getenv("SMTP_SERVER")
__PORT = 465  # For SSL
__EMAIL_USER = os.getenv("EMAIL_USER")
__EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

if __SMTP_SERVER and __EMAIL_USER and __EMAIL_PASSWORD:
    context = ssl.create_default_context()
else:
    logger.warning(
        "You have not specified all emails environment. "
        "Role automation will not work properly."
    )

ACADEMIC_EMAIL_PATTERN = re.compile(r"^[a-zA-Z0-9_.-]+@([a-z.-]+)$")

with open(STATIC_DIR / "text/academies.txt") as f:
    academies = f.read().splitlines()


def is_academic_email(email: str) -> bool:
    """
    Check if an email is an academic email
    """
    if match := ACADEMIC_EMAIL_PATTERN.match(email):
        return match.group(1) in academies


def send(receiver_email: str, message: str) -> bool:
    """
    Send an email from credentials in .env
    """
    if not (__SMTP_SERVER and __EMAIL_USER and __EMAIL_PASSWORD):
        return False

    email = EmailMessage()
    email["Subject"] = "Vérification de votre adresse email"
    email["From"] = __EMAIL_USER
    email["To"] = receiver_email
    email.set_content(message)
    try:
        with smtplib.SMTP_SSL(__SMTP_SERVER, __PORT, context=context) as server:
            server.login(__EMAIL_USER, __EMAIL_PASSWORD)
            server.send_message(email)
        return True
    except Exception as e:
        logger.error(e)
        return False


def generate_verification_code() -> str:
    """
    Generate a random 6 digit code
    """
    return str(random.randint(100000, 999999))
