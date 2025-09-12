"""
BeeAI Jira Scrum Master Agent Package - Reworked with BeeAI Framework
"""

__version__ = "2.0.0"
__author__ = "Matfej"
__description__ = "AI Scrum Master with BeeAI Framework and Jira MCP integration"

# Re-export main agent function for easy importing
from .agent import jira_scrum_master

__all__ = ["jira_scrum_master"]
