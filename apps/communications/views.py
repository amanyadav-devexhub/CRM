from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.db.models import Q

from .models import MessageTemplate, Message, Campaign, Feedback
from .serializers import (
    MessageTemplateSerializer,
    MessageListSerializer, MessageDetailSerializer,
    CampaignListSerializer, CampaignDetailSerializer,
    FeedbackSerializer,
)


# ══════════════════════════════════════════════
# Message Templates
# ══════════════════════════════════════════════

class MessageTemplateListCreateAPIView(APIView):
    """
    GET  /api/communications/templates/     → list all templates
    POST /api/communications/templates/     → create a new template
    """

    def get(self, request):
        templates = MessageTemplate.objects.all()

        # Filter by channel
        channel = request.query_params.get("channel")
        if channel:
            templates = templates.filter(channel=channel)

        # Filter by active status
        active = request.query_params.get("active")
        if active is not None:
            templates = templates.filter(is_active=active.lower() == "true")

        # Search
        search = request.query_params.get("search", "").strip()
        if search:
            templates = templates.filter(
                Q(name__icontains=search) | Q(body__icontains=search)
            )

        serializer = MessageTemplateSerializer(templates, many=True)
        return Response({"count": len(serializer.data), "results": serializer.data})

    def post(self, request):
        serializer = MessageTemplateSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class MessageTemplateDetailAPIView(APIView):
    """
    GET    /api/communications/templates/{id}/
    PUT    /api/communications/templates/{id}/
    DELETE /api/communications/templates/{id}/
    """

    def _get_object(self, pk):
        return get_object_or_404(MessageTemplate, pk=pk)

    def get(self, request, pk):
        template = self._get_object(pk)
        return Response(MessageTemplateSerializer(template).data)

    def put(self, request, pk):
        template = self._get_object(pk)
        serializer = MessageTemplateSerializer(template, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        template = self._get_object(pk)
        template.delete()
        return Response(
            {"message": f"Template '{template.name}' deleted."},
            status=status.HTTP_200_OK,
        )


# ══════════════════════════════════════════════
# Messages
# ══════════════════════════════════════════════

class MessageListCreateAPIView(APIView):
    """
    GET  /api/communications/messages/     → paginated list
    POST /api/communications/messages/     → compose & queue a message
    """

    def get(self, request):
        messages = Message.objects.select_related("patient", "template").all()

        # Filters
        channel = request.query_params.get("channel")
        if channel:
            messages = messages.filter(channel=channel)

        msg_status = request.query_params.get("status")
        if msg_status:
            messages = messages.filter(status=msg_status)

        patient_id = request.query_params.get("patient")
        if patient_id:
            messages = messages.filter(patient_id=patient_id)

        # Pagination
        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("page_size", 20))
        start = (page - 1) * page_size
        end = start + page_size

        total = messages.count()
        messages = messages[start:end]

        serializer = MessageListSerializer(messages, many=True)
        return Response({
            "count": total,
            "page": page,
            "page_size": page_size,
            "results": serializer.data,
        })

    def post(self, request):
        serializer = MessageDetailSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(
                sent_by=request.user if request.user.is_authenticated else None
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class MessageDetailAPIView(APIView):
    """
    GET    /api/communications/messages/{id}/
    PUT    /api/communications/messages/{id}/
    DELETE /api/communications/messages/{id}/
    """

    def _get_object(self, pk):
        return get_object_or_404(Message, pk=pk)

    def get(self, request, pk):
        message = self._get_object(pk)
        return Response(MessageDetailSerializer(message).data)

    def put(self, request, pk):
        message = self._get_object(pk)
        serializer = MessageDetailSerializer(message, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        message = self._get_object(pk)
        message.delete()
        return Response(
            {"message": "Message deleted."},
            status=status.HTTP_200_OK,
        )


# ══════════════════════════════════════════════
# Campaigns
# ══════════════════════════════════════════════

class CampaignListCreateAPIView(APIView):
    """
    GET  /api/communications/campaigns/     → list campaigns
    POST /api/communications/campaigns/     → create a new campaign
    """

    def get(self, request):
        campaigns = Campaign.objects.select_related("template").all()

        campaign_status = request.query_params.get("status")
        if campaign_status:
            campaigns = campaigns.filter(status=campaign_status)

        search = request.query_params.get("search", "").strip()
        if search:
            campaigns = campaigns.filter(name__icontains=search)

        # Pagination
        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("page_size", 20))
        start = (page - 1) * page_size
        end = start + page_size

        total = campaigns.count()
        campaigns = campaigns[start:end]

        serializer = CampaignListSerializer(campaigns, many=True)
        return Response({
            "count": total,
            "page": page,
            "page_size": page_size,
            "results": serializer.data,
        })

    def post(self, request):
        serializer = CampaignDetailSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(
                created_by=request.user if request.user.is_authenticated else None
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CampaignDetailAPIView(APIView):
    """
    GET    /api/communications/campaigns/{id}/
    PUT    /api/communications/campaigns/{id}/
    DELETE /api/communications/campaigns/{id}/     → soft delete
    """

    def _get_object(self, pk):
        return get_object_or_404(Campaign, pk=pk)

    def get(self, request, pk):
        campaign = self._get_object(pk)
        return Response(CampaignDetailSerializer(campaign).data)

    def put(self, request, pk):
        campaign = self._get_object(pk)
        serializer = CampaignDetailSerializer(campaign, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        campaign = self._get_object(pk)
        campaign.delete()  # soft delete via SoftDeleteMixin
        return Response(
            {"message": f"Campaign '{campaign.name}' deleted."},
            status=status.HTTP_200_OK,
        )


# ══════════════════════════════════════════════
# Feedback
# ══════════════════════════════════════════════

class FeedbackListCreateAPIView(APIView):
    """
    GET  /api/communications/feedback/     → list all feedback
    POST /api/communications/feedback/     → submit new feedback
    """

    def get(self, request):
        feedbacks = Feedback.objects.select_related("patient", "appointment").all()

        # Filter by patient
        patient_id = request.query_params.get("patient")
        if patient_id:
            feedbacks = feedbacks.filter(patient_id=patient_id)

        # Filter by rating
        rating = request.query_params.get("rating")
        if rating:
            feedbacks = feedbacks.filter(rating=int(rating))

        # Pagination
        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("page_size", 20))
        start = (page - 1) * page_size
        end = start + page_size

        total = feedbacks.count()
        feedbacks = feedbacks[start:end]

        serializer = FeedbackSerializer(feedbacks, many=True)
        return Response({
            "count": total,
            "page": page,
            "page_size": page_size,
            "results": serializer.data,
        })

    def post(self, request):
        serializer = FeedbackSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class FeedbackDetailAPIView(APIView):
    """
    GET    /api/communications/feedback/{id}/
    PUT    /api/communications/feedback/{id}/
    DELETE /api/communications/feedback/{id}/
    """

    def _get_object(self, pk):
        return get_object_or_404(Feedback, pk=pk)

    def get(self, request, pk):
        feedback = self._get_object(pk)
        return Response(FeedbackSerializer(feedback).data)

    def put(self, request, pk):
        feedback = self._get_object(pk)
        serializer = FeedbackSerializer(feedback, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        feedback = self._get_object(pk)
        feedback.delete()
        return Response(
            {"message": "Feedback deleted."},
            status=status.HTTP_200_OK,
        )
