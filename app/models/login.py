# app/models/login.py
from pydantic import BaseModel

class LoginRequest(BaseModel):
    identifier: str   
    password: str  

class OTPVerifyRequest(BaseModel):
    identifier: str  
    otp_code: str
