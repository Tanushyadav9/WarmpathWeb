"""
Module descriptor for 'availability'
Owner: M3
"""

from app.modules.availability.router import router as ROUTER
from app.modules.availability.service import presence_port_instance


def register_events(bus):
    """Register outbox event handlers for availability."""
    pass


def register_ports(registry):
    """Register synchronous ports implemented by availability."""
    registry.presence = presence_port_instance
