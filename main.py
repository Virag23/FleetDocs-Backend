# main.py
from fastapi import FastAPI
from app.routes.auth import router as auth_router
from app.routes.contact import router as contact_router
from app.routes.admin import router as admin_router
from app.routes.company import router as company_router
from app.routes.recovery import router as recovery_router
from app.routes.trucks import router as trucks_router
from app.routes.drivers import router as drivers_router
from app.routes.assignments import router as assignments_router
from app.scheduler import scheduler

app = FastAPI(
    
    title="FleetDocs API",
    description="The complete backend API for the FleetDocs Fleet & Driver Management System.",
    version="1.0.0"
)

@app.on_event("startup")
async def startup_event():
    """Start the scheduler on app startup."""
    scheduler.start()

@app.on_event("shutdown")
async def shutdown_event():
    """Stop the scheduler on app shutdown."""
    scheduler.shutdown()

@app.get("/")
def read_root():
    return {"message": "FleetDocs API is running 🚛"}

app.include_router(contact_router, prefix="/contact", tags=["Contact"])
app.include_router(auth_router, prefix="/auth", tags=["Authentication"])
app.include_router(admin_router, prefix="/admin", tags=["Admin Panel"])
app.include_router(company_router, prefix="/company", tags=["Company"])
app.include_router(recovery_router, prefix="/recovery", tags=["Account Recovery"])
app.include_router(trucks_router, prefix="/trucks", tags=["Truck Management"])
app.include_router(drivers_router, prefix="/drivers", tags=["Driver Management"]) 
app.include_router(assignments_router, prefix="/assignments", tags=["Assignments"])