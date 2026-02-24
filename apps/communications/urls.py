from django.urls import path
from .views import (
    MessageTemplateListCreateAPIView, MessageTemplateDetailAPIView,
    MessageListCreateAPIView, MessageDetailAPIView,
    CampaignListCreateAPIView, CampaignDetailAPIView,
    FeedbackListCreateAPIView, FeedbackDetailAPIView,
)

urlpatterns = [
    # Message Templates
    path("templates/", MessageTemplateListCreateAPIView.as_view(), name="template-list-create"),
    path("templates/<uuid:pk>/", MessageTemplateDetailAPIView.as_view(), name="template-detail"),

    # Messages
    path("messages/", MessageListCreateAPIView.as_view(), name="message-list-create"),
    path("messages/<uuid:pk>/", MessageDetailAPIView.as_view(), name="message-detail"),

    # Campaigns
    path("campaigns/", CampaignListCreateAPIView.as_view(), name="campaign-list-create"),
    path("campaigns/<uuid:pk>/", CampaignDetailAPIView.as_view(), name="campaign-detail"),

    # Feedback
    path("feedback/", FeedbackListCreateAPIView.as_view(), name="feedback-list-create"),
    path("feedback/<uuid:pk>/", FeedbackDetailAPIView.as_view(), name="feedback-detail"),
]
