# models/contact.py
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr
from typing import List, Optional

router = APIRouter()

class ContactRequest(BaseModel):
    company_name: str
    owner_name: str
    email: EmailStr
    primary_phone: str
    secondary_phones: Optional[List[str]] = []
    address: Optional[str] = None
    logo_url: Optional[str] = None

@router.post("/", status_code=status.HTTP_201_CREATED)
def submit_contact_form(payload: ContactRequest):
    return {
        "message": "Contact request received!",
        "data": payload.dict()
    }