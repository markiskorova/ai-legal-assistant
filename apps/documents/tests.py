from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from openpyxl import Workbook
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

    def test_upload_csv_document_creates_spreadsheet_record(self):
        upload = SimpleUploadedFile(
            "clauses.csv",
            b"Clause,Risk\nTermination notice,High\nIndemnity,Medium\n",
            content_type="text/csv",
        )
        resp = self.client.post(
            "/v1/documents/upload",
            {"title": "CSV Contract Data", "file": upload},
            format="multipart",
        )
        self.assertEqual(resp.status_code, 201)

        doc = Document.objects.get(id=resp.data["id"])
        self.assertEqual(doc.source_type, "spreadsheet")
        self.assertEqual(doc.ingestion_metadata.get("kind"), "spreadsheet")
        self.assertIn("sheets", doc.ingestion_metadata)
        self.assertTrue(doc.ingestion_metadata["sheets"][0]["rows"])
        self.assertIn("[Sheet: Sheet1]", doc.text)

    def test_upload_xlsx_document_creates_spreadsheet_record(self):
        wb = Workbook()
        ws = wb.active
        ws.title = "Terms"
        ws.append(["Clause", "Detail"])
        ws.append(["Termination", "Either party may terminate with 30 days notice"])
        ws.append(["Indemnity", "Vendor indemnifies customer"])
        buffer = BytesIO()
        wb.save(buffer)

        upload = SimpleUploadedFile(
            "clauses.xlsx",
            buffer.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        resp = self.client.post(
            "/v1/documents/upload",
            {"title": "XLSX Contract Data", "file": upload},
            format="multipart",
        )
        self.assertEqual(resp.status_code, 201)

        doc = Document.objects.get(id=resp.data["id"])
        self.assertEqual(doc.source_type, "spreadsheet")
        self.assertEqual(doc.ingestion_metadata.get("kind"), "spreadsheet")
        self.assertIn("Terms", [s["name"] for s in doc.ingestion_metadata.get("sheets", [])])
        self.assertIn("[Sheet: Terms]", doc.text)
