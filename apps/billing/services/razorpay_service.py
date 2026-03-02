import razorpay
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class RazorpayService:
    def __init__(self):
        self.client = razorpay.Client(
            auth=(
                getattr(settings, "RAZORPAY_KEY_ID", ""),
                getattr(settings, "RAZORPAY_KEY_SECRET", "")
            )
        )

    def create_order(self, amount_in_inr, currency="INR"):
        """
        Create a Razorpay Order.
        Amount should be in INR (human readable), converted to paise for Razorpay.
        """
        try:
            amount_in_paise = int(float(amount_in_inr) * 100)
            data = {
                "amount": amount_in_paise,
                "currency": currency,
                "payment_capture": 1  # Auto-capture
            }
            order = self.client.order.create(data=data)
            return order
        except Exception as e:
            logger.error(f"Razorpay Order creation failed: {e}")
            return None

    def verify_signature(self, razorpay_order_id, razorpay_payment_id, razorpay_signature):
        """
        Verify the Razorpay payment signature.
        """
        try:
            params_dict = {
                'razorpay_order_id': razorpay_order_id,
                'razorpay_payment_id': razorpay_payment_id,
                'razorpay_signature': razorpay_signature
            }
            self.client.utility.verify_payment_signature(params_dict)
            return True
        except Exception as e:
            logger.error(f"Razorpay signature verification failed: {e}")
            return False
