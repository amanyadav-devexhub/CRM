import stripe
import json
from django.conf import settings
from django.http import JsonResponse, HttpResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.shortcuts import get_object_or_404, redirect
from apps.billing.models import Invoice, Payment
from apps.tenants.models import SubscriptionPlan, TenantSubscription
from apps.billing.services.stripe_service import StripeService

stripe.api_key = settings.STRIPE_SECRET_KEY

class CreateCheckoutSessionView(View):
    """
    Creates a Checkout Session and redirects user to Stripe.
    Handles both Invoices (one-time) and Subscription Plans (recurring).
    """
    def post(self, request, *args, **kwargs):
        object_type = request.POST.get("type") # 'invoice' or 'plan'
        object_id = request.POST.get("id")
        
        # Determine URLs
        base_url = f"{request.scheme}://{request.get_host()}"
        success_url = base_url + "/dashboard/billing/success/"
        cancel_url = base_url + "/dashboard/billing/cancel/"
        
        if object_type == "invoice":
            obj = get_object_or_404(Invoice, pk=object_id)
            success_url = base_url + f"/dashboard/billing/{obj.id}/?payment=success"
        else:
            obj = get_object_or_404(SubscriptionPlan, pk=object_id)
            success_url = base_url + "/dashboard/?subscription=success"

        session = StripeService.create_checkout_session(
            obj, 
            success_url=success_url, 
            cancel_url=cancel_url,
            customer_email=request.user.email
        )
        
        # Save session ID to track locally
        if object_type == "invoice":
            obj.stripe_checkout_id = session.id
            obj.save()

        return redirect(session.url, code=303)

@method_decorator(csrf_exempt, name='dispatch')
class StripeWebhookView(View):
    """
    Handles Stripe webhooks (e.g., checkout.session.completed).
    """
    def post(self, request, *args, **kwargs):
        payload = request.body
        sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
        endpoint_secret = settings.STRIPE_WEBHOOK_SECRET

        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, endpoint_secret
            )
        except (ValueError, stripe.error.SignatureVerificationError):
            return HttpResponse(status=400)

        # Handle the event
        if event['type'] == 'checkout.session.completed':
            session = event['data']['object']
            self._handle_successful_payment(session)

        return HttpResponse(status=200)

    def _handle_successful_payment(self, session):
        """Processes a successful checkout session."""
        checkout_id = session.id
        payment_intent = session.payment_intent
        
        # 1. Try to find local Invoice
        invoice = Invoice.objects.filter(stripe_checkout_id=checkout_id).first()
        if invoice:
            Payment.objects.create(
                invoice=invoice,
                amount=invoice.grand_total,
                method='ONLINE',
                transaction_ref=payment_intent,
                stripe_payment_intent_id=payment_intent,
            )
            invoice.status = 'PAID'
            invoice.save()
            return

        # 2. Try to find subscription metadata (if any)
        # In a real app, you'd use Stripe Customer ID or metadata to map back
        pass
