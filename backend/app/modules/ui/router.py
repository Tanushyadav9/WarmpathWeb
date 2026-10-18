"""API and HTML Router for WarmPath UI & Jury Demo Mode."""
import json
import uuid
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.modules.ui.demo_service import demo_service

router = APIRouter(tags=["ui"])


@router.get("/demo/status", summary="Get Jury Demo step completion status")
async def get_demo_status():
    return {
        "step_status": demo_service.step_status,
        "completed_count": sum(1 for v in demo_service.step_status.values() if v),
        "total_steps": 8,
    }


@router.post("/demo/reset", summary="One-click reset restoring clean state for Jury Demo")
async def post_demo_reset(db: AsyncSession = Depends(get_db)):
    result = await demo_service.reset_demo(db)
    return result


@router.post("/demo/step/{step_num}", summary="Run a specific step of the Jury Demo story")
async def post_demo_step(step_num: int, db: AsyncSession = Depends(get_db)):
    if step_num < 1 or step_num > 8:
        raise HTTPException(status_code=400, detail="Step number must be between 1 and 8")
    result = await demo_service.run_step(db, step_num)
    return result


@router.post("/demo/refine-intent", summary="Live AI intent refinement tool")
async def post_refine_intent(payload: Dict[str, str]):
    raw = payload.get("intent", "").strip()
    if not raw:
        return {"refined_intent": demo_service.refined_intent}
    
    # Concrete domain enrichment for mentorship intents
    refined = (
        f"System Design & Backend Architecture: {raw.capitalize()} "
        f"(Structured Objectives: High Concurrency, Clean Architecture & Production Reliability)"
    )
    return {
        "raw_intent": raw,
        "refined_intent": refined,
        "recommended_tags": ["System Design", "Distributed Systems", "Clean Architecture", "Concurrency"],
    }


@router.get("/", response_class=HTMLResponse, summary="WarmPath Full Interactive Web Application")
@router.get("/demo", response_class=HTMLResponse, summary="WarmPath Jury Demo Mode")
async def get_ui_application():
    from app.modules.ui.html_template import get_ui_html
    return HTMLResponse(content=get_ui_html())
