from pymongo import MongoClient
import os
from dotenv import load_dotenv
import bcrypt

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB = os.getenv("MONGO_DB")

client = MongoClient(os.getenv("MONGO_URI"))
db = client[os.getenv("MONGO_DB")]

admin_username = "virag_jain"
admin_email = "viragsjain1975@gmail.com"
admin_phone = "9325033281"
admin_password_plain = "Virag$2310" 

hashed = bcrypt.hashpw(admin_password_plain.encode('utf-8'), bcrypt.gensalt())

admin_data = {
    "name": "Virag Nandgaonkar",
    "username": "virag_jain",
    "email": "viragsjain1975@gmail.com",
    "phone": "9325033281",
    "password": hashed.decode('utf-8'),
    "role": "admin",
    "created_at": None
}

existing = db.admins.find_one({"username": "virag_jain"})
if existing:
    print("Admin already exists.")
else:
    db.admins.insert_one(admin_data)
    print("Admin inserted successfully.")
