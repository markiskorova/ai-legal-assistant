export class ApiError extends Error {
  readonly status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "";

function buildUrl(path: string): string {
  if (!API_BASE_URL) {
    return path;
  }

  if (path.startsWith("/")) {
    return `${API_BASE_URL}${path}`;
  }

  return `${API_BASE_URL}/${path}`;
}

export async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(buildUrl(path), init);
  const contentType = response.headers.get("content-type") || "";
  const isJson = contentType.includes("application/json");

  if (!response.ok) {
    let detail = `Request failed with status ${response.status}`;
    if (isJson) {
      const data = (await response.json()) as { detail?: string };
      if (typeof data.detail === "string" && data.detail.length > 0) {
        detail = data.detail;
      }
    }
    throw new ApiError(detail, response.status);
  }

  if (!isJson) {
    throw new ApiError("Expected JSON response.", response.status);
  }

  return (await response.json()) as T;
}
