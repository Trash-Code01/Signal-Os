import requests
import json
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from core.models import Base, Campaign, CampaignLocation, IndustryConfig, ProviderAccount, JobRun, Business, BusinessSource, DecisionMaker, Score, Opportunity, CRMLead, CRMActivity

# Local DB URL
LOCAL_DB_URL = "postgresql+psycopg://devacia:devacia_password@postgres:5432/devacia_os"

# The live API URL we just deployed to Render
API_URL = "https://devacia-api.onrender.com/api/migrate-upload"

print("Connecting to local database...")
try:
    local_engine = create_engine(LOCAL_DB_URL)
    LocalSession = sessionmaker(bind=local_engine)
    local_db = LocalSession()
except Exception as e:
    print("Could not connect to your local database. Ensure your local docker containers are running!")
    print(e)
    exit(1)

def serialize_record(record):
    """Convert SQLAlchemy model instance to dict, handling datetimes."""
    d = {}
    for column in record.__table__.columns:
        val = getattr(record, column.name)
        if isinstance(val, datetime):
            d[column.name] = val.isoformat()
        else:
            d[column.name] = val
    return d

def copy_table(model_class):
    table_name = model_class.__tablename__
    print(f"Reading {table_name}...")
    records = local_db.query(model_class).all()
    
    if not records:
        print(f"No records found in {table_name}.")
        return

    serialized_records = [serialize_record(r) for r in records]
    
    print(f"Uploading {len(serialized_records)} records to live server for {table_name}...")
    response = requests.post(
        API_URL, 
        json={"table_name": table_name, "records": serialized_records}
    )
    
    if response.status_code == 200:
        res_data = response.json()
        if res_data.get("status") == "ok":
            print(f"✅ Successfully migrated {table_name}")
        else:
            print(f"❌ Error migrating {table_name}: {res_data.get('message')}")
    else:
        print(f"❌ HTTP Error {response.status_code}: {response.text}")

try:
    # Order matters for foreign keys
    tables_to_copy = [
        IndustryConfig,
        ProviderAccount,
        Campaign,
        CampaignLocation,
        JobRun,
        Business,
        BusinessSource,
        DecisionMaker,
        Score,
        Opportunity,
        CRMLead,
        CRMActivity
    ]
    
    for table in tables_to_copy:
        copy_table(table)
        
    print("\n🎉 Migration complete! Your local data has been securely beamed to the cloud over HTTP.")

finally:
    local_db.close()
