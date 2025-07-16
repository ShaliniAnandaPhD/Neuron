import weave
import openai
import anthropic
import base64
import time
from typing import Dict, Any
from config.config import Config

@weave.op()
class VisionModelInterface:
    def __init__(self):
        self.openai_client = openai.OpenAI(api_key=Config.OPENAI_API_KEY)
        self.anthropic_client = anthropic.Anthropic(api_key=Config.ANTHROPIC_API_KEY)
    
    @weave.op()
    async def analyze_with_gpt4v(self, image_data: bytes, prompt: str) -> Dict[str, Any]:
        """Analyze image with GPT-4V"""
        start_time = time.time()
        
        # Convert image to base64
        image_b64 = base64.b64encode(image_data).decode('utf-8')
        
        response = self.openai_client.chat.completions.create(
            model="gpt-4-vision-preview",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}
                        }
                    ]
                }
            ],
            max_tokens=500
        )
        
        processing_time = time.time() - start_time
        
        # Parse response for damage assessment
        content = response.choices[0].message.content
        
        return {
            'assessment': self._parse_damage_assessment(content),
            'confidence': self._extract_confidence(content),
            'raw_response': content,
            'processing_time': processing_time,
            'model': 'gpt-4-vision-preview'
        }
    
    @weave.op()
    async def analyze_with_claude3v(self, image_data: bytes, prompt: str) -> Dict[str, Any]:
        """Analyze image with Claude-3V"""
        start_time = time.time()
        
        # Convert image to base64
        image_b64 = base64.b64encode(image_data).decode('utf-8')
        
        message = self.anthropic_client.messages.create(
            model="claude-3-sonnet-20240229",
            max_tokens=500,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
                                "data": image_b64
                            }
                        },
                        {"type": "text", "text": prompt}
                    ]
                }
            ]
        )
        
        processing_time = time.time() - start_time
        content = message.content[0].text
        
        return {
            'assessment': self._parse_damage_assessment(content),
            'confidence': self._extract_confidence(content),
            'raw_response': content,
            'processing_time': processing_time,
            'model': 'claude-3-sonnet-20240229'
        }
    
    def _parse_damage_assessment(self, content: str) -> Dict[str, Any]:
        """Parse damage assessment from model response"""
        # Simple parsing - in production, use more sophisticated NLP
        damage_keywords = {
            'none': 0, 'minimal': 2, 'minor': 3, 'moderate': 5, 
            'significant': 7, 'severe': 8, 'total': 10
        }
        
        content_lower = content.lower()
        severity = 0
        
        for keyword, score in damage_keywords.items():
            if keyword in content_lower:
                severity = max(severity, score)
        
        return {
            'severity': severity,
            'description': content[:200],  # First 200 chars
            'keywords_found': [k for k in damage_keywords.keys() if k in content_lower]
        }
    
    def _extract_confidence(self, content: str) -> float:
        """Extract confidence score from response"""
        # Look for confidence indicators in response
        import re
        
        # Look for percentage patterns
        pct_match = re.search(r'(\d+)%', content)
        if pct_match:
            return float(pct_match.group(1)) / 100
        
        # Look for confidence words
        confidence_words = {
            'certain': 0.95, 'confident': 0.9, 'likely': 0.8,
            'probable': 0.7, 'possible': 0.6, 'uncertain': 0.4
        }
        
        content_lower = content.lower()
        for word, score in confidence_words.items():
            if word in content_lower:
                return score
        
        return 0.75  # Default confidence