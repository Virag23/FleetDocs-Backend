# app/models/admin.py
from pydantic import BaseModel, EmailStr

class AdminModel(BaseModel):
    name: str
    username: str
    email: EmailStr
    phone: str
    password: str
