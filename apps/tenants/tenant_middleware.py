from apps.tenants.services.subscription_service import SubscriptionService

class TenantMiddleware:

    def __call__(self, request):

        tenant = request.tenant  # already loaded

        if not SubscriptionService.is_subscription_valid(tenant):
            return HttpResponse("Subscription expired", status=403)

        return self.get_response(request)
