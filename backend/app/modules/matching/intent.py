"""
backend/app/modules/matching/intent.py - Intent structuring & Request quality engine (F6 & F7).

1. Question: "What do you want next?"
2. Converts raw text to structured intent via LLM adapter (or deterministic fallback in DEMO_MODE):
   - goal_type (mentor, referral, mock_interview, resume_review, project_feedback)
   - target_role
   - target_company_type
   - required_skills
3. Request quality pre-flight step:
   - Flags vague asks (<30 chars, no goal type, no technical skills)
   - Generates suggested refinement allowing student to accept, edit, or keep own
   - Blocks empty, gibberish, or spam requests
"""

import re
from typing import Any, Dict, List, Optional
from app.modules.matching.schemas import (
    IntentQualityCheckResponse,
    StructuredIntentData,
)

EXAMPLES = [
    "I want to break into backend engineering at a high-growth fintech startup and need mock interview practice with someone experienced in Go and Kubernetes.",
    "Looking for resume review and referral advice for Google or tier-1 product companies in distributed systems.",
    "Need feedback on my machine learning project architecture and guidance on research engineer career paths.",
]

KNOWN_SKILLS = [
    "Python", "Go", "Golang", "Kubernetes", "Docker", "FastAPI", "React", "Next.js",
    "PostgreSQL", "System Design", "Distributed Systems", "Machine Learning", "PyTorch",
    "TensorFlow", "AWS", "GCP", "Java", "C++", "Rust", "Node.js", "TypeScript", "SQL"
]

SPAM_PATTERNS = [
    r"\b(whatsapp|telegram|dm me on|call me at|send money|paytm|crypto|gpay|upi|giftcard|free cash)\b",
    r"(.)\1{6,}",  # aaaaaaa
    r"^(asdf|test|help|please|hi|hello|hey|xyz|asdfasdf|none|nothing)$",
]


def analyze_intent_quality(raw_text: str) -> IntentQualityCheckResponse:
    """
    Performs pre-flight request quality analysis.
    Blocks empty or spam requests; flags vague asks with suggestions.
    """
    text = (raw_text or "").strip()

    # 1. Block empty or extremely short inputs
    if not text or len(text) < 10:
        return IntentQualityCheckResponse(
            quality_score=0.0,
            is_vague=True,
            is_blocked=True,
            block_reason="Your request is too short or empty. Please explain what guidance or practice you are looking for.",
            issues=["Too short (< 10 characters)"],
            suggested_refinement=None,
            examples=EXAMPLES,
        )

    # 2. Block spam, off-platform solicitation, or repetitive gibberish
    for pat in SPAM_PATTERNS:
        if re.search(pat, text, re.IGNORECASE):
            return IntentQualityCheckResponse(
                quality_score=0.0,
                is_vague=True,
                is_blocked=True,
                block_reason="Request contains invalid spam patterns or prohibited off-platform contact details.",
                issues=["Spam, scam, or prohibited off-platform contact pattern detected"],
                suggested_refinement=None,
                examples=EXAMPLES,
            )

    issues: List[str] = []
    lower = text.lower()

    # Detect goal type
    goal_type = None
    if any(k in lower for k in ["mock interview", "interview practice", "interview prep", "mock"]):
        goal_type = "mock_interview"
    elif any(k in lower for k in ["resume review", "cv review", "review my resume", "resume feedback"]):
        goal_type = "resume_review"
    elif any(k in lower for k in ["referral", "refer me", "job referral", "hiring chat"]):
        goal_type = "referral"
    elif any(k in lower for k in ["project feedback", "code review", "architecture feedback", "project"]):
        goal_type = "project_feedback"
    elif any(k in lower for k in ["mentor", "career guidance", "guidance", "career advice", "advice"]):
        goal_type = "mentor"

    if not goal_type:
        issues.append("No specific goal type detected (choose: mock interview, resume review, referral, project feedback, or mentor)")

    # Detect technical skills / target roles
    skills_found = [s for s in KNOWN_SKILLS if re.search(r"\b" + re.escape(s) + r"\b", text, re.IGNORECASE)]
    role_hints = [r for r in ["backend", "frontend", "fullstack", "software engineer", "devops", "ai", "ml", "data engineer", "product manager"] if r in lower]

    if not skills_found and not role_hints:
        issues.append("No technical skills or target role mentioned")

    if len(text) < 30:
        issues.append("Request is very brief (< 30 characters)")

    is_vague = len(issues) > 0
    quality_score = 0.95 if not is_vague else (0.55 if len(issues) == 1 else 0.35)

    suggested = None
    if is_vague:
        suggested = generate_suggested_refinement(text, goal_type, skills_found, role_hints)

    return IntentQualityCheckResponse(
        quality_score=round(quality_score, 2),
        is_vague=is_vague,
        is_blocked=False,
        block_reason=None,
        issues=issues,
        suggested_refinement=suggested,
        examples=EXAMPLES,
    )


def generate_suggested_refinement(
    raw_text: str,
    goal_type: Optional[str],
    skills: List[str],
    roles: List[str],
) -> str:
    """Generates a refined high-signal request based on detected intent fragments."""
    primary_skill = skills[0] if skills else "Python and System Design"
    primary_role = roles[0].title() if roles else "Software Engineer - Backend"
    
    if goal_type == "mock_interview":
        return (
            f"I am preparing for {primary_role} roles and would like a 30-minute mock interview "
            f"focusing on problem solving and {primary_skill}. I want actionable feedback on my technical communication."
        )
    elif goal_type == "resume_review":
        return (
            f"I am targeting {primary_role} positions at product companies and am seeking a resume review. "
            f"I would like feedback on how to effectively showcase my projects in {primary_skill}."
        )
    elif goal_type == "referral":
        return (
            f"I am interested in opportunities in {primary_role} and would appreciate referral guidance. "
            f"I have built projects using {primary_skill} and would love advice on aligning with hiring expectations."
        )
    elif goal_type == "project_feedback":
        return (
            f"I have built a system using {primary_skill} and would value technical feedback on its architecture, "
            f"scalability, and code structure from an experienced engineer."
        )
    else:
        return (
            f"I am an aspiring {primary_role} seeking career guidance. I would love 30 minutes to discuss "
            f"transitioning from academic projects in {primary_skill} to industry roles at high-growth engineering teams."
        )


def structure_intent(
    raw_text: str,
    goal_type_override: Optional[str] = None,
    target_role_override: Optional[str] = None,
    target_company_type_override: Optional[str] = None,
    required_skills_override: Optional[List[str]] = None,
) -> StructuredIntentData:
    """
    Structures the student's answer into a clean actionable schema.
    Uses deterministic parsing with rule-based heuristics in demo mode.
    """
    lower = raw_text.lower()

    # 1. Goal Type
    goal_type = goal_type_override
    if not goal_type:
        if any(k in lower for k in ["mock interview", "interview practice", "interview prep", "mock"]):
            goal_type = "mock_interview"
        elif any(k in lower for k in ["resume review", "cv review", "review my resume", "resume"]):
            goal_type = "resume_review"
        elif any(k in lower for k in ["referral", "refer me", "job referral"]):
            goal_type = "referral"
        elif any(k in lower for k in ["project feedback", "code review", "architecture feedback"]):
            goal_type = "project_feedback"
        else:
            goal_type = "mentor"

    # 2. Target Role
    target_role = target_role_override
    if not target_role:
        if "backend" in lower:
            target_role = "Software Engineer - Backend"
        elif "frontend" in lower:
            target_role = "Software Engineer - Frontend"
        elif "fullstack" in lower:
            target_role = "Full Stack Engineer"
        elif "ai" in lower or "ml" in lower or "machine learning" in lower:
            target_role = "Machine Learning Engineer"
        elif "data" in lower:
            target_role = "Data Engineer"
        elif "devops" in lower or "sre" in lower:
            target_role = "DevOps / Site Reliability Engineer"
        else:
            target_role = "Software Engineer"

    # 3. Target Company Type
    target_company = target_company_type_override
    if not target_company:
        if "fintech" in lower:
            target_company = "High-growth Fintech Startup"
        elif any(k in lower for k in ["google", "tier-1", "tier 1", "faang", "product company", "big tech"]):
            target_company = "Tier-1 Product / Big Tech"
        elif "startup" in lower:
            target_company = "Early / Growth Stage Startup"
        else:
            target_company = "Product Companies"

    # 4. Required Skills
    if required_skills_override:
        required_skills = required_skills_override
    else:
        required_skills = [s for s in KNOWN_SKILLS if re.search(r"\b" + re.escape(s) + r"\b", raw_text, re.IGNORECASE)]
        if not required_skills:
            if "backend" in lower:
                required_skills = ["Python", "FastAPI"]
            elif "ml" in lower or "ai" in lower:
                required_skills = ["PyTorch", "Python"]
            elif "frontend" in lower:
                required_skills = ["React", "TypeScript"]
            else:
                required_skills = ["Software Engineering"]

    return StructuredIntentData(
        goal_type=goal_type,
        target_role=target_role,
        target_company_type=target_company,
        required_skills=required_skills,
        timeline="Next 2-4 weeks",
        raw_text=raw_text,
    )
