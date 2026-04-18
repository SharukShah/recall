import type {
  DashboardStats,
  CaptureListItem,
  CaptureDetail,
  CaptureRequest,
  CaptureResponse,
  DueQuestionsResponse,
  EvaluateRequest,
  EvaluateResponse,
  RateRequest,
  RateResponse,
} from "@/types/api";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(
  path: string,
  options?: RequestInit,
): Promise<T> {
  const url = `${API_BASE}${path}`;
  try {
    const res = await fetch(url, {
      headers: {
        "Content-Type": "application/json",
        ...options?.headers,
      },
      ...options,
    });
    if (!res.ok) {
      const body = await res.text().catch(() => "");
      throw new ApiError(res.status, body || `Request failed with status ${res.status}`);
    }
    return res.json();
  } catch (err) {
    if (err instanceof ApiError) throw err;
    throw new Error("Failed to connect to server. Check your connection.");
  }
}

export async function fetchDashboardStats(): Promise<DashboardStats> {
  return request<DashboardStats>("/api/stats/dashboard");
}

export async function createCapture(data: CaptureRequest): Promise<CaptureResponse> {
  return request<CaptureResponse>("/api/captures/", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function listCaptures(
  limit: number = 20,
  offset: number = 0,
): Promise<CaptureListItem[]> {
  return request<CaptureListItem[]>(
    `/api/captures/?limit=${limit}&offset=${offset}`,
  );
}

export async function getCaptureDetail(id: string): Promise<CaptureDetail> {
  return request<CaptureDetail>(`/api/captures/${encodeURIComponent(id)}`);
}

export async function getDueQuestions(
  limit: number = 20,
): Promise<DueQuestionsResponse> {
  return request<DueQuestionsResponse>(`/api/reviews/due?limit=${limit}`);
}

export async function evaluateAnswer(
  data: EvaluateRequest,
): Promise<EvaluateResponse> {
  return request<EvaluateResponse>("/api/reviews/evaluate", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function rateQuestion(data: RateRequest): Promise<RateResponse> {
  return request<RateResponse>("/api/reviews/rate", {
    method: "POST",
    body: JSON.stringify(data),
  });
}
