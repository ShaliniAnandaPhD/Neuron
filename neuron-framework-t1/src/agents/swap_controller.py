import weave
import time
import asyncio
from src.core.base_agent import BaseAgent, Message
from src.models.vision_models import VisionModelInterface
from typing import Dict, Any
from config.config import Config

@weave.op()
class SwapController(BaseAgent):
    """Manages model swapping and validation"""
    
    def __init__(self, agent_id: str = "swap_controller_001"):
        super().__init__(agent_id)
        self.swap_timeout = Config.SWAP_TIMEOUT
        self.accuracy_tolerance = Config.ACCURACY_TOLERANCE
        self.vision_models = VisionModelInterface()
    
    @weave.op()
    async def execute_swap(self, message: Message) -> Message:
        """Execute model swap and validate results"""
        swap_data = message.payload
        swap_start = time.time()
        
        try:
            # Execute fallback model with timeout
            fallback_result = await asyncio.wait_for(
                self._analyze_with_fallback(swap_data),
                timeout=self.swap_timeout
            )
            
            swap_duration = time.time() - swap_start
            
            # Validate swap results
            is_valid = self._validate_swap_results(
                swap_data['primary_result'],
                fallback_result,
                swap_data['text_result']
            )
            
            accuracy_preserved = self._check_accuracy_preservation(
                swap_data['primary_result'], fallback_result
            )
            
            # Log swap execution to Weave
            weave.log({
                'event': 'model_swap_executed',
                'claim_id': swap_data['claim_data']['claim_id'],
                'swap_duration': swap_duration,
                'primary_model': swap_data['primary_result']['model'],
                'fallback_model': swap_data['fallback_model'],
                'swap_valid': is_valid,
                'accuracy_preserved': accuracy_preserved,
                'swap_completed_timestamp': time.time()
            })
            
            return self._create_swap_response(
                swap_data, fallback_result, swap_duration, is_valid
            )
            
        except asyncio.TimeoutError:
            return await self._handle_swap_timeout(swap_data)
        except Exception as e:
            return await self._handle_swap_failure(swap_data, str(e))
    
    @weave.op()
    async def _analyze_with_fallback(self, swap_data: Dict) -> Dict[str, Any]:
        """Analyze with fallback vision model"""
        prompt = """Analyze this vehicle for damage. Provide:
        1. Damage severity (0-10 scale)
        2. Your confidence level
        3. Brief description of damage observed
        
        Be specific about damage severity and confidence."""
        
        image_data = swap_data['claim_data']['image_data']
        
        if 'claude' in swap_data['fallback_model'].lower():
            return await self.vision_models.analyze_with_claude3v(image_data, prompt)
        else:
            return await self.vision_models.analyze_with_gpt4v(image_data, prompt)
    
    def _validate_swap_results(self, primary: Dict, fallback: Dict, text: Dict) -> bool:
        """Validate that swap resolved the conflict"""
        # Calculate deltas
        primary_delta = abs(primary['assessment']['severity'] - text['severity_score']) / 10.0
        fallback_delta = abs(fallback['assessment']['severity'] - text['severity_score']) / 10.0
        
        # Swap is valid if fallback has lower conflict
        return fallback_delta < primary_delta
    
    def _check_accuracy_preservation(self, primary: Dict, fallback: Dict) -> bool:
        """Check if accuracy is preserved within tolerance"""
        primary_conf = primary.get('confidence', 0)
        fallback_conf = fallback.get('confidence', 0)
        
        accuracy_delta = abs(primary_conf - fallback_conf)
        return accuracy_delta <= self.accuracy_tolerance
    
    def _create_swap_response(self, swap_data: Dict, fallback_result: Dict, 
                            swap_duration: float, is_valid: bool) -> Message:
        """Create final response after swap"""
        return Message(
            type="analysis_complete",
            payload={
                'claim_id': swap_data['claim_data']['claim_id'],
                'analysis_result': {
                    'primary_analysis': swap_data['primary_result'],
                    'fallback_analysis': fallback_result,
                    'text_analysis': swap_data['text_result'],
                    'final_recommendation': fallback_result if is_valid else swap_data['primary_result'],
                    'conflict_detected': True,
                    'swap_executed': True,
                    'swap_duration': swap_duration,
                    'swap_valid': is_valid,
                    'accuracy_preserved': self._check_accuracy_preservation(
                        swap_data['primary_result'], fallback_result
                    )
                },
                'metadata': {
                    'processing_complete': True,
                    'models_used': [
                        swap_data['primary_result']['model'],
                        fallback_result['model']
                    ],
                    'confidence_improved': is_valid
                }
            },
            source=self.agent_id,
            target="result_processor"
        )
    
    async def _handle_swap_timeout(self, swap_data: Dict) -> Message:
        """Handle swap timeout"""
        weave.log({
            'event': 'swap_timeout',
            'claim_id': swap_data['claim_data']['claim_id'],
            'timeout_duration': self.swap_timeout
        })
        
        # Return primary result on timeout
        return self._create_swap_response(
            swap_data, swap_data['primary_result'], self.swap_timeout, False
        )
    
    async def _handle_swap_failure(self, swap_data: Dict, error: str) -> Message:
        """Handle swap failure"""
        weave.log({
            'event': 'swap_failure',
            'claim_id': swap_data['claim_data']['claim_id'],
            'error': error
        })
        
        # Return primary result on failure
        return self._create_swap_response(
            swap_data, swap_data['primary_result'], 0, False
        )