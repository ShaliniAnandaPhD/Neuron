"""
main.py - Main Test Runner

Entry point for running chaos engineering tests.
"""

import asyncio
import argparse
import logging
import sys
from pathlib import Path
from datetime import datetime
import signal
import traceback

from agent import AgentPool
from chaos_injector import ChaosInjector
from monitor import HealthMonitor
from orchestrator import RecoveryOrchestrator
from metrics import MetricsCollector, TestReporter
from test_scenarios import get_scenario, SCENARIOS

# Setup logging
def setup_logging(level: str = "INFO"):
    """Setup logging configuration"""
    log_format = "[%(asctime)s] %(levelname)s: %(message)s"
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format=log_format,
        datefmt="%Y-%m-%dT%H:%M:%S"
    )
    
    # Reduce noise from asyncio
    logging.getLogger("asyncio").setLevel(logging.WARNING)


class ChaosTestRunner:
    """
    Main test runner that coordinates all components.
    """
    
    def __init__(self, agent_count: int = 6):
        self.agent_count = agent_count
        self.agent_pool = None
        self.chaos_injector = None
        self.monitor = None
        self.orchestrator = None
        self.metrics = None
        self.reporter = TestReporter()
        
        # Shutdown handling
        self._shutdown = False
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logging.info("Shutdown signal received")
        self._shutdown = True
    
    async def setup(self):
        """Initialize all components"""
        logging.info(f"Setting up chaos test with {self.agent_count} agents")
        
        # Create agent pool
        self.agent_pool = AgentPool(self.agent_count)
        await self.agent_pool.initialize()
        
        # Create chaos injector
        self.chaos_injector = ChaosInjector(self.agent_pool)
        
        # Create monitor
        self.monitor = HealthMonitor(
            self.agent_pool,
            check_interval=0.5,
            failure_threshold=1.0
        )
        await self.monitor.start()
        
        # Create orchestrator
        self.orchestrator = RecoveryOrchestrator(
            self.agent_pool,
            self.monitor,
            max_recovery_time=2.0
        )
        await self.orchestrator.start()
        
        # Create metrics collector
        self.metrics = MetricsCollector()
        await self.metrics.start()
        
        logging.info("All components initialized")
    
    async def teardown(self):
        """Cleanup all components"""
        logging.info("Tearing down components")
        
        if self.metrics:
            await self.metrics.stop()
        
        if self.orchestrator:
            await self.orchestrator.stop()
        
        if self.monitor:
            await self.monitor.stop()
        
        if self.chaos_injector:
            await self.chaos_injector.stop_chaos()
        
        if self.agent_pool:
            await self.agent_pool.shutdown()
        
        logging.info("Teardown complete")
    
    async def run_scenario(self, scenario_name: str):
        """Run a specific test scenario"""
        logging.info(f"Running scenario: {scenario_name}")
        
        try:
            # Get scenario
            scenario = get_scenario(scenario_name)
            
            # Setup scenario with components
            await scenario.setup({
                "agent_pool": self.agent_pool,
                "chaos_injector": self.chaos_injector,
                "monitor": self.monitor,
                "orchestrator": self.orchestrator,
                "metrics": self.metrics
            })
            
            # Run scenario
            result = await scenario.run()
            
            # Generate report
            report_path = self.reporter.generate_report(result)
            
            logging.info(f"Scenario completed. Report: {report_path}")
            
            return result
            
        except Exception as e:
            logging.error(f"Scenario failed: {e}")
            traceback.print_exc()
            raise
    
    async def run_all_scenarios(self):
        """Run all available scenarios"""
        results = {}
        
        for scenario_name in SCENARIOS:
            if self._shutdown:
                break
            
            logging.info(f"\n{'='*60}")
            logging.info(f"Running scenario: {scenario_name}")
            logging.info(f"{'='*60}\n")
            
            try:
                result = await self.run_scenario(scenario_name)
                results[scenario_name] = result
                
                # Wait between scenarios
                await asyncio.sleep(5)
                
            except Exception as e:
                logging.error(f"Scenario {scenario_name} failed: {e}")
                results[scenario_name] = None
        
        # Summary report
        self._print_summary(results)
        
        return results
    
    def _print_summary(self, results: dict):
        """Print summary of all test results"""
        print("\n" + "="*60)
        print("CHAOS TEST SUMMARY")
        print("="*60)
        
        total = len(results)
        passed = sum(1 for r in results.values() if r and r.success)
        
        print(f"\nTotal Scenarios: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {total - passed}")
        
        print("\nDetailed Results:")
        print("-"*60)
        
        for scenario_name, result in results.items():
            if result:
                status = "PASSED" if result.success else "FAILED"
                print(f"\n{scenario_name}: {status}")
                print(f"  Detection: {result.failure_detection_time:.3f}s " +
                      f"({'✓' if result.detection_passed else '✗'})")
                print(f"  Recovery: {result.recovery_time:.3f}s " +
                      f"({'✓' if result.recovery_passed else '✗'})")
                print(f"  Integrity: {result.data_integrity:.1%} " +
                      f"({'✓' if result.integrity_passed else '✗'})")
            else:
                print(f"\n{scenario_name}: ERROR")
        
        print("\n" + "="*60)


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="AI Agent Chaos Engineering Test Suite"
    )
    
    parser.add_argument(
        "--scenario",
        choices=list(SCENARIOS.keys()) + ["all"],
        default="cascade-failure",
        help="Test scenario to run"
    )
    
    parser.add_argument(
        "--agents",
        type=int,
        default=6,
        help="Number of agents in the pool"
    )
    
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level"
    )
    
    parser.add_argument(
        "--report-dir",
        default="chaos_reports",
        help="Directory for test reports"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.log_level)
    
    # Print header
    print("\n" + "="*60)
    print("AI AGENT CHAOS ENGINEERING TEST SUITE")
    print("="*60)
    print(f"Scenario: {args.scenario}")
    print(f"Agents: {args.agents}")
    print(f"Log Level: {args.log_level}")
    print(f"Report Dir: {args.report_dir}")
    print("="*60 + "\n")
    
    # Create runner
    runner = ChaosTestRunner(agent_count=args.agents)
    
    try:
        # Setup
        await runner.setup()
        
        # Run scenarios
        if args.scenario == "all":
            await runner.run_all_scenarios()
        else:
            await runner.run_scenario(args.scenario)
        
    except KeyboardInterrupt:
        logging.info("Test interrupted by user")
    except Exception as e:
        logging.error(f"Test failed: {e}")
        traceback.print_exc()
        sys.exit(1)
    finally:
        # Cleanup
        await runner.teardown()
    
    logging.info("Test complete")


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())