#!/usr/bin/env python3
"""
Neuron industry agent.

One agent, configured per use case. Each file in use_cases/ names an industry,
the use case the agent serves, its behavior profile, and the compliance
standards that apply. The agent wires three blocks together:

    MemoryAgent       store, retrieve, search
    ReasoningAgent    analyze, solve, predict
    ReliabilityAgent  health_check, compliance, metrics

Usage:
    python neuron_agent.py --list
    python neuron_agent.py --use-case healthcare
    python neuron_agent.py --use-case legal --profile analyst
    python neuron_agent.py --use-case retail --smoke-test
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import time
import uuid
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from enum import Enum, auto
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("neuron-agent")

USE_CASES_DIR = Path(__file__).resolve().parent / "use_cases"

# Standards a new use case starts with when its config does not list its own.
INDUSTRY_COMPLIANCE = {
    "Healthcare": ["HIPAA", "FDA", "HITECH"],
    "Financial": ["PCI-DSS", "SOX", "GDPR"],
    "Insurance": ["NAIC", "Solvency II", "ISO-27001"],
    "Legal": ["ABA", "Legal Professional Privilege", "GDPR"],
    "Manufacturing": ["ISO-9001", "OSHA", "ISO-14001"],
    "Retail": ["PCI-DSS", "GDPR", "FTC Guidelines"],
}


# ---------------------------------------------------------------------------
# Behavior profiles
# ---------------------------------------------------------------------------


class BehaviorTrait(Enum):
    CURIOSITY = "curiosity"
    CAUTION = "caution"
    PERSISTENCE = "persistence"
    COOPERATION = "cooperation"
    CREATIVITY = "creativity"
    RATIONALITY = "rationality"
    RESPONSIVENESS = "responsiveness"
    AUTONOMY = "autonomy"


class BehaviorMode(Enum):
    NORMAL = auto()
    PERFORMANCE = auto()
    CREATIVE = auto()


@dataclass
class BehaviorProfile:
    name: str
    mode: BehaviorMode
    traits: Dict[BehaviorTrait, float]


BEHAVIOR_PROFILES: Dict[str, BehaviorProfile] = {
    "balanced": BehaviorProfile(
        name="balanced",
        mode=BehaviorMode.NORMAL,
        traits={trait: 0.5 for trait in BehaviorTrait},
    ),
    "explorer": BehaviorProfile(
        name="explorer",
        mode=BehaviorMode.CREATIVE,
        traits={
            BehaviorTrait.CURIOSITY: 0.9,
            BehaviorTrait.CREATIVITY: 0.8,
            BehaviorTrait.AUTONOMY: 0.85,
            BehaviorTrait.PERSISTENCE: 0.6,
            BehaviorTrait.CAUTION: 0.25,
            BehaviorTrait.COOPERATION: 0.4,
            BehaviorTrait.RATIONALITY: 0.5,
            BehaviorTrait.RESPONSIVENESS: 0.7,
        },
    ),
    "analyst": BehaviorProfile(
        name="analyst",
        mode=BehaviorMode.PERFORMANCE,
        traits={
            BehaviorTrait.CURIOSITY: 0.7,
            BehaviorTrait.CREATIVITY: 0.4,
            BehaviorTrait.AUTONOMY: 0.5,
            BehaviorTrait.PERSISTENCE: 0.9,
            BehaviorTrait.CAUTION: 0.8,
            BehaviorTrait.COOPERATION: 0.6,
            BehaviorTrait.RATIONALITY: 0.95,
            BehaviorTrait.RESPONSIVENESS: 0.4,
        },
    ),
}


# ---------------------------------------------------------------------------
# Use case configuration
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class UseCase:
    key: str
    industry: str
    name: str
    description: str
    behavior_profile: str
    compliance_standards: List[str]


def available_use_cases() -> List[str]:
    return sorted(path.stem for path in USE_CASES_DIR.glob("*.json"))


def resolve_use_case_key(key_or_industry: str) -> str:
    """Accept a use case key, or an industry name that has exactly one use case."""
    keys = available_use_cases()
    wanted = key_or_industry.strip().lower()
    if wanted in keys:
        return wanted
    matches = [key for key in keys if key.split("-", 1)[0] == wanted]
    if len(matches) == 1:
        return matches[0]
    if matches:
        raise ValueError(
            f"'{key_or_industry}' matches several use cases: {', '.join(matches)}"
        )
    raise ValueError(
        f"Unknown use case '{key_or_industry}'. Available: {', '.join(keys)}"
    )


def load_use_case(key_or_industry: str) -> UseCase:
    key = resolve_use_case_key(key_or_industry)
    data = json.loads((USE_CASES_DIR / f"{key}.json").read_text())

    profile = data["behavior_profile"].lower()
    if profile not in BEHAVIOR_PROFILES:
        raise ValueError(
            f"{key}.json: behavior_profile '{data['behavior_profile']}' must be one of "
            f"{', '.join(BEHAVIOR_PROFILES)}"
        )

    return UseCase(
        key=key,
        industry=data["industry"],
        name=data["use_case"],
        description=data["description"],
        behavior_profile=profile,
        compliance_standards=list(data["compliance_standards"]),
    )


# ---------------------------------------------------------------------------
# Messaging
# ---------------------------------------------------------------------------


class AgentMessage:
    """A request routed to one of the agents, with a record of where it went."""

    def __init__(
        self, sender: str, recipient: str, msg_type: str, payload: Dict[str, Any]
    ):
        self.id = str(uuid.uuid4())
        self.sender = sender
        self.recipient = recipient
        self.msg_type = msg_type
        self.payload = payload
        self.timestamp = datetime.now()
        self.route_history: List[Dict[str, str]] = []

    def add_route_step(self, processor: str, status: str) -> None:
        self.route_history.append(
            {
                "processor": processor,
                "status": status,
                "timestamp": datetime.now().isoformat(),
            }
        )


# ---------------------------------------------------------------------------
# Agents
# ---------------------------------------------------------------------------


class MemoryAgent:
    """In-memory key/value store with keyword search. Nothing is persisted to disk."""

    def __init__(self, episodic_limit: int = 1000):
        self.memory: Dict[str, Dict[str, Any]] = {}
        self.episodic_memory: deque = deque(maxlen=episodic_limit)
        self.stats = {"stored": 0, "retrieved": 0}

    async def process(self, message: AgentMessage) -> Dict[str, Any]:
        message.add_route_step("MemoryAgent", "processing")

        if message.msg_type == "store":
            return self._store(message.payload)
        if message.msg_type == "retrieve":
            return self._retrieve(message.payload)
        if message.msg_type == "search":
            return self._search(message.payload)
        return {
            "status": "error",
            "message": f"Unknown memory operation: {message.msg_type}",
        }

    def _store(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        key = payload.get("key")
        data = payload.get("data")
        confidence = payload.get("confidence", 0.7)

        if not key or data is None:
            return {"status": "error", "message": "Missing key or data"}

        item = {
            "id": str(uuid.uuid4()),
            "key": key,
            "data": data,
            "confidence": confidence,
            "timestamp": time.time(),
            "access_count": 0,
        }
        self.memory[key] = item
        self.episodic_memory.append(item)
        self.stats["stored"] += 1

        logger.info("Stored memory: %s (confidence: %s)", key, confidence)
        return {"status": "success", "key": key, "confidence": confidence}

    def _retrieve(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        key = payload.get("key")
        if key not in self.memory:
            return {"status": "not_found", "key": key}

        item = self.memory[key]
        item["access_count"] += 1
        self.stats["retrieved"] += 1

        return {
            "status": "success",
            "data": item["data"],
            "confidence": item["confidence"],
            "access_count": item["access_count"],
        }

    def _search(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        query = str(payload.get("query", "")).lower()
        limit = payload.get("limit", 10)

        results = [
            {"key": key, "data": item["data"], "confidence": item["confidence"]}
            for key, item in self.memory.items()
            if query in str(item["data"]).lower()
        ][:limit]

        return {"status": "success", "results": results, "count": len(results)}


class ReasoningAgent:
    """Picks a reasoning strategy from the behavior profile and applies it."""

    def __init__(self, behavior_profile: BehaviorProfile):
        self.behavior_profile = behavior_profile
        self.stats = {"analyses": 0, "decisions": 0}

    def _trait(self, trait: BehaviorTrait) -> float:
        return self.behavior_profile.traits[trait]

    async def process(self, message: AgentMessage) -> Dict[str, Any]:
        message.add_route_step("ReasoningAgent", "processing")

        if message.msg_type == "analyze":
            return self._analyze(message.payload)
        if message.msg_type == "solve":
            return self._solve(message.payload)
        if message.msg_type == "predict":
            return self._predict(message.payload)
        return {
            "status": "error",
            "message": f"Unknown reasoning operation: {message.msg_type}",
        }

    def _select_strategy(self) -> str:
        if self._trait(BehaviorTrait.CREATIVITY) > 0.7:
            return "creative"
        if self._trait(BehaviorTrait.RATIONALITY) > 0.8:
            return "analytical"
        return "systematic"

    def _analyze(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        data = payload.get("data", [])
        if not data:
            return {"status": "error", "message": "No data provided"}

        strategy = self._select_strategy()
        patterns = self._detect_patterns(strategy)
        insights = [
            {
                "pattern_type": pattern["type"],
                "description": f"{strategy.title()} insight: {pattern['description']}",
                "confidence": pattern["confidence"],
                "recommendations": [
                    f"Apply the {strategy} approach to similar data",
                    "Monitor how the pattern evolves",
                    "Validate findings with additional data",
                ],
            }
            for pattern in patterns
        ]

        pattern_confidence = sum(p["confidence"] for p in patterns) / len(patterns)
        confidence = min(0.95, max(0.1, (len(data) / 100.0 + pattern_confidence) / 2))

        self.stats["analyses"] += 1
        return {
            "status": "success",
            "strategy": strategy,
            "patterns": patterns,
            "insights": insights,
            "confidence": confidence,
            "data_count": len(data),
        }

    def _detect_patterns(self, strategy: str) -> List[Dict[str, Any]]:
        # Placeholder: one representative pattern per strategy,
        # not computed from the data.
        if strategy == "analytical":
            return [
                {
                    "type": "trend",
                    "description": "Linear trend detected",
                    "confidence": 0.85,
                }
            ]
        if strategy == "creative":
            return [
                {
                    "type": "emergent",
                    "description": "Unexpected pattern formation",
                    "confidence": 0.72,
                }
            ]
        return [
            {
                "type": "sequential",
                "description": "Ordered progression pattern",
                "confidence": 0.78,
            }
        ]

    def _solve(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        problem = payload.get("problem", "")
        if not problem:
            return {"status": "error", "message": "No problem provided"}

        solutions = []
        if self._trait(BehaviorTrait.CREATIVITY) > 0.6:
            solutions.append(
                {
                    "approach": "creative",
                    "description": "Innovative solution using unconventional methods",
                    "score": 0.8,
                    "steps": [
                        "Brainstorm alternatives",
                        "Prototype ideas",
                        "Test innovations",
                    ],
                }
            )
        if self._trait(BehaviorTrait.RATIONALITY) > 0.7:
            solutions.append(
                {
                    "approach": "analytical",
                    "description": "Data driven solution based on logical analysis",
                    "score": 0.85,
                    "steps": ["Analyze data", "Model scenarios", "Optimize results"],
                }
            )
        if self._trait(BehaviorTrait.COOPERATION) > 0.6:
            solutions.append(
                {
                    "approach": "collaborative",
                    "description": "Team based solution using collective expertise",
                    "score": 0.75,
                    "steps": [
                        "Assemble team",
                        "Facilitate sessions",
                        "Build consensus",
                    ],
                }
            )
        if not solutions:
            # No trait stands out (e.g. the balanced profile),
            # so fall back to a step by step plan.
            solutions.append(
                {
                    "approach": "systematic",
                    "description": "Step by step solution, working through it in order",
                    "score": 0.7,
                    "steps": [
                        "Break the problem down",
                        "Address each part in order",
                        "Review the outcome",
                    ],
                }
            )

        self.stats["decisions"] += 1
        return {
            "status": "success",
            "problem": problem,
            "solutions": solutions,
            "recommended": max(solutions, key=lambda s: s["score"]),
            "solution_count": len(solutions),
        }

    def _predict(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        data = payload.get("data", [])
        horizon = payload.get("horizon", 1)
        if not data:
            return {"status": "error", "message": "No data for prediction"}

        if len(data) > 1 and all(isinstance(x, (int, float)) for x in data):
            trend = (data[-1] - data[0]) / (len(data) - 1)
            prediction = data[-1] + trend * horizon
            scale = max(abs(x) for x in data) or 1.0
            confidence = max(0.1, min(0.9, 1.0 - abs(trend) / scale))
            method = "linear_trend"
        else:
            prediction = data[-1]
            confidence = 0.5
            method = "last_value"

        return {
            "status": "success",
            "prediction": prediction,
            "confidence": confidence,
            "horizon": horizon,
            "method": method,
        }


class ReliabilityAgent:
    """Reports measured health and the compliance standards for the use case."""

    def __init__(self, use_case: UseCase):
        self.use_case = use_case
        self.started_at = time.time()
        self.requests = 0
        self.errors = 0
        self.total_response_time = 0.0

    def record_request(self, duration: float, ok: bool) -> None:
        self.requests += 1
        self.total_response_time += duration
        if not ok:
            self.errors += 1

    async def process(self, message: AgentMessage) -> Dict[str, Any]:
        message.add_route_step("ReliabilityAgent", "processing")

        if message.msg_type == "health_check":
            return {"status": "success", **self._health()}
        if message.msg_type == "compliance":
            return self._compliance()
        if message.msg_type == "metrics":
            return {"status": "success", "health_metrics": self._health()["metrics"]}
        return {
            "status": "error",
            "message": f"Unknown reliability operation: {message.msg_type}",
        }

    def _health(self) -> Dict[str, Any]:
        error_rate = self.errors / self.requests if self.requests else 0.0
        metrics = {
            "uptime_seconds": round(time.time() - self.started_at, 3),
            "requests": self.requests,
            "errors": self.errors,
            "error_rate": round(error_rate, 4),
            "avg_response_ms": (
                round(1000 * self.total_response_time / self.requests, 3)
                if self.requests
                else 0.0
            ),
        }
        if error_rate < 0.05:
            health_status = "healthy"
        elif error_rate < 0.2:
            health_status = "degraded"
        else:
            health_status = "critical"
        return {"health_status": health_status, "metrics": metrics}

    def _compliance(self) -> Dict[str, Any]:
        return {
            "status": "success",
            "industry": self.use_case.industry,
            "use_case": self.use_case.name,
            "standards": self.use_case.compliance_standards,
            "verified": False,
            "note": (
                "Lists the standards this use case must meet. "
                "The agent does not audit against them."
            ),
        }


# ---------------------------------------------------------------------------
# System
# ---------------------------------------------------------------------------


class NeuronSystem:
    """Routes requests to the memory, reasoning and reliability agents."""

    def __init__(self, use_case: UseCase, profile: Optional[str] = None):
        profile_name = (profile or use_case.behavior_profile).lower()
        if profile_name not in BEHAVIOR_PROFILES:
            raise ValueError(
                f"Unknown behavior profile '{profile}'. "
                f"Choose from {', '.join(BEHAVIOR_PROFILES)}"
            )

        self.use_case = use_case
        self.behavior_profile = BEHAVIOR_PROFILES[profile_name]

        self.memory_agent = MemoryAgent()
        self.reasoning_agent = ReasoningAgent(self.behavior_profile)
        self.reliability_agent = ReliabilityAgent(use_case)
        self.agents = {
            "memory": self.memory_agent,
            "reasoning": self.reasoning_agent,
            "reliability": self.reliability_agent,
        }

        self.is_running = False
        logger.info(
            "Neuron system ready: %s / %s (%s profile)",
            use_case.industry,
            use_case.name,
            profile_name,
        )

    async def start(self) -> Dict[str, Any]:
        self.is_running = True
        return {"status": "started", "timestamp": datetime.now().isoformat()}

    async def stop(self) -> Dict[str, Any]:
        self.is_running = False
        return {
            "status": "stopped",
            "uptime_seconds": time.time() - self.reliability_agent.started_at,
        }

    async def process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle a request such as {"type": "memory_store", "payload": {...}}.

        The type is "<agent>_<operation>", where agent is memory, reasoning
        or reliability.
        """
        if not self.is_running:
            return {"status": "error", "message": "System not running"}

        start = time.time()
        request_type = request.get("type", "")
        agent_name, _, operation = request_type.partition("_")
        agent = self.agents.get(agent_name)

        try:
            if agent is None or not operation:
                result = {
                    "status": "error",
                    "message": f"Unknown request type: {request_type}",
                }
            else:
                message = AgentMessage(
                    "system", agent_name, operation, request.get("payload", {})
                )
                result = await agent.process(message)
        except Exception as exc:  # keep the system up if one agent fails
            logger.exception("Request %s failed", request_type)
            result = {"status": "error", "message": str(exc)}

        duration = time.time() - start
        self.reliability_agent.record_request(duration, ok=result["status"] != "error")
        result["processing_time"] = duration
        return result

    def get_status(self) -> Dict[str, Any]:
        return {
            "use_case": self.use_case.key,
            "industry": self.use_case.industry,
            "name": self.use_case.name,
            "description": self.use_case.description,
            "is_running": self.is_running,
            "requests": self.reliability_agent.requests,
            "behavior_profile": {
                "name": self.behavior_profile.name,
                "mode": self.behavior_profile.mode.name,
                "traits": {
                    trait.value: value
                    for trait, value in self.behavior_profile.traits.items()
                },
            },
        }


# ---------------------------------------------------------------------------
# Command line
# ---------------------------------------------------------------------------

CLI_HELP = """Commands:
  status                 show the use case and behavior profile
  store <key> <text>     remember something
  get <key>              recall it
  search <text>          search what has been stored
  analyze <numbers...>   analyze a series, e.g. analyze 1 2 3 4
  predict <numbers...>   predict the next value, e.g. predict 10 15 20
  solve <problem>        propose solutions to a problem
  health                 request count, error rate and response time
  compliance             standards that apply to this use case
  help                   show this list
  quit                   exit"""


def _numbers(args: List[str]) -> List[float]:
    return [float(x) for x in args]


async def run_cli(system: NeuronSystem) -> None:
    await system.start()
    print(f"Neuron agent: {system.use_case.industry} / {system.use_case.name}")
    print(system.use_case.description)
    print(f"Behavior profile: {system.behavior_profile.name}")
    print(CLI_HELP)

    while True:
        try:
            line = input("\nneuron> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not line:
            continue

        command, *args = line.split()
        command = command.lower()

        try:
            if command == "quit":
                break
            elif command == "help":
                print(CLI_HELP)
                continue
            elif command == "status":
                result = system.get_status()
            elif command == "store" and len(args) >= 2:
                result = await system.process_request(
                    {
                        "type": "memory_store",
                        "payload": {"key": args[0], "data": " ".join(args[1:])},
                    }
                )
            elif command == "get" and len(args) == 1:
                result = await system.process_request(
                    {"type": "memory_retrieve", "payload": {"key": args[0]}}
                )
            elif command == "search" and args:
                result = await system.process_request(
                    {"type": "memory_search", "payload": {"query": " ".join(args)}}
                )
            elif command == "analyze" and args:
                result = await system.process_request(
                    {"type": "reasoning_analyze", "payload": {"data": _numbers(args)}}
                )
            elif command == "predict" and args:
                result = await system.process_request(
                    {"type": "reasoning_predict", "payload": {"data": _numbers(args)}}
                )
            elif command == "solve" and args:
                result = await system.process_request(
                    {"type": "reasoning_solve", "payload": {"problem": " ".join(args)}}
                )
            elif command == "health":
                result = await system.process_request(
                    {"type": "reliability_health_check"}
                )
            elif command == "compliance":
                result = await system.process_request(
                    {"type": "reliability_compliance"}
                )
            else:
                print("Unknown command or missing arguments. Type 'help'.")
                continue
            print(json.dumps(result, indent=2, default=str))
        except ValueError as exc:
            print(f"Error: {exc}")

    await system.stop()
    print("Goodbye")


async def smoke_test(system: NeuronSystem) -> None:
    """Exercise every agent once. Exits non-zero on the first failure."""
    await system.start()
    checks = [
        ("memory_store", {"key": "smoke", "data": "smoke test"}),
        ("memory_retrieve", {"key": "smoke"}),
        ("reasoning_analyze", {"data": [1, 2, 3]}),
        ("reasoning_solve", {"problem": f"Improve {system.use_case.name.lower()}"}),
        ("reasoning_predict", {"data": [10, 15, 20]}),
        ("reliability_health_check", {}),
        ("reliability_compliance", {}),
    ]
    for request_type, payload in checks:
        result = await system.process_request(
            {"type": request_type, "payload": payload}
        )
        if result["status"] != "success":
            raise SystemExit(f"FAIL {request_type}: {result}")
        print(f"ok  {request_type}")
    await system.stop()
    print(f"Smoke test passed for {system.use_case.key}")


def main(argv: Optional[List[str]] = None) -> None:
    parser = argparse.ArgumentParser(
        description="Run a Neuron industry agent for one use case."
    )
    parser.add_argument(
        "--use-case", help="use case key, or an industry with one use case (e.g. legal)"
    )
    parser.add_argument(
        "--profile",
        choices=sorted(BEHAVIOR_PROFILES),
        help="override the use case's behavior profile",
    )
    parser.add_argument(
        "--list", action="store_true", help="list the available use cases"
    )
    parser.add_argument(
        "--smoke-test", action="store_true", help="run every agent once and exit"
    )
    parser.add_argument("--verbose", action="store_true", help="log every request")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )

    if args.list:
        for key in available_use_cases():
            use_case = load_use_case(key)
            print(f"{key:<48} {use_case.industry:<14} {use_case.name}")
        return

    if not args.use_case:
        parser.error("--use-case is required (see --list)")

    try:
        use_case = load_use_case(args.use_case)
    except ValueError as exc:
        parser.error(str(exc))

    system = NeuronSystem(use_case, profile=args.profile)
    asyncio.run(smoke_test(system) if args.smoke_test else run_cli(system))


if __name__ == "__main__":
    main()
