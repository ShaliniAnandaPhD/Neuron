# scripts/tools/pii_detector.py

import re

class PIIDetectionTool:
    """
    A tool to detect Personally Identifiable Information (PII) in text.
    
    This is a basic implementation using regular expressions. For a production
    system, using a library like spaCy or Microsoft Presidio would be more robust.
    """
    def __init__(self):
        print("🛠️  Tool Loaded: PIIDetectionTool")
        # Regex for simple name patterns (e.g., John Doe)
        self.name_pattern = re.compile(r'\b([A-Z][a-z]+)\s([A-Z][a-z]+)\b')
        # Regex for simple phone number patterns
        self.phone_pattern = re.compile(r'\b(\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4})\b')
        # Regex for simple email patterns
        self.email_pattern = re.compile(r'\b([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\b')

    def run(self, text_to_scan: str) -> dict:
        """
        Scans the input text for PII and returns a report.
        
        Args:
            text_to_scan: The string to analyze.
        
        Returns:
            A dictionary containing detected PII.
        """
        detections = {
            "names_found": self.name_pattern.findall(text_to_scan),
            "phones_found": self.phone_pattern.findall(text_to_scan),
            "emails_found": self.email_pattern.findall(text_to_scan)
        }
        
        pii_found = any(detections.values())
        
        report = {
            "pii_detected": pii_found,
            "details": detections
        }
        
        print(f"🛡️  PII Check Report: {report}")
        return report

