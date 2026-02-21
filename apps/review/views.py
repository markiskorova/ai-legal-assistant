from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from apps.documents.models import Document
from apps.review.llm.schema import LLMValidationError
from .serializers import ReviewRunRequestSerializer, ReviewRunSerializer
from .services import persist_review_run, run_full_analysis_for_instance


class ReviewRunView(APIView):
    def post(self, request, *args, **kwargs):
        serializer = ReviewRunRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        document_id = serializer.validated_data["document_id"]
        doc = get_object_or_404(Document, id=document_id)

        try:
            payload = run_full_analysis_for_instance(doc)
        except LLMValidationError as exc:
            return Response(
                {"detail": f"LLM response validation failed: {str(exc)}"},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        # MVP Step 7: persist the run + findings so they can be retrieved later.
        run = persist_review_run(doc, payload.get("clauses", []), payload.get("findings", []))

        # Include run metadata in the response (useful for follow-up retrieval calls).
        payload["run"] = ReviewRunSerializer(run).data

        return Response(payload, status=status.HTTP_200_OK)
