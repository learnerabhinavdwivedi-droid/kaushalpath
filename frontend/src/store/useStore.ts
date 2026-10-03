import { create } from 'zustand';
import { createJSONStorage, persist } from 'zustand/middleware';

// jsdom / SSR may expose no global localStorage; keep persistence a safe no-op
// there instead of throwing on the first setState.
const safeStorage = {
  getItem: (name: string) =>
    typeof localStorage !== 'undefined' ? localStorage.getItem(name) : null,
  setItem: (name: string, value: string) => {
    if (typeof localStorage !== 'undefined') localStorage.setItem(name, value);
  },
  removeItem: (name: string) => {
    if (typeof localStorage !== 'undefined') localStorage.removeItem(name);
  },
};
const storage = createJSONStorage(() => safeStorage);

interface AuthState {
  token: string | null;
  role: string | null;
  studentId: number | null;
  setAuth: (token: string, role: string, studentId: number | null) => void;
  setStudentId: (studentId: number | null) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      role: null,
      studentId: null,
      setAuth: (token, role, studentId) => {
        if (typeof localStorage !== 'undefined') localStorage.setItem('token', token);
        set({ token, role, studentId });
      },
      setStudentId: (studentId) => set({ studentId }),
      logout: () => {
        if (typeof localStorage !== 'undefined') localStorage.removeItem('token');
        set({ token: null, role: null, studentId: null });
      },
    }),
    { name: 'auth-storage', storage }
  )
);

interface ProfileState {
  edu_level: string;
  district: string;
  state: string;
  budget: number;
  duration: number;
  income_band: string;
  setProfile: (profile: Partial<ProfileState>) => void;
}

export const useProfileStore = create<ProfileState>()(
  persist(
    (set) => ({
      edu_level: '',
      district: '',
      state: 'Maharashtra',
      budget: 0,
      duration: 0,
      income_band: '',
      setProfile: (profile) => set((state) => ({ ...state, ...profile })),
    }),
    { name: 'profile-storage', storage }
  )
);

interface AssessmentState {
  assessmentId: number | null;
  answers: Record<string, string>;
  currentQuestionIndex: number;
  setAssessmentId: (id: number | null) => void;
  setAnswer: (questionId: string, answer: string) => void;
  nextQuestion: () => void;
  prevQuestion: () => void;
  resetAssessment: () => void;
}

export const useAssessmentStore = create<AssessmentState>()(
  persist(
    (set) => ({
      assessmentId: null,
      answers: {},
      currentQuestionIndex: 0,
      setAssessmentId: (assessmentId) => set({ assessmentId }),
      setAnswer: (questionId, answer) => set((state) => ({
        answers: { ...state.answers, [questionId]: answer }
      })),
      nextQuestion: () => set((state) => ({ currentQuestionIndex: state.currentQuestionIndex + 1 })),
      prevQuestion: () => set((state) => ({ currentQuestionIndex: Math.max(0, state.currentQuestionIndex - 1) })),
      resetAssessment: () => set({ assessmentId: null, answers: {}, currentQuestionIndex: 0 }),
    }),
    { name: 'assessment-storage', storage }
  )
);

interface ResultsState {
  recommendations: any[];
  setRecommendations: (results: any[]) => void;
}

export const useResultsStore = create<ResultsState>()(
  persist(
    (set) => ({
      recommendations: [],
      setRecommendations: (recommendations) => set({ recommendations }),
    }),
    { name: 'results-storage', storage }
  )
);

interface RoomState {
  // Active family decision room code, kept so the room pages survive a reload.
  code: string | null;
  setCode: (code: string | null) => void;
  clear: () => void;
}

export const useRoomStore = create<RoomState>()(
  persist(
    (set) => ({
      code: null,
      setCode: (code) => set({ code }),
      clear: () => set({ code: null }),
    }),
    { name: 'room-storage', storage }
  )
);
