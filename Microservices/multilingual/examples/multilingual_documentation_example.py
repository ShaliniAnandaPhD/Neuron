# examples/multilingual_documentation_example.py

import asyncio
from microservices.multilingual.multilingual_documentation import MultilingualDocumentationMicroservice

async def main():
    # Create medical device documentation microservice
    doc_service = MultilingualDocumentationMicroservice(
        name="Medical Device Documentation Service",
        description="Processes technical documentation for medical devices across languages"
    )
    
    # Deploy the service
    doc_service.deploy()
    
    # Example cardiac monitor operation manual section
    cardiac_monitor_manual = """
    # Operation Manual: CardioSense Pro X7
    
    ## Warning: Safety Precautions
    
    WARNING: Do not use this device in the presence of flammable anesthetics or gases.
    
    WARNING: This device must be used with the supplied 24V DC power adapter rated for medical use.
    
    ## Installation
    
    1. Position the monitor at least 6 inches away from other electronic devices.
    2. Connect the power adapter to a hospital-grade outlet rated for 110V/60Hz.
    3. Attach the patient leads according to the color-coding guide below.
    
    ## Measurement Specifications
    
    - Operating Temperature: 50°F to 85°F
    - Humidity Range: 30% to 75% non-condensing
    - Storage Temperature: 32°F to 95°F
    - Weight: 2.5 lb (without accessories)
    - Dimensions: 8 inches × 6 inches × 2 inches
    
    ## Troubleshooting
    
    If the device shows error code E101:
    1. Disconnect from power for 30 seconds
    2. Reconnect and power on
    3. If error persists, call technical support at 1-800-555-0123
    
    CAUTION: Do not attempt to open the device housing. There are no user-serviceable parts inside.
    """
    
    # Translate the document from English to Japanese
    result = await doc_service.translate_document(
        document=cardiac_monitor_manual,
        source_language="en_US",
        target_language="ja_JP"
    )
    
    # Print the results
    print("Translation completed:")
    print(f"Document ID: {result['document_id']}")
    print(f"Source: {result['source_language']} → Target: {result['target_language']}")
    print("\nMetadata:")
    print(f"- Terminology count: {result['metadata']['terminology_count']}")
    print(f"- Cultural adaptations: {', '.join(result['metadata']['cultural_adaptations'])}")
    print(f"- Safety verified: {result['metadata']['safety_verified']}")
    
    if not result['metadata']['safety_verified']:
        print("\nSafety Issues:")
        for issue in result['metadata']['issues']:
            print(f"- {issue['type']}: {issue['issue']}")
    
    print("\nTranslated Document:")
    print(result['translated_document'])

if __name__ == "__main__":
    asyncio.run(main())
