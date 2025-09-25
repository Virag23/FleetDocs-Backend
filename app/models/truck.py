from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date, datetime
from bson import ObjectId
from pydantic_core import core_schema

class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate
    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid objectid")
        return ObjectId(v)
    @classmethod
    def __get_pydantic_json_schema__(
        cls, core_schema: core_schema.CoreSchema, handler
    ):
        return core_schema.StringSchema(
            min_length=24,
            max_length=24,
            pattern='^[0-9a-fA-F]{24}$',
        )

class RCDetails(BaseModel):
    issue_date: Optional[date] = None
    expiry_date: Optional[date] = None
    s3_url: str

class PUCDetails(BaseModel):
    number: Optional[str] = None
    issue_date: Optional[date] = None
    expiry_date: Optional[date] = None
    s3_url: str

class TaxDetails(BaseModel):
    number: Optional[str] = None
    issue_date: Optional[date] = None
    expiry_date: Optional[date] = None
    s3_url: str

class InsuranceDetails(BaseModel):
    number: Optional[str] = None
    issue_date: Optional[date] = None
    expiry_date: Optional[date] = None
    s3_url: str

class NationalPermitDetails(BaseModel):
    number: Optional[str] = None
    issue_date: Optional[date] = None
    expiry_date: Optional[date] = None
    s3_url: str

class StatePermitDetails(BaseModel):
    number: Optional[str] = None
    issue_date: Optional[date] = None
    expiry_date: Optional[date] = None
    s3_url: str

class FitnessDetails(BaseModel):
    number: Optional[str] = None
    application_no: Optional[str] = None
    issue_date: Optional[date] = None
    main_expiry_date: Optional[date] = None
    next_inspection_due_date: Optional[date] = None
    s3_url: str

class EmiDetails(BaseModel):
    total_loan_amount: float
    emi_per_month: float
    emi_start_date: date
    emi_end_date: date
    completed_installments: int = 0

class AllDocuments(BaseModel):
    rc: RCDetails
    puc: PUCDetails
    tax: TaxDetails
    insurance: InsuranceDetails
    national_permit: NationalPermitDetails
    state_permit: StatePermitDetails
    fitness: FitnessDetails

class TruckBase(BaseModel):
    truck_number: str
    model_number: str
    engine_number: str
    chassis_number: str
    registration_date: date
    tire_count: int
    truck_photo_url: str
    company_id: PyObjectId = Field(alias="company_id")
    documents: AllDocuments
    emi_details: Optional[EmiDetails] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class TruckInDB(TruckBase):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")

class TruckOut(TruckInDB):
    class Config:
        json_encoders = {ObjectId: str}

