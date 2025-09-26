from fastapi import APIRouter, HTTPException, status, Depends, Header
from typing import List
from datetime import datetime, timedelta
from bson import ObjectId
from app.database.database import db
from app.models.company import CompanyOut, SetCredentialsRequest
from app.utils.jwt_utils import extract_token_from_header
from app.utils.jwt_utils import verify_access_token
from app.utils.email_utils import send_email
from app.utils.reset_utils import generate_reset_token
import bcrypt
import uuid

router = APIRouter()

def get_current_admin(authorization: str = Header(...)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid auth header")
    token = extract_token_from_header(authorization)
    payload = verify_access_token(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    if payload.get("role") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    return payload

@router.post("/company-approve/{company_id}", tags=["admin"])
async def approve_company(company_id: str, admin: dict = Depends(get_current_admin)):
    result = db.companies.update_one(
        {"_id": ObjectId(company_id)},
        {"$set": {"status": "approved", "approved_at": None}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
    return {"message": "Company approved", "company_id": company_id}

@router.post("/company-reject/{company_id}", tags=["admin"])
async def reject_company(company_id: str, admin: dict = Depends(get_current_admin)):
    result = db.companies.update_one(
        {"_id": ObjectId(company_id)},
        {"$set": {"status": "rejected"}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
    return {"message": "Company rejected", "company_id": company_id}

def get_admin_payload(authorization: str = Header(...)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid auth header")
    token = extract_token_from_header(authorization)
    payload = verify_access_token(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    if payload.get("role") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    return payload

@router.get("/dashboard-stats", tags=["Admin"])
def dashboard_stats(admin: dict = Depends(get_admin_payload)):
    pending = db.contact_requests.count_documents({"status": "pending_submission"})
    under_review = db.companies.count_documents({"status": "under_review"})
    waiting_payment = db.companies.count_documents({"status": "waiting_payment"})
    active = db.companies.count_documents({"status": "active"})
    total = db.companies.count_documents({})

    recent = []
    cursor = db.contact_requests.find({"status": "pending_submission"}).sort("submitted_at", -1).limit(5)
    for c in cursor:
        recent.append({
            "id": str(c["_id"]),
            "company_name": c["company_name"],
            "status": c.get("status"),
            "submitted_at": c.get("submitted_at")
        })

    return {
        "new_requests": pending,
        "under_review": under_review,
        "waiting_payment": waiting_payment,
        "active_companies": active,
        "total_companies": total,
        "recent_requests": recent
    }

@router.get("/companies", response_model=List[CompanyOut], tags=["Admin"])
def list_companies(status: str = None, admin: dict = Depends(get_admin_payload)):
    query = {}
    if status:
        query["status"] = status
    docs = db.companies.find(query)
    out = []
    for c in docs:
        c_out = CompanyOut(
            id=str(c["_id"]),
            company_name=c["company_name"],
            owner_name=c["owner_name"],
            email=c["email"],
            primary_phone=c["primary_phone"],
            secondary_phones=c.get("secondary_phones", []),
            address=c.get("address"),
            logo_url=c.get("logo_url"),
            status=c.get("status"),
            submitted_at=c.get("submitted_at"),
            payment_due_at=c.get("payment_due_at"),
            payment_reminder_sent=c.get("payment_reminder_sent", False),
            must_change_password=c.get("must_change_password", False),
            username=c.get("username")
        )
        out.append(c_out)
    return out

@router.get("/company/{company_id}", response_model=CompanyOut, tags=["Admin"])
def get_company(company_id: str, admin: dict = Depends(get_admin_payload)):
    c = db.companies.find_one({"_id": ObjectId(company_id)})
    if not c:
        raise HTTPException(status_code=404, detail="Company not found")
    return CompanyOut(
        id=str(c["_id"]),
        company_name=c["company_name"],
        owner_name=c["owner_name"],
        email=c["email"],
        primary_phone=c["primary_phone"],
        secondary_phones=c.get("secondary_phones", []),
        address=c.get("address"),
        logo_url=c.get("logo_url"),
        status=c.get("status"),
        submitted_at=c.get("submitted_at"),
        payment_due_at=c.get("payment_due_at"),
        payment_reminder_sent=c.get("payment_reminder_sent", False),
        must_change_password=c.get("must_change_password", False),
        username=c.get("username")
    )

@router.post("/company/{company_id}/review", tags=["Admin"])
def review_company(company_id: str, admin: dict = Depends(get_admin_payload)):
    result = db.companies.update_one(
        {"_id": ObjectId(company_id), "status": "pending_submission"},
        {"$set": {"status": "under_review"}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=400, detail="Company not in pending state or not found")
    return {"message": "Company marked as under review"}

@router.delete("/company/{company_id}", tags=["Admin"])
def delete_company(company_id: str, admin: dict = Depends(get_admin_payload)):
    result = db.companies.delete_one({"_id": ObjectId(company_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Company not found")
    return {"message": "Company rejected and deleted"}

@router.post("/company/{company_id}/send-payment", tags=["Admin"])
def send_payment_details(company_id: str, admin: dict = Depends(get_admin_payload)):
    c = db.companies.find_one({"_id": ObjectId(company_id)})
    if not c:
        raise HTTPException(status_code=404, detail="Company not found")

    if c.get("status") != "under_review":
        raise HTTPException(status_code=400, detail="Company not in under_review state")

    due_time = datetime.utcnow() + timedelta(hours=6)
    db.companies.update_one(
        {"_id": ObjectId(company_id)},
        {"$set": {
            "status": "waiting_payment",
            "payment_due_at": due_time,
            "payment_reminder_sent": False
        }}
    )

    subject = "FleetDocs – Payment Instructions"
    body = f"""
        Hi {c.get('owner_name')},

        Your company {c.get('company_name')} has been approved for registration of FleetDocs.

        Please complete the payment within 6 hours. After that, your request will be re-queued.

        Payment details:
        [Insert your payment link / QR code / bank details]

        After payment, admin will set your login credentials and you’ll receive an email.

        Thank you,
        FleetDocs Team
        """
    send_email(c.get("email"), subject, body)

    return {"message": "Payment instructions sent", "payment_due_at": due_time}

@router.post("/company/{company_id}/remind-payment", tags=["Admin"])
def remind_payment(company_id: str, admin: dict = Depends(get_admin_payload)):
    c = db.companies.find_one({"_id": ObjectId(company_id)})
    if not c:
        raise HTTPException(status_code=404, detail="Company not found")
    if c.get("status") != "waiting_payment":
        raise HTTPException(status_code=400, detail="Company not waiting payment")

    if c.get("payment_reminder_sent"):
        raise HTTPException(status_code=400, detail="Reminder already sent")

    subject = "Reminder: FleetDocs Payment Due"
    body = f"""
        Hi {c.get('owner_name')},

        This is a reminder to complete your payment for FleetDocs registration for {c.get('company_name')}. Please complete within remaining time.

        Payment details are the same as previously sent.

        Thank you,
        FleetDocs Team
        """
    send_email(c.get("email"), subject, body)

    db.companies.update_one(
        {"_id": ObjectId(company_id)},
        {"$set": {"payment_reminder_sent": True}}
    )

    return {"message": "Payment reminder sent"}

@router.post("/company/{company_id}/confirm-payment", tags=["Admin"])
def confirm_payment(company_id: str, admin: dict = Depends(get_admin_payload)):
    c = db.companies.find_one({"_id": ObjectId(company_id)})
    if not c:
        raise HTTPException(status_code=404, detail="Company not found")

    if c.get("status") != "waiting_payment":
        raise HTTPException(status_code=400, detail="Not in waiting payment state")

    db.companies.update_one(
        {"_id": ObjectId(company_id)},
        {"$set": {"status": "ready_for_credentials"}}
    )
    return {"message": "Payment confirmed, ready for credential setup"}

@router.post("/company/{company_id}/set-credentials", tags=["Admin"])
def set_credentials(company_id: str, payload: SetCredentialsRequest, admin: dict = Depends(get_admin_payload)):
    c = db.companies.find_one({"_id": ObjectId(company_id)})
    if not c:
        raise HTTPException(status_code=404, detail="Company not found")

    status_now = c.get("status")
    if status_now not in ("ready_for_credentials", "waiting_payment"):
        raise HTTPException(status_code=400, detail="Not ready for credentials")

    if payload.username:
        username = payload.username
    else:
        base = f"{c.get('company_name')}_{c.get('owner_name')}".lower().replace(" ", "")
        exists = db.companies.find_one({"username": username})
        if exists:
            username = base + "_" + str(uuid.uuid4())[:6]

    if payload.password:
        password_plain = payload.password
    else:
        password_plain = uuid.uuid4().hex[:7]  

    hashed = bcrypt.hashpw(password_plain.encode(), bcrypt.gensalt()).decode()

    db.companies.update_one(
        {"_id": ObjectId(company_id)},
        {"$set": {
            "username": username,
            "password": hashed,
            "status": "active",
            "must_change_password": True
        }}
    )

    subject = "Your FleetDocs Login Credentials"
    body = f"""
        Hi {c.get('owner_name')},

        Your company has been activated on FleetDocs.

        Please use the following credentials to login:

        Username: {username}
        Password: {password_plain}

        On your first login, please change your password.

        Thank you,
        FleetDocs Team
        """
    send_email(c.get("email"), subject, body)

    return {"message": "Credentials set and emailed", "username": username}

@router.put("/change-password", tags=["Admin"])
def change_admin_password(old_password: str, new_password: str, admin: dict = Depends(get_admin_payload)):
    admin_username = admin.get("sub")
    doc = db.admins.find_one({"username": admin_username})
    if not doc:
        raise HTTPException(status_code=404, detail="Admin not found")

    if not bcrypt.checkpw(old_password.encode(), doc["password"].encode()):
        raise HTTPException(status_code=400, detail="Old password incorrect")

    hashed = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
    db.admins.update_one({"username": admin_username}, {"$set": {"password": hashed}})
    return {"message": "Password changed successfully"}

@router.get("/company-requests/{request_id}", tags=["admin"])
async def get_company_requests(request_id: str, admin: dict = Depends(get_admin_payload)):
    """
    Fetches a single contact request by its ID from the contact_requests collection.
    """
    req = db.contact_requests.find_one({"_id": ObjectId(request_id)})
    if not req:
        raise HTTPException(status_code=404, detail="Contact request not found")
    
    req["id"] = str(req["_id"])
    return req