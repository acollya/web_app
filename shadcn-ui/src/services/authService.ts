import { apiClient } from './apiClient';
import { API_ENDPOINTS } from '@/lib/constants';
import { AuthResponse, LoginCredentials, RegisterData } from '@/types/user';
import { mockUser } from '@/lib/mockData';

// Mock authentication service - will be replaced with real API calls
export const authService = {
  async login(credentials: LoginCredentials): Promise<AuthResponse> {
    // Simulate API call
    await new Promise(resolve => setTimeout(resolve, 1000));
    
    // Mock response
    return {
      user: mockUser,
      token: 'mock-jwt-token-' + Date.now(),
    };
    
    // Future real implementation:
    // return apiClient.post<AuthResponse>(API_ENDPOINTS.auth.login, credentials);
  },

  async register(data: RegisterData): Promise<AuthResponse> {
    // Simulate API call
    await new Promise(resolve => setTimeout(resolve, 1000));
    
    // Mock response
    return {
      user: { ...mockUser, name: data.name, email: data.email },
      token: 'mock-jwt-token-' + Date.now(),
    };
    
    // Future real implementation:
    // return apiClient.post<AuthResponse>(API_ENDPOINTS.auth.register, data);
  },

  async loginWithGoogle(): Promise<AuthResponse> {
    // Simulate API call
    await new Promise(resolve => setTimeout(resolve, 1000));
    
    // Mock response
    return {
      user: mockUser,
      token: 'mock-jwt-token-google-' + Date.now(),
    };
    
    // Future real implementation:
    // return apiClient.post<AuthResponse>(API_ENDPOINTS.auth.google, {});
  },

  async forgotPassword(email: string): Promise<{ message: string }> {
    // Simulate API call
    await new Promise(resolve => setTimeout(resolve, 1000));
    
    return {
      message: 'Email de recuperação enviado com sucesso',
    };
    
    // Future real implementation:
    // return apiClient.post(API_ENDPOINTS.auth.forgotPassword, { email });
  },

  logout() {
    // Clear local storage
    localStorage.removeItem('acollya_token');
    localStorage.removeItem('acollya_user');
  },
};