/**
 * Chat types for Acollya PWA
 */

export interface ChatMessage {
  id: string;
  session_id: string;
  user_id: string;
  role: 'user' | 'assistant';
  content: string;
  created_at: string;
  tokens_used?: number;
  model?: string;
  embedding?: number[];
}

export interface ChatSession {
  id: string;
  user_id: string;
  title: string;
  summary?: string;
  context_window: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  last_message_at: string;
  message_count?: number;
}

export interface StreamEvent {
  chunk?: string;
  done?: boolean;
  session_id?: string;
  tokens?: number;
  cost?: number;
  remaining?: number;
  error?: string;
  message?: string;
}

export interface SendMessageOptions {
  message: string;
  sessionId?: string;
  onChunk?: (chunk: string) => void;
  onComplete?: (data: StreamEvent) => void;
  onError?: (error: Error) => void;
}

export interface ChatResponse {
  response?: string;
  session_id: string;
  cached?: boolean;
  remaining?: number;
  tokens?: number;
  cost?: number;
}

export interface RateLimitInfo {
  remaining: number;
  limit: number;
  resetAt?: string;
}