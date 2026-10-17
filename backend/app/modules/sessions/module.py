"""
Module descriptor for 'sessions'
Owner: M3
"""

from app.modules.sessions.router import router as ROUTER
from app.modules.sessions.service import sessions_port_instance


def register_events(bus):
    """Register outbox event handlers for sessions."""
    pass


def register_ports(registry):
    """Register synchronous ports implemented by sessions."""
    registry.sessions = sessions_port_instance
