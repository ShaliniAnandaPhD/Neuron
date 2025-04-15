import unittest
import asyncio
from ..ambiguity_resolver import ToneAgent

class TestToneAgent(unittest.TestCase):
    def setUp(self):
        self.agent = ToneAgent(name="Test Tone Agent")
    
    def test_politeness_detection(self):
        # Set up asyncio event loop for testing
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Test polite query
        polite_query = "Just wondering if someone could help me with my account issue."
        tone_analysis = loop.run_until_complete(self.agent._analyze_tone(polite_query))
        
        # Assertions
        self.assertGreater(tone_analysis["politeness_score"], 0.6)
        self.assertTrue(any(category["category"] == "hedges" for category in tone_analysis["detected_patterns"]["politeness"]))
        
        # Test direct query
        direct_query = "Fix my account now."
        tone_analysis = loop.run_until_complete(self.agent._analyze_tone(direct_query))
        
        # Assertions
        self.assertLess(tone_analysis["politeness_score"], 0.3)
        self.assertGreater(tone_analysis["urgency_score"], 0.3)
        
        # Clean up
        loop.close()
    
    def test_urgency_detection(self):
        # Set up asyncio event loop for testing
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Test urgent query
        urgent_query = "I need this fixed immediately. It's extremely urgent."
        tone_analysis = loop.run_until_complete(self.agent._analyze_tone(urgent_query))
        
        # Assertions
        self.assertGreater(tone_analysis["urgency_score"], 0.7)
        self.assertTrue(any(category["category"] == "time_constraints" for category in tone_analysis["detected_patterns"]["urgency"]))
        
        # Test non-urgent query
        non_urgent_query = "When you have some time, could you look at this issue?"
        tone_analysis = loop.run_until_complete(self.agent._analyze_tone(non_urgent_query))
        
        # Assertions
        self.assertLess(tone_analysis["urgency_score"], 0.4)
        
        # Clean up
        loop.close()
    
    def test_tone_masking_detection(self):
        # Set up asyncio event loop for testing
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Test masked urgency
        masked_query = "Sorry to bother you, but I can't access my account and I have a presentation in an hour."
        tone_analysis = loop.run_until_complete(self.agent._analyze_tone(masked_query))
        
        # Assertions
        self.assertTrue(tone_analysis["tone_masking_detected"])
        self.assertGreater(tone_analysis["politeness_score"], 0.5)
        self.assertGreater(tone_analysis["urgency_score"], 0.3)
        
        # Clean up
        loop.close()
