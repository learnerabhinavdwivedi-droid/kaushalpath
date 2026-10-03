export const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000';

async function fetchWithRetry(url: string, options: RequestInit = {}, retries = 3, backoff = 300): Promise<Response> {
  try {
    const response = await fetch(url, options);
    if (!response.ok && response.status >= 500 && retries > 0) {
      await new Promise(r => setTimeout(r, backoff));
      return fetchWithRetry(url, options, retries - 1, backoff * 2);
    }
    return response;
  } catch (error) {
    if (retries > 0) {
      await new Promise(r => setTimeout(r, backoff));
      return fetchWithRetry(url, options, retries - 1, backoff * 2);
    }
    throw error; // likely offline or network failure
  }
}

export async function apiRequest<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const token = localStorage.getItem('token');
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string> || {})
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  if (!navigator.onLine) {
    throw new Error('You are currently offline. Please check your connection.');
  }

  const response = await fetchWithRetry(`${API_BASE}${endpoint}`, {
    ...options,
    headers
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || 'API Request Failed');
  }

  return response.json();
}

// --- Typed contracts mirroring the FastAPI routes --------------------------

export interface MeOut {
  user_id: number;
  email: string;
  role: string;
  lang: string;
  student_id: number | null;
}

export interface ConstraintPayload {
  age?: number | null;
  edu_level: string;
  district: string;
  state: string;
  budget_band: string;
  income_band?: string | null;
  relocate_ok: boolean;
  language: string;
  max_duration_months?: number | null;
}

export interface AssessmentItem {
  id: string;
  section: 'interest' | 'aptitude';
  text: string;
  dimension?: string;
  scale?: number[];
  options?: string[];
}

export interface NextItemOut {
  assessment_id: number;
  status: string;
  done: boolean;
  items_answered: number;
  confidence: number;
  item?: AssessmentItem | null;
}

export interface ReasonOut {
  code: string;
  description: string;
  evidence?: number | null;
  source?: string;
}

export interface RecommendationOut {
  rank: number;
  occupation_id: number;
  occupation_name: string;
  course_id: number | null;
  course_name: string | null;
  score: number;
  reasons: ReasonOut[];
  is_demo: boolean;
}

export const getMe = () => apiRequest<MeOut>('/auth/me');

export const saveConstraints = (studentId: number, payload: ConstraintPayload) =>
  apiRequest(`/assessment/student?student_id=${studentId}`, {
    method: 'POST',
    body: JSON.stringify(payload)
  });

export const startSession = (studentId: number) =>
  apiRequest<NextItemOut>(`/assessment/session?student_id=${studentId}`, { method: 'POST' });

export const resumeSession = (assessmentId: number) =>
  apiRequest<NextItemOut>(`/assessment/next?assessment_id=${assessmentId}`);

export const submitAnswer = (assessmentId: number, answer: unknown, itemId?: string) =>
  apiRequest<NextItemOut>('/assessment/answer', {
    method: 'POST',
    body: JSON.stringify({ assessment_id: assessmentId, answer, item_id: itemId })
  });

export const getRecommendations = (studentId: number, topK = 3) =>
  apiRequest<{ recommendations: RecommendationOut[]; model_version?: string }>('/recommend', {
    method: 'POST',
    body: JSON.stringify({ student_id: studentId, top_k: topK })
  });

// --- Phase 7: Family Decision Room contracts ------------------------------

export interface RoomMember {
  user_id: number;
  role: string;
}

export interface MemberWeights {
  user_id: number;
  cost: number;
  duration: number;
  salary: number;
  local_jobs: number;
  distance: number;
}

export interface RoomVote {
  user_id: number;
  occupation_id: number;
  score: number;
}

export interface ObjectionTag {
  id: number;
  raised_by_user_id: number;
  occupation_id: number | null;
  topic: string;
  sentiment: string;
}

export interface RoomSnapshot {
  code: string;
  student_id: number;
  members: RoomMember[];
  weights: MemberWeights[];
  votes: RoomVote[];
  objections: ObjectionTag[];
}

export interface WeightsInput {
  cost: number;
  duration: number;
  salary: number;
  local_jobs: number;
  distance: number;
}

export interface CompareCriteria {
  cost: number;
  duration: number;
  salary: number;
  local_jobs: number;
  distance: number;
}

export interface CompareResultItem {
  occupation_id: number;
  occupation_name: string;
  criteria: CompareCriteria;
  member_totals: Record<string, number>;
  family_score: number;
  spread: number;
}

export interface Disagreement {
  occupation_id: number | null;
  criterion: string | null;
  detail: string;
}

export interface CompareResponse {
  results: CompareResultItem[];
  disagreement: Disagreement;
}

export interface ConsensusRanking {
  occupation_id: number;
  avg_score: number;
}

export interface ConsensusResult {
  ranking: ConsensusRanking[];
  agreement_index: number;
  next_step: string;
}

export interface RoadmapStep {
  step: number;
  type: string;
  detail: string;
}

export interface RoadmapResult {
  occupation_id: number;
  occupation_name: string;
  district: string | null;
  is_demo: boolean;
  source: string | null;
  expected: string | null;
  steps: RoadmapStep[];
}

export type ObjectionTopic = 'income' | 'security' | 'social' | 'safety' | 'other';
export type ObjectionSentiment = 'concern' | 'neutral' | 'positive';

export const createRoom = () =>
  apiRequest<{ code: string; student_id: number }>('/rooms', { method: 'POST' });

export const joinRoom = (code: string) =>
  apiRequest<{ status: string; room_code: string }>(`/rooms/${code}/join`, { method: 'POST' });

export const getRoom = (code: string) => apiRequest<RoomSnapshot>(`/rooms/${code}`);

export const updateWeights = (code: string, weights: WeightsInput) =>
  apiRequest<{ status: string }>(`/rooms/${code}/weights`, {
    method: 'PUT',
    body: JSON.stringify(weights)
  });

export const castVote = (code: string, occupationId: number, score: number) =>
  apiRequest<{ status: string }>(`/rooms/${code}/vote`, {
    method: 'POST',
    body: JSON.stringify({ occupation_id: occupationId, score })
  });

export const getConsensus = (code: string) =>
  apiRequest<ConsensusResult>(`/rooms/${code}/consensus`);

export const compareOccupations = (code: string, occupationIds: number[]) =>
  apiRequest<CompareResponse>(`/rooms/${code}/compare`, {
    method: 'POST',
    body: JSON.stringify({ occupation_ids: occupationIds })
  });

export const recordObjection = (
  code: string,
  payload: {
    topic: ObjectionTopic;
    sentiment: ObjectionSentiment;
    occupation_id?: number | null;
    note?: string | null;
  }
) =>
  apiRequest<ObjectionTag>(`/rooms/${code}/objection`, {
    method: 'POST',
    body: JSON.stringify(payload)
  });

export const escalateRoom = (code: string, reason: string, occupationId?: number | null) =>
  apiRequest<{ id: number; room_code: string; status: string; reason: string }>(
    `/rooms/${code}/escalate`,
    { method: 'POST', body: JSON.stringify({ reason, occupation_id: occupationId ?? null }) }
  );

export const getRoadmap = (occupationId: number, district?: string | null) =>
  apiRequest<RoadmapResult>(
    `/roadmap/${occupationId}${district ? `?district=${encodeURIComponent(district)}` : ''}`
  );
