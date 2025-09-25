from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from typing import List, Optional
from datetime import date
import uuid
import time
from app.database.database import db
from app.models.truck import (
    TruckInDB, TruckOut, AllDocuments, RCDetails, PUCDetails, TaxDetails,
    InsuranceDetails, NationalPermitDetails, StatePermitDetails, FitnessDetails, EmiDetails
)
from app.routes.company import get_current_company
from app.utils.aws_utils import upload_file_to_s3, start_document_text_detection, get_document_text_detection_results
from app.utils.parser_utils import get_parser_for_doc_type
from app.utils.email_utils import send_truck_added_email, send_truck_updated_email, send_truck_deleted_email
from bson import ObjectId
import logging

router = APIRouter()
logging.basicConfig(level=logging.INFO)

@router.post("/extract-document", status_code=status.HTTP_200_OK)
async def extract_document_data(
    doc_type: str = Form(...),
    truck_number: str = Form(...),
    file: UploadFile = File(...),
    company: dict = Depends(get_current_company)
):
    """
    Processes a single document upload to extract and verify its data
    without saving it to the database. Used for the interactive "Extract" button on the frontend.
    """
    VALID_DOC_TYPES = ["rc", "puc", "tax", "insurance", "national_permit", "state_permit", "fitness"]
    if doc_type not in VALID_DOC_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid document type '{doc_type}'.")

    truck_number_clean = truck_number.replace(" ", "").replace("-", "").upper()
    if not truck_number_clean:
         raise HTTPException(status_code=400, detail="Truck Number is required to verify the document.")

    s3_object_name = f"temp/{company['company_id']}/{uuid.uuid4().hex}.pdf"
    upload_file_to_s3(file, company['company_id'], s3_object_name)

    job_id = start_document_text_detection(s3_object_name)
    full_text = ""
    max_retries = 30
    for _ in range(max_retries):
        job_status, lines = get_document_text_detection_results(job_id)
        if job_status == 'SUCCEEDED':
            full_text = "\n".join(lines)
            break
        elif job_status == 'FAILED':
            raise HTTPException(status_code=500, detail=f"Text extraction failed for {doc_type.upper()}.")
        time.sleep(2)
    else:
        raise HTTPException(status_code=500, detail=f"Text extraction timed out for {doc_type.upper()}.")

    parser = get_parser_for_doc_type(doc_type)
    extracted_info = parser(full_text)
    extracted_truck_no = extracted_info.get('truck_number')

    if not extracted_truck_no or extracted_truck_no != truck_number_clean:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Verification failed. Document belongs to truck '{extracted_truck_no}', not '{truck_number_clean}'."
        )
    
    return extracted_info

@router.post("/", status_code=status.HTTP_201_CREATED, response_model=TruckOut)
async def add_truck(
    truck_number: str = Form(...),
    model_number: str = Form(...),
    engine_number: str = Form(...),
    chassis_number: str = Form(...),
    registration_date: date = Form(...),
    tire_count: int = Form(...),
    has_emi: bool = Form(False),
    total_loan_amount: Optional[float] = Form(None),
    emi_per_month: Optional[float] = Form(None),
    emi_start_date: Optional[date] = Form(None),
    emi_end_date: Optional[date] = Form(None),
    completed_installments: Optional[int] = Form(0),
    truck_photo: UploadFile = File(...),
    rc_file: UploadFile = File(...),
    puc_file: UploadFile = File(...),
    tax_file: UploadFile = File(...),
    insurance_file: UploadFile = File(...),
    national_permit_file: UploadFile = File(...),
    state_permit_file: UploadFile = File(...),
    fitness_file: UploadFile = File(...),
    company: dict = Depends(get_current_company)
):
    company_id_obj = ObjectId(company["company_id"])
    truck_number_clean = truck_number.replace(" ", "").replace("-", "").upper()

    if db.trucks.find_one({"company_id": company_id_obj, "truck_number": truck_number_clean}):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Truck with number {truck_number_clean} already exists.")

    photo_s3_path = f"{company['company_id']}/{truck_number_clean}/truck_photo_{uuid.uuid4().hex}.jpg"
    truck_photo_url = upload_file_to_s3(truck_photo, company['company_id'], photo_s3_path)
    
    documents = {
        "rc": rc_file, "puc": puc_file, "tax": tax_file, "insurance": insurance_file,
        "national_permit": national_permit_file, "state_permit": state_permit_file, "fitness": fitness_file
    }
    
    textract_jobs = {}
    s3_urls = {}
    for doc_type, file in documents.items():
        s3_object_name = f"{company['company_id']}/{truck_number_clean}/{doc_type}_{uuid.uuid4().hex}"
        s3_urls[doc_type] = upload_file_to_s3(file, company['company_id'], s3_object_name)
        textract_jobs[doc_type] = start_document_text_detection(s3_object_name)

    parsed_data = {}
    max_retries = 30 
    for doc_type, job_id in textract_jobs.items():
        for _ in range(max_retries):
            status, lines = get_document_text_detection_results(job_id)
            if status == 'SUCCEEDED':
                full_text = "\n".join(lines)
                parser = get_parser_for_doc_type(doc_type)
                if parser:
                    extracted_info = parser(full_text)
                    if not extracted_info.get('truck_number') or extracted_info.get('truck_number') != truck_number_clean:
                        raise HTTPException(status_code=400, detail=f"Verification failed for {doc_type.upper()}. Document belongs to '{extracted_info.get('truck_number')}', not '{truck_number_clean}'.")
                    parsed_data[doc_type] = extracted_info
                    break 
            elif status == 'FAILED':
                 raise HTTPException(status_code=500, detail=f"Text extraction failed for {doc_type.upper()}.")
            time.sleep(2) 
        else:
            raise HTTPException(status_code=500, detail=f"Text extraction timed out for {doc_type.upper()}.")

    fitness_details = FitnessDetails(**parsed_data['fitness'], s3_url=s3_urls['fitness'])
    rc_details = RCDetails(**parsed_data['rc'], s3_url=s3_urls['rc'])
    rc_details.expiry_date = fitness_details.main_expiry_date

    all_docs = AllDocuments(rc=rc_details, puc=PUCDetails(**parsed_data['puc'], s3_url=s3_urls['puc']), tax=TaxDetails(**parsed_data['tax'], s3_url=s3_urls['tax']), insurance=InsuranceDetails(**parsed_data['insurance'], s3_url=s3_urls['insurance']), national_permit=NationalPermitDetails(**parsed_data['national_permit'], s3_url=s3_urls['national_permit']), state_permit=StatePermitDetails(**parsed_data['state_permit'], s3_url=s3_urls['state_permit']), fitness=fitness_details)
    emi_data = None
    if has_emi:
        if not all([total_loan_amount, emi_per_month, emi_start_date, emi_end_date]):
            raise HTTPException(status_code=400, detail="If EMI is selected, all EMI fields are required.")
        emi_data = EmiDetails(total_loan_amount=total_loan_amount, emi_per_month=emi_per_month, emi_start_date=emi_start_date, emi_end_date=emi_end_date, completed_installments=completed_installments)

    new_truck = TruckInDB(truck_number=truck_number_clean, model_number=model_number, engine_number=engine_number, chassis_number=chassis_number, registration_date=registration_date, tire_count=tire_count, truck_photo_url=truck_photo_url, company_id=company_id_obj, documents=all_docs, emi_details=emi_data)
    
    result = db.trucks.insert_one(new_truck.dict(by_alias=True))
    created_truck = db.trucks.find_one({"_id": result.inserted_id})
    
    try:
        company_details = company.get("company_data", {})
        send_truck_added_email(
            to_email=company_details.get("email"),
            company_name=company_details.get("company_name"),
            truck=created_truck
        )
    except Exception as e:
        logging.error(f"Failed to send truck added email for truck {created_truck['truck_number']}: {e}")

    return TruckOut(**created_truck)

@router.get("/", response_model=List[TruckOut])
def get_all_trucks(company: dict = Depends(get_current_company)):
    company_id = ObjectId(company["company_id"])
    trucks_cursor = db.trucks.find({"company_id": company_id})
    return [TruckOut(**truck) for truck in trucks_cursor]

@router.get("/{truck_id}", response_model=TruckOut)
def get_truck_by_id(truck_id: str, company: dict = Depends(get_current_company)):
    company_id = ObjectId(company["company_id"])
    truck = db.trucks.find_one({"_id": ObjectId(truck_id), "company_id": company_id})
    if not truck:
        raise HTTPException(status_code=404, detail="Truck not found.")
    return TruckOut(**truck)

@router.delete("/{truck_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_truck(truck_id: str, company: dict = Depends(get_current_company)):
    company_id = ObjectId(company["company_id"])
    
    truck_to_delete = db.trucks.find_one({"_id": ObjectId(truck_id), "company_id": company_id})
    if not truck_to_delete:
        raise HTTPException(status_code=404, detail="Truck not found or you do not have permission to delete it.")

    delete_result = db.trucks.delete_one({"_id": ObjectId(truck_id)})
    
    if delete_result.deleted_count > 0:
        try:
            company_details = company.get("company_data", {})
            send_truck_deleted_email(
                to_email=company_details.get("email"),
                company_name=company_details.get("company_name"),
                truck_number=truck_to_delete.get("truck_number")
            )
        except Exception as e:
            logging.error(f"Failed to send truck deleted email for truck {truck_to_delete.get('truck_number')}: {e}")
    return

@router.put("/document/{truck_id}/{doc_type}", response_model=TruckOut)
async def update_truck_document(
    truck_id: str,
    doc_type: str,
    file: UploadFile = File(...),
    company: dict = Depends(get_current_company)
):
    company_id = ObjectId(company["company_id"])
    truck_id_obj = ObjectId(truck_id)
    
    VALID_DOC_TYPES = ["rc", "puc", "tax", "insurance", "national_permit", "state_permit", "fitness"]
    if doc_type not in VALID_DOC_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid document type '{doc_type}'.")

    truck = db.trucks.find_one({"_id": truck_id_obj, "company_id": company_id})
    if not truck:
        raise HTTPException(status_code=404, detail="Truck not found.")
        
    truck_number_clean = truck['truck_number']

    s3_object_name = f"{company['company_id']}/{truck_number_clean}/{doc_type}_{uuid.uuid4().hex}"
    s3_url = upload_file_to_s3(file, company['company_id'], s3_object_name)

    job_id = start_document_text_detection(s3_object_name)
    full_text = ""
    max_retries = 30
    for _ in range(max_retries):
        job_status, lines = get_document_text_detection_results(job_id)
        if job_status == 'SUCCEEDED':
            full_text = "\n".join(lines)
            break
        elif job_status == 'FAILED':
            raise HTTPException(status_code=500, detail=f"Text extraction failed for {doc_type.upper()}.")
        time.sleep(2)
    else:
        raise HTTPException(status_code=500, detail=f"Text extraction timed out for {doc_type.upper()}.")

    parser = get_parser_for_doc_type(doc_type)
    extracted_info = parser(full_text)
    if not extracted_info.get('truck_number') or extracted_info.get('truck_number') != truck_number_clean:
        raise HTTPException(status_code=400, detail=f"Verification failed. New {doc_type.upper()} document belongs to truck '{extracted_info.get('truck_number')}', not '{truck_number_clean}'.")
    
    doc_models = {"rc": RCDetails, "puc": PUCDetails, "tax": TaxDetails, "insurance": InsuranceDetails, "national_permit": NationalPermitDetails, "state_permit": StatePermitDetails, "fitness": FitnessDetails}
    updated_doc_model = doc_models[doc_type](**extracted_info, s3_url=s3_url)
    
    update_query = {"$set": {f"documents.{doc_type}": updated_doc_model.dict()}}
    
    if doc_type == 'fitness':
        update_query["$set"]["documents.rc.expiry_date"] = updated_doc_model.main_expiry_date

    db.trucks.update_one({"_id": truck_id_obj}, update_query)
    
    updated_truck = db.trucks.find_one({"_id": truck_id_obj})
    
    try:
        company_details = company.get("company_data", {})
        send_truck_updated_email(
            to_email=company_details.get("email"),
            company_name=company_details.get("company_name"),
            truck=updated_truck,
            updated_doc_type=doc_type,
            new_doc_url=s3_url 
        )
    except Exception as e:
        logging.error(f"Failed to send truck updated email for truck {updated_truck['truck_number']}: {e}")
    
    return TruckOut(**updated_truck)

