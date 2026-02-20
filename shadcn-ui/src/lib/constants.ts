// Acollya Constants

export const COLORS = {
  lavandaSerenidade: '#C9C1F0',
  azulSalvia: '#6A80A6',
  offWhite: '#F5F4F8',
  lavandaProfunda: '#7E71C9',
  pessego: '#F3D5C4',
  verdeNevoa: '#B9D6C2',
  cinzaCalmo: '#A3A3AF',
  cinzaNeutro: '#CECED8',
};

export const EMOTIONS = [
  { id: 'muito-bem', label: 'Muito bem', icon: '😊', level: 5 },
  { id: 'bem', label: 'Bem', icon: '🙂', level: 4 },
  { id: 'neutro', label: 'Neutro', icon: '😐', level: 3 },
  { id: 'triste', label: 'Triste', icon: '😔', level: 2 },
  { id: 'muito-triste', label: 'Muito triste', icon: '😢', level: 1 },
];

export const CRISIS_KEYWORDS = [
  'suicídio',
  'suicidio',
  'me matar',
  'acabar com tudo',
  'não aguento mais',
  'nao aguento mais',
  'quero morrer',
  'autoagressão',
  'autoagressao',
  'me machucar',
];

export const CVV_PHONE = '188';
export const CVV_MESSAGE = `Se você está em crise ou pensando em se machucar, por favor, ligue para o CVV (Centro de Valorização da Vida) no número ${CVV_PHONE}. O atendimento é gratuito, sigiloso e disponível 24 horas.`;

export const CHAT_DISCLAIMER = 'A Acollya não substitui terapia presencial nem atendimento de emergência. Em caso de risco imediato, ligue 188 (CVV).';

export const API_ENDPOINTS = {
  auth: {
    login: '/auth/login',
    register: '/auth/register',
    google: '/auth/google',
    forgotPassword: '/auth/forgot-password',
  },
  user: {
    me: '/me',
    update: '/me',
    delete: '/me',
  },
  mood: {
    checkins: '/mood-checkins',
    summary: '/mood-checkins/summary',
  },
  journal: {
    entries: '/journals',
    reflection: '/ai/journal-reflection',
  },
  chat: {
    send: '/chat/send',
    sessions: '/chat/sessions',
    session: (id: string) => `/chat/sessions/${id}`,
  },
  programs: {
    list: '/programs',
    detail: (id: string) => `/programs/${id}`,
    progress: (id: string) => `/programs/${id}/progress`,
  },
  analytics: {
    mood: '/analytics/mood',
    recommendations: '/analytics/recommendations',
  },
  therapists: {
    list: '/therapists',
    detail: (id: string) => `/therapists/${id}`,
    availability: (id: string) => `/therapists/${id}/availability`,
  },
  appointments: {
    create: '/appointments',
    list: '/appointments',
  },
  subscriptions: {
    current: '/subscriptions/current',
    upgrade: '/subscriptions/upgrade',
  },
};