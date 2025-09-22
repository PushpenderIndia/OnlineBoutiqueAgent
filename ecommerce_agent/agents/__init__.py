from .product_finder_agent.agent import product_finder_agent
from .product_recommendation_agent.agent import product_recommendation_agent
from .virtual_tryon_agent.agent import virtual_tryon_agent
from .order_placement_agent.agent import order_placement_agent
from .export_agent.agent import export_agent

# Import the root agent using absolute import
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from agent import root_agent

# Set the agent attribute that ADK expects
agent = root_agent

# Make all agents available when importing from agents
__all__ = [
    'product_finder_agent',
    'product_recommendation_agent',
    'virtual_tryon_agent',
    'order_placement_agent',
    'export_agent'
    'agent'
]