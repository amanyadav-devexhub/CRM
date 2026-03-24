from django.core.management.base import BaseCommand
from apps.core.models import Currency, Language, Timezone, DateFormat, Country

class Command(BaseCommand):
    help = "Seed Currencies, Languages, Timezones, and Date Formats"

    def handle(self, *args, **options):
        # 1. Date Formats
        date_formats = [
            {"format_code": "DD/MM/YYYY", "label": "Day/Month/Year (23/03/2026)"},
            {"format_code": "MM/DD/YYYY", "label": "Month/Day/Year (03/23/2026)"},
            {"format_code": "YYYY-MM-DD", "label": "Year-Month-Day (2026-03-23)"},
            {"format_code": "DD-MMM-YYYY", "label": "Day-MonthName-Year (23-Mar-2026)"},
        ]
        for df in date_formats:
            DateFormat.objects.get_or_create(format_code=df["format_code"], defaults={"label": df["label"]})
        self.stdout.write(self.style.SUCCESS("Seeded Date Formats"))

        # 2. Currencies
        currencies = [
            {"code": "INR", "name": "Indian Rupee", "symbol": "₹"},
            {"code": "USD", "name": "US Dollar", "symbol": "$"},
            {"code": "EUR", "name": "Euro", "symbol": "€"},
            {"code": "GBP", "name": "British Pound", "symbol": "£"},
            {"code": "AED", "name": "UAE Dirham", "symbol": "د.إ"},
            {"code": "SGD", "name": "Singapore Dollar", "symbol": "S$"},
            {"code": "AUD", "name": "Australian Dollar", "symbol": "A$"},
            {"code": "CAD", "name": "Canadian Dollar", "symbol": "C$"},
        ]
        for c in currencies:
            Currency.objects.get_or_create(code=c["code"], defaults={"name": c["name"], "symbol": c["symbol"]})
        self.stdout.write(self.style.SUCCESS("Seeded Currencies"))

        # 3. Languages
        languages = [
            {"code": "en", "name": "English", "native_name": "English"},
            {"code": "hi", "name": "Hindi", "native_name": "हिन्दी"},
            {"code": "ar", "name": "Arabic", "native_name": "العربية"},
            {"code": "fr", "name": "French", "native_name": "Français"},
            {"code": "de", "name": "German", "native_name": "Deutsch"},
            {"code": "es", "name": "Spanish", "native_name": "Español"},
        ]
        for l in languages:
            Language.objects.get_or_create(code=l["code"], defaults={"name": l["name"], "native_name": l["native_name"]})
        self.stdout.write(self.style.SUCCESS("Seeded Languages"))

        # 4. Timezones (Common ones)
        timezones = [
            {"name": "Asia/Kolkata", "offset": "GMT+5:30"},
            {"name": "UTC", "offset": "GMT+0:00"},
            {"name": "America/New_York", "offset": "GMT-5:00"},
            {"name": "Europe/London", "offset": "GMT+0:00"},
            {"name": "Asia/Dubai", "offset": "GMT+4:00"},
            {"name": "Asia/Singapore", "offset": "GMT+8:00"},
            {"name": "Australia/Sydney", "offset": "GMT+11:00"},
            {"name": "Europe/Paris", "offset": "GMT+1:00"},
            {"name": "Europe/Berlin", "offset": "GMT+1:00"},
        ]
        for tz in timezones:
            Timezone.objects.get_or_create(name=tz["name"], defaults={"offset_label": tz["offset"]})
        self.stdout.write(self.style.SUCCESS("Seeded Timezones"))

        # 5. Link Countries to Defaults
        country_defaults = {
            "IN": {"cur": "INR", "lang": "hi", "tz": "Asia/Kolkata"},
            "US": {"cur": "USD", "lang": "en", "tz": "America/New_York"},
            "GB": {"cur": "GBP", "lang": "en", "tz": "Europe/London"},
            "AE": {"cur": "AED", "lang": "ar", "tz": "Asia/Dubai"},
            "AU": {"cur": "AUD", "lang": "en", "tz": "Australia/Sydney"},
            "CA": {"cur": "CAD", "lang": "en", "tz": "America/New_York"}, # Approximation
            "SG": {"cur": "SGD", "lang": "en", "tz": "Asia/Singapore"},
            "DE": {"cur": "EUR", "lang": "de", "tz": "Europe/Berlin"},
            "FR": {"cur": "EUR", "lang": "fr", "tz": "Europe/Paris"},
        }

        for iso, defs in country_defaults.items():
            try:
                country = Country.objects.get(iso_code=iso)
                country.primary_currency = Currency.objects.get(code=defs["cur"])
                country.primary_language = Language.objects.get(code=defs["lang"])
                country.primary_timezone = Timezone.objects.get(name=defs["tz"])
                country.save()
                self.stdout.write(f"Updated defaults for {country.name}")
            except Country.DoesNotExist:
                pass
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error updating {iso}: {str(e)}"))

        self.stdout.write(self.style.SUCCESS("Localization Seeding Complete"))
