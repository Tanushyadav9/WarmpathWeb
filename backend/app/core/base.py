"""
backend/app/core/base.py - DeclarativeBase for WarmPath models.
Eliminates circular imports between db.py and models.py.
"""

from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass
