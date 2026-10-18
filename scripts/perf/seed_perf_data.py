#!/usr/bin/env python3
"""
scripts/perf/seed_perf_data.py - Generates isolated load-test data.
Inserts institutions, verified students, and givers with 768-dim vector embeddings
in a separate range/domain that is never mixed with demo data.
"""

import asyncio
import os
import random
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

# Add backend directory to sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))

from sqlalchemy import select
from app.core.db import async_session_maker, Institution, User
from app.modules.matching.models import GiverProfile, StudentMatchProfile
from app.modules.matching.service import deterministic_dummy_vector

LOAD_TEST_DOMAIN = "loadtest.warmpath.org"

TECH_SKILLS = [
    {"name": "Python", "category": "Programming Languages"},
    {"name": "FastAPI", "category": "Web Frameworks"},
    {"name": "PostgreSQL", "category": "Databases"},
    {"name": "Docker", "category": "Cloud & DevOps"},
    {"name": "Kubernetes", "category": "Cloud & DevOps"},
    {"name": "Flutter", "category": "Mobile Development"},
    {"name": "React", "category": "Web Frameworks"},
    {"name": "TypeScript", "category": "Programming Languages"},
    {"name": "Machine Learning", "category": "AI/ML"},
    {"name": "PyTorch", "category": "AI/ML"},
]

OFFERS_POOL = [
    "resume_review",
    "mock_interview",
    "referral_advice",
    "career_guidance",
    "project_feedback",
    "domain_talk",
]

COMPANIES = ["Google", "Microsoft", "Amazon", "Zerodha", "Swiggy", "Zomato", "Flipkart", "Cred"]
ROLES = ["Software Engineer II", "Senior Backend Engineer", "Product Manager", "Data Scientist", "Engineering Manager"]


async def seed_perf_dataset(num_givers: int = 500, num_students: int = 500):
    print(f"[*] Seeding performance dataset ({num_givers} givers, {num_students} students)...")
    async with async_session_maker() as session:
        # 1. Ensure Load Test Institution exists
        stmt_inst = select(Institution).where(Institution.name == "WarmPath Load Test University")
        res_inst = await session.execute(stmt_inst)
        inst = res_inst.scalar_one_or_none()
        if not inst:
            inst = Institution(
                name="WarmPath Load Test University",
                short_name="WPLTU",
                city="New Delhi",
                email_domains=[LOAD_TEST_DOMAIN],
                created_at=datetime.now(timezone.utc),
            )
            session.add(inst)
            await session.commit()
            await session.refresh(inst)

        inst_id = inst.id
        print(f"[+] Using Institution ID: {inst_id} ({inst.name})")

        # 2. Seed Giver Profiles
        print(f"[*] Creating {num_givers} giver profiles with 768-dim embeddings...")
        giver_ids = []
        for i in range(1, num_givers + 1):
            email = f"giver_{i:04d}@{LOAD_TEST_DOMAIN}"
            user_id = uuid.uuid5(uuid.NAMESPACE_DNS, email)

            # Check if user exists
            stmt_u = select(User).where(User.id == user_id)
            res_u = await session.execute(stmt_u)
            user = res_u.scalar_one_or_none()
            if not user:
                user = User(
                    id=user_id,
                    email=email,
                    full_name=f"Perf Giver {i}",
                    institution_id=inst_id,
                    roles=["alumnus"],
                    created_at=datetime.now(timezone.utc),
                )
                session.add(user)

            # Giver Profile
            skills_sample = random.sample(TECH_SKILLS, k=random.randint(3, 6))
            offers_sample = random.sample(OFFERS_POOL, k=random.randint(2, 4))
            bio = f"Alumnus {i} with {random.randint(2, 8)} years in industry. Excited to guide juniors."
            vec_seed = f"giver:{email}:{bio}"
            embedding = deterministic_dummy_vector(vec_seed)

            stmt_gp = select(GiverProfile).where(GiverProfile.user_id == user_id)
            res_gp = await session.execute(stmt_gp)
            gp = res_gp.scalar_one_or_none()
            if not gp:
                gp = GiverProfile(
                    user_id=user_id,
                    offers=offers_sample,
                    topics=[s["name"] for s in skills_sample],
                    skills=skills_sample,
                    domains=["Technology", "Fintech"],
                    company=random.choice(COMPANIES),
                    role_title=random.choice(ROLES),
                    bio=bio,
                    languages=["English", "Hindi"],
                    embedding=embedding,
                    weekly_capacity=random.randint(2, 5),
                    institution_id=inst_id,
                    department="Computer Science",
                    batch=2020 + (i % 4),
                    societies=["ACM", "IEEE"],
                    daily_impressions_count=0,
                    updated_at=datetime.now(timezone.utc),
                )
                session.add(gp)
            giver_ids.append(str(user_id))

        await session.commit()
        print(f"[+] Successfully seeded {len(giver_ids)} givers.")

        # 3. Seed Student Match Profiles
        print(f"[*] Creating {num_students} student match profiles...")
        student_ids = []
        for i in range(1, num_students + 1):
            email = f"student_{i:04d}@{LOAD_TEST_DOMAIN}"
            user_id = uuid.uuid5(uuid.NAMESPACE_DNS, email)

            stmt_u = select(User).where(User.id == user_id)
            res_u = await session.execute(stmt_u)
            user = res_u.scalar_one_or_none()
            if not user:
                user = User(
                    id=user_id,
                    email=email,
                    full_name=f"Perf Student {i}",
                    institution_id=inst_id,
                    roles=["student"],
                    created_at=datetime.now(timezone.utc),
                )
                session.add(user)

            skills_sample = random.sample(TECH_SKILLS, k=random.randint(2, 4))
            vec_seed = f"student:{email}:profile"
            profile_vec = deterministic_dummy_vector(vec_seed)
            intent_vec = deterministic_dummy_vector(f"student:{email}:intent")

            stmt_sp = select(StudentMatchProfile).where(StudentMatchProfile.user_id == user_id)
            res_sp = await session.execute(stmt_sp)
            sp = res_sp.scalar_one_or_none()
            if not sp:
                sp = StudentMatchProfile(
                    user_id=user_id,
                    institution_id=inst_id,
                    department="Computer Science",
                    batch=2025 + (i % 2),
                    societies=["ACM"],
                    skills=skills_sample,
                    domains=["Technology"],
                    profile_embedding=profile_vec,
                    intent_goal="Looking for software engineering internship and mock interview prep",
                    intent_roles=["Software Engineer Intern"],
                    intent_domains=["Technology"],
                    intent_help_type=random.choice(OFFERS_POOL),
                    intent_embedding=intent_vec,
                    profile_version=1,
                    updated_at=datetime.now(timezone.utc),
                )
                session.add(sp)
            student_ids.append(str(user_id))

        await session.commit()
        print(f"[+] Successfully seeded {len(student_ids)} students.")

        # Write sample IDs to load_ids.json for Locust test
        ids_file = Path(__file__).resolve().parent / "load_ids.json"
        import json
        ids_file.write_text(json.dumps({
            "givers": giver_ids,
            "students": student_ids,
            "institution_id": inst_id,
        }, indent=2), encoding="utf-8")
        print(f"[+] Saved IDs manifest to {ids_file}")


if __name__ == "__main__":
    asyncio.run(seed_perf_dataset())
