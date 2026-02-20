// Utility functions for calling Supabase Edge Functions
import { supabase, isDemoMode } from './supabase';

const SUPABASE_URL = import.meta.env.VITE_SUPABASE_URL || '';

// Helper to call Edge Functions with proper authentication
export async function callEdgeFunction<T = unknown>(
  functionName: string,
  payload: Record<string, unknown>
): Promise<T> {
  if (isDemoMode() || !supabase) {
    throw new Error('Edge Functions not available in demo mode');
  }

  // Get current session for authentication
  const {
    data: { session },
    error: sessionError,
  } = await supabase.auth.getSession();

  if (sessionError) {
    console.error('Error getting session:', sessionError);
    throw new Error('Authentication required');
  }

  if (!session) {
    throw new Error('No active session');
  }

  // Call Edge Function
  const response = await fetch(`${SUPABASE_URL}/functions/v1/${functionName}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${session.access_token}`,
      apikey: import.meta.env.VITE_SUPABASE_ANON_KEY || '',
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const errorText = await response.text();
    let errorMessage = `Edge Function error: ${response.status}`;

    try {
      const errorJson = JSON.parse(errorText) as { error?: string };
      errorMessage = errorJson.error || errorMessage;
    } catch {
      errorMessage = errorText || errorMessage;
    }

    throw new Error(errorMessage);
  }

  const data = await response.json();
  return data as T;
}

// Specific Edge Function callers

export interface ChatAIRequest {
  message: string;
  userId: string;
  sessionId?: string;
}

export interface ChatAIResponse {
  success: boolean;
  response: string;
  messagesRemaining: number | null;
}

export async function callChatAI(request: ChatAIRequest): Promise<ChatAIResponse> {
  return callEdgeFunction<ChatAIResponse>('chat-ai', request);
}

export interface JournalReflectionRequest {
  entryId: string;
  content: string;
  userId: string;
}

export interface JournalReflectionResponse {
  success: boolean;
  reflection: string;
}

export async function callJournalReflection(
  request: JournalReflectionRequest
): Promise<JournalReflectionResponse> {
  return callEdgeFunction<JournalReflectionResponse>('journal-reflection', request);
}

export interface TherapistMatchingRequest {
  userId: string;
  answers: {
    preferredGender?: 'male' | 'female' | 'any';
    specializations?: string[];
    ageRange?: 'young' | 'middle' | 'senior' | 'any';
    approach?: string[];
    language?: string[];
    availability?: 'morning' | 'afternoon' | 'evening' | 'any';
    budget?: 'low' | 'medium' | 'high' | 'any';
  };
}

export interface TherapistMatch {
  id: string;
  name: string;
  specialization: string;
  bio: string;
  rating: number;
  hourlyRate: number;
  score: number;
  matchReasons: string[];
}

export interface TherapistMatchingResponse {
  success: boolean;
  matches: TherapistMatch[];
  totalAnalyzed: number;
}

export async function callTherapistMatching(
  request: TherapistMatchingRequest
): Promise<TherapistMatchingResponse> {
  return callEdgeFunction<TherapistMatchingResponse>('therapist-matching', request);
}

export interface MoodInsightsRequest {
  userId: string;
  period: 'week' | 'month' | 'year';
}

export interface MoodInsights {
  period: string;
  totalCheckins: number;
  averageMood: number;
  moodDistribution: Record<string, number>;
  trends: string[];
  recommendations: string[];
  mostCommonMood: string;
  moodImprovement: number;
}

export interface MoodInsightsResponse {
  success: boolean;
  insights: MoodInsights;
}

export async function callMoodInsights(
  request: MoodInsightsRequest
): Promise<MoodInsightsResponse> {
  return callEdgeFunction<MoodInsightsResponse>('mood-insights', request);
}

export interface MoodCheckinRequest {
  userId: string;
  mood: string;
  intensity: number;
  note?: string;
  activities?: string[];
  generateInsight?: boolean;
}

export interface MoodCheckinResponse {
  success: boolean;
  checkin: {
    id: string;
    mood: string;
    intensity: number;
    note?: string;
    createdAt: string;
  };
  insight?: string;
  message: string;
}

export async function callMoodCheckin(
  request: MoodCheckinRequest
): Promise<MoodCheckinResponse> {
  return callEdgeFunction<MoodCheckinResponse>('mood-checkin', request);
}

export interface ProgramProgressRequest {
  userId: string;
  programId: string;
  chapterId: string;
  action: 'complete' | 'reset';
}

export interface ProgramProgress {
  totalChapters: number;
  completedChapters: number;
  percentageComplete: number;
  lastUpdated: string;
  chapters: Array<{
    id: string;
    completed: boolean;
    completedAt?: string;
  }>;
}

export interface ProgramProgressResponse {
  success: boolean;
  progress: ProgramProgress;
  message: string;
}

export async function callProgramProgress(
  request: ProgramProgressRequest
): Promise<ProgramProgressResponse> {
  return callEdgeFunction<ProgramProgressResponse>('program-progress', request);
}

export interface AppointmentBookingRequest {
  userId: string;
  therapistId: string;
  date: string;
  time: string;
  action?: 'create' | 'cancel';
  appointmentId?: string;
}

export interface AppointmentDetails {
  id: string;
  userId: string;
  therapistId: string;
  therapistName: string;
  date: string;
  time: string;
  status: string;
  meetLink: string;
  amount: number;
  createdAt: string;
}

export interface AppointmentBookingResponse {
  success: boolean;
  appointment?: AppointmentDetails;
  message: string;
}

export async function callAppointmentBooking(
  request: AppointmentBookingRequest
): Promise<AppointmentBookingResponse> {
  return callEdgeFunction<AppointmentBookingResponse>('appointment-booking', request);
}