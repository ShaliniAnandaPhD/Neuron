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
