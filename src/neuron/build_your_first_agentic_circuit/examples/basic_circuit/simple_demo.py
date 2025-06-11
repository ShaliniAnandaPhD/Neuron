
"""
Neuron Framework: Simple Working Demoy

A complete working example demonstrating the Neuron framework with:
- 3 DeliberativeAgents working together
- SynapticBus message routing
- Working memory systems
- Basic Kotler flow optimization simulation
"""

import asyncio
import logging
import time
import json
from typing import Dict, Any

# Import Neuron framework components
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from neuron.core.messaging import SynapticBus, RoutingRule, RoutingStrategy
from neuron.core.base import Message, MessageType, MessagePriority, AgentCapabilities, MemoryType
from neuron.agents.deliberative_agent import DeliberativeAgent, create_kotler_agent
from neuron.memory.working import WorkingMemory

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# =====================================
# Demo Configuration
# =====================================

DEMO_CONFIG = {
    'agents': {
        'cognitive_detector': {
            'capabilities': ['flow_detection', 'pattern_analysis', 'user_assessment'],
            'memory_size': 300,
            'confidence_threshold': 0.75
        },
        'memory_controller': {
            'capabilities': ['memory_management', 'context_retrieval', 'experience_storage'],
            'memory_size': 500,
            'confidence_threshold': 0.70
        },
        'decision_engine': {
            'capabilities': ['decision_making', 'optimization', 'intervention_planning'],
            'memory_size': 200,
            'confidence_threshold': 0.80
        }
    },
    'demo_scenarios': [
        {
            'name': 'Basic Flow Analysis',
            'user_profile': {'stress': 3, 'challenge': 7, 'skill': 5, 'focus': 6},
            'expected_flow': 0.65
        },
        {
            'name': 'High Stress Scenario',
            'user_profile': {'stress': 8, 'challenge': 6, 'skill': 7, 'focus': 3},
            'expected_flow': 0.45
        },
        {
            'name': 'Optimal Flow State',
            'user_profile': {'stress': 2, 'challenge': 8, 'skill': 8, 'focus': 9},
            'expected_flow': 0.90
        }
    ]
}

# =====================================
# Demo Circuit Class
# =====================================

class SimpleNeuroCircuit:
    """
    A simple neural circuit demonstrating Neuron framework capabilities
    
    This circuit consists of 3 agents working together to analyze and optimize
    user flow states using the Kotler flow model.
    """
    
    def __init__(self):
        self.synaptic_bus = SynapticBus()
        self.agents = {}
        self.is_running = False
        
        # Statistics
        self.demo_stats = {
            'messages_sent': 0,
            'successful_optimizations': 0,
            'total_scenarios': 0,
            'average_flow_improvement': 0.0
        }
    
    async def initialize(self):
        """Initialize the circuit with agents and routing"""
        logger.info("🚀 Initializing Simple Neuro Circuit...")
        
        # Create agents
        await self._create_agents()
        
        # Setup routing rules
        await self._setup_routing()
        
        # Start the synaptic bus
        self.synaptic_bus.start(num_workers=2)
        
        # Start all agents
        for agent in self.agents.values():
            await agent.start()
        
        self.is_running = True
        logger.info("✅ Simple Neuro Circuit initialized and running!")
    
    async def _create_agents(self):
        """Create and configure the agents"""
        
        # Cognitive Detector - Analyzes user state and flow patterns
        cognitive_detector = DeliberativeAgent(
            agent_id="cognitive_detector",
            capabilities=AgentCapabilities(
                capabilities=set(DEMO_CONFIG['agents']['cognitive_detector']['capabilities']),
                memory_types={MemoryType.WORKING, MemoryType.EPISODIC}
            ),
            config={
                'confidence_threshold': DEMO_CONFIG['agents']['cognitive_detector']['confidence_threshold'],
                'working_memory_size': DEMO_CONFIG['agents']['cognitive_detector']['memory_size']
            }
        )
        
        # Memory Controller - Manages information storage and retrieval
        memory_controller = DeliberativeAgent(
            agent_id="memory_controller",
            capabilities=AgentCapabilities(
                capabilities=set(DEMO_CONFIG['agents']['memory_controller']['capabilities']),
                memory_types={MemoryType.WORKING, MemoryType.EPISODIC, MemoryType.SEMANTIC}
            ),
            config={
                'confidence_threshold': DEMO_CONFIG['agents']['memory_controller']['confidence_threshold'],
                'working_memory_size': DEMO_CONFIG['agents']['memory_controller']['memory_size']
            }
        )
        
        # Decision Engine - Makes optimization decisions and creates intervention plans
        decision_engine = DeliberativeAgent(
            agent_id="decision_engine", 
            capabilities=AgentCapabilities(
                capabilities=set(DEMO_CONFIG['agents']['decision_engine']['capabilities']),
                memory_types={MemoryType.WORKING, MemoryType.PROCEDURAL}
            ),
            config={
                'confidence_threshold': DEMO_CONFIG['agents']['decision_engine']['confidence_threshold'],
                'working_memory_size': DEMO_CONFIG['agents']['decision_engine']['memory_size']
            }
        )
        
        # Register agents
        self.agents['cognitive_detector'] = cognitive_detector
        self.agents['memory_controller'] = memory_controller
        self.agents['decision_engine'] = decision_engine
        
        # Register with synaptic bus
        for agent in self.agents.values():
            self.synaptic_bus.register_agent(agent)
        
        logger.info(f"Created {len(self.agents)} agents: {list(self.agents.keys())}")
    
    async def _setup_routing(self):
        """Setup routing rules for the circuit"""
        
        # Rule 1: Flow analysis requests go to cognitive detector
        flow_analysis_rule = RoutingRule(
            pattern={'content_key': 'flow_analysis'},
            strategy=RoutingStrategy.CAPABILITY_BASED,
            required_capabilities={'flow_detection', 'pattern_analysis'}
        )
        self.synaptic_bus.add_routing_rule(flow_analysis_rule)
        
        # Rule 2: Memory requests go to memory controller
        memory_rule = RoutingRule(
            pattern={'content_key': 'memory_operation'},
            strategy=RoutingStrategy.CAPABILITY_BASED,
            required_capabilities={'memory_management'}
        )
        self.synaptic_bus.add_routing_rule(memory_rule)
        
        # Rule 3: Decision requests go to decision engine
        decision_rule = RoutingRule(
            pattern={'content_key': 'decision_request'},
            strategy=RoutingStrategy.CAPABILITY_BASED,
            required_capabilities={'decision_making', 'optimization'}
        )
        self.synaptic_bus.add_routing_rule(decision_rule)
        
        # Rule 4: High priority messages get boosted
        priority_rule = RoutingRule(
            pattern={'type': 'request'},
            strategy=RoutingStrategy.DIRECT,
            priority_boost=1
        )
        self.synaptic_bus.add_routing_rule(priority_rule)
        
        logger.info("✅ Routing rules configured")
    
    async def process_flow_scenario(self, scenario: Dict[str, Any]) -> Dict[str, Any]:
        """Process a complete flow optimization scenario"""
        scenario_name = scenario['name']
        user_profile = scenario['user_profile']
        expected_flow = scenario['expected_flow']
        
        logger.info(f"\n🎯 Processing scenario: {scenario_name}")
        logger.info(f"   User Profile: {user_profile}")
        logger.info(f"   Expected Flow: {expected_flow}")
        
        results = {
            'scenario_name': scenario_name,
            'user_profile': user_profile,
            'expected_flow': expected_flow,
            'steps': [],
            'messages_exchanged': 0,
            'final_flow': 0.0,
            'improvement': 0.0,
            'success': False
        }
        
        try:
            # Step 1: Flow Analysis by Cognitive Detector
            step1_result = await self._step1_flow_analysis(user_profile)
            results['steps'].append(step1_result)
            results['messages_exchanged'] += step1_result.get('messages', 0)
            
            if not step1_result['success']:
                return results
            
            current_flow = step1_result['current_flow']
            
            # Step 2: Memory Storage and Context Retrieval
            step2_result = await self._step2_memory_operations(user_profile, current_flow)
            results['steps'].append(step2_result)
            results['messages_exchanged'] += step2_result.get('messages', 0)
            
            # Step 3: Decision Making and Optimization
            step3_result = await self._step3_optimization_decision(user_profile, current_flow, step2_result.get('context', {}))
            results['steps'].append(step3_result)
            results['messages_exchanged'] += step3_result.get('messages', 0)
            
            if step3_result['success']:
                results['final_flow'] = step3_result['optimized_flow']
                results['improvement'] = results['final_flow'] - current_flow
                results['success'] = True
                
                # Update statistics
                self.demo_stats['successful_optimizations'] += 1
            
            self.demo_stats['messages_sent'] += results['messages_exchanged']
            
            return results
            
        except Exception as e:
            logger.error(f"Error processing scenario {scenario_name}: {e}")
            results['error'] = str(e)
            return results
    
    async def _step1_flow_analysis(self, user_profile: Dict[str, Any]) -> Dict[str, Any]:
        """Step 1: Analyze current flow state"""
        logger.info("   📊 Step 1: Flow Analysis")
        
        try:
            # Create flow analysis request
            flow_request = Message(
                type=MessageType.REQUEST,
                priority=MessagePriority.HIGH,
                sender_id="demo_controller",
                recipient_id="cognitive_detector",
                content={
                    'type': 'reasoning_request',
                    'problem': f"Analyze flow state for user profile: {user_profile}",
                    'flow_analysis': True,
                    'user_profile': user_profile,
                    'strategy': 'multi_criteria',
                    'context': {
                        'analysis_type': 'kotler_flow',
                        'metrics': ['challenge', 'skill', 'stress', 'focus']
                    }
                }
            )
            
            # Send request and wait for response
            await self.synaptic_bus.route_message(flow_request)
            
            # Simulate response processing (in real implementation, would wait for actual response)
            await asyncio.sleep(0.5)
            
            # Calculate current flow based on Kotler model (simplified)
            challenge = user_profile.get('challenge', 5)
            skill = user_profile.get('skill', 5)
            stress = user_profile.get('stress', 5)
            focus = user_profile.get('focus', 5)
            
            # Flow = (skill/challenge balance) * focus_factor * (1 - stress_factor)
            skill_challenge_ratio = min(skill / max(challenge, 1), 2.0)
            focus_factor = focus / 10.0
            stress_factor = stress / 15.0  # Reduce stress impact
            
            current_flow = skill_challenge_ratio * focus_factor * (1 - stress_factor)
            current_flow = max(0.1, min(0.95, current_flow))  # Clamp to reasonable range
            
            logger.info(f"      ✅ Current flow calculated: {current_flow:.2f}")
            
            return {
                'step': 'flow_analysis',
                'success': True,
                'current_flow': current_flow,
                'analysis_details': {
                    'skill_challenge_ratio': skill_challenge_ratio,
                    'focus_factor': focus_factor,
                    'stress_factor': stress_factor
                },
                'messages': 1,
                'confidence': 0.85
            }
            
        except Exception as e:
            logger.error(f"Flow analysis error: {e}")
            return {
                'step': 'flow_analysis',
                'success': False,
                'error': str(e),
                'messages': 1
            }
    
    async def _step2_memory_operations(self, user_profile: Dict[str, Any], current_flow: float) -> Dict[str, Any]:
        """Step 2: Store current state and retrieve relevant context"""
        logger.info("   🧠 Step 2: Memory Operations")
        
        try:
            # Create memory storage request
            memory_request = Message(
                type=MessageType.REQUEST,
                priority=MessagePriority.NORMAL,
                sender_id="demo_controller",
                recipient_id="memory_controller",
                content={
                    'type': 'reasoning_request',
                    'problem': f"Store and retrieve flow context for optimization",
                    'memory_operation': True,
                    'operations': [
                        {
                            'type': 'store',
                            'key': f"flow_state_{int(time.time())}",
                            'data': {
                                'user_profile': user_profile,
                                'current_flow': current_flow,
                                'timestamp': time.time()
                            }
                        },
                        {
                            'type': 'search',
                            'query': {'key_pattern': 'flow_state'}
                        }
                    ]
                }
            )
            
            # Send request
            await self.synaptic_bus.route_message(memory_request)
            await asyncio.sleep(0.3)
            
            # Simulate retrieving similar past cases
            similar_profiles = [
                {'stress': 4, 'challenge': 6, 'skill': 5, 'focus': 7, 'past_flow': 0.68},
                {'stress': 3, 'challenge': 7, 'skill': 6, 'focus': 6, 'past_flow': 0.72}
            ]
            
            # Calculate context relevance
            context_strength = 0.7 if similar_profiles else 0.3
            
            logger.info(f"      ✅ Memory operations completed, context strength: {context_strength:.2f}")
            
            return {
                'step': 'memory_operations',
                'success': True,
                'context': {
                    'similar_cases': len(similar_profiles),
                    'historical_data': similar_profiles,
                    'context_strength': context_strength
                },
                'messages': 1,
                'confidence': 0.80
            }
            
        except Exception as e:
            logger.error(f"Memory operations error: {e}")
            return {
                'step': 'memory_operations',
                'success': False,
                'error': str(e),
                'messages': 1
            }
    
    async def _step3_optimization_decision(self, user_profile: Dict[str, Any], 
                                         current_flow: float, context: Dict[str, Any]) -> Dict[str, Any]:
        """Step 3: Make optimization decisions and calculate improved flow"""
        logger.info("   🎯 Step 3: Optimization Decision")
        
        try:
            # Create decision request
            decision_request = Message(
                type=MessageType.REQUEST,
                priority=MessagePriority.HIGH,
                sender_id="demo_controller",
                recipient_id="decision_engine",
                content={
                    'type': 'decision_request',
                    'decision_request': True,
                    'problem': f"Optimize flow from {current_flow:.2f} for user profile",
                    'options': [
                        {
                            'name': 'reduce_challenge',
                            'description': 'Lower task difficulty to match skill level',
                            'feasibility': 0.8,
                            'effectiveness': 0.7
                        },
                        {
                            'name': 'enhance_skills',
                            'description': 'Provide skill-building interventions',
                            'feasibility': 0.6,
                            'effectiveness': 0.9
                        },
                        {
                            'name': 'stress_reduction',
                            'description': 'Apply stress reduction techniques',
                            'feasibility': 0.9,
                            'effectiveness': 0.6
                        },
                        {
                            'name': 'focus_enhancement',
                            'description': 'Improve attention and concentration',
                            'feasibility': 0.7,
                            'effectiveness': 0.8
                        }
                    ],
                    'criteria': {
                        'feasibility': 0.4,
                        'effectiveness': 0.6
                    },
                    'context': context,
                    'current_flow': current_flow,
                    'user_profile': user_profile
                }
            )
            
            # Send request
            await self.synaptic_bus.route_message(decision_request)
            await asyncio.sleep(0.4)
            
            # Simulate optimization decision making
            stress = user_profile.get('stress', 5)
            challenge = user_profile.get('challenge', 5)
            skill = user_profile.get('skill', 5)
            focus = user_profile.get('focus', 5)
            
            # Determine best intervention based on user profile
            optimization_strategy = None
            flow_improvement = 0.0
            
            if stress > 7:
                optimization_strategy = 'stress_reduction'
                flow_improvement = 0.15
            elif abs(challenge - skill) > 2:
                if challenge > skill:
                    optimization_strategy = 'enhance_skills'
                    flow_improvement = 0.20
                else:
                    optimization_strategy = 'reduce_challenge'
                    flow_improvement = 0.12
            elif focus < 5:
                optimization_strategy = 'focus_enhancement'
                flow_improvement = 0.18
            else:
                optimization_strategy = 'enhance_skills'
                flow_improvement = 0.10
            
            # Apply context boost
            context_boost = context.get('context_strength', 0.5) * 0.05
            flow_improvement += context_boost
            
            # Calculate optimized flow
            optimized_flow = min(0.95, current_flow + flow_improvement)
            
            logger.info(f"      ✅ Strategy: {optimization_strategy}, Flow: {current_flow:.2f} → {optimized_flow:.2f}")
            
            return {
                'step': 'optimization_decision',
                'success': True,
                'strategy': optimization_strategy,
                'optimized_flow': optimized_flow,
                'improvement': flow_improvement,
                'confidence': 0.88,
                'messages': 1,
                'intervention_details': {
                    'target_factor': self._identify_limiting_factor(user_profile),
                    'expected_timeline': '5-10 minutes',
                    'sustainability': 'high'
                }
            }
            
        except Exception as e:
            logger.error(f"Optimization decision error: {e}")
            return {
                'step': 'optimization_decision',
                'success': False,
                'error': str(e),
                'messages': 1
            }
    
    def _identify_limiting_factor(self, user_profile: Dict[str, Any]) -> str:
        """Identify the primary factor limiting flow"""
        stress = user_profile.get('stress', 5)
        challenge = user_profile.get('challenge', 5)
        skill = user_profile.get('skill', 5)
        focus = user_profile.get('focus', 5)
        
        factors = {
            'stress': stress,
            'skill_challenge_mismatch': abs(challenge - skill),
            'focus': 10 - focus  # Invert so higher = more limiting
        }
        
        limiting_factor = max(factors, key=factors.get)
        return limiting_factor
    
    async def run_demo(self):
        """Run the complete demonstration"""
        logger.info("\n🚀 Starting Neuron Framework Demo")
        logger.info("="*60)
        
        if not self.is_running:
            await self.initialize()
        
        # Process each scenario
        all_results = []
        
        for i, scenario in enumerate(DEMO_CONFIG['demo_scenarios'], 1):
            logger.info(f"\n📋 Scenario {i}/{len(DEMO_CONFIG['demo_scenarios'])}")
            result = await self.process_flow_scenario(scenario)
            all_results.append(result)
            
            self.demo_stats['total_scenarios'] += 1
            
            # Display results
            self._display_scenario_results(result)
            
            # Brief pause between scenarios
            await asyncio.sleep(1.0)
        
        # Display final summary
        await self._display_demo_summary(all_results)
        
        return all_results
    
    def _display_scenario_results(self, result: Dict[str, Any]):
        """Display results for a single scenario"""
        success_icon = "✅" if result['success'] else "❌"
        
        logger.info(f"\n   {success_icon} Results for {result['scenario_name']}:")
        logger.info(f"      Expected Flow: {result['expected_flow']:.2f}")
        
        if result['success']:
            logger.info(f"      Final Flow:    {result['final_flow']:.2f}")
            logger.info(f"      Improvement:   +{result['improvement']:.2f}")
            logger.info(f"      Messages:      {result['messages_exchanged']}")
            
            # Show optimization strategy
            if result['steps'] and len(result['steps']) > 2:
                strategy = result['steps'][2].get('strategy', 'unknown')
                logger.info(f"      Strategy:      {strategy}")
        else:
            logger.info(f"      Status:        Failed")
            if 'error' in result:
                logger.info(f"      Error:         {result['error']}")
    
    async def _display_demo_summary(self, all_results: List[Dict[str, Any]]):
        """Display comprehensive demo summary"""
        logger.info("\n" + "="*60)
        logger.info("🎉 DEMO SUMMARY")
        logger.info("="*60)
        
        # Calculate statistics
        successful_scenarios = [r for r in all_results if r['success']]
        total_improvement = sum(r.get('improvement', 0) for r in successful_scenarios)
        avg_improvement = total_improvement / len(successful_scenarios) if successful_scenarios else 0
        
        self.demo_stats['average_flow_improvement'] = avg_improvement
        
        # Display overall stats
        logger.info(f"📊 Overall Performance:")
        logger.info(f"   • Scenarios Processed:     {len(all_results)}")
        logger.info(f"   • Successful Optimizations: {len(successful_scenarios)}")
        logger.info(f"   • Success Rate:            {len(successful_scenarios)/len(all_results)*100:.1f}%")
        logger.info(f"   • Average Flow Improvement: +{avg_improvement:.3f}")
        logger.info(f"   • Total Messages Sent:     {self.demo_stats['messages_sent']}")
        
        # Display agent performance
        agent_stats = await self._get_agent_statistics()
        logger.info(f"\n🤖 Agent Performance:")
        for agent_id, stats in agent_stats.items():
            logger.info(f"   • {agent_id}:")
            logger.info(f"     - Messages Processed: {stats['messages_processed']}")
            logger.info(f"     - Average Response:   {stats['avg_response_time']:.3f}s")
            logger.info(f"     - Confidence Score:   {stats['confidence']:.2f}")
        
        # Display system health
        bus_stats = self.synaptic_bus.get_statistics()
        logger.info(f"\n📡 System Health:")
        logger.info(f"   • Message Success Rate:    {bus_stats['success_rate']:.1f}%")
        logger.info(f"   • Average Message Latency: {bus_stats['average_latency']:.3f}s")
        logger.info(f"   • Queue Size:              {bus_stats['queue_size']}")
        logger.info(f"   • Healthy Agents:          {bus_stats['healthy_agents']}/{bus_stats['registered_agents']}")
        
        # Show best performing scenario
        if successful_scenarios:
            best_scenario = max(successful_scenarios, key=lambda x: x['improvement'])
            logger.info(f"\n🏆 Best Performance:")
            logger.info(f"   • Scenario: {best_scenario['scenario_name']}")
            logger.info(f"   • Improvement: +{best_scenario['improvement']:.3f}")
            logger.info(f"   • Final Flow: {best_scenario['final_flow']:.3f}")
        
        logger.info("\n✨ Demo completed successfully!")
    
    async def _get_agent_statistics(self) -> Dict[str, Dict[str, Any]]:
        """Get performance statistics for all agents"""
        stats = {}
        
        for agent_id, agent in self.agents.items():
            agent_metrics = agent.metrics
            stats[agent_id] = {
                'messages_processed': agent_metrics.messages_processed,
                'messages_sent': agent_metrics.messages_sent,
                'avg_response_time': agent_metrics.average_response_time,
                'confidence': agent_metrics.confidence_score,
                'uptime': agent_metrics.get_uptime(),
                'errors': agent_metrics.errors_count
            }
        
        return stats
    
    async def shutdown(self):
        """Gracefully shutdown the circuit"""
        logger.info("🔽 Shutting down Simple Neuro Circuit...")
        
        # Stop all agents
        for agent in self.agents.values():
            await agent.stop()
        
        # Stop synaptic bus
        self.synaptic_bus.stop()
        
        self.is_running = False
        logger.info("✅ Shutdown complete")

# =====================================
# Standalone Demo Functions
# =====================================

async def run_basic_demo():
    """Run the basic demonstration"""
    circuit = SimpleNeuroCircuit()
    
    try:
        results = await circuit.run_demo()
        return results
    except KeyboardInterrupt:
        logger.info("\n⏹️  Demo interrupted by user")
    except Exception as e:
        logger.error(f"Demo error: {e}")
    finally:
        await circuit.shutdown()

async def run_interactive_demo():
    """Run an interactive demonstration where user can input their own profile"""
    circuit = SimpleNeuroCircuit()
    
    try:
        await circuit.initialize()
        
        print("\n🎯 INTERACTIVE NEURON DEMO")
        print("="*40)
        
        while True:
            print("\nEnter your current state (1-10 scale):")
            
            try:
                stress = int(input("Stress level (1=calm, 10=very stressed): ") or "5")
                challenge = int(input("Challenge level (1=easy, 10=very hard): ") or "5")
                skill = int(input("Skill level (1=beginner, 10=expert): ") or "5")
                focus = int(input("Focus level (1=distracted, 10=laser focused): ") or "5")
                
                # Validate inputs
                for val, name in [(stress, 'stress'), (challenge, 'challenge'), 
                                (skill, 'skill'), (focus, 'focus')]:
                    if not 1 <= val <= 10:
                        print(f"❌ {name} must be between 1 and 10")
                        continue
                
                # Create custom scenario
                custom_scenario = {
                    'name': 'Interactive User Session',
                    'user_profile': {
                        'stress': stress,
                        'challenge': challenge,
                        'skill': skill,
                        'focus': focus
                    },
                    'expected_flow': (skill/challenge) * (focus/10) * (1 - stress/15)
                }
                
                # Process the scenario
                result = await circuit.process_flow_scenario(custom_scenario)
                
                # Display results
                print(f"\n📊 ANALYSIS RESULTS:")
                print(f"   Current Flow State: {result.get('final_flow', 0):.2f}")
                
                if result['success'] and len(result['steps']) > 2:
                    strategy = result['steps'][2].get('strategy', 'unknown')
                    improvement = result.get('improvement', 0)
                    print(f"   Recommended Strategy: {strategy}")
                    print(f"   Expected Improvement: +{improvement:.2f}")
                    
                    # Provide user-friendly interpretation
                    if result['final_flow'] >= 0.8:
                        print("   🌟 Excellent flow state!")
                    elif result['final_flow'] >= 0.6:
                        print("   ✅ Good flow state with room for improvement")
                    else:
                        print("   ⚠️  Flow state needs attention")
                
                # Ask if user wants to continue
                continue_demo = input("\nAnalyze another state? (y/n): ").lower().strip()
                if continue_demo not in ['y', 'yes']:
                    break
                    
            except ValueError:
                print("❌ Please enter valid numbers")
            except KeyboardInterrupt:
                print("\n⏹️  Demo interrupted")
                break
    
    except Exception as e:
        logger.error(f"Interactive demo error: {e}")
    finally:
        await circuit.shutdown()

# =====================================
# Main Entry Point
# =====================================

def main():
    """Main entry point for the demo"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Neuron Framework Simple Demo")
    parser.add_argument(
        '--mode', 
        choices=['basic', 'interactive'], 
        default='basic',
        help='Demo mode: basic (predefined scenarios) or interactive (user input)'
    )
    parser.add_argument(
        '--verbose', 
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    print("🧠 Neuron Framework - Simple Working Demo")
    print("This demo shows a 3-agent circuit optimizing Kotler flow states")
    print()
    
    if args.mode == 'interactive':
        asyncio.run(run_interactive_demo())
    else:
        asyncio.run(run_basic_demo())

if __name__ == "__main__":
    main()
