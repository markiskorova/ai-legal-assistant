from .extractor import extract_clauses
from .rules_engine import run_rules
from .llm.provider import run_llm_analysis

def run_full_review(document):
    # Step 1 — Extract
    clauses = extract_clauses(document.text)

    results = []

    # Step 2 — Rules
    rule_findings = run_rules(document, clauses)
    results.extend(rule_findings)

    # Step 3 — LLM
    llm_findings = run_llm_analysis(document, clauses)
    results.extend(llm_findings)

    return results
