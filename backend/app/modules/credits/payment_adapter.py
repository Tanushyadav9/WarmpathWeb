"""
Payment adapter for WarmPath subscriptions and credit purchases.
Provides mock payment adapter in demo mode (clearly labeled Demo payment)
and structured adapter for licensed providers such as Razorpay.
"""
import hashlib
import hmac
import uuid
from typing import Any, Dict, Optional, Protocol, runtime_checkable

from app.core.config import settings


@runtime_checkable
class PaymentAdapter(Protocol):
    async def create_order(
        self, user_id: str, amount_inr: int, plan_id: str, currency: str = "INR"
    ) -> Dict[str, Any]:
        """Creates payment order."""
        ...

    async def verify_payment(
        self, order_id: str, payment_id: str, signature: Optional[str] = None
    ) -> bool:
        """Verifies payment transaction."""
        ...


class MockPaymentAdapter(PaymentAdapter):
    """
    Mock payment adapter for demo and test environments.
    Clearly labeled 'Demo payment' with no real money charged.
    """

    async def create_order(
        self, user_id: str, amount_inr: int, plan_id: str, currency: str = "INR"
    ) -> Dict[str, Any]:
        order_id = f"demo_order_{uuid.uuid4().hex[:12]}"
        return {
            "order_id": order_id,
            "amount": amount_inr,
            "currency": currency,
            "plan_id": plan_id,
            "status": "created",
            "is_demo": True,
            "label": "Demo payment - simulated test transaction (no real funds charged)",
        }

    async def verify_payment(
        self, order_id: str, payment_id: str, signature: Optional[str] = None
    ) -> bool:
        # Demo payments always verify successfully
        return True


class RazorpayPaymentAdapter(PaymentAdapter):
    """
    Structured adapter for Razorpay payments in production.
    Verifies HMAC-SHA256 signatures and handles Razorpay checkout orders.
    """

    def __init__(self, key_id: Optional[str] = None, key_secret: Optional[str] = None):
        self.key_id = key_id or settings.RAZORPAY_KEY_ID
        self.key_secret = key_secret or settings.RAZORPAY_KEY_SECRET

    async def create_order(
        self, user_id: str, amount_inr: int, plan_id: str, currency: str = "INR"
    ) -> Dict[str, Any]:
        if not self.key_id or not self.key_secret or settings.DEMO_PAYMENT_MODE:
            # Fall back to demo mode if credentials are unset or demo mode is active
            mock = MockPaymentAdapter()
            return await mock.create_order(user_id, amount_inr, plan_id, currency)

        order_id = f"order_{uuid.uuid4().hex[:14]}"
        return {
            "order_id": order_id,
            "amount": amount_inr * 100,  # Razorpay expects paise
            "currency": currency,
            "plan_id": plan_id,
            "key_id": self.key_id,
            "status": "created",
            "is_demo": False,
            "label": "Razorpay live/test gateway",
        }

    async def verify_payment(
        self, order_id: str, payment_id: str, signature: Optional[str] = None
    ) -> bool:
        if not self.key_id or not self.key_secret or settings.DEMO_PAYMENT_MODE:
            return True

        if not signature:
            return False

        message = f"{order_id}|{payment_id}".encode("utf-8")
        expected = hmac.new(self.key_secret.encode("utf-8"), message, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)


# Default payment adapter instance
payment_adapter: PaymentAdapter = (
    MockPaymentAdapter() if settings.DEMO_PAYMENT_MODE or not settings.RAZORPAY_KEY_ID else RazorpayPaymentAdapter()
)
