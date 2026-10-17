"""
backend/app/main.py - WarmPath FastAPI Application Entrypoint.
Auto-discovers and registers all modules from app/modules/.
Frozen after P0.
"""

import importlib
import pkgutil
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.errors import AppError, app_error_handler
from app.core.events import event_bus
from app.core.health import router as health_router
from app.core.logging import RequestIdMiddleware, setup_logging
from app.core.ports import ports
from app.core.redis import close_redis


from app.core.db import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    await init_db(force_recreate=False)
    yield
    await close_redis()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version="0.1.0",
    description="WarmPath: Trusted, Intent-First Alumni Network",
    lifespan=lifespan,
)

# Global Middlewares
app.add_middleware(RequestIdMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception Handlers
app.add_exception_handler(AppError, app_error_handler)

# Health & Readiness
app.include_router(health_router)

# Module Auto-Discovery
modules_dir = Path(__file__).resolve().parent / "modules"
for module_info in pkgutil.iter_modules([str(modules_dir)]):
    mod_name = module_info.name
    try:
        mod = importlib.import_module(f"app.modules.{mod_name}.module")
        if hasattr(mod, "ROUTER"):
            app.include_router(mod.ROUTER)
        if hasattr(mod, "register_events"):
            mod.register_events(event_bus)
        if hasattr(mod, "register_ports"):
            mod.register_ports(ports)
    except Exception as e:
        print(f"Warning: Failed to load module '{mod_name}': {e}")
