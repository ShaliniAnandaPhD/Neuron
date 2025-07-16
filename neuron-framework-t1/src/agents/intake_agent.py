import weave
from src.core.base_agent import BaseAgent, Message
from typing import Dict, Any

@weave.op()
class IntakeAgent(BaseAgent):
    """Processes incoming insurance claims"""
    
    def __init__(self, agent_id: str = "intake_001"):
        super().__init__(agent_id)
        self.supported_formats = ['image/jpeg', 'image/png', 'text/plain']
    
    @weave.op()
    async def process_claim(self, claim_data: Dict[str, Any]) -> Message:
        """Process incoming insurance claim"""
        
        # Validate input
        if not self._validate_claim_format(claim_data):
            raise ValueError("Invalid claim format")
        
        # Log intake to Weave
        weave.log({
            'event': 'claim_intake',
            'claim_id': claim_data['claim_id'],
            'agent': self.agent_id,
            'timestamp': self.get_timestamp()
        })
        
        # Create message for conflict detector
        message = Message(
            type="vision_analysis_request",
            payload={
                'claim_id': claim_data['claim_id'],
                'image_data': claim_data['visual_evidence'],
                'damage_description': claim_data['text_description'],
                'priority': self._determine_priority(claim_data),
                'intake_timestamp': self.get_timestamp()
            },
            source=self.agent_id,
            target="conflict_detector"
        )
        
        return message
    
    def _validate_claim_format(self, claim_data: Dict[str, Any]) -> bool:
        required_fields = ['claim_id', 'visual_evidence', 'text_description']
        return all(field in claim_data for field in required_fields)
    
    def _determine_priority(self, claim_data: Dict[str, Any]) -> str:
        damage_keywords = ['total loss', 'severe', 'critical']
        description = claim_data.get('text_description', '').lower()
        
        if any(keyword in description for keyword in damage_keywords):
            return 'high'
        return 'normal'