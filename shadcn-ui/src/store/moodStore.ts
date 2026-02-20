import { create } from 'zustand';
import { EmotionLevel } from '@/types/mood';

interface MoodState {
  todayMood: EmotionLevel | null;
  setTodayMood: (mood: EmotionLevel) => void;
  clearTodayMood: () => void;
}

export const useMoodStore = create<MoodState>((set) => ({
  todayMood: null,

  setTodayMood: (mood) => {
    localStorage.setItem('acollya_today_mood', mood);
    set({ todayMood: mood });
  },

  clearTodayMood: () => {
    localStorage.removeItem('acollya_today_mood');
    set({ todayMood: null });
  },
}));