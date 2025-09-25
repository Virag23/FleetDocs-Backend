# app/models/company.py

from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

class CompanyBase(BaseModel):
    company_name: str
    owner_name: str
    email: EmailStr
    primary_phone: str
    secondary_phones: Optional[list[str]] = []
    address: Optional[str] = None
    logo_url: Optional[str] = None

class CompanyCreate(CompanyBase):
    pass 

class CompanyOut(CompanyBase):
    id: str
    status: str
    submitted_at: datetime
    payment_due_at: Optional[datetime] = None
    payment_reminder_sent: Optional[bool] = False
    must_change_password: Optional[bool] = False
    onboarding_complete: Optional[bool] = False # <-- ADD THIS FIELD
    username: Optional[str] = None

class CredentialRequest(BaseModel):
    amount: float 

class SetCredentialsRequest(BaseModel):
    username: Optional[str] 
    password: Optional[str]
