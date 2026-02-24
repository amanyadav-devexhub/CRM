"""
JWT API views — programmatic token endpoints for mobile apps / API clients.

Routes:
  POST /api/auth/token/         → obtain access + refresh pair
  POST /api/auth/token/refresh/ → refresh access token
  POST /api/auth/token/verify/  → verify token validity
"""
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)


class JWTTokenObtainView(TokenObtainPairView):
    """POST username + password → access + refresh tokens (JSON response)."""
    pass


class JWTTokenRefreshView(TokenRefreshView):
    """POST refresh token → new access token (JSON response)."""
    pass


class JWTTokenVerifyView(TokenVerifyView):
    """POST token → verify validity (JSON response)."""
    pass
