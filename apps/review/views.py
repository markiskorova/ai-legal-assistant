from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from apps.documents.models import Document
from .serializers import ReviewRunRequestSerializer, ReviewRunSerializer
from .services import run_full_analysis_for_document, persist_review_run


class ReviewRunView(APIView):
    def post(self, request, *args, **kwargs):
        serializer = ReviewRunRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        document_id = serializer.validated_data["document_id"]

        try:
            payload = run_full_analysis_for_document(document_id)
            doc = Document.objects.get(id=document_id)
        except Document.DoesNotExist:
            return Response(
                {"detail": "Document not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # MVP Step 7: persist the run + findings so they can be retrieved later.
        run = persist_review_run(doc, payload.get("clauses", []), payload.get("findings", []))

        # Include run metadata in the response (useful for follow-up retrieval calls).
        payload["run"] = ReviewRunSerializer(run).data

        return Response(payload, status=status.HTTP_200_OK)
