from django.views.generic import TemplateView
from django.db.models import Avg, Count, Q

from .models import MessageTemplate, Message, Campaign, Feedback


class CommunicationsIndexView(TemplateView):
    """Communications hub — overview of messages, campaigns, feedback."""
    template_name = "communications/index.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        # Message stats
        ctx["total_messages"] = Message.objects.count()
        ctx["queued_messages"] = Message.objects.filter(status="queued").count()
        ctx["sent_messages"] = Message.objects.filter(status="sent").count()
        ctx["failed_messages"] = Message.objects.filter(status="failed").count()

        # Campaign stats
        ctx["total_campaigns"] = Campaign.objects.count()
        ctx["active_campaigns"] = Campaign.objects.filter(
            status__in=["scheduled", "running"]
        ).count()

        # Feedback stats
        ctx["total_feedback"] = Feedback.objects.count()
        ctx["avg_rating"] = Feedback.objects.aggregate(
            avg=Avg("rating")
        )["avg"] or 0

        # Recent items
        ctx["recent_messages"] = Message.objects.select_related(
            "patient"
        ).order_by("-created_at")[:5]
        ctx["recent_campaigns"] = Campaign.objects.order_by("-created_at")[:5]
        ctx["recent_feedback"] = Feedback.objects.select_related(
            "patient"
        ).order_by("-submitted_at")[:5]

        # Templates count
        ctx["template_count"] = MessageTemplate.objects.filter(is_active=True).count()

        return ctx


class MessageListView(TemplateView):
    """Full messages list page."""
    template_name = "communications/messages.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        messages = Message.objects.select_related("patient", "template").all()

        # Filters from query params
        channel = self.request.GET.get("channel")
        if channel:
            messages = messages.filter(channel=channel)

        status_filter = self.request.GET.get("status")
        if status_filter:
            messages = messages.filter(status=status_filter)

        search = self.request.GET.get("search", "").strip()
        if search:
            messages = messages.filter(
                Q(patient__first_name__icontains=search)
                | Q(patient__last_name__icontains=search)
                | Q(subject__icontains=search)
            )

        ctx["messages"] = messages[:50]
        ctx["total_count"] = messages.count()
        ctx["channel_filter"] = channel or ""
        ctx["status_filter"] = status_filter or ""
        ctx["search_query"] = search
        ctx["channels"] = Message.Channel.choices
        ctx["statuses"] = Message.Status.choices
        return ctx


class CampaignListView(TemplateView):
    """Campaign management page."""
    template_name = "communications/campaigns.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        campaigns = Campaign.objects.select_related("template").all()

        status_filter = self.request.GET.get("status")
        if status_filter:
            campaigns = campaigns.filter(status=status_filter)

        ctx["campaigns"] = campaigns[:50]
        ctx["total_count"] = campaigns.count()
        ctx["status_filter"] = status_filter or ""
        ctx["statuses"] = Campaign.Status.choices
        return ctx


class FeedbackListView(TemplateView):
    """Patient feedback & ratings page."""
    template_name = "communications/feedback.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        feedbacks = Feedback.objects.select_related("patient", "appointment").all()

        rating_filter = self.request.GET.get("rating")
        if rating_filter:
            feedbacks = feedbacks.filter(rating=int(rating_filter))

        ctx["feedbacks"] = feedbacks[:50]
        ctx["total_count"] = feedbacks.count()
        ctx["avg_rating"] = Feedback.objects.aggregate(avg=Avg("rating"))["avg"] or 0
        ctx["rating_filter"] = rating_filter or ""

        # Rating distribution
        ctx["rating_distribution"] = {
            i: Feedback.objects.filter(rating=i).count() for i in range(1, 6)
        }
        return ctx
