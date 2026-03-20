"""
Admin views for notification management
"""
from django.shortcuts import render, redirect
from django.views import View
from django.contrib import messages
from apps.notifications.models import Notification, NotificationPreference
from apps.accounts.models import User, Role
from apps.tenants.models import Tenant


class AdminNotificationSettingsView(View):
    """Manage global notification settings"""
    template_name = "dashboard/admin_notifications.html"
    
    def get(self, request):
        # Get notification stats
        total_notifications = Notification.objects.count()
        unread_notifications = Notification.objects.filter(is_read=False).count()
        
        # Get notification preferences by role
        roles = Role.objects.filter(tenant__isnull=True).distinct()  # Global roles
        
        # Recent notifications
        recent_notifications = Notification.objects.select_related(
            'user', 'tenant'
        ).order_by('-created_at')[:50]
        
        context = {
            'total_notifications': total_notifications,
            'unread_notifications': unread_notifications,
            'recent_notifications': recent_notifications,
            'roles': roles,
        }
        
        return render(request, self.template_name, context)
    
    def post(self, request):
        action = request.POST.get('action')
        
        if action == 'clear_old':
            # Delete notifications older than 30 days
            from datetime import timedelta
            from django.utils import timezone
            
            cutoff = timezone.now() - timedelta(days=30)
            deleted_count = Notification.objects.filter(
                created_at__lt=cutoff,
                is_read=True
            ).delete()[0]
            
            messages.success(request, f'Deleted {deleted_count} old notifications')
        
        elif action == 'test_notification':
            # Send test notification to all admins
            admin_users = User.objects.filter(role__name='Admin')
            
            for admin in admin_users:
                Notification.objects.create(
                    user=admin,
                    tenant=admin.tenant,
                    type='system',
                    title='🧪 Test Notification',
                    body='This is a test notification from the admin panel',
                    priority='low',
                )
            
            messages.success(request, f'Sent test notification to {admin_users.count()} admins')
        
        return redirect('/admin-notifications/')


class AdminNotificationBulkView(View):
    """Send bulk notifications"""
    template_name = "dashboard/admin_notifications_bulk.html"
    
    def get(self, request):
        tenants = Tenant.objects.filter(is_active=True)
        roles = Role.objects.values('name').distinct()
        
        return render(request, self.template_name, {
            'tenants': tenants,
            'roles': roles,
        })
    
    def post(self, request):
        title = request.POST.get('title')
        body = request.POST.get('body')
        priority = request.POST.get('priority', 'medium')
        target_type = request.POST.get('target_type')  # 'all', 'tenant', 'role'
        
        target_tenants = request.POST.getlist('target_tenants')
        target_roles = request.POST.getlist('target_roles')
        
        if not title or not body:
            messages.error(request, 'Title and body are required')
            return redirect('/admin-notifications/bulk/')
        
        # Build user queryset based on target
        if target_type == 'all':
            users = User.objects.filter(is_active=True)
        elif target_type == 'tenant':
            users = User.objects.filter(tenant__id__in=target_tenants, is_active=True)
        elif target_type == 'role':
            users = User.objects.filter(role__name__in=target_roles, is_active=True)
        else:
            users = User.objects.none()
        
        # Create notifications
        count = 0
        for user in users:
            Notification.objects.create(
                user=user,
                tenant=user.tenant,
                type='system',
                title=title,
                body=body,
                priority=priority,
            )
            count += 1
        
        messages.success(request, f'Sent notification to {count} users')
        return redirect('/admin-notifications/bulk/')