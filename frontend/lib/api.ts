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
  SearchRequest,
  SearchResponse,
  TeachStartResponse,
  TeachRespondResponse,
  TeachSessionResponse,
  ReflectionResponse,
  ReflectionStatusResponse,
  ReflectionListItem,
  URLCaptureRequest,
  TagItem,
  QuestionListResponse,
  QuestionDetail,
  QuestionStatsSummary,
  TopicCoverageResponse,
  WeakCategoriesResponse,
  StreakInfoResponse,
  GymSessionRequest,
  GymSessionResponse,
  GymStatsResponse,
} from "@/types/api";
import type {
  PushSubscriptionData,
  NotificationSettings,
  NotificationSettingsResponse,
} from "@/types/notification";
import type {
  LociCreateRequest,
  LociCreateResponse,
  LociRecallRequest,
  LociRecallResponse,
  LociListItem,
} from "@/types/loci";
import type {
  GraphDataResponse,
  NodeDetailResponse,
} from "@/types/graph";
import type {
  AnalyticsResponse,
  RetentionCurveResponse,
  WeakAreasResponse,
  ActivityResponse,
} from "@/types/analytics";

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
      // Try to get error message from response
      const contentType = res.headers.get("content-type");
      let errorMessage = `Request failed with status ${res.status}`;
      
      if (contentType?.includes("application/json")) {
        try {
          const errorData = await res.json();
          errorMessage = errorData.detail || errorData.message || errorMessage;
        } catch {
          // If JSON parsing fails, use status text
          errorMessage = res.statusText || errorMessage;
        }
      } else {
        // Non-JSON response (HTML error page, etc.)
        errorMessage = `Server error (${res.status}). Please check if the backend is running correctly.`;
      }
      
      throw new ApiError(res.status, errorMessage);
    }
    
    // Check if response is JSON before parsing
    const contentType = res.headers.get("content-type");
    if (!contentType?.includes("application/json")) {
      throw new Error("Expected JSON response but got " + contentType);
    }
    
    return res.json();
  } catch (err) {
    if (err instanceof ApiError) throw err;
    if (err instanceof Error) throw err;
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

export async function deleteCapture(id: string): Promise<void> {
  await request<{ ok: boolean }>(`/api/captures/${encodeURIComponent(id)}`, {
    method: "DELETE",
  });
}

export async function getAllTags(): Promise<TagItem[]> {
  return request<TagItem[]>("/api/captures/tags");
}

export async function updateCaptureTags(captureId: string, tags: string[]): Promise<{ tags: string[] }> {
  return request<{ tags: string[] }>(`/api/captures/${encodeURIComponent(captureId)}/tags`, {
    method: "PUT",
    body: JSON.stringify({ tags }),
  });
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

export async function searchKnowledge(data: SearchRequest): Promise<SearchResponse> {
  return request<SearchResponse>("/api/knowledge/search", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

// Phase 3: Teach Me Mode
export async function startTeachSession(topic: string): Promise<TeachStartResponse> {
  return request<TeachStartResponse>("/api/teach/start", {
    method: "POST",
    body: JSON.stringify({ topic }),
  });
}

export async function respondToTeach(sessionId: string, answer: string): Promise<TeachRespondResponse> {
  return request<TeachRespondResponse>("/api/teach/respond", {
    method: "POST",
    body: JSON.stringify({ session_id: sessionId, answer }),
  });
}

export async function getTeachSession(sessionId: string): Promise<TeachSessionResponse> {
  return request<TeachSessionResponse>(`/api/teach/${encodeURIComponent(sessionId)}`);
}

// Phase 3: Evening Reflection
export async function submitReflection(content: string): Promise<ReflectionResponse> {
  return request<ReflectionResponse>("/api/reflections/", {
    method: "POST",
    body: JSON.stringify({ content }),
  });
}

export async function getReflectionStatus(): Promise<ReflectionStatusResponse> {
  return request<ReflectionStatusResponse>("/api/reflections/status");
}

export async function listReflections(limit: number = 20, offset: number = 0): Promise<ReflectionListItem[]> {
  return request<ReflectionListItem[]>(`/api/reflections/?limit=${limit}&offset=${offset}`);
}

// Phase 3: URL Ingestion
export async function captureURL(data: URLCaptureRequest): Promise<CaptureResponse> {
  return request<CaptureResponse>("/api/captures/url", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

// Phase 4: Voice Agent
export interface VoiceStatusResponse {
  available: boolean;
  provider: string | null;
  modes: string[];
}

export async function getVoiceStatus(): Promise<VoiceStatusResponse> {
  return request<VoiceStatusResponse>("/api/voice/status");
}

// Phase 5: Push Notifications
export async function subscribeToNotifications(subscription: PushSubscriptionData): Promise<void> {
  await request("/api/notifications/subscribe", {
    method: "POST",
    body: JSON.stringify(subscription),
  });
}

export async function unsubscribeFromNotifications(subscription: PushSubscriptionData): Promise<void> {
  await request("/api/notifications/subscribe", {
    method: "DELETE",
    body: JSON.stringify(subscription),
  });
}

export async function getNotificationSettings(): Promise<NotificationSettingsResponse> {
  return request<NotificationSettingsResponse>("/api/notifications/settings");
}

export async function updateNotificationSettings(settings: NotificationSettings): Promise<void> {
  await request("/api/notifications/settings", {
    method: "PUT",
    body: JSON.stringify(settings),
  });
}

export async function sendTestNotification(): Promise<void> {
  await request("/api/notifications/test", {
    method: "POST",
    body: JSON.stringify({}),
  });
}

// Loci (Memory Palace) API
export async function createLociSession(data: LociCreateRequest): Promise<LociCreateResponse> {
  return request<LociCreateResponse>("/api/loci/create", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function getLociSession(sessionId: string): Promise<LociCreateResponse> {
  return request<LociCreateResponse>(`/api/loci/${encodeURIComponent(sessionId)}`);
}

export async function submitLociRecall(
  sessionId: string,
  data: LociRecallRequest,
): Promise<LociRecallResponse> {
  return request<LociRecallResponse>(`/api/loci/${encodeURIComponent(sessionId)}/recall`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function listLociSessions(): Promise<LociListItem[]> {
  return request<LociListItem[]>("/api/loci/");
}

// Knowledge Graph API
export async function getGraphData(
  minSimilarity: number = 0.7,
  limit: number = 200,
): Promise<GraphDataResponse> {
  return request<GraphDataResponse>(
    `/api/graph/data?min_similarity=${minSimilarity}&limit=${limit}`,
  );
}

export async function getNodeDetail(pointId: string): Promise<NodeDetailResponse> {
  return request<NodeDetailResponse>(`/api/graph/node/${encodeURIComponent(pointId)}`);
}

// Analytics API
export async function getAnalytics(): Promise<AnalyticsResponse> {
  return request<AnalyticsResponse>("/api/stats/analytics");
}

export async function getRetentionCurve(weeks: number = 12): Promise<RetentionCurveResponse> {
  return request<RetentionCurveResponse>(`/api/stats/analytics/retention?weeks=${weeks}`);
}

export async function getWeakAreas(limit: number = 10): Promise<WeakAreasResponse> {
  return request<WeakAreasResponse>(`/api/stats/analytics/weak-areas?limit=${limit}`);
}

export async function getActivity(days: number = 90): Promise<ActivityResponse> {
  return request<ActivityResponse>(`/api/stats/analytics/activity?days=${days}`);
}

// Question Bank
export async function listQuestions(params: {
  limit?: number; offset?: number; search?: string;
  question_type?: string; state?: number; sort?: string;
  order?: string; capture_id?: string; tag?: string;
}): Promise<QuestionListResponse> {
  const qs = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== '') qs.set(k, String(v));
  });
  return request<QuestionListResponse>(`/api/questions?${qs.toString()}`);
}

export async function getQuestionDetail(id: string): Promise<QuestionDetail> {
  return request<QuestionDetail>(`/api/questions/${encodeURIComponent(id)}`);
}

export async function updateQuestion(id: string, data: { question_text?: string; answer_text?: string; mnemonic_hint?: string; question_type?: string }): Promise<QuestionDetail> {
  return request<QuestionDetail>(`/api/questions/${encodeURIComponent(id)}`, { method: "PATCH", body: JSON.stringify(data) });
}

export async function deleteQuestion(id: string): Promise<void> {
  await request(`/api/questions/${encodeURIComponent(id)}`, { method: "DELETE" });
}

export async function bulkDeleteQuestions(ids: string[]): Promise<{ deleted_count: number }> {
  return request(`/api/questions/bulk-delete`, { method: "POST", body: JSON.stringify({ question_ids: ids }) });
}

export async function rescheduleQuestion(id: string, action: string, days?: number): Promise<void> {
  await request(`/api/questions/${encodeURIComponent(id)}/reschedule`, { method: "POST", body: JSON.stringify({ action, days }) });
}

export async function getQuestionStats(): Promise<QuestionStatsSummary> {
  return request<QuestionStatsSummary>(`/api/questions/stats/summary`);
}

// Stats APIs
export async function getTopicCoverage() {
  return request<TopicCoverageResponse>('/api/stats/topic-coverage');
}

export async function getWeakCategories() {
  return request<WeakCategoriesResponse>('/api/stats/weak-categories');
}

export async function getStreakInfo() {
  return request<StreakInfoResponse>('/api/stats/streak-info');
}

// Focus session
export async function startFocusSession(categories: string[], limit = 10) {
  return request<DueQuestionsResponse>('/api/reviews/focus-session', {
    method: 'POST',
    body: JSON.stringify({ categories, limit }),
  });
}

// Memory Gym
export async function recordGymSession(data: GymSessionRequest): Promise<GymSessionResponse> {
  return request<GymSessionResponse>('/api/gym/', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function getGymStats(): Promise<GymStatsResponse> {
  return request<GymStatsResponse>('/api/gym/stats');
}
