import unittest
import asyncio
from ..ambiguity_resolver import AmbiguityResolverMicroservice

class TestAmbiguityResolver(unittest.TestCase):
    def setUp(self):
        self.resolver = AmbiguityResolverMicroservice(
            name="Test Ambiguity Resolver",
            description="Testing ambiguity resolution"
        )
        self.resolver.deploy()
    
    def test_end_to_end(self):
        # Set up asyncio event loop for testing
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Test queries
        test_queries = [
            {
                "query": "Just wondering if someone could help with my account issue.",
                "expected_intent": "account_issue",
                "expected_urgency_level": "medium"
            },
            {
                "query": "My password isn't working and I need to log in right now.",
                "expected_intent": "account_issue",
                "expected_urgency_level": "high"
            }
        ]
        
        for test_case in test_queries:
            result = loop.run_until_complete(self.resolver.resolve_ambiguity(test_case["query"]))
            
            # Assertions
            self.assertEqual(result["resolution"]["resolved_intent"], test_case["expected_intent"])
            self.assertEqual(result["resolution"]["resolved_urgency_level"], test_case["expected_urgency_level"])
        
        # Clean up
        loop.close()
    
    def test_polite_masking_detection(self):
        # Set up asyncio event loop for testing
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Test query with polite tone masking urgency
        query = "I'm sorry to bother you, but I was just wondering if someone might be able to look at my account when they have time. I have an important client meeting in 20 minutes."
        
        result = loop.run_until_complete(self.resolver.resolve_ambiguity(query))
        
        # Assertions
        self.assertTrue(result["resolution"]["tone_masking_detected"])
        self.assertTrue(result["resolution"]["urgency_mismatch_detected"])
        self.assertGreaterEqual(result["resolution"]["resolved_urgency_score"], 0.5)
        
        # Clean up
        loop.close()
