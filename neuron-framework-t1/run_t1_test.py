#!/usr/bin/env python3
import asyncio
from src import tracing as weave
from tests.test_t1_system import T1SystemTest, generate_test_cases
from config.config import Config

async def main():
    # Initialize Weave
    weave.init(Config.WEAVE_PROJECT)
    
    print("🚀 Starting T1 Hot-Swap Test...")
    print(f"📊 Weave Project: {Config.WEAVE_PROJECT}")
    print()
    
    # Create test system
    test_system = T1SystemTest()
    test_cases = generate_test_cases()
    
    print(f"🧪 Running {len(test_cases)} test cases...")
    
    # Run tests
    results = []
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📊 Running Test {i}/{len(test_cases)}: {test_case['description']}")
        
        try:
            result = await test_system.run_complete_test(test_case)
            results.append(result)
            
            # Print results
            success_icon = "✅" if result['success'] else "❌"
            print(f"{success_icon} Success: {result['success']}")
            print(f"📈 Metrics:")
            for metric, value in result['metrics'].items():
                print(f"   {metric}: {value}")
            
            print(f"📋 Success Criteria:")
            for criterion, passed in result['success_criteria'].items():
                status = "✅" if passed else "❌"
                print(f"   {status} {criterion}: {passed}")
            
        except Exception as e:
            print(f"❌ Test failed: {e}")
            results.append({
                'test_case_id': test_case['id'],
                'success': False,
                'error': str(e)
            })
    
    # Summary
    passed = sum(1 for r in results if r.get('success', False))
    total = len(results)
    
    print(f"\n🎯 T1 Test Summary:")
    print(f"   Total Tests: {total}")
    print(f"   Passed: {passed}")
    print(f"   Failed: {total - passed}")
    print(f"   Success Rate: {passed/total*100:.1f}%")
    
    # Detailed results for failed tests
    failed_tests = [r for r in results if not r.get('success', False)]
    if failed_tests:
        print(f"\n❌ Failed Tests:")
        for test in failed_tests:
            print(f"   - {test['test_case_id']}: {test.get('error', 'Unknown error')}")
    
    # T1 Success Criteria Summary
    print(f"\n📊 T1 Success Criteria Analysis:")
    if results:
        criteria_summary = {}
        for result in results:
            if 'success_criteria' in result:
                for criterion, passed in result['success_criteria'].items():
                    if criterion not in criteria_summary:
                        criteria_summary[criterion] = {'passed': 0, 'total': 0}
                    criteria_summary[criterion]['total'] += 1
                    if passed:
                        criteria_summary[criterion]['passed'] += 1
        
        for criterion, stats in criteria_summary.items():
            rate = stats['passed'] / stats['total'] * 100
            status = "✅" if rate == 100 else "⚠️" if rate >= 80 else "❌"
            print(f"   {status} {criterion}: {stats['passed']}/{stats['total']} ({rate:.1f}%)")
    
    # Log final summary to Weave
    weave.log({
        'final_summary': {
            'total_tests': total,
            'passed_tests': passed,
            'success_rate': passed/total,
            'all_results': results,
            'criteria_analysis': criteria_summary if 'criteria_summary' in locals() else {}
        }
    })
    
    print(f"\n📊 View detailed results in Weave dashboard")
    print(f"🔗 Project: {Config.WEAVE_PROJECT}")
    
    # Return success status
    return passed == total

if __name__ == "__main__":
    success = asyncio.run(main())
    if success:
        print("\n🎉 All T1 tests passed! System ready for production validation.")
        exit(0)
    else:
        print("\n⚠️ Some T1 tests failed. Review results and fix issues.")
        exit(1)