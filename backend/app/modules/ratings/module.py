"""
Module descriptor for 'ratings'
Owner: M3
"""

from app.modules.ratings.router import router as ROUTER
from app.modules.ratings.service import ratings_port_instance


def register_events(bus):
    """Register outbox event handlers for ratings."""
    pass


def register_ports(registry):
    """Register synchronous ports implemented by ratings."""
    registry.ratings = ratings_port_instance
