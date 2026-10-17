"""
Module descriptor for 'trust'
Owner: M1
"""

from app.modules.trust.router import router as ROUTER
from app.modules.trust.service import trust_port_instance


def register_events(bus):
    """Register outbox event handlers for trust."""
    pass


def register_ports(registry):
    """Register synchronous ports implemented by trust."""
    registry.trust = trust_port_instance
