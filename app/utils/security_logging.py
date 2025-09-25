# app/utils/security_logging.py

import logging

security_logger = logging.getLogger("security")

def log_login_attempt(email: str, success: bool, ip: str):
    security_logger.info(f"Login attempt for {email} from IP {ip} - {'SUCCESS' if success else 'FAILURE'}")

def log_password_reset_request(email: str, ip: str):
    security_logger.info(f"Password reset requested for {email} from IP {ip}")

def log_otp_request(phone: str, ip: str):
    security_logger.info(f"OTP requested for {phone} from IP {ip}")

def log_otp_verification(phone: str, success: bool, ip: str):
    security_logger.info(f"OTP verification for {phone} from IP {ip} - {'SUCCESS' if success else 'FAILURE'}")

def log_credential_change(email: str, change_type: str, ip: str):
    security_logger.info(f"Credential {change_type} for {email} from IP {ip}")
