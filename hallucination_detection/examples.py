"""
Hallucination Detection - Usage Examples

Demonstrates practical applications of the hallucination detection system
across various domains and use cases.
"""

import asyncio
from hallucination_detector import (
    HallucinationDetector,
    HallucinationType,
    ConfidenceLevel
)


# =============================================================================
# Example 1: Healthcare Clinical Decision Support
# =============================================================================

async def healthcare_example():
    """
    Example: Detecting hallucinations in clinical recommendations
    """
    print("\n" + "=" * 70)
    print("EXAMPLE 1: Healthcare Clinical Decision Support")
    print("=" * 70)
    
    detector = HallucinationDetector(config={
        'hallucination_threshold': 0.7,  # Higher threshold for medical safety
        'consistency_samples': 5,
        'consensus_threshold': 0.8
    })
    
    # Scenario: AI recommends treatment based on patient data
    clinical_response = """
    Based on the blood pressure reading of 180/120 mmHg, the patient has
    severe hypertension requiring immediate intervention. I recommend 
    increasing the ACE inhibitor dosage to 40mg daily and scheduling a
    follow-up in one week to reassess. The patient should also start
    a low-sodium diet immediately.
    """
    
    patient_context = {
        'patient_id': 'P12345',
        'current_medications': 'Lisinopril 10mg daily',
        'recent_bp_readings': ['140/90', '145/92', '150/95'],
        'allergies': 'None known',
        'medical_history': 'Hypertension diagnosed 6 months ago',
        'age': 55,
        'last_visit': '2024-01-15'
    }
    
    result = await detector.detect(clinical_response, patient_context)
    
    print(f"\nClinical Response Analysis:")
    print(f"  Hallucination Detected: {result.is_hallucination}")
    print(f"  Confidence Score: {result.confidence_score:.3f}")
    print(f"  Detected Issues: {[ht.value for ht in result.hallucination_types]}")
    print(f"\n  Reasoning: {result.reasoning}")
    print(f"\n  Recommended Actions:")
    for suggestion in result.mitigation_suggestions:
        print(f"    - {suggestion}")
    
    # Decision: Route to human physician if hallucination detected
    if result.is_hallucination or result.confidence_score < 0.8:
        print(f"\n  ⚠️  ESCALATION: Routing to human physician for review")
    else:
        print(f"\n  ✓ Recommendation appears safe to present to provider")


# =============================================================================
# Example 2: Customer Support - Product Information
# =============================================================================

async def customer_support_example():
    """
    Example: Preventing false product information in customer support
    """
    print("\n" + "=" * 70)
    print("EXAMPLE 2: Customer Support Product Information")
    print("=" * 70)
    
    detector = HallucinationDetector(config={
        'hallucination_threshold': 0.6,
        'consistency_samples': 3
    })
    
    # Scenario: Support agent answering warranty question
    support_response = """
    Your Premium Plus warranty covers accidental damage, water damage, and
    theft for a full 3 years from your purchase date. You can file up to
    5 claims per year with no deductible. The warranty also includes free
    battery replacements every 12 months.
    """
    
    product_context = {
        'product_id': 'LAPTOP-X1000',
        'purchase_date': '2024-01-15',
        'warranty_type': 'Standard 1-year manufacturer warranty',
        'warranty_terms': {
            'duration': '1 year',
            'coverage': 'Manufacturing defects only',
            'exclusions': 'Accidental damage, water damage, theft',
            'claims_limit': 'Unlimited for covered issues'
        },
        'customer_tier': 'Regular'
    }
    
    result = await detector.detect(support_response, product_context)
    
    print(f"\nSupport Response Analysis:")
    print(f"  Hallucination Detected: {result.is_hallucination}")
    print(f"  Confidence Score: {result.confidence_score:.3f}")
    print(f"  Detected Issues: {[ht.value for ht in result.hallucination_types]}")
    
    # Check for specific unsupported claims
    if HallucinationType.UNSUPPORTED_CLAIM in result.hallucination_types:
        print(f"\n  ⚠️  WARNING: Response contains unverified warranty claims")
        print(f"  Action: Requesting citation of official warranty documentation")
    
    print(f"\n  Mitigation Steps:")
    for suggestion in result.mitigation_suggestions:
        print(f"    - {suggestion}")


# =============================================================================
# Example 3: Legal Compliance Verification
# =============================================================================

async def legal_compliance_example():
    """
    Example: Verifying legal and compliance statements
    """
    print("\n" + "=" * 70)
    print("EXAMPLE 3: Legal Compliance Verification")
    print("=" * 70)
    
    detector = HallucinationDetector(config={
        'hallucination_threshold': 0.8,  # Very high threshold for legal
        'consistency_samples': 7,
        'consensus_threshold': 0.9
    })
    
    # Scenario: AI providing GDPR compliance guidance
    compliance_response = """
    Your data processing activity is compliant with GDPR Article 6(1)(f)
    based on legitimate interests. You don't need explicit consent because
    the processing is necessary for your business operations. The data can
    be retained indefinitely as long as it serves your business purpose.
    """
    
    compliance_context = {
        'data_type': 'customer_email_addresses',
        'processing_purpose': 'marketing_campaigns',
        'data_subjects': 'EU_residents',
        'retention_policy': 'not_specified',
        'consent_obtained': False,
        'legitimate_interest_assessment': 'not_performed'
    }
    
    result = await detector.detect(compliance_response, compliance_context)
    
    print(f"\nCompliance Statement Analysis:")
    print(f"  Hallucination Detected: {result.is_hallucination}")
    print(f"  Confidence Score: {result.confidence_score:.3f}")
    print(f"  Legal Risk Level: {'HIGH' if result.is_hallucination else 'MEDIUM'}")
    
    if result.is_hallucination or result.confidence_score < 0.9:
        print(f"\n  🚨 CRITICAL: Legal claim requires human attorney review")
        print(f"  Reason: {result.reasoning}")
    
    print(f"\n  Required Actions:")
    for suggestion in result.mitigation_suggestions:
        print(f"    - {suggestion}")
    print(f"    - Consult qualified legal counsel before proceeding")


# =============================================================================
# Example 4: Emergency Response Triage
# =============================================================================

async def emergency_response_example():
    """
    Example: Hallucination detection in emergency triage
    """
    print("\n" + "=" * 70)
    print("EXAMPLE 4: Emergency Response Triage")
    print("=" * 70)
    
    detector = HallucinationDetector(config={
        'hallucination_threshold': 0.75,
        'consistency_samples': 5,
        'consensus_threshold': 0.85
    })
    
    # Scenario: AI triaging emergency call
    triage_response = """
    Based on the reported symptoms, this appears to be a moderate priority
    case. The chest pain is likely muscular strain from the reported heavy
    lifting. Recommend patient takes over-the-counter pain medication and
    follows up with primary care doctor tomorrow. No need for immediate
    emergency room visit.
    """
    
    emergency_context = {
        'reported_symptoms': [
            'chest_pain_radiating_to_left_arm',
            'shortness_of_breath',
            'sweating',
            'nausea'
        ],
        'patient_age': 58,
        'medical_history': 'hypertension, high_cholesterol',
        'recent_activity': 'heavy_lifting_30_minutes_ago',
        'pain_scale': '8/10',
        'duration': '15_minutes'
    }
    
    result = await detector.detect(triage_response, emergency_context)
    
    print(f"\nTriage Assessment Analysis:")
    print(f"  Hallucination Detected: {result.is_hallucination}")
    print(f"  Confidence Score: {result.confidence_score:.3f}")
    
    # Critical check for emergency scenarios
    if result.is_hallucination or result.confidence_score < 0.9:
        print(f"\n  🚨 ALERT: Triage recommendation flagged for immediate human review")
        print(f"  Risk: Potentially dangerous underestimation of symptoms")
        print(f"  Protocol: Escalate to emergency medical dispatcher immediately")
    
    print(f"\n  Detection Details:")
    print(f"    Issues: {[ht.value for ht in result.hallucination_types]}")
    print(f"    Evidence: {result.reasoning}")


# =============================================================================
# Example 5: Financial Advisory
# =============================================================================

async def financial_advisory_example():
    """
    Example: Detecting hallucinations in financial advice
    """
    print("\n" + "=" * 70)
    print("EXAMPLE 5: Financial Advisory")
    print("=" * 70)
    
    detector = HallucinationDetector(config={
        'hallucination_threshold': 0.65,
        'consistency_samples': 5
    })
    
    # Scenario: AI providing investment recommendation
    financial_response = """
    Based on your risk tolerance and investment timeline, I recommend
    allocating 80% of your portfolio to cryptocurrency investments,
    specifically emerging altcoins. Historical data shows these can
    return 500% annually with minimal risk. You should liquidate your
    retirement accounts to maximize this opportunity.
    """
    
    client_context = {
        'age': 55,
        'risk_tolerance': 'conservative',
        'investment_timeline': '10_years_to_retirement',
        'current_portfolio': {
            'stocks': 40,
            'bonds': 50,
            'cash': 10
        },
        'financial_goals': 'retirement_security',
        'dependents': 2
    }
    
    result = await detector.detect(financial_response, client_context)
    
    print(f"\nFinancial Advice Analysis:")
    print(f"  Hallucination Detected: {result.is_hallucination}")
    print(f"  Confidence Score: {result.confidence_score:.3f}")
    print(f"  Detected Issues: {[ht.value for ht in result.hallucination_types]}")
    
    if result.is_hallucination:
        print(f"\n  ⚠️  WARNING: Advice contradicts client profile and risk tolerance")
        print(f"  Action: Blocking recommendation and flagging for human advisor")
        print(f"  Reason: {result.reasoning}")
    
    print(f"\n  Required Safeguards:")
    for suggestion in result.mitigation_suggestions:
        print(f"    - {suggestion}")


# =============================================================================
# Example 6: Multi-Session Memory Consistency
# =============================================================================

async def multi_session_consistency_example():
    """
    Example: Checking consistency across multiple sessions
    """
    print("\n" + "=" * 70)
    print("EXAMPLE 6: Multi-Session Memory Consistency")
    print("=" * 70)
    
    detector = HallucinationDetector()
    
    # Scenario: Checking if current response contradicts previous sessions
    current_response = """
    Your monthly premium for the health insurance plan is $450, and
    your deductible is $2,000. This has been consistent since you
    enrolled in January 2024.
    """
    
    context_with_history = {
        'customer_id': 'C789',
        'current_session': 'session_5',
        'previous_interactions': [
            {
                'session_id': 'session_1',
                'date': '2024-01-15',
                'claim': 'Monthly premium is $350'
            },
            {
                'session_id': 'session_3', 
                'date': '2024-02-10',
                'claim': 'Deductible is $2,000'
            },
            {
                'session_id': 'session_4',
                'date': '2024-02-20',
                'claim': 'Premium is $350 per month'
            }
        ],
        'policy_changes': []  # No documented changes
    }
    
    result = await detector.detect(current_response, context_with_history)
    
    print(f"\nCross-Session Consistency Analysis:")
    print(f"  Hallucination Detected: {result.is_hallucination}")
    print(f"  Confidence Score: {result.confidence_score:.3f}")
    
    if HallucinationType.FACTUAL_INCONSISTENCY in result.hallucination_types:
        print(f"\n  ⚠️  INCONSISTENCY: Current claim contradicts previous sessions")
        print(f"  Previous claims: $350/month premium")
        print(f"  Current claim: $450/month premium")
        print(f"  Action: Requesting verification of actual policy terms")


# =============================================================================
# Main Execution
# =============================================================================

async def main():
    """Run all examples"""
    print("\n" + "=" * 70)
    print("HALLUCINATION DETECTION SYSTEM - USAGE EXAMPLES")
    print("=" * 70)
    
    await healthcare_example()
    await customer_support_example()
    await legal_compliance_example()
    await emergency_response_example()
    await financial_advisory_example()
    await multi_session_consistency_example()
    
    print("\n" + "=" * 70)
    print("Examples completed successfully!")
    print("=" * 70)
    print("\nKey Takeaways:")
    print("  1. Different domains require different confidence thresholds")
    print("  2. High-risk scenarios (medical, legal) need stricter validation")
    print("  3. Multi-session consistency prevents contradictory information")
    print("  4. Evidence-based verification reduces unsupported claims")
    print("  5. Mitigation suggestions enable graceful handling of hallucinations")
    print("\n")


if __name__ == "__main__":
    asyncio.run(main())
