
"""
simulate_metrics.py
Simulates realistic performance metrics for different agents and environments
Save as: .github/scripts/simulate_metrics.py
"""

import json
import random
import argparse
import sys
from datetime import datetime

def simulate_metrics(environment, agent_type, simulate_load, include_recent_swaps=False):
    """Generate realistic performance metrics"""
    
    # Base performance metrics for different environments
    base_performance = {
        'production': {
            'memory_agent': {
                'cpu_usage': 0.65, 'memory_usage': 0.70, 'response_time_ms': 350,
                'cache_hit_rate': 0.85, 'error_rate': 0.02, 'throughput': 450
            },
            'reasoning_agent': {
                'cpu_usage': 0.70, 'memory_usage': 0.60, 'response_time_ms': 800,
                'decision_accuracy': 0.92, 'error_rate': 0.01, 'throughput': 200
            },
            'communication_system': {
                'message_throughput': 1200, 'avg_latency_ms': 45, 'queue_depth': 25,
                'message_loss_rate': 0.0005, 'connection_pool_usage': 0.60
            }
        },
        'staging': {
            'memory_agent': {
                'cpu_usage': 0.45, 'memory_usage': 0.50, 'response_time_ms': 250,
                'cache_hit_rate': 0.80, 'error_rate': 0.01, 'throughput': 200
            },
            'reasoning_agent': {
                'cpu_usage': 0.50, 'memory_usage': 0.40, 'response_time_ms': 600,
                'decision_accuracy': 0.88, 'error_rate': 0.005, 'throughput': 100
            },
            'communication_system': {
                'message_throughput': 600, 'avg_latency_ms': 30, 'queue_depth': 15,
                'message_loss_rate': 0.0002, 'connection_pool_usage': 0.40
            }
        },
        'development': {
            'memory_agent': {
                'cpu_usage': 0.25, 'memory_usage': 0.30, 'response_time_ms': 200,
                'cache_hit_rate': 0.75, 'error_rate': 0.005, 'throughput': 100
            },
            'reasoning_agent': {
                'cpu_usage': 0.30, 'memory_usage': 0.25, 'response_time_ms': 400,
                'decision_accuracy': 0.85, 'error_rate': 0.002, 'throughput': 50
            },
            'communication_system': {
                'message_throughput': 300, 'avg_latency_ms': 20, 'queue_depth': 5,
                'message_loss_rate': 0.0001, 'connection_pool_usage': 0.20
            }
        }
    }
    
    # Load condition multipliers
    load_multipliers = {
        'normal': 1.0,
        'high': 1.5,
        'critical': 2.0,
        'low': 0.7,
        'spike': 2.5
    }
    
    multiplier = load_multipliers.get(simulate_load, 1.0)
    # Add random variation (±15%)
    multiplier *= random.uniform(0.85, 1.15)
    
    # Initialize metrics structure
    metrics = {
        'timestamp': datetime.now().isoformat(),
        'environment': environment,
        'load_condition': simulate_load,
        'collection_duration_ms': random.uniform(50, 150)
    }
    
    # Determine which agents to simulate
    if agent_type == 'all':
        agent_types = ['memory_agent', 'reasoning_agent', 'communication_system']
    else:
        if agent_type == 'communication':
            agent_types = ['communication_system']
        else:
            agent_types = [f'{agent_type}_agent']
    
    # Generate metrics for each agent type
    for agent in agent_types:
        if agent in base_performance[environment]:
            base_metrics = base_performance[environment][agent].copy()
            
            # Apply load multiplier to stress-related metrics
            if 'cpu_usage' in base_metrics:
                base_metrics['cpu_usage'] = min(0.95, base_metrics['cpu_usage'] * multiplier)
            if 'memory_usage' in base_metrics:
                base_metrics['memory_usage'] = min(0.95, base_metrics['memory_usage'] * multiplier)
            if 'response_time_ms' in base_metrics:
                base_metrics['response_time_ms'] *= multiplier
            if 'error_rate' in base_metrics:
                base_metrics['error_rate'] = min(0.15, base_metrics['error_rate'] * multiplier)
            if 'avg_latency_ms' in base_metrics:
                base_metrics['avg_latency_ms'] *= multiplier
            if 'queue_depth' in base_metrics:
                base_metrics['queue_depth'] = int(base_metrics['queue_depth'] * multiplier)
            
            # Apply improvements if recent swaps were successful
            if include_recent_swaps:
                improvement_factor = 0.85  # 15% improvement
                if 'response_time_ms' in base_metrics:
                    base_metrics['response_time_ms'] *= improvement_factor
                if 'cpu_usage' in base_metrics:
                    base_metrics['cpu_usage'] *= improvement_factor
                if 'error_rate' in base_metrics:
                    base_metrics['error_rate'] *= improvement_factor
                if 'cache_hit_rate' in base_metrics:
                    base_metrics['cache_hit_rate'] = min(0.95, base_metrics['cache_hit_rate'] * 1.1)
            
            metrics[agent] = base_metrics
    
    # Add system-level metrics
    metrics['system'] = {
        'overall_cpu': random.uniform(0.4, 0.8) * multiplier,
        'overall_memory': random.uniform(0.5, 0.7) * multiplier,
        'disk_usage': random.uniform(0.3, 0.6),
        'network_utilization': random.uniform(0.2, 0.5) * multiplier,
        'active_connections': int(random.uniform(50, 150) * multiplier),
        'uptime_hours': random.uniform(24, 720)
    }
    
    return metrics

def main():
    parser = argparse.ArgumentParser(description='Simulate performance metrics for agents')
    parser.add_argument('--environment', required=True, 
                       choices=['production', 'staging', 'development'],
                       help='Target environment')
    parser.add_argument('--agent-type', required=True,
                       choices=['memory', 'reasoning', 'communication', 'all'],
                       help='Agent type to simulate')
    parser.add_argument('--output-file', required=True,
                       help='Output JSON file path')
    parser.add_argument('--simulate-load', default='normal',
                       choices=['normal', 'high', 'critical', 'low', 'spike'],
                       help='Load condition to simulate')
    parser.add_argument('--include-recent-swaps', action='store_true',
                       help='Include performance improvements from recent swaps')
    
    args = parser.parse_args()
    
    try:
        # Generate metrics
        metrics = simulate_metrics(
            args.environment, 
            args.agent_type, 
            args.simulate_load, 
            args.include_recent_swaps
        )
        
        # Save to file
        with open(args.output_file, 'w') as f:
            json.dump(metrics, f, indent=2)
        
        # Print success message
        print(f"✅ Metrics generated successfully")
        print(f"📊 Environment: {args.environment}")
        print(f"🎯 Agent type: {args.agent_type}")
        print(f"📈 Load condition: {args.simulate_load}")
        print(f"💾 Saved to: {args.output_file}")
        
        # Show sample metrics
        if args.agent_type != 'all':
            agent_key = f'{args.agent_type}_agent' if args.agent_type != 'communication' else 'communication_system'
            if agent_key in metrics:
                print(f"📋 Sample metrics for {args.agent_type}:")
                for key, value in list(metrics[agent_key].items())[:3]:
                    print(f"   {key}: {value}")
        
    except Exception as e:
        print(f"❌ Error generating metrics: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
