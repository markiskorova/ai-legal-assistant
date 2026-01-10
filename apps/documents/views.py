from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .ingestion.pdf_reader import extract_pdf_text
from .models import Document
from .serializers import DocumentSerializer, DocumentUploadSerializer

from apps.review.models import Finding, ReviewRun
from apps.review.serializers import FindingSerializer, ReviewRunSerializer


class DocumentUploadView(APIView):
    def post(self, request):
        serializer = DocumentUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        file = serializer.validated_data["file"]
        title = serializer.validated_data["title"]

        # Extract text depending on file type
        if file.name.lower().endswith(".pdf"):
            text = extract_pdf_text(file)
        else:
            text = file.read().decode("utf-8", errors="ignore")

        doc = Document.objects.create(title=title, text=text)

        return Response(DocumentSerializer(doc).data, status=status.HTTP_201_CREATED)


class DocumentFindingsView(APIView):
    """Retrieve persisted findings for a document.

    GET /v1/documents/{id}/findings

    By default, returns findings for the most recent ReviewRun. You can request
    a specific run via ?run_id=<uuid>.
    """

    def get(self, request, document_id):
        doc = get_object_or_404(Document, id=document_id)

        run_id = request.query_params.get("run_id")
        if run_id:
            run = get_object_or_404(ReviewRun, id=run_id, document=doc)
        else:
            run = ReviewRun.objects.filter(document=doc).order_by("-created_at").first()

        if not run:
            return Response(
                {
                    "document": {"id": str(doc.id), "title": doc.title},
                    "run": None,
                    "findings": [],
                },
                status=status.HTTP_200_OK,
            )

        qs = Finding.objects.filter(document=doc, run=run).order_by("created_at")

        return Response(
            {
                "document": {"id": str(doc.id), "title": doc.title},
                "run": ReviewRunSerializer(run).data,
                "findings": FindingSerializer(qs, many=True).data,
            },
            status=status.HTTP_200_OK,
        )
