from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import asyncio
import uvicorn
import json
from healthcare_integration import HealthcareDataIntegrationMicroservice

app = FastAPI(title="Healthcare Integration API")

# Initialize microservice
resolver = HealthcareDataIntegrationMicroservice(
    name="Healthcare Integration API",
    description="API for integrating multilingual healthcare records"
)
resolver.deploy()

class PatientRecordsRequest(BaseModel):
    patient_records: list
    patient_id: str = "anonymous"

@app.post("/integrate")
async def integrate_records(request: PatientRecordsRequest):
    """Integrate patient healthcare records."""
    try:
        result = await resolver.integrate_patient_records(request.patient_records)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/metrics")
async def get_metrics():
    """Get current performance metrics."""
    return resolver.get_metrics()

if __name__ == "__main__":
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
