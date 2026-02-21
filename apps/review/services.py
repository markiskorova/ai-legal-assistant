from datetime import timedelta
from typing import Any, Dict, List, Optional, Tuple

from django.db import transaction
from django.utils import timezone

from apps.documents.models import Document
from apps.review.extractor import extract_clauses
from apps.review.rules import run_rules
from apps.review.llm.provider import generate_llm_findings_for_clauses
from apps.review.models import Finding, FindingSeverity, FindingSource, ReviewRun, ReviewRunStatus

IDEMPOTENCY_WINDOW = timedelta(hours=24)


def run_full_analysis_for_instance(doc: Document) -> Dict[str, Any]:
    """
    Run the review pipeline for a loaded Document instance.
    """

    # Step 3 - clause extraction
    clauses = extract_clauses(doc.text)

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
        "findings": all_findings,
    }


@transaction.atomic
def persist_findings_for_run(
    run: ReviewRun, clauses: List[Dict[str, Any]], findings: List[Dict[str, Any]]
) -> ReviewRun:
    """Persist findings for an existing run.

    Existing findings for the run are deleted before insert so retries remain idempotent.
    """

    doc = run.document

    by_clause_id = {c.get("id"): c for c in (clauses or [])}

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
        clause = by_clause_id.get(clause_id) or {}

        # Normalize across rule + llm finding shapes
        evidence = f.get("evidence") or f.get("evidence_text") or ""

        rows.append(
            Finding(
                document=doc,
                run=run,
                clause_id=clause_id,
                clause_heading=clause.get("heading"),
                clause_body=clause.get("body"),
                summary=f.get("summary", ""),
                explanation=f.get("explanation"),
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

    return run


@transaction.atomic
def create_queued_review_run(doc: Document, idempotency_key: Optional[str] = None) -> ReviewRun:
    return ReviewRun.objects.create(
        document=doc,
        idempotency_key=idempotency_key,
        status=ReviewRunStatus.QUEUED,
    )


def get_or_create_idempotent_run(
    doc: Document, idempotency_key: Optional[str]
) -> Tuple[ReviewRun, bool, bool]:
    """Return (run, reused, expired_key)."""

    if not idempotency_key:
        return create_queued_review_run(doc), False, False

    existing = (
        ReviewRun.objects.filter(document=doc, idempotency_key=idempotency_key)
        .order_by("-created_at")
        .first()
    )
    if not existing:
        return create_queued_review_run(doc, idempotency_key=idempotency_key), False, False

    if existing.created_at >= timezone.now() - IDEMPOTENCY_WINDOW:
        return existing, True, False

    return existing, False, True


def process_review_run(run_id: str) -> ReviewRun:
    run = ReviewRun.objects.select_related("document").get(id=run_id)
    doc = run.document

    run.status = ReviewRunStatus.RUNNING
    run.error = None
    run.save(update_fields=["status", "error"])

    try:
        payload = run_full_analysis_for_instance(doc)
        persist_findings_for_run(run, payload.get("clauses", []), payload.get("findings", []))
        run.status = ReviewRunStatus.SUCCEEDED
        run.save(update_fields=["status"])
        return run
    except Exception as exc:
        run.status = ReviewRunStatus.FAILED
        run.error = str(exc)
        run.save(update_fields=["status", "error"])
        raise
