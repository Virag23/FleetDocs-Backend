import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timedelta
from app.database.database import db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def archive_old_assignments():
    """
    Finds active assignments older than 24 hours and moves them to 'history'.
    """
    logger.info("Scheduler: Running job to archive old assignments...")
    twenty_four_hours_ago = datetime.utcnow() - timedelta(hours=24)
    
    result = db.assignments.update_many(
        {"status": "active", "assignment_date": {"$lt": twenty_four_hours_ago}},
        {"$set": {"status": "history", "completed_at": datetime.utcnow()}}
    )
    logger.info(f"Scheduler: Archived {result.modified_count} assignments.")

def delete_very_old_assignments():
    """
    Finds history assignments older than 30 days and deletes them permanently.
    """
    logger.info("Scheduler: Running job to delete very old assignment history...")
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    
    result = db.assignments.delete_many(
        {"status": "history", "assignment_date": {"$lt": thirty_days_ago}}
    )
    logger.info(f"Scheduler: Deleted {result.deleted_count} old history records.")

scheduler = AsyncIOScheduler()
scheduler.add_job(archive_old_assignments, 'interval', hours=1) 
scheduler.add_job(delete_very_old_assignments, 'interval', days=1)
