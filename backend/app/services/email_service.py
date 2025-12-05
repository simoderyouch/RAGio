import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pydantic import EmailStr
from fastapi import HTTPException
from app.config import SMTP_HOST, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD, HOST
import logging

logger = logging.getLogger("hcp_backend")


def send_email(email: EmailStr, subject: str, message: str):
    """
    Send an email to the provided email address with the given subject and message.

    Reads SMTP settings from `app.config` so you can supply an App Password
    for Gmail or switch to another provider via environment variables.
    """

    smtp_server = SMTP_HOST or 'smtp.gmail.com'
    smtp_port = int(SMTP_PORT or 587)
    smtp_username = SMTP_USERNAME
    smtp_password = SMTP_PASSWORD

    if not smtp_username or not smtp_password:
        logger.error("SMTP credentials are not configured (SMTP_USERNAME/SMTP_PASSWORD).")
        raise HTTPException(status_code=500, detail="SMTP credentials are not configured")

    msg = MIMEMultipart('alternative')
    msg['From'] = smtp_username
    msg['To'] = email
    msg['Subject'] = subject
    msg.attach(MIMEText(message, 'html'))

    try:
        # Use SSL for port 465, otherwise use STARTTLS
        if smtp_port == 465:
            server = smtplib.SMTP_SSL(smtp_server, smtp_port)
            server.login(smtp_username, smtp_password)
        else:
            server = smtplib.SMTP(smtp_server, smtp_port, timeout=10)
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(smtp_username, smtp_password)

        server.sendmail(smtp_username, email, msg.as_string())
        server.quit()
    except smtplib.SMTPAuthenticationError as e:
        # Common with Gmail when App Password or browser verification is required
        logger.error(f"SMTP auth error: {e}")
        raise HTTPException(status_code=500, detail="SMTP authentication failed. For Gmail, create an App Password and use it as SMTP_PASSWORD.")
    except Exception as e:
        logger.exception("Unexpected error sending email")
        raise HTTPException(status_code=500, detail=str(e))



def send_verification_email(email: EmailStr, verification_token: str):
    """
    Send a verification email to the provided email address with a verification token.
    """
    subject = "Verify Your Email"
    verification_link = f"{HOST}/api/auth/verify-email/{verification_token}"
    message = f"""
    <html>
    <body>
        <p>Please click the following link to verify your email:</p>
        <form action="{verification_link}" method="get">
            <button type="submit">Verify Email</button>
        </form>
        <p>If you cannot click the button, copy and paste the following link into your browser:</p>
        <a href="{verification_link}">{verification_link}</a>
    </body>
    </html>
    """
    send_email(email, subject, message)