import asyncio
import json
import os
import sys
import time

# Add parent directory to path to allow imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from microservices.ambiguity.ambiguity_resolver import AmbiguityResolverMicroservice

class SupportTicket:
    """Example support ticket class for integration demonstration."""
    
    def __init__(self, ticket_id, query, user_id="anonymous"):
        self.ticket_id = ticket_id
        self.query = query
        self.user_id = user_id
        self.created_at = time.time()
        self.resolution = None
        self.priority = "normal"  # default priority
        self.assigned_to = None
        self.status = "new"
    
    def set_priority(self, priority):
        """Set ticket priority."""
        self.priority = priority
        print(f"Ticket {self.ticket_id} priority set to: {priority}")
    
    def assign_agent(self, agent_id):
        """Assign ticket to support agent."""
        self.assigned_to = agent_id
        self.status = "assigned"
        print(f"Ticket {self.ticket_id} assigned to agent: {agent_id}")
    
    def to_dict(self):
        """Convert ticket to dictionary."""
        return {
            "ticket_id": self.ticket_id,
            "query": self.query,
            "user_id": self.user_id,
            "created_at": self.created_at,
            "priority": self.priority,
            "assigned_to": self.assigned_to,
            "status": self.status,
            "resolution": self.resolution
        }

class SupportSystem:
    """Example support system for integration demonstration."""
    
    def __init__(self):
        self.tickets = {}
        self.agents = {
            "agent_1": {"name": "Alex", "specialization": "account_issue", "availability": "high"},
            "agent_2": {"name": "Taylor", "specialization": "billing_issue", "availability": "medium"},
            "agent_3": {"name": "Jordan", "specialization": "request_help", "availability": "low"}
        }
        
        # Initialize ambiguity resolver
        self.resolver = AmbiguityResolverMicroservice(
            name="Support System Resolver",
            description="Ambiguity resolver for support ticket prioritization"
        )
        self.resolver.deploy()
    
    async def create_ticket(self, query, user_id="anonymous"):
        """Create a new support ticket."""
        ticket_id = f"TICKET-{len(self.tickets) + 1:04d}"
        ticket = SupportTicket(ticket_id, query, user_id)
        self.tickets[ticket_id] = ticket
        
        # Process through ambiguity resolver
        result = await self.resolver.resolve_ambiguity(query)
        
        # Apply resolution to ticket
        ticket.resolution = result
        
        # Set priority based on urgency
        urgency_level = result["resolution"]["resolved_urgency_level"]
        if urgency_level == "high":
            ticket.set_priority("urgent")
        elif urgency_level == "medium":
            ticket.set_priority("normal")
        else:
            ticket.set_priority("low")
        
        # Assign to appropriate agent based on intent
        intent = result["resolution"]["resolved_intent"]
        await self._assign_agent(ticket, intent)
        
        return ticket_id
    
    async def _assign_agent(self, ticket, intent):
        """Assign ticket to appropriate agent based on intent and availability."""
        # Find agents with matching specialization
        matching_agents = [
            agent_id for agent_id, agent in self.agents.items()
            if agent["specialization"] == intent
        ]
        
        if matching_agents:
            # Sort by availability
            sorted_agents = sorted(
                matching_agents,
                key=lambda agent_id: {
                    "high": 0,
                    "medium": 1,
                    "low": 2
                }[self.agents[agent_id]["availability"]]
            )
            
            # Assign to most available agent
            ticket.assign_agent(sorted_agents[0])
        else:
            # No matching agent, assign to any agent based on availability
            sorted_agents = sorted(
                self.agents.keys(),
                key=lambda agent_id: {
                    "high": 0,
                    "medium": 1,
                    "low": 2
                }[self.agents[agent_id]["availability"]]
            )
            
            ticket.assign_agent(sorted_agents[0])
    
    def get_ticket(self, ticket_id):
        """Get ticket by ID."""
        return self.tickets.get(ticket_id)
    
    def get_all_tickets(self):
        """Get all tickets."""
        return self.tickets

async def run_demo():
    """Run support system integration demo."""
    support_system = SupportSystem()
    
    # Sample support queries
    queries = [
        "Just wondering if someone could help me with my account issue.",
        "I'm having a bit of trouble with my login, whenever you get a chance to look at it.",
        "Sorry to bother you, but I can't access my account and I have a presentation in an hour.",
        "I've been charged twice this month, if you could please look into it when you have time.",
        "Just a quick question about how to change my profile picture, no rush."
    ]
    
    print("\n🧠 Neuron Ambiguity Resolver - Support System Integration Demo\n")
    print("Processing support tickets with ambiguity resolution...\n")
    
    # Process each query
    for i, query in enumerate(queries):
        print(f"Query {i+1}: \"{query}\"")
        ticket_id = await support_system.create_ticket(query, f"user_{i+1}")
        ticket = support_system.get_ticket(ticket_id)
        
        # Print ticket details
        print(f"  Ticket ID: {ticket.ticket_id}")
        print(f"  Detected Intent: {ticket.resolution['resolution']['resolved_intent']}")
        print(f"  Urgency Level: {ticket.resolution['resolution']['resolved_urgency_level']}")
        print(f"  Priority Set: {ticket.priority}")
        print(f"  Assigned To: {ticket.assigned_to} ({support_system.agents[ticket.assigned_to]['name']})")
        
        if ticket.resolution["resolution"]["urgency_mismatch_detected"]:
            print(f"  ⚠️  Detected polite language masking urgency")
        
        print("")
    
    print("Demo complete!")

if __name__ == "__main__":
    asyncio.run(run_demo())
