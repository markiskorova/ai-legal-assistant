import json
from typing import List, Dict

from django.conf import settings
from openai import OpenAI

from .prompts import SYSTEM_PROMPT, PROMPT_REV

import uuid
from typing import Tuple

client = OpenAI(api_key=getattr(settings, "OPENAI_API_KEY", None))


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


def call_llm_for_clauses(clauses: List[Dict]) -> List[Dict]:
    """
    Calls the LLM once with all clauses and returns a list of findings.

    Expected raw JSON response shape:
    {
      "findings": [
        {
          "clause_id": "...",
          "severity": "low|medium|high",
          "summary": "string",
          "explanation": "string",
          "evidence_text": "string",
          "confidence": 0.0-1.0
        },
        ...
      ]
    }
    """
    if not clauses:
        return []

    model = getattr(settings, "OPENAI_MODEL", "gpt-4o-mini")

    payload = {
        "clauses": _build_clauses_payload(clauses),
    }

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
        return []

    # Optionally: record tokens/cost in DB later using response.usage

    return findings_raw, model

def generate_llm_findings_for_clauses(clauses: List[Dict]) -> List[Dict]:
    """
    Public function:
    - Calls the LLM
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
        summary = item.get("summary", "").strip()
        explanation = item.get("explanation", "").strip()
        evidence_text = item.get("evidence_text", "").strip()
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
