import weave
import asyncio
import time
from src.core.base_agent import BaseAgent, Message
from src.models.vision_models import VisionModelInterface
from typing import Dict, Any
from config.config import Config

@weave.op()
class ConflictDetector(BaseAgent):
    """Detects conflicts between vision and text analysis"""
    
    def __init__(self, agent_id: str = "conflict_detector_001"):
        super().__init__(agent_id)
        self.confidence_threshold = Config.CONFIDENCE_THRESHOLD
        self.vision_models = VisionModelInterface()
    
    @weave.op()
    async def analyze_claim(self, message: Message) -> Message:
        """Analyze claim and detect conflicts"""
        claim_data = message.payload
        analysis_start = time.time()
        
        # Parallel analysis
        vision_task = self._analyze_visual_evidence(claim_data['image_data'])
        text_task = self._analyze_text_description(claim_data['damage_description'])
        
        vision_result, text_result = await asyncio.gather(vision_task, text_task)
        
        # Calculate confidence delta
        confidence_delta = self._calculate_confidence_delta(vision_result, text_result)
        
        analysis_duration = time.time() - analysis_start
        
        # Log analysis to Weave
        weave.log({
            'event': 'conflict_analysis',
            'claim_id': claim_data['claim_id'],
            'vision_confidence': vision_result['confidence'],
            'text_severity': text_result['severity_score'],
            'confidence_delta': confidence_delta,
            'threshold': self.confidence_threshold,
            'conflict_detected': confidence_delta > self.confidence_threshold,
            'analysis_duration': analysis_duration,
            'conflict_detected_timestamp': time.time()
        })
        
        # Check if swap needed
        if confidence_delta > self.confidence_threshold:
            return self._create_swap_request(claim_data, vision_result, text_result)
        
        # No conflict - return analysis
        return self._create_analysis_response(claim_data, vision_result, text_result, swapped=False)
    
    @weave.op()
    async def _analyze_visual_evidence(self, image_data: bytes) -> Dict[str, Any]:
        """Analyze image using primary vision model"""
        prompt = """Analyze this vehicle for damage. Provide:
        1. Damage severity (0-10 scale)
        2. Your confidence level
        3. Brief description of damage observed
        
        Be specific about damage severity and confidence."""
        
        return await self.vision_models.analyze_with_gpt4v(image_data, prompt)
    
    @weave.op()
    async def _analyze_text_description(self, description: str) -> Dict[str, Any]:
        """Extract damage indicators from text"""
        damage_indicators = self._extract_damage_keywords(description)
        severity_score = self._calculate_text_severity(damage_indicators)
        
        return {
            'damage_indicators': damage_indicators,
            'severity_score': severity_score,
            'confidence': min(0.9, len(damage_indicators) * 0.2 + 0.5),
            'text_analysis': description
        }
    
    def _extract_damage_keywords(self, text: str) -> list:
        """Extract damage-related keywords"""
        damage_keywords = [
            'total loss', 'severe', 'significant', 'major', 'critical',
            'minor', 'slight', 'minimal', 'cosmetic', 'pristine',
            'undamaged', 'perfect', 'excellent'
        ]
        
        text_lower = text.lower()
        return [keyword for keyword in damage_keywords if keyword in text_lower]
    
    def _calculate_text_severity(self, indicators: list) -> float:
        """Calculate severity from text indicators"""
        severity_map = {
            'pristine': 0, 'undamaged': 0, 'perfect': 0, 'excellent': 0,
            'minimal': 2, 'slight': 2, 'cosmetic': 2, 'minor': 3,
            'moderate': 5, 'significant': 7, 'major': 8, 'severe': 9, 
            'critical': 9, 'total loss': 10
        }
        
        max_severity = 0
        for indicator in indicators:
            if indicator in severity_map:
                max_severity = max(max_severity, severity_map[indicator])
        
        return max_severity
    
    def _calculate_confidence_delta(self, vision_result: Dict, text_result: Dict) -> float:
        """Calculate confidence delta between analyses"""
        vision_severity = vision_result['assessment']['severity']
        text_severity = text_result['severity_score']
        
        # Normalize to 0-1 scale
        normalized_vision = vision_severity / 10.0
        normalized_text = text_severity / 10.0
        
        return abs(normalized_vision - normalized_text)
    
    def _create_swap_request(self, claim_data: Dict, vision_result: Dict, text_result: Dict) -> Message:
        """Create swap request message"""
        return Message(
            type="model_swap_request",
            payload={
                'claim_data': claim_data,
                'primary_result': vision_result,
                'text_result': text_result,
                'fallback_model': Config.FALLBACK_VISION_MODEL,
                'swap_reason': 'confidence_conflict',
                'swap_triggered_timestamp': time.time()
            },
            source=self.agent_id,
            target="swap_controller"
        )
    
    def _create_analysis_response(self, claim_data: Dict, vision_result: Dict, text_result: Dict, swapped: bool) -> Message:
        """Create final analysis response"""
        return Message(
            type="analysis_complete",
            payload={
                'claim_id': claim_data['claim_id'],
                'analysis_result': {
                    'vision_analysis': vision_result,
                    'text_analysis': text_result,
                    'conflict_detected': False,
                    'swap_executed': swapped,
                    'final_recommendation': vision_result
                }
            },
            source=self.agent_id,
            target="result_processor"
        )