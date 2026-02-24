# apps/tenants/serializers.py
from rest_framework import serializers
from .models import Client, Domain

class TenantCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100)
    schema_name = serializers.CharField(max_length=50)
    domain_url = serializers.CharField(max_length=100)
    owner_email = serializers.EmailField()
    owner_password = serializers.CharField(write_only=True)

    def validate_schema_name(self, value):
        if Client.objects.filter(schema_name=value).exists():
            raise serializers.ValidationError("Schema name already exists.")
        return value

    def validate_domain_url(self, value):
        if Domain.objects.filter(domain=value).exists():
            raise serializers.ValidationError("Domain URL already exists.")
        return value
