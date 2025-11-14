from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .serializers import DocumentUploadSerializer, DocumentSerializer
from .models import Document
from .ingestion.pdf_reader import extract_pdf_text

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
