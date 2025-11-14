from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from apps.documents.models import Document
from .serializers import ReviewRunSerializer
from .services import run_full_analysis_for_document


class ReviewRunView(APIView):
    def post(self, request, *args, **kwargs):
        serializer = ReviewRunSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        document_id = serializer.validated_data["document_id"]

        try:
            payload = run_full_analysis_for_document(document_id)
        except Document.DoesNotExist:
            return Response(
                {"detail": "Document not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(payload, status=status.HTTP_200_OK)
