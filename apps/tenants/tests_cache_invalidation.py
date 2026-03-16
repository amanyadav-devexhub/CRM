from django.test import TestCase
from django.core.cache import cache
from apps.tenants.models import Tenant, SubscriptionPlan, Feature, PlanFeature, TenantFeature, TenantSubscription, Client
from django.utils import timezone
from datetime import timedelta

class CacheInvalidationTest(TestCase):
    def setUp(self):
        cache.clear()
        # Setup base objects
        self.client_obj = Client.objects.create(name="Test Client", schema_name="test_schema")
        self.tenant = Tenant.objects.create(
            name="Test Clinic",
            subdomain="testclinic",
            client=self.client_obj,
            category="CLINIC"
        )
        self.plan = SubscriptionPlan.objects.create(
            name="BASIC",
            display_name="Basic Plan",
            price=100
        )
        self.subscription = TenantSubscription.objects.create(
            tenant=self.tenant,
            plan=self.plan,
            status="ACTIVE",
            end_date=timezone.now() + timedelta(days=30)
        )
        self.feature = Feature.objects.create(code="patients", name="Patients", is_active=True)

    def test_plan_feature_invalidation(self):
        # Initial state: feature not in plan
        self.assertFalse(self.tenant.has_feature("patients"))
        
        # Manually cache it as False
        cache_key = f"tenant_feature_{self.tenant.id}_patients"
        self.assertFalse(cache.get(cache_key))

        # Add feature to plan
        PlanFeature.objects.create(plan=self.plan, feature=self.feature)
        
        # Cache should be cleared
        self.assertIsNone(cache.get(cache_key))
        
        # Now should be True
        self.assertTrue(self.tenant.has_feature("patients"))

    def test_tenant_feature_override_invalidation(self):
        # Initial state: feature not in plan
        self.assertFalse(self.tenant.has_feature("patients"))
        
        # Manually cache it
        self.tenant.has_feature("patients")
        cache_key = f"tenant_feature_{self.tenant.id}_patients"
        self.assertIsNotNone(cache.get(cache_key))

        # Override for tenant
        TenantFeature.objects.create(tenant=self.tenant, feature_name="patients", is_enabled=True)
        
        # Cache should be cleared
        self.assertIsNone(cache.get(cache_key))
        
        # Now should be True
        self.assertTrue(self.tenant.has_feature("patients"))

    def test_plan_change_invalidation(self):
        # Feature in Premium plan, not Basic
        premium_plan = SubscriptionPlan.objects.create(name="PREMIUM", display_name="Premium Plan", price=500)
        PlanFeature.objects.create(plan=premium_plan, feature=self.feature)
        
        # Currently on Basic
        self.assertFalse(self.tenant.has_feature("patients"))
        cache_key = f"tenant_feature_{self.tenant.id}_patients"
        
        # Change plan
        self.subscription.plan = premium_plan
        self.subscription.save()
        
        # Cache should be cleared
        self.assertIsNone(cache.get(cache_key))
        
        # Now should be True
        self.assertTrue(self.tenant.has_feature("patients"))
