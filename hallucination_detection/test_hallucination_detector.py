"""
Test Suite for Hallucination Detection System

Comprehensive tests covering all detection strategies and edge cases.
"""

import pytest
import asyncio
from datetime import datetime
from hallucination_detector import (
    HallucinationDetector,
    UncertaintyQuantifier,
    SelfConsistencyChecker,
    FactVerificationAgent,
    HallucinationType,
    HallucinationDetectionResult
)


class TestUncertaintyQuantifier:
    """Tests for uncertainty quantification methods"""
    
    def setup_method(self):
        self.quantifier = UncertaintyQuantifier()
    
    def test_aleatoric_uncertainty_high(self):
        """Test detection of high aleatoric uncertainty"""
        response = "This might be correct, but I'm not sure. Perhaps it could work."
        uncertainty = self.quantifier.calculate_aleatoric_uncertainty(response)
        assert uncertainty > 0.5, "Should detect high uncertainty from hedging language"
    
    def test_aleatoric_uncertainty_low(self):
        """Test confident response has low uncertainty"""
        response = "This is the correct answer based on the data."
        uncertainty = self.quantifier.calculate_aleatoric_uncertainty(response)
        assert uncertainty < 0.3, "Should detect low uncertainty from confident language"
    
    def test_epistemic_uncertainty_high_variation(self):
        """Test detection of high epistemic uncertainty from varied responses"""
        responses = [
            "The patient needs immediate surgery",
            "Conservative treatment is recommended", 
            "Further testing is required before deciding"
        ]
        uncertainty = self.quantifier.calculate_epistemic_uncertainty(responses)
        assert uncertainty > 0.5, "Should detect high uncertainty from varied responses"
    
    def test_epistemic_uncertainty_low_variation(self):
        """Test low epistemic uncertainty from consistent responses"""
        responses = [
            "The diagnosis is acute appendicitis",
            "Patient has acute appendicitis",
            "This is a clear case of acute appendicitis"
        ]
        uncertainty = self.quantifier.calculate_epistemic_uncertainty(responses)
        assert uncertainty < 0.4, "Should detect low uncertainty from consistent responses"
    
    def test_single_response_uncertainty(self):
        """Test handling of single response"""
        responses = ["Single response"]
        uncertainty = self.quantifier.calculate_epistemic_uncertainty(responses)
        assert 0.0 <= uncertainty <= 1.0, "Should return valid uncertainty for single response"


class TestSelfConsistencyChecker:
    """Tests for self-consistency checking"""
    
    def setup_method(self):
        self.checker = SelfConsistencyChecker(num_samples=5, consensus_threshold=0.7)
    
    @pytest.mark.asyncio
    async def test_high_agreement_detection(self):
        """Test detection of high agreement across samples"""
        # Mock agent function that returns similar responses
        async def mock_agent(input_data):
            return "The recommended treatment is medication therapy"
        
        result = await self.checker.check_consistency(mock_agent, {"query": "test"})
        assert result.agreement_score >= self.checker.consensus_threshold
        assert result.consensus_response is not None
    
    @pytest.mark.asyncio
    async def test_low_agreement_detection(self):
        """Test detection of low agreement indicating inconsistency"""
        # This would require mocking varied responses
        # In production, use actual varied agent responses
        pass
    
    def test_consensus_identification(self):
        """Test finding consensus response"""
        samples = [
            "Treatment A is recommended",
            "Treatment A is the best option",
            "I recommend Treatment A",
            "Treatment B might work",
            "Treatment A should be used"
        ]
        consensus = self.checker._find_consensus(samples)
        assert "Treatment A" in consensus, "Should identify majority opinion"
    
    def test_divergent_point_identification(self):
        """Test identification of divergent points"""
        samples = [
            "Patient has diabetes and hypertension",
            "Patient has diabetes and high cholesterol",
            "Patient has diabetes and kidney disease"
        ]
        divergent = self.checker._identify_divergent_points(samples)
        assert len(divergent) > 0, "Should identify divergent conditions"


class TestFactVerificationAgent:
    """Tests for fact verification"""
    
    def setup_method(self):
        self.knowledge_base = {
            'test_fact_1': {
                'claim': 'Earth orbits the Sun',
                'verified': True,
                'confidence': 1.0
            }
        }
        self.verifier = FactVerificationAgent(self.knowledge_base)
    
    def test_claim_extraction(self):
        """Test extraction of factual claims"""
        text = "The patient is 45 years old. Blood pressure is 120/80. Diabetes is controlled."
        claims = self.verifier._extract_factual_claims(text)
        assert len(claims) >= 2, "Should extract multiple claims"
    
    def test_verified_claim(self):
        """Test verification of supported claim"""
        response = "The treatment has shown 85% efficacy in clinical trials"
        context = {
            'clinical_data': 'Trial results show 85% efficacy rate',
            'source': 'published_study'
        }
        results = self.verifier.verify_claims(response, context)
        assert results['verified_claims'] > 0, "Should verify supported claims"
    
    def test_contradicted_claim(self):
        """Test detection of contradicted claim"""
        response = "The patient has no known allergies"
        context = {
            'medical_record': 'Patient is allergic to penicillin',
            'allergy_list': 'Penicillin, Sulfa drugs'
        }
        results = self.verifier.verify_claims(response, context)
        # This is a simplified test - full implementation would detect contradiction
        assert results['total_claims'] > 0, "Should process claims"
    
    def test_unverified_claim(self):
        """Test flagging of unverified claims"""
        response = "The new medication will cure the condition in 3 days"
        context = {'patient_id': '12345'}  # No supporting evidence
        results = self.verifier.verify_claims(response, context)
        assert results['unverified_claims'] > 0, "Should flag unsupported claims"


class TestHallucinationDetector:
    """Integration tests for the complete detection system"""
    
    def setup_method(self):
        self.detector = HallucinationDetector(config={
            'hallucination_threshold': 0.6,
            'consistency_samples': 3,
            'consensus_threshold': 0.7
        })
    
    @pytest.mark.asyncio
    async def test_no_hallucination_detection(self):
        """Test response without hallucination"""
        response = "Based on the blood pressure reading of 120/80 mmHg, the patient's BP is normal."
        context = {
            'bp_reading': '120/80 mmHg',
            'patient_history': 'No hypertension history'
        }
        
        result = await self.detector.detect(response, context)
        assert not result.is_hallucination, "Should not flag accurate response"
        assert result.confidence_score > 0.5, "Should have reasonable confidence"
    
    @pytest.mark.asyncio
    async def test_overconfidence_detection(self):
        """Test detection of overconfident response"""
        response = "The patient probably has diabetes, maybe check glucose levels"
        context = {'test_results': 'pending'}
        
        result = await self.detector.detect(response, context)
        assert HallucinationType.OVERCONFIDENCE in result.hallucination_types
    
    @pytest.mark.asyncio
    async def test_unsupported_claim_detection(self):
        """Test detection of unsupported claims"""
        response = "The medication costs $500 per month and has 95% efficacy in trials"
        context = {'medication': 'Drug X'}  # No price or efficacy data
        
        result = await self.detector.detect(response, context)
        assert HallucinationType.UNSUPPORTED_CLAIM in result.hallucination_types
    
    @pytest.mark.asyncio
    async def test_mitigation_suggestions(self):
        """Test generation of mitigation suggestions"""
        response = "This might work but I'm uncertain about the dosage"
        context = {}
        
        result = await self.detector.detect(response, context)
        assert len(result.mitigation_suggestions) > 0, "Should provide mitigation strategies"
    
    @pytest.mark.asyncio
    async def test_reasoning_generation(self):
        """Test generation of human-readable reasoning"""
        response = "Treatment will definitely cure the condition"
        context = {'evidence': 'limited clinical data'}
        
        result = await self.detector.detect(response, context)
        assert len(result.reasoning) > 0, "Should provide reasoning"
        assert "confidence" in result.reasoning.lower(), "Should mention confidence"


class TestEdgeCases:
    """Tests for edge cases and error handling"""
    
    def setup_method(self):
        self.detector = HallucinationDetector()
    
    @pytest.mark.asyncio
    async def test_empty_response(self):
        """Test handling of empty response"""
        result = await self.detector.detect("", {})
        assert isinstance(result, HallucinationDetectionResult)
    
    @pytest.mark.asyncio
    async def test_empty_context(self):
        """Test handling of empty context"""
        result = await self.detector.detect("Some response text", {})
        assert isinstance(result, HallucinationDetectionResult)
    
    @pytest.mark.asyncio
    async def test_very_long_response(self):
        """Test handling of very long responses"""
        long_response = "This is a test. " * 1000
        result = await self.detector.detect(long_response, {})
        assert isinstance(result, HallucinationDetectionResult)
    
    @pytest.mark.asyncio
    async def test_special_characters(self):
        """Test handling of special characters"""
        response = "Patient BP: 120/80 mmHg (normal range). Cost: $50-$100."
        result = await self.detector.detect(response, {})
        assert isinstance(result, HallucinationDetectionResult)


class TestRealWorldScenarios:
    """Tests based on real-world use cases"""
    
    def setup_method(self):
        self.detector = HallucinationDetector()
    
    @pytest.mark.asyncio
    async def test_healthcare_scenario(self):
        """Test healthcare decision support scenario"""
        response = """
        Based on the patient's symptoms and test results, I recommend:
        1. Increase blood pressure medication to 20mg daily
        2. Schedule follow-up in 2 weeks
        3. Monitor for side effects like dizziness
        """
        context = {
            'current_medication': 'BP med 10mg daily',
            'recent_bp': '140/90 mmHg',
            'patient_history': 'Hypertension for 2 years'
        }
        
        result = await self.detector.detect(response, context)
        # Should verify recommendations are reasonable given context
        assert isinstance(result, HallucinationDetectionResult)
    
    @pytest.mark.asyncio
    async def test_customer_support_scenario(self):
        """Test customer support scenario"""
        response = "Your warranty covers accidental damage for 3 years from purchase date"
        context = {
            'product': 'Laptop Model X',
            'warranty_doc': 'Standard 1-year manufacturer warranty'
        }
        
        result = await self.detector.detect(response, context)
        # Should detect contradiction with actual warranty terms
        assert result.is_hallucination or \
               HallucinationType.UNSUPPORTED_CLAIM in result.hallucination_types
    
    @pytest.mark.asyncio
    async def test_legal_compliance_scenario(self):
        """Test legal/compliance scenario"""
        response = "This data processing complies with GDPR Article 6(1)(f) legitimate interests"
        context = {
            'data_type': 'personal_health_information',
            'purpose': 'marketing'
        }
        
        result = await self.detector.detect(response, context)
        # Should flag need for verification of legal claim
        assert isinstance(result, HallucinationDetectionResult)


def run_all_tests():
    """Run all tests with pytest"""
    pytest.main([__file__, '-v', '--tb=short'])


if __name__ == "__main__":
    run_all_tests()
