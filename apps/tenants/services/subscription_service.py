from django.utils import timezone
from django.db import transaction
from datetime import timedelta
from apps.tenants.models import SubscriptionPlan, TenantSubscription


class SubscriptionService:

    # ---------------------------------------------------
    # 1️⃣ Create Subscription (New Tenant)
    # ---------------------------------------------------
    @staticmethod
    @transaction.atomic
    def create_subscription(tenant, plan_name, trial=False):
        plan = SubscriptionPlan.objects.get(name=plan_name)

        start_date = timezone.now()
        end_date = start_date + timedelta(days=plan.duration_days)

        status = "TRIAL" if trial else "ACTIVE"

        subscription = TenantSubscription.objects.create(
            tenant=tenant,
            plan=plan,
            status=status,
            start_date=start_date,
            end_date=end_date,
            trial=trial
        )

        return subscription

    # ---------------------------------------------------
    # 2️⃣ Upgrade / Downgrade Plan
    # ---------------------------------------------------
    @staticmethod
    @transaction.atomic
    def change_plan(tenant, new_plan_name):
        subscription = tenant.subscription
        new_plan = SubscriptionPlan.objects.get(name=new_plan_name)

        subscription.plan = new_plan
        subscription.start_date = timezone.now()
        subscription.end_date = timezone.now() + timedelta(days=new_plan.duration_days)
        subscription.status = "ACTIVE"
        subscription.save()

        return subscription

    # ---------------------------------------------------
    # 3️⃣ Cancel Subscription
    # ---------------------------------------------------
    @staticmethod
    def cancel_subscription(tenant):
        subscription = tenant.subscription
        subscription.status = "CANCELLED"
        subscription.save()
        return subscription

    # ---------------------------------------------------
    # 4️⃣ Suspend Subscription
    # ---------------------------------------------------
    @staticmethod
    def suspend_subscription(tenant):
        subscription = tenant.subscription
        subscription.status = "SUSPENDED"
        subscription.save()
        return subscription

    # ---------------------------------------------------
    # 5️⃣ Renew Subscription
    # ---------------------------------------------------
    @staticmethod
    def renew_subscription(tenant):
        subscription = tenant.subscription
        plan = subscription.plan

        subscription.start_date = timezone.now()
        subscription.end_date = timezone.now() + timedelta(days=plan.duration_days)
        subscription.status = "ACTIVE"
        subscription.save()

        return subscription

    # ---------------------------------------------------
    # 6️⃣ Check Feature Access
    # ---------------------------------------------------
    @staticmethod
    def has_feature(tenant, feature_name):
        subscription = tenant.subscription
        plan = subscription.plan

        if not subscription.is_active():
            return False

        feature_map = {
            "AI": plan.ai_enabled,
            "LAB": plan.lab_module_enabled,
            "PHARMACY": plan.pharmacy_module_enabled,
        }

        return feature_map.get(feature_name.upper(), False)

    # ---------------------------------------------------
    # 7️⃣ Check Subscription Validity
    # ---------------------------------------------------
    @staticmethod
    def is_subscription_valid(tenant):
        subscription = tenant.subscription

        if subscription.status in ["CANCELLED", "SUSPENDED"]:
            return False

        if subscription.end_date < timezone.now():
            subscription.status = "EXPIRED"
            subscription.save()
            return False

        return True
