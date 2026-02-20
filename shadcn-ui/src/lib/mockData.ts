import { User } from '@/types/user';
import { MoodCheckin, MoodSummary } from '@/types/mood';
import { JournalEntry } from '@/types/journal';
import { Program, ProgramProgress } from '@/types/program';
import { ChatMessage, ChatSession } from '@/types/chat';

export const mockUser: User = {
  id: '1',
  name: 'Maria Silva',
  email: 'maria@example.com',
  whatsapp: '+55 11 98765-4321',
  registrationDate: '2024-01-15',
  planCode: 0,
  createdAt: '2024-01-15T10:00:00Z',
  termsAccepted: false,
  termsAcceptedDate: undefined,
  preferences: {
    notifications: true,
    emailUpdates: true,
  },
};

export const mockMoodCheckins: MoodCheckin[] = [
  {
    id: '1',
    userId: '1',
    mood: 'good',
    intensity: 4,
    notes: 'Dia produtivo no trabalho',
    createdAt: new Date(Date.now() - 86400000).toISOString(),
  },
  {
    id: '2',
    userId: '1',
    mood: 'neutral',
    intensity: 3,
    notes: 'Dia normal',
    createdAt: new Date(Date.now() - 172800000).toISOString(),
  },
];

export const mockMoodSummary: MoodSummary = {
  averageMood: 3.5,
  totalCheckins: 15,
  streak: 7,
  moodDistribution: {
    great: 3,
    good: 5,
    neutral: 4,
    bad: 2,
    terrible: 1,
  },
};

export const mockJournalEntries: JournalEntry[] = [
  {
    id: '1',
    userId: '1',
    content: 'Hoje foi um dia desafiador, mas consegui superar...',
    createdAt: new Date(Date.now() - 86400000).toISOString(),
  },
  {
    id: '2',
    userId: '1',
    content: 'Estou me sentindo mais confiante a cada dia...',
    createdAt: new Date(Date.now() - 172800000).toISOString(),
  },
];

export const mockPrograms: Program[] = [
  {
    id: '1',
    title: 'Mindfulness para Iniciantes',
    description: 'Aprenda técnicas de atenção plena para reduzir o estresse',
    category: 'mindfulness',
    duration: 7,
    difficulty: 'beginner',
    imageUrl: '/images/photo1764818399.jpg',
    isPremium: false,
  },
  {
    id: '2',
    title: 'Gestão de Ansiedade',
    description: 'Ferramentas práticas para lidar com a ansiedade do dia a dia',
    category: 'anxiety',
    duration: 14,
    difficulty: 'intermediate',
    imageUrl: '/images/photo1764818400.jpg',
    isPremium: true,
  },
];

export const mockProgramProgress: ProgramProgress = {
  id: '1',
  userId: '1',
  programId: '1',
  currentDay: 3,
  completedDays: [1, 2],
  startedAt: new Date(Date.now() - 172800000).toISOString(),
  lastAccessedAt: new Date(Date.now() - 86400000).toISOString(),
  status: 'in-progress',
};

export const mockChatMessages: ChatMessage[] = [
  {
    id: '1',
    sessionId: 'session-1',
    role: 'ai',
    content: 'Olá! Eu sou a Acollya, sua assistente de suporte emocional. Como você está se sentindo hoje?',
    timestamp: new Date(Date.now() - 3600000).toISOString(),
  },
  {
    id: '2',
    sessionId: 'session-1',
    role: 'user',
    content: 'Estou me sentindo um pouco ansiosa hoje.',
    timestamp: new Date(Date.now() - 3500000).toISOString(),
  },
  {
    id: '3',
    sessionId: 'session-1',
    role: 'ai',
    content: 'Entendo que você está se sentindo ansiosa. A ansiedade é uma emoção válida e comum. Gostaria de conversar sobre o que está causando essa sensação?',
    timestamp: new Date(Date.now() - 3400000).toISOString(),
  },
];

export const mockChatSession: ChatSession = {
  id: 'session-1',
  userId: '1',
  title: 'Conversa sobre ansiedade',
  createdAt: new Date(Date.now() - 86400000).toISOString(),
  updatedAt: new Date(Date.now() - 3400000).toISOString(),
};

export const mockAIResponses: string[] = [
  'Entendo como você está se sentindo. Suas emoções são válidas e importantes.',
  'Obrigada por compartilhar isso comigo. Como posso te apoiar melhor neste momento?',
  'Percebo que você está passando por um momento desafiador. Vamos conversar sobre isso?',
  'É corajoso da sua parte expressar seus sentimentos. Como você gostaria de lidar com essa situação?',
  'Suas palavras mostram muita autoconsciência. O que você acha que poderia te ajudar agora?',
  'Estou aqui para te ouvir e apoiar. Conte-me mais sobre o que está acontecendo.',
  'Vejo que isso é importante para você. Vamos explorar juntas algumas estratégias que podem te ajudar.',
];