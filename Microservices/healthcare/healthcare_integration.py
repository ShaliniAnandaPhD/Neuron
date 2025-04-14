# microservices/healthcare/healthcare_integration.py

from typing import Dict, Any, List, Optional
import json
import uuid
import re
from datetime import datetime

from neuron.agent import DeliberativeAgent, ReflexAgent
from neuron.circuit_designer import CircuitDefinition
from neuron.types import AgentType, ConnectionType
from ..base_microservice import BaseMicroservice

class MultilingualNLPComponent(DeliberativeAgent):
    """Agent for processing multilingual healthcare records."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.supported_languages = ["en", "es"]
        self.language_patterns = self._init_language_patterns()
    
    def _init_language_patterns(self):
        """Initialize language detection patterns."""
        return {
            "en": {
                "common_words": ["the", "and", "patient", "history", "medication", "treatment"],
                "date_formats": [r"\d{1,2}/\d{1,2}/\d{4}", r"\d{4}-\d{2}-\d{2}"],
                "medical_terms": ["diagnosis", "prescription", "symptoms", "allergies"]
            },
            "es": {
                "common_words": ["el", "la", "paciente", "historia", "medicamento", "tratamiento"],
                "date_formats": [r"\d{1,2}/\d{1,2}/\d{4}", r"\d{4}-\d{2}-\d{2}"],
                "medical_terms": ["diagnóstico", "receta", "síntomas", "alergias"]
            }
        }
    
    async def process_message(self, message):
        patient_records = message.content.get("patient_records", [])
        processed_records = []
        
        for record in patient_records:
            # Detect language
            detected_language = await self._detect_language(record)
            
            # Parse record based on detected language
            parsed_record = await self._parse_record(record, detected_language)
            
            # Add language information to the record
            parsed_record["detected_language"] = detected_language
            parsed_record["original_text"] = record.get("content", "")
            
            processed_records.append(parsed_record)
        
        # Forward processed records to the next component
        await self.send_message(
            recipients=[message.metadata.get("next_agent", "measurement_standardization")],
            content={"processed_records": processed_records}
        )
    
    async def _detect_language(self, record):
        """Detect the language of the record."""
        content = record.get("content", "")
        scores = {}
        
        for lang, patterns in self.language_patterns.items():
            score = 0
            
            # Check for common words
            for word in patterns["common_words"]:
                if re.search(r"\b" + word + r"\b", content, re.IGNORECASE):
                    score += 1
            
            # Check for date formats
            for date_format in patterns["date_formats"]:
                if re.search(date_format, content):
                    score += 1
            
            # Check for medical terms
            for term in patterns["medical_terms"]:
                if re.search(r"\b" + term + r"\b", content, re.IGNORECASE):
                    score += 2  # Weight medical terms more heavily
            
            scores[lang] = score
        
        # Return the language with the highest score
        return max(scores, key=scores.get)
    
    async def _parse_record(self, record, language):
        """Parse record based on detected language."""
        content = record.get("content", "")
        record_type = record.get("type", "unknown")
        
        parsed_data = {
            "record_id": record.get("id", str(uuid.uuid4())),
            "provider": record.get("provider", "unknown"),
            "date": record.get("date", "unknown"),
            "type": record_type,
        }
        
        # Extract structured information based on record type
        if record_type == "medication":
            parsed_data.update(await self._parse_medication(content, language))
        elif record_type == "diagnosis":
            parsed_data.update(await self._parse_diagnosis(content, language))
        elif record_type == "lab_result":
            parsed_data.update(await self._parse_lab_result(content, language))
        elif record_type == "vital_signs":
            parsed_data.update(await self._parse_vital_signs(content, language))
        else:
            # Generic parsing for unknown record types
            parsed_data["extracted_text"] = content
        
        return parsed_data
    
    async def _parse_medication(self, content, language):
        """Parse medication record."""
        if language == "en":
            # Extract medication name, dosage, frequency
            med_match = re.search(r"Medication:\s*(\w+(?:\s+\w+)*)", content)
            dosage_match = re.search(r"Dosage:\s*([\d.]+\s*(?:mg|g|mcg|ml))", content)
            freq_match = re.search(r"Frequency:\s*(\w+(?:\s+\w+)*)", content)
            
            return {
                "medication_name": med_match.group(1) if med_match else "unknown",
                "dosage": dosage_match.group(1) if dosage_match else "unknown",
                "frequency": freq_match.group(1) if freq_match else "unknown"
            }
        elif language == "es":
            # Extract medication name, dosage, frequency in Spanish
            med_match = re.search(r"Medicamento:\s*(\w+(?:\s+\w+)*)", content)
            dosage_match = re.search(r"Dosis:\s*([\d.]+\s*(?:mg|g|mcg|ml))", content)
            freq_match = re.search(r"Frecuencia:\s*(\w+(?:\s+\w+)*)", content)
            
            return {
                "medication_name": med_match.group(1) if med_match else "unknown",
                "dosage": dosage_match.group(1) if dosage_match else "unknown",
                "frequency": freq_match.group(1) if freq_match else "unknown"
            }
        
        return {"raw_content": content}
    
    async def _parse_diagnosis(self, content, language):
        """Parse diagnosis record."""
        if language == "en":
            # Extract diagnosis, date, provider
            diag_match = re.search(r"Diagnosis:\s*(\w+(?:\s+\w+)*)", content)
            date_match = re.search(r"Date:\s*(\d{1,2}/\d{1,2}/\d{4}|\d{4}-\d{2}-\d{2})", content)
            icd_match = re.search(r"ICD-\d+:\s*([A-Z\d.]+)", content)
            
            return {
                "diagnosis": diag_match.group(1) if diag_match else "unknown",
                "diagnosis_date": date_match.group(1) if date_match else "unknown",
                "icd_code": icd_match.group(1) if icd_match else "unknown"
            }
        elif language == "es":
            # Extract diagnosis, date, provider in Spanish
            diag_match = re.search(r"Diagnóstico:\s*(\w+(?:\s+\w+)*)", content)
            date_match = re.search(r"Fecha:\s*(\d{1,2}/\d{1,2}/\d{4}|\d{4}-\d{2}-\d{2})", content)
            icd_match = re.search(r"ICD-\d+:\s*([A-Z\d.]+)", content)
            
            return {
                "diagnosis": diag_match.group(1) if diag_match else "unknown",
                "diagnosis_date": date_match.group(1) if date_match else "unknown",
                "icd_code": icd_match.group(1) if icd_match else "unknown"
            }
        
        return {"raw_content": content}
    
    async def _parse_lab_result(self, content, language):
        """Parse lab result record."""
        # Implementation would extract test name, value, units, reference range
        # This is a simplified placeholder implementation
        lab_data = {"raw_content": content}
        
        # Extract test results using regex patterns
        if language == "en":
            lab_match = re.search(r"Test:\s*(\w+(?:\s+\w+)*)", content)
            if lab_match:
                lab_data["test_name"] = lab_match.group(1)
            
            value_match = re.search(r"Result:\s*([\d.]+)\s*(\w+)", content)
            if value_match:
                lab_data["value"] = value_match.group(1)
                lab_data["units"] = value_match.group(2)
            
            range_match = re.search(r"Reference Range:\s*([\d.-]+)\s*-\s*([\d.]+)", content)
            if range_match:
                lab_data["reference_min"] = range_match.group(1)
                lab_data["reference_max"] = range_match.group(2)
        
        elif language == "es":
            lab_match = re.search(r"Prueba:\s*(\w+(?:\s+\w+)*)", content)
            if lab_match:
                lab_data["test_name"] = lab_match.group(1)
            
            value_match = re.search(r"Resultado:\s*([\d.]+)\s*(\w+)", content)
            if value_match:
                lab_data["value"] = value_match.group(1)
                lab_data["units"] = value_match.group(2)
            
            range_match = re.search(r"Rango de Referencia:\s*([\d.-]+)\s*-\s*([\d.]+)", content)
            if range_match:
                lab_data["reference_min"] = range_match.group(1)
                lab_data["reference_max"] = range_match.group(2)
        
        return lab_data
    
    async def _parse_vital_signs(self, content, language):
        """Parse vital signs record."""
        vitals = {"raw_content": content}
        
        # Extract vital signs using regex patterns
        if language == "en":
            bp_match = re.search(r"Blood Pressure:\s*(\d+)/(\d+)", content)
            if bp_match:
                vitals["systolic"] = bp_match.group(1)
                vitals["diastolic"] = bp_match.group(2)
            
            hr_match = re.search(r"Heart Rate:\s*(\d+)", content)
            if hr_match:
                vitals["heart_rate"] = hr_match.group(1)
            
            temp_match = re.search(r"Temperature:\s*([\d.]+)\s*([CF])", content)
            if temp_match:
                vitals["temperature"] = temp_match.group(1)
                vitals["temp_unit"] = temp_match.group(2)
            
            weight_match = re.search(r"Weight:\s*([\d.]+)\s*(kg|lb)", content)
            if weight_match:
                vitals["weight"] = weight_match.group(1)
                vitals["weight_unit"] = weight_match.group(2)
        
        elif language == "es":
            bp_match = re.search(r"Presión Arterial:\s*(\d+)/(\d+)", content)
            if bp_match:
                vitals["systolic"] = bp_match.group(1)
                vitals["diastolic"] = bp_match.group(2)
            
            hr_match = re.search(r"Frecuencia Cardíaca:\s*(\d+)", content)
            if hr_match:
                vitals["heart_rate"] = hr_match.group(1)
            
            temp_match = re.search(r"Temperatura:\s*([\d.]+)\s*([CF])", content)
            if temp_match:
                vitals["temperature"] = temp_match.group(1)
                vitals["temp_unit"] = temp_match.group(2)
            
            weight_match = re.search(r"Peso:\s*([\d.]+)\s*(kg|lb)", content)
            if weight_match:
                vitals["weight"] = weight_match.group(1)
                vitals["weight_unit"] = weight_match.group(2)
        
        return vitals


class MeasurementStandardization(DeliberativeAgent):
    """Agent for standardizing measurements across healthcare records."""
    
    async def process_message(self, message):
        processed_records = message.content.get("processed_records", [])
        standardized_records = []
        
        for record in processed_records:
            # Standardize measurements based on record type
            if record["type"] == "lab_result":
                standardized_record = await self._standardize_lab_result(record)
            elif record["type"] == "vital_signs":
                standardized_record = await self._standardize_vital_signs(record)
            elif record["type"] == "medication":
                standardized_record = await self._standardize_medication(record)
            else:
                # No standardization needed
                standardized_record = record
            
            standardized_records.append(standardized_record)
        
        # Forward standardized records to the next component
        await self.send_message(
            recipients=[message.metadata.get("next_agent", "medical_terminology_resolver")],
            content={"standardized_records": standardized_records}
        )
    
    async def _standardize_lab_result(self, record):
        """Standardize lab result measurements."""
        standardized = record.copy()
        
        # Handle glucose measurements (convert to mmol/L if in mg/dL)
        if "test_name" in record and "glucose" in record["test_name"].lower():
            if "units" in record and record["units"].lower() == "mg/dl" and "value" in record:
                try:
                    value = float(record["value"])
                    # Convert mg/dL to mmol/L (divide by 18)
                    standardized["original_value"] = value
                    standardized["original_units"] = "mg/dL"
                    standardized["value"] = round(value / 18.0, 2)
                    standardized["units"] = "mmol/L"
                    standardized["conversion_applied"] = "mg/dL to mmol/L"
                except (ValueError, TypeError):
                    standardized["standardization_error"] = "Could not convert glucose value"
        
        # Handle cholesterol measurements (convert to mmol/L if in mg/dL)
        elif "test_name" in record and any(term in record["test_name"].lower() for term in ["cholesterol", "ldl", "hdl", "triglycerides"]):
            if "units" in record and record["units"].lower() == "mg/dl" and "value" in record:
                try:
                    value = float(record["value"])
                    # Convert mg/dL to mmol/L (divide by 38.67 for cholesterol, 88.57 for triglycerides)
                    standardized["original_value"] = value
                    standardized["original_units"] = "mg/dL"
                    
                    if "triglycerides" in record["test_name"].lower():
                        standardized["value"] = round(value / 88.57, 2)
                    else:
                        standardized["value"] = round(value / 38.67, 2)
                    
                    standardized["units"] = "mmol/L"
                    standardized["conversion_applied"] = "mg/dL to mmol/L"
                except (ValueError, TypeError):
                    standardized["standardization_error"] = "Could not convert cholesterol value"
        
        # Other lab result standardizations would go here
        
        return standardized
    
    async def _standardize_vital_signs(self, record):
        """Standardize vital sign measurements."""
        standardized = record.copy()
        
        # Standardize temperature (convert to Celsius if in Fahrenheit)
        if "temperature" in record and "temp_unit" in record:
            if record["temp_unit"] == "F":
                try:
                    temp_f = float(record["temperature"])
                    # Convert Fahrenheit to Celsius
                    standardized["original_temperature"] = temp_f
                    standardized["original_temp_unit"] = "F"
                    standardized["temperature"] = round((temp_f - 32) * 5/9, 1)
                    standardized["temp_unit"] = "C"
                    standardized["conversion_applied"] = "F to C"
                except (ValueError, TypeError):
                    standardized["standardization_error"] = "Could not convert temperature"
        
        # Standardize weight (convert to kg if in lb)
        if "weight" in record and "weight_unit" in record:
            if record["weight_unit"] == "lb":
                try:
                    weight_lb = float(record["weight"])
                    # Convert pounds to kilograms
                    standardized["original_weight"] = weight_lb
                    standardized["original_weight_unit"] = "lb"
                    standardized["weight"] = round(weight_lb * 0.45359237, 1)
                    standardized["weight_unit"] = "kg"
                    standardized["conversion_applied"] = "lb to kg"
                except (ValueError, TypeError):
                    standardized["standardization_error"] = "Could not convert weight"
        
        # Standardize blood pressure (no conversion needed, just validation)
        if "systolic" in record and "diastolic" in record:
            try:
                systolic = int(record["systolic"])
                diastolic = int(record["diastolic"])
                
                # Check for potential errors or unlikely values
                if systolic < diastolic:
                    standardized["validation_warning"] = "Systolic pressure is lower than diastolic"
                elif systolic > 300 or systolic < 50:
                    standardized["validation_warning"] = "Systolic pressure is outside normal range"
                elif diastolic > 200 or diastolic < 30:
                    standardized["validation_warning"] = "Diastolic pressure is outside normal range"
            except (ValueError, TypeError):
                pass
        
        return standardized
    
    async def _standardize_medication(self, record):
        """Standardize medication dosages."""
        standardized = record.copy()
        
        # Standardize dosage units if needed
        if "dosage" in record:
            dosage = record["dosage"]
            
            # Convert mcg to mg where appropriate (for doses > 1000 mcg)
            mcg_match = re.search(r"([\d.]+)\s*mcg", dosage)
            if mcg_match:
                try:
                    mcg_value = float(mcg_match.group(1))
                    if mcg_value >= 1000:
                        mg_value = mcg_value / 1000
                        standardized["original_dosage"] = dosage
                        standardized["dosage"] = f"{mg_value} mg"
                        standardized["conversion_applied"] = "mcg to mg"
                except (ValueError, TypeError):
                    pass
            
            # Convert g to mg where appropriate (for doses < 1 g)
            g_match = re.search(r"(0\.[\d]+)\s*g", dosage)
            if g_match:
                try:
                    g_value = float(g_match.group(1))
                    if g_value < 1:
                        mg_value = g_value * 1000
                        standardized["original_dosage"] = dosage
                        standardized["dosage"] = f"{mg_value} mg"
                        standardized["conversion_applied"] = "g to mg"
                except (ValueError, TypeError):
                    pass
        
        return standardized


class MedicalTerminologyResolver(DeliberativeAgent):
    """Agent for resolving medical terminology and connecting related concepts."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.medication_db = {}
        self.diagnosis_db = {}
        self.load_medical_databases()
    
    def load_medical_databases(self):
        """Load medication and diagnosis databases."""
        # In a real implementation, this would load from a medical terminology database
        # For this example, we'll use a simplified mock database
        
        # Medication database (brand names to generic names)
        self.medication_db = {
            "lipitor": {"generic": "atorvastatin", "class": "statin", "conditions": ["hypercholesterolemia"]},
            "crestor": {"generic": "rosuvastatin", "class": "statin", "conditions": ["hypercholesterolemia"]},
            "zocor": {"generic": "simvastatin", "class": "statin", "conditions": ["hypercholesterolemia"]},
            "glucophage": {"generic": "metformin", "class": "biguanide", "conditions": ["type 2 diabetes"]},
            "januvia": {"generic": "sitagliptin", "class": "DPP-4 inhibitor", "conditions": ["type 2 diabetes"]},
            "lantus": {"generic": "insulin glargine", "class": "insulin", "conditions": ["diabetes"]},
            "novolog": {"generic": "insulin aspart", "class": "insulin", "conditions": ["diabetes"]},
            "lasix": {"generic": "furosemide", "class": "loop diuretic", "conditions": ["hypertension", "edema"]},
            "norvasc": {"generic": "amlodipine", "class": "calcium channel blocker", "conditions": ["hypertension"]},
            "prinivil": {"generic": "lisinopril", "class": "ACE inhibitor", "conditions": ["hypertension", "heart failure"]},
            "zestril": {"generic": "lisinopril", "class": "ACE inhibitor", "conditions": ["hypertension", "heart failure"]},
            "toprol": {"generic": "metoprolol", "class": "beta blocker", "conditions": ["hypertension", "heart failure"]}
        }
        
        # Also add generic names as keys
        generic_entries = {}
        for brand, data in self.medication_db.items():
            generic = data["generic"]
            if generic not in self.medication_db and generic not in generic_entries:
                generic_entries[generic] = {"generic": generic, "class": data["class"], "conditions": data["conditions"], "brands": [brand]}
            elif generic in generic_entries:
                generic_entries[generic]["brands"].append(brand)
        
        self.medication_db.update(generic_entries)
        
        # Diagnosis database (diagnosis codes to names)
        self.diagnosis_db = {
            "E11": {"name": "Type 2 diabetes mellitus", "category": "endocrine", "related_codes": ["E11.9", "E11.65"]},
            "E11.9": {"name": "Type 2 diabetes mellitus without complications", "category": "endocrine", "parent": "E11"},
            "E11.65": {"name": "Type 2 diabetes mellitus with hyperglycemia", "category": "endocrine", "parent": "E11"},
            "I10": {"name": "Essential (primary) hypertension", "category": "cardiovascular", "related_codes": ["I11", "I12"]},
            "I11": {"name": "Hypertensive heart disease", "category": "cardiovascular", "related_codes": ["I10", "I11.0"]},
            "I11.0": {"name": "Hypertensive heart disease with heart failure", "category": "cardiovascular", "parent": "I11"},
            "I12": {"name": "Hypertensive chronic kidney disease", "category": "cardiovascular", "related_codes": ["I10", "N18"]},
            "E78.0": {"name": "Pure hypercholesterolemia", "category": "endocrine", "related_codes": ["E78.2", "E78.5"]},
            "E78.2": {"name": "Mixed hyperlipidemia", "category": "endocrine", "related_codes": ["E78.0", "E78.5"]},
            "E78.5": {"name": "Hyperlipidemia, unspecified", "category": "endocrine", "related_codes": ["E78.0", "E78.2"]},
            "N18": {"name": "Chronic kidney disease (CKD)", "category": "renal", "related_codes": ["N18.1", "N18.2", "N18.3", "N18.4", "N18.5", "N18.6"]},
            "N18.3": {"name": "Chronic kidney disease, stage 3", "category": "renal", "parent": "N18"},
            "N18.4": {"name": "Chronic kidney disease, stage 4", "category": "renal", "parent": "N18"}
        }
    
    async def process_message(self, message):
        standardized_records = message.content.get("standardized_records", [])
        resolved_records = []
        
        for record in standardized_records:
            # Resolve terminology based on record type
            if record["type"] == "medication":
                resolved_record = await self._resolve_medication(record)
            elif record["type"] == "diagnosis":
                resolved_record = await self._resolve_diagnosis(record)
            else:
                # No terminology resolution needed
                resolved_record = record
            
            resolved_records.append(resolved_record)
        
        # Forward resolved records to the next component
        await self.send_message(
            recipients=[message.metadata.get("next_agent", "health_data_synthesizer")],
            content={"resolved_records": resolved_records}
        )
    
    async def _resolve_medication(self, record):
        """Resolve medication terminology."""
        resolved = record.copy()
        
        if "medication_name" in record:
            med_name = record["medication_name"].lower()
            
            # Check if medication exists in our database
            if med_name in self.medication_db:
                med_data = self.medication_db[med_name]
                
                # Add resolved information
                resolved["resolved_medication"] = {
                    "original_name": record["medication_name"],
                    "generic_name": med_data["generic"],
                    "medication_class": med_data["class"],
                    "treated_conditions": med_data["conditions"]
                }
                
                # Add brand names if it's a generic
                if "brands" in med_data:
                    resolved["resolved_medication"]["brand_names"] = med_data["brands"]
                
                # Flag potential conflicts
                if "generic" in med_data and med_data["generic"] != med_name:
                    # It's a brand name, check if other medications with same generic are present
                    resolved["potential_duplicate"] = True
            else:
                resolved["terminology_resolution"] = "medication_not_found"
        
        return resolved
    
    async def _resolve_diagnosis(self, record):
        """Resolve diagnosis terminology."""
        resolved = record.copy()
        
        if "icd_code" in record:
            icd_code = record["icd_code"]
            
            # Extract the base code without decimals for broader matching
            base_code = icd_code.split('.')[0] if '.' in icd_code else icd_code
            
            # Check if code exists in our database
            if icd_code in self.diagnosis_db:
                # Exact match
                diag_data = self.diagnosis_db[icd_code]
                
                # Add resolved information
                resolved["resolved_diagnosis"] = {
                    "original_code": icd_code,
                    "diagnosis_name": diag_data["name"],
                    "category": diag_data["category"],
                    "related_codes": diag_data.get("related_codes", []),
                    "parent_code": diag_data.get("parent", None)
                }
            elif base_code in self.diagnosis_db:
                # Base code match
                diag_data = self.diagnosis_db[base_code]
                
                # Add resolved information
                resolved["resolved_diagnosis"] = {
                    "original_code": icd_code,
                    "base_code": base_code,
                    "diagnosis_name": diag_data["name"] + " (specific subtype)",
                    "category": diag_data["category"],
                    "related_codes": diag_data.get("related_codes", []),
                    "estimated_match": True
                }
            else:
                resolved["terminology_resolution"] = "diagnosis_code_not_found"
        
        return resolved


class HealthDataSynthesizer(DeliberativeAgent):
    """Agent for synthesizing health data and identifying care gaps."""
    
    async def process_message(self, message):
        resolved_records = message.content.get("resolved_records", [])
        
        # Organize records by type for easier processing
        categorized_records = self._categorize_records(resolved_records)
        
        # Identify patient conditions
        conditions = await self._identify_conditions(categorized_records)
        
        # Identify current treatments
        treatments = await self._identify_treatments(categorized_records)
        
        # Find care gaps
        care_gaps = await self._identify_care_gaps(conditions, treatments, categorized_records)
        
        # Generate clinical recommendations
        recommendations = await self._generate_recommendations(conditions, treatments, care_gaps, categorized_records)
        
        # Create synthesized health data
        synthesis = {
            "patient_id": self._extract_patient_id(resolved_records),
            "conditions": conditions,
            "treatments": treatments,
            "care_gaps": care_gaps,
            "recommendations": recommendations,
            "records_analyzed": len(resolved_records),
            "record_types": list(categorized_records.keys()),
            "latest_record_date": self._get_latest_record_date(resolved_records)
        }
        
        # Forward synthesis to the output agent
        await self.send_message(
            recipients=[message.metadata.get("output_agent", "output")],
            content={"health_synthesis": synthesis, "original_records": resolved_records}
        )
    
    def _categorize_records(self, records):
        """Organize records by type."""
        categorized = {}
        
        for record in records:
            record_type = record.get("type", "unknown")
            if record_type not in categorized:
                categorized[record_type] = []
            
            categorized[record_type].append(record)
        
        return categorized
    
    def _extract_patient_id(self, records):
        """Extract patient ID from records."""
        # In a real implementation, this would ensure all records belong to the same patient
        # For this example, we'll generate a synthetic ID
        return f"P{uuid.uuid4().hex[:8].upper()}"
    
    def _get_latest_record_date(self, records):
        """Get the date of the most recent record."""
        dates = []
        
        for record in records:
            record_date = record.get("date")
            if record_date and record_date != "unknown":
                dates.append(record_date)
        
        return max(dates) if dates else "unknown"
    
    async def _identify_conditions(self, categorized_records):
        """Identify patient conditions from records."""
        conditions = []
        
        # Extract conditions from diagnosis records
        if "diagnosis" in categorized_records:
            for record in categorized_records["diagnosis"]:
                if "resolved_diagnosis" in record:
                    condition = {
                        "name": record["resolved_diagnosis"]["diagnosis_name"],
                        "icd_code": record.get("icd_code", "unknown"),
                        "category": record["resolved_diagnosis"].get("category", "unknown"),
                        "date_diagnosed": record.get("diagnosis_date", record.get("date", "unknown")),
                        "provider": record.get("provider", "unknown"),
                        "source_record_id": record.get("record_id")
                    }
                    conditions.append(condition)
        
        # Infer conditions from medications
        if "medication" in categorized_records:
            for record in categorized_records["medication"]:
                if "resolved_medication" in record:
                    med_conditions = record["resolved_medication"].get("treated_conditions", [])
                    
                    for condition_name in med_conditions:
                        # Check if condition already identified
                        if not any(c["name"].lower() == condition_name.lower() for c in conditions):
                            # Add as inferred condition
                            condition = {
                                "name": condition_name,
                                "inferred": True,
                                "inference_source": "medication",
                                "source_medication": record["resolved_medication"].get("generic_name", 
                                                   record["medication_name"]),
                                "provider": record.get("provider", "unknown"),
                                "source_record_id": record.get("record_id")
                            }
                            conditions.append(condition)
        
        # Infer conditions from lab results
        if "lab_result" in categorized_records:
            for record in categorized_records["lab_result"]:
                if "test_name" in record and "value" in record:
                    # Check glucose levels for potential diabetes
                    if "glucose" in record["test_name"].lower():
                        try:
                            glucose_value = float(record["value"])
                            if record.get("units") == "mmol/L" and glucose_value > 7.0:
                                if not any("diabetes" in c["name"].lower() for c in conditions):
                                    condition = {
                                        "name": "Potential diabetes",
                                        "inferred": True,
                                        "inference_source": "lab_result",
                                        "source_test": record["test_name"],
                                        "test_value": f"{glucose_value} {record.get('units', '')}",
                                        "date": record.get("date", "unknown"),
                                        "provider": record.get("provider", "unknown"),
                                        "source_record_id": record.get("record_id"),
                                        "requires_confirmation": True
                                    }
                                    conditions.append(condition)
                        except (ValueError, TypeError):
                            pass
                    
                    # Check cholesterol levels for potential hypercholesterolemia
                    elif "cholesterol" in record["test_name"].lower() and "total" in record["test_name"].lower():
                        try:
                            chol_value = float(record["value"])
                            if record.get("units") == "mmol/L" and chol_value > 5.2:
                                if not any("cholesterol" in c["name"].lower() for c in conditions):
                                    condition = {
                                        "name": "Potential hypercholesterolemia",
                                        "inferred": True,
                                        "inference_source": "lab_result",
                                        "source_test": record["test_name"],
                                        "test_value": f"{chol_value} {record.get('units', '')}",
                                        "date": record.get("date", "unknown"),
                                        "provider": record.get("provider", "unknown"),
                                        "source_record_id": record.get("record_id"),
                                        "requires_confirmation": True
                                    }
                                    conditions.append(condition)
                        except (ValueError, TypeError):
                            pass
        
        # Infer conditions from vital signs
        if "vital_signs" in categorized_records:
            for record in categorized_records["vital_signs"]:
                if "systolic" in record and "diastolic" in record:
                    try:
                        systolic = int(record["systolic"])
                        diastolic = int(record["diastolic"])
                        
                        # Check for potential hypertension
                        if systolic >= 140 or diastolic >= 90:
                            if not any("hypertension" in c["name"].lower() for c in conditions):
                                condition = {
                                    "name": "Potential hypertension",
                                    "inferred": True,
                                    "inference_source": "vital_signs",
                                    "source_measurement": "blood_pressure",
                                    "measurement_value": f"{systolic}/{diastolic} mmHg",
                                    "date": record.get("date", "unknown"),
                                    "provider": record.get("provider", "unknown"),
                                    "source_record_id": record.get("record_id"),
                                    "requires_confirmation": True
                                }
                                conditions.append(condition)
                    except (ValueError, TypeError):
                        pass
        
        return conditions
    
    async def _identify_treatments(self, categorized_records):
        """Identify current treatments from records."""
        treatments = []
        
        # Extract treatments from medication records
        if "medication" in categorized_records:
            for record in categorized_records["medication"]:
                if "resolved_medication" in record:
                    treatment = {
                        "type": "medication",
                        "name": record["medication_name"],
                        "generic_name": record["resolved_medication"].get("generic_name", record["medication_name"]),
                        "medication_class": record["resolved_medication"].get("medication_class", "unknown"),
                        "dosage": record.get("dosage", "unknown"),
                        "frequency": record.get("frequency", "unknown"),
                        "provider": record.get("provider", "unknown"),
                        "date_prescribed": record.get("date", "unknown"),
                        "source_record_id": record.get("record_id")
                    }
                    treatments.append(treatment)
        
        # Extract treatments from procedure records (if available)
        if "procedure" in categorized_records:
            for record in categorized_records["procedure"]:
                treatment = {
                    "type": "procedure",
                    "name": record.get("procedure_name", "unknown procedure"),
                    "date_performed": record.get("date", "unknown"),
                    "provider": record.get("provider", "unknown"),
                    "source_record_id": record.get("record_id")
                }
                treatments.append(treatment)
        
        return treatments
    
    async def _identify_care_gaps(self, conditions, treatments, categorized_records):
        """Identify care gaps based on conditions and treatments."""
        care_gaps = []
        
        # Check for diabetes without appropriate monitoring
        if any("diabetes" in c["name"].lower() for c in conditions):
            # Check for recent HbA1c test
            has_recent_hba1c = False
            if "lab_result" in categorized_records:
                for record in categorized_records["lab_result"]:
                    if "test_name" in record and "hba1c" in record["test_name"].lower():
                        # Check if test is recent (within 6 months)
                        if "date" in record and record["date"] != "unknown":
                            try:
                                test_date = datetime.strptime(record["date"], "%Y-%m-%d")
                                today = datetime.now()
                                if (today - test_date).days <= 180:
                                    has_recent_hba1c = True
                            except ValueError:
                                pass
            
            if not has_recent_hba1c:
                care_gaps.append({
                    "type": "missing_test",
                    "description": "No recent HbA1c test (last 6 months) for diabetic patient",
                    "severity": "high",
                    "related_condition": "diabetes"
                })
            
            # Check for missing diabetic medications in type 2 diabetes
            if any("type 2 diabetes" in c["name"].lower() for c in conditions):
                has_antidiabetic_med = False
                for treatment in treatments:
                    if treatment["type"] == "medication":
                        med_class = treatment.get("medication_class", "").lower()
                        if any(c in med_class for c in ["biguanide", "sulfonylurea", "dpp-4", "sglt2", "insulin"]):
                            has_antidiabetic_med = True
                            break
                
                if not has_antidiabetic_med:
                    care_gaps.append({
                        "type": "missing_medication",
                        "description": "No antidiabetic medication for type 2 diabetes",
                        "severity": "high",
                        "related_condition": "type 2 diabetes"
                    })
        
        # Check for hypertension without appropriate treatment
        if any("hypertension" in c["name"].lower() for c in conditions):
            has_antihypertensive = False
            for treatment in treatments:
                if treatment["type"] == "medication":
                    med_class = treatment.get("medication_class", "").lower()
                    if any(c in med_class for c in ["ace inhibitor", "arb", "beta blocker", "calcium channel blocker", "diuretic"]):
                        has_antihypertensive = True
                        break
            
            if not has_antihypertensive:
                care_gaps.append({
                    "type": "missing_medication",
                    "description": "No antihypertensive medication for hypertension",
                    "severity": "high",
                    "related_condition": "hypertension"
                })
        
        # Check for hypercholesterolemia without statin
        if any("cholesterol" in c["name"].lower() for c in conditions):
            has_statin = False
            for treatment in treatments:
                if treatment["type"] == "medication":
                    med_class = treatment.get("medication_class", "").lower()
                    if "statin" in med_class:
                        has_statin = True
                        break
            
            if not has_statin:
                care_gaps.append({
                    "type": "missing_medication",
                    "description": "No statin therapy for hypercholesterolemia",
                    "severity": "medium",
                    "related_condition": "hypercholesterolemia"
                })
        
        # Check for diabetes with hypertension on ACE inhibitor
        if any("diabetes" in c["name"].lower() for c in conditions) and any("hypertension" in c["name"].lower() for c in conditions):
            # Check for kidney function tests
            has_recent_renal_function = False
            if "lab_result" in categorized_records:
                for record in categorized_records["lab_result"]:
                    if "test_name" in record and any(term in record["test_name"].lower() for term in ["creatinine", "egfr", "kidney", "renal"]):
                        # Check if test is recent (within 1 year)
                        if "date" in record and record["date"] != "unknown":
                            try:
                                test_date = datetime.strptime(record["date"], "%Y-%m-%d")
                                today = datetime.now()
                                if (today - test_date).days <= 365:
                                    has_recent_renal_function = True
                            except ValueError:
                                pass
            
            # Check if on ACE inhibitor
            on_ace_inhibitor = False
            for treatment in treatments:
                if treatment["type"] == "medication":
                    med_class = treatment.get("medication_class", "").lower()
                    if "ace inhibitor" in med_class:
                        on_ace_inhibitor = True
                        break
            
            if on_ace_inhibitor and not has_recent_renal_function:
                care_gaps.append({
                    "type": "missing_test",
                    "description": "No recent kidney function test for diabetic patient on ACE inhibitor",
                    "severity": "high",
                    "related_condition": "diabetes with hypertension"
                })
        
        return care_gaps
    
    async def _generate_recommendations(self, conditions, treatments, care_gaps, categorized_records):
        """Generate clinical recommendations based on identified care gaps."""
        recommendations = []
        
        # Convert care gaps to recommendations
        for gap in care_gaps:
            if gap["type"] == "missing_test":
                recommendations.append({
                    "priority": "high" if gap["severity"] == "high" else "medium",
                    "recommendation": f"Schedule {gap['description'].split('No recent ')[1].split(' for')[0]}",
                    "reason": gap["description"],
                    "type": "diagnostic"
                })
            elif gap["type"] == "missing_medication":
                recommendations.append({
                    "priority": "high" if gap["severity"] == "high" else "medium",
                    "recommendation": f"Consider medication for {gap['related_condition']}",
                    "reason": gap["description"],
                    "type": "medication"
                })
        
        # Add recommendations for potential conditions requiring confirmation
        for condition in conditions:
            if condition.get("inferred", False) and condition.get("requires_confirmation", False):
                recommendations.append({
                    "priority": "medium",
                    "recommendation": f"Confirm potential diagnosis of {condition['name']}",
                    "reason": f"Abnormal {condition['inference_source']} ({condition.get('source_test', '')}: {condition.get('test_value', '')})",
                    "type": "diagnostic"
                })
        
        # Check medication interactions
        statins = []
        fibrates = []
        
        for treatment in treatments:
            if treatment["type"] == "medication":
                med_class = treatment.get("medication_class", "").lower()
                if "statin" in med_class:
                    statins.append(treatment["name"])
                elif "fibrate" in med_class:
                    fibrates.append(treatment["name"])
        
        # Check for statin-fibrate interaction
        if statins and fibrates:
            recommendations.append({
                "priority": "high",
                "recommendation": "Review lipid-lowering medication regimen",
                "reason": f"Potential interaction between statin ({', '.join(statins)}) and fibrate ({', '.join(fibrates)})",
                "type": "medication_safety"
            })
        
        # Check for diabetes patients without eye exam
        if any("diabetes" in c["name"].lower() for c in conditions):
            has_eye_exam = False
            if "procedure" in categorized_records:
                for record in categorized_records["procedure"]:
                    if "procedure_name" in record and any(term in record["procedure_name"].lower() for term in ["eye exam", "retinal", "ophthalmology"]):
                        has_eye_exam = True
                        break
            
            if not has_eye_exam:
                recommendations.append({
                    "priority": "medium",
                    "recommendation": "Schedule diabetic eye examination",
                    "reason": "No record of eye examination for diabetic patient",
                    "type": "preventive"
                })
        
        return recommendations


class OutputAgent(ReflexAgent):
    """Output agent that packages the results of healthcare data integration."""
    
    async def process_message(self, message):
        health_synthesis = message.content.get("health_synthesis", {})
        original_records = message.content.get("original_records", [])
        
        # Create summary statistics
        record_count = len(original_records)
        provider_count = len(set(record.get("provider", "unknown") for record in original_records))
        condition_count = len(health_synthesis.get("conditions", []))
        treatment_count = len(health_synthesis.get("treatments", []))
        gap_count = len(health_synthesis.get("care_gaps", []))
        recommendation_count = len(health_synthesis.get("recommendations", []))
        
        # Create the final output
        output = {
            "patient_id": health_synthesis.get("patient_id", "unknown"),
            "integration_id": str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "records_processed": record_count,
                "providers_integrated": provider_count,
                "conditions_identified": condition_count,
                "treatments_identified": treatment_count,
                "care_gaps_found": gap_count,
                "recommendations_generated": recommendation_count
            },
            "health_data": health_synthesis,
            "integration_metadata": {
                "language_breakdown": self._count_languages(original_records),
                "provider_breakdown": self._count_providers(original_records),
                "record_type_breakdown": self._count_record_types(original_records)
            }
        }
        
        return output
    
    def _count_languages(self, records):
        """Count records by language."""
        language_counts = {}
        
        for record in records:
            lang = record.get("detected_language", "unknown")
            if lang not in language_counts:
                language_counts[lang] = 0
            language_counts[lang] += 1
        
        return language_counts
    
    def _count_providers(self, records):
        """Count records by provider."""
        provider_counts = {}
        
        for record in records:
            provider = record.get("provider", "unknown")
            if provider not in provider_counts:
                provider_counts[provider] = 0
            provider_counts[provider] += 1
        
        return provider_counts
    
    def _count_record_types(self, records):
        """Count records by type."""
        type_counts = {}
        
        for record in records:
            record_type = record.get("type", "unknown")
            if record_type not in type_counts:
                type_counts[record_type] = 0
            type_counts[record_type] += 1
        
        return type_counts


class HealthcareDataIntegrationMicroservice(BaseMicroservice):
    """Microservice for healthcare data integration."""
    
    def _initialize(self):
        """Initialize the healthcare data integration agents."""
        self.agents = {
            "multilingual_nlp": MultilingualNLPComponent(name="Multilingual NLP Component"),
            "measurement_standardization": MeasurementStandardization(name="Measurement Standardization"),
            "medical_terminology_resolver": MedicalTerminologyResolver(name="Medical Terminology Resolver"),
            "health_data_synthesizer": HealthDataSynthesizer(name="Health Data Synthesizer"),
            "output": OutputAgent(name="Output Agent")
        }
    
    def get_circuit_definition(self):
        """Get the circuit definition for healthcare data integration."""
        return CircuitDefinition.create(
            name=f"{self.name} Circuit",
            description=self.description or "Healthcare data integration pipeline",
            agents={
                "multilingual_nlp": {
                    "type": "MultilingualNLPComponent",
                    "instance": self.agents["multilingual_nlp"]
                },
                "measurement_standardization": {
                    "type": "MeasurementStandardization",
                    "instance": self.agents["measurement_standardization"]
                },
                "medical_terminology_resolver": {
                    "type": "MedicalTerminologyResolver",
                    "instance": self.agents["medical_terminology_resolver"]
                },
                "health_data_synthesizer": {
                    "type": "HealthDataSynthesizer",
                    "instance": self.agents["health_data_synthesizer"]
                },
                "output": {
                    "type": "OutputAgent",
                    "instance": self.agents["output"]
                }
            },
            connections=[
                {
                    "source": "multilingual_nlp",
                    "target": "measurement_standardization",
                    "connection_type": ConnectionType.DIRECT
                },
                {
                    "source": "measurement_standardization",
                    "target": "medical_terminology_resolver",
                    "connection_type": ConnectionType.DIRECT
                },
                {
                    "source": "medical_terminology_resolver",
                    "target": "health_data_synthesizer",
                    "connection_type": ConnectionType.DIRECT
                },
                {
                    "source": "health_data_synthesizer",
                    "target": "output",
                    "connection_type": ConnectionType.DIRECT
                }
            ],
            input_agents=["multilingual_nlp"],
            output_agents=["output"]
        )
    
    async def integrate_patient_records(self, patient_records):
        """Integrate patient health records."""
        input_data = {
            "patient_records": patient_records
        }
        return await self.process(input_data)
