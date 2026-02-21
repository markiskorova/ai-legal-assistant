export interface DocumentSummary {
  id: string;
  title: string;
  created_at: string;
}

export interface ReviewRun {
  id: string;
  status: string;
  llm_model: string | null;
  prompt_rev: string | null;
  error: string | null;
  created_at: string;
}

export interface Clause {
  id: string;
  heading: string | null;
  body: string;
}

export interface EvidenceSpan {
  start: number;
  end: number;
}

export interface Finding {
  id: string;
  run_id: string | null;
  clause_id: string | null;
  clause_heading: string | null;
  clause_body: string | null;
  summary: string;
  explanation: string | null;
  severity: "low" | "medium" | "high" | string;
  evidence: string;
  evidence_span: EvidenceSpan | null;
  source: "rule" | "llm" | "unknown" | string;
  rule_code: string | null;
  model: string | null;
  confidence: number | null;
  prompt_rev: string | null;
  created_at: string;
}

export interface ReviewRunResponse {
  document: {
    id: string;
    title: string;
  };
  clauses: Clause[];
  findings: Finding[];
  run: ReviewRun;
}

export interface DocumentFindingsResponse {
  document: {
    id: string;
    title: string;
  };
  run: ReviewRun | null;
  findings: Finding[];
}
