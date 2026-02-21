from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.documents.models import Document
from apps.review.llm.schema import LLMValidationError, validate_llm_response


class LLMResponseSchemaTests(TestCase):
    def test_accepts_valid_payload(self):
        payload = {
            "findings": [
                {
                    "clause_id": "abc123",
                    "severity": "medium",
                    "summary": "Sample summary",
                    "explanation": "Sample explanation",
                    "evidence_text": "termination with 15 days notice",
                    "evidence_span": {"start": 5, "end": 22},
                    "confidence": 0.72,
                }
            ]
        }
        validated = validate_llm_response(payload)
        self.assertEqual(validated, payload)

    def test_rejects_missing_evidence_span(self):
        payload = {
            "findings": [
                {
                    "clause_id": "abc123",
                    "severity": "medium",
                    "summary": "Sample summary",
                    "explanation": "Sample explanation",
                    "evidence_text": "termination with 15 days notice",
                    "confidence": 0.72,
                }
            ]
        }
        with self.assertRaises(LLMValidationError):
            validate_llm_response(payload)


@override_settings(LLM_PROVIDER="mock")
class EvidenceSpanPersistenceTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.document = Document.objects.create(
            title="Test Agreement",
            text=(
                "1. Termination\n"
                "Either party may terminate this agreement with 15 days notice.\n\n"
                "2. Indemnity\n"
                "Vendor agrees to indemnify and hold harmless the customer."
            ),
        )

    def test_review_run_and_retrieval_include_evidence_spans(self):
        run_resp = self.client.post(
            "/v1/review/run",
            {"document_id": str(self.document.id)},
            format="json",
        )
        self.assertEqual(run_resp.status_code, 200)

        findings = run_resp.data.get("findings", [])
        self.assertTrue(findings)
        for finding in findings:
            self.assertIn("evidence_span", finding)
            span = finding["evidence_span"]
            self.assertIsInstance(span, dict)
            self.assertIn("start", span)
            self.assertIn("end", span)
            self.assertLess(span["start"], span["end"])

        run_id = run_resp.data["run"]["id"]
        get_resp = self.client.get(
            f"/v1/documents/{self.document.id}/findings",
            {"run_id": run_id},
        )
        self.assertEqual(get_resp.status_code, 200)
        persisted = get_resp.data.get("findings", [])
        self.assertTrue(persisted)
        for finding in persisted:
            self.assertIn("evidence_span", finding)
            span = finding["evidence_span"]
            self.assertIsInstance(span, dict)
            self.assertIn("start", span)
            self.assertIn("end", span)
