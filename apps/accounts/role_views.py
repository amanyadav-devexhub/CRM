from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.db import transaction
from apps.accounts.models import Role, Permission

class RoleListView(View):
    """List all custom roles for the current tenant."""

    def get(self, request):
        tenant = getattr(request.user, "tenant", None)
        if not tenant:
            return redirect("/dashboard/")

        roles = Role.objects.filter(tenant=tenant)
        return render(request, "dashboard/settings/roles/list.html", {"roles": roles})


class RoleCreateView(View):
    """Create a new custom role and assign permissions."""

    def get(self, request):
        tenant = getattr(request.user, "tenant", None)
        if not tenant:
            return redirect("/dashboard/")

        # Group permissions logically for the UI
        permissions = Permission.objects.all().order_by("code")
        
        # Simple grouping by prefix (e.g., patient, dashboard, appointment)
        grouped_perms = {}
        for p in permissions:
            prefix = p.code.split(".")[0]
            if prefix not in grouped_perms:
                grouped_perms[prefix] = []
            grouped_perms[prefix].append(p)

        return render(request, "dashboard/settings/roles/form.html", {
            "grouped_perms": grouped_perms,
            "form_data": {"name": "", "description": ""}
        })

    def post(self, request):
        tenant = getattr(request.user, "tenant", None)
        if not tenant:
            return redirect("/dashboard/")

        name = request.POST.get("name", "").strip()
        selected_perms = request.POST.getlist("permissions")

        if not name:
            permissions = Permission.objects.all().order_by("code")
            grouped_perms = {}
            for p in permissions:
                prefix = p.code.split(".")[0]
                if prefix not in grouped_perms:
                    grouped_perms[prefix] = []
                grouped_perms[prefix].append(p)
                
            return render(request, "dashboard/settings/roles/form.html", {
                "errors": ["Role Name is required."],
                "grouped_perms": grouped_perms,
                "form_data": request.POST
            })

        with transaction.atomic():
            role = Role.objects.create(
                tenant=tenant,
                name=name,
                is_system_role=False
            )
            
            if selected_perms:
                role.permissions.set(selected_perms)

        return redirect("/dashboard/settings/roles/")


class RoleEditView(View):
    """Edit an existing custom role."""

    def get(self, request, pk):
        tenant = getattr(request.user, "tenant", None)
        if not tenant:
            return redirect("/dashboard/")

        role = get_object_or_404(Role, pk=pk, tenant=tenant)
        
        if role.is_system_role:
            # Prevent editing system default roles if desired, or just show them
            pass

        permissions = Permission.objects.all().order_by("code")
        grouped_perms = {}
        for p in permissions:
            prefix = p.code.split(".")[0]
            if prefix not in grouped_perms:
                grouped_perms[prefix] = []
            grouped_perms[prefix].append(p)

        role_perm_ids = role.permissions.values_list("id", flat=True)

        return render(request, "dashboard/settings/roles/form.html", {
            "role": role,
            "editing": True,
            "grouped_perms": grouped_perms,
            "role_perm_ids": list(role_perm_ids),
            "form_data": {
                "name": "",
            }
        })

    def post(self, request, pk):
        tenant = getattr(request.user, "tenant", None)
        if not tenant:
            return redirect("/dashboard/")

        role = get_object_or_404(Role, pk=pk, tenant=tenant)

        # Allow name edits if not system default
        if not role.is_system_role:
            role.name = request.POST.get("name", role.name).strip()
            role.save()

        # Update permissions
        selected_perms = request.POST.getlist("permissions")
        role.permissions.set(selected_perms)

        # Mark as customized so superadmin template updates won't overwrite
        if role.source_template and not role.is_customized:
            role.is_customized = True
            role.save(update_fields=["is_customized"])

        return redirect("/dashboard/settings/roles/")


class RoleDeleteView(View):
    """Delete a custom role (prevent deletion of system roles or roles in use)."""

    def post(self, request, pk):
        tenant = getattr(request.user, "tenant", None)
        if not tenant:
            return redirect("/dashboard/")

        role = get_object_or_404(Role, pk=pk, tenant=tenant)
        
        if role.is_system_role:
            return redirect("/dashboard/settings/roles/")
            
        if role.users.exists():
            # In a real app, flash a message "Cannot delete role in use"
            return redirect("/dashboard/settings/roles/")

        role.delete()
        return redirect("/dashboard/settings/roles/")
