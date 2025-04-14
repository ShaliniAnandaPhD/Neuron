import asyncio
from microservices.healthcare.healthcare_integration import HealthcareDataIntegrationMicroservice

async def main():
    # Create healthcare data integration microservice
    health_service = HealthcareDataIntegrationMicroservice(
        name="Patient Record Integration Service",
        description="Integrates multilingual healthcare records across providers"
    )
    
    # Deploy the service
    health_service.deploy()
    
    # Example patient records from different providers
    patient_records = [
        {
            "id": "med-123",
            "provider": "Family Practice Clinic",
            "date": "2025-01-15",
            "type": "medication",
            "content": "Medication: Lisinopril\nDosage: 10 mg\nFrequency: Once daily\nPrescribed for hypertension management."
        },
        {
            "id": "diag-456",
            "provider": "Endocrinology Center",
            "date": "2024-11-03",
            "type": "diagnosis",
            "content": "Diagnosis: Type 2 Diabetes Mellitus\nDate: 2024-11-03\nICD-10: E11.9\nNotes: Patient presents with elevated blood glucose. Recommend lifestyle changes and medication."
        },
        {
            "id": "lab-789",
            "provider": "Regional Medical Laboratory",
            "date": "2025-02-02",
            "type": "lab_result",
            "content": "Test: Glucose\nResult: 168 mg/dL\nReference Range: 70 - 99\nNotes: Elevated glucose levels indicating poor glycemic control."
        },
        {
            "id": "vital-012",
            "provider": "Community Health Clinic",
            "date": "2025-03-01",
            "type": "vital_signs",
            "content": "Blood Pressure: 142/88\nHeart Rate: 76\nTemperature: 98.6 F\nWeight: 185 lb\nNotes: Blood pressure remains elevated despite medication."
        },
        {
            "id": "med-345",
            "provider": "Farmacia Central",
            "date": "2025-02-10",
            "type": "medication",
            "content": "Medicamento: Metformina\nDosis: 500 mg\nFrecuencia: Dos veces al día\nPrescrito para control de diabetes tipo 2."
        }
    ]
    
    # Integrate the patient records
    result = await health_service.integrate_patient_records(patient_records)
    
    # Print the results
    print(f"Integration completed for patient {result['patient_id']}\n")
    
    print("Summary Statistics:")
    for key, value in result["summary"].items():
        print(f"- {key.replace('_', ' ').title()}: {value}")
    
    print("\nConditions Identified:")
    for condition in result["health_data"]["conditions"]:
        condition_source = "confirmed" if not condition.get("inferred", False) else f"inferred from {condition.get('inference_source', 'unknown')}"
        print(f"- {condition['name']} ({condition_source})")
    
    print("\nCare Gaps Found:")
    for gap in result["health_data"]["care_gaps"]:
        print(f"- {gap['description']} (Severity: {gap['severity']})")
    
    print("\nClinical Recommendations:")
    for rec in result["health_data"]["recommendations"]:
        print(f"- {rec['recommendation']} (Priority: {rec['priority']})")
        print(f"  Reason: {rec['reason']}")

if __name__ == "__main__":
    asyncio.run(main())
