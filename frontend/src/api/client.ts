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
  type?: 'positive' | 'negative' | 'neutral';
}

export interface RecommendationOut {
  id?: number;
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
  // Phase 15: numeric room id (needed to bind a shared conversation).
  room_id: number;
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

// --- Phase 8: counsellor dashboard, feedback loop, audit --------------------

export interface CohortRow {
  student_id: number;
  district: string;
  edu_level: string;
  language: string;
  status: string;
  has_room: boolean;
  open_escalations: number;
}

export interface CohortFilters {
  district?: string;
  edu_level?: string;
  language?: string;
  status?: string;
}

export interface RecommendationRow {
  occupation_id: number;
  occupation_name: string;
  rank: number;
  score: number;
  reasons: ReasonOut[];
  is_demo: boolean;
}

export interface RoomStatusOut {
  code: string | null;
  members: number;
  votes: number;
  objections: number;
  consensus_reached: boolean;
}

export interface StudentDetail {
  student_id: number;
  district: string;
  state: string;
  edu_level: string;
  language: string;
  budget_band: string;
  assessment: {
    status: string;
    items_answered: number;
    confidence: number;
    riasec: Record<string, number>;
  } | null;
  recommendations: RecommendationRow[];
  overrides: {
    occupation_id: number;
    occupation_name: string;
    note: string;
    counsellor_id: number;
    created_at: string | null;
  }[];
  room: RoomStatusOut | null;
}

export interface CountBucket {
  label: string;
  count: number;
}

export interface AnalyticsResponse {
  riasec: { distribution: CountBucket[]; suppressed_groups: number };
  top_trades: { top_trades: CountBucket[]; suppressed_groups: number };
  dropoff: { started: number; completed: number; dropped: number; dropoff_rate: number };
  rooms: { rooms_created: number; consensus_reached: number };
  avg_items: { average_items: number; n: number };
  district_mismatch: {
    districts: { district: string; n_students: number; top_trade: string; recommendations: number }[];
    suppressed_groups: number;
  };
}

export interface ResistanceResponse {
  total_objections: number;
  by_topic: CountBucket[];
  by_district: CountBucket[];
  by_trade: CountBucket[];
  concern_by_topic: CountBucket[];
  suppressed_groups: number;
}

// --- Phase 16: scheme-administrator resistance dashboard -------------------

export interface DashboardFilters {
  from?: string;
  to?: string;
  state?: string;
  trade?: string;
  lang?: string;
}

export interface DashboardKpis {
  families_counselled: number;
  total_conversations: number;
  pct_high_resistance: number;
  top_concern: string;
  escalation_rate: number;
  sentiment_improved_pct: number;
}

export interface DistrictRow {
  district: string;
  state: string | null;
  lat: number;
  lon: number;
  n: number;
  avg_rs: number | null;
  share_high: number | null;
  top_topics: string[];
  shift: { softened: number; hardened: number; unchanged: number };
  is_suppressed: boolean;
}

export interface ConcernTradeMatrix {
  concerns: string[];
  trades: string[];
  cells: (number | null)[][];
  suppressed_cells: number;
}

export interface ResistanceDashboard {
  filters: Required<DashboardFilters>;
  kpis: DashboardKpis;
  districts: DistrictRow[];
  matrix: ConcernTradeMatrix;
  phrases: Record<string, string[]>;
  trend: { date: string; avg_rs: number; n_conversations: number }[];
  shift: { softened: number; hardened: number; unchanged: number };
  suppressed_groups: number;
  high_threshold: number;
  is_demo: boolean;
}

export interface AuditEntry {
  id: number;
  actor_user_id: number | null;
  action: string;
  entity_type: string;
  entity_id: string | null;
  detail: Record<string, unknown> | null;
  created_at: string | null;
}

export interface FeedbackPayload {
  recommendation_id: number;
  helpful: boolean;
  chosen: boolean;
  topic?: string;
  sentiment?: string;
}

export const getCohort = (filters: CohortFilters = {}) => {
  const qs = new URLSearchParams(
    Object.entries(filters).filter(([, v]) => v) as [string, string][]
  ).toString();
  return apiRequest<CohortRow[]>(`/counsellor/cohort${qs ? `?${qs}` : ''}`);
};

export const getStudentDetail = (studentId: number) =>
  apiRequest<StudentDetail>(`/counsellor/students/${studentId}`);

export const submitOverride = (studentId: number, occupationId: number, note: string) =>
  apiRequest<{ status: string; override_id: number }>('/counsellor/override', {
    method: 'POST',
    body: JSON.stringify({ student_id: studentId, occupation_id: occupationId, note })
  });

export const getAnalytics = () => apiRequest<AnalyticsResponse>('/counsellor/analytics');

export const getResistance = () => apiRequest<ResistanceResponse>('/counsellor/resistance');

export const getResistanceDashboard = (filters: DashboardFilters = {}) => {
  const qs = new URLSearchParams(
    Object.entries(filters).filter(([, v]) => v) as [string, string][]
  ).toString();
  return apiRequest<ResistanceDashboard>(`/admin/resistance/dashboard${qs ? `?${qs}` : ''}`);
};

// CSV export reuses the unchanged Phase 13 endpoint, but must send the Bearer
// token, so we fetch to a Blob and hand back an object URL for download.
export const exportResistanceCsv = async (): Promise<string> => {
  const token = localStorage.getItem('token');
  const res = await fetch(`${API_BASE}/admin/resistance/export.csv`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!res.ok) throw new Error('Export failed');
  const blob = await res.blob();
  return URL.createObjectURL(blob);
};

export const getAuditLog = () => apiRequest<AuditEntry[]>('/counsellor/audit');

export const sendFeedback = (payload: FeedbackPayload) =>
  apiRequest<{ id: number } & FeedbackPayload>('/feedback', {
    method: 'POST',
    body: JSON.stringify(payload)
  });

export const getModelVersion = () =>
  apiRequest<{ model_version: string }>('/meta/model-version');

// --- Phase 15: shared family chat + guest parent join -----------------------

/** One grounded fact as stored on an assistant turn (never LLM-invented). */
export interface GroundedFact {
  key: string;
  label: string;
  value: number | string;
  unit?: string | null;
  source?: string | null;
  source_year?: number | null;
  is_demo?: boolean;
}

export interface TurnOut {
  id: number;
  speaker: string; // learner | parent | counsellor | assistant
  text: string;
  lang: string;
  intent: string | null;
  topic: string | null;
  sentiment: string | null;
  intensity: number;
  facts_json: GroundedFact[] | null;
  fallback_used: boolean;
  created_at: string;
}

export interface ConversationOut {
  id: number;
  student_id: number;
  room_id: number | null;
  lang: string;
  status: string; // active | escalated | closed
  created_at: string;
  turns: TurnOut[];
}

export interface TurnResponse {
  reply: string;
  lang: string;
  intent: string;
  topic: string;
  facts: GroundedFact[];
  followups: string[];
  escalation_suggested: boolean;
  fallback_used: boolean;
}

export interface EscalationAck {
  id: number;
  status: string; // open | assigned | contacted | resolved | unreachable
  assigned_counsellor_id: number | null;
  in_pool: boolean;
  case_pack?: Record<string, unknown> | null;
}

export interface EscalationPayload {
  reason: string;
  occupation_id?: number | null;
  contact_phone?: string | null;
  preferred_language?: string | null;
  preferred_slot?: string | null;
  channel?: string;
  priority?: string;
}

export interface GuestToken {
  access_token: string;
  token_type: string;
  room_code: string;
  room_id: number;
  student_id: number;
  name: string;
}

/** Parent joins a room with just code + first name (no email/password). */
export const guestJoin = (room_code: string, name: string, phone?: string, lang = 'hi') =>
  apiRequest<GuestToken>('/auth/guest', {
    method: 'POST',
    body: JSON.stringify({ room_code, name, phone: phone || null, lang })
  });

export const createConversation = (student_id: number, room_id?: number | null, lang = 'hi') =>
  apiRequest<ConversationOut>('/conversations', {
    method: 'POST',
    body: JSON.stringify({ student_id, room_id: room_id ?? null, lang })
  });

export const getConversation = (id: number) =>
  apiRequest<ConversationOut>(`/conversations/${id}`);

export const sendTurn = (
  id: number,
  payload: { speaker: string; text: string; occupation_id?: number | null; lang?: string | null }
) =>
  apiRequest<TurnResponse>(`/conversations/${id}/turns`, {
    method: 'POST',
    body: JSON.stringify(payload)
  });

export const escalateConversation = (id: number, payload: EscalationPayload) =>
  apiRequest<EscalationAck>(`/conversations/${id}/escalate`, {
    method: 'POST',
    body: JSON.stringify(payload)
  });

/** Live status of the family's hand-off (lifecycle fields only, poll-safe). */
export const getConversationEscalation = (id: number) =>
  apiRequest<EscalationAck>(`/conversations/${id}/escalation`);
