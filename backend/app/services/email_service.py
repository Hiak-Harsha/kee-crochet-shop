import logging
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)

async def send_otp_email(to_email: str, code: str) -> bool:
    """
    Send OTP code via Resend transactional email API if key exists,
    otherwise print to console/logs as a simulation fallback.
    """
    subject = "Your Kee Crochet Verification Code"
    html_content = f"""
    <div style="font-family: 'Inter', sans-serif; max-width: 600px; margin: auto; padding: 30px; border: 1px solid #e2e8f0; border-radius: 16px; background-color: #ffffff;">
      <h2 style="color: #d97706; margin-bottom: 20px;">Kee Crochet Verification</h2>
      <p style="font-size: 14px; color: #4a5568; line-height: 1.6;">
        Welcome to Kee Crochet! Use the verification code below to complete your login or registration.
      </p>
      <div style="margin: 25px 0; padding: 15px; background-color: #fef3c7; border: 1px solid #fde68a; border-radius: 12px; text-align: center;">
        <span style="font-size: 32px; font-weight: 800; font-family: monospace; letter-spacing: 4px; color: #b45309;">{code}</span>
      </div>
      <p style="font-size: 12px; color: #718096;">
        This code will expire in {settings.OTP_EXPIRE_MINUTES} minutes. If you did not request this code, please ignore this email.
      </p>
      <hr style="border: 0; border-top: 1px solid #edf2f7; margin: 25px 0;" />
      <p style="font-size: 10px; color: #a0aec0; text-align: center;">
        Kee Crochet • Premium Handcrafted Crochet Store
      </p>
    </div>
    """
    
    if not settings.RESEND_API_KEY:
        # Highlighted log console fallback for local/sandbox runs
        logger.critical(
            f"\n"
            f"========================================================================\n"
            f"📧 [EMAIL SIMULATION] - TRANSCRIPTION DETAILS\n"
            f"------------------------------------------------------------------------\n"
            f"Recipient : {to_email}\n"
            f"Sender    : {settings.MAIL_FROM}\n"
            f"Subject   : {subject}\n"
            f"OTP Code  : {code}\n"
            f"========================================================================\n"
        )
        return True

    url = "https://api.resend.com/emails"
    headers = {
        "Authorization": f"Bearer {settings.RESEND_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "from": settings.MAIL_FROM,
        "to": [to_email],
        "subject": subject,
        "html": html_content
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=payload)
            if response.status_code == 200 or response.status_code == 201:
                logger.info(f"OTP email successfully dispatched to {to_email} via Resend.")
                return True
            else:
                logger.error(f"Resend email dispatch failed (HTTP {response.status_code}): {response.text}")
                return False
    except Exception as e:
        logger.error(f"Failed to connect to Resend API: {e}")
        return False


async def send_welcome_email(to_email: str, full_name: str | None) -> bool:
    """
    Send a welcome email to newly registered users via Resend if key exists,
    otherwise print a simulation fallback.
    """
    name_str = full_name or "Craft Lover"
    subject = "Welcome to Kee Crochet! 🧶"
    html_content = f"""
    <div style="font-family: 'Inter', sans-serif; max-width: 600px; margin: auto; padding: 30px; border: 1px solid #e2e8f0; border-radius: 16px; background-color: #ffffff;">
      <h2 style="color: #d97706; margin-bottom: 20px;">Welcome to Kee Crochet!</h2>
      <p style="font-size: 14px; color: #4a5568; line-height: 1.6;">
        Hi {name_str},
      </p>
      <p style="font-size: 14px; color: #4a5568; line-height: 1.6;">
        Thank you for joining our community of handcrafted crochet lovers. Your account has been successfully verified and activated!
      </p>
      <p style="font-size: 14px; color: #4a5568; line-height: 1.6;">
        Explore our cozy collections of flower bouquets, custom-stitched plushies, and keychains today. If you need any assistance, our AI Personal Shopper "Kee" is always online to help you find the perfect gift!
      </p>
      <hr style="border: 0; border-top: 1px solid #edf2f7; margin: 25px 0;" />
      <p style="font-size: 10px; color: #a0aec0; text-align: center;">
        Kee Crochet • Premium Handcrafted Crochet Store
      </p>
    </div>
    """
    
    if not settings.RESEND_API_KEY:
        logger.critical(
            f"\n"
            f"========================================================================\n"
            f"📧 [EMAIL SIMULATION] - WELCOME EMAIL\n"
            f"------------------------------------------------------------------------\n"
            f"Recipient : {to_email}\n"
            f"Sender    : {settings.MAIL_FROM}\n"
            f"Subject   : {subject}\n"
            f"Message   : Welcome to Kee Crochet, {name_str}! Account activated.\n"
            f"========================================================================\n"
        )
        return True

    url = "https://api.resend.com/emails"
    headers = {
        "Authorization": f"Bearer {settings.RESEND_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "from": settings.MAIL_FROM,
        "to": [to_email],
        "subject": subject,
        "html": html_content
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=payload)
            if response.status_code == 200 or response.status_code == 201:
                logger.info(f"Welcome email successfully dispatched to {to_email} via Resend.")
                return True
            else:
                logger.error(f"Resend welcome email failed (HTTP {response.status_code}): {response.text}")
                return False
    except Exception as e:
        logger.error(f"Failed to connect to Resend API: {e}")
        return False
