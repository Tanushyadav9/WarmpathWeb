"""
scripts/perf/locustfile.py - Locust Performance & Load Test Suite for WarmPath.
Simulates real student seekers, alumni givers, OTP authentication via Mailpit,
presence checks, session requests, and signed Razorpay payment webhooks.
"""

import hashlib
import hmac
import json
import os
import random
import re
import time
import uuid
from pathlib import Path
from typing import Optional
from locust import HttpUser, between, task, events

# Configuration & Defaults
MAILPIT_URL = os.environ.get("MAILPIT_URL", "http://localhost:8025")
RAZORPAY_SECRET = os.environ.get("RAZORPAY_WEBHOOK_SECRET", "test_webhook_secret_warmpath")
MANIFEST_PATH = Path(__file__).resolve().parent / "load_ids.json"

# Load seeded test IDs if available
TEST_GIVER_IDS = []
TEST_STUDENT_IDS = []
if MANIFEST_PATH.exists():
    try:
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        TEST_GIVER_IDS = manifest.get("givers", [])
        TEST_STUDENT_IDS = manifest.get("students", [])
    except Exception:
        pass


def sign_razorpay_payload(payload_bytes: bytes, secret: str) -> str:
    """Computes HMAC-SHA256 signature for Razorpay webhooks."""
    return hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()


class StudentSeekerUser(HttpUser):
    wait_time = between(0.8, 2.5)

    def on_start(self):
        """Authenticates the student via real OTP flow (or test token)."""
        self.user_index = random.randint(1, 500)
        self.email = f"student_{self.user_index:04d}@loadtest.warmpath.org"
        self.user_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, self.email))
        self.token = None
        self.login_via_otp()

    def login_via_otp(self):
        """Requests OTP, fetches code from Mailpit API, and verifies token."""
        try:
            # 1. Request OTP
            req_resp = self.client.post(
                "/auth/request-otp",
                json={"email": self.email},
                name="[Auth] POST /auth/request-otp",
            )

            otp_code = None
            # 2. Extract code from Mailpit API
            if req_resp.status_code in [200, 201]:
                time.sleep(0.1)  # small pause for message delivery
                try:
                    import urllib.request
                    mailpit_endpoint = f"{MAILPIT_URL}/api/v1/messages"
                    req = urllib.request.Request(mailpit_endpoint, headers={"Accept": "application/json"})
                    with urllib.request.urlopen(req, timeout=3.0) as resp:
                        data = json.loads(resp.read().decode("utf-8"))
                        messages = data.get("messages", [])
                        for msg in messages:
                            to_list = [t.get("Address", "") for t in msg.get("To", [])]
                            if self.email in to_list:
                                msg_id = msg.get("ID")
                                # Fetch message body
                                with urllib.request.urlopen(f"{MAILPIT_URL}/api/v1/message/{msg_id}") as b_resp:
                                    b_data = json.loads(b_resp.read().decode("utf-8"))
                                    body_text = b_data.get("Text", "") or b_data.get("HTML", "")
                                    match = re.search(r"\b(\d{6})\b", body_text)
                                    if match:
                                        otp_code = match.group(1)
                                        break
                except Exception:
                    pass

            # Fallback code for test environments if Mailpit is unreachable
            otp_code = otp_code or "123456"

            # 3. Verify OTP
            verify_resp = self.client.post(
                "/auth/verify-otp",
                json={"email": self.email, "otp": otp_code},
                name="[Auth] POST /auth/verify-otp",
            )
            if verify_resp.status_code == 200:
                self.token = verify_resp.json().get("access_token")
                self.client.headers.update({"Authorization": f"Bearer {self.token}"})
            else:
                # Set X-User-Id header for mock/dev fallback
                self.client.headers.update({"X-User-Id": self.user_id})
        except Exception:
            self.client.headers.update({"X-User-Id": self.user_id})

    @task(35)
    def get_own_college_recommendations(self):
        """High-frequency browse: own-college alumni recommendations feed."""
        self.client.get(
            "/recommendations?scope=own_college&limit=10",
            name="[Matching] GET /recommendations?scope=own_college",
        )

    @task(15)
    def get_cross_college_recommendations(self):
        """Cross-college discovery feed (may return locked cards for standard plan)."""
        self.client.get(
            "/recommendations?scope=cross_college&limit=10",
            name="[Matching] GET /recommendations?scope=cross_college",
        )

    @task(25)
    def view_giver_card(self):
        """Viewing a public giver card (exercises hot-reads cache & why_lines)."""
        giver_id = random.choice(TEST_GIVER_IDS) if TEST_GIVER_IDS else str(uuid.uuid4())
        self.client.get(
            f"/givers/{giver_id}",
            name="[Matching] GET /givers/{id}",
        )

    @task(15)
    def check_presence(self):
        """Polling real-time mentor presence status."""
        self.client.get(
            "/presence",
            name="[Availability] GET /presence",
        )

    @task(10)
    def request_session(self):
        """Requesting a mentorship session with an alumnus."""
        giver_id = random.choice(TEST_GIVER_IDS) if TEST_GIVER_IDS else str(uuid.uuid4())
        idempotency_key = str(uuid.uuid4())
        self.client.post(
            "/requests",
            json={
                "giver_id": giver_id,
                "help_type": "resume_review",
                "message": "Hi, I would love feedback on my backend resume.",
            },
            headers={"Idempotency-Key": idempotency_key},
            name="[Sessions] POST /requests",
        )


class PaymentWebhookUser(HttpUser):
    wait_time = between(3.0, 8.0)

    @task
    def post_razorpay_webhook(self):
        """Exercises signed Razorpay payment webhook processing."""
        payment_id = f"pay_{uuid.uuid4().hex[:14]}"
        user_id = str(uuid.uuid4())
        payload_dict = {
            "entity": "event",
            "event": "payment.captured",
            "contains": ["payment"],
            "payload": {
                "payment": {
                    "entity": {
                        "id": payment_id,
                        "amount": 49900,  # 499 INR in paise
                        "currency": "INR",
                        "status": "captured",
                        "notes": {"user_id": user_id, "plan": "High"},
                    }
                }
            },
        }
        payload_bytes = json.dumps(payload_dict).encode("utf-8")
        signature = sign_razorpay_payload(payload_bytes, RAZORPAY_SECRET)

        self.client.post(
            "/webhooks/razorpay",
            data=payload_bytes,
            headers={
                "Content-Type": "application/json",
                "X-Razorpay-Signature": signature,
            },
            name="[Payments] POST /webhooks/razorpay",
        )
