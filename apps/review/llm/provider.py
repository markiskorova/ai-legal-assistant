import json
import uuid
from typing import List, Dict, Tuple

from django.conf import settings
from openai import OpenAI

from .prompts import SYSTEM_PROMPT, PROMPT_REV


def _build_clauses_payload(clauses: List[Dict]) -> List[Dict]:
    """
    Minimal payload to send to the LLM: only what it needs.
    """
    return [
        {
            "id": clause["id"],
            "heading": clause.get("heading"),
            "body": clause.get("body"),
        }
        for clause in clauses
    ]


def _mock_findings_for_clauses(clauses: List[Dict]) -> List[Dict]:
    """
    Simple deterministic mock response:
    - One finding per clause
    - evidence_text is non-empty so your evidence gating keeps it
    """
    findings: List[Dict] = []

    for c in clauses:
        clause_id = c["id"]
        heading = (c.get("heading") or "").strip()
        body = (c.get("body") or "").strip()

        evidence_text = body[:200] if body else (heading[:200] if heading else "Evidence unavailable.")
        summary = "Mock review: potential issues flagged for review."
        if heading:
            summary = f"Mock review ({heading}): potential issues flagged for review."

        findings.append(
            {
                "clause_id": clause_id,
                "severity": "medium",
                "summary": summary,
                "explanation": "Mock mode is enabled, so this finding was generated without an LLM call.",
                "evidence_text": evidence_text,
                "confidence": 0.65,
            }
        )

    return findings


def call_llm_for_clauses(clauses: List[Dict]) -> Tuple[List[Dict], str]:
    """
    Calls the LLM once with all clauses and returns (raw_findings, model_name).

    Raw JSON response shape:
    {
      "findings": [
        {
          "clause_id": "...",
          "severity": "low|medium|high",
          "summary": "string",
          "explanation": "string",
          "evidence_text": "string",
          "confidence": 0.0-1.0
        }
      ]
    }
    """
    provider = getattr(settings, "LLM_PROVIDER", "openai").lower()

    # 1) Quick mock check
    if provider == "mock":
        return _mock_findings_for_clauses(clauses), "mock"

    model = getattr(settings, "OPENAI_MODEL", "gpt-4o-mini")

    # Always return a tuple (findings, model)
    if not clauses:
        return [], model

    api_key = getattr(settings, "OPENAI_API_KEY", None)

    # Optional: if no key, silently fall back to mock so you can keep working.
    if not api_key:
        return _mock_findings_for_clauses(clauses), "mock"

    client = OpenAI(api_key=api_key)

    payload = {"clauses": _build_clauses_payload(clauses)}

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT.strip()},
        {
            "role": "user",
            "content": (
                "Review the following clauses and return JSON with a 'findings' array.\n\n"
                + json.dumps(payload)
            ),
        },
    ]

    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.1,
        response_format={"type": "json_object"},
    )

    content = response.choices[0].message.content
    raw = json.loads(content)

    findings_raw = raw.get("findings", [])
    if not isinstance(findings_raw, list):
        return [], model

    return findings_raw, model


def generate_llm_findings_for_clauses(clauses: List[Dict]) -> List[Dict]:
    """
    Public function:
    - Calls the LLM (or mock)
    - Normalizes the raw JSON into internal finding dicts
    """
    raw_findings, model = call_llm_for_clauses(clauses)

    by_clause_id = {c["id"]: c for c in clauses}

    normalized: List[Dict] = []
    for item in raw_findings:
        clause_id = item.get("clause_id")
        if clause_id not in by_clause_id:
            continue

        severity = item.get("severity", "medium")
        summary = (item.get("summary") or "").strip()
        explanation = (item.get("explanation") or "").strip()
        evidence_text = (item.get("evidence_text") or "").strip()
        confidence = item.get("confidence", 0.8)

        if not evidence_text:
            # Simple "evidence gating": skip items without evidence.
            continue

        normalized.append(
            {
                "id": str(uuid.uuid4()),
                "clause_id": clause_id,
                "rule_code": None,  # only for deterministic rules
                "severity": severity,
                "summary": summary,
                "explanation": explanation,
                "evidence_text": evidence_text,
                "source": "llm",
                "confidence": float(confidence),
                "model": model,
                "prompt_rev": PROMPT_REV,
            }
        )

    return normalized
