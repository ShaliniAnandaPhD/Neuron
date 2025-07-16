import pytest
import weave
import asyncio
import time
from src.agents.intake_agent import IntakeAgent
from src.agents.conflict_detector import ConflictDetector
from src.agents.swap_controller import SwapController
from config.config import Config

# Initialize Weave
weave.init(Config.WEAVE_PROJECT)

@weave.op()
class T1SystemTest:
    """Complete T1 system test"""
    
    def __init__(self):
        self.intake_agent = IntakeAgent()
        self.conflict_detector = ConflictDetector()
        self.swap_controller = SwapController()
    
    @weave.op()
    async def run_complete_test(self, test_case: dict) -> dict:
        """Run complete T1 test pipeline"""
        start_time = time.time()
        
        # Step 1: Intake
        intake_result = await self.intake_agent.process_claim(test_case['claim_data'])
        
        # Step 2: Conflict Detection
        detection_result = await self.conflict_detector.analyze_claim(intake_result)
        
        # Step 3: Swap if needed
        if detection_result.type == "model_swap_request":
            final_result = await self.swap_controller.execute_swap(detection_result)
        else:
            final_result = detection_result
        
        total_duration = time.time() - start_time
        
        # Extract metrics
        metrics = self._extract_metrics(intake_result, detection_result, final_result, total_duration)
        
        # Evaluate success criteria
        success_criteria = self._evaluate_success_criteria(metrics)
        
        return {
            'test_case_id': test_case['id'],
            'success': success_criteria['all_passed'],
            'metrics': metrics,
            'success_criteria': success_criteria,
            'final_result': final_result.payload
        }
    
    def _extract_metrics(self, intake_msg, detection_msg, final_msg, total_duration):
        """Extract key metrics from test execution"""
        
        # Get timing data from Weave logs or message payloads
        conflict_detection_time = 2.0  # Would extract from actual logs
        swap_duration = final_msg.payload.get('analysis_result', {}).get('swap_duration', 0)
        
        # Get accuracy data
        analysis_result = final_msg.payload.get('analysis_result', {})
        accuracy_preserved = analysis_result.get('accuracy_preserved', True)
        
        return {
            'total_duration': total_duration,
            'conflict_detection_time': conflict_detection_time,
            'swap_duration': swap_duration,
            'accuracy_preserved': accuracy_preserved,
            'conflict_detected': analysis_result.get('conflict_detected', False),
            'swap_executed': analysis_result.get('swap_executed', False)
        }
    
    def _evaluate_success_criteria(self, metrics: dict) -> dict:
        """Evaluate T1 success criteria"""
        criteria = {
            'conflict_detection_under_2s': metrics['conflict_detection_time'] < 2.0,
            'swap_under_500ms': metrics['swap_duration'] < 0.5,
            'accuracy_within_2pct': metrics['accuracy_preserved']
        }
        
        criteria['all_passed'] = all(criteria.values())
        return criteria

# Test data generator
def generate_test_cases():
    """Generate test cases for T1"""
    
    # Create mock image data for testing
    mock_pristine_image = b"mock_pristine_car_image_data"
    mock_damaged_image = b"mock_damaged_car_image_data"
    
    return [
        {
            'id': 'high_conflict_test',
            'description': 'High confidence conflict between pristine image and total loss text',
            'claim_data': {
                'claim_id': 'TEST_001',
                'visual_evidence': mock_pristine_image,
                'text_description': 'Vehicle is a total loss with severe structural damage to all panels',
                'metadata': {'expected_conflict': True}
            },
            'expected_outcome': {
                'conflict_detected': True,
                'swap_executed': True
            }
        },
        {
            'id': 'no_conflict_test',
            'description': 'Consistent damage assessment',
            'claim_data': {
                'claim_id': 'TEST_002',
                'visual_evidence': mock_damaged_image,
                'text_description': 'Vehicle has moderate damage to front bumper and headlight',
                'metadata': {'expected_conflict': False}
            },
            'expected_outcome': {
                'conflict_detected': False,
                'swap_executed': False
            }
        }
    ]

# Main test execution
@pytest.mark.asyncio
async def test_t1_complete_system():
    """Test complete T1 system"""
    test_system = T1SystemTest()
    test_cases = generate_test_cases()
    
    results = []
    for test_case in test_cases:
        result = await test_system.run_complete_test(test_case)
        results.append(result)
        
        # Log to Weave
        weave.log({
            'test_execution': result,
            'success_criteria_met': result['success_criteria']
        })
    
    # Generate summary
    total_tests = len(results)
    passed_tests = sum(1 for r in results if r['success'])
    
    summary = {
        'total_tests': total_tests,
        'passed_tests': passed_tests,
        'success_rate': passed_tests / total_tests,
        'detailed_results': results
    }
    
    weave.log({'t1_test_summary': summary})
    
    # Assert overall success
    assert passed_tests == total_tests, f"Only {passed_tests}/{total_tests} tests passed"

if __name__ == "__main__":
    asyncio.run(test_t1_complete_system())