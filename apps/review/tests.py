from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.documents.models import Document
from apps.review.models import ReviewRun
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

    @patch("apps.review.views.process_review_run_task.delay")
    def test_review_run_and_retrieval_include_evidence_spans(self, mock_delay):
        run_resp = self.client.post(
            "/v1/review/run",
            {"document_id": str(self.document.id)},
            format="json",
        )
        self.assertEqual(run_resp.status_code, 202)
        self.assertEqual(run_resp.data["run"]["status"], "queued")
        self.assertEqual(mock_delay.call_count, 1)

        run_id = run_resp.data["run"]["id"]
        get_resp = self.client.get(
            f"/v1/documents/{self.document.id}/findings",
            {"run_id": run_id},
        )
        self.assertEqual(get_resp.status_code, 200)
        self.assertEqual(get_resp.data["findings"], [])


@override_settings(LLM_PROVIDER="mock", CELERY_TASK_ALWAYS_EAGER=True)
class AsyncReviewRunEagerExecutionTests(TestCase):
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

    def test_eager_task_execution_persists_findings(self):
        run_resp = self.client.post(
            "/v1/review/run",
            {"document_id": str(self.document.id)},
            format="json",
        )
        self.assertEqual(run_resp.status_code, 202)
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
            self.assertLess(span["start"], span["end"])


@override_settings(LLM_PROVIDER="mock")
class IdempotencyRunTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.document = Document.objects.create(
            title="Idempotency Contract",
            text="Simple contract body for idempotency testing.",
        )

    @patch("apps.review.views.process_review_run_task.delay")
    def test_reuses_existing_run_for_same_recent_idempotency_key(self, mock_delay):
        headers = {"HTTP_IDEMPOTENCY_KEY": "dup-key-1"}
        first = self.client.post(
            "/v1/review/run",
            {"document_id": str(self.document.id)},
            format="json",
            **headers,
        )
        self.assertEqual(first.status_code, 202)
        first_run_id = first.data["run"]["id"]

        second = self.client.post(
            "/v1/review/run",
            {"document_id": str(self.document.id)},
            format="json",
            **headers,
        )
        self.assertEqual(second.status_code, 200)
        self.assertTrue(second.data["idempotency_reused"])
        self.assertEqual(second.data["run"]["id"], first_run_id)

        self.assertEqual(mock_delay.call_count, 1)

    @patch("apps.review.views.process_review_run_task.delay")
    def test_expired_idempotency_key_returns_conflict(self, mock_delay):
        key = "expired-key-1"
        run = ReviewRun.objects.create(
            document=self.document,
            idempotency_key=key,
            status="queued",
        )
        ReviewRun.objects.filter(id=run.id).update(created_at=timezone.now() - timedelta(hours=25))

        resp = self.client.post(
            "/v1/review/run",
            {"document_id": str(self.document.id)},
            format="json",
            HTTP_IDEMPOTENCY_KEY=key,
        )
        self.assertEqual(resp.status_code, 409)
        self.assertIn("run_id", resp.data)
        self.assertEqual(mock_delay.call_count, 0)
