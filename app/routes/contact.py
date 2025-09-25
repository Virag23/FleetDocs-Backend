from fastapi import APIRouter, HTTPException
from app.models.contact import ContactRequest
from app.database.database import db
from datetime import datetime
from app.utils.email_utils import send_contact_confirmation_email

router = APIRouter()

@router.get("/owner-info")
async def get_owner_info():
    return {
        "name": "Virag Jain",
        "email": "viragsjain1975@gmail.com",
        "phone": "+919325033281",
        "photo_url": "https://res.cloudinary.com/djoafwyhn/image/upload/v1758732345/Virag_toi6n6.jpg"
    }

@router.post("/contact")
async def submit_contact_form(payload: ContactRequest):
    contact_data = payload.dict()
    contact_data["status"] = "pending_submission"
    contact_data["submitted_at"] = datetime.utcnow()

    try:
        existing = db.contact_requests.find_one({
            "email": payload.email,
            "company_name": payload.company_name,
            "status": "pending_submission"
        })

        if existing:
            return {
                "message": "Duplicate",
                "status": "pending_submission"
            }

        db.contact_requests.insert_one(contact_data)

        if payload.email:
            send_contact_confirmation_email(payload.email, payload.company_name)

        return {
            "message": "Contact form submitted successfully",
            "status": "pending_submission"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
