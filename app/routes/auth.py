# app/routes/auth.py

from fastapi import APIRouter, HTTPException, status, Depends, Response, Body, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from app.utils.jwt_utils import create_refresh_token, verify_refresh_token, create_access_token
import jwt
from app.models.login import LoginRequest, OTPVerifyRequest
from app.database.database import db
from app.utils.jwt_utils import create_access_token
from app.utils.otp_utils import send_otp, verify_otp
from app.models.reset_password import PasswordResetRequest, PasswordResetConfirm
from app.utils.reset_utils import generate_reset_token, get_token_expiry
from app.utils.email_utils import send_reset_email
from datetime import datetime
import bcrypt
from app.config import JWT_SECRET_KEY, JWT_ALGORITHM 

router = APIRouter()

class TokenRefreshRequest(BaseModel):
    refresh_token: str

@router.post("/login")
async def login(payload: LoginRequest):
    identifier = payload.identifier.strip()
    password = payload.password

    admin = db.admins.find_one({"$or": [{"username": identifier}, {"email": identifier}]})

    if admin:
        if not bcrypt.checkpw(password.encode('utf-8'), admin["password"].encode('utf-8')):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username/email or password")
        
        phone_full = admin["primary_phone"]
        send_status = send_otp(phone_full if phone_full.startswith("+") else f"+91{phone_full}")
        if send_status not in ("pending", "sent"):
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unable to send OTP")
        return {
            "message": "OTP sent to admin phone",
            "role": "admin",
            "identifier": identifier
        }

    company = db.companies.find_one({"$or":[{"username": identifier}, {"email": identifier}]})
    if company:
        if not bcrypt.checkpw(password.encode('utf-8'), company["password"].encode('utf-8')):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username/email or password")

        if company.get("status") != "active":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your account is not active yet. Please wait for admin approval.",
            )

        phone_full = company["primary_phone"]
        send_status = send_otp(phone_full if phone_full.startswith("+") else f"+91{phone_full}")
        if send_status not in ("pending", "sent"):
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unable to send OTP to company phone")

        return {
            "message": "OTP sent to company phone",
            "role": "company",
            "identifier": identifier
        }

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

@router.post("/verify-login-otp")
async def verify_login_otp(payload: OTPVerifyRequest):
    identifier = payload.identifier.strip()
    code = payload.otp_code

    admin = db.admins.find_one({"$or":[{"username": identifier}, {"email": identifier}]})
    if admin:
        phone_full = admin["primary_phone"]
        if verify_otp(phone_full if phone_full.startswith("+") else f"+91{phone_full}", code):
            token_data = {
                "sub": admin["username"],
                "role": "admin",
                "name": admin["name"]
            }
            token = create_access_token(token_data)
            return {
                "message": "Admin authenticated",
                "access_token": token,
                "role": "admin"
            }
        else:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid OTP")

    company = db.companies.find_one({"$or":[{"username": identifier}, {"email": identifier}]})
    if company:
        phone_full = company["primary_phone"]
        if verify_otp(phone_full if phone_full.startswith("+") else f"+91{phone_full}", code):
            token_data = {
                "sub": company["username"],
                "role": "company",
                "company_id": str(company["_id"]),
                "name": company["company_name"],
                "must_change_password": company.get("must_change_password", False) 
            }
            token = create_access_token(token_data)
            return {
                "message": "Company authenticated",
                "access_token": token,
                "role": "company"
            }
        else:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid OTP")

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

@router.post("/request-password-reset")
async def request_password_reset(payload: PasswordResetRequest):
    identifier = payload.identifier.strip()

    admin = db.admins.find_one({"$or": [{"email": identifier}, {"username": identifier}]})
    if admin:
        token = generate_reset_token()
        expiry = get_token_expiry()

        db.admins.update_one(
            {"_id": admin["_id"]},
            {"$set": {"reset_token": token, "reset_token_expiry": expiry}}
        )

        send_reset_email(admin["email"], token, identifier, "admin")
        return {"message": "If your email or username exists, a reset link has been sent."}

    company = db.companies.find_one({"$or": [{"email": identifier}, {"username": identifier}]})
    if company:
        token = generate_reset_token()
        expiry = get_token_expiry()

        db.companies.update_one(
            {"_id": company["_id"]},
            {"$set": {"reset_token": token, "reset_token_expiry": expiry}}
        )

        send_reset_email(company["email"], token, identifier, "company")
        return {"message": "If your email or username exists, a reset link has been sent."}

    return {"message": "If your email or username exists, a reset link has been sent."}


@router.post("/reset-password")
async def reset_password(payload: PasswordResetConfirm):
    identifier = payload.identifier.strip()
    token = payload.token.strip()
    new_password = payload.new_password.strip()

    if len(new_password) < 6:
        raise HTTPException(status_code=400, detail="Password too short. Must be at least 6 characters.")

    admin = db.admins.find_one({"$or": [{"email": identifier}, {"username": identifier}]})
    if admin:
        if admin.get("reset_token") != token or admin.get("reset_token_expiry") < datetime.utcnow():
            raise HTTPException(status_code=400, detail="Invalid or expired token")

        hashed_pw = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()

        db.admins.update_one(
            {"_id": admin["_id"]},
            {
                "$set": {"password": hashed_pw},
                "$unset": {"reset_token": "", "reset_token_expiry": ""}
            }
        )
        return {"message": "Password reset successful"}

    company = db.companies.find_one({"$or": [{"email": identifier}, {"username": identifier}]})
    if company:
        if company.get("reset_token") != token or company.get("reset_token_expiry") < datetime.utcnow():
            raise HTTPException(status_code=400, detail="Invalid or expired token")

        hashed_pw = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()

        db.companies.update_one(
            {"_id": company["_id"]},
            {
                "$set": {"password": hashed_pw},
                "$unset": {"reset_token": "", "reset_token_expiry": ""}
            }
        )
        return {"message": "Password reset successful"}

    raise HTTPException(status_code=404, detail="User not found")

@router.post("/refresh-token")
async def refresh_access_token(request: TokenRefreshRequest):
    payload = verify_refresh_token(request.refresh_token)
    user_data = {k: v for k, v in payload.items() if k not in ("exp", "iat", "type")}
    new_access_token = create_access_token(user_data)
    new_refresh_token = create_refresh_token(user_data)
    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer"
    }