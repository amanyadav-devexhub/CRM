"""
JWTCookieMiddleware — Reads JWT from HTTP-only cookies and authenticates
the request. If the access token is expired but a valid refresh token
exists, the access token is silently refreshed.

Place AFTER AuthenticationMiddleware in settings.MIDDLEWARE so
Django admin can still use session auth.
"""
import logging
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken

logger = logging.getLogger(__name__)
User = get_user_model()

COOKIE_ACCESS = getattr(settings, "JWT_AUTH_COOKIE", "access_token")
COOKIE_REFRESH = getattr(settings, "JWT_AUTH_REFRESH_COOKIE", "refresh_token")


class JWTCookieMiddleware:
    """
    Middleware that:
    1. Reads access_token cookie → sets request.user if valid
    2. On expired access, uses refresh_token to issue a new access cookie
    3. Falls through to session auth for Django admin
    """

    # Skip JWT auth: admin uses sessions, auth pages shouldn't re-auth from stale JWTs
    SKIP_PREFIXES = (
        "/admin/", "/static/", "/__debug__/",
        "/login/", "/register/", "/logout/",
        "/verify-otp/", "/resend-otp/",
        "/auth-bridge/", "/password-reset/",
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path

        # Don't override admin's session auth
        if any(path.startswith(p) for p in self.SKIP_PREFIXES):
            return self.get_response(request)

        access_raw = request.COOKIES.get(COOKIE_ACCESS)
        refresh_raw = request.COOKIES.get(COOKIE_REFRESH)

        # Track if we need to set a new access cookie on the response
        new_access_token = None

        if access_raw:
            try:
                token = AccessToken(access_raw)
                user = User.objects.get(id=token["user_id"])
                request.user = user
                request._jwt_user = user
            except (TokenError, InvalidToken, User.DoesNotExist):
                # Access token invalid/expired — try refresh
                if refresh_raw:
                    new_access_token = self._try_refresh(request, refresh_raw)
        elif refresh_raw:
            # No access token but refresh exists — auto-issue access
            new_access_token = self._try_refresh(request, refresh_raw)

        response = self.get_response(request)

        # Set the new access cookie if we refreshed it
        if new_access_token:
            response.set_cookie(
                COOKIE_ACCESS,
                new_access_token,
                max_age=int(settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"].total_seconds()),
                httponly=getattr(settings, "JWT_AUTH_HTTPONLY", True),
                secure=getattr(settings, "JWT_AUTH_SECURE", False),
                samesite=getattr(settings, "JWT_AUTH_SAMESITE", "Lax"),
                path="/",
            )

        return response

    def _try_refresh(self, request, refresh_raw):
        """
        Attempt to refresh the access token using the refresh token.
        Returns the new access token string if successful, None otherwise.
        """
        try:
            refresh = RefreshToken(refresh_raw)
            user = User.objects.get(id=refresh["user_id"])

            # Issue new access token
            new_access = str(refresh.access_token)

            # Set user on request
            request.user = user
            request._jwt_user = user
            return new_access

        except (TokenError, InvalidToken, User.DoesNotExist) as e:
            logger.debug(f"JWT refresh failed: {e}")
            return None
