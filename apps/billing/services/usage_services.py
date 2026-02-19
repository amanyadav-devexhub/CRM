from datetime import date
from apps.billing.models import UsageMetric


class UsageService:

    @staticmethod
    def current_month():
        today = date.today()
        return date(today.year, today.month, 1)

    @staticmethod
    def increment(tenant, metric_type, amount=1):
        month = UsageService.current_month()

        metric, _ = UsageMetric.objects.get_or_create(
            tenant=tenant,
            metric_type=metric_type,
            month=month
        )

        metric.quantity += amount
        metric.save()
