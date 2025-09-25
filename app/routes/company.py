from fastapi import APIRouter, Depends, HTTPException, Header, status, Response, Body, Request
from app.database.database import db
from app.utils.jwt_utils import verify_access_token, extract_token_from_header, create_refresh_token, verify_refresh_token, create_access_token
from bson import ObjectId
from pydantic import BaseModel, EmailStr, Field, constr, validator
from typing import List, Optional
from datetime import datetime, timedelta
from fastapi.responses import JSONResponse
from app.models.login import LoginRequest, OTPVerifyRequest
from app.utils.otp_utils import send_otp, verify_otp
from app.models.reset_password import PasswordResetRequest, PasswordResetConfirm
from app.utils.email_utils import send_password_change_notification, send_profile_update_email, send_contact_confirmation_email, send_reset_email
from app.utils.jwt_utils import JWT_SECRET_KEY, JWT_ALGORITHM
from datetime import datetime
import bcrypt
import jwt

router = APIRouter()

async def get_current_company(authorization: str = Header(...)):
    """
    Dependency to verify JWT token and get current company data.
    This protects endpoints and provides company context.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid authorization header.")
    
    token = authorization.split(" ")[1]
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        if payload.get("role") != "company":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized for this resource.")
        
        company_id = payload.get("company_id")
        if not company_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token: Missing company ID.")

        company_data = db.companies.find_one({"_id": ObjectId(company_id)})
        if not company_data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found.")

        return {"company_id": str(company_data["_id"]), "company_data": company_data, **payload}

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired.")
    except (jwt.PyJWTError, KeyError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials.")

class ProfileData(BaseModel):
    company_name: str
    owner_name: str
    email: Optional[EmailStr] = None
    primary_phone: Optional[str] = None
    secondary_phones: List[str] = Field(default=[])
    address: Optional[str] = None
    logo_url: Optional[str] = None

    @validator('secondary_phones')
    def validate_phones(cls, v):
        for phone in v:
            if not phone.isdigit():
                raise ValueError('Secondary phone numbers must contain only digits.')
        return v

class ProfileUpdateRequest(BaseModel):
    company_name: str
    owner_name: str
    secondary_phones: List[str]
    address: Optional[str]
    logo_url: Optional[str]

class ProfileUpdateConfirmRequest(BaseModel):
    otp_code: str
    updated_data: ProfileUpdateRequest

class PasswordChangeRequest(BaseModel):
    new_password: str

class RunningAssignment(BaseModel):
    truck_number: str
    truck_photo_url: Optional[str] = None
    driver_name: str
    driver_photo_url: Optional[str] = None
    assignment_date: datetime

class DashboardStats(BaseModel):
    total_trucks: int
    total_drivers: int
    expiring_documents: int
    active_assignments: int
    running_assignments: List[RunningAssignment]

class PasswordChangeRequest(BaseModel):
    new_password: str

async def get_current_company(authorization: str = Header(...)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid authorization header.")
    
    token = authorization.split(" ")[1]
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        if payload.get("role") != "company":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized.")
        
        company_id = payload.get("company_id")
        if not company_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload.")

        company_data = db.companies.find_one({"_id": ObjectId(company_id)})
        if not company_data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found.")

        token_session_key = payload.get("session_key")
        db_session_key = company_data.get("session_invalidator", "")
        if token_session_key != db_session_key:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired. Please log in again.")

        return {"company_id": str(company_data["_id"]), "company_data": company_data, **payload}

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired.")
    except (jwt.PyJWTError, KeyError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials.")


class RunningAssignment(BaseModel):
    truck_number: str
    truck_photo_url: Optional[str] = None
    driver_name: str
    driver_photo_url: Optional[str] = None
    assignment_date: datetime

class DashboardStats(BaseModel):
    total_trucks: int
    total_drivers: int
    expiring_documents: int
    active_assignments: int
    running_assignments: List[RunningAssignment]

@router.get("/dashboard", response_model=DashboardStats, tags=["Company"])
async def get_dashboard_data(company: dict = Depends(get_current_company)):
    """
    Fetches aggregated data for the company's dashboard.
    This single endpoint provides all necessary data for the main dashboard screen.
    """
    company_id = ObjectId(company["company_id"])
    total_trucks = db.trucks.count_documents({"company_id": company_id})
    total_drivers = db.drivers.count_documents({"company_id": company_id})
    active_assignments = db.assignments.count_documents({
        "company_id": company_id,
        "status": "running"
    })
    
    expiry_threshold_date = datetime.utcnow() + timedelta(days=7)
    expiring_count = 0
    
    company_trucks = db.trucks.find({"company_id": company_id})
    
    for truck in company_trucks:
        for doc_type, doc_details in truck.get("documents", {}).items():
            if "expiry_date" in doc_details and doc_details["expiry_date"] <= expiry_threshold_date:
                expiring_count += 1

    company_drivers = db.drivers.find({"company_id": company_id})
    for driver in company_drivers:
        license_details = driver.get("license", {})
        if "expiry_date" in license_details and license_details["expiry_date"] <= expiry_threshold_date:
            expiring_count += 1
            
    running_assignments_cursor = db.assignments.find({
        "company_id": company_id,
        "status": "running"
    }).limit(10)

    running_assignments_list = []
    for assignment in running_assignments_cursor:
        truck = db.trucks.find_one({"_id": assignment["truck_id"]}, {"truck_number": 1, "truck_photo_url": 1})
        driver = db.drivers.find_one({"_id": assignment["driver_id"]}, {"first_name": 1, "last_name": 1, "driver_photo_url": 1})

        if truck and driver:
            running_assignments_list.append(
                RunningAssignment(
                    truck_number=truck.get("truck_number"),
                    truck_photo_url=truck.get("truck_photo_url"),
                    driver_name=f"{driver.get('first_name')} {driver.get('last_name')}",
                    driver_photo_url=driver.get("driver_photo_url"),
                    assignment_date=assignment["assignment_date"]
                )
            )

    return DashboardStats(
        total_trucks=total_trucks,
        total_drivers=total_drivers,
        expiring_documents=expiring_count,
        active_assignments=active_assignments,
        running_assignments=running_assignments_list
    )

@router.post("/verify-login-otp")
async def verify_login_otp(payload: OTPVerifyRequest):
    identifier = payload.identifier.strip()
    code = payload.otp_code

    admin = db.admins.find_one({"$or":[{"username": identifier}, {"email": identifier}]})
    if admin:
        phone_full = admin["phone"]
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

@router.post("/force-change-password", status_code=status.HTTP_200_OK)
async def force_change_password(payload: PasswordChangeRequest, company: dict = Depends(get_current_company)):
    company_data = company["company_data"]
    if not company_data.get("must_change_password"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Password change not required.")

    hashed_password = bcrypt.hashpw(payload.new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    db.companies.update_one(
        {"_id": ObjectId(company["company_id"])},
        {"$set": {"password": hashed_password, "must_change_password": False}}
    )

    send_password_change_notification(to_email=company_data["email"], company_name=company_data["company_name"])
    return {"message": "Password changed successfully."}

@router.post("/complete-onboarding", status_code=status.HTTP_200_OK)
async def complete_onboarding(company: dict = Depends(get_current_company)):
    db.companies.update_one(
        {"_id": ObjectId(company["company_id"])},
        {"$set": {"onboarding_complete": True}}
    )
    return {"message": "Onboarding marked as complete."}

@router.get("/profile", response_model=ProfileData, tags=["Company"])
async def get_company_profile(company: dict = Depends(get_current_company)):
    company_data = company.get("company_data", {})
    return ProfileData(**company_data)

@router.post("/profile/request-update", status_code=status.HTTP_200_OK, tags=["Company"])
async def request_profile_update(payload: ProfileUpdateRequest, company: dict = Depends(get_current_company)):
    company_data = company.get("company_data", {})
    primary_phone = company_data.get("primary_phone")
    if not primary_phone:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Primary phone number not found.")

    phone_full = f"+91{primary_phone}"
    send_status = send_otp(phone_full)
    if send_status not in ("pending", "sent"):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not send OTP.")

    return {"message": f"An OTP has been sent to your primary phone number ending in {primary_phone[-4:]} to confirm the update."}

@router.post("/profile/confirm-update", status_code=status.HTTP_200_OK, tags=["Company"])
async def confirm_profile_update(payload: ProfileUpdateConfirmRequest, company: dict = Depends(get_current_company)):
    company_data = company.get("company_data", {})
    company_id = company.get("company_id")
    primary_phone = company_data.get("primary_phone")
    phone_full = f"+91{primary_phone}"

    if not verify_otp(phone_full, payload.otp_code):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid OTP provided.")

    update_data = payload.updated_data.dict(exclude_unset=True)
    result = db.companies.update_one({"_id": ObjectId(company_id)}, {"$set": update_data})

    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found.")
    
    final_details = {
        "Company Name": update_data.get("company_name"),
        "Owner Name": update_data.get("owner_name"),
        "Email": company_data.get("email"),
        "Primary Phone": company_data.get("primary_phone"),
        "Secondary Phones": ", ".join(update_data.get("secondary_phones", [])) or "N/A",
        "Address": update_data.get("address") or "N/A"
    }

    send_profile_update_email(
        to_email=company_data.get("email"),
        company_name=update_data.get("company_name"),
        updated_details=final_details
    )

    return {"message": "Your profile has been updated successfully."}

