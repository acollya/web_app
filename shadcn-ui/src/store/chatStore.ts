import { create } from 'zustand';

interface ChatState {
  activeSessionId: string | null;
  isTyping: boolean;
  setActiveSession: (sessionId: string) => void;
  setIsTyping: (isTyping: boolean) => void;
  clearActiveSession: () => void;
}

export const useChatStore = create<ChatState>((set) => ({
  activeSessionId: null,
  isTyping: false,

  setActiveSession: (sessionId) => set({ activeSessionId: sessionId }),

  setIsTyping: (isTyping) => set({ isTyping }),

  clearActiveSession: () => set({ activeSessionId: null, isTyping: false }),
}));