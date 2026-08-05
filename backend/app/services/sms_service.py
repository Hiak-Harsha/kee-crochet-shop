import logging
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)

async def send_otp_sms(phone_number: str, code: str) -> bool:
    """
    Send OTP code via SMS using Twilio or MSG91 if configured,
    otherwise print to console/logs as a simulation fallback.
    """
    clean_phone = "".join(c for c in phone_number if c.isdigit())
    
    # Twilio integration
    if settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN and settings.TWILIO_FROM_NUMBER:
        url = f"https://api.twilio.com/2010-04-01/Accounts/{settings.TWILIO_ACCOUNT_SID}/Messages.json"
        auth = (settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        to_number = phone_number if phone_number.startswith("+") else f"+91{clean_phone[-10:]}"
        payload = {
            "From": settings.TWILIO_FROM_NUMBER,
            "To": to_number,
            "Body": f"Your Kee Crochet verification code is {code}. It expires in {settings.OTP_EXPIRE_MINUTES} minutes."
        }
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, auth=auth, data=payload)
                if response.status_code == 201:
                    logger.info(f"OTP SMS successfully dispatched to {to_number} via Twilio.")
                    return True
                else:
                    logger.error(f"Twilio SMS dispatch failed (HTTP {response.status_code}): {response.text}")
                    return False
        except Exception as e:
            logger.error(f"Failed to connect to Twilio SMS API: {e}")
            return False

    # MSG91 integration
    elif settings.MSG91_AUTH_KEY and settings.MSG91_TEMPLATE_ID:
        url = "https://control.msg91.com/api/v5/otp"
        headers = {
            "authkey": settings.MSG91_AUTH_KEY,
            "Content-Type": "application/json"
        }
        to_number = clean_phone[-10:] if len(clean_phone) >= 10 else clean_phone
        payload = {
            "template_id": settings.MSG91_TEMPLATE_ID,
            "mobile": f"91{to_number}",
            "otp": code
        }
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, headers=headers, json=payload)
                if response.status_code == 200:
                    logger.info(f"OTP SMS successfully dispatched to 91{to_number} via MSG91.")
                    return True
                else:
                    logger.error(f"MSG91 SMS dispatch failed (HTTP {response.status_code}): {response.text}")
                    return False
        except Exception as e:
            logger.error(f"Failed to connect to MSG91 SMS API: {e}")
            return False

    # Fallback log console simulation
    else:
        display_number = phone_number if phone_number.startswith("+") else f"+91 {clean_phone[-10:-5]} {clean_phone[-5:]}"
        logger.critical(
            f"\n"
            f"========================================================================\n"
            f"📱 [SMS SIMULATION] - TRANSCRIPTION DETAILS\n"
            f"------------------------------------------------------------------------\n"
            f"Recipient : {display_number}\n"
            f"Message   : Your Kee Crochet verification code is {code}. Expires in {settings.OTP_EXPIRE_MINUTES} mins.\n"
            f"========================================================================\n"
        )
        return True
