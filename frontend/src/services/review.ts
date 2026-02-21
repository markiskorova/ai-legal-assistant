import { requestJson } from "./http";
import type { ReviewRunResponse } from "../types/api";

interface RunReviewRequest {
  document_id: string;
}

export async function runReview(documentId: string): Promise<ReviewRunResponse> {
  const payload: RunReviewRequest = { document_id: documentId };
  return requestJson<ReviewRunResponse>("/v1/review/run", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
}
