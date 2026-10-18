"""
scripts/seed_all.py - Complete, realistic dataset seeder for WarmPath.
Can be executed directly: python scripts/seed_all.py
or imported as a module: await run_seed(db)
"""

import asyncio
from datetime import datetime, timedelta, timezone
import os
import random
import sys
import uuid
from pathlib import Path
from typing import Any, Optional

# Setup sys.path for direct script execution
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import async_session_maker, init_db, Base, engine
from app.core.models import (
    AuditLog,
    Availability,
    Capacity,
    CreditLedger,
    CreditWallet,
    GiverProfile,
    Institution,
    Notification,
    Opportunity,
    Rating,
    Report,
    Request,
    RequestMessage,
    Resume,
    ScamRule,
    Session,
    Skill,
    StudentProfile,
    User,
    UserSkill,
    Vouch,
    AlumniRosterRecord,
    EmailOTP,
    VerificationRequest,
    PeerVouchRequest,
)

from app.core.security import hash_password


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


DEFAULT_PASSWORD = "demo1234"


async def run_seed(session: Optional[Any] = None) -> None:
    """Wipes and seeds the database with rich, realistic benchmark data."""
    if session is None:
        await init_db(force_recreate=True)
        from app.core.db import get_db_session_context
        db = get_db_session_context()
        try:
            await _seed_data(db)
        finally:
            await db.close()

    else:
        await _seed_data(session)


async def _seed_data(db: AsyncSession) -> None:
    print("[*] Clearing existing WarmPath tables...")

    # Clear tables in dependency order
    for model in [
        AuditLog, Notification, Report, ScamRule, Vouch, Rating,
        Session, RequestMessage, Request, CreditLedger, CreditWallet,
        Opportunity, UserSkill, Skill, Resume, Capacity, Availability,
        GiverProfile, StudentProfile,
        PeerVouchRequest, VerificationRequest, EmailOTP, AlumniRosterRecord,
        User, Institution
    ]:

        try:
            await db.execute(delete(model))
        except Exception:
            pass
    await db.commit()

    print("[+] Seeding Institutions...")
    institutions_data = [
        {
            "id": 1,
            "name": "Indraprastha Institute of Information Technology Delhi",
            "short_name": "IIIT Delhi",
            "city": "New Delhi",
            "email_domains": ["iiitd.ac.in"],
            "verified_domain": "iiitd.ac.in",
        },
        {
            "id": 2,
            "name": "Indian Institute of Technology Delhi",
            "short_name": "IIT Delhi",
            "city": "New Delhi",
            "email_domains": ["iitd.ac.in"],
            "verified_domain": "iitd.ac.in",
        },
        {
            "id": 3,
            "name": "Birla Institute of Technology and Science, Pilani",
            "short_name": "BITS Pilani",
            "city": "Pilani",
            "email_domains": ["pilani.bits-pilani.ac.in"],
            "verified_domain": "bits-pilani.ac.in",
        },
    ]
    institutions = [Institution(**data) for data in institutions_data]
    db.add_all(institutions)
    await db.commit()

    print("[+] Seeding Institution Alumni CSV Rosters...")
    roster_records = [
        AlumniRosterRecord(
            id=uuid.uuid4(),
            institution_id=1,
            email="vikram.malhotra@alumni.iiitd.ac.in",
            full_name="Vikram Malhotra",
            batch=2021,
            branch="Computer Science",
            roll_number="2017001",
        ),
        AlumniRosterRecord(
            id=uuid.uuid4(),
            institution_id=1,
            email="rohan.gupta@alumni.iiitd.ac.in",
            full_name="Rohan Gupta",
            batch=2021,
            branch="Computer Science",
            roll_number="2017089",
        ),
        AlumniRosterRecord(
            id=uuid.uuid4(),
            institution_id=1,
            email="sneha.patel@alumni.iiitd.ac.in",
            full_name="Sneha Patel",
            batch=2020,
            branch="Electronics & Communication",
            roll_number="2016045",
        ),
        AlumniRosterRecord(
            id=uuid.uuid4(),
            institution_id=1,
            email="ananya.roy@alumni.iiitd.ac.in",
            full_name="Ananya Roy",
            batch=2022,
            branch="Computer Science",
            roll_number="2018112",
        ),
        AlumniRosterRecord(
            id=uuid.uuid4(),
            institution_id=1,
            email="tanmay.bhatia@alumni.iiitd.ac.in",
            full_name="Tanmay Bhatia",
            batch=2021,
            branch="Computer Science",
            roll_number="2017234",
        ),
        AlumniRosterRecord(
            id=uuid.uuid4(),
            institution_id=1,
            email="nikhil.aggarwal@alumni.iiitd.ac.in",
            full_name="Nikhil Aggarwal",
            batch=2020,
            branch="Computer Science",
            roll_number="2016045",
        ),
    ]
    db.add_all(roster_records)
    await db.commit()


    print("[+] Seeding Core Skills Taxonomy...")
    skills_list = [
        ("Python", "Languages"), ("TypeScript", "Languages"), ("JavaScript", "Languages"),
        ("Go", "Languages"), ("C++", "Languages"), ("Rust", "Languages"), ("Java", "Languages"),
        ("FastAPI", "Frameworks"), ("Next.js", "Frameworks"), ("React", "Frameworks"),
        ("Node.js", "Frameworks"), ("Flutter", "Frameworks"), ("PyTorch", "AI/ML"),
        ("TensorFlow", "AI/ML"), ("LLM Engineering", "AI/ML"), ("Computer Vision", "AI/ML"),
        ("PostgreSQL", "Databases"), ("Redis", "Databases"), ("Vector DBs", "Databases"),
        ("Docker", "DevOps/Cloud"), ("Kubernetes", "DevOps/Cloud"), ("AWS", "DevOps/Cloud"),
        ("System Design", "Systems"), ("Distributed Systems", "Systems"), ("Microservices", "Systems"),
        ("Product Management", "Product"), ("Resume Critique", "Career"), ("Mock Interviews", "Career"),
    ]
    skills_map = {}
    for name, cat in skills_list:
        sk = Skill(id=uuid.uuid4(), name=name, category=cat)
        db.add(sk)
        skills_map[name] = sk
    await db.commit()

    hashed_pwd = hash_password(DEFAULT_PASSWORD)

    # 1. Institution Admin Persona
    print("[+] Seeding Admin Persona...")
    admin_user = User(
        id=uuid.uuid4(),
        email="admin@iiitd.ac.in",
        password_hash=hashed_pwd,
        full_name="Dean Alumni Affairs (IIITD)",
        role="admin",
        roles=["admin"],
        institution_id=1,
        verification_level="trusted",
        trust_score=99.0,
        is_active=True,
    )
    db.add(admin_user)

    # 2. Demo Student Persona (Aarav Sharma)
    print("[+] Seeding Demo Student Persona...")
    demo_student = User(
        id=uuid.uuid4(),
        email="aarav.sharma@iiitd.ac.in",
        password_hash=hashed_pwd,
        full_name="Aarav Sharma",
        role="student",
        roles=["student"],
        institution_id=1,
        verification_level="verified_alumnus",
        trust_score=75.0,
        is_active=True,
    )
    db.add(demo_student)
    await db.flush()

    db.add(StudentProfile(
        user_id=demo_student.id,
        headline="3rd Year B.Tech CSE at IIIT Delhi | Aspiring Backend & Distributed Systems Engineer",
        bio="Passionate about high-throughput APIs, distributed consensus, and database internals. Building open source projects.",
        batch=2026,
        department="Computer Science and Engineering",
        cgpa=8.84,
        target_role="Software Engineer (Backend)",
        target_domain="Fintech & Cloud Platforms",
        intent_ask="Looking for alumni in Google / Razorpay for a mock system design interview and resume critique.",
    ))
    db.add(CreditWallet(user_id=demo_student.id, balance=5, escrow_held=0))

    # Add skills for demo student
    for s_name in ["Python", "FastAPI", "PostgreSQL", "Docker", "System Design"]:
        db.add(UserSkill(user_id=demo_student.id, skill_id=skills_map[s_name].id, endorsements_count=3))

    # Add demo resume
    db.add(Resume(
        user_id=demo_student.id,
        raw_file_ref="/resumes/aarav_sharma_resume.pdf",
        parsed_json={
            "education": [{"college": "IIIT Delhi", "degree": "B.Tech CSE", "year": "2022-2026", "cgpa": "8.84"}],
            "skills": ["Python", "FastAPI", "Docker", "PostgreSQL", "Redis"],
            "projects": [{"title": "WarmPath Microservices", "desc": "High-throughput async event bus"}],
        },
        edited_json={"confirmed": True},
        is_committed=True,
        parsed_at=utc_now(),
    ))

    # 3. Demo Alumni Persona (Vikram Malhotra - Top Rated at Google)
    print("[+] Seeding Demo Alumni Persona...")
    demo_alumni = User(
        id=uuid.uuid4(),
        email="vikram.malhotra@alumni.iiitd.ac.in",
        password_hash=hashed_pwd,
        full_name="Vikram Malhotra",
        role="alumni",
        roles=["alumni"],
        institution_id=1,
        batch=2021,
        branch="Computer Science",
        company="Google",
        verification_level="trusted",
        trust_score=95.0,
        is_active=True,
    )

    db.add(demo_alumni)
    await db.flush()

    db.add(GiverProfile(
        user_id=demo_alumni.id,
        headline="Staff Software Engineer at Google | Ex-Uber | IIITD Class of 2018",
        bio="8+ years building large-scale distributed storage and real-time infrastructure. Passionate about helping IIITD juniors crack tier-1 tech interviews.",
        role_title="Staff Software Engineer",
        company="Google",
        domain="Distributed Systems & Cloud",
        topics=["System Design", "Mock Interviews", "Distributed Storage", "Career Navigation"],
        offers=["mock_interview", "resume_review", "referral_advice"],
        languages=["English", "Hindi"],
        band="top_rated",
        rating_avg=4.95,
        rating_count=24,
        completion_rate=1.0,
        weekly_capacity=3,
    ))
    db.add(Availability(
        user_id=demo_alumni.id,
        status="active_now",
        time_window=["19:00-21:00 IST Sat", "11:00-13:00 IST Sun"],
        avg_reply_minutes=25,
        response_rate=0.98,
    ))
    db.add(Capacity(user_id=demo_alumni.id, weekly_cap=3, free_monthly_cap=6, current_week_booked=1))
    db.add(CreditWallet(user_id=demo_alumni.id, balance=12, escrow_held=2))

    # 4. Demo Faculty Persona (Dr. Pankaj Jalote)
    print("[+] Seeding Demo Faculty Persona...")
    demo_faculty = User(
        id=uuid.uuid4(),
        email="dr.pankaj@iiitd.ac.in",
        password_hash=hashed_pwd,
        full_name="Dr. Pankaj Jalote",
        role="faculty",
        roles=["faculty"],
        institution_id=1,
        verification_level="verified_professional",
        trust_score=98.0,
        is_active=True,
    )
    db.add(demo_faculty)
    await db.flush()

    db.add(GiverProfile(
        user_id=demo_faculty.id,
        headline="Distinguished Professor & Founding Director | IIIT Delhi",
        bio="Academic research in software engineering metrics, fault tolerance, and higher education leadership.",
        role_title="Distinguished Professor",
        company="IIIT Delhi",
        domain="Software Engineering & Higher Studies",
        topics=["Research Advising", "Thesis Formulation", "MS/PhD Guidance"],
        offers=["domain_talk", "career_guidance"],
        languages=["English", "Hindi"],
        band="top_rated",
        rating_avg=4.98,
        rating_count=35,
        completion_rate=1.0,
        weekly_capacity=2,
    ))
    db.add(Availability(user_id=demo_faculty.id, status="available_today", time_window=["15:00-17:00 Thu"]))
    db.add(Capacity(user_id=demo_faculty.id, weekly_cap=2, free_monthly_cap=4))
    db.add(CreditWallet(user_id=demo_faculty.id, balance=0, escrow_held=0))

    # 5. Demo Recruiter Persona (Priya Menon at Razorpay)
    print("[+] Seeding Demo Recruiter Persona...")
    demo_recruiter = User(
        id=uuid.uuid4(),
        email="priya.recruiter@razorpay.com",
        password_hash=hashed_pwd,
        full_name="Priya Menon",
        role="recruiter",
        roles=["recruiter"],
        institution_id=None,
        verification_level="verified_employer",
        trust_score=90.0,
        is_active=True,
    )
    db.add(demo_recruiter)
    await db.flush()

    db.add(GiverProfile(
        user_id=demo_recruiter.id,
        headline="Talent Acquisition Lead at Razorpay | Hiring Backend & Full-Stack Interns",
        bio="Connecting passionate student builders with engineering teams at Razorpay.",
        role_title="Talent Acquisition Lead",
        company="Razorpay",
        domain="Fintech Recruitment",
        topics=["Resume Review", "Hiring Chats", "Culture Fit Advice"],
        offers=["referral_advice"],
        band="trusted",
        rating_avg=4.75,
        rating_count=12,
        weekly_capacity=4,
    ))
    db.add(Availability(user_id=demo_recruiter.id, status="active_now"))
    db.add(Capacity(user_id=demo_recruiter.id, weekly_cap=4, free_monthly_cap=8))
    db.add(CreditWallet(user_id=demo_recruiter.id, balance=20, escrow_held=0))

    # 6. Demo Founder Persona (Kunal Shah at Postman)
    print("[+] Seeding Demo Founder Persona...")
    demo_founder = User(
        id=uuid.uuid4(),
        email="kunal.founder@postman.com",
        password_hash=hashed_pwd,
        full_name="Kunal Shah",
        role="founder",
        roles=["founder"],
        institution_id=2,  # IIT Delhi alum
        verification_level="verified_employer",
        trust_score=94.0,
        is_active=True,
    )
    db.add(demo_founder)
    await db.flush()

    db.add(GiverProfile(
        user_id=demo_founder.id,
        headline="Co-Founder & CTO | Angel Investor | B.Tech IIT Delhi 2015",
        bio="Scaling developer tools from 0 to 10M users. Looking for high-agency student founders and early engineers.",
        role_title="Co-Founder & CTO",
        company="Postman",
        domain="DevTools & Enterprise SaaS",
        topics=["Startup 0-to-1", "Product Architecture", "Founding Engineer Roles"],
        offers=["career_guidance", "referral_advice"],
        band="top_rated",
        rating_avg=4.90,
        rating_count=18,
        weekly_capacity=2,
    ))
    db.add(Availability(user_id=demo_founder.id, status="available_today"))
    db.add(Capacity(user_id=demo_founder.id, weekly_cap=2, free_monthly_cap=4))
    db.add(CreditWallet(user_id=demo_founder.id, balance=50, escrow_held=0))

    # --- 60 Students Population ---
    print("[+] Generating 59 additional realistic students (Total: 60)...")
    first_names = [
        "Ananya", "Rohan", "Diya", "Aryan", "Ishaan", "Priya", "Sneha", "Aditya", "Tanvi", "Kabir",
        "Riya", "Siddharth", "Meera", "Varun", "Pooja", "Rahul", "Neha", "Karan", "Shruti", "Akash",
        "Bhavya", "Dev", "Esha", "Farhan", "Gauri", "Harsh", "Ira", "Jai", "Kavya", "Laksh",
        "Manish", "Nandini", "Om", "Parth", "Radhika", "Sameer", "Tara", "Uday", "Veda", "Yash",
        "Zoya", "Aniket", "Charu", "Dhruv", "Gitanjali", "Hitesh", "Jasleen", "Kartik", "Lavanya", "Mohit",
        "Nidhi", "Pranav", "Reet", "Shaurya", "Trisha", "Utkarsh", "Vidhi", "Zeeshan", "Kriti"
    ]
    last_names = [
        "Verma", "Patel", "Gupta", "Mehra", "Rao", "Nair", "Reddy", "Kumar", "Joshi", "Mehta",
        "Sen", "Roy", "Iyer", "Malhotra", "Deshmukh", "Saxena", "Bansal", "Kapoor", "Agrawal", "Bhatia",
        "Chopra", "Das", "Fernandes", "Ghosh", "Hegde", "Jain", "Kulkarni", "Lal", "Menon", "Narang"
    ]
    depts = [
        "Computer Science and Engineering",
        "Artificial Intelligence & Data Science",
        "Electronics and Communications Engineering",
        "Computational Biology"
    ]
    target_roles = [
        "Backend Engineer", "Full-Stack Engineer", "Machine Learning Engineer",
        "Data Scientist", "DevOps/SRE Engineer", "Mobile App Engineer"
    ]

    all_students = [demo_student]
    for i, fname in enumerate(first_names):
        lname = last_names[i % len(last_names)]
        name = f"{fname} {lname}"
        inst_id = 1 if i < 35 else (2 if i < 48 else 3)
        inst_domain = "iiitd.ac.in" if inst_id == 1 else ("iitd.ac.in" if inst_id == 2 else "pilani.bits-pilani.ac.in")
        email = f"{fname.lower()}.{lname.lower()}_{i+1}@{inst_domain}"
        
        user = User(
            id=uuid.uuid4(),
            email=email,
            password_hash=hashed_pwd,
            full_name=name,
            role="student",
            roles=["student"],
            institution_id=inst_id,
            verification_level="verified_alumnus",
            trust_score=round(random.uniform(55.0, 85.0), 1),
            is_active=True,
        )
        db.add(user)
        await db.flush()

        role_target = random.choice(target_roles)
        db.add(StudentProfile(
            user_id=user.id,
            headline=f"Student ({random.choice(['3rd', '4th'])} Year) at {institutions_data[inst_id-1]['short_name']}",
            bio=f"Interested in {role_target} roles and scalable software systems.",
            batch=random.choice([2025, 2026, 2027]),
            department=random.choice(depts),
            cgpa=round(random.uniform(7.5, 9.6), 2),
            target_role=role_target,
            target_domain="Tech / Software",
            intent_ask=f"Looking for mock interviews and portfolio guidance for {role_target} openings.",
        ))
        db.add(CreditWallet(user_id=user.id, balance=random.randint(1, 4), escrow_held=0))
        all_students.append(user)
    await db.commit()

    # --- 50 Verified Alumni Population ---
    print("[+] Generating 49 additional realistic alumni (Total: 50)...")
    alumni_companies = [
        ("Google", "Staff Software Engineer", "Distributed Systems"),
        ("Microsoft", "Senior Software Engineer", "Cloud Infrastructure"),
        ("Amazon", "Software Development Engineer II", "E-Commerce Microservices"),
        ("Uber", "Senior Backend Engineer", "Realtime Dispatch Systems"),
        ("Swiggy", "Lead Architect", "Delivery Logistics"),
        ("Zomato", "Engineering Manager", "High-Volume Transaction Processing"),
        ("Zerodha", "Core Systems Engineer", "Low-Latency Trading"),
        ("Cred", "Senior Full-Stack Engineer", "Fintech Payment Rails"),
        ("Flipkart", "Data Platform Lead", "Big Data & Recommendation Engines"),
        ("Adobe", "Computer Vision Scientist", "Creative Intelligence"),
        ("Atlassian", "Staff SRE", "Reliability Engineering"),
        ("Stripe", "Senior Infrastructure Engineer", "Global Financial Systems"),
    ]

    all_alumni = [demo_alumni]
    for i in range(1, 50):
        fname = random.choice(first_names)
        lname = random.choice(last_names)
        inst_id = 1 if i < 28 else (2 if i < 42 else 3)
        inst_domain = "alumni.iiitd.ac.in" if inst_id == 1 else ("alumni.iitd.ac.in" if inst_id == 2 else "alumni.bits-pilani.ac.in")
        email = f"{fname.lower()}.{lname.lower()}{i}@{inst_domain}"

        company_info = alumni_companies[i % len(alumni_companies)]
        comp, role_title, domain = company_info

        # Distribute bands: ~15 Rising, ~20 Trusted, ~15 Top Rated
        if i <= 15:
            band = "rising"
            sessions_count = random.randint(1, 4)
            rating = round(random.uniform(4.0, 4.8), 2)
        elif i <= 35:
            band = "trusted"
            sessions_count = random.randint(5, 9)
            rating = round(random.uniform(4.25, 4.75), 2)
        else:
            band = "top_rated"
            sessions_count = random.randint(10, 30)
            rating = round(random.uniform(4.70, 5.0), 2)

        avail_status = random.choice(["active_now", "available_today", "inactive"])
        batch_year = random.choice([2019, 2020, 2021, 2022, 2023])

        alumni_user = User(
            id=uuid.uuid4(),
            email=email,
            password_hash=hashed_pwd,
            full_name=f"{fname} {lname}",
            role="alumni",
            roles=["alumni"],
            institution_id=inst_id,
            batch=batch_year,
            branch="Computer Science",
            company=comp,
            verification_level="trusted" if band == "top_rated" else "verified_alumnus",
            trust_score=round(random.uniform(70.0, 98.0), 1),
            is_active=True,
        )

        db.add(alumni_user)
        await db.flush()

        db.add(GiverProfile(
            user_id=alumni_user.id,
            headline=f"{role_title} at {comp} | {institutions_data[inst_id-1]['short_name']} Alum",
            bio=f"Working on {domain} at {comp}. Happy to guide motivated students in system architecture and technical interviews.",
            role_title=role_title,
            company=comp,
            domain=domain,
            topics=["System Design", "Mock Interview", "Resume Review", "Career Strategy"],
            offers=["mock_interview", "resume_review", "referral_advice"],
            languages=["English", "Hindi"],
            band=band,
            rating_avg=rating,
            rating_count=sessions_count,
            completion_rate=round(random.uniform(0.92, 1.0), 2),
            weekly_capacity=random.choice([2, 3, 4]),
        ))
        db.add(Availability(
            user_id=alumni_user.id,
            status=avail_status,
            time_window=["18:00-20:00 IST"],
            avg_reply_minutes=random.randint(15, 90),
            response_rate=round(random.uniform(0.85, 0.99), 2),
        ))
        db.add(Capacity(user_id=alumni_user.id, weekly_cap=3, free_monthly_cap=6))
        db.add(CreditWallet(user_id=alumni_user.id, balance=sessions_count * 2, escrow_held=0))
        all_alumni.append(alumni_user)
    await db.commit()

    # --- 6 Faculty Total ---
    print("[+] Seeding 5 additional Faculty members (Total: 6)...")
    faculty_names = [
        ("Dr. Pushpendra Singh", "Professor, Mobile Systems & Ubiquitous Computing", 1),
        ("Dr. Richa Singh", "Professor, Computer Vision & Deep Biometrics", 1),
        ("Dr. Mayank Vatsa", "Professor, Trustworthy Machine Learning & AI", 1),
        ("Dr. Chetan Arora", "Associate Professor, Deep Learning for Vision", 2),
        ("Dr. Preeti Ranjan Panda", "Professor, Embedded Systems & Compilers", 2),
    ]
    for name, title, inst_id in faculty_names:
        inst_domain = "iiitd.ac.in" if inst_id == 1 else "iitd.ac.in"
        slug = name.lower().replace("dr. ", "").replace(" ", ".")
        f_user = User(
            id=uuid.uuid4(),
            email=f"{slug}@{inst_domain}",
            password_hash=hashed_pwd,
            full_name=name,
            role="faculty",
            roles=["faculty"],
            institution_id=inst_id,
            verification_level="verified_professional",
            trust_score=97.0,
            is_active=True,
        )
        db.add(f_user)
        await db.flush()

        db.add(GiverProfile(
            user_id=f_user.id,
            headline=f"{title} | {institutions_data[inst_id-1]['short_name']}",
            bio=f"Academic advisor and researcher at {institutions_data[inst_id-1]['name']}.",
            role_title=title.split(",")[0],
            company=institutions_data[inst_id-1]['name'],
            domain="Computer Science Research",
            topics=["Research Advising", "Thesis Review", "Higher Studies"],
            offers=["domain_talk", "career_guidance"],
            band="top_rated",
            rating_avg=4.92,
            rating_count=random.randint(10, 25),
            weekly_capacity=2,
        ))
        db.add(Availability(user_id=f_user.id, status="available_today"))
        db.add(Capacity(user_id=f_user.id, weekly_cap=2, free_monthly_cap=4))
        db.add(CreditWallet(user_id=f_user.id, balance=0, escrow_held=0))
    await db.commit()

    # --- 5 Recruiters Total ---
    print("[+] Seeding 4 additional Recruiters (Total: 5)...")
    recruiter_list = [
        ("Amit Singhal", "amit.recruiter@microsoft.com", "Microsoft", "University Recruiting Lead"),
        ("Shweta Kulkarni", "shweta.recruiter@google.com", "Google", "Campus Talent Partner"),
        ("Rajesh Nair", "rajesh.recruiter@uber.com", "Uber", "Senior Technical Recruiter"),
        ("Divya Aggarwal", "divya.recruiter@zepto.com", "Zepto", "Head of Early Careers"),
    ]
    for name, email, company, title in recruiter_list:
        r_user = User(
            id=uuid.uuid4(),
            email=email,
            password_hash=hashed_pwd,
            full_name=name,
            role="recruiter",
            roles=["recruiter"],
            institution_id=None,
            verification_level="verified_employer",
            trust_score=92.0,
            is_active=True,
        )
        db.add(r_user)
        await db.flush()
        db.add(GiverProfile(
            user_id=r_user.id,
            headline=f"{title} at {company}",
            company=company,
            role_title=title,
            domain="Campus Hiring",
            topics=["Resume Review", "Hiring Chats"],
            offers=["referral_advice"],
            band="trusted",
            rating_avg=4.8,
            rating_count=10,
        ))
        db.add(Availability(user_id=r_user.id, status="active_now"))
        db.add(Capacity(user_id=r_user.id, weekly_cap=5, free_monthly_cap=10))
        db.add(CreditWallet(user_id=r_user.id, balance=15, escrow_held=0))
    await db.commit()

    # --- 5 Founders Total ---
    print("[+] Seeding 4 additional Founders (Total: 5)...")
    founder_list = [
        ("Tanmai Gopal", "tanmai.founder@hasura.com", "Hasura", "Co-Founder & CEO"),
        ("Bhupinder Singh", "bhupinder.founder@incred.com", "InCred", "Founder & CEO"),
        ("Kaivalya Vohra", "kaivalya.founder@zepto.com", "Zepto", "Co-Founder & CTO"),
        ("Ritesh Arora", "ritesh.founder@browserstack.com", "BrowserStack", "Co-Founder & CEO"),
    ]
    for name, email, company, title in founder_list:
        fnd_user = User(
            id=uuid.uuid4(),
            email=email,
            password_hash=hashed_pwd,
            full_name=name,
            role="founder",
            roles=["founder"],
            institution_id=1,
            verification_level="verified_employer",
            trust_score=96.0,
            is_active=True,
        )
        db.add(fnd_user)
        await db.flush()
        db.add(GiverProfile(
            user_id=fnd_user.id,
            headline=f"{title} at {company}",
            company=company,
            role_title=title,
            domain="High-Growth Startups",
            topics=["Startup 0-to-1", "Product Architecture"],
            offers=["career_guidance"],
            band="top_rated",
            rating_avg=4.95,
            rating_count=20,
        ))
        db.add(Availability(user_id=fnd_user.id, status="available_today"))
        db.add(Capacity(user_id=fnd_user.id, weekly_cap=2, free_monthly_cap=4))
        db.add(CreditWallet(user_id=fnd_user.id, balance=30, escrow_held=0))
    await db.commit()

    # --- Curated Opportunities (Jobs, Referrals, Hackathons, Events) ---
    print("[+] Seeding Verified Opportunities...")
    opps_data = [
        {
            "creator_id": demo_recruiter.id,
            "type": "job",
            "title": "Software Development Engineer Intern (Backend)",
            "description": "Join Razorpay's Core Payments team to build distributed transaction pipelines in Go and Python.",
            "company": "Razorpay",
            "location": "Bengaluru (Hybrid)",
            "skills": ["Go", "Python", "PostgreSQL", "Kafka"],
            "college_affinity_id": 1,
            "url": "https://razorpay.com/careers",
            "is_verified": True,
        },
        {
            "creator_id": demo_founder.id,
            "type": "referral",
            "title": "Founding Systems Engineer Referral",
            "description": "Direct fast-track interview referral for senior undergraduate or recent alumni with strong systems background.",
            "company": "Postman",
            "location": "Bengaluru / Remote",
            "skills": ["TypeScript", "Node.js", "Distributed Systems"],
            "college_affinity_id": 2,
            "url": "https://postman.com/jobs",
            "is_verified": True,
        },
        {
            "creator_id": admin_user.id,
            "type": "hackathon",
            "title": "IIIT Delhi Alumni Innovation Hackathon 2026",
            "description": "48-hour buildathon with $10,000 in prizes, judged by alumni VCs and engineering directors.",
            "company": "IIITD Alumni Association",
            "location": "IIIT Delhi Campus",
            "skills": ["Next.js", "FastAPI", "AI/ML", "pgvector"],
            "college_affinity_id": 1,
            "url": "https://iiitd.ac.in/hackathon2026",
            "is_verified": True,
        },
        {
            "creator_id": demo_alumni.id,
            "type": "event",
            "title": "Cracking Google System Design & L4/L5 Roles - Alumni AMA",
            "description": "Live virtual fireside talk and Q&A covering distributed caching, rate limiters, and consensus protocols.",
            "company": "Google",
            "location": "Virtual (Google Meet)",
            "skills": ["System Design", "Distributed Systems"],
            "college_affinity_id": 1,
            "url": "https://meet.google.com/warmpath-ama",
            "is_verified": True,
        },
    ]
    for o_data in opps_data:
        db.add(Opportunity(id=uuid.uuid4(), **o_data))
    await db.commit()

    # --- Past Completed Sessions & Ratings & Endorsements ---
    print("[+] Seeding Past Completed Sessions, Ratings & Vouches...")
    for idx in range(30):
        student = all_students[(idx + 1) % len(all_students)]
        alumnus = all_alumni[idx % len(all_alumni)]
        is_cross = (student.institution_id != alumnus.institution_id)

        req = Request(
            id=uuid.uuid4(),
            seeker_id=student.id,
            giver_id=alumnus.id,
            status="completed",
            intent_category="mock_interview",
            ask_details=f"Mock interview on system design and resume review session #{idx+1}.",
            scheduled_at=utc_now() - timedelta(days=random.randint(2, 20)),
            credits_locked=1 if is_cross else 0,
            is_cross_college=is_cross,
        )
        db.add(req)
        await db.flush()

        sess = Session(
            id=uuid.uuid4(),
            request_id=req.id,
            giver_id=alumnus.id,
            seeker_id=student.id,
            scheduled_at=req.scheduled_at,
            duration_minutes=45,
            meeting_link="https://meet.jit.si/warmpath-session-demo",
            status="completed",
            completed_at=req.scheduled_at + timedelta(minutes=45),
        )
        db.add(sess)
        await db.flush()

        # Add rating
        score = random.choice([5, 5, 4, 5, 4])
        db.add(Rating(
            id=uuid.uuid4(),
            session_id=sess.id,
            reviewer_id=student.id,
            reviewee_id=alumnus.id,
            score=score,
            tags=["Helpful", "On time", "Clear feedback", "Actionable advice"][:random.randint(2, 4)],
            comment=f"Exceptional guidance! Helped refine my portfolio and explained scalable concurrency patterns clearly.",
            audit_status="normal",
        ))

        # Add alumni vouch on student profile (first 10 sessions)
        if idx < 10:
            db.add(Vouch(
                id=uuid.uuid4(),
                giver_id=alumnus.id,
                student_id=student.id,
                session_id=sess.id,
                vouch_text=f"Demonstrated deep understanding of systems during our mock session. Strongly recommend for backend roles.",
                is_public=True,
            ))

    await db.commit()

    # --- Incoming Active Requests for Demo Alumni ---
    print("[+] Seeding Active Requests & Chats for Demo Accounts...")
    active_req = Request(
        id=uuid.uuid4(),
        seeker_id=demo_student.id,
        giver_id=demo_alumni.id,
        status="pending",
        intent_category="mock_interview",
        ask_details="Hi Vikram! I am preparing for backend SDE interviews. Would love a 45-min mock system design session on high-concurrency rate limiters.",
        credits_locked=0,
        is_cross_college=False,
    )
    db.add(active_req)
    await db.flush()

    db.add(RequestMessage(
        id=uuid.uuid4(),
        request_id=active_req.id,
        sender_id=demo_student.id,
        recipient_id=demo_alumni.id,
        content="Hello Vikram, thank you for making time for students! I have reviewed your Google talks on distributed storage.",
    ))

    # --- Pending Verifications & Moderation Queue ---
    print("[+] Seeding Pending Verifications and Moderation Reports...")
    pending_alumnus = User(
        id=uuid.uuid4(),
        email="pending.alumni@iiitd.ac.in",
        password_hash=hashed_pwd,
        full_name="Kavita Saxena",
        role="alumni",
        roles=["alumni"],
        institution_id=1,
        verification_level="pending",
        trust_score=50.0,
        is_active=True,
    )
    db.add(pending_alumnus)
    await db.flush()
    db.add(GiverProfile(
        user_id=pending_alumnus.id,
        headline="Senior DevOps Engineer at Atlassian | Degree upload pending",
        company="Atlassian",
        role_title="Senior DevOps Engineer",
    ))
    db.add(VerificationRequest(

        id=uuid.uuid4(),
        user_id=pending_alumnus.id,
        institution_id=1,
        request_type="document_review",
        document_ref="degree_kavita_saxena_2020.pdf",
        document_type="degree_certificate",
        status="pending",
        review_notes="Degree certificate uploaded by applicant. Match pending admin review against archived roll sheets.",
    ))


    # Moderation report
    db.add(Report(
        id=uuid.uuid4(),
        reporter_id=demo_student.id,
        reported_user_id=all_students[5].id,
        context_type="chat",
        context_id="msg-101",
        reason="Suspicious off-platform payment request",
        description="User asked to transfer 500 INR via UPI handle rather than in-app platform escrow.",
        status="pending",
    ))

    # Scam Rules
    print("[+] Seeding Scam Detection Rules...")
    scam_rules = [
        (r"(\+91[\-\s]?)?[6-9]\d{9}", "regex", "block", "Phone number leak detected in chat"),
        (r"[\w\.-]+@[\w\.-]+\.\w+", "regex", "flag", "Personal email address leak detected in chat"),
        (r"[\w\.\-_]+@(okaxis|okhdfcbank|oksbi|paytm|upi|ybl)", "regex", "block", "External UPI payment handle detected in chat"),
        (r"(t\.me\/|telegram\.me\/|wa\.me\/|chat\.whatsapp\.com\/)", "regex", "block", "Off-platform external messenger link detected"),
    ]
    for pattern, r_type, sev, reason in scam_rules:
        db.add(ScamRule(id=uuid.uuid4(), pattern=pattern, rule_type=r_type, severity=sev, reason=reason, is_active=True))

    # Notifications
    print("[+] Seeding Initial Notifications...")
    db.add(Notification(
        id=uuid.uuid4(),
        user_id=demo_student.id,
        title="Welcome to WarmPath!",
        message="Your IIIT Delhi institutional student account is verified. Complete your intent profile to receive personalized alumni recommendations.",
        type="system",
        is_read=False,
    ))
    db.add(Notification(
        id=uuid.uuid4(),
        user_id=demo_alumni.id,
        title="New Mentorship Request",
        message="Aarav Sharma (3rd Year CSE) requested a Mock Interview session with you.",
        type="request",
        is_read=False,
    ))

    await db.commit()
    print("[SUCCESS] WarmPath database successfully seeded!")
    print(f"    - Admin:    admin@iiitd.ac.in (pwd: {DEFAULT_PASSWORD})")
    print(f"    - Student:  aarav.sharma@iiitd.ac.in (pwd: {DEFAULT_PASSWORD})")
    print(f"    - Alumni:   vikram.malhotra@alumni.iiitd.ac.in (pwd: {DEFAULT_PASSWORD})")
    print(f"    - Faculty:  dr.pankaj@iiitd.ac.in (pwd: {DEFAULT_PASSWORD})")
    print(f"    - Recruiter: priya.recruiter@razorpay.com (pwd: {DEFAULT_PASSWORD})")
    print(f"    - Founder:  kunal.founder@postman.com (pwd: {DEFAULT_PASSWORD})")


if __name__ == "__main__":
    asyncio.run(run_seed())
