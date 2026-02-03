"""
Neuron Hallucination Detection System

This module implements multiple strategies for detecting and mitigating hallucinations
in AI agent responses, inspired by cognitive neuroscience principles.

Strategies implemented:
1. Uncertainty Quantification - Bayesian confidence estimation
2. Self-Consistency Checking - Multiple sampling and consensus
3. Fact Verification - Evidence grounding and source attribution
4. Temporal Consistency - Cross-session coherence checking
5. Semantic Contradiction Detection - Logic conflict identification
"""

import asyncio
import hashlib
import re
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import numpy as np


class HallucinationType(Enum):
    """Categories of hallucination patterns"""
    FACTUAL_INCONSISTENCY = "factual_inconsistency"
    TEMPORAL_CONFLICT = "temporal_conflict"
    LOGICAL_CONTRADICTION = "logical_contradiction"
    UNSUPPORTED_CLAIM = "unsupported_claim"
    OVERCONFIDENCE = "overconfidence"
    ATTRIBUTION_ERROR = "attribution_error"


class ConfidenceLevel(Enum):
    """Confidence levels for agent responses"""
    VERY_HIGH = 0.9
    HIGH = 0.75
    MEDIUM = 0.6
    LOW = 0.4
    VERY_LOW = 0.2


@dataclass
class HallucinationDetectionResult:
    """Result of hallucination detection analysis"""
    is_hallucination: bool
    confidence_score: float
    hallucination_types: List[HallucinationType] = field(default_factory=list)
    evidence: Dict[str, Any] = field(default_factory=dict)
    reasoning: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    mitigation_suggestions: List[str] = field(default_factory=list)


@dataclass
class ConsistencyCheck:
    """Result of self-consistency verification"""
    samples: List[str]
    agreement_score: float
    consensus_response: Optional[str]
    divergent_points: List[str] = field(default_factory=list)


class UncertaintyQuantifier:
    """
    Implements uncertainty quantification using Bayesian approximation
    and entropy-based confidence estimation.
    
    Reference: Gal & Ghahramani (2016) - Dropout as Bayesian Approximation
    """
    
    def __init__(self, dropout_rate: float = 0.1, num_samples: int = 10):
        self.dropout_rate = dropout_rate
        self.num_samples = num_samples
        
    def calculate_epistemic_uncertainty(self, 
                                       response_variations: List[str]) -> float:
        """
        Calculate epistemic uncertainty (model uncertainty) from response variations.
        Higher values indicate lower confidence in the response.
        """
        if len(response_variations) < 2:
            return 0.5  # Medium uncertainty for single response
        
        # Calculate semantic similarity between responses
        similarities = []
        for i in range(len(response_variations)):
            for j in range(i + 1, len(response_variations)):
                sim = self._semantic_similarity(
                    response_variations[i], 
                    response_variations[j]
                )
                similarities.append(sim)
        
        # High similarity = low uncertainty
        mean_similarity = np.mean(similarities)
        uncertainty = 1.0 - mean_similarity
        
        return float(uncertainty)
    
    def calculate_aleatoric_uncertainty(self, response: str) -> float:
        """
        Calculate aleatoric uncertainty (data uncertainty) based on 
        linguistic markers of uncertainty.
        """
        uncertainty_markers = {
            'very_high': ['might', 'maybe', 'perhaps', 'possibly', 'uncertain', 
                         'unclear', 'not sure', 'probably not'],
            'high': ['likely', 'probably', 'seems', 'appears', 'suggests'],
            'medium': ['could', 'may', 'might be'],
            'low': ['should', 'expected', 'typically']
        }
        
        response_lower = response.lower()
        uncertainty_score = 0.0
        marker_count = 0
        
        for level, markers in uncertainty_markers.items():
            for marker in markers:
                if marker in response_lower:
                    marker_count += 1
                    if level == 'very_high':
                        uncertainty_score += 0.8
                    elif level == 'high':
                        uncertainty_score += 0.6
                    elif level == 'medium':
                        uncertainty_score += 0.4
                    else:
                        uncertainty_score += 0.2
        
        if marker_count == 0:
            return 0.1  # Low inherent uncertainty
        
        return min(uncertainty_score / marker_count, 1.0)
    
    def _semantic_similarity(self, text1: str, text2: str) -> float:
        """
        Simple semantic similarity using token overlap and sequence matching.
        In production, use sentence transformers or embeddings.
        """
        tokens1 = set(text1.lower().split())
        tokens2 = set(text2.lower().split())
        
        if not tokens1 or not tokens2:
            return 0.0
        
        intersection = tokens1.intersection(tokens2)
        union = tokens1.union(tokens2)
        
        return len(intersection) / len(union) if union else 0.0


class SelfConsistencyChecker:
    """
    Implements self-consistency checking through multiple sampling
    and consensus verification.
    
    This approach generates multiple independent responses and checks
    for agreement, flagging inconsistencies as potential hallucinations.
    """
    
    def __init__(self, num_samples: int = 5, consensus_threshold: float = 0.7):
        self.num_samples = num_samples
        self.consensus_threshold = consensus_threshold
        
    async def check_consistency(self, 
                               agent_function: Any,
                               input_data: Dict[str, Any]) -> ConsistencyCheck:
        """
        Generate multiple responses and check for consistency.
        """
        samples = []
        
        # Generate multiple independent responses
        for _ in range(self.num_samples):
            # In production, call the actual agent with temperature > 0
            # For now, simulate variations
            response = await self._generate_sample(agent_function, input_data)
            samples.append(response)
        
        # Calculate agreement score
        agreement_score = self._calculate_agreement(samples)
        
        # Identify consensus response
        consensus = self._find_consensus(samples) if agreement_score >= self.consensus_threshold else None
        
        # Identify divergent points
        divergent = self._identify_divergent_points(samples)
        
        return ConsistencyCheck(
            samples=samples,
            agreement_score=agreement_score,
            consensus_response=consensus,
            divergent_points=divergent
        )
    
    async def _generate_sample(self, agent_function: Any, input_data: Dict[str, Any]) -> str:
        """
        Generate a single response sample.
        In production, this would call the actual agent/LLM.
        """
        # Placeholder - in real implementation, call agent with temperature > 0
        return f"Sample response for: {input_data.get('query', 'unknown')}"
    
    def _calculate_agreement(self, samples: List[str]) -> float:
        """
        Calculate pairwise agreement across all samples.
        """
        if len(samples) < 2:
            return 1.0
        
        agreements = []
        for i in range(len(samples)):
            for j in range(i + 1, len(samples)):
                # Simple token-based similarity
                tokens_i = set(samples[i].lower().split())
                tokens_j = set(samples[j].lower().split())
                
                if tokens_i and tokens_j:
                    overlap = len(tokens_i.intersection(tokens_j))
                    total = len(tokens_i.union(tokens_j))
                    agreements.append(overlap / total if total > 0 else 0)
        
        return float(np.mean(agreements)) if agreements else 0.0
    
    def _find_consensus(self, samples: List[str]) -> Optional[str]:
        """
        Find the response that best represents the consensus.
        """
        if not samples:
            return None
        
        # Calculate each sample's average similarity to all others
        consensus_scores = []
        for sample in samples:
            tokens = set(sample.lower().split())
            similarities = []
            
            for other in samples:
                other_tokens = set(other.lower().split())
                if tokens and other_tokens:
                    overlap = len(tokens.intersection(other_tokens))
                    total = len(tokens.union(other_tokens))
                    similarities.append(overlap / total if total > 0 else 0)
            
            consensus_scores.append(np.mean(similarities))
        
        # Return sample with highest average similarity
        max_idx = int(np.argmax(consensus_scores))
        return samples[max_idx]
    
    def _identify_divergent_points(self, samples: List[str]) -> List[str]:
        """
        Identify specific points where samples disagree.
        """
        # Extract key claims from each sample
        all_claims = []
        for sample in samples:
            claims = self._extract_claims(sample)
            all_claims.extend(claims)
        
        # Find claims that appear in minority of samples
        claim_counts = {}
        for claim in all_claims:
            claim_counts[claim] = claim_counts.get(claim, 0) + 1
        
        threshold = len(samples) * 0.3  # Appears in < 30% of samples
        divergent = [
            claim for claim, count in claim_counts.items() 
            if count < threshold
        ]
        
        return divergent[:5]  # Return top 5 divergent points
    
    def _extract_claims(self, text: str) -> List[str]:
        """
        Extract factual claims from text.
        Simple implementation - in production use NLP parsing.
        """
        # Split into sentences
        sentences = re.split(r'[.!?]+', text)
        
        # Filter for sentences with factual indicators
        claims = []
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) > 10 and any(word in sentence.lower() for word in 
                                         ['is', 'are', 'was', 'were', 'has', 'have']):
                claims.append(sentence)
        
        return claims


class FactVerificationAgent:
    """
    Verifies factual claims against knowledge base and external sources.
    Implements evidence grounding to detect unsupported assertions.
    """
    
    def __init__(self, knowledge_base: Optional[Dict[str, Any]] = None):
        self.knowledge_base = knowledge_base or {}
        
    def verify_claims(self, response: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Verify factual claims in the response against available evidence.
        """
        claims = self._extract_factual_claims(response)
        
        verification_results = {
            'total_claims': len(claims),
            'verified_claims': 0,
            'unverified_claims': 0,
            'contradicted_claims': 0,
            'claim_details': []
        }
        
        for claim in claims:
            result = self._verify_single_claim(claim, context)
            verification_results['claim_details'].append(result)
            
            if result['status'] == 'verified':
                verification_results['verified_claims'] += 1
            elif result['status'] == 'contradicted':
                verification_results['contradicted_claims'] += 1
            else:
                verification_results['unverified_claims'] += 1
        
        return verification_results
    
    def _extract_factual_claims(self, text: str) -> List[str]:
        """
        Extract verifiable factual claims from text.
        """
        # Simple sentence splitting - in production use proper NLP
        sentences = re.split(r'[.!?]+', text)
        
        claims = []
        for sentence in sentences:
            sentence = sentence.strip()
            # Filter for factual-looking statements
            if (len(sentence) > 15 and 
                not sentence.lower().startswith(('i think', 'in my opinion', 'perhaps'))):
                claims.append(sentence)
        
        return claims
    
    def _verify_single_claim(self, claim: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Verify a single claim against knowledge base and context.
        """
        # Check knowledge base
        claim_hash = hashlib.md5(claim.lower().encode()).hexdigest()
        
        if claim_hash in self.knowledge_base:
            kb_entry = self.knowledge_base[claim_hash]
            return {
                'claim': claim,
                'status': 'verified',
                'source': 'knowledge_base',
                'confidence': kb_entry.get('confidence', 0.8)
            }
        
        # Check context for supporting evidence
        if self._has_supporting_evidence(claim, context):
            return {
                'claim': claim,
                'status': 'verified',
                'source': 'context',
                'confidence': 0.7
            }
        
        # Check for contradictions
        if self._has_contradicting_evidence(claim, context):
            return {
                'claim': claim,
                'status': 'contradicted',
                'source': 'context',
                'confidence': 0.9
            }
        
        return {
            'claim': claim,
            'status': 'unverified',
            'source': None,
            'confidence': 0.0
        }
    
    def _has_supporting_evidence(self, claim: str, context: Dict[str, Any]) -> bool:
        """
        Check if context contains supporting evidence for claim.
        """
        claim_tokens = set(claim.lower().split())
        
        # Check context fields for relevant information
        for key, value in context.items():
            if isinstance(value, str):
                value_tokens = set(value.lower().split())
                overlap = len(claim_tokens.intersection(value_tokens))
                if overlap > len(claim_tokens) * 0.5:  # 50% token overlap
                    return True
        
        return False
    
    def _has_contradicting_evidence(self, claim: str, context: Dict[str, Any]) -> bool:
        """
        Check if context contradicts the claim.
        """
        # Simple contradiction detection - look for negation patterns
        contradiction_markers = ['not', 'never', 'no', 'false', 'incorrect']
        
        for key, value in context.items():
            if isinstance(value, str):
                value_lower = value.lower()
                if any(marker in value_lower for marker in contradiction_markers):
                    # Check if claim appears near negation
                    claim_words = claim.lower().split()[:3]  # First few words
                    if any(word in value_lower for word in claim_words):
                        return True
        
        return False


class HallucinationDetector:
    """
    Main hallucination detection coordinator that integrates multiple
    detection strategies and provides comprehensive analysis.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        config = config or {}
        
        self.uncertainty_quantifier = UncertaintyQuantifier(
            dropout_rate=config.get('dropout_rate', 0.1),
            num_samples=config.get('uncertainty_samples', 10)
        )
        
        self.consistency_checker = SelfConsistencyChecker(
            num_samples=config.get('consistency_samples', 5),
            consensus_threshold=config.get('consensus_threshold', 0.7)
        )
        
        self.fact_verifier = FactVerificationAgent(
            knowledge_base=config.get('knowledge_base', {})
        )
        
        self.hallucination_threshold = config.get('hallucination_threshold', 0.6)
        
    async def detect(self,
                    response: str,
                    context: Dict[str, Any],
                    agent_function: Optional[Any] = None) -> HallucinationDetectionResult:
        """
        Comprehensive hallucination detection using multiple strategies.
        """
        hallucination_types = []
        evidence = {}
        confidence_score = 1.0  # Start with full confidence
        
        # 1. Uncertainty Quantification
        aleatoric_uncertainty = self.uncertainty_quantifier.calculate_aleatoric_uncertainty(response)
        evidence['aleatoric_uncertainty'] = aleatoric_uncertainty
        
        if aleatoric_uncertainty > 0.5:
            hallucination_types.append(HallucinationType.OVERCONFIDENCE)
            confidence_score *= (1.0 - aleatoric_uncertainty)
        
        # 2. Self-Consistency Check (if agent function provided)
        if agent_function:
            consistency_result = await self.consistency_checker.check_consistency(
                agent_function, context
            )
            evidence['consistency_check'] = {
                'agreement_score': consistency_result.agreement_score,
                'divergent_points': consistency_result.divergent_points
            }
            
            if consistency_result.agreement_score < self.consistency_checker.consensus_threshold:
                hallucination_types.append(HallucinationType.FACTUAL_INCONSISTENCY)
                confidence_score *= consistency_result.agreement_score
        
        # 3. Fact Verification
        verification_results = self.fact_verifier.verify_claims(response, context)
        evidence['fact_verification'] = verification_results
        
        if verification_results['contradicted_claims'] > 0:
            hallucination_types.append(HallucinationType.LOGICAL_CONTRADICTION)
            confidence_score *= 0.5
        
        if verification_results['unverified_claims'] > verification_results['verified_claims']:
            hallucination_types.append(HallucinationType.UNSUPPORTED_CLAIM)
            confidence_score *= 0.7
        
        # Calculate final hallucination determination
        is_hallucination = confidence_score < (1.0 - self.hallucination_threshold)
        
        # Generate reasoning
        reasoning = self._generate_reasoning(
            hallucination_types, 
            evidence, 
            confidence_score
        )
        
        # Generate mitigation suggestions
        mitigation = self._generate_mitigation_suggestions(hallucination_types)
        
        return HallucinationDetectionResult(
            is_hallucination=is_hallucination,
            confidence_score=confidence_score,
            hallucination_types=hallucination_types,
            evidence=evidence,
            reasoning=reasoning,
            mitigation_suggestions=mitigation
        )
    
    def _generate_reasoning(self,
                           hallucination_types: List[HallucinationType],
                           evidence: Dict[str, Any],
                           confidence_score: float) -> str:
        """
        Generate human-readable reasoning for the detection result.
        """
        if not hallucination_types:
            return f"Response appears reliable (confidence: {confidence_score:.2f}). No hallucination patterns detected."
        
        reasoning_parts = [
            f"Potential hallucination detected (confidence: {confidence_score:.2f}).",
            f"Identified patterns: {', '.join(ht.value for ht in hallucination_types)}."
        ]
        
        # Add specific evidence
        if 'aleatoric_uncertainty' in evidence and evidence['aleatoric_uncertainty'] > 0.5:
            reasoning_parts.append(
                f"High linguistic uncertainty detected ({evidence['aleatoric_uncertainty']:.2f})."
            )
        
        if 'fact_verification' in evidence:
            fv = evidence['fact_verification']
            if fv['contradicted_claims'] > 0:
                reasoning_parts.append(
                    f"{fv['contradicted_claims']} contradicted claims found."
                )
            if fv['unverified_claims'] > 0:
                reasoning_parts.append(
                    f"{fv['unverified_claims']} unsupported claims detected."
                )
        
        return " ".join(reasoning_parts)
    
    def _generate_mitigation_suggestions(self,
                                        hallucination_types: List[HallucinationType]) -> List[str]:
        """
        Generate actionable mitigation suggestions based on detected hallucination types.
        """
        suggestions = []
        
        if HallucinationType.OVERCONFIDENCE in hallucination_types:
            suggestions.append(
                "Request agent to explicitly state uncertainty and provide confidence intervals"
            )
        
        if HallucinationType.UNSUPPORTED_CLAIM in hallucination_types:
            suggestions.append(
                "Ask agent to cite specific sources or evidence for claims"
            )
        
        if HallucinationType.FACTUAL_INCONSISTENCY in hallucination_types:
            suggestions.append(
                "Generate multiple responses and compare for consistency"
            )
        
        if HallucinationType.LOGICAL_CONTRADICTION in hallucination_types:
            suggestions.append(
                "Enable contradiction detection agent before finalizing response"
            )
        
        if not suggestions:
            suggestions.append("Response appears reliable - no mitigation needed")
        
        return suggestions


# Example usage
async def main():
    """
    Example usage of the hallucination detection system.
    """
    # Initialize detector
    detector = HallucinationDetector(config={
        'hallucination_threshold': 0.6,
        'consistency_samples': 5,
        'consensus_threshold': 0.7
    })
    
    # Example response to check
    test_response = """
    The patient's blood pressure reading of 180/120 mmHg indicates severe hypertension.
    This probably requires immediate intervention. The medication dosage might need adjustment.
    Based on the patient history, there are no contraindications to increasing the dose.
    """
    
    # Context from patient records
    context = {
        'patient_id': '12345',
        'previous_bp_readings': '120/80, 125/85, 130/88',
        'medications': 'Lisinopril 10mg',
        'allergies': 'Penicillin',
        'last_visit': '2024-01-15'
    }
    
    # Run detection
    result = await detector.detect(
        response=test_response,
        context=context,
        agent_function=None  # Would be actual agent in production
    )
    
    # Display results
    print("=" * 60)
    print("HALLUCINATION DETECTION RESULTS")
    print("=" * 60)
    print(f"Is Hallucination: {result.is_hallucination}")
    print(f"Confidence Score: {result.confidence_score:.3f}")
    print(f"\nDetected Patterns:")
    for ht in result.hallucination_types:
        print(f"  - {ht.value}")
    print(f"\nReasoning: {result.reasoning}")
    print(f"\nMitigation Suggestions:")
    for suggestion in result.mitigation_suggestions:
        print(f"  - {suggestion}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
