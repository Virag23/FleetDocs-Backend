# app/models/company.py

from pydantic import BaseModel, EmailStr, Field, constr
from typing import List, Optional
from datetime import datetime

class CompanyBase(BaseModel):
    company_name: str
    owner_name: str
    email: EmailStr
    primary_phone: str
    secondary_phones: Optional[List[str]] = []
    address: Optional[str] = None
    logo_url: Optional[str] = None
    
class CompanyCreate(CompanyBase):
    pass

class CompanyInDB(CompanyBase):
    id: str = Field(..., alias="_id")
    status: str
    username: Optional[str] = None
    password: Optional[str] = None
    submitted_at: datetime
    approved_at: Optional[datetime] = None
    payment_due_at: Optional[datetime] = None
    payment_reminder_sent: bool = False
    must_change_password: bool = False
    session_invalidator: str = ""

class CompanyOut(BaseModel):
    id: str
    company_name: str
    owner_name: str
    email: EmailStr
    primary_phone: str
    secondary_phones: List[str]
    address: Optional[str] = None
    logo_url: Optional[str] = None
    status: str
    submitted_at: Optional[datetime] = None
    payment_due_at: Optional[datetime] = None
    payment_reminder_sent: bool = False
    must_change_password: bool = False
    username: Optional[str] = None

class SetCredentialsRequest(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None