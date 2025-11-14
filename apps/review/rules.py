import re
import uuid
from typing import List, Dict, Sequence, Optional
from typing import Literal

Severity = Literal["low", "medium", "high"]


def _make_finding(
    *,
    clause_id: str,
    rule_code: str,
    severity: Severity,
    summary: str,
    explanation: str,
    evidence_text: str,
) -> Dict:
    return {
        "id": str(uuid.uuid4()),
        "clause_id": clause_id,
        "rule_code": rule_code,
        "severity": severity,
        "summary": summary,
        "explanation": explanation,
        "evidence_text": evidence_text.strip(),
        "source": "rule",
    }


def _find_min_days(text: str) -> Optional[int]:
    """
    Find the smallest 'X days' mentioned in the text.
    Matches things like '30 days', '15 business days', etc.
    """
    pattern = re.compile(r"(\d+)\s+(business\s+)?days?", re.IGNORECASE)
    days = []
    for match in pattern.finditer(text):
        try:
            days.append(int(match.group(1)))
        except ValueError:
            continue
    return min(days) if days else None


def _find_max_years(text: str) -> Optional[int]:
    """
    Find the largest 'X years' mentioned in the text.
    Useful for confidentiality duration.
    """
    pattern = re.compile(r"(\d+)\s+years?", re.IGNORECASE)
    years = []
    for match in pattern.finditer(text):
        try:
            years.append(int(match.group(1)))
        except ValueError:
            continue
    return max(years) if years else None


def _short_snippet(text: str, max_len: int = 280) -> str:
    text = text.strip()
    if len(text) <= max_len:
        return text
    return text[: max_len - 3].rstrip() + "..."


# --------------------------------------------------------------------
# Individual rules
# --------------------------------------------------------------------

def rule_termination_notice_period(clause: Dict, **kwargs) -> List[Dict]:
    """
    Flag if termination notice period appears shorter than 30 days.
    """
    heading = clause.get("heading", "")
    body = clause.get("body", "")
    text = f"{heading}\n{body}"

    if not re.search(r"terminate|termination", text, re.IGNORECASE):
        return []

    min_days = _find_min_days(text)
    if min_days is None:
        return []

    findings: List[Dict] = []

    if min_days < 30:
        severity: Severity = "high"
        summary = "Short termination notice period (< 30 days)."
    elif min_days < 60:
        severity = "medium"
        summary = "Termination notice period between 30 and 60 days."
    else:
        # 60+ days: don't flag for now
        return []

    explanation = (
        f"The termination clause appears to allow termination with only {min_days} days' notice. "
        f"This may be shorter than a typical minimum of 30 days."
    )
    evidence = _short_snippet(text)

    findings.append(
        _make_finding(
            clause_id=clause["id"],
            rule_code="TERM_NOTICE_MIN",
            severity=severity,
            summary=summary,
            explanation=explanation,
            evidence_text=evidence,
        )
    )
    return findings


def rule_indemnity_clause(clause: Dict, **kwargs) -> List[Dict]:
    """
    Identify indemnity clauses. For MVP, simply flag presence as 'high' risk.
    """
    heading = clause.get("heading", "")
    body = clause.get("body", "")
    text = f"{heading}\n{body}"

    if not re.search(r"indemnify|indemnification", text, re.IGNORECASE):
        return []

    summary = "Indemnity clause present."
    explanation = (
        "This clause includes indemnity language (e.g., 'indemnify' or 'indemnification'). "
        "Indemnity provisions can shift significant liability and should be reviewed carefully."
    )
    evidence = _short_snippet(text)

    return [
        _make_finding(
            clause_id=clause["id"],
            rule_code="INDEMNITY_PRESENT",
            severity="high",
            summary=summary,
            explanation=explanation,
            evidence_text=evidence,
        )
    ]


def rule_confidentiality_duration(clause: Dict, **kwargs) -> List[Dict]:
    """
    Flag confidentiality clauses with long or perpetual duration.
    """
    heading = clause.get("heading", "")
    body = clause.get("body", "")
    text = f"{heading}\n{body}"

    if not re.search(
        r"confidentiality|confidential information|non[- ]disclosure|nondisclosure",
        text,
        re.IGNORECASE,
    ):
        return []

    # Perpetual / indefinite language
    if re.search(r"perpetual|in\s+perpetuity|indefinite", text, re.IGNORECASE):
        summary = "Confidentiality obligations appear perpetual."
        explanation = (
            "The confidentiality clause appears to impose obligations in perpetuity or indefinitely. "
            "This may be more restrictive than typical time-limited confidentiality provisions."
        )
        evidence = _short_snippet(text)
        return [
            _make_finding(
                clause_id=clause["id"],
                rule_code="CONF_PERPETUAL",
                severity="high",
                summary=summary,
                explanation=explanation,
                evidence_text=evidence,
            )
        ]

    # Explicit number of years
    max_years = _find_max_years(text)
    if max_years is None:
        return []

    findings: List[Dict] = []
    if max_years > 5:
        severity: Severity = "medium"
        summary = "Confidentiality obligations longer than 5 years."
        explanation = (
            f"The confidentiality clause appears to apply for {max_years} years, "
            "which may be longer than common 2–5 year periods."
        )
        evidence = _short_snippet(text)
        findings.append(
            _make_finding(
                clause_id=clause["id"],
                rule_code="CONF_LONG_TERM",
                severity=severity,
                summary=summary,
                explanation=explanation,
                evidence_text=evidence,
            )
        )

    return findings


def rule_governing_law_mismatch(clause: Dict, *, preferred_jurisdiction: str = "California", **kwargs) -> List[Dict]:
    """
    Flag governing law clauses that don't match the preferred jurisdiction.
    """
    heading = clause.get("heading", "")
    body = clause.get("body", "")
    text = f"{heading}\n{body}"

    if not re.search(r"governing law|laws of", text, re.IGNORECASE):
        return []

    if re.search(preferred_jurisdiction, text, re.IGNORECASE):
        return []

    summary = f"Governing law differs from preferred jurisdiction ({preferred_jurisdiction})."
    explanation = (
        f"The clause appears to specify a governing law other than {preferred_jurisdiction}. "
        "This may affect dispute resolution and should be reviewed."
    )
    evidence = _short_snippet(text)

    return [
        _make_finding(
            clause_id=clause["id"],
            rule_code="GOV_LAW_MISMATCH",
            severity="medium",
            summary=summary,
            explanation=explanation,
            evidence_text=evidence,
        )
    ]


# --------------------------------------------------------------------
# Orchestrator
# --------------------------------------------------------------------

RULE_FUNCTIONS = [
    rule_termination_notice_period,
    rule_indemnity_clause,
    rule_confidentiality_duration,
    rule_governing_law_mismatch,
]


def run_rules(
    clauses: Sequence[Dict],
    *,
    preferred_jurisdiction: str = "California",
) -> List[Dict]:
    """
    Run all deterministic rules on a list of clauses.
    Returns a flat list of findings.
    """
    all_findings: List[Dict] = []
    for clause in clauses:
        for rule_func in RULE_FUNCTIONS:
            findings = rule_func(
                clause,
                preferred_jurisdiction=preferred_jurisdiction,
            )
            all_findings.extend(findings)
    return all_findings
