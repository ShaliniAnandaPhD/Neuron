"""
Scripts Package
Utility scripts for monitoring, health checking, and deployment
"""

__version__ = "1.0.0"

# Import main script functions
from .monitor_dashboard import main as monitor_main
from .health_checker import main as health_main  
from .deployment_utils import main as deploy_main

__all__ = [
    "monitor_main",
    "health_main", 
    "deploy_main"
]