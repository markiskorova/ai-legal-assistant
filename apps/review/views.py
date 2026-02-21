from django.conf import settings
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.documents.models import Document
from apps.review.models import ReviewRunStatus
from .serializers import ReviewRunRequestSerializer, ReviewRunSerializer
from .services import get_or_create_idempotent_run
from .tasks import process_review_run_task


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

        run, reused, expired_key = get_or_create_idempotent_run(doc, idempotency_key)
        if expired_key:
            return Response(
                {
                    "detail": "Idempotency key has expired (older than 24 hours). Use a new Idempotency-Key.",
                    "run_id": str(run.id),
                },
                status=status.HTTP_409_CONFLICT,
            )

        if not reused:
            try:
                process_review_run_task.delay(str(run.id))
            except Exception as exc:
                run.status = ReviewRunStatus.FAILED
                run.error = f"Failed to enqueue review run: {exc}"
                run.save(update_fields=["status", "error"])
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
