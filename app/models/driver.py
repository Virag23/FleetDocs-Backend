from pydantic import BaseModel, Field, EmailStr
from typing import Optional
from datetime import date, datetime
from bson import ObjectId
from app.models.truck import PyObjectId 

class LicenseDetails(BaseModel):
    """Holds all the data extracted from the driving license."""
    license_number: str
    name_on_license: str
    issue_date: Optional[date] = None
    validity_nt: Optional[date] = None 
    validity_tr: Optional[date] = None 
    s3_url: str

class DriverBase(BaseModel):
    """Core fields for a driver."""
    first_name: str = Field(..., description="Driver's first name.")
    last_name: str = Field(..., description="Driver's last name.")
    email: Optional[EmailStr] = Field(None, description="Driver's email address (optional).")
    phone_number: str = Field(..., description="Driver's 10-digit mobile number.")
    driver_photo_url: str = Field(..., description="URL of the uploaded driver's photo.")
    company_id: PyObjectId = Field(..., alias="company_id")
    license: LicenseDetails
    created_at: datetime = Field(default_factory=datetime.utcnow)

class DriverInDB(DriverBase):
    """Model for data as stored in MongoDB."""
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")

class DriverOut(DriverInDB):
    """Model for API responses, converting ObjectId to string."""
    class Config:
        json_encoders = {ObjectId: str}
        populate_by_name = True

class DriverUpdate(BaseModel):
    """Model for updating a driver's phone number."""
    phone_number: str = Field(..., description="Driver's new 10-digit mobile number.")
