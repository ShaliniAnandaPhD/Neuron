
"""
performance_decision.py
Analyzes performance metrics and makes intelligent swap decisions
Save as: .github/scripts/performance_decision.py
"""

import json
import argparse
import sys
import os
from datetime import datetime
from typing import Dict, Any, Optional

def log(message):
    """Simple logging function"""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")

class PerformanceDecisionEngine:
    """Makes intelligent decisions about component swapping based on performance"""
    
    def __init__(self):
        # Performance thresholds for different components
        self.thresholds = {
            'memory_agent': {
                'cpu_usage': 0.80,
                'memory_usage': 0.85,
                'response_time_ms': 500,
                'error_rate': 0.05,
                'cache_hit_rate': 0.75
            },
            'reasoning_agent': {
                'cpu_usage': 0.75,
                'memory_usage': 0.80,
                'response_time_ms': 1000,
                'error_rate': 0.03,
                'decision_accuracy': 0.85
            },
            'communication_system': {
                'message_throughput': 800,
                'avg_latency_ms': 60,
                'queue_depth': 50,
                'message_loss_rate': 0.001
            }
        }
        
        # Available component versions and their characteristics
        self.component_versions = {
            'memory': {
                'v1.0-standard': {'performance': 0.7, 'efficiency': 0.8, 'stability': 0.9},
                'v1.1-performance': {'performance': 0.9, 'efficiency': 0.6, 'stability': 0.8},
                'v1.2-efficient': {'performance': 0.6, 'efficiency': 0.9, 'stability': 0.95}
            },
            'reasoning': {
                'v2.0-analytical': {'performance': 0.7, 'accuracy': 0.95, 'stability': 0.9},
                'v2.1-fast': {'performance': 0.9, 'accuracy': 0.85, 'stability': 0.8},
                'v1.9-reliable': {'performance': 0.6, 'accuracy': 0.97, 'stability': 0.98}
            },
            'communication': {
                'v3.0-standard': {'performance': 0.7, 'throughput': 0.8, 'stability': 0.9},
                'v3.1-highperf': {'performance': 0.9, 'throughput': 0.95, 'stability': 0.85}
            }
        }
        
        log("Performance decision engine initialized")
    
    def analyze_performance(self, metrics: Dict[str, Any], threshold: float, action: str) -> Dict[str, Any]:
        """Main analysis function"""
        try:
            log(f"Analyzing performance with threshold={threshold}, action={action}")
            
            analysis = {
                'timestamp': datetime.now().isoformat(),
                'threshold': threshold,
                'action': action,
                'component_scores': {},
                'swap_needed': False,
                'recommendations': []
            }
            
            # Check if metrics contain errors
            if 'error' in metrics:
                log(f"Warning: Metrics contain error: {metrics['error']}")
                analysis.update({
                    'target_agent': 'none',
                    'current_version': '',
                    'recommended_version': '',
                    'swap_reason': f"Metrics collection failed: {metrics['error']}",
                    'performance_score': 0.5,
                    'confidence': 0.0
                })
                return analysis
            
            # Calculate performance scores for each component
            for component in ['memory_agent', 'reasoning_agent', 'communication_system']:
                if component in metrics:
                    try:
                        score = self._calculate_performance_score(component, metrics[component])
                        analysis['component_scores'][component] = score
                        log(f"{component} performance score: {score:.3f}")
                        
                        # Check if swap is needed
                        if score < threshold:
                            component_name = component.replace('_agent', '').replace('_system', '')
                            recommendation = self._recommend_version(component_name, metrics[component], score)
                            
                            if recommendation:
                                analysis['swap_needed'] = True
                                analysis['recommendations'].append(recommendation)
                                log(f"Swap recommended for {component}: {recommendation['reason']}")
                                
                    except Exception as e:
                        log(f"Error analyzing {component}: {e}")
                        analysis['component_scores'][component] = 0.5
            
            # Select primary recommendation (most urgent)
            if analysis['recommendations']:
                # Sort by urgency (lowest score first)
                analysis['recommendations'].sort(key=lambda x: x['current_score'])
                primary_rec = analysis['recommendations'][0]
                
                analysis.update({
                    'target_agent': primary_rec['component'],
                    'current_version': primary_rec['current_version'],
                    'recommended_version': primary_rec['recommended_version'],
                    'swap_reason': primary_rec['reason'],
                    'performance_score': primary_rec['current_score'],
                    'confidence': primary_rec['confidence']
                })
            else:
                # No swap needed
                best_score = max(analysis['component_scores'].values()) if analysis['component_scores'] else 1.0
                analysis.update({
                    'target_agent': 'none',
                    'current_version': '',
                    'recommended_version': '',
                    'swap_reason': 'All components performing within thresholds',
                    'performance_score': best_score,
                    'confidence': 0.0
                })
            
            log(f"Analysis complete: swap_needed={analysis['swap_needed']}")
            return analysis
            
        except Exception as e:
            log(f"Critical error in performance analysis: {e}")
            return {
                'timestamp': datetime.now().isoformat(),
                'threshold': threshold,
                'action': action,
                'component_scores': {},
                'swap_needed': False,
                'target_agent': 'none',
                'current_version': '',
                'recommended_version': '',
                'swap_reason': f'Analysis failed: {str(e)}',
                'performance_score': 0.5,
                'confidence': 0.0,
                'error': str(e)
            }
    
    def _calculate_performance_score(self, component: str, metrics: Dict[str, Any]) -> float:
        """Calculate performance score for a component (0.0 = bad, 1.0 = perfect)"""
        try:
            thresholds = self.thresholds.get(component, {})
            if not thresholds:
                log(f"Warning: No thresholds defined for {component}")
                return 1.0
            
            score = 0.0
            weight_sum = 0.0
            
            # Define metric weights
            metric_weights = {
                'cpu_usage': 0.25, 'memory_usage': 0.25, 'response_time_ms': 0.30,
                'error_rate': 0.20, 'cache_hit_rate': 0.15, 'decision_accuracy': 0.25,
                'message_throughput': 0.30, 'avg_latency_ms': 0.25, 'queue_depth': 0.20,
                'message_loss_rate': 0.15
            }
            
            for metric, threshold_val in thresholds.items():
                if metric in metrics and metric in metric_weights:
                    current_val = metrics[metric]
                    weight = metric_weights[metric]
                    weight_sum += weight
                    
                    # Calculate metric score (different logic for different metric types)
                    if metric in ['cpu_usage', 'memory_usage', 'response_time_ms', 'error_rate', 
                                 'avg_latency_ms', 'queue_depth', 'message_loss_rate']:
                        # Lower is better metrics
                        metric_score = max(0, 1 - (current_val / threshold_val))
                    else:
                        # Higher is better metrics (cache_hit_rate, decision_accuracy, message_throughput)
                        metric_score = min(1, current_val / threshold_val)
                    
                    score += metric_score * weight
            
            final_score = score / weight_sum if weight_sum > 0 else 1.0
            return final_score
            
        except Exception as e:
            log(f"Error calculating score for {component}: {e}")
            return 0.5
    
    def _recommend_version(self, component: str, metrics: Dict[str, Any], current_score: float) -> Optional[Dict[str, Any]]:
        """Recommend the best version for current conditions"""
        try:
            if component not in self.component_versions:
                log(f"Warning: No versions available for {component}")
                return None
            
            versions = self.component_versions[component]
            
            # Mock current version (in real system, this would come from deployment info)
            current_version = "v1.0-standard"  # Default current version
            
            # Determine what kind of optimization is needed
            optimization_needed = self._determine_optimization_type(component, metrics)
            
            # Score each version based on what we need
            best_version = None
            best_score = 0
            
            for version, characteristics in versions.items():
                if version == current_version:
                    continue
                
                # Score version based on optimization needs
                if optimization_needed == 'performance':
                    version_score = characteristics.get('performance', 0) * 0.6 + characteristics.get('stability', 0) * 0.4
                elif optimization_needed == 'efficiency':
                    version_score = characteristics.get('efficiency', 0) * 0.6 + characteristics.get('stability', 0) * 0.4
                elif optimization_needed == 'stability':
                    version_score = characteristics.get('stability', 0) * 0.8 + characteristics.get('performance', 0) * 0.2
                else:
                    version_score = sum(characteristics.values()) / len(characteristics)
                
                if version_score > best_score:
                    best_score = version_score
                    best_version = version
            
            if best_version:
                return {
                    'component': component,
                    'current_version': current_version,
                    'recommended_version': best_version,
                    'reason': f"{optimization_needed} optimization needed (score: {current_score:.3f})",
                    'current_score': current_score,
                    'expected_improvement': (best_score - current_score) * 100,
                    'confidence': min(0.95, best_score)
                }
            
            return None
            
        except Exception as e:
            log(f"Error recommending version for {component}: {e}")
            return None
    
    def _determine_optimization_type(self, component: str, metrics: Dict[str, Any]) -> str:
        """Determine what type of optimization is needed"""
        try:
            thresholds = self.thresholds.get(component, {})
            
            performance_issues = 0
            efficiency_issues = 0
            
            if component == 'memory_agent':
                if metrics.get('response_time_ms', 0) > thresholds.get('response_time_ms', 500) * 0.8:
                    performance_issues += 1
                if metrics.get('cpu_usage', 0) > 0.7:
                    efficiency_issues += 1
                if metrics.get('memory_usage', 0) > 0.7:
                    efficiency_issues += 1
            
            elif component == 'reasoning_agent':
                if metrics.get('response_time_ms', 0) > thresholds.get('response_time_ms', 1000) * 0.8:
                    performance_issues += 1
                if metrics.get('decision_accuracy', 1) < 0.9:
                    performance_issues += 1
                if metrics.get('cpu_usage', 0) > 0.7:
                    efficiency_issues += 1
            
            elif component == 'communication_system':
                if metrics.get('message_throughput', 1000) < thresholds.get('message_throughput', 800):
                    performance_issues += 1
                if metrics.get('avg_latency_ms', 0) > thresholds.get('avg_latency_ms', 60) * 0.8:
                    performance_issues += 1
            
            if performance_issues > efficiency_issues:
                return 'performance'
            elif efficiency_issues > 0:
                return 'efficiency'
            else:
                return 'stability'
                
        except Exception as e:
            log(f"Error determining optimization type: {e}")
            return 'performance'

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Analyze performance and make swap decisions')
    parser.add_argument('--metrics-file', required=True,
                       help='Path to metrics JSON file')
    parser.add_argument('--threshold', type=float, default=0.7,
                       help='Performance threshold (0.0-1.0)')
    parser.add_argument('--action', default='monitor_and_swap',
                       choices=['monitor_and_swap', 'monitor_only', 'force_swap', 'status_check'],
                       help='Action to perform')
    parser.add_argument('--webhook-data', default='{}',
                       help='Webhook data JSON string')
    
    args = parser.parse_args()
    
    try:
        log(f"Starting performance analysis with file: {args.metrics_file}")
        
        # Load metrics
        if not os.path.exists(args.metrics_file):
            raise FileNotFoundError(f"Metrics file '{args.metrics_file}' not found")
        
        with open(args.metrics_file, 'r') as f:
            metrics = json.load(f)
        
        # Parse webhook data
        try:
            webhook_data = json.loads(args.webhook_data) if args.webhook_data != '{}' else {}
        except json.JSONDecodeError:
            log("Warning: Invalid webhook data, using empty dict")
            webhook_data = {}
        
        # Initialize decision engine
        engine = PerformanceDecisionEngine()
        
        # Analyze performance
        analysis = engine.analyze_performance(metrics, args.threshold, args.action)
        
        # Save analysis results
        with open('decision_analysis.json', 'w') as f:
            json.dump(analysis, f, indent=2)
        
        # Set GitHub Actions outputs
        try:
            print(f"::set-output name=swap_needed::{str(analysis['swap_needed']).lower()}")
            print(f"::set-output name=target_agent::{analysis['target_agent']}")
            print(f"::set-output name=current_version::{analysis['current_version']}")
            print(f"::set-output name=recommended_version::{analysis['recommended_version']}")
            print(f"::set-output name=swap_reason::{analysis['swap_reason']}")
            print(f"::set-output name=performance_score::{analysis['performance_score']}")
        except Exception as e:
            log(f"Warning: Error setting GitHub outputs: {e}")
        
        # Display analysis results
        print(f"\n🔍 Performance Analysis Results:")
        print(f"Swap Needed: {analysis['swap_needed']}")
        print(f"Performance Score: {analysis['performance_score']:.3f}")
        
        if analysis['swap_needed']:
            print(f"Target Agent: {analysis['target_agent']}")
            print(f"Current Version: {analysis['current_version']}")
            print(f"Recommended Version: {analysis['recommended_version']}")
            print(f"Reason: {analysis['swap_reason']}")
            print(f"Confidence: {analysis.get('confidence', 0):.2f}")
        else:
            print(f"Status: {analysis['swap_reason']}")
        
        # Show component scores
        if analysis['component_scores']:
            print(f"\n📊 Component Performance Scores:")
            for component, score in analysis['component_scores'].items():
                status = "✅" if score >= args.threshold else "⚠️"
                print(f"  {status} {component}: {score:.3f}")
        
        log("Performance analysis completed successfully")
        return 0
        
    except Exception as e:
        log(f"Fatal error: {e}")
        print(f"❌ Error during analysis: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
