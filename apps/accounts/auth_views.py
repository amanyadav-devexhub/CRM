"""
Authentication views: Register, OTP Verification, Login, Logout.
"""
import random
import logging
from django.shortcuts import render, redirect
from django.views import View
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings

logger = logging.getLogger(__name__)
User = get_user_model()


class RegisterView(View):
    """
    GET  → render registration form
    POST → validate, create inactive user, generate OTP, redirect to verify
    """
    template_name = "accounts/register.html"

    def get(self, request):
        if request.user.is_authenticated:
            return redirect("/dashboard/")
        return render(request, self.template_name)

    def post(self, request):
        username = request.POST.get("username", "").strip()
        email = request.POST.get("email", "").strip()
        phone = request.POST.get("phone", "").strip()
        password = request.POST.get("password", "")
        confirm_password = request.POST.get("confirm_password", "")

        errors = []

        if not username:
            errors.append("Username is required.")
        if not email:
            errors.append("Email is required.")
        if not password or len(password) < 8:
            errors.append("Password must be at least 8 characters.")
        if password != confirm_password:
            errors.append("Passwords do not match.")
        if User.objects.filter(username=username).exists():
            errors.append("Username already taken.")
        if User.objects.filter(email=email).exists():
            errors.append("Email already registered.")

        if errors:
            return render(request, self.template_name, {
                "errors": errors,
                "username": username,
                "email": email,
                "phone": phone,
            })

        # Create inactive user
        user = User.objects.create_user(
            username=username, email=email, password=password,
            is_active=False,
        )

        # Generate OTP
        otp = f"{random.randint(100000, 999999)}"
        request.session["otp_code"] = otp
        request.session["otp_user_id"] = str(user.pk)
        request.session["otp_created"] = timezone.now().isoformat()
        request.session["otp_email"] = email

        # Send OTP email (console backend in dev)
        try:
            send_mail(
                subject="Your HealthCRM Verification Code",
                message=f"Your verification code is: {otp}\n\nThis code expires in 5 minutes.",
                from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@healthcrm.com"),
                recipient_list=[email],
                fail_silently=False,
            )
        except Exception as e:
            logger.error(f"Failed to send OTP email: {e}")

        return redirect("/verify-otp/")


class OTPVerifyView(View):
    """
    GET  → render OTP input form
    POST → verify OTP, activate user, redirect to onboarding
    """
    template_name = "accounts/verify_otp.html"

    def get(self, request):
        email = request.session.get("otp_email", "")
        if not email:
            return redirect("/register/")
        return render(request, self.template_name, {"email": email})

    def post(self, request):
        entered = request.POST.get("otp", "").strip()
        stored = request.session.get("otp_code")
        user_id = request.session.get("otp_user_id")
        email = request.session.get("otp_email", "")
        created = request.session.get("otp_created")

        errors = []

        if not stored or not user_id:
            return redirect("/register/")

        # Check expiry (5 min)
        if created:
            from datetime import datetime, timedelta
            created_dt = datetime.fromisoformat(created)
            if timezone.now().replace(tzinfo=None) - created_dt.replace(tzinfo=None) > timedelta(minutes=5):
                errors.append("OTP has expired. Please request a new one.")
                return render(request, self.template_name, {"errors": errors, "email": email, "expired": True})

        if entered != stored:
            errors.append("Invalid verification code. Please try again.")
            return render(request, self.template_name, {"errors": errors, "email": email})

        # Activate user and log them in
        try:
            user = User.objects.get(pk=user_id)
            user.is_active = True
            user.save(update_fields=["is_active"])

            login(request, user)

            # Clean up session OTP keys
            for key in ["otp_code", "otp_user_id", "otp_created", "otp_email"]:
                request.session.pop(key, None)

            return redirect("/onboarding/")

        except User.DoesNotExist:
            errors.append("User not found. Please register again.")
            return render(request, self.template_name, {"errors": errors, "email": email})


class ResendOTPView(View):
    """Resend OTP to the user's email."""

    def post(self, request):
        email = request.session.get("otp_email")
        user_id = request.session.get("otp_user_id")

        if not email or not user_id:
            return redirect("/register/")

        otp = f"{random.randint(100000, 999999)}"
        request.session["otp_code"] = otp
        request.session["otp_created"] = timezone.now().isoformat()

        try:
            send_mail(
                subject="Your HealthCRM Verification Code",
                message=f"Your new verification code is: {otp}\n\nThis code expires in 5 minutes.",
                from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@healthcrm.com"),
                recipient_list=[email],
                fail_silently=False,
            )
        except Exception as e:
            logger.error(f"Failed to resend OTP: {e}")

        return redirect("/verify-otp/")


class LoginView(View):
    """
    GET  → render login form
    POST → authenticate, redirect based on role
    """
    template_name = "accounts/login.html"

    def get(self, request):
        if request.user.is_authenticated:
            return self._redirect_by_role(request.user)
        return render(request, self.template_name)

    def post(self, request):
        username_or_email = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")

        # If user entered an email, look up the username
        username = username_or_email
        if "@" in username_or_email:
            try:
                user_obj = User.objects.get(email=username_or_email)
                username = user_obj.username
            except User.DoesNotExist:
                pass

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return self._redirect_by_role(user)
        else:
            return render(request, self.template_name, {
                "errors": ["Invalid username or password."],
                "username": username_or_email,
            })

    def _redirect_by_role(self, user):
        """Redirect to correct panel based on user role."""
        if user.is_superuser and user.tenant is None:
            return redirect("/admin-dashboard/")
        elif user.tenant:
            return redirect("/dashboard/")
        else:
            return redirect("/dashboard/")


class LogoutView(View):
    """Log the user out and redirect to login."""

    def get(self, request):
        logout(request)
        return redirect("/login/")

    def post(self, request):
        logout(request)
        return redirect("/login/")
