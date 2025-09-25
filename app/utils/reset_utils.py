# app/utils/reset_utils.py

import secrets
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

load_dotenv()

RESET_TOKEN_EXPIRE_MINUTES = int(os.getenv("RESET_TOKEN_EXPIRE_MINUTES", "60"))

def generate_reset_token():
    return secrets.token_urlsafe(32)

def get_token_expiry():
    return datetime.utcnow() + timedelta(minutes=RESET_TOKEN_EXPIRE_MINUTES)
