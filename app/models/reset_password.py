# app/models/reset_password.py

from pydantic import BaseModel, EmailStr
from typing import Optional

class PasswordResetRequest(BaseModel):
    identifier: str

class PasswordResetConfirm(BaseModel):
    identifier: str
    token: str
    new_password: str
