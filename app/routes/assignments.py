from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List
from app.database.database import db
from app.models.assignment import AssignmentCreate, AssignmentOut
from app.models.truck import TruckOut
from app.models.driver import DriverOut
from app.routes.company import get_current_company
from bson import ObjectId
from datetime import datetime

router = APIRouter()

@router.post("/", status_code=status.HTTP_201_CREATED, response_model=AssignmentOut)
async def create_assignment(payload: AssignmentCreate, company: dict = Depends(get_current_company)):
    company_id = ObjectId(company["company_id"])
    active_assignment = db.assignments.find_one({
        "company_id": company_id,
        "status": "active",
        "$or": [
            {"truck_id": ObjectId(payload.truck_id)},
            {"driver_id": ObjectId(payload.driver_id)}
        ]
    })
    if active_assignment:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The selected truck or driver is already on an active assignment."
        )

    assignment_data = payload.dict(by_alias=True)
    assignment_data["company_id"] = company_id
    assignment_data["assignment_date"] = datetime.utcnow()
    assignment_data["status"] = "active"
    result = db.assignments.insert_one(assignment_data)
    new_assignment = get_assignments_with_details(company_id, {"_id": result.inserted_id})
    if not new_assignment:
        raise HTTPException(status_code=500, detail="Failed to retrieve created assignment.")
        
    return new_assignment[0]


@router.get("/", response_model=List[AssignmentOut])
async def get_assignments(
    status: str = Query("active", enum=["active", "history"]), 
    company: dict = Depends(get_current_company)
):
    company_id = ObjectId(company["company_id"])
    return get_assignments_with_details(company_id, {"status": status})


@router.post("/{assignment_id}/complete", status_code=status.HTTP_200_OK)
async def complete_assignment(assignment_id: str, company: dict = Depends(get_current_company)):
    company_id = ObjectId(company["company_id"])
    assignment_id_obj = ObjectId(assignment_id)

    result = db.assignments.update_one(
        {"_id": assignment_id_obj, "company_id": company_id, "status": "active"},
        {"$set": {"status": "history", "completed_at": datetime.utcnow()}}
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Active assignment not found.")
    
    return {"message": "Assignment marked as complete and moved to history."}


@router.get("/unassigned", response_model=dict)
async def get_unassigned_resources(company: dict = Depends(get_current_company)):
    """
    Provides lists of trucks and drivers that are not currently on an active assignment,
    making it easy for the frontend to populate dropdowns.
    """
    company_id = ObjectId(company["company_id"])
    active_assignments = db.assignments.find({"company_id": company_id, "status": "active"})
    assigned_truck_ids = {a["truck_id"] for a in active_assignments}
    active_assignments.rewind()
    assigned_driver_ids = {a["driver_id"] for a in active_assignments}
    unassigned_trucks = db.trucks.find({"company_id": company_id, "_id": {"$nin": list(assigned_truck_ids)}})
    unassigned_drivers = db.drivers.find({"company_id": company_id, "_id": {"$nin": list(assigned_driver_ids)}})
    
    return {
        "trucks": [TruckOut(**t) for t in unassigned_trucks],
        "drivers": [DriverOut(**d) for d in unassigned_drivers]
    }


def get_assignments_with_details(company_id: ObjectId, match_filter: dict) -> List[AssignmentOut]:
    """
    Helper function to query assignments and populate truck/driver details
    using MongoDB's aggregation framework.
    """
    pipeline = [
        {"$match": {"company_id": company_id, **match_filter}},
        {"$lookup": {
            "from": "trucks",
            "localField": "truck_id",
            "foreignField": "_id",
            "as": "truckDetails"
        }},
        {"$lookup": {
            "from": "drivers",
            "localField": "driver_id",
            "foreignField": "_id",
            "as": "driverDetails"
        }},
        {"$unwind": "$truckDetails"},
        {"$unwind": "$driverDetails"},
        {"$project": {
            "id": {"$toString": "$_id"},
            "truck": "$truckDetails",
            "driver": "$driverDetails",
            "status": "$status",
            "assignment_date": "$assignment_date",
            "completed_at": "$completed_at",
            "type_of_load": "$type_of_load",
            "origin": "$origin",
            "destination": "$destination"
        }}
    ]
    
    results = list(db.assignments.aggregate(pipeline))
    return [AssignmentOut.model_validate(r) for r in results]
