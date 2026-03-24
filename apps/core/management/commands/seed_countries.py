from django.core.management.base import BaseCommand
from apps.core.models import Country

class Command(BaseCommand):
    help = "Seed initial countries and dial codes"

    def handle(self, *args, **options):
        countries = [
            {"name": "India", "dial_code": "+91", "iso_code": "IN"},
            {"name": "United States", "dial_code": "+1", "iso_code": "US"},
            {"name": "United Kingdom", "dial_code": "+44", "iso_code": "GB"},
            {"name": "United Arab Emirates", "dial_code": "+971", "iso_code": "AE"},
            {"name": "Australia", "dial_code": "+61", "iso_code": "AU"},
            {"name": "Canada", "dial_code": "+1", "iso_code": "CA"},
            {"name": "Singapore", "dial_code": "+65", "iso_code": "SG"},
            {"name": "Germany", "dial_code": "+49", "iso_code": "DE"},
            {"name": "France", "dial_code": "+33", "iso_code": "FR"},
        ]

        for country_data in countries:
            iso_lower = country_data["iso_code"].lower()
            flag_url = f"https://flagcdn.com/w320/{iso_lower}.png"
            
            Country.objects.update_or_create(
                iso_code=country_data["iso_code"],
                defaults={
                    "name": country_data["name"],
                    "dial_code": country_data["dial_code"],
                    "flag_url": flag_url,
                    "status": True
                }
            )
            self.stdout.write(f"Updated {country_data['name']} with flag logo.")
