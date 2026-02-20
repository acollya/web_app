export type EmotionLevel = 'muito-bem' | 'bem' | 'neutro' | 'triste' | 'muito-triste';

export interface Emotion {
  id: string;
  label: string;
  level: EmotionLevel;
  icon: string;
}

export interface MoodCheckin {
  id: string;
  userId: string;
  primaryEmotion: EmotionLevel;
  secondaryEmotions?: EmotionLevel[];
  note?: string;
  createdAt: string;
}

export interface MoodSummary {
  last7Days: {
    date: string;
    emotion: EmotionLevel;
  }[];
  insights: string[];
  recommendation?: string;
}