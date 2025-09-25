from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, EmailStr
from app.database.database import db
from app.utils.otp_utils import send_otp, verify_otp
from app.utils.email_utils import send_account_recovery_credentials
import bcrypt
import secrets
import uuid

router = APIRouter()

class RecoveryRequest(BaseModel):
    company_name: str
    email: EmailStr

class RecoveryVerification(BaseModel):
    company_name: str
    email: EmailStr
    otp_code: str

@router.post("/request-otp", status_code=status.HTTP_200_OK)
async def request_recovery_otp(payload: RecoveryRequest):
    company = db.companies.find_one({"email": payload.email, "company_name": payload.company_name})
    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="If your company details are correct, an OTP will be sent.")

    phone_full = company["primary_phone"]
    send_status = send_otp(phone_full if phone_full.startswith("+") else f"+91{phone_full}")
    if send_status not in ("pending", "sent"):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not send OTP. Please try again later.")

    return {"message": "OTP has been sent to the registered primary phone number."}

@router.post("/verify-otp-and-reset", status_code=status.HTTP_200_OK)
async def verify_otp_and_reset(payload: RecoveryVerification):
    company = db.companies.find_one({"email": payload.email, "company_name": payload.company_name})
    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found.")

    phone_full = company["primary_phone"]
    if not verify_otp(phone_full if phone_full.startswith("+") else f"+91{phone_full}", payload.otp_code):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid OTP provided.")

    new_password = secrets.token_urlsafe(8)
    hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    session_invalidator = str(uuid.uuid4())

    db.companies.update_one(
        {"_id": company["_id"]},
        {
            "$set": {
                "password": hashed_password,
                "must_change_password": True, 
                "session_invalidator": session_invalidator
            }
        }
    )

    send_account_recovery_credentials(
        to_email=company["email"],
        company_name=company["company_name"],
        username=company["username"],
        new_password=new_password
    )

    return {"message": "Account recovered successfully. Please check your email for new login credentials."}
