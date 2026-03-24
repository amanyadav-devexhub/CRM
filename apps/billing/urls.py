from django.urls import path
from .views import BillingListView, BillingCreateView, BillingDetailView
from .stripe_views import CreateCheckoutSessionView, StripeWebhookView

app_name = 'billing'

urlpatterns = [
    path('', BillingListView.as_view(), name='billing-list'),
    path('create/', BillingCreateView.as_view(), name='billing-create'),
    path('<uuid:pk>/', BillingDetailView.as_view(), name='billing-detail'),
    
    # Stripe Integration
    path('stripe/checkout/', CreateCheckoutSessionView.as_view(), name='stripe-checkout'),
    path('stripe/webhook/', StripeWebhookView.as_view(), name='stripe-webhook'),
]
