"""
Module descriptor for 'credits'
Owner: M4
"""

from app.modules.credits.router import router as ROUTER
from app.modules.credits.service import credits_port_instance


def register_events(bus):
    """Register outbox event handlers for credits."""
    pass


def register_ports(registry):
    """Register synchronous ports implemented by credits."""
    registry.credits = credits_port_instance
