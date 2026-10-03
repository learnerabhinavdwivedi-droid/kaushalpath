import { describe, it, expect, beforeEach } from 'vitest';
import { useAuthStore, useAssessmentStore } from './useStore';

describe('useStore', () => {
  beforeEach(() => {
    // Reset stores
    useAuthStore.setState({ token: null, role: null, studentId: null });
    useAssessmentStore.setState({ assessmentId: null, answers: {}, currentQuestionIndex: 0 });
  });

  it('sets and clears auth', () => {
    const { setAuth, logout } = useAuthStore.getState();

    setAuth('fake-token', 'student', 7);
    expect(useAuthStore.getState().token).toBe('fake-token');
    expect(useAuthStore.getState().role).toBe('student');
    expect(useAuthStore.getState().studentId).toBe(7);

    logout();
    expect(useAuthStore.getState().token).toBeNull();
    expect(useAuthStore.getState().role).toBeNull();
    expect(useAuthStore.getState().studentId).toBeNull();
  });

  it('manages assessment answers and progression', () => {
    const { setAnswer, nextQuestion, prevQuestion } = useAssessmentStore.getState();
    
    setAnswer('q1', 'opt1');
    expect(useAssessmentStore.getState().answers['q1']).toBe('opt1');
    
    expect(useAssessmentStore.getState().currentQuestionIndex).toBe(0);
    nextQuestion();
    expect(useAssessmentStore.getState().currentQuestionIndex).toBe(1);
    prevQuestion();
    expect(useAssessmentStore.getState().currentQuestionIndex).toBe(0);
  });
});
