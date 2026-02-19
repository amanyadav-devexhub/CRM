from apps.tenants.models import Tenant

class TenantMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        hostname = request.get_host().split(':')[0]
        subdomain = hostname.split('.')[0]

        try:
            tenant = Tenant.objects.get(subdomain=subdomain)
            request.tenant = tenant
        except Tenant.DoesNotExist:
            request.tenant = None

        response = self.get_response(request)
        return response
