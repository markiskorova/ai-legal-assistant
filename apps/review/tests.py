from datetime import timedelta
from unittest.mock import patch

from django.core.cache import cache
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.documents.models import Document
from apps.review.models import Finding, ReviewChunk, ReviewRun
from apps.review.llm.schema import LLMValidationError, validate_llm_response
from apps.review.services import create_queued_review_run, process_review_run


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

        status_resp = self.client.get(f"/v1/review-runs/{run_id}")
        self.assertEqual(status_resp.status_code, 200)
        self.assertEqual(status_resp.data["run"]["status"], "queued")
        self.assertIsNone(status_resp.data["run"]["started_at"])
        self.assertIsNone(status_resp.data["run"]["completed_at"])
        self.assertIsNone(status_resp.data["run"]["current_stage"])


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
            self.assertIn("chunk_id", finding)
            self.assertTrue(finding["chunk_id"])
            span = finding["evidence_span"]
            self.assertIsInstance(span, dict)
            self.assertIn("start", span)
            self.assertIn("end", span)
            self.assertLess(span["start"], span["end"])

        chunks = ReviewChunk.objects.filter(run_id=run_id).order_by("ordinal")
        self.assertTrue(chunks.exists())
        for chunk in chunks:
            self.assertTrue(chunk.chunk_id.startswith("chk_"))
            self.assertEqual(chunk.schema_version, "v1")

        status_resp = self.client.get(f"/v1/review-runs/{run_id}")
        self.assertEqual(status_resp.status_code, 200)
        self.assertEqual(status_resp.data["run"]["status"], "succeeded")
        self.assertIsNotNone(status_resp.data["run"]["started_at"])
        self.assertIsNotNone(status_resp.data["run"]["completed_at"])
        self.assertIsNone(status_resp.data["run"]["current_stage"])
        self.assertGreater(status_resp.data["run"]["findings_count"], 0)

    def test_integration_enqueue_run_persist_retrieve(self):
        enqueue_resp = self.client.post(
            "/v1/review/run",
            {"document_id": str(self.document.id)},
            format="json",
        )
        self.assertEqual(enqueue_resp.status_code, 202)
        run_id = enqueue_resp.data["run"]["id"]

        run_resp = self.client.get(f"/v1/review-runs/{run_id}")
        self.assertEqual(run_resp.status_code, 200)
        self.assertEqual(run_resp.data["run"]["id"], run_id)
        self.assertIn(run_resp.data["run"]["status"], ["succeeded", "partial"])

        findings_resp = self.client.get(
            f"/v1/documents/{self.document.id}/findings",
            {"run_id": run_id},
        )
        self.assertEqual(findings_resp.status_code, 200)
        self.assertEqual(findings_resp.data["run"]["id"], run_id)
        self.assertGreaterEqual(len(findings_resp.data["findings"]), 1)


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


@override_settings(LLM_PROVIDER="mock")
class WorkerRetrySafetyTests(TestCase):
    def setUp(self):
        self.document = Document.objects.create(
            title="Retry Safety Contract",
            text=(
                "1. Termination\n"
                "Either party may terminate this agreement with 15 days notice.\n\n"
                "2. Indemnity\n"
                "Vendor agrees to indemnify and hold harmless the customer."
            ),
        )

    def test_reprocessing_run_does_not_duplicate_findings(self):
        run = create_queued_review_run(self.document)

        process_review_run(str(run.id))
        first_count = Finding.objects.filter(run=run).count()
        first_chunk_ids = list(ReviewChunk.objects.filter(run=run).order_by("ordinal").values_list("chunk_id", flat=True))
        self.assertGreater(first_count, 0)
        self.assertTrue(first_chunk_ids)

        process_review_run(str(run.id))
        second_count = Finding.objects.filter(run=run).count()
        second_chunk_ids = list(ReviewChunk.objects.filter(run=run).order_by("ordinal").values_list("chunk_id", flat=True))
        self.assertEqual(second_count, first_count)
        self.assertEqual(second_chunk_ids, first_chunk_ids)


@override_settings(LLM_PROVIDER="mock", CELERY_TASK_ALWAYS_EAGER=True)
class SpreadsheetEvidencePointerTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.document = Document.objects.create(
            title="Spreadsheet Contract",
            text=(
                "[Sheet: Terms]\n"
                "Row 2: Clause=Termination ; Detail=Either party may terminate with 30 days notice\n"
                "Row 3: Clause=Indemnity ; Detail=Vendor indemnifies customer\n"
            ),
            source_type="spreadsheet",
            ingestion_metadata={
                "kind": "spreadsheet",
                "schema_version": "v1",
                "sheets": [
                    {
                        "name": "Terms",
                        "columns": ["Clause", "Detail"],
                        "rows": [
                            {
                                "row_number": 2,
                                "cells": ["Termination", "Either party may terminate with 30 days notice"],
                                "cell_map": {
                                    "Clause": "Termination",
                                    "Detail": "Either party may terminate with 30 days notice",
                                },
                                "text": "Clause=Termination ; Detail=Either party may terminate with 30 days notice",
                            },
                            {
                                "row_number": 3,
                                "cells": ["Indemnity", "Vendor indemnifies customer"],
                                "cell_map": {
                                    "Clause": "Indemnity",
                                    "Detail": "Vendor indemnifies customer",
                                },
                                "text": "Clause=Indemnity ; Detail=Vendor indemnifies customer",
                            },
                        ],
                    }
                ],
            },
        )

    def test_spreadsheet_findings_include_pointer_metadata(self):
        run_resp = self.client.post(
            "/v1/review/run",
            {"document_id": str(self.document.id)},
            format="json",
        )
        self.assertEqual(run_resp.status_code, 202)
        run_id = run_resp.data["run"]["id"]

        findings_resp = self.client.get(
            f"/v1/documents/{self.document.id}/findings",
            {"run_id": run_id},
        )
        self.assertEqual(findings_resp.status_code, 200)
        findings = findings_resp.data.get("findings", [])
        self.assertTrue(findings)

        for finding in findings:
            span = finding.get("evidence_span")
            self.assertIsInstance(span, dict)
            pointer = span.get("pointer")
            self.assertIsInstance(pointer, dict)
            self.assertEqual(pointer.get("kind"), "spreadsheet")
            self.assertEqual(pointer.get("sheet"), "Terms")
            self.assertIn("row_start", pointer)
            self.assertIn("row_end", pointer)

        chunks = ReviewChunk.objects.filter(run_id=run_id)
        self.assertTrue(chunks.exists())
        for chunk in chunks:
            pointer = (chunk.metadata or {}).get("evidence_pointer")
            self.assertIsInstance(pointer, dict)
            self.assertEqual(pointer.get("kind"), "spreadsheet")


@override_settings(LLM_PROVIDER="mock", CELERY_TASK_ALWAYS_EAGER=True, REVIEW_ENABLE_PIPELINE_CACHE=True)
class RunInstrumentationCacheTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.document = Document.objects.create(
            title="Cache Contract",
            text=(
                "1. Termination\n"
                "Either party may terminate this agreement with 15 days notice.\n\n"
                "2. Indemnity\n"
                "Vendor agrees to indemnify and hold harmless the customer."
            ),
        )

    def test_second_run_uses_cache_and_records_metrics(self):
        first_resp = self.client.post(
            "/v1/review/run",
            {"document_id": str(self.document.id)},
            format="json",
        )
        self.assertEqual(first_resp.status_code, 202)
        first_run_id = first_resp.data["run"]["id"]
        first_run = ReviewRun.objects.get(id=first_run_id)
        self.assertEqual(first_run.status, "succeeded")
        self.assertEqual(first_run.cache_misses, 1)
        self.assertEqual(first_run.cache_hits, 0)
        self.assertIn("preprocess_ms", first_run.stage_timings)
        self.assertIn("rules_ms", first_run.stage_timings)
        self.assertIn("llm_ms", first_run.stage_timings)
        self.assertIn("persist_ms", first_run.stage_timings)
        self.assertIn("total_tokens", first_run.token_usage)
        self.assertTrue(first_run.cache_key)

        second_resp = self.client.post(
            "/v1/review/run",
            {"document_id": str(self.document.id)},
            format="json",
        )
        self.assertEqual(second_resp.status_code, 202)
        second_run_id = second_resp.data["run"]["id"]
        second_run = ReviewRun.objects.get(id=second_run_id)
        self.assertEqual(second_run.status, "succeeded")
        self.assertEqual(second_run.cache_hits, 1)
        self.assertEqual(second_run.cache_misses, 0)
        self.assertIn("cache_lookup_ms", second_run.stage_timings)
        self.assertIn("persist_ms", second_run.stage_timings)
        self.assertTrue(second_run.cache_key)


@override_settings(LLM_PROVIDER="mock", REVIEW_MAX_CONCURRENT_RUNS=1, REVIEW_RATE_LIMIT_PER_MINUTE=10)
class ConcurrencyLimitTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.document = Document.objects.create(
            title="Concurrent Contract",
            text="Contract text.",
        )

    def test_rejects_when_concurrency_cap_reached(self):
        ReviewRun.objects.create(
            document=self.document,
            status="queued",
            request_fingerprint="ip:127.0.0.1",
        )
        resp = self.client.post(
            "/v1/review/run",
            {"document_id": str(self.document.id)},
            format="json",
        )
        self.assertEqual(resp.status_code, 429)
        self.assertIn("Too many concurrent review runs", resp.data["detail"])


@override_settings(LLM_PROVIDER="mock", REVIEW_MAX_CONCURRENT_RUNS=50, REVIEW_RATE_LIMIT_PER_MINUTE=1)
class RateLimitTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.document = Document.objects.create(
            title="Rate Limit Contract",
            text="Contract text.",
        )

    def test_rejects_when_rate_limit_reached(self):
        ReviewRun.objects.create(
            document=self.document,
            status="succeeded",
            request_fingerprint="ip:127.0.0.1",
        )
        resp = self.client.post(
            "/v1/review/run",
            {"document_id": str(self.document.id)},
            format="json",
        )
        self.assertEqual(resp.status_code, 429)
        self.assertIn("Rate limit exceeded", resp.data["detail"])


@override_settings(LLM_PROVIDER="mock", REVIEW_ENABLE_PIPELINE_CACHE=False)
class FailureModePolicyTests(TestCase):
    def setUp(self):
        self.document = Document.objects.create(
            title="Failure Mode Contract",
            text=(
                "1. Termination\n"
                "Either party may terminate this agreement with 15 days notice.\n\n"
                "2. Indemnity\n"
                "Vendor agrees to indemnify and hold harmless the customer."
            ),
        )

    def test_worker_crash_marks_failed_with_no_findings(self):
        run = create_queued_review_run(self.document)
        with patch("apps.review.services.preprocess_document_to_chunks", side_effect=RuntimeError("boom")):
            with self.assertRaises(RuntimeError):
                process_review_run(str(run.id))

        run.refresh_from_db()
        self.assertEqual(run.status, "failed")
        self.assertIn("boom", run.error or "")
        self.assertIsNotNone(run.completed_at)
        self.assertEqual(Finding.objects.filter(run=run).count(), 0)

    def test_llm_timeout_marks_partial_and_persists_rule_findings(self):
        run = create_queued_review_run(self.document)
        with patch(
            "apps.review.services.generate_llm_findings_with_usage_for_clauses",
            side_effect=TimeoutError("upstream timeout"),
        ):
            process_review_run(str(run.id))

        run.refresh_from_db()
        self.assertEqual(run.status, "partial")
        self.assertIn("timeout", (run.error or "").lower())
        self.assertIsNotNone(run.completed_at)
        self.assertIn("llm_ms", run.stage_timings)
        self.assertIn("persist_ms", run.stage_timings)

        findings = list(Finding.objects.filter(run=run))
        self.assertGreater(len(findings), 0)
        self.assertTrue(all(f.source == "rule" for f in findings))
