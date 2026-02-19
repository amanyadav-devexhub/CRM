from apps.tenants.models import Tenant, SubscriptionPlan
from apps.accounts.models import User
from django.db import transaction

class TenantService:

    @staticmethod
    @transaction.atomic
    def create_tenant(data):
        # 1️⃣ Create tenant
        tenant = Tenant.objects.create(
            name=data["clinic_name"],
            subdomain=data["subdomain"],
            email=data["email"],
            phone=data["phone"],
        )

        # 2️⃣ Assign subscription plan
        plan = SubscriptionPlan.objects.get(name=data["plan"])
        tenant.subscriptionplan = plan
        tenant.save()

        # 3️⃣ Create default admin user
        admin_user = User.objects.create_user(
            email=data["email"],
            password="Temp@1234",
            tenant=tenant,
            role="ADMIN"
        )

        # 4️⃣ Initialize default configuration
        # Example: enable basic modules
        # TenantConfiguration.objects.create(...)

        return tenant
