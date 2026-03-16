import os
import django
import sys

# Add current directory to path
sys.path.append(os.getcwd())

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.inventory.models import ItemType
from apps.tenants.models import Client
from django_tenants.utils import schema_context

def check():
    clients = Client.objects.all()
    print(f"Total clients found: {clients.count()}")
    for client in clients:
        with schema_context(client.schema_name):
            count = ItemType.objects.filter(is_active=True).count()
            print(f"Schema: {client.schema_name}, Active ItemType count: {count}")

if __name__ == "__main__":
    check()
