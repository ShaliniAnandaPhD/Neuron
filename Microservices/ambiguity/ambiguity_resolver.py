# microservices/ambiguity/ambiguity_resolver.py

from typing import Dict, Any, List, Optional, Tuple, Union
import json
import re
import uuid
import os
import logging
from datetime import datetime

from neuron.agent import DeliberativeAgent, ReflexAgent
from neuron.circuit_designer import CircuitDefinition
from neuron.types import AgentType, ConnectionType
from neuron.memory import Memory, MemoryType
from ..base_microservice import BaseMicroservice

class ToneAgent(DeliberativeAgent):
    """Agent for analyzing the tone of user messages."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.politeness_markers = self._init_politeness_markers()
        self.urgency_markers = self._init_urgency_markers()
        
    def _init_politeness_markers(self):
        """Initialize politeness marker patterns."""
        return {
            "hedges": [
                r"\bjust\b", r"\bperhaps\b", r"\bmaybe\b", r"\bpossibly\b",
                r"\bi think\b", r"\bi guess\b", r"\bsort of\b", r"\bkind of\b",
                r"\bsomewhat\b", r"\ba bit\b", r"\ba little\b", r"\bwonder if\b"
            ],
            "subjunctives": [
                r"\bcould you\b", r"\bwould you\b", r"\bmight you\b",
                r"\bwould it be possible\b", r"\bcould it be possible\b"
            ],
            "politeness_markers": [
                r"\bplease\b", r"\bthanks\b", r"\bthank you\b", r"\bappreciate\b",
                r"\bgrateful\b", r"\bwould be great\b", r"\bwould be helpful\b"
            ],
            "apologies": [
                r"\bsorry\b", r"\bapologies\b", r"\bexcuse me\b", r"\bpardon\b"
            ],
            "minimizers": [
                r"\bsmall\b", r"\bquick\b", r"\bjust a moment\b", r"\bbrief\b",
                r"\btiny\b", r"\blittle\b", r"\bminor\b"
            ]
        }
    
    def _init_urgency_markers(self):
        """Initialize urgency marker patterns."""
        return {
            "time_constraints": [
                r"\basap\b", r"\burgent\b", r"\bimmediately\b", r"\bquickly\b",
                r"\bas soon as\b", r"\bright away\b", r"\bnow\b", r"\bemergency\b",
                r"\bdeadline\b", r"\btoday\b", r"\btomorrow\b", r"\bwithin\s+\d+\s+(?:hour|minute|day|week)s?\b"
            ],
            "consequences": [
                r"\bimportant\b", r"\bcritical\b", r"\bcrucial\b", r"\bvital\b",
                r"\bessential\b", r"\bsignificant\b", r"\bserious\b"
            ],
            "escalation": [
                r"\bescalate\b", r"\bmanager\b", r"\bsupervisor\b", r"\bcomplaint\b",
                r"\bdissatisfied\b", r"\bunhappy\b", r"\bfrustrated\b", r"\bangry\b",
                r"\bannoy\b", r"\bdisappoint\b"
            ],
            "repeats": [
                r"\bagain\b", r"\brepeat\b", r"\balready\b", r"\bstill\b",
                r"\bnot working\b", r"\bstill not\b", r"\bonce more\b"
            ]
        }
    
    async def process_message(self, message):
        """Process a message to analyze its tone."""
        content = message.content
        query = content.get("query", "")
        
        # Analyze tone and politeness
        tone_analysis = await self._analyze_tone(query)
        
        # Send results to next agent
        await self.send_message(
            recipients=[message.metadata.get("next_agent", "intent_resolver")],
            content={
                "query": query,
                "tone_analysis": tone_analysis
            }
        )
    
    async def _analyze_tone(self, text):
        """Analyze the tone of a text message."""
        analysis = {
            "politeness_score": 0.0,
            "urgency_score": 0.0,
            "detected_patterns": {
                "politeness": [],
                "urgency": []
            },
            "tone_masking_detected": False
        }
        
        # Count politeness markers
        politeness_count = 0
        for category, patterns in self.politeness_markers.items():
            detected = []
            for pattern in patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                if matches:
                    detected.extend(matches)
                    politeness_count += len(matches)
            
            if detected:
                analysis["detected_patterns"]["politeness"].append({
                    "category": category,
                    "instances": detected
                })
        
        # Count urgency markers
        urgency_count = 0
        for category, patterns in self.urgency_markers.items():
            detected = []
            for pattern in patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                if matches:
                    detected.extend(matches)
                    urgency_count += len(matches)
            
            if detected:
                analysis["detected_patterns"]["urgency"].append({
                    "category": category,
                    "instances": detected
                })
        
        # Calculate scores
        text_length = len(text.split())
        politeness_factor = 1.0 if text_length < 10 else min(20.0, text_length) / 20.0
        
        analysis["politeness_score"] = min(1.0, politeness_count / (5.0 * politeness_factor))
        analysis["urgency_score"] = min(1.0, urgency_count / (3.0 * politeness_factor))
        
        # Detect tone masking (high politeness with underlying urgency)
        if analysis["politeness_score"] > 0.6 and analysis["urgency_score"] > 0.3:
            analysis["tone_masking_detected"] = True
        
        return analysis


class UrgencyScorer(DeliberativeAgent):
    """Agent for scoring the true urgency of user requests."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.urgency_factors = {
            "tone_multiplier": 1.5,
            "intent_multiplier": 1.2,
            "ambiguity_penalty": 0.8,
            "base_intent_urgency": {
                "report_problem": 0.7,
                "account_issue": 0.6,
                "billing_issue": 0.8,
                "request_help": 0.5,
                "request_feature": 0.3,
                "general_inquiry": 0.2
            }
        }
    
    async def process_message(self, message):
        """Process a message to calculate its true urgency score."""
        content = message.content
        query = content.get("query", "")
        tone_analysis = content.get("tone_analysis", {})
        intent_analysis = content.get("intent_analysis", {})
        
        # Calculate true urgency score
        urgency_analysis = await self._calculate_urgency(query, tone_analysis, intent_analysis)
        
        # Create final resolution
        resolution = {
            "query": query,
            "tone_analysis": tone_analysis,
            "intent_analysis": intent_analysis,
            "urgency_analysis": urgency_analysis,
            "final_resolution": await self._create_final_resolution(tone_analysis, intent_analysis, urgency_analysis)
        }
        
        # Send results to the output agent
        await self.send_message(
            recipients=[message.metadata.get("output_agent", "output")],
            content=resolution
        )
    
    async def _calculate_urgency(self, query, tone_analysis, intent_analysis):
        """Calculate true urgency score based on tone and intent analysis."""
        urgency_analysis = {
            "explicit_urgency": tone_analysis.get("urgency_score", 0.0),
            "implied_urgency": 0.0,
            "intent_based_urgency": 0.0,
            "true_urgency": 0.0,
            "urgency_mismatch": False
        }
        
        # Calculate intent-based urgency
        primary_intent = intent_analysis.get("primary_intent", "general_inquiry")
        base_urgency = self.urgency_factors["base_intent_urgency"].get(primary_intent, 0.2)
        intent_confidence = intent_analysis.get("intent_confidence", 0.5)
        
        intent_urgency = base_urgency * intent_confidence * self.urgency_factors["intent_multiplier"]
        urgency_analysis["intent_based_urgency"] = min(1.0, intent_urgency)
        
        # Calculate implied urgency based on tone + intent
        implied_urgency = 0.0
        
        if intent_analysis.get("implied_urgency", False):
            implied_urgency = max(0.4, urgency_analysis["intent_based_urgency"])
            
            if tone_analysis.get("tone_masking_detected", False):
                politeness_score = tone_analysis.get("politeness_score", 0.0)
                # Higher politeness with masked urgency increases implied urgency
                implied_urgency *= (1.0 + (politeness_score * 0.5))
        
        urgency_analysis["implied_urgency"] = min(1.0, implied_urgency)
        
        # Apply ambiguity penalty if needed
        ambiguity_level = intent_analysis.get("ambiguity_level", 0.0)
        ambiguity_factor = 1.0 - (ambiguity_level * self.urgency_factors["ambiguity_penalty"])
        
        # Calculate true urgency
        explicit_urgency = urgency_analysis["explicit_urgency"]
        implied_urgency = urgency_analysis["implied_urgency"]
        intent_urgency = urgency_analysis["intent_based_urgency"]
        
        # True urgency considers both explicit and implied, with higher weight to implied
        true_urgency = max(
            explicit_urgency,
            implied_urgency * 0.8 + intent_urgency * 0.2
        ) * ambiguity_factor
        
        urgency_analysis["true_urgency"] = min(1.0, true_urgency)
        
        # Detect urgency mismatch
        if implied_urgency > explicit_urgency + 0.3:
            urgency_analysis["urgency_mismatch"] = True
        
        return urgency_analysis
    
    async def _create_final_resolution(self, tone_analysis, intent_analysis, urgency_analysis):
        """Create a final resolution based on all analyses."""
        primary_intent = intent_analysis.get("primary_intent", "general_inquiry")
        true_urgency = urgency_analysis.get("true_urgency", 0.0)
        urgency_mismatch = urgency_analysis.get("urgency_mismatch", False)
        
        # Determine urgency level
        urgency_level = "low"
        if true_urgency > 0.7:
            urgency_level = "high"
        elif true_urgency > 0.4:
            urgency_level = "medium"
        
        # Determine if tone masking was detected
        tone_masking = tone_analysis.get("tone_masking_detected", False)
        
        return {
            "resolved_intent": primary_intent,
            "resolved_urgency_level": urgency_level,
            "resolved_urgency_score": true_urgency,
            "tone_masking_detected": tone_masking,
            "urgency_mismatch_detected": urgency_mismatch,
            "confidence": intent_analysis.get("intent_confidence", 0.0),
            "timestamp": datetime.now().isoformat()
        }


class OutputAgent(ReflexAgent):
    """Output agent that formats and logs the final resolution."""
    
    async def process_message(self, message):
        """Process the final resolution and format the output."""
        resolution = message.content
        
        # Log the resolution
        log_path = os.path.join("logs", f"resolution_{datetime.now().strftime('%Y%m%d%H%M%S')}.json")
        os.makedirs("logs", exist_ok=True)
        
        with open(log_path, "w") as f:
            json.dump(resolution, f, indent=2)
        
        self.logger.info(f"Resolution logged to {log_path}")
        
        # Create a formatted output
        output = {
            "original_query": resolution.get("query", ""),
            "resolution": resolution.get("final_resolution", {}),
            "resolution_id": str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat()
        }
        
        return output


class AmbiguityResolverMicroservice(BaseMicroservice):
    """Microservice for resolving ambiguity in user messages."""
    
    def _initialize(self):
        """Initialize the ambiguity resolver agents."""
        self.agents = {
            "tone_agent": ToneAgent(name="Tone Analysis Agent"),
            "intent_resolver": IntentResolver(name="Intent Resolution Agent"),
            "urgency_scorer": UrgencyScorer(name="Urgency Scoring Agent"),
            "output": OutputAgent(name="Output Agent")
        }
    
    def get_circuit_definition(self):
        """Get the circuit definition for ambiguity resolution."""
        return CircuitDefinition.create(
            name=f"{self.name} Circuit",
            description=self.description or "Ambiguity resolution pipeline",
            agents={
                "tone_agent": {
                    "type": "ToneAgent",
                    "instance": self.agents["tone_agent"]
                },
                "intent_resolver": {
                    "type": "IntentResolver",
                    "instance": self.agents["intent_resolver"]
                },
                "urgency_scorer": {
                    "type": "UrgencyScorer",
                    "instance": self.agents["urgency_scorer"]
                },
                "output": {
                    "type": "OutputAgent",
                    "instance": self.agents["output"]
                }
            },
            connections=[
                {
                    "source": "tone_agent",
                    "target": "intent_resolver",
                    "connection_type": ConnectionType.DIRECT
                },
                {
                    "source": "intent_resolver",
                    "target": "urgency_scorer",
                    "connection_type": ConnectionType.DIRECT
                },
                {
                    "source": "urgency_scorer",
                    "target": "output",
                    "connection_type": ConnectionType.DIRECT
                }
            ],
            input_agents=["tone_agent"],
            output_agents=["output"]
        )
    
    async def resolve_ambiguity(self, query):
        """Resolve ambiguity in a user query.
        
        Args:
            query: The user query to analyze
            
        Returns:
            Resolution result with detected intent and true urgency
        """
        input_data = {
            "query": query
        }
        return await self.process(input_data)


class IntentResolver(DeliberativeAgent):
    """Agent for resolving the true intent of ambiguous user messages."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.intent_patterns = self._init_intent_patterns()
        self.memory = Memory(MemoryType.SHORT_TERM)
    
    def _init_intent_patterns(self):
        """Initialize intent pattern categories."""
        return {
            "request_help": [
                r"\bhelp\b", r"\bassist\b", r"\bsupport\b", r"\bguide\b",
                r"\binformation\b", r"\binfo\b", r"\badvice\b"
            ],
            "report_problem": [
                r"\bissue\b", r"\bproblem\b", r"\berror\b", r"\bfail\b", r"\bbug\b",
                r"\bbroken\b", r"\bnot working\b", r"\bcan'?t\b.*\bwork\b"
            ],
            "request_feature": [
                r"\bfeature\b", r"\bfunctionality\b", r"\bcapability\b",
                r"\badd\b", r"\bimplement\b", r"\bsuggestion\b", r"\benhancement\b"
            ],
            "account_issue": [
                r"\baccount\b", r"\blogin\b", r"\bpassword\b", r"\bsign in\b",
                r"\bprofile\b", r"\bsubscription\b", r"\bregistration\b"
            ],
            "billing_issue": [
                r"\bbill\b", r"\bcharge\b", r"\bpayment\b", r"\brefund\b",
                r"\binvoice\b", r"\bcredit card\b", r"\bsubscription\b"
            ]
        }
    
    async def process_message(self, message):
        """Process a message to resolve its intent."""
        content = message.content
        query = content.get("query", "")
        tone_analysis = content.get("tone_analysis", {})
        
        # Resolve intent
        intent_analysis = await self._resolve_intent(query, tone_analysis)
        
        # Send results to next agent
        await self.send_message(
            recipients=[message.metadata.get("next_agent", "urgency_scorer")],
            content={
                "query": query,
                "tone_analysis": tone_analysis,
                "intent_analysis": intent_analysis
            }
        )
    
    async def _resolve_intent(self, text, tone_analysis):
        """Resolve the true intent behind a user message."""
        analysis = {
            "primary_intent": "general_inquiry",
            "intent_confidence": 0.0,
            "detected_intents": {},
            "implied_urgency": False,
            "ambiguity_level": 0.0
        }
        
        # Detect intents
        intent_scores = {}
        for intent, patterns in self.intent_patterns.items():
            score = 0
            matches = []
            for pattern in patterns:
                pattern_matches = re.findall(pattern, text, re.IGNORECASE)
                if pattern_matches:
                    matches.extend(pattern_matches)
                    score += len(pattern_matches)
            
            if score > 0:
                intent_scores[intent] = score
                analysis["detected_intents"][intent] = {
                    "score": score,
                    "matches": matches
                }
        
        # Find primary intent
        if intent_scores:
            primary_intent = max(intent_scores, key=intent_scores.get)
            primary_score = intent_scores[primary_intent]
            
            # Calculate confidence based on difference between primary and secondary intents
            all_scores = list(intent_scores.values())
            if len(all_scores) > 1:
                all_scores.sort(reverse=True)
                score_difference = all_scores[0] - all_scores[1]
                confidence = min(1.0, 0.5 + (score_difference / 5.0))
            else:
                confidence = min(1.0, 0.5 + (primary_score / 5.0))
            
            analysis["primary_intent"] = primary_intent
            analysis["intent_confidence"] = confidence
        
        # Calculate ambiguity level
        num_intents = len(intent_scores)
        if num_intents == 0:
            analysis["ambiguity_level"] = 0.8  # High ambiguity with no clear intent
        elif num_intents == 1:
            analysis["ambiguity_level"] = 0.2  # Low ambiguity with single intent
        else:
            # Calculate ambiguity based on intent score distribution
            primary_score = max(intent_scores.values())
            total_score = sum(intent_scores.values())
            score_ratio = primary_score / total_score if total_score > 0 else 0
            
            analysis["ambiguity_level"] = 1.0 - score_ratio
        
        # Infer implied urgency based on tone analysis
        if tone_analysis.get("tone_masking_detected", False) or tone_analysis.get("urgency_score", 0) > 0.4:
            analysis["implied_urgency"] = True
        
        return analysis
