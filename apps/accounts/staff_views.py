"""
Staff / Employee CRUD views for the clinic dashboard.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib.auth import get_user_model
from apps.accounts.models import Employee, Role
from apps.clinical.models import Doctor, DoctorSlot

User = get_user_model()


class StaffListView(View):
    """List all employees for the current tenant."""

    def get(self, request):
        tenant = getattr(request.user, "tenant", None)
        if not tenant:
            return redirect("/dashboard/")

        employees = Employee.objects.filter(
            user__tenant=tenant
        ).select_related("user", "user__role")

        context = {
            "employees": employees,
            "employee_types": Employee.EMPLOYEE_TYPES,
            "total": employees.count(),
            "active": employees.filter(is_active=True).count(),
        }
        return render(request, "dashboard/staff/list.html", context)


class StaffCreateView(View):
    """Create a new employee + user account."""

    def get(self, request):
        tenant = getattr(request.user, "tenant", None)
        if not tenant:
            return redirect("/dashboard/")

        roles = Role.objects.filter(tenant=tenant)
        context = {
            "employee_types": Employee.EMPLOYEE_TYPES,
            "roles": roles,
            "form_data": {
                "first_name": "",
                "last_name": "",
                "email": "",
                "username": "",
                "employee_type": "",
                "department": "",
                "phone": "",
            },
        }
        return render(request, "dashboard/staff/form.html", context)

    def post(self, request):
        tenant = getattr(request.user, "tenant", None)
        if not tenant:
            return redirect("/dashboard/")

        errors = []

        # Read form data
        first_name = request.POST.get("first_name", "").strip()
        last_name = request.POST.get("last_name", "").strip()
        email = request.POST.get("email", "").strip()
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        employee_type = request.POST.get("employee_type", "")
        department = request.POST.get("department", "").strip()
        phone = request.POST.get("phone", "").strip()
        role_id = request.POST.get("role", "")

        # Validate
        if not first_name:
            errors.append("First name is required.")
        if not username:
            errors.append("Username is required.")
        if not password or len(password) < 6:
            errors.append("Password must be at least 6 characters.")
        if User.objects.filter(username=username).exists():
            errors.append("Username already taken.")
        if email and User.objects.filter(email=email).exists():
            errors.append("Email already registered.")

        if errors:
            roles = Role.objects.filter(tenant=tenant)
            return render(request, "dashboard/staff/form.html", {
                "errors": errors,
                "employee_types": Employee.EMPLOYEE_TYPES,
                "roles": roles,
                "form_data": request.POST,
            })

        # Create user
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            tenant=tenant,
        )

        # Assign role
        if role_id:
            try:
                role = Role.objects.get(pk=role_id, tenant=tenant)
                user.role = role
                user.save(update_fields=["role"])
            except Role.DoesNotExist:
                pass

        # Create employee profile
        Employee.objects.create(
            user=user,
            employee_type=employee_type,
            department=department,
            phone=phone,
        )

        # If doctor type, also create Doctor record
        if employee_type == "DOCTOR":
            specialization = request.POST.get("specialization", "General")
            consultation_fee = request.POST.get("consultation_fee", 0)
            Doctor.objects.create(
                user=user,
                name=f"{first_name} {last_name}",
                specialization=specialization,
                phone=phone,
                email=email,
                consultation_fee=consultation_fee or 0,
            )

        return redirect("/dashboard/staff/")


class StaffEditView(View):
    """Edit an existing employee."""

    def get(self, request, pk):
        tenant = getattr(request.user, "tenant", None)
        if not tenant:
            return redirect("/dashboard/")

        employee = get_object_or_404(Employee, pk=pk, user__tenant=tenant)
        roles = Role.objects.filter(tenant=tenant)
        context = {
            "employee": employee,
            "employee_types": Employee.EMPLOYEE_TYPES,
            "roles": roles,
            "editing": True,
        }
        return render(request, "dashboard/staff/form.html", context)

    def post(self, request, pk):
        tenant = getattr(request.user, "tenant", None)
        if not tenant:
            return redirect("/dashboard/")

        employee = get_object_or_404(Employee, pk=pk, user__tenant=tenant)
        user = employee.user

        # Update user fields
        user.first_name = request.POST.get("first_name", "").strip()
        user.last_name = request.POST.get("last_name", "").strip()
        user.email = request.POST.get("email", "").strip()

        role_id = request.POST.get("role", "")
        if role_id:
            try:
                user.role = Role.objects.get(pk=role_id, tenant=tenant)
            except Role.DoesNotExist:
                pass
        user.save()

        # Update employee fields
        employee.employee_type = request.POST.get("employee_type", employee.employee_type)
        employee.department = request.POST.get("department", "").strip()
        employee.phone = request.POST.get("phone", "").strip()
        employee.is_active = request.POST.get("is_active") == "on"
        employee.save()

        return redirect("/dashboard/staff/")


class StaffDeleteView(View):
    """Deactivate an employee (soft delete)."""

    def post(self, request, pk):
        tenant = getattr(request.user, "tenant", None)
        if not tenant:
            return redirect("/dashboard/")

        employee = get_object_or_404(Employee, pk=pk, user__tenant=tenant)
        employee.is_active = False
        employee.save(update_fields=["is_active"])

        # Also deactivate user account
        employee.user.is_active = False
        employee.user.save(update_fields=["is_active"])

        return redirect("/dashboard/staff/")


class DoctorListView(View):
    """List all doctors for the current tenant."""

    def get(self, request):
        tenant = getattr(request.user, "tenant", None)
        if not tenant:
            return redirect("/dashboard/")

        doctors = Doctor.objects.filter(
            user__tenant=tenant
        ).prefetch_related("slots") | Doctor.objects.filter(user__isnull=True)

        context = {
            "doctors": doctors,
            "total": doctors.count(),
            "active": doctors.filter(is_active=True).count(),
        }
        return render(request, "dashboard/doctors/list.html", context)
