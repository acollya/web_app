export interface Therapist {
  id: string;
  name: string;
  photo: string;
  specialties: string[];
  rating: number;
  hourlyRate: number;
  premiumDiscount?: number;
  bio?: string;
  credentials?: string[];
}

export interface TherapistAvailability {
  therapistId: string;
  date: string;
  availableSlots: string[]; // Array of time slots like "09:00", "10:00", etc.
}

export interface MatchingAnswers {
  question1: string;
  question2: string;
  question3: string;
  question4: string;
}

export interface Appointment {
  id: string;
  userId: string;
  therapistId: string;
  therapist: Therapist;
  date: string;
  time: string;
  status: 'pending' | 'paid' | 'completed' | 'cancelled';
  amount: number;
  meetLink?: string;
  createdAt: string;
}

export interface CreateAppointmentRequest {
  therapistId: string;
  date: string;
  time: string;
}

export interface MatchingResponse {
  therapists: Therapist[];
  matchScore?: Record<string, number>;
}