"""
Public-schema URL configuration.

Only exposes authentication, onboarding, and admin pages.
Tenant data endpoints (patients, billing, etc.) are NOT available
on the public schema — they require subdomain-based tenant access.
"""

from django.contrib import admin
from django.urls import path
from django.contrib.auth import views as auth_views

from apps.accounts.public_views import LandingPageView
from apps.accounts.auth_views import (
    RegisterView, OTPVerifyView, ResendOTPView,
    LoginView, LogoutView,
)
from apps.accounts.jwt_views import (
    JWTTokenObtainView, JWTTokenRefreshView, JWTTokenVerifyView,
)
from apps.accounts.onboarding_views import (
    OnboardingStep1View, OnboardingStep2View, OnboardingStep3View,
)
from apps.tenants.views import AdminDashboardView
from apps.tenants.template_views import (
    CategoryIndexView, CategoryListView,
    TenantCreatePageView,
)
from apps.tenants.admin_views import (
    AdminTenantListView, AdminSubscriptionListView,
    AdminPlanListView, AdminFeatureListView, AdminSettingsView,
    AdminAnalyticsView, AdminRevenueView,
)
from apps.notifications.template_views import NotificationCenterView

urlpatterns = [
    path("admin/", admin.site.urls),

    # ── Public / Auth ──
    path("", LandingPageView.as_view(), name="landing"),
    path("login/", LoginView.as_view(), name="login"),
    path("register/", RegisterView.as_view(), name="register"),
    path("verify-otp/", OTPVerifyView.as_view(), name="verify-otp"),
    path("resend-otp/", ResendOTPView.as_view(), name="resend-otp"),
    path("logout/", LogoutView.as_view(), name="logout"),

    # ── Password Reset ──
    path("password-reset/", auth_views.PasswordResetView.as_view(
        template_name="accounts/password_reset.html",
        email_template_name="accounts/password_reset_email.html",
        subject_template_name="accounts/password_reset_subject.txt",
        success_url="/password-reset/done/",
    ), name="password_reset"),
    path("password-reset/done/", auth_views.PasswordResetDoneView.as_view(
        template_name="accounts/password_reset_done.html",
    ), name="password_reset_done"),
    path("password-reset/<uidb64>/<token>/", auth_views.PasswordResetConfirmView.as_view(
        template_name="accounts/password_reset_confirm.html",
        success_url="/password-reset/complete/",
    ), name="password_reset_confirm"),
    path("password-reset/complete/", auth_views.PasswordResetCompleteView.as_view(
        template_name="accounts/password_reset_complete.html",
    ), name="password_reset_complete"),

    # ── Onboarding Wizard ──
    path("onboarding/", OnboardingStep1View.as_view(), name="onboarding-step1"),
    path("onboarding/plan/", OnboardingStep2View.as_view(), name="onboarding-step2"),
    path("onboarding/confirm/", OnboardingStep3View.as_view(), name="onboarding-step3"),

    # ── Admin Dashboard (Platform Owner / SuperAdmin) ──
    path("admin-dashboard/", AdminDashboardView.as_view(), name="admin-dashboard"),
    path("admin-tenants/", AdminTenantListView.as_view(), name="admin-tenants"),
    path("admin-subscriptions/", AdminSubscriptionListView.as_view(), name="admin-subscriptions"),
    path("admin-plans/", AdminPlanListView.as_view(), name="admin-plans"),
    path("admin-features/", AdminFeatureListView.as_view(), name="admin-features"),
    path("admin-settings/", AdminSettingsView.as_view(), name="admin-settings"),
    path("admin-analytics/", AdminAnalyticsView.as_view(), name="admin-analytics"),
    path("admin-revenue/", AdminRevenueView.as_view(), name="admin-revenue"),

    # ── SuperAdmin: Categories & Tenants ──
    path("categories/", CategoryIndexView.as_view(), name="category-index"),
    path("categories/list/<slug:category_slug>/", CategoryListView.as_view(), name="category-list"),
    path("tenants/create/", TenantCreatePageView.as_view(), name="tenant-create-page"),

    # ── Notifications ──
    path("notifications/", NotificationCenterView.as_view(), name="notification-center"),

    # ── JWT Auth Endpoints ──
    path("api/auth/token/", JWTTokenObtainView.as_view(), name="token-obtain"),
    path("api/auth/token/refresh/", JWTTokenRefreshView.as_view(), name="token-refresh"),
    path("api/auth/token/verify/", JWTTokenVerifyView.as_view(), name="token-verify"),
]
