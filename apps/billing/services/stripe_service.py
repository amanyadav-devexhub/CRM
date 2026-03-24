import stripe
from django.conf import settings
from django.urls import reverse

stripe.api_key = settings.STRIPE_SECRET_KEY

class StripeService:
    @staticmethod
    def sync_catalog_item(item):
        """
        Synchronizes a ServiceCatalog or SubscriptionPlan with Stripe.
        Returns the (product_id, price_id).
        """
        # 1. Create or retrieve Product
        product_name = getattr(item, 'name', 'Service')
        product_description = getattr(item, 'description', '')
        
        # Check if we already have a product ID stored
        # For simplicity, we create a new one if not found
        # In a real app, you'd check StripeProductMapping
        
        product = stripe.Product.create(
            name=product_name,
            description=product_description,
            active=item.is_active
        )
        
        # 2. Create Price
        # Unit amount is in cents
        unit_amount = int(item.price * 100) 
        currency = getattr(settings, 'STRIPE_CURRENCY', 'inr').lower()
        
        price_kwargs = {
            "unit_amount": unit_amount,
            "currency": currency,
            "product": product.id,
        }
        
        # If it's a SubscriptionPlan, add recurring interval
        if hasattr(item, 'billing_cycle'):
            interval = 'month' if item.billing_cycle == 'MONTHLY' else 'year'
            price_kwargs["recurring"] = {"interval": interval}

        price = stripe.Price.create(**price_kwargs)
        
        # 3. Update local item with Price ID
        item.stripe_price_id = price.id
        item.save()
        
        return product.id, price.id

    @staticmethod
    def update_stripe_status(item):
        """Toggles Stripe Product active status based on Django item."""
        if not item.stripe_price_id:
            return
            
        try:
            price = stripe.Price.retrieve(item.stripe_price_id)
            stripe.Product.modify(
                price.product,
                active=item.is_active
            )
        except stripe.error.StripeError:
            pass

    @staticmethod
    def create_checkout_session(invoice_or_plan, success_url, cancel_url, customer_email=None):
        """Creates a Stripe Checkout Session."""
        if hasattr(invoice_or_plan, 'stripe_price_id') and invoice_or_plan.stripe_price_id:
            # Single item checkout (e.g. for Subscription Plan)
            line_items = [{
                'price': invoice_or_plan.stripe_price_id,
                'quantity': 1,
            }]
            mode = 'subscription' if hasattr(invoice_or_plan, 'billing_cycle') else 'payment'
        else:
            # Ad-hoc invoice checkout (multiple items)
            # This is a bit more complex, for now we assume one total amount
            line_items = [{
                'price_data': {
                    'currency': 'inr',
                    'product_data': {
                        'name': f"Invoice {invoice_or_plan.invoice_number}",
                    },
                    'unit_amount': int(invoice_or_plan.grand_total * 100),
                },
                'quantity': 1,
            }]
            mode = 'payment'

        session_kwargs = {
            'payment_method_types': ['card'],
            'line_items': line_items,
            'mode': mode,
            'success_url': success_url,
            'cancel_url': cancel_url,
        }
        
        if customer_email:
            session_kwargs['customer_email'] = customer_email

        session = stripe.checkout.Session.create(**session_kwargs)
        return session
