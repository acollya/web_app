export interface Therapist {
  id: string;
  name: string;
  crp: string;
  photoUrl?: string;
  approach: string[];
  specialties: string[];
  bio: string;
  priceRange: string;
  rating?: number;
  reviewCount?: number;
}

export interface Availability {
  date: string;
  slots: {
    time: string;
    available: boolean;
  }[];
}

export interface Appointment {
  id: string;
  userId: string;
  therapistId: string;
  date: string;
  time: string;
  status: 'scheduled' | 'completed' | 'cancelled';
  meetingLink?: string;
}