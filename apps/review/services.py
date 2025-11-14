from typing import Any, Dict

from apps.documents.models import Document
from apps.review.extractor import extract_clauses
from apps.review.rules import run_rules
from apps.review.llm.provider import generate_llm_findings_for_clauses


def run_full_analysis_for_document(document_id: str) -> Dict[str, Any]:
    """
    Combined pipeline for MVP:
    - Load document
    - Clause extraction
    - Rule engine
    - LLM findings

    Returns a dict suitable for the /v1/review/run endpoint:
    {
        "document": {...},
        "clauses": [...],
        "findings": [...]
    }
    """
    doc = Document.objects.get(id=document_id)
    return run_full_analysis_for_instance(doc)


def run_full_analysis_for_instance(doc: Document) -> Dict[str, Any]:
    """
    Same as run_full_analysis_for_document, but takes a Document instance.
    Useful if you already have the Document loaded.
    """

    # Step 3 — clause extraction
    clauses = extract_clauses(doc.text)

    # Step 4 — deterministic rules
    rule_findings = run_rules(clauses, preferred_jurisdiction="California")

    # Step 5 — LLM analysis
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
