import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface AuthState {
  token: string | null;
  role: string | null;
  setAuth: (token: string, role: string) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      role: null,
      setAuth: (token, role) => {
        localStorage.setItem('token', token);
        set({ token, role });
      },
      logout: () => {
        localStorage.removeItem('token');
        set({ token: null, role: null });
      },
    }),
    { name: 'auth-storage' }
  )
);

interface ProfileState {
  edu_level: string;
  district: string;
  budget: number;
  duration: number;
  setProfile: (profile: Partial<ProfileState>) => void;
}

export const useProfileStore = create<ProfileState>()(
  persist(
    (set) => ({
      edu_level: '',
      district: '',
      budget: 0,
      duration: 0,
      setProfile: (profile) => set((state) => ({ ...state, ...profile })),
    }),
    { name: 'profile-storage' }
  )
);

interface AssessmentState {
  answers: Record<string, string>;
  currentQuestionIndex: number;
  setAnswer: (questionId: string, answer: string) => void;
  nextQuestion: () => void;
  prevQuestion: () => void;
  resetAssessment: () => void;
}

export const useAssessmentStore = create<AssessmentState>()(
  persist(
    (set) => ({
      answers: {},
      currentQuestionIndex: 0,
      setAnswer: (questionId, answer) => set((state) => ({
        answers: { ...state.answers, [questionId]: answer }
      })),
      nextQuestion: () => set((state) => ({ currentQuestionIndex: state.currentQuestionIndex + 1 })),
      prevQuestion: () => set((state) => ({ currentQuestionIndex: Math.max(0, state.currentQuestionIndex - 1) })),
      resetAssessment: () => set({ answers: {}, currentQuestionIndex: 0 }),
    }),
    { name: 'assessment-storage' }
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
    { name: 'results-storage' }
  )
);
