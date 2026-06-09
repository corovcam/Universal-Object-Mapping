import os
import time

import requests

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

if __name__ == "__main__":
    # MongoDB Relational Migrator API endpoint
    base_url = "http://localhost:8091/api/v1"
    
    # Load the migration configuration from the .relmig file
    with open(os.path.join(SCRIPT_DIR, "UOM WideWorldImporters.relmig"), "r") as f:
        migration_config = f.read()
    # Send the migration configuration to the API
    response = requests.post(f"{base_url}/project/import", data=migration_config, headers={"Content-Type": "application/json"})
    if response.status_code == 200:
        print("Migration configuration imported successfully!")
        res = response.json()
        # print(f"Response: {res}")
    else:
        print(f"Failed to import migration configuration: {response.status_code} - {response.text}")
        exit(1)
    
    project_id: str = res.get("id")
    jdbc_id: str = res.get("jdbcId")
    mongodb_id: str = res.get("mongodbId")
    if not project_id or not jdbc_id or not mongodb_id:
        print("One or more required IDs not returned from import response, cannot proceed with migration execution.")
        exit(1)
    
    job_payload: dict[str, object] = {
        "projectId": project_id,
        "jdbcConnectionDetails": {
            "id": jdbc_id,
            "type": "SQL_SERVER",
            "url": "jdbc:sqlserver://mssql_db;databaseName=WideWorldImporters;encrypt=true;trustServerCertificate=true",
            "user": "sa",
            "password": "Testingorms123",
            "savePassword": False,
            "isManualUri": False
        },
        "mongodbConnectionDetails": {
            "id": mongodb_id,
            "connectionString": "mongodb://root:root@mongodb:27017/uom?authSource=admin",
            "savePassword": False
        },
        "options": {
            "dropCollections": True,
            "mode": "SNAPSHOT",
            "truncationReportMode": "WARN"
        },
        "verification": {
            "enabled": False
        }
    }
    
    # Trigger the migration execution
    response = requests.post(f"{base_url}/jobs", json=job_payload)
    if response.status_code == 200:
        print("Migration execution started successfully!")
        res = response.json()
        print(f"Response: {res}")
        job_id = res.get("id")
        print(f"Migration Job ID: {job_id}")
    else:
        print(f"Failed to start migration execution: {response.status_code} - {response.text}")
        exit(1)
    
    print("Polling for migration job status every 10 seconds. It should take around 10-15 minutes to complete depending on your machine's resources...")
    while True:
        # Poll the job status every 10 seconds
        response = requests.get(f"{base_url}/jobs/{job_id}")
        if response.status_code == 200:
            res = response.json()
            print(f"Job Status Response: {res}")
            job_status = res.get("status")
            print(f"Current Job Status: {job_status}")
            if job_status in ["COMPLETED", "FAILED"]:
                print(f"Migration execution finished with status: {job_status}")
                break
            else:
                print(f"Migration execution still in progress... Current status: {job_status}")
        else:
            print(f"Failed to fetch job status: {response.status_code} - {response.text}")
            break
        time.sleep(10)
