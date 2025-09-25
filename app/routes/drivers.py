from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from typing import List, Optional
import uuid
import time
from app.database.database import db
from app.models.driver import DriverInDB, DriverOut, DriverUpdate, LicenseDetails
from app.routes.company import get_current_company
from app.utils.aws_utils import upload_file_to_s3, start_document_text_detection, get_document_text_detection_results
from app.utils.parser_utils import get_parser_for_doc_type
from app.utils.email_utils import send_driver_added_email, send_driver_updated_email
from bson import ObjectId
import logging

router = APIRouter()
logging.basicConfig(level=logging.INFO)

@router.post("/", status_code=status.HTTP_201_CREATED, response_model=DriverOut)
async def add_driver(
    first_name: str = Form(...),
    last_name: str = Form(...),
    phone_number: str = Form(...),
    email: Optional[str] = Form(None),
    driver_photo: UploadFile = File(...),
    license_file: UploadFile = File(...),
    company: dict = Depends(get_current_company)
):
    company_id_obj = ObjectId(company["company_id"])
    license_s3_path = f"{company['company_id']}/drivers/licenses/{uuid.uuid4().hex}"
    license_s3_url = upload_file_to_s3(license_file, company['company_id'], license_s3_path)
    
    job_id = start_document_text_detection(license_s3_path)
    full_text = ""
    max_retries = 30
    for _ in range(max_retries):
        job_status, lines = get_document_text_detection_results(job_id)
        if job_status == 'SUCCEEDED':
            full_text = "\n".join(lines)
            break
        elif job_status == 'FAILED':
            raise HTTPException(status_code=500, detail="License text extraction failed.")
        time.sleep(2)
    else:
        raise HTTPException(status_code=500, detail="License text extraction timed out.")

    parser = get_parser_for_doc_type("license")
    extracted_data = parser(full_text)
    input_full_name = f"{first_name} {last_name}".lower().strip()
    license_name = extracted_data.get("name_on_license", "").lower().strip()

    if not license_name or license_name not in input_full_name:
         raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Verification Failed: Name on license ('{license_name.title()}') does not match the input name ('{input_full_name.title()}')."
        )

    license_details = LicenseDetails(**extracted_data, s3_url=license_s3_url)

    photo_s3_path = f"{company['company_id']}/drivers/photos/{uuid.uuid4().hex}"
    driver_photo_url = upload_file_to_s3(driver_photo, company['company_id'], photo_s3_path)
    
    new_driver = DriverInDB(
        first_name=first_name,
        last_name=last_name,
        phone_number=phone_number,
        email=email,
        driver_photo_url=driver_photo_url,
        company_id=company_id_obj,
        license=license_details
    )
    
    result = db.drivers.insert_one(new_driver.dict(by_alias=True))
    created_driver = db.drivers.find_one({"_id": result.inserted_id})
    
    try:
        company_details = company.get("company_data", {})
        send_driver_added_email(
            to_email=company_details.get("email"),
            company_name=company_details.get("company_name"),
            driver=created_driver
        )
    except Exception as e:
        logging.error(f"Failed to send driver added email: {e}")
        
    return DriverOut(**created_driver)

@router.get("/", response_model=List[DriverOut])
async def get_all_drivers(company: dict = Depends(get_current_company)):
    company_id = ObjectId(company["company_id"])
    drivers_cursor = db.drivers.find({"company_id": company_id})
    return [DriverOut(**driver) for driver in drivers_cursor]

@router.get("/{driver_id}", response_model=DriverOut)
async def get_driver(driver_id: str, company: dict = Depends(get_current_company)):
    company_id = ObjectId(company["company_id"])
    driver = db.drivers.find_one({"_id": ObjectId(driver_id), "company_id": company_id})
    if not driver:
        raise HTTPException(status_code=404, detail="Driver not found.")
    return DriverOut(**driver)

@router.put("/{driver_id}", response_model=DriverOut)
async def update_driver_phone(driver_id: str, payload: DriverUpdate, company: dict = Depends(get_current_company)):
    company_id = ObjectId(company["company_id"])
    driver_id_obj = ObjectId(driver_id)
    
    db.drivers.update_one(
        {"_id": driver_id_obj, "company_id": company_id},
        {"$set": {"phone_number": payload.phone_number}}
    )
    
    updated_driver = db.drivers.find_one({"_id": driver_id_obj})
    if not updated_driver:
        raise HTTPException(status_code=404, detail="Driver not found after update.")
        
    try:
        company_details = company.get("company_data", {})
        send_driver_updated_email(
            to_email=company_details.get("email"),
            company_name=company_details.get("company_name"),
            driver=updated_driver,
            update_type="Phone Number"
        )
    except Exception as e:
        logging.error(f"Failed to send driver updated email: {e}")
        
    return DriverOut(**updated_driver)
    
@router.put("/license/{driver_id}", response_model=DriverOut)
async def update_driver_license(
    driver_id: str, 
    license_file: UploadFile = File(...), 
    company: dict = Depends(get_current_company)
):
    company_id = ObjectId(company["company_id"])
    driver_id_obj = ObjectId(driver_id)
    
    driver = db.drivers.find_one({"_id": driver_id_obj, "company_id": company_id})
    if not driver:
        raise HTTPException(status_code=404, detail="Driver not found.")

    license_s3_path = f"{company['company_id']}/drivers/licenses/{uuid.uuid4().hex}"
    license_s3_url = upload_file_to_s3(license_file, company['company_id'], license_s3_path)
    
    job_id = start_document_text_detection(license_s3_path)
    full_text = ""

    
    parser = get_parser_for_doc_type("license")
    extracted_data = parser(full_text)
    
    input_full_name = f"{driver['first_name']} {driver['last_name']}".lower().strip()
    license_name = extracted_data.get("name_on_license", "").lower().strip()
    if not license_name or license_name not in input_full_name:
         raise HTTPException(status_code=400, detail=f"Verification Failed: New license name ('{license_name.title()}') does not match driver's name.")
    
    new_license_details = LicenseDetails(**extracted_data, s3_url=license_s3_url)
    
    db.drivers.update_one(
        {"_id": driver_id_obj},
        {"$set": {"license": new_license_details.dict()}}
    )
    
    updated_driver = db.drivers.find_one({"_id": driver_id_obj})

    try:
        company_details = company.get("company_data", {})
        send_driver_updated_email(
            to_email=company_details.get("email"),
            company_name=company_details.get("company_name"),
            driver=updated_driver,
            update_type="Driving License"
        )
    except Exception as e:
        logging.error(f"Failed to send driver updated email: {e}")
        
    return DriverOut(**updated_driver)

@router.delete("/{driver_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_driver(driver_id: str, company: dict = Depends(get_current_company)):
    company_id = ObjectId(company["company_id"])
    result = db.drivers.delete_one({"_id": ObjectId(driver_id), "company_id": company_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Driver not found or you do not have permission to delete it.")
    return
