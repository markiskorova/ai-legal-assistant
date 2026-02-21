from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework.test import APIClient

from apps.documents.models import Document


class DocumentAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_upload_text_document_creates_record(self):
        upload = SimpleUploadedFile(
            "sample.txt",
            b"Confidentiality: The parties agree to keep information secret.",
            content_type="text/plain",
        )
        resp = self.client.post(
            "/v1/documents/upload",
            {"title": "Sample Contract", "file": upload},
            format="multipart",
        )
        self.assertEqual(resp.status_code, 201)
        self.assertIn("id", resp.data)
        self.assertEqual(resp.data["title"], "Sample Contract")

    def test_findings_endpoint_returns_empty_when_no_runs(self):
        doc = Document.objects.create(title="No Runs Yet", text="Simple contract body.")
        resp = self.client.get(f"/v1/documents/{doc.id}/findings")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["run"], None)
        self.assertEqual(resp.data["findings"], [])
