import { requestJson } from "./http";
import type { DocumentFindingsResponse, DocumentSummary } from "../types/api";

export async function uploadDocument(title: string, file: File): Promise<DocumentSummary> {
  const formData = new FormData();
  formData.append("title", title);
  formData.append("file", file);

  return requestJson<DocumentSummary>("/v1/documents/upload", {
    method: "POST",
    body: formData,
  });
}

export async function getDocumentFindings(
  documentId: string,
  runId?: string,
): Promise<DocumentFindingsResponse> {
  const query = runId ? `?run_id=${encodeURIComponent(runId)}` : "";
  return requestJson<DocumentFindingsResponse>(`/v1/documents/${documentId}/findings${query}`);
}
