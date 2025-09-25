# app/utils/otp_utils.py
from twilio.rest import Client
import os
from dotenv import load_dotenv


load_dotenv()

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_VERIFY_SID = os.getenv("TWILIO_VERIFY_SID")

client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

def send_otp(phone: str):
    verification = client.verify.v2.services(TWILIO_VERIFY_SID).verifications.create(
        to = phone,
        channel = "sms"
    )
    return verification.status

def verify_otp(phone: str, code: str):
    check = client.verify.v2.services(TWILIO_VERIFY_SID).verification_checks.create(
        to = phone,
        code = code
    )
    return check.status == "approved"
