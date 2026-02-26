import hashlib
import json
import time
from datetime import timedelta
from typing import Any, Dict, List, Optional, Tuple

from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.utils import timezone

from apps.documents.models import Document
from apps.review.embeddings import (
    build_finding_embedding_input,
    generate_embeddings,
    sync_pgvector_embeddings,
)
from apps.review.llm.prompts import PROMPT_REV
from apps.review.llm.provider import (
    generate_llm_findings_for_clauses,
    generate_llm_findings_with_usage_for_clauses,
)
from apps.review.models import (
    Finding,
    FindingSeverity,
    FindingSource,
    ReviewChunk,
    ReviewRun,
    ReviewRunStage,
    ReviewRunStatus,
)
from apps.review.preprocessing import CHUNK_SCHEMA_VERSION, preprocess_document_to_chunks
from apps.review.rules import run_rules

IDEMPOTENCY_WINDOW = timedelta(hours=24)


def run_full_analysis_for_instance(doc: Document) -> Dict[str, Any]:
    """
    Run the review pipeline for a loaded Document instance.
    """

    # Step 2.6 - preprocessing/chunk extraction
    chunks = preprocess_document_to_chunks(
        doc.text,
        source_type=getattr(doc, "source_type", "text"),
        ingestion_metadata=getattr(doc, "ingestion_metadata", {}),
    )
    clauses = [
        {"id": chunk["chunk_id"], "heading": chunk.get("heading"), "body": chunk.get("body")}
        for chunk in chunks
    ]

    # Step 4 - deterministic rules
    rule_findings = run_rules(clauses, preferred_jurisdiction="California")

    # Step 5 - LLM analysis
    llm_findings = generate_llm_findings_for_clauses(clauses)

    # Merge findings (later you can dedupe / reconcile)
    all_findings = rule_findings + llm_findings

    return {
        "document": {
            "id": str(doc.id),
            "title": doc.title,
        },
        "clauses": clauses,
        "chunks": chunks,
        "findings": all_findings,
    }


def _attach_chunk_pointers_to_findings(findings: List[Dict[str, Any]], chunks: List[Dict[str, Any]]) -> None:
    chunk_by_id = {chunk["chunk_id"]: chunk for chunk in chunks or []}
    for finding in findings or []:
        chunk_id = finding.get("chunk_id") or finding.get("clause_id")
        if not chunk_id:
            continue

        finding["chunk_id"] = chunk_id
        chunk = chunk_by_id.get(chunk_id)
        if not chunk:
            continue

        pointer = (chunk.get("metadata") or {}).get("evidence_pointer")
        if not pointer:
            continue

        evidence_text = finding.get("evidence") or finding.get("evidence_text") or ""
        span = finding.get("evidence_span")
        if not isinstance(span, dict):
            span = {"start": 0, "end": max(1, len(evidence_text))}
        span["pointer"] = pointer
        finding["evidence_span"] = span


def _document_hash(doc: Document) -> str:
    source_type = getattr(doc, "source_type", "text") or "text"
    metadata = getattr(doc, "ingestion_metadata", {}) or {}
    payload = json.dumps(
        {
            "source_type": source_type,
            "text": doc.text or "",
            "ingestion_metadata": metadata,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_pipeline_cache_key(doc: Document) -> str:
    return f"review:{_document_hash(doc)}:{PROMPT_REV}:{CHUNK_SCHEMA_VERSION}"


@transaction.atomic
def persist_findings_for_run(
    run: ReviewRun, clauses: List[Dict[str, Any]], findings: List[Dict[str, Any]]
) -> ReviewRun:
    """Persist findings for an existing run.

    Existing findings for the run are deleted before insert so retries remain idempotent.
    """

    doc = run.document

    by_chunk_id = {c.get("id"): c for c in (clauses or [])}

    # Best-effort extraction of run-level metadata from LLM findings.
    llm_model = None
    prompt_rev = None
    for f in findings or []:
        if f.get("source") == "llm":
            llm_model = f.get("model") or llm_model
            prompt_rev = f.get("prompt_rev") or prompt_rev
            break

    run.llm_model = llm_model
    run.prompt_rev = prompt_rev
    run.save(update_fields=["llm_model", "prompt_rev"])

    Finding.objects.filter(run=run).delete()

    rows: List[Finding] = []
    for f in findings or []:
        clause_id = f.get("clause_id")
        chunk_id = f.get("chunk_id") or clause_id
        clause = by_chunk_id.get(chunk_id) or by_chunk_id.get(clause_id) or {}

        # Normalize across rule + llm finding shapes
        evidence = f.get("evidence") or f.get("evidence_text") or ""

        rows.append(
            Finding(
                document=doc,
                run=run,
                clause_id=clause_id,
                chunk_id=chunk_id,
                clause_heading=clause.get("heading"),
                clause_body=clause.get("body"),
                summary=f.get("summary", ""),
                explanation=f.get("explanation"),
                recommendation=f.get("recommendation"),
                severity=f.get("severity") or f.get("risk") or FindingSeverity.MEDIUM,
                evidence=evidence,
                evidence_span=f.get("evidence_span"),
                source=f.get("source", FindingSource.UNKNOWN),
                rule_code=f.get("rule_code"),
                model=f.get("model"),
                confidence=f.get("confidence"),
                prompt_rev=f.get("prompt_rev"),
            )
        )

    if rows:
        Finding.objects.bulk_create(rows)
        _store_findings_embeddings(run)

    return run


def _store_findings_embeddings(run: ReviewRun) -> None:
    if not settings.REVIEW_ENABLE_EMBEDDINGS:
        return

    finding_rows = list(
        Finding.objects.filter(run=run).only("id", "summary", "explanation", "evidence", "embedding")
    )
    if not finding_rows:
        return

    embedding_inputs = [
        build_finding_embedding_input(
            summary=f.summary,
            explanation=f.explanation or "",
            evidence=f.evidence or "",
        )
        for f in finding_rows
    ]
    vectors = generate_embeddings(embedding_inputs)
    for finding, vector in zip(finding_rows, vectors):
        finding.embedding = vector

    Finding.objects.bulk_update(finding_rows, ["embedding"])
    sync_pgvector_embeddings(finding_rows)


@transaction.atomic
def persist_chunks_for_run(run: ReviewRun, chunks: List[Dict[str, Any]]) -> None:
    ReviewChunk.objects.filter(run=run).delete()

    rows: List[ReviewChunk] = []
    for chunk in chunks or []:
        rows.append(
            ReviewChunk(
                run=run,
                document=run.document,
                chunk_id=chunk["chunk_id"],
                schema_version=chunk.get("schema_version", "v1"),
                ordinal=chunk.get("ordinal") or 0,
                heading=chunk.get("heading"),
                body=chunk.get("body") or "",
                start_offset=chunk.get("start_offset"),
                end_offset=chunk.get("end_offset"),
                metadata=chunk.get("metadata") or {},
            )
        )
    if rows:
        ReviewChunk.objects.bulk_create(rows)


@transaction.atomic
def create_queued_review_run(
    doc: Document,
    idempotency_key: Optional[str] = None,
    request_fingerprint: Optional[str] = None,
) -> ReviewRun:
    return ReviewRun.objects.create(
        document=doc,
        idempotency_key=idempotency_key,
        request_fingerprint=request_fingerprint,
        status=ReviewRunStatus.QUEUED,
    )


def find_idempotent_run(
    doc: Document, idempotency_key: Optional[str]
) -> Tuple[Optional[ReviewRun], bool, bool]:
    """Return (run, reused, expired_key)."""
    if not idempotency_key:
        return None, False, False
    existing = (
        ReviewRun.objects.filter(document=doc, idempotency_key=idempotency_key)
        .order_by("-created_at")
        .first()
    )
    if not existing:
        return None, False, False

    if existing.created_at >= timezone.now() - IDEMPOTENCY_WINDOW:
        return existing, True, False

    return existing, False, True


def process_review_run(run_id: str) -> ReviewRun:
    run = ReviewRun.objects.select_related("document").get(id=run_id)
    doc = run.document
    stage_timings: Dict[str, int] = {}
    token_usage: Dict[str, Any] = {}
    llm_failed = False
    llm_error: Optional[str] = None

    now = timezone.now()
    update_fields = {
        "status": ReviewRunStatus.RUNNING,
        "error": None,
        "completed_at": None,
        "current_stage": ReviewRunStage.PREPROCESS,
        "stage_timings": {},
        "token_usage": {},
    }
    if run.started_at is None:
        update_fields["started_at"] = now
    cache_key = build_pipeline_cache_key(doc)
    update_fields["cache_key"] = cache_key
    for field, value in update_fields.items():
        setattr(run, field, value)
    run.save(update_fields=list(update_fields.keys()))

    try:
        cache_lookup_start = time.perf_counter()
        cached_payload = None
        if settings.REVIEW_ENABLE_PIPELINE_CACHE:
            cached_payload = cache.get(cache_key)
        stage_timings["cache_lookup_ms"] = int((time.perf_counter() - cache_lookup_start) * 1000)

        if cached_payload:
            run.cache_hits += 1
            chunks = cached_payload.get("chunks", [])
            clauses = [
                {"id": chunk["chunk_id"], "heading": chunk.get("heading"), "body": chunk.get("body")}
                for chunk in chunks
            ]
            all_findings = cached_payload.get("findings", [])
            token_usage = cached_payload.get("token_usage") or {}
            if cached_payload.get("llm_model"):
                run.llm_model = cached_payload.get("llm_model")
            if cached_payload.get("prompt_rev"):
                run.prompt_rev = cached_payload.get("prompt_rev")
            run.save(update_fields=["cache_hits", "llm_model", "prompt_rev"])
        else:
            run.cache_misses += 1
            run.save(update_fields=["cache_misses"])

            run.current_stage = ReviewRunStage.PREPROCESS
            run.save(update_fields=["current_stage"])
            preprocess_start = time.perf_counter()
            chunks = preprocess_document_to_chunks(
                doc.text,
                source_type=getattr(doc, "source_type", "text"),
                ingestion_metadata=getattr(doc, "ingestion_metadata", {}),
            )
            clauses = [
                {"id": chunk["chunk_id"], "heading": chunk.get("heading"), "body": chunk.get("body")}
                for chunk in chunks
            ]
            stage_timings["preprocess_ms"] = int((time.perf_counter() - preprocess_start) * 1000)

            run.current_stage = ReviewRunStage.RULES
            run.save(update_fields=["current_stage"])
            rules_start = time.perf_counter()
            rule_findings = run_rules(clauses, preferred_jurisdiction="California")
            stage_timings["rules_ms"] = int((time.perf_counter() - rules_start) * 1000)

            run.current_stage = ReviewRunStage.LLM
            run.save(update_fields=["current_stage"])
            llm_start = time.perf_counter()
            llm_findings: List[Dict[str, Any]] = []
            llm_model = None
            try:
                llm_findings, llm_model, token_usage = generate_llm_findings_with_usage_for_clauses(clauses)
            except TimeoutError as exc:
                llm_failed = True
                llm_error = f"LLM stage timeout: {exc}"
            except Exception as exc:
                llm_failed = True
                llm_error = f"LLM stage failed: {exc}"
            stage_timings["llm_ms"] = int((time.perf_counter() - llm_start) * 1000)

            if llm_failed:
                all_findings = rule_findings
            else:
                all_findings = rule_findings + llm_findings
            _attach_chunk_pointers_to_findings(all_findings, chunks)

            if settings.REVIEW_ENABLE_PIPELINE_CACHE:
                # Cache only fully successful runs.
                if not llm_failed:
                    cache.set(
                        cache_key,
                        {
                            "chunks": chunks,
                            "findings": all_findings,
                            "llm_model": llm_model,
                            "prompt_rev": PROMPT_REV,
                            "token_usage": token_usage,
                        },
                        timeout=settings.REVIEW_CACHE_TTL_SECONDS,
                    )

        run.current_stage = ReviewRunStage.PERSIST
        run.save(update_fields=["current_stage"])
        persist_start = time.perf_counter()
        persist_chunks_for_run(run, chunks)
        persist_findings_for_run(run, clauses, all_findings)
        stage_timings["persist_ms"] = int((time.perf_counter() - persist_start) * 1000)

        if llm_failed:
            run.status = ReviewRunStatus.PARTIAL
            run.error = llm_error
        else:
            run.status = ReviewRunStatus.SUCCEEDED
            run.error = None
        run.completed_at = timezone.now()
        run.current_stage = None
        run.token_usage = token_usage
        run.stage_timings = stage_timings
        run.save(
            update_fields=[
                "status",
                "error",
                "completed_at",
                "current_stage",
                "token_usage",
                "stage_timings",
            ]
        )
        return run
    except Exception as exc:
        run.status = ReviewRunStatus.FAILED
        run.error = str(exc)
        run.completed_at = timezone.now()
        run.stage_timings = stage_timings
        run.token_usage = token_usage
        run.save(
            update_fields=["status", "error", "completed_at", "stage_timings", "token_usage"]
        )
        raise
