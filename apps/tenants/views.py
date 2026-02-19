# apps/tenants/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django_tenants.utils import schema_context
from django.contrib.auth import get_user_model
from .serializers import TenantCreateSerializer
from .models import Client, Domain

User = get_user_model()

class TenantCreateAPIView(APIView):
    """
    Create a tenant using data passed through the API.
    """
    def post(self, request):
        serializer = TenantCreateSerializer(data=request.data)
        if serializer.is_valid():
            data = serializer.validated_data

            # 1️⃣ Create Tenant
            tenant = Client.objects.create(
                name=data['name'],
                schema_name=data['schema_name'],
                paid_until="2099-12-31",  # optional
                on_trial=True
            )

            # 2️⃣ Create Domain
            Domain.objects.create(
                domain=data['domain_url'],
                tenant=tenant,
                is_primary=True
            )

            # 3️⃣ Create Superuser in tenant schema using API-provided data
            with schema_context(tenant.schema_name):
                if User.objects.filter(username=data['owner_username']).exists():
                    return Response(
                        {"error": "Username already exists in tenant schema"},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                User.objects.create_superuser(
                    username=data['owner_username'],
                    email=data['owner_email'],
                    password=data['owner_password']
                )

            return Response({
                "message": "Tenant created successfully!",
                "schema_name": tenant.schema_name,
                "domain_url": data['domain_url'],
                "admin_username": data['owner_username']
            }, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
