# Microservices/ambiguity/ambiguity_resolver.py

from typing import Dict, Any, List, Optional, Tuple, Union
import json
import re
import uuid
import os
import logging
from datetime import datetime

from neuron.agent import DeliberativeAgent, ReflexAgent
from neuron.circuit_designer import CircuitDefinition
from ..base_microservice import BaseMicroservice

logger = logging.getLogger(__name__)

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
                r"\bsomewhat\b", r"\ba bit\b", r"\ba little\b", r"\bwonder(?:ing)? if\b",
                r"\bwhen (?:you|they|someone) (?:have|has|get|gets) (?:a (?:moment|minute|chance)|(?:some )?time)\b"
            ],
            "subjunctives": [
                r"\bcould you\b", r"\bwould you\b", r"\bmight you\b",
                r"\bwould it be possible\b", r"\bcould it be possible\b",
                r"\b(?:someone|anyone|somebody) (?:could|might|would)\b", r"\bmight be able to\b"
            ],
            "politeness_markers": [
                r"\bplease\b", r"\bthanks\b", r"\bthank you\b", r"\bappreciate\b",
                r"\bgrateful\b", r"\bwould be great\b", r"\bwould be helpful\b",
                r"\bi know you'?re busy\b"
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
                r"\bdeadline\b", r"\btoday\b", r"\btomorrow\b", r"\bwithin\s+\d+\s+(?:hour|minute|day|week)s?\b",
                r"\bin\s+(?:an?|\d+)\s+(?:hour|minute)s?\b"
            ],
            "consequences": [
                r"\bimportant\b", r"\bcritical\b", r"\bcrucial\b", r"\bvital\b",
                r"\bessential\b", r"\bsignificant\b", r"\bserious\b",
                r"\bcan'?t (?:access|log ?in|sign in)\b", r"\blocked out\b",
                r"\bclient (?:demo|meeting|call|presentation)\b", r"\bpresentation\b"
            ],
            "escalation": [
                r"\bescalate\b", r"\bmanager\b", r"\bsupervisor\b", r"\bcomplaint\b",
                r"\bdissatisfied\b", r"\bunhappy\b", r"\bfrustrated\b", r"\bangry\b",
                r"\bannoy\b", r"\bdisappoint\b"
            ],
            "repeats": [
                r"\bagain\b", r"\brepeat\b", r"\balready\b", r"\bstill\b",
                r"\bnot working\b", r"\bisn'?t working\b", r"\bstill not\b", r"\bonce more\b",
                r"\b(?:multiple|several|many) times\b"
            ],
            "intensifiers": [
                r"\bright now\b", r"\bextremely\b", r"\bat once\b", r"\breally need\b"
            ]
        }
    
    # How much one match in each category counts. Scores saturate:
    # score = 1 - 0.5 ** (weighted matches), so one strong cue gives ~0.5-0.65
    # and three or more give ~0.9, whatever the message length.
    POLITENESS_WEIGHTS = {
        "hedges": 1.0, "subjunctives": 1.0, "politeness_markers": 1.5,
        "apologies": 1.5, "minimizers": 0.5,
    }
    URGENCY_WEIGHTS = {
        "time_constraints": 1.0, "consequences": 0.75, "escalation": 1.0,
        "repeats": 0.5, "intensifiers": 0.5,
    }
    # Phrases that explicitly lower urgency ("no rush"). "When you have time"
    # is not one: it is a polite hedge that often wraps urgent requests.
    CALMING_PATTERNS = [
        r"\bno rush\b", r"\bno hurry\b", r"\bnot urgent\b",
        r"\bwhenever (?:you|it'?s) (?:can|convenient)\b", r"\bat your convenience\b",
    ]
    
    async def process_message(self, message):
        """Process a message to analyze its tone."""
        content = message.content
        query = content.get("query", "")
        
        # Analyze tone and politeness
        tone_analysis = await self._analyze_tone(query)
        
        # Send results to next agent
        await self.send_message(
            recipients=message.sender,
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
            "tone_masking_detected": False,
            "calming_detected": False
        }
        
        # Count politeness markers
        politeness_count = 0.0
        for category, patterns in self.politeness_markers.items():
            detected = []
            for pattern in patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                if matches:
                    detected.extend(matches)
                    politeness_count += len(matches) * self.POLITENESS_WEIGHTS.get(category, 1.0)
            
            if detected:
                analysis["detected_patterns"]["politeness"].append({
                    "category": category,
                    "instances": detected
                })
        
        # Count urgency markers
        urgency_count = 0.0
        for category, patterns in self.urgency_markers.items():
            detected = []
            for pattern in patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                if matches:
                    detected.extend(matches)
                    urgency_count += len(matches) * self.URGENCY_WEIGHTS.get(category, 1.0)
            
            if detected:
                analysis["detected_patterns"]["urgency"].append({
                    "category": category,
                    "instances": detected
                })
        
        # Calculate scores
        analysis["politeness_score"] = 1.0 - 0.5 ** politeness_count
        analysis["urgency_score"] = 1.0 - 0.5 ** urgency_count
        analysis["calming_detected"] = any(
            re.search(pattern, text, re.IGNORECASE) for pattern in self.CALMING_PATTERNS
        )
        
        # Detect tone masking (polite wording around explicit urgency cues)
        if analysis["politeness_score"] > 0.5 and analysis["urgency_score"] > 0.3:
            analysis["tone_masking_detected"] = True
        
        return analysis


class UrgencyScorer(DeliberativeAgent):
    """Agent for scoring the true urgency of user requests."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Typical urgency of each intent when the message has no explicit cues
        self.base_intent_urgency = {
            "report_problem": 0.7,
            "account_issue": 0.6,
            "billing_issue": 0.8,
            "request_help": 0.3,
            "request_feature": 0.3,
            "general_inquiry": 0.2
        }
        # Multiplier applied when the user says there is no rush
        self.calming_factor = 0.4
    
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
            recipients=message.sender,
            content=resolution
        )
    
    async def _calculate_urgency(self, query, tone_analysis, intent_analysis):
        """
        Calculate true urgency from explicit cues and the request's intent.
        
        explicit_urgency      urgency words in the message ("immediately", "in an hour")
        intent_based_urgency  how urgent this kind of request usually is
        true_urgency          both combined as independent evidence:
                              1 - (1 - explicit) * (1 - intent)
        perceived_urgency     what the wording conveys once politeness softens it
        implied_urgency       true minus perceived: urgency the polite tone hides
        """
        explicit = tone_analysis.get("urgency_score", 0.0)
        politeness = tone_analysis.get("politeness_score", 0.0)
        
        primary_intent = intent_analysis.get("primary_intent", "general_inquiry")
        base_urgency = self.base_intent_urgency.get(primary_intent, 0.2)
        confidence = intent_analysis.get("intent_confidence", 0.0)
        intent_urgency = base_urgency * (0.5 + 0.5 * confidence)
        
        true_urgency = 1.0 - (1.0 - explicit) * (1.0 - intent_urgency)
        if tone_analysis.get("calming_detected", False) and explicit < 0.3:
            true_urgency *= self.calming_factor
        
        perceived = explicit * (1.0 - politeness)
        masking = tone_analysis.get("tone_masking_detected", False) or (
            politeness > 0.5 and true_urgency > 0.4
        )
        
        return {
            "explicit_urgency": explicit,
            "intent_based_urgency": intent_urgency,
            "perceived_urgency": perceived,
            "implied_urgency": max(0.0, true_urgency - perceived),
            "true_urgency": min(1.0, true_urgency),
            "tone_masking": masking,
            "urgency_mismatch": masking and true_urgency - perceived >= 0.3
        }
    
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
        
        # Polite wording around a request that is at least medium urgency
        tone_masking = urgency_analysis.get("tone_masking", False)
        
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
        
        # Log the resolution (the microservice's log file is set up in
        # BaseMicroservice)
        logger.info("Resolution: %s", json.dumps(resolution)[:1000])
        
        # Create a formatted output
        output = {
            "original_query": resolution.get("query", ""),
            "resolution": resolution.get("final_resolution", {}),
            "resolution_id": str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat()
        }
        
        await self.send_message(message.sender, output)


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
                    "role": "INPUT"
                },
                "intent_resolver": {
                    "type": "IntentResolver",
                    "role": "PROCESSOR"
                },
                "urgency_scorer": {
                    "type": "UrgencyScorer",
                    "role": "PROCESSOR"
                },
                "output": {
                    "type": "OutputAgent",
                    "role": "OUTPUT"
                }
            },
            connections=[
                {
                    "source": "tone_agent",
                    "target": "intent_resolver",
                    "connection_type": "direct"
                },
                {
                    "source": "intent_resolver",
                    "target": "urgency_scorer",
                    "connection_type": "direct"
                },
                {
                    "source": "urgency_scorer",
                    "target": "output",
                    "connection_type": "direct"
                }
            ]
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
    
    def _init_intent_patterns(self):
        """
        Intent patterns as (pattern, weight) pairs. Generic words that appear
        in most support requests ("help", "issue", "error") count half as much
        as words that name the topic ("password", "charge"); "account" is
        common in billing messages too, so it counts 0.75.
        """
        return {
            "request_help": [
                (r"\bhelp\b", 0.5), (r"\bassist(?:ance)?\b", 0.5), (r"\bsupport\b", 0.5),
                (r"\bguide\b", 0.5), (r"\binformation\b", 0.5), (r"\binfo\b", 0.5),
                (r"\badvice\b", 0.5), (r"\bhow (?:do|can|to)\b", 1.0), (r"\btell me how\b", 1.0)
            ],
            "report_problem": [
                (r"\bissue\b", 0.5), (r"\bproblem\b", 0.5), (r"\berror\b", 0.5),
                (r"\bfail(?:s|ed|ing)?\b", 0.5), (r"\bbug\b", 0.5), (r"\bbroken\b", 0.5),
                (r"\b(?:not|isn'?t|doesn'?t) work(?:ing)?\b", 0.5), (r"\bcan'?t\b.*\bwork\b", 0.5)
            ],
            "request_feature": [
                (r"\bfeature\b", 1.0), (r"\bfunctionality\b", 1.0), (r"\bcapability\b", 1.0),
                (r"\badd\b", 1.0), (r"\bimplement\b", 1.0), (r"\bsuggestion\b", 1.0),
                (r"\benhancement\b", 1.0)
            ],
            "account_issue": [
                (r"\baccount\b", 0.75), (r"\blog ?in\b", 1.0), (r"\bpassword\b", 1.0),
                (r"\bsign in\b", 1.0), (r"\bprofile\b", 1.0), (r"\bregistration\b", 1.0)
            ],
            "billing_issue": [
                (r"\bbill(?:s|ed|ing)?\b", 1.0), (r"\bcharge[sd]?\b", 1.0), (r"\bpayment\b", 1.0),
                (r"\brefund\b", 1.0), (r"\binvoice\b", 1.0), (r"\bcredit card\b", 1.0),
                (r"\bsubscription\b", 1.0)
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
            recipients=message.sender,
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
            score = 0.0
            matches = []
            for pattern, weight in patterns:
                pattern_matches = re.findall(pattern, text, re.IGNORECASE)
                if pattern_matches:
                    matches.extend(pattern_matches)
                    score += len(pattern_matches) * weight
            
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
            
            # Confidence is the primary intent's share of all intent evidence
            confidence = primary_score / sum(intent_scores.values())
            
            analysis["primary_intent"] = primary_intent
            analysis["intent_confidence"] = confidence
            analysis["ambiguity_level"] = 1.0 - confidence
        else:
            analysis["ambiguity_level"] = 0.8  # High ambiguity with no clear intent
        
        # Infer implied urgency based on tone analysis
        if tone_analysis.get("tone_masking_detected", False) or tone_analysis.get("urgency_score", 0) > 0.4:
            analysis["implied_urgency"] = True
        
        return analysis
