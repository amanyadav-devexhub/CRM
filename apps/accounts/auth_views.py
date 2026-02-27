"""
Authentication views: Register, OTP Verification, Login, Logout, AuthBridge.

Uses JWT tokens stored in HTTP-only cookies for authentication.
Django's authenticate() validates credentials, then JWT tokens are issued
as cookies — no Django sessions needed for auth.

AuthBridgeView handles cross-subdomain login by accepting a signed token
in the URL and setting local cookies on the tenant subdomain.
"""
import random
import logging
from django.shortcuts import render, redirect
from django.views import View
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.core import signing
from rest_framework_simplejwt.tokens import RefreshToken

logger = logging.getLogger(__name__)
User = get_user_model()

# Cookie config from settings
COOKIE_ACCESS = getattr(settings, "JWT_AUTH_COOKIE", "access_token")
COOKIE_REFRESH = getattr(settings, "JWT_AUTH_REFRESH_COOKIE", "refresh_token")


def _set_jwt_cookies(response, user):
    """Issue JWT access + refresh tokens as HTTP-only session cookies."""
    refresh = RefreshToken.for_user(user)
    access = str(refresh.access_token)

    # No max_age → session cookies → cleared when browser closes
    response.set_cookie(
        COOKIE_ACCESS,
        access,
        httponly=getattr(settings, "JWT_AUTH_HTTPONLY", True),
        secure=getattr(settings, "JWT_AUTH_SECURE", False),
        samesite=getattr(settings, "JWT_AUTH_SAMESITE", "Lax"),
        path="/",
    )
    response.set_cookie(
        COOKIE_REFRESH,
        str(refresh),
        httponly=getattr(settings, "JWT_AUTH_HTTPONLY", True),
        secure=getattr(settings, "JWT_AUTH_SECURE", False),
        samesite=getattr(settings, "JWT_AUTH_SAMESITE", "Lax"),
        path="/",
    )
    return response


def _clear_jwt_cookies(response):
    """Remove JWT cookies."""
    response.delete_cookie(COOKIE_ACCESS, path="/")
    response.delete_cookie(COOKIE_REFRESH, path="/")
    return response


class RegisterView(View):
    """
    GET  → render registration form
    POST → validate, create inactive user, generate OTP, redirect to verify
    """
    template_name = "accounts/register.html"

    def get(self, request):
        plan_id = request.GET.get("plan_id")
        if plan_id:
            request.session["preselected_plan_id"] = plan_id

        if request.user.is_authenticated:
            user = request.user
            if user.is_superuser and user.tenant is None:
                return redirect("/admin-dashboard/")
            elif user.tenant and user.tenant.subdomain:
                host = LoginView._get_tenant_host(user.tenant.subdomain, request)
                token = signing.dumps({"user_id": user.pk}, salt="auth-bridge")
                return redirect(f"{host}/auth-bridge/?token={token}")
            else:
                return redirect("/onboarding/")
        return render(request, self.template_name)

    def post(self, request):
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "")
        confirm_password = request.POST.get("confirm_password", "")

        errors = []

        if not email:
            errors.append("Email is required.")
        if not password or len(password) < 8:
            errors.append("Password must be at least 8 characters.")
        if password != confirm_password:
            errors.append("Passwords do not match.")
        if User.objects.filter(email=email).exists():
            errors.append("Email already registered.")

        if errors:
            return render(request, self.template_name, {
                "errors": errors,
                "email": email,
            })

        # Auto-generate username from email
        username = email.split("@")[0]
        # Ensure uniqueness
        base_username = username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1

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

        # Send OTP email
        html_message = f"""
        <div style="font-family: 'Segoe UI', Arial, sans-serif; max-width: 480px; margin: 0 auto;
                    background: #111827; border-radius: 16px; padding: 32px; color: #f1f5f9;">
            <div style="text-align: center; margin-bottom: 24px;">
                <div style="display: inline-block; background: linear-gradient(135deg, #3b82f6, #8b5cf6, #ec4899);
                            border-radius: 12px; width: 42px; height: 42px; line-height: 42px;
                            font-size: 18px; font-weight: 800; color: #fff;">H</div>
                <h2 style="margin: 8px 0 0; font-size: 20px;
                           background: linear-gradient(135deg, #3b82f6, #8b5cf6, #ec4899);
                           -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
                    HealthCRM</h2>
            </div>
            <h1 style="text-align: center; font-size: 22px; margin-bottom: 8px; color: #f1f5f9;">
                Email Verification</h1>
            <p style="text-align: center; color: rgba(241,245,249,0.6); font-size: 14px; margin-bottom: 24px;">
                Use the code below to verify your email address</p>
            <div style="background: rgba(59,130,246,0.1); border: 1px solid rgba(59,130,246,0.2);
                        border-radius: 12px; padding: 20px; text-align: center; margin-bottom: 24px;">
                <span style="font-size: 32px; font-weight: 800; letter-spacing: 8px; color: #3b82f6;">
                    {otp}</span>
            </div>
            <p style="text-align: center; color: rgba(241,245,249,0.5); font-size: 13px;">
                This code expires in <strong style="color: #10b981;">5 minutes</strong>.</p>
            <hr style="border: none; border-top: 1px solid rgba(255,255,255,0.06); margin: 24px 0;">
            <p style="text-align: center; color: rgba(241,245,249,0.35); font-size: 12px;">
                If you didn't request this, you can safely ignore this email.</p>
        </div>
        """
        try:
            send_mail(
                subject="Your HealthCRM Verification Code",
                message=f"Your HealthCRM verification code is: {otp}\n\nThis code expires in 5 minutes.\n\nIf you didn't request this, please ignore this email.",
                from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@healthcrm.com"),
                recipient_list=[email],
                html_message=html_message,
                fail_silently=False,
            )
            logger.info(f"OTP email sent successfully to {email}")
        except Exception as e:
            logger.error(f"Failed to send OTP email to {email}: {e}")
            request.session["otp_email_error"] = True

        return redirect("/verify-otp/")


class OTPVerifyView(View):
    """
    GET  → render OTP input form
    POST → verify OTP, activate user, issue JWT cookies, redirect to onboarding
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

        # Activate user and issue JWT tokens
        try:
            user = User.objects.get(pk=user_id)
            user.is_active = True
            user.save(update_fields=["is_active"])

            # Also do Django login for session auth (needed for onboarding)
            login(request, user)

            # Clean up session OTP keys
            for key in ["otp_code", "otp_user_id", "otp_created", "otp_email"]:
                request.session.pop(key, None)

            # Issue JWT cookies and redirect
            response = redirect("/onboarding/")
            _set_jwt_cookies(response, user)
            return response

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

        html_message = f"""
        <div style="font-family: 'Segoe UI', Arial, sans-serif; max-width: 480px; margin: 0 auto;
                    background: #111827; border-radius: 16px; padding: 32px; color: #f1f5f9;">
            <div style="text-align: center; margin-bottom: 24px;">
                <div style="display: inline-block; background: linear-gradient(135deg, #3b82f6, #8b5cf6, #ec4899);
                            border-radius: 12px; width: 42px; height: 42px; line-height: 42px;
                            font-size: 18px; font-weight: 800; color: #fff;">H</div>
                <h2 style="margin: 8px 0 0; font-size: 20px;
                           background: linear-gradient(135deg, #3b82f6, #8b5cf6, #ec4899);
                           -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
                    HealthCRM</h2>
            </div>
            <h1 style="text-align: center; font-size: 22px; margin-bottom: 8px; color: #f1f5f9;">
                Email Verification</h1>
            <p style="text-align: center; color: rgba(241,245,249,0.6); font-size: 14px; margin-bottom: 24px;">
                Here is your new verification code</p>
            <div style="background: rgba(59,130,246,0.1); border: 1px solid rgba(59,130,246,0.2);
                        border-radius: 12px; padding: 20px; text-align: center; margin-bottom: 24px;">
                <span style="font-size: 32px; font-weight: 800; letter-spacing: 8px; color: #3b82f6;">
                    {otp}</span>
            </div>
            <p style="text-align: center; color: rgba(241,245,249,0.5); font-size: 13px;">
                This code expires in <strong style="color: #10b981;">5 minutes</strong>.</p>
            <hr style="border: none; border-top: 1px solid rgba(255,255,255,0.06); margin: 24px 0;">
            <p style="text-align: center; color: rgba(241,245,249,0.35); font-size: 12px;">
                If you didn't request this, you can safely ignore this email.</p>
        </div>
        """
        try:
            send_mail(
                subject="Your HealthCRM Verification Code",
                message=f"Your new HealthCRM verification code is: {otp}\n\nThis code expires in 5 minutes.\n\nIf you didn't request this, please ignore this email.",
                from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@healthcrm.com"),
                recipient_list=[email],
                html_message=html_message,
                fail_silently=False,
            )
            logger.info(f"Resend OTP email sent to {email}")
        except Exception as e:
            logger.error(f"Failed to resend OTP to {email}: {e}")

        return redirect("/verify-otp/")


class LoginView(View):
    """
    GET  → render login form (redirect if already authenticated)
    POST → authenticate, issue JWT cookies, redirect based on role
    """
    template_name = "accounts/login.html"

    def get(self, request):
        if request.user.is_authenticated:
            return self._redirect_by_role(request.user, request)
        return render(request, self.template_name)

    def post(self, request):
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "")

        # Look up username from email for Django's authenticate()
        username = email
        try:
            user_obj = User.objects.get(email=email)
            username = user_obj.username
        except User.DoesNotExist:
            pass

        user = authenticate(request, username=username, password=password)

        if user is not None:
            # Also do Django session login (keeps admin panel working)
            login(request, user)

            # Issue JWT cookies
            response = self._redirect_by_role(user, request)
            _set_jwt_cookies(response, user)
            return response
        else:
            return render(request, self.template_name, {
                "errors": ["Invalid email or password."],
                "email": email,
            })

    def _redirect_by_role(self, user, request=None):
        """Redirect to correct panel based on user role."""
        if user.is_superuser and user.tenant is None:
            return redirect("/admin-dashboard/")
        elif user.tenant and user.tenant.subdomain:
            # Use auth bridge to transfer session to tenant subdomain
            token = signing.dumps({"user_id": user.pk}, salt="auth-bridge")
            host = self._get_tenant_host(user.tenant.subdomain, request)
            return redirect(f"{host}/auth-bridge/?token={token}")
        else:
            return redirect("/onboarding/")

    @staticmethod
    def _get_tenant_host(subdomain, request=None):
        """Build the tenant host URL dynamically from the request."""
        if request:
            request_host = request.get_host()
            base_host = request_host.split(":")[0]
            port_part = request_host.split(":")[1] if ":" in request_host else ""
            scheme = "https" if request.is_secure() else "http"
            # Can't have subdomains on IP addresses — use localhost instead
            if base_host in ("127.0.0.1", "0.0.0.0"):
                base_host = "localhost"
            port_suffix = f":{port_part}" if port_part else ""
            return f"{scheme}://{subdomain}.{base_host}{port_suffix}"
        # Fallback for when request is not available
        from django.conf import settings
        port = getattr(settings, "TENANT_PORT", "8000")
        scheme = "https" if getattr(settings, "TENANT_USE_HTTPS", False) else "http"
        return f"{scheme}://{subdomain}.localhost:{port}"


class LogoutView(View):
    """Log the user out — clear ALL auth cookies and session."""

    def _is_tenant_subdomain(self, request):
        host = request.get_host().split(":")[0]
        return host != "localhost" and host != "127.0.0.1" and (
            host.endswith(".localhost") or "." in host
        )

    def _public_url(self, path, request=None):
        if request:
            request_host = request.get_host()
            base_host = request_host.split(":")[0]
            port_part = request_host.split(":")[1] if ":" in request_host else ""
            scheme = "https" if request.is_secure() else "http"
            # Extract root domain from subdomain (e.g., test-free.localhost → localhost)
            parts = base_host.split(".")
            if len(parts) > 1:
                root_host = ".".join(parts[1:])  # drop first part (subdomain)
            else:
                root_host = base_host
            if root_host in ("127.0.0.1", "0.0.0.0"):
                root_host = "localhost"
            port_suffix = f":{port_part}" if port_part else ""
            return f"{scheme}://{root_host}{port_suffix}{path}"
        port = getattr(settings, "TENANT_PORT", "8000")
        scheme = "https" if getattr(settings, "TENANT_USE_HTTPS", False) else "http"
        return f"{scheme}://localhost:{port}{path}"

    def _full_clear(self, request, response):
        """Nuke every auth-related cookie."""
        # 1. Django session flush
        logout(request)
        request.session.flush()

        # 2. Delete JWT cookies
        _clear_jwt_cookies(response)

        # 3. Also explicitly delete session + CSRF cookies
        response.delete_cookie("sessionid", path="/")
        response.delete_cookie("csrftoken", path="/")

        return response

    def _do_logout(self, request):
        if self._is_tenant_subdomain(request):
            # Step 1: Clear everything on THIS subdomain,
            # then redirect to public /logout/ to clear that domain too.
            response = redirect(self._public_url("/logout/", request))
            self._full_clear(request, response)
        else:
            # Step 2 (or direct public logout): Clear and go to login
            response = redirect("/login/")
            self._full_clear(request, response)
        return response

    def get(self, request):
        return self._do_logout(request)

    def post(self, request):
        return self._do_logout(request)


class AuthBridgeView(View):
    """
    Cross-subdomain auth bridge.

    After login on localhost:8000, the user is redirected to:
        http://test-free.localhost:8000/auth-bridge/?token=<signed>

    This view validates the signed token, logs the user in on THIS
    subdomain (setting session + JWT cookies locally), then redirects
    to /dashboard/.

    The token expires after 60 seconds and can only be used once.
    """

    def get(self, request):
        token = request.GET.get("token", "")
        if not token:
            return redirect("/login/")

        try:
            data = signing.loads(token, salt="auth-bridge", max_age=60)
        except (signing.BadSignature, signing.SignatureExpired):
            return redirect("/login/")

        try:
            user = User.objects.get(pk=data["user_id"])
        except User.DoesNotExist:
            return redirect("/login/")

        # Create local session on this subdomain
        login(request, user)

        # Set JWT cookies for this subdomain
        response = redirect("/dashboard/")
        _set_jwt_cookies(response, user)
        return response

