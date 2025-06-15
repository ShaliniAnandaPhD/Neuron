# .github/scripts/validate_performance.py

"""
validate_performance.py
Validates performance improvements after component swapping
Save as: .github/scripts/validate_performance.py
"""

import argparse
import json
import time
import random
import sys
import os
from datetime import datetime
from typing import Dict, Any

def log(message):
    """Simple logging function"""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")

class PerformanceValidator:
    """Validates performance improvements after swapping"""
    
    def __init__(self):
        self.validation_criteria = {
            'memory': {
                'response_time_improvement': 10,  # % improvement required
                'error_rate_max': 0.05,
                'cache_hit_rate_min': 0.75,
                'memory_usage_max': 0.85
            },
            'reasoning': {
                'response_time_improvement': 15,
                'accuracy_min': 0.85,
                'error_rate_max': 0.03,
                'cpu_usage_max': 0.80
            },
            'communication': {
                'throughput_improvement': 20,
                'latency_improvement': 15,
                'message_loss_rate_max': 0.001,
                'queue_depth_max': 50
            }
        }
        log("Performance validator initialized")
    
    def validate_performance(self, component: str, expected_version: str, baseline_file: str, duration: int) -> Dict[str, Any]:
        """Performs comprehensive validation for the specified component"""
        log(f"Starting validation for {component} (expected version: {expected_version}) for {duration} seconds.")
        
        baseline_metrics = self._load_baseline_metrics(baseline_file)
        if not baseline_metrics:
            return {'status': 'failed', 'message': 'Failed to load baseline metrics.'}

        validation_results = {
            'component': component,
            'expected_version': expected_version,
            'status': 'in_progress',
            'checks': []
        }

        # Simulate monitoring over time
        for i in range(duration // 10): # Check every 10 seconds
            time.sleep(10)
            log(f"  Simulating monitoring... ({ (i + 1) * 10 }/{duration}s)")
            
            # Simulate current metrics for comparison
            current_metrics = self._simulate_current_metrics(component)

            # Perform various checks
            resource_check = self._check_resource_utilization(component, expected_version, baseline_metrics)
            validation_results['checks'].append(resource_check)

            performance_check = self._check_performance_metrics(component, current_metrics, baseline_metrics)
            validation_results['checks'].append(performance_check)
            
            sla_check = self._check_sla_compliance(component, current_metrics)
            validation_results['checks'].append(sla_check)

            if not resource_check['compliant'] or not performance_check['compliant'] or not sla_check['compliant']:
                log(f"  Validation issues detected for {component} at {datetime.now().strftime('%H:%M:%S')}")
                validation_results['status'] = 'failed'
                validation_results['message'] = f"Validation failed due to issues with {resource_check['status']}, {performance_check['status']}, or {sla_check['status']}."
                return validation_results

        # Final overall assessment
        all_checks_passed = all(c['status'] == 'passed' for c in validation_results['checks'])
        
        if all_checks_passed:
            validation_results['status'] = 'passed'
            validation_results['message'] = f"✅ {component} performance validated successfully for version {expected_version}."
            log(f"✅ Validation for {component} passed.")
        else:
            validation_results['status'] = 'failed'
            validation_results['message'] = f"❌ {component} performance validation failed after swap to version {expected_version}."
            log(f"❌ Validation for {component} failed.")
        
        return validation_results

    def _load_baseline_metrics(self, baseline_file: str) -> Optional[Dict[str, Any]]:
        """Load baseline metrics from a JSON file."""
        try:
            with open(baseline_file, 'r') as f:
                metrics = json.load(f)
                log(f"Loaded baseline metrics from {baseline_file}")
                return metrics
        except FileNotFoundError:
            log(f"ERROR: Baseline metrics file not found at {baseline_file}")
            return None
        except json.JSONDecodeError:
            log(f"ERROR: Invalid JSON in baseline metrics file {baseline_file}")
            return None
        except Exception as e:
            log(f"ERROR: An error occurred loading baseline metrics: {e}")
            return None

    def _simulate_current_metrics(self, component: str) -> Dict[str, float]:
        """Simulate current live metrics for a component."""
        log(f"  Simulating current metrics for {component}...")
        if component == 'memory':
            return {
                'cpu_usage': random.uniform(0.2, 0.6),
                'memory_usage': random.uniform(0.3, 0.7),
                'response_time_ms': random.uniform(150, 300),
                'cache_hit_rate': random.uniform(0.80, 0.95),
                'error_rate': random.uniform(0.005, 0.03)
            }
        elif component == 'reasoning':
            return {
                'cpu_usage': random.uniform(0.3, 0.7),
                'memory_usage': random.uniform(0.4, 0.8),
                'response_time_ms': random.uniform(400, 700),
                'decision_accuracy': random.uniform(0.88, 0.98),
                'error_rate': random.uniform(0.001, 0.02)
            }
        elif component == 'communication':
            return {
                'throughput': random.uniform(500, 1000),
                'latency_ms': random.uniform(5, 20),
                'message_loss_rate': random.uniform(0.00005, 0.0005),
                'queue_depth': random.uniform(10, 40)
            }
        return {}

    def _check_performance_metrics(self, component: str, current_metrics: Dict[str, float], baseline_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Check if current performance metrics meet improvement criteria."""
        log(f"  Checking performance metrics for {component}...")
        criteria = self.validation_criteria.get(component, {})
        baseline = baseline_metrics.get(f'{component}_agent' if component != 'communication' else 'communication_system', {})
        
        issues = []
        status = 'passed'
        message = f"{component} performance within expected range."

        if component == 'memory':
            # Response time improvement
            if 'response_time_ms' in current_metrics and 'response_time_ms' in baseline:
                baseline_rt = baseline['response_time_ms']
                current_rt = current_metrics['response_time_ms']
                if baseline_rt > 0 and current_rt < baseline_rt * (1 - criteria.get('response_time_improvement', 0)/100):
                    log(f"    Response time improved for {component}")
                else:
                    issues.append('response_time')
                    status = 'failed'
                    log(f"    Response time for {component} did not improve as expected. Baseline: {baseline_rt:.2f}ms, Current: {current_rt:.2f}ms")

            # Error rate check
            if current_metrics.get('error_rate', 0) > criteria.get('error_rate_max', 1.0):
                issues.append('error_rate')
                status = 'failed'
                log(f"    Error rate for {component} is too high: {current_metrics.get('error_rate', 0):.4f}")

            # Cache hit rate check
            if current_metrics.get('cache_hit_rate', 0) < criteria.get('cache_hit_rate_min', 0):
                issues.append('cache_hit_rate')
                status = 'failed'
                log(f"    Cache hit rate for {component} is too low: {current_metrics.get('cache_hit_rate', 0):.2f}")

        elif component == 'reasoning':
            # Response time improvement
            if 'response_time_ms' in current_metrics and 'response_time_ms' in baseline:
                baseline_rt = baseline['response_time_ms']
                current_rt = current_metrics['response_time_ms']
                if baseline_rt > 0 and current_rt < baseline_rt * (1 - criteria.get('response_time_improvement', 0)/100):
                    log(f"    Response time improved for {component}")
                else:
                    issues.append('response_time')
                    status = 'failed'
                    log(f"    Response time for {component} did not improve as expected. Baseline: {baseline_rt:.2f}ms, Current: {current_rt:.2f}ms")

            # Accuracy check
            if current_metrics.get('decision_accuracy', 0) < criteria.get('accuracy_min', 0):
                issues.append('accuracy')
                status = 'failed'
                log(f"    Decision accuracy for {component} is too low: {current_metrics.get('decision_accuracy', 0):.2f}")

            # Error rate check
            if current_metrics.get('error_rate', 0) > criteria.get('error_rate_max', 1.0):
                issues.append('error_rate')
                status = 'failed'
                log(f"    Error rate for {component} is too high: {current_metrics.get('error_rate', 0):.4f}")

        elif component == 'communication':
            # Throughput improvement
            if 'throughput' in current_metrics and 'throughput' in baseline:
                baseline_tp = baseline['throughput']
                current_tp = current_metrics['throughput']
                if current_tp > baseline_tp * (1 + criteria.get('throughput_improvement', 0)/100):
                    log(f"    Throughput improved for {component}")
                else:
                    issues.append('throughput')
                    status = 'failed'
                    log(f"    Throughput for {component} did not improve as expected. Baseline: {baseline_tp:.2f}, Current: {current_tp:.2f}")

            # Latency improvement
            if 'latency_ms' in current_metrics and 'latency_ms' in baseline:
                baseline_lat = baseline['latency_ms']
                current_lat = current_metrics['latency_ms']
                if baseline_lat > 0 and current_lat < baseline_lat * (1 - criteria.get('latency_improvement', 0)/100):
                    log(f"    Latency improved for {component}")
                else:
                    issues.append('latency')
                    status = 'failed'
                    log(f"    Latency for {component} did not improve as expected. Baseline: {baseline_lat:.2f}ms, Current: {current_lat:.2f}ms")

            # Message loss rate check
            if current_metrics.get('message_loss_rate', 0) > criteria.get('message_loss_rate_max', 1.0):
                issues.append('message_loss_rate')
                status = 'failed'
                log(f"    Message loss rate for {component} is too high: {current_metrics.get('message_loss_rate', 0):.6f}")

        if issues:
            message = f"{component} performance issues: " + ", ".join(issues)
        
        return {
            'check': 'performance_metrics',
            'status': status,
            'message': message,
            'compliant': status == 'passed',
            'issues': issues,
            'current_metrics': current_metrics
        }
    
    def _check_sla_compliance(self, component: str, current_metrics: Dict[str, float]) -> Dict[str, Any]:
        """Check if the component's performance complies with defined SLAs."""
        log(f"  Checking SLA compliance for {component}...")
        
        # Example SLA thresholds (these would typically come from configuration)
        sla_thresholds = {
            'memory': {
                'availability_min': 0.999,
                'response_time_p95_max': 400, # ms
                'error_rate_max': 0.01,
                'throughput_min': 400 # req/s
            },
            'reasoning': {
                'availability_min': 0.995,
                'response_time_p95_max': 900, # ms
                'error_rate_max': 0.02,
                'accuracy_min': 0.90
            },
            'communication': {
                'availability_min': 0.9999,
                'latency_p99_max': 30, # ms
                'message_loss_rate_max': 0.0001,
                'throughput_min': 800 # messages/s
            }
        }

        component_slas = sla_thresholds.get(component, {})
        
        # Simulate SLA metrics (these would typically be observed from live systems)
        sla_metrics = {
            'availability': random.uniform(0.99, 0.9999),
            'response_time_p95': current_metrics.get('response_time_ms', 0) * random.uniform(1.1, 1.3), # P95 is higher than avg
            'error_rate': current_metrics.get('error_rate', 0),
            'throughput': current_metrics.get('throughput', 0),
            'latency_p99': current_metrics.get('latency_ms', 0) * random.uniform(1.2, 1.5),
            'accuracy': current_metrics.get('decision_accuracy', 0)
        }
        
        compliant = True
        violated_metrics = []

        if component == 'memory':
            if sla_metrics['availability'] < component_slas.get('availability_min', 0): compliant = False; violated_metrics.append('availability')
            if sla_metrics['response_time_p95'] > component_slas.get('response_time_p95_max', float('inf')): compliant = False; violated_metrics.append('response_time_p95')
            if sla_metrics['error_rate'] > component_slas.get('error_rate_max', float('inf')): compliant = False; violated_metrics.append('error_rate')
            if sla_metrics['throughput'] < component_slas.get('throughput_min', 0): compliant = False; violated_metrics.append('throughput')
        elif component == 'reasoning':
            if sla_metrics['availability'] < component_slas.get('availability_min', 0): compliant = False; violated_metrics.append('availability')
            if sla_metrics['response_time_p95'] > component_slas.get('response_time_p95_max', float('inf')): compliant = False; violated_metrics.append('response_time_p95')
            if sla_metrics['error_rate'] > component_slas.get('error_rate_max', float('inf')): compliant = False; violated_metrics.append('error_rate')
            if sla_metrics['accuracy'] < component_slas.get('accuracy_min', 0): compliant = False; violated_metrics.append('accuracy')
        elif component == 'communication':
            if sla_metrics['availability'] < component_slas.get('availability_min', 0): compliant = False; violated_metrics.append('availability')
            if sla_metrics['latency_p99'] > component_slas.get('latency_p99_max', float('inf')): compliant = False; violated_metrics.append('latency_p99')
            if sla_metrics['message_loss_rate'] > component_slas.get('message_loss_rate_max', float('inf')): compliant = False; violated_metrics.append('message_loss_rate')
            if sla_metrics['throughput'] < component_slas.get('throughput_min', 0): compliant = False; violated_metrics.append('throughput')

        return {
            'check': 'sla_compliance',
            'status': 'passed' if compliant else 'failed',
            'message': f"{component} {'meets' if compliant else 'violates'} SLA requirements. {'Violated: ' + ', '.join(violated_metrics) if not compliant else ''}",
            'sla_metrics': sla_metrics,
            'sla_thresholds': component_slas,
            'compliant': compliant
        }
    
    def _check_resource_utilization(self, component: str, expected_version: str, baseline_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Check resource utilization efficiency"""
        log(f"  Checking resource utilization for {component}...")
        # Simulate resource metrics
        resource_metrics = {
            'cpu_usage': random.uniform(0.3, 0.8),
            'memory_usage': random.uniform(0.4, 0.7),
            'disk_io': random.uniform(0.1, 0.4),
            'network_bandwidth': random.uniform(50, 200)
        }
        
        # Define acceptable ranges (example values)
        acceptable_ranges = {
            'memory': {
                'cpu_usage': (0.2, 0.7),
                'memory_usage': (0.3, 0.8),
                'disk_io': (0.05, 0.5),
                'network_bandwidth': (20, 250)
            },
            'reasoning': {
                'cpu_usage': (0.3, 0.85),
                'memory_usage': (0.4, 0.9),
                'disk_io': (0.1, 0.6),
                'network_bandwidth': (30, 300)
            },
            'communication': {
                'cpu_usage': (0.1, 0.5),
                'memory_usage': (0.2, 0.6),
                'disk_io': (0.02, 0.3),
                'network_bandwidth': (100, 500)
            }
        }

        component_ranges = acceptable_ranges.get(component, {})
        
        compliant = True
        issues = []
        for metric, value in resource_metrics.items():
            if metric in component_ranges:
                min_val, max_val = component_ranges[metric]
                if not (min_val <= value <= max_val):
                    compliant = False
                    issues.append(f"{metric} ({value:.2f} out of range {min_val}-{max_val})")
        
        status = 'passed' if compliant else 'failed'
        message = f"{component} resource utilization is {'optimal' if compliant else 'suboptimal'}. {'Issues: ' + ', '.join(issues) if issues else ''}"
        
        return {
            'check': 'resource_utilization',
            'status': status,
            'message': message,
            'resource_metrics': resource_metrics,
            'compliant': compliant
        }

def main():
    parser = argparse.ArgumentParser(description="Validate performance after component swap.")
    parser.add_argument('--component', required=True, help='Component to validate (e.g., memory, reasoning, communication)')
    parser.add_argument('--expected-version', required=True, help='Expected version after swap')
    parser.add_argument('--baseline-metrics', required=True, help='Path to baseline metrics JSON file')
    parser.add_argument('--validation-duration', type=int, default=60, help='Duration for performance validation in seconds')
    
    args = parser.parse_args()
    
    validator = PerformanceValidator()
    results = validator.validate_performance(
        args.component,
        args.expected_version,
        args.baseline_metrics,
        args.validation_duration
    )
    
    # Save results to a file for artifact upload
    output_filename = f"{args.component}_validation_results.json"
    with open(output_filename, 'w') as f:
        json.dump(results, f, indent=2)
    
    log(f"Validation results saved to {output_filename}")
    
    # Set GitHub Actions outputs
    # Using '::set-output' is deprecated, should use GITHUB_OUTPUT environment file.
    # For compatibility, this might still work in some runners, but the new way is preferred.
    # The workflow YAML would need to capture these as outputs if they are defined as such.
    # For a simple pass/fail, you can just exit with 0 or 1.
    print(f"validation_passed={results['status'] == 'passed'}")
    print(f"validation_status={results['status']}")
    print(f"validation_message={results['message']}")
    
    if results['status'] == 'passed':
        log(f"✅ Validation for {args.component} SUCCEEDED.")
        sys.exit(0)
    else:
        log(f"❌ Validation for {args.component} FAILED. Reason: {results['message']}")
        sys.exit(1)

if __name__ == "__main__":
    main()
