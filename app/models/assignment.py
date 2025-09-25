from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from bson import ObjectId
from app.models.truck import PyObjectId, TruckOut
from app.models.driver import DriverOut

class AssignmentBase(BaseModel):
    """Core fields for creating an assignment."""
    truck_id: PyObjectId = Field(..., alias="truckId")
    driver_id: PyObjectId = Field(..., alias="driverId")
    type_of_load: Optional[str] = Field(None, description="Type of goods being transported.")
    origin: Optional[str] = Field(None, description="Starting point of the job.")
    destination: Optional[str] = Field(None, description="Ending point of the job.")

class AssignmentCreate(AssignmentBase):
    """Model for API request to create an assignment."""
    pass

class AssignmentInDB(AssignmentBase):
    """Model for data as stored in MongoDB."""
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    company_id: PyObjectId = Field(..., alias="company_id")
    assignment_date: datetime = Field(default_factory=datetime.utcnow)
    status: str = Field("active", description="Status can be 'active' or 'history'.")
    completed_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class AssignmentOut(BaseModel):
    """
    Model for API responses, with full truck and driver details populated.
    This is not a direct DB model but a representation of aggregated data.
    """
    id: str
    truck: TruckOut
    driver: DriverOut
    status: str
    assignment_date: datetime
    completed_at: Optional[datetime] = None
    type_of_load: Optional[str] = None
    origin: Optional[str] = None
    destination: Optional[str] = None
    
    class Config:
        populate_by_name = True
