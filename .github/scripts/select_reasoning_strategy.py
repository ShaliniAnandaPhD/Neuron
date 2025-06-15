
"""
select_reasoning_strategy.py
Selects optimal reasoning strategy based on performance analysis
Save as: .github/scripts/select_reasoning_strategy.py
"""

import argparse
import json
import sys
from datetime import datetime

def select_optimal_strategy(analysis_data, target_performance, behavior_profile):
    """Select the optimal reasoning strategy based on analysis and requirements"""
    
    # Load analysis data
    try:
        if isinstance(analysis_data, str):
            with open(analysis_data, 'r') as f:
                analysis = json.load(f)
        else:
            analysis = analysis_data
    except Exception as e:
        print(f"⚠️ Could not load analysis data: {e}")
        analysis = {'recommended_optimization': 'balanced'}
    
    # Define strategy characteristics
    strategy_profiles = {
        'analytical': {
            'performance_score': 0.6,
            'accuracy_score': 0.95,
            'speed_score': 0.4,
            'resource_efficiency': 0.3,
            'stability_score': 0.9,
            'best_for': ['complex_analysis', 'high_accuracy_needs', 'research_tasks'],
            'trade_offs': 'High accuracy but slower response times'
        },
        'fast': {
            'performance_score': 0.95,
            'accuracy_score': 0.7,
            'speed_score': 0.95,
            'resource_efficiency': 0.8,
            'stability_score': 0.75,
            'best_for': ['real_time_decisions', 'high_volume_processing', 'user_interaction'],
            'trade_offs': 'Fast response but may sacrifice some accuracy'
        },
        'creative': {
            'performance_score': 0.7,
            'accuracy_score': 0.8,
            'speed_score': 0.6,
            'resource_efficiency': 0.6,
            'stability_score': 0.7,
            'best_for': ['problem_solving', 'innovation_tasks', 'novel_situations'],
            'trade_offs': 'Flexible and innovative but less predictable'
        },
        'reliable': {
            'performance_score': 0.65,
            'accuracy_score': 0.9,
            'speed_score': 0.5,
            'resource_efficiency': 0.9,
            'stability_score': 0.98,
            'best_for': ['production_systems', 'critical_decisions', 'consistent_results'],
            'trade_offs': 'Very stable but conservative in approach'
        }
    }
    
    # Define target performance weights based on requirements
    performance_weights = {
        'high_speed': {'speed_score': 0.4, 'performance_score': 0.3, 'accuracy_score': 0.2, 'stability_score': 0.1},
        'high_accuracy': {'accuracy_score': 0.4, 'stability_score': 0.3, 'performance_score': 0.2, 'speed_score': 0.1},
        'balanced': {'performance_score': 0.25, 'accuracy_score': 0.25, 'speed_score': 0.25, 'stability_score': 0.25},
        'resource_efficient': {'resource_efficiency': 0.4, 'stability_score': 0.3, 'performance_score': 0.2, 'speed_score': 0.1},
        'real_time': {'speed_score': 0.5, 'performance_score': 0.3, 'resource_efficiency': 0.2}
    }
    
    # Behavior profile adjustments
    behavior_adjustments = {
        'performance': {'performance_score': 1.2, 'speed_score': 1.1},
        'accuracy': {'accuracy_score': 1.2, 'stability_score': 1.1},
        'efficiency': {'resource_efficiency': 1.2, 'stability_score': 1.1},
        'innovation': {'creative': 1.3, 'analytical': 1.1},
        'stability': {'reliable': 1.3, 'analytical': 1.1}
    }
    
    # Get optimization recommendation from analysis
    optimization_type = analysis.get('recommended_optimization', 'balanced')
    current_strategy = analysis.get('current_strategy', 'analytical')
    
    # Calculate scores for each strategy
    weights = performance_weights.get(target_performance, performance_weights['balanced'])
    strategy_scores = {}
    
    for strategy_name, strategy_chars in strategy_profiles.items():
        score = 0
        total_weight = 0
        
        for metric, weight in weights.items():
            if metric in strategy_chars:
                strategy_score = strategy_chars[metric]
                
                # Apply behavior profile adjustments
                if behavior_profile in behavior_adjustments:
                    adjustments = behavior_adjustments[behavior_profile]
                    if strategy_name in adjustments:
                        strategy_score *= adjustments[strategy_name]
                    elif metric in adjustments:
                        strategy_score *= adjustments[metric]
                
                score += strategy_score * weight
                total_weight += weight
        
        strategy_scores[strategy_name] = score / total_weight if total_weight > 0 else 0
    
    # Apply optimization-specific bonuses
    optimization_bonuses = {
        'performance': {'fast': 0.15, 'analytical': -0.05},
        'efficiency': {'reliable': 0.15, 'fast': 0.10, 'analytical': -0.05},
        'accuracy': {'analytical': 0.15, 'reliable': 0.10, 'fast': -0.10},
        'stability': {'reliable': 0.20, 'analytical': 0.05, 'creative': -0.10}
    }
    
    if optimization_type in optimization_bonuses:
        for strategy, bonus in optimization_bonuses[optimization_type].items():
            if strategy in strategy_scores:
                strategy_scores[strategy] += bonus
    
    # Penalize staying with current strategy if it's underperforming
    performance_issues = analysis.get('performance_issues', [])
    if len(performance_issues) > 2 and current_strategy in strategy_scores:
        strategy_scores[current_strategy] -= 0.1
    
    # Select the best strategy
    recommended_strategy = max(strategy_scores, key=strategy_scores.get)
    confidence = strategy_scores[recommended_strategy]
    
    # Generate selection rationale
    selection_rationale = _generate_selection_rationale(
        recommended_strategy, current_strategy, optimization_type, 
        strategy_profiles[recommended_strategy], strategy_scores
    )
    
    # Create selection result
    selection_result = {
        'timestamp': datetime.now().isoformat(),
        'recommended_strategy': recommended_strategy,
        'current_strategy': current_strategy,
        'target_performance': target_performance,
        'behavior_profile': behavior_profile,
        'confidence': confidence,
        'strategy_scores': strategy_scores,
        'selection_rationale': selection_rationale,
        'strategy_characteristics': strategy_profiles[recommended_strategy],
        'expected_improvements': _calculate_expected_improvements(
            current_strategy, recommended_strategy, strategy_profiles
        ),
        'implementation_recommendations': _generate_implementation_recommendations(
            recommended_strategy, optimization_type
        )
    }
    
    return selection_result

def _generate_selection_rationale(recommended, current, optimization, strategy_chars, scores):
    """Generate human-readable rationale for strategy selection"""
    
    if recommended == current:
        return f"Current {current} strategy is optimal for {optimization} optimization requirements"
    
    score_improvement = scores[recommended] - scores.get(current, 0)
    
    rationale = f"Switching from {current} to {recommended} strategy provides {score_improvement:.2f} score improvement. "
    rationale += f"The {recommended} strategy excels in {', '.join(strategy_chars['best_for'][:2])} "
    rationale += f"which aligns with {optimization} optimization needs. "
    rationale += f"Trade-off: {strategy_chars['trade_offs']}"
    
    return rationale

def _calculate_expected_improvements(current, recommended, strategy_profiles):
    """Calculate expected improvements from strategy change"""
    
    if current == recommended:
        return {"no_change": "Strategy remains optimal"}
    
    current_profile = strategy_profiles.get(current, {})
    recommended_profile = strategy_profiles.get(recommended, {})
    
    improvements = {}
    
    for metric in ['performance_score', 'accuracy_score', 'speed_score', 'resource_efficiency', 'stability_score']:
        if metric in current_profile and metric in recommended_profile:
            current_val = current_profile[metric]
            recommended_val = recommended_profile[metric]
            improvement = ((recommended_val - current_val) / current_val) * 100
            
            if abs(improvement) > 5:  # Only report significant changes
                improvements[metric.replace('_score', '')] = f"{improvement:+.1f}%"
    
    return improvements

def _generate_implementation_recommendations(strategy, optimization):
    """Generate implementation recommendations for the selected strategy"""
    
    implementation_configs = {
        'analytical': {
            'reasoning_depth': 'deep',
            'validation_steps': 'comprehensive',
            'timeout_ms': 2000,
            'parallel_processing': False,
            'caching_strategy': 'result_based'
        },
        'fast': {
            'reasoning_depth': 'shallow',
            'validation_steps': 'minimal',
            'timeout_ms': 500,
            'parallel_processing': True,
            'caching_strategy': 'aggressive'
        },
        'creative': {
            'reasoning_depth': 'moderate',
            'validation_steps': 'adaptive',
            'timeout_ms': 1500,
            'parallel_processing': True,
            'caching_strategy': 'pattern_based'
        },
        'reliable': {
            'reasoning_depth': 'thorough',
            'validation_steps': 'extensive',
            'timeout_ms': 3000,
            'parallel_processing': False,
            'caching_strategy': 'conservative'
        }
    }
    
    base_config = implementation_configs.get(strategy, implementation_configs['analytical'])
    
    # Adjust based on optimization type
    optimization_adjustments = {
        'performance': {'timeout_ms': lambda x: x * 0.7, 'parallel_processing': True},
        'efficiency': {'timeout_ms': lambda x: x * 0.8, 'caching_strategy': 'aggressive'},
        'accuracy': {'validation_steps': 'comprehensive', 'reasoning_depth': 'deep'},
        'stability': {'validation_steps': 'extensive', 'timeout_ms': lambda x: x * 1.2}
    }
    
    config = base_config.copy()
    if optimization in optimization_adjustments:
        adjustments = optimization_adjustments[optimization]
        for key, adjustment in adjustments.items():
            if callable(adjustment):
                config[key] = int(adjustment(config[key]))
            else:
                config[key] = adjustment
    
    return config

def main():
    parser = argparse.ArgumentParser(description='Select optimal reasoning strategy')
    parser.add_argument('--analysis-file', required=True,
                       help='Path to performance analysis JSON file')
    parser.add_argument('--target-performance', default='balanced',
                       choices=['high_speed', 'high_accuracy', 'balanced', 'resource_efficient', 'real_time'],
                       help='Target performance characteristics')
    parser.add_argument('--behavior-profile', default='performance',
                       choices=['performance', 'accuracy', 'efficiency', 'innovation', 'stability'],
                       help='Desired behavior profile')
    
    args = parser.parse_args()
    
    try:
        # Select optimal strategy
        selection = select_optimal_strategy(
            args.analysis_file,
            args.target_performance,
            args.behavior_profile
        )
        
        # Save selection results
        with open('reasoning_strategy_selection.json', 'w') as f:
            json.dump(selection, f, indent=2)
        
        # Set GitHub Actions outputs
        print(f"::set-output name=recommended_strategy::{selection['recommended_strategy']}")
        print(f"::set-output name=confidence::{selection['confidence']:.2f}")
        print(f"::set-output name=strategy_changed::{str(selection['recommended_strategy'] != selection['current_strategy']).lower()}")
        
        # Display selection results
        print(f"\n🤖 Reasoning Strategy Selection Results:")
        print(f"Current Strategy: {selection['current_strategy']}")
        print(f"Recommended Strategy: {selection['recommended_strategy']}")
        print(f"Confidence: {selection['confidence']:.2f}")
        print(f"Target Performance: {args.target_performance}")
        
        if selection['recommended_strategy'] != selection['current_strategy']:
            print(f"\n📈 Expected Improvements:")
            for metric, improvement in selection['expected_improvements'].items():
                print(f"  • {metric.replace('_', ' ').title()}: {improvement}")
            
            print(f"\n💡 Rationale:")
            print(f"  {selection['selection_rationale']}")
            
            print(f"\n⚙️ Implementation Configuration:")
            for key, value in selection['implementation_recommendations'].items():
                print(f"  • {key.replace('_', ' ').title()}: {value}")
        else:
            print(f"\n✅ Current strategy is optimal for requirements")
        
        print(f"\n📊 Strategy Scores:")
        for strategy, score in sorted(selection['strategy_scores'].items(), key=lambda x: x[1], reverse=True):
            indicator = "👑" if strategy == selection['recommended_strategy'] else "  "
            print(f"  {indicator} {strategy}: {score:.3f}")
        
        print(f"\n✅ Reasoning strategy selection completed")
        
    except Exception as e:
        print(f"❌ Error during strategy selection: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
