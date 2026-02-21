import { useMemo, useState } from "react";

import { getDocumentFindings, uploadDocument } from "./services/documents";
import { ApiError } from "./services/http";
import { runReview } from "./services/review";
import type { DocumentSummary, Finding, ReviewRun } from "./types/api";

type EvidenceExpandedState = Record<string, boolean>;

function formatTimestamp(value: string | null | undefined): string {
  if (!value) {
    return "-";
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString();
}

function severityClass(severity: string): string {
  if (severity === "high") {
    return "severity severity-high";
  }
  if (severity === "medium") {
    return "severity severity-medium";
  }
  return "severity severity-low";
}

export default function App() {
  const [title, setTitle] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [document, setDocument] = useState<DocumentSummary | null>(null);
  const [run, setRun] = useState<ReviewRun | null>(null);
  const [findings, setFindings] = useState<Finding[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [isRunning, setIsRunning] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedEvidence, setExpandedEvidence] = useState<EvidenceExpandedState>({});

  const stats = useMemo(() => {
    const high = findings.filter((f) => f.severity === "high").length;
    const medium = findings.filter((f) => f.severity === "medium").length;
    const low = findings.filter((f) => f.severity === "low").length;
    return { high, medium, low };
  }, [findings]);

  async function onUpload(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!title.trim() || !file) {
      setError("Provide both title and file before uploading.");
      return;
    }

    setError(null);
    setIsUploading(true);
    try {
      const uploaded = await uploadDocument(title.trim(), file);
      setDocument(uploaded);
      setRun(null);
      setFindings([]);
      setExpandedEvidence({});
    } catch (err) {
      const message = err instanceof ApiError ? err.message : "Failed to upload document.";
      setError(message);
    } finally {
      setIsUploading(false);
    }
  }

  async function onRunAnalysis() {
    if (!document) {
      setError("Upload a document before running analysis.");
      return;
    }

    setError(null);
    setIsRunning(true);
    try {
      const result = await runReview(document.id);
      setRun(result.run);
      setFindings(result.findings);
      setExpandedEvidence({});
    } catch (err) {
      const message = err instanceof ApiError ? err.message : "Failed to run analysis.";
      setError(message);
    } finally {
      setIsRunning(false);
    }
  }

  async function onRefreshFindings() {
    if (!document) {
      return;
    }

    setError(null);
    setIsRefreshing(true);
    try {
      const result = await getDocumentFindings(document.id, run?.id);
      setRun(result.run);
      setFindings(result.findings);
    } catch (err) {
      const message = err instanceof ApiError ? err.message : "Failed to fetch findings.";
      setError(message);
    } finally {
      setIsRefreshing(false);
    }
  }

  function toggleEvidence(findingId: string) {
    setExpandedEvidence((prev) => ({
      ...prev,
      [findingId]: !prev[findingId],
    }));
  }

  return (
    <main className="page-shell">
      <section className="hero">
        <p className="eyebrow">MVP Review Console</p>
        <h1>AI Legal Assistant</h1>
        <p className="subtitle">Upload a document, run review, inspect findings and evidence spans.</p>
      </section>

      <section className="panel">
        <h2>1. Upload Document</h2>
        <form onSubmit={onUpload} className="form-grid">
          <label>
            Title
            <input
              type="text"
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              placeholder="NDA - ACME Vendor Agreement"
              required
            />
          </label>
          <label>
            File
            <input
              type="file"
              accept=".txt,.pdf"
              onChange={(event) => setFile(event.target.files?.[0] ?? null)}
              required
            />
          </label>
          <button type="submit" className="btn-primary" disabled={isUploading}>
            {isUploading ? "Uploading..." : "Upload"}
          </button>
        </form>

        <div className="metadata">
          <div>
            <strong>Document ID:</strong> {document?.id ?? "-"}
          </div>
          <div>
            <strong>Title:</strong> {document?.title ?? "-"}
          </div>
          <div>
            <strong>Uploaded:</strong> {formatTimestamp(document?.created_at)}
          </div>
        </div>
      </section>

      <section className="panel">
        <h2>2. Run Analysis</h2>
        <div className="action-row">
          <button type="button" className="btn-primary" disabled={!document || isRunning} onClick={onRunAnalysis}>
            {isRunning ? "Running..." : "Run Analysis"}
          </button>
          <button
            type="button"
            className="btn-secondary"
            disabled={!document || isRefreshing}
            onClick={onRefreshFindings}
          >
            {isRefreshing ? "Refreshing..." : "Refresh Findings"}
          </button>
        </div>

        <div className="metadata">
          <div>
            <strong>Run ID:</strong> {run?.id ?? "-"}
          </div>
          <div>
            <strong>Status:</strong> {run?.status ?? "-"}
          </div>
          <div>
            <strong>Model:</strong> {run?.llm_model ?? "-"}
          </div>
          <div>
            <strong>Prompt Rev:</strong> {run?.prompt_rev ?? "-"}
          </div>
        </div>

        {error && <p className="error-banner">{error}</p>}
      </section>

      <section className="panel">
        <h2>3. Findings</h2>
        <div className="finding-stats">
          <span className="chip chip-high">High: {stats.high}</span>
          <span className="chip chip-medium">Medium: {stats.medium}</span>
          <span className="chip chip-low">Low: {stats.low}</span>
          <span className="chip chip-total">Total: {findings.length}</span>
        </div>

        {findings.length === 0 ? (
          <p className="empty-state">No findings yet. Upload and run analysis to populate results.</p>
        ) : (
          <div className="finding-list">
            {findings.map((finding) => {
              const isExpanded = !!expandedEvidence[finding.id];
              return (
                <article key={finding.id} className="finding-card">
                  <header className="finding-header">
                    <h3>{finding.summary || "Untitled finding"}</h3>
                    <span className={severityClass(finding.severity)}>{finding.severity}</span>
                  </header>

                  <p className="finding-meta">
                    <strong>Source:</strong> {finding.source} | <strong>Clause:</strong>{" "}
                    {finding.clause_heading || finding.clause_id || "-"}
                  </p>

                  {finding.explanation && <p className="finding-explanation">{finding.explanation}</p>}

                  <button
                    type="button"
                    className="btn-link"
                    onClick={() => toggleEvidence(finding.id)}
                  >
                    {isExpanded ? "Hide Evidence" : "Show Evidence"}
                  </button>

                  {isExpanded && (
                    <div className="evidence-box">
                      <p>{finding.evidence}</p>
                      <p className="evidence-meta">
                        Span:{" "}
                        {finding.evidence_span
                          ? `${finding.evidence_span.start}-${finding.evidence_span.end}`
                          : "-"}
                      </p>
                    </div>
                  )}
                </article>
              );
            })}
          </div>
        )}
      </section>
    </main>
  );
}
