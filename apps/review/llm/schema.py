"""Strict schema definitions and validators for LLM review responses."""

from __future__ import annotations

from typing import Any, Dict, List


FINDINGS_JSON_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["findings"],
    "properties": {
        "findings": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "clause_id",
                    "severity",
                    "summary",
                    "explanation",
                    "evidence_text",
                    "evidence_span",
                    "confidence",
                ],
                "properties": {
                    "clause_id": {"type": "string", "minLength": 1},
                    "severity": {"type": "string", "enum": ["low", "medium", "high"]},
                    "summary": {"type": "string", "minLength": 1},
                    "explanation": {"type": "string", "minLength": 1},
                    "evidence_text": {"type": "string", "minLength": 1},
                    "evidence_span": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["start", "end"],
                        "properties": {
                            "start": {"type": "integer", "minimum": 0},
                            "end": {"type": "integer", "minimum": 1},
                        },
                    },
                    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                },
            },
        }
    },
}


class LLMValidationError(ValueError):
    """Raised when LLM output does not match strict response requirements."""


def _require_keys(obj: Dict[str, Any], required: List[str], context: str) -> None:
    missing = [k for k in required if k not in obj]
    if missing:
        raise LLMValidationError(f"{context}: missing required keys: {missing}")


def _reject_extra_keys(obj: Dict[str, Any], allowed: List[str], context: str) -> None:
    extra = [k for k in obj.keys() if k not in allowed]
    if extra:
        raise LLMValidationError(f"{context}: unexpected keys: {extra}")


def _require_non_empty_str(value: Any, context: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise LLMValidationError(f"{context}: expected non-empty string")


def validate_llm_response(raw: Any) -> Dict[str, Any]:
    """Validate the top-level LLM response and each finding strictly."""
    if not isinstance(raw, dict):
        raise LLMValidationError("root: expected object")

    _require_keys(raw, ["findings"], "root")
    _reject_extra_keys(raw, ["findings"], "root")

    findings = raw["findings"]
    if not isinstance(findings, list):
        raise LLMValidationError("root.findings: expected array")

    allowed_finding_keys = [
        "clause_id",
        "severity",
        "summary",
        "explanation",
        "evidence_text",
        "evidence_span",
        "confidence",
    ]

    for idx, finding in enumerate(findings):
        ctx = f"finding[{idx}]"
        if not isinstance(finding, dict):
            raise LLMValidationError(f"{ctx}: expected object")

        _require_keys(finding, allowed_finding_keys, ctx)
        _reject_extra_keys(finding, allowed_finding_keys, ctx)

        _require_non_empty_str(finding["clause_id"], f"{ctx}.clause_id")
        severity = finding["severity"]
        if severity not in ("low", "medium", "high"):
            raise LLMValidationError(f"{ctx}.severity: expected one of low|medium|high")

        _require_non_empty_str(finding["summary"], f"{ctx}.summary")
        _require_non_empty_str(finding["explanation"], f"{ctx}.explanation")
        _require_non_empty_str(finding["evidence_text"], f"{ctx}.evidence_text")

        span = finding["evidence_span"]
        if not isinstance(span, dict):
            raise LLMValidationError(f"{ctx}.evidence_span: expected object")
        _require_keys(span, ["start", "end"], f"{ctx}.evidence_span")
        _reject_extra_keys(span, ["start", "end"], f"{ctx}.evidence_span")

        start = span["start"]
        end = span["end"]
        if not isinstance(start, int) or not isinstance(end, int):
            raise LLMValidationError(f"{ctx}.evidence_span: start/end must be integers")
        if start < 0 or end <= start:
            raise LLMValidationError(f"{ctx}.evidence_span: expected 0 <= start < end")

        confidence = finding["confidence"]
        if not isinstance(confidence, (int, float)):
            raise LLMValidationError(f"{ctx}.confidence: expected number")
        if confidence < 0 or confidence > 1:
            raise LLMValidationError(f"{ctx}.confidence: expected between 0 and 1")

    return raw
