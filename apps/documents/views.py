import math

from django.conf import settings
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .ingestion.pdf_reader import extract_pdf_text
from .ingestion.spreadsheet_reader import parse_csv_bytes, parse_xlsx_bytes
from .models import Document, DocumentSourceType
from .serializers import DocumentSerializer, DocumentUploadSerializer

from apps.review.models import Finding, ReviewRun
from apps.review.serializers import FindingSerializer, ReviewRunSerializer


class DocumentUploadView(APIView):
    def post(self, request):
        serializer = DocumentUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        file = serializer.validated_data["file"]
        title = serializer.validated_data["title"]
        filename = file.name.lower()
        metadata = {}

        # Extract text depending on file type
        if filename.endswith(".pdf"):
            text = extract_pdf_text(file)
            source_type = DocumentSourceType.PDF
        elif filename.endswith(".csv"):
            text, metadata = parse_csv_bytes(file.read())
            source_type = DocumentSourceType.SPREADSHEET
        elif filename.endswith(".xlsx"):
            text, metadata = parse_xlsx_bytes(file.read())
            source_type = DocumentSourceType.SPREADSHEET
        else:
            text = file.read().decode("utf-8", errors="ignore")
            source_type = DocumentSourceType.TEXT

        doc = Document.objects.create(
            title=title,
            text=text,
            source_type=source_type,
            ingestion_metadata=metadata,
        )

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
                    "pagination": _pagination_payload(page=1, page_size=_default_page_size(), total=0),
                },
                status=status.HTTP_200_OK,
            )

        page = _parse_positive_int(request.query_params.get("page"), default=1)
        page_size = _parse_positive_int(
            request.query_params.get("page_size"),
            default=_default_page_size(),
        )
        page_size = min(page_size, _max_page_size())
        ordering = _safe_ordering(request.query_params.get("ordering"))

        qs = Finding.objects.filter(document=doc, run=run).order_by(ordering, "id")
        total = qs.count()
        start = (page - 1) * page_size
        end = start + page_size

        return Response(
            {
                "document": {"id": str(doc.id), "title": doc.title},
                "run": ReviewRunSerializer(run).data,
                "findings": FindingSerializer(qs[start:end], many=True).data,
                "pagination": _pagination_payload(page=page, page_size=page_size, total=total),
            },
            status=status.HTTP_200_OK,
        )


def _safe_ordering(ordering: str | None) -> str:
    if not ordering:
        return "created_at"
    normalized = ordering.strip()
    if not normalized:
        return "created_at"
    base = normalized[1:] if normalized.startswith("-") else normalized
    allowed_fields = {"created_at", "severity", "source", "confidence"}
    if base not in allowed_fields:
        return "created_at"
    return normalized


def _default_page_size() -> int:
    return max(1, int(getattr(settings, "REVIEW_FINDINGS_DEFAULT_PAGE_SIZE", 50)))


def _max_page_size() -> int:
    return max(1, int(getattr(settings, "REVIEW_FINDINGS_MAX_PAGE_SIZE", 200)))


def _parse_positive_int(value: str | None, default: int) -> int:
    if value is None:
        return default
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default


def _pagination_payload(page: int, page_size: int, total: int) -> dict:
    total_pages = math.ceil(total / page_size) if total else 0
    return {
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": total_pages,
        "has_next": total_pages > 0 and page < total_pages,
        "has_prev": page > 1 and total_pages > 0,
    }
