#!/usr/bin/env python3
"""
System Test Script for LLaMA3 Neuron Framework
Tests the complete system with various scenarios
"""

import asyncio
import httpx
import json
import time
from typing import Dict, Any, List
import argparse

# Test configuration
DEFAULT_API_URL = "http://localhost:8000"
DEFAULT_API_KEY = "your-api-key"

# Test data
TEST_REQUESTS = [
    {
        "name": "Simple Analysis",
        "request": {
            "content": "Analyze the impact of artificial intelligence on healthcare, focusing on diagnostic accuracy, treatment planning, and patient outcomes.",
            "content_type": "text",
            "pattern": "sequential",
            "priority": "high"
        }
    },
    {
        "name": "Complex Report",
        "request": {
            "content": """
            Create a comprehensive analysis of the following quarterly business metrics:
            - Revenue: $2.5M (up 15% YoY)
            - Customer acquisition: 1,200 new customers (up 25% YoY)
            - Churn rate: 5.2% (down from 6.8%)
            - NPS score: 72 (up from 68)
            
            Identify trends, risks, and provide strategic recommendations.
            """,
            "content_type": "text",
            "pattern": "parallel",
            "priority": "medium"
        }
    },
    {
        "name": "Adaptive Processing",
        "request": {
            "content": "What are the key considerations for implementing a microservices architecture?",
            "content_type": "text",
            "pattern": "adaptive",
            "priority": "low"
        }
    }
]

class SystemTester:
    """System test runner"""
    
    def __init__(self, api_url: str, api_key: str):
        self.api_url = api_url
        self.api_key = api_key
        self.headers = {"X-API-Key": api_key}
        self.results = []
    
    async def test_health_check(self) -> bool:
        """Test health check endpoint"""
        print("\n🏥 Testing Health Check...")
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(f"{self.api_url}/health")
                data = response.json()
                
                print(f"  Status: {data['status']}")
                print(f"  Components:")
                for component, status in data.get("components", {}).items():
                    print(f"    - {component}: {status}")
                
                return response.status_code == 200
                
            except Exception as e:
                print(f"  ❌ Health check failed: {e}")
                return False
    
    async def test_agent_status(self) -> bool:
        """Test agent status endpoint"""
        print("\n🤖 Testing Agent Status...")
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.api_url}/api/v1/agents/status",
                    headers=self.headers
                )
                
                if response.status_code != 200:
                    print(f"  ❌ Failed with status {response.status_code}")
                    return False
                
                agents = response.json()
                print(f"  Found {len(agents)} agents:")
                
                for agent_id, status in agents.items():
                    print(f"    - {agent_id}: {status['status']} "
                          f"(processed: {status['processed_tasks']}, "
                          f"failed: {status['failed_tasks']})")
                
                return True
                
            except Exception as e:
                print(f"  ❌ Agent status check failed: {e}")
                return False
    
    async def test_processing(self, test_case: Dict[str, Any]) -> bool:
        """Test content processing"""
        name = test_case["name"]
        request = test_case["request"]
        
        print(f"\n📝 Testing: {name}")
        print(f"  Pattern: {request.get('pattern', 'default')}")
        print(f"  Priority: {request.get('priority', 'medium')}")
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                start_time = time.time()
                
                # Send processing request
                response = await client.post(
                    f"{self.api_url}/api/v1/process",
                    json=request,
                    headers=self.headers
                )
                
                if response.status_code != 200:
                    print(f"  ❌ Failed with status {response.status_code}")
                    print(f"  Response: {response.text}")
                    return False
                
                data = response.json()
                processing_time = time.time() - start_time
                
                # Store result
                self.results.append({
                    "test": name,
                    "status": data["status"],
                    "processing_time": processing_time,
                    "response_time_ms": data["processing_time_ms"],
                    "pattern_used": data["pattern_used"],
                    "agents_involved": data["agents_involved"]
                })
                
                # Display results
                print(f"  ✅ Status: {data['status']}")
                print(f"  Processing time: {processing_time:.2f}s")
                print(f"  Pattern used: {data['pattern_used']}")
                print(f"  Agents involved: {', '.join(data['agents_involved'])}")
                
                if data.get("result"):
                    print(f"  Result preview: {str(data['result'])[:200]}...")
                
                return data["status"] == "completed"
                
            except Exception as e:
                print(f"  ❌ Processing test failed: {e}")
                return False
    
    async def test_batch_processing(self) -> bool:
        """Test batch processing"""
        print("\n📦 Testing Batch Processing...")
        
        batch_request = {
            "requests": [
                {
                    "content": f"Test request {i}: Summarize the benefits of cloud computing.",
                    "content_type": "text",
                    "priority": "batch"
                }
                for i in range(3)
            ],
            "pattern": "parallel",
            "priority": "batch"
        }
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
                start_time = time.time()
                
                response = await client.post(
                    f"{self.api_url}/api/v1/batch",
                    json=batch_request,
                    headers=self.headers
                )
                
                if response.status_code != 200:
                    print(f"  ❌ Failed with status {response.status_code}")
                    return False
                
                data = response.json()
                processing_time = time.time() - start_time
                
                print(f"  ✅ Batch status: {data['status']}")
                print(f"  Total processed: {data['total_processed']}")
                print(f"  Total failed: {data['total_failed']}")
                print(f"  Processing time: {processing_time:.2f}s")
                print(f"  Success rate: {(data['total_processed'] - data['total_failed']) / data['total_processed'] * 100:.1f}%")
                
                return data["status"] == "completed"
                
            except Exception as e:
                print(f"  ❌ Batch processing test failed: {e}")
                return False
    
    async def test_metrics(self) -> bool:
        """Test metrics endpoint"""
        print("\n📊 Testing Metrics Endpoint...")
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.api_url}/api/v1/metrics",
                    headers=self.headers
                )
                
                if response.status_code != 200:
                    print(f"  ❌ Failed with status {response.status_code}")
                    return False
                
                metrics = response.json()
                
                print("  System Metrics:")
                print(f"    - Total requests: {metrics.get('total_requests', 0)}")
                print(f"    - Active agents: {metrics.get('active_agents', 0)}")
                print(f"    - Queue size: {metrics.get('queue_size', 0)}")
                print(f"    - Avg response time: {metrics.get('avg_response_time_ms', 0):.1f}ms")
                
                if "agent_metrics" in metrics:
                    print("  Agent Metrics:")
                    for agent_id, agent_metrics in metrics["agent_metrics"].items():
                        print(f"    - {agent_id}:")
                        print(f"        Tasks: {agent_metrics.get('processed_tasks', 0)}")
                        print(f"        Success rate: {agent_metrics.get('success_rate', 0):.1%}")
                
                return True
                
            except Exception as e:
                print(f"  ❌ Metrics test failed: {e}")
                return False
    
    async def test_circuit_health(self) -> bool:
        """Test circuit health endpoint"""
        print("\n🔌 Testing Circuit Health...")
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.api_url}/api/v1/circuit/health",
                    headers=self.headers
                )
                
                if response.status_code != 200:
                    print(f"  ❌ Failed with status {response.status_code}")
                    return False
                
                data = response.json()
                
                print(f"  Circuit Status: {data['status']}")
                print(f"  Active Circuits: {data.get('active_circuits', 0)}")
                print(f"  Total Agents: {data.get('total_agents', 0)}")
                
                if "circuits" in data:
                    print("  Circuit Details:")
                    for circuit_id, circuit_info in data["circuits"].items():
                        print(f"    - {circuit_id}: {circuit_info['status']} "
                              f"(agents: {len(circuit_info.get('agents', []))})")
                
                return True
                
            except Exception as e:
                print(f"  ❌ Circuit health test failed: {e}")
                return False
    
    async def test_error_handling(self) -> bool:
        """Test error handling with invalid requests"""
        print("\n⚠️  Testing Error Handling...")
        
        test_cases = [
            {
                "name": "Missing content",
                "request": {
                    "content_type": "text",
                    "pattern": "sequential"
                }
            },
            {
                "name": "Invalid pattern",
                "request": {
                    "content": "Test content",
                    "content_type": "text",
                    "pattern": "invalid_pattern"
                }
            },
            {
                "name": "Invalid priority",
                "request": {
                    "content": "Test content",
                    "content_type": "text",
                    "priority": "super_urgent"
                }
            }
        ]
        
        async with httpx.AsyncClient() as client:
            all_passed = True
            
            for test_case in test_cases:
                print(f"  Testing: {test_case['name']}")
                
                try:
                    response = await client.post(
                        f"{self.api_url}/api/v1/process",
                        json=test_case["request"],
                        headers=self.headers
                    )
                    
                    if response.status_code in [400, 422]:
                        print(f"    ✅ Correctly rejected with status {response.status_code}")
                    else:
                        print(f"    ❌ Unexpected status {response.status_code}")
                        all_passed = False
                        
                except Exception as e:
                    print(f"    ❌ Error: {e}")
                    all_passed = False
            
            return all_passed
    
    async def run_stress_test(self, num_requests: int = 10) -> bool:
        """Run stress test with concurrent requests"""
        print(f"\n🔥 Running Stress Test ({num_requests} concurrent requests)...")
        
        async def send_request(client: httpx.AsyncClient, index: int) -> Dict[str, Any]:
            request = {
                "content": f"Stress test request {index}: Explain quantum computing in simple terms.",
                "content_type": "text",
                "pattern": "adaptive",
                "priority": "low"
            }
            
            start_time = time.time()
            try:
                response = await client.post(
                    f"{self.api_url}/api/v1/process",
                    json=request,
                    headers=self.headers
                )
                
                return {
                    "index": index,
                    "success": response.status_code == 200,
                    "status_code": response.status_code,
                    "response_time": time.time() - start_time
                }
            except Exception as e:
                return {
                    "index": index,
                    "success": False,
                    "error": str(e),
                    "response_time": time.time() - start_time
                }
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            start_time = time.time()
            
            # Send all requests concurrently
            tasks = [send_request(client, i) for i in range(num_requests)]
            results = await asyncio.gather(*tasks)
            
            total_time = time.time() - start_time
            
            # Analyze results
            successful = sum(1 for r in results if r["success"])
            failed = num_requests - successful
            avg_response_time = sum(r["response_time"] for r in results) / num_requests
            
            print(f"  Total time: {total_time:.2f}s")
            print(f"  Successful: {successful}/{num_requests} ({successful/num_requests*100:.1f}%)")
            print(f"  Failed: {failed}")
            print(f"  Avg response time: {avg_response_time:.2f}s")
            print(f"  Requests/second: {num_requests/total_time:.1f}")
            
            return successful == num_requests
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*60)
        print("📊 TEST SUMMARY")
        print("="*60)
        
        if self.results:
            print("\nProcessing Test Results:")
            print(f"{'Test Name':<25} {'Status':<12} {'Time (s)':<10} {'Pattern':<15}")
            print("-"*70)
            
            for result in self.results:
                print(f"{result['test']:<25} "
                      f"{result['status']:<12} "
                      f"{result['processing_time']:<10.2f} "
                      f"{result['pattern_used']:<15}")
            
            # Calculate statistics
            total_time = sum(r['processing_time'] for r in self.results)
            avg_time = total_time / len(self.results)
            
            print(f"\nTotal processing time: {total_time:.2f}s")
            print(f"Average processing time: {avg_time:.2f}s")
    
    async def run_all_tests(self):
        """Run all tests"""
        print("🚀 Starting Neuron Framework System Tests")
        print("="*60)
        
        tests_passed = 0
        tests_failed = 0
        
        # Run each test
        test_functions = [
            ("Health Check", self.test_health_check),
            ("Agent Status", self.test_agent_status),
            ("Circuit Health", self.test_circuit_health),
            ("Metrics", self.test_metrics),
            ("Error Handling", self.test_error_handling),
        ]
        
        # Run basic tests
        for test_name, test_func in test_functions:
            try:
                if await test_func():
                    tests_passed += 1
                else:
                    tests_failed += 1
            except Exception as e:
                print(f"\n❌ {test_name} test crashed: {e}")
                tests_failed += 1
        
        # Run processing tests
        for test_case in TEST_REQUESTS:
            try:
                if await self.test_processing(test_case):
                    tests_passed += 1
                else:
                    tests_failed += 1
            except Exception as e:
                print(f"\n❌ Processing test '{test_case['name']}' crashed: {e}")
                tests_failed += 1
        
        # Run batch test
        try:
            if await self.test_batch_processing():
                tests_passed += 1
            else:
                tests_failed += 1
        except Exception as e:
            print(f"\n❌ Batch processing test crashed: {e}")
            tests_failed += 1
        
        # Run stress test
        try:
            if await self.run_stress_test(10):
                tests_passed += 1
            else:
                tests_failed += 1
        except Exception as e:
            print(f"\n❌ Stress test crashed: {e}")
            tests_failed += 1
        
        # Print summary
        self.print_summary()
        
        print("\n" + "="*60)
        print("🏁 TEST RESULTS")
        print("="*60)
        print(f"Total tests: {tests_passed + tests_failed}")
        print(f"✅ Passed: {tests_passed}")
        print(f"❌ Failed: {tests_failed}")
        print(f"Success rate: {tests_passed/(tests_passed+tests_failed)*100:.1f}%")
        
        return tests_failed == 0


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="System test script for LLaMA3 Neuron Framework"
    )
    parser.add_argument(
        "--api-url",
        default=DEFAULT_API_URL,
        help=f"API URL (default: {DEFAULT_API_URL})"
    )
    parser.add_argument(
        "--api-key",
        default=DEFAULT_API_KEY,
        help="API key for authentication"
    )
    parser.add_argument(
        "--stress-only",
        action="store_true",
        help="Run only stress test"
    )
    parser.add_argument(
        "--stress-count",
        type=int,
        default=10,
        help="Number of concurrent requests for stress test (default: 10)"
    )
    
    args = parser.parse_args()
    
    # Create tester
    tester = SystemTester(args.api_url, args.api_key)
    
    try:
        if args.stress_only:
            # Run only stress test
            print(f"🔥 Running stress test with {args.stress_count} requests...")
            success = await tester.run_stress_test(args.stress_count)
            return 0 if success else 1
        else:
            # Run all tests
            success = await tester.run_all_tests()
            return 0 if success else 1
            
    except KeyboardInterrupt:
        print("\n⚠️  Tests interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Test runner failed: {e}")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(asyncio.run(main()))