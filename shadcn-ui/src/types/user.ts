export interface User {
  id: string;
  name: string;
  email: string;
  phone?: string;
  birthDate?: string;
  gender?: string;
  whatsapp?: string;
  registrationDate?: string;
  planCode: number; // 0 = Gratuito, 1 = Premium
  trialEndsAt?: string;
  createdAt?: string;
  termsAccepted: boolean;
  termsAcceptedDate?: string;
  preferences?: {
    notifications: boolean;
    emailUpdates: boolean;
  };
}

export interface AuthResponse {
  user: User;
  token: string;
}

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface RegisterData {
  name: string;
  email: string;
  password: string;
  acceptedTerms: boolean;
}

export interface UpdateUserData {
  name?: string;
  whatsapp?: string;
  phone?: string;
  birthDate?: string;
  gender?: string;
  termsAccepted?: boolean;
  termsAcceptedDate?: string;
}