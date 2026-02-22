from datetime import timedelta

from django.conf import settings
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.documents.models import Document
from apps.review.models import ReviewRun, ReviewRunStatus
from .serializers import ReviewRunRequestSerializer, ReviewRunSerializer
from .services import create_queued_review_run, find_idempotent_run
from .tasks import process_review_run_task


def _request_fingerprint(request) -> str:
    user = getattr(request, "user", None)
    if user is not None and getattr(user, "is_authenticated", False):
        return f"user:{user.pk}"
    xff = request.META.get("HTTP_X_FORWARDED_FOR", "")
    ip = xff.split(",")[0].strip() if xff else request.META.get("REMOTE_ADDR", "unknown")
    return f"ip:{ip or 'unknown'}"


class ReviewRunView(APIView):
    def post(self, request, *args, **kwargs):
        serializer = ReviewRunRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        document_id = serializer.validated_data["document_id"]
        doc = get_object_or_404(Document, id=document_id)

        idempotency_key = request.headers.get("Idempotency-Key") or serializer.validated_data.get(
            "idempotency_key"
        )
        if idempotency_key:
            idempotency_key = idempotency_key.strip()

        requester = _request_fingerprint(request)
        run, reused, expired_key = find_idempotent_run(doc, idempotency_key)
        if expired_key:
            return Response(
                {
                    "detail": "Idempotency key has expired (older than 24 hours). Use a new Idempotency-Key.",
                    "run_id": str(run.id),
                },
                status=status.HTTP_409_CONFLICT,
            )

        if not reused:
            concurrent_limit = max(1, int(settings.REVIEW_MAX_CONCURRENT_RUNS))
            active_count = ReviewRun.objects.filter(
                status__in=[ReviewRunStatus.QUEUED, ReviewRunStatus.RUNNING]
            ).count()
            if active_count >= concurrent_limit:
                return Response(
                    {
                        "detail": "Too many concurrent review runs. Try again shortly.",
                        "limit": concurrent_limit,
                    },
                    status=status.HTTP_429_TOO_MANY_REQUESTS,
                )

            rate_limit = max(1, int(settings.REVIEW_RATE_LIMIT_PER_MINUTE))
            window_start = timezone.now() - timedelta(minutes=1)
            recent_count = ReviewRun.objects.filter(
                request_fingerprint=requester,
                created_at__gte=window_start,
            ).count()
            if recent_count >= rate_limit:
                return Response(
                    {
                        "detail": "Rate limit exceeded for review run requests.",
                        "limit_per_minute": rate_limit,
                    },
                    status=status.HTTP_429_TOO_MANY_REQUESTS,
                )

            run = create_queued_review_run(
                doc,
                idempotency_key=idempotency_key,
                request_fingerprint=requester,
            )

        if not reused:
            try:
                process_review_run_task.delay(str(run.id))
            except Exception as exc:
                run.status = ReviewRunStatus.FAILED
                run.error = f"Failed to enqueue review run: {exc}"
                run.completed_at = timezone.now()
                run.save(update_fields=["status", "error", "completed_at"])
                return Response(
                    {
                        "detail": "Failed to enqueue review run.",
                        "run": ReviewRunSerializer(run).data,
                    },
                    status=status.HTTP_503_SERVICE_UNAVAILABLE,
                )
            if settings.CELERY_TASK_ALWAYS_EAGER:
                run.refresh_from_db()

        payload = {
            "document": {"id": str(doc.id), "title": doc.title},
            "clauses": [],
            "findings": [],
            "run": ReviewRunSerializer(run).data,
            "idempotency_reused": reused,
        }

        return Response(payload, status=status.HTTP_200_OK if reused else status.HTTP_202_ACCEPTED)


class ReviewRunStatusView(APIView):
    def get(self, request, run_id, *args, **kwargs):
        run = get_object_or_404(ReviewRun.objects.select_related("document"), id=run_id)
        return Response(
            {
                "run": ReviewRunSerializer(run).data,
                "document": {"id": str(run.document.id), "title": run.document.title},
            },
            status=status.HTTP_200_OK,
        )
