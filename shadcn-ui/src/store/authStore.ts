import { create } from 'zustand';
import { User } from '@/types/user';

interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  setUser: (user: User | null) => void;
  setToken: (token: string | null) => void;
  updateUser: (user: User) => void;
  login: (user: User, token: string) => void;
  logout: () => void;
  initializeAuth: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  token: null,
  isAuthenticated: false,
  isLoading: true,

  setUser: (user) => set({ user, isAuthenticated: !!user }),

  setToken: (token) => set({ token }),

  updateUser: (user) => {
    localStorage.setItem('acollya_user', JSON.stringify(user));
    set({ user });
  },

  login: (user, token) => {
    localStorage.setItem('acollya_user', JSON.stringify(user));
    localStorage.setItem('acollya_token', token);
    set({ user, token, isAuthenticated: true });
  },

  logout: () => {
    localStorage.removeItem('acollya_user');
    localStorage.removeItem('acollya_token');
    set({ user: null, token: null, isAuthenticated: false });
  },

  initializeAuth: () => {
    const storedUser = localStorage.getItem('acollya_user');
    const storedToken = localStorage.getItem('acollya_token');

    if (storedUser && storedToken) {
      set({
        user: JSON.parse(storedUser),
        token: storedToken,
        isAuthenticated: true,
        isLoading: false,
      });
    } else {
      set({ isLoading: false });
    }
  },
}));