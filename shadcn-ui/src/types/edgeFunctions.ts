// Type definitions for Edge Function requests and responses

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

export interface ChatAIError {
  error: string;
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

export interface JournalReflectionError {
  error: string;
}

// Therapist Matching Types
export interface TherapistMatchingRequest {
  userId: string;
  answers: MatchingAnswers;
}

export interface MatchingAnswers {
  preferredGender?: 'male' | 'female' | 'any';
  specializations?: string[];
  ageRange?: 'young' | 'middle' | 'senior' | 'any';
  approach?: string[];
  language?: string[];
  availability?: 'morning' | 'afternoon' | 'evening' | 'any';
  budget?: 'low' | 'medium' | 'high' | 'any';
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

// Mood Insights Types
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

// Mood Check-in Types
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

// Program Progress Types
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

// Appointment Booking Types
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

// Rate limit error type
export interface RateLimitError {
  error: string;
  messagesRemaining: number;
  resetTime?: string;
}

// Generic Edge Function error
export interface EdgeFunctionError {
  error: string;
  statusCode?: number;
  details?: unknown;
}