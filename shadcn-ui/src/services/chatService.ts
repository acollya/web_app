/**
 * Chat Service - Handles streaming chat with Acollya AI
 */

import { createClient } from '@supabase/supabase-js';
import type {
  ChatMessage,
  ChatSession,
  StreamEvent,
  SendMessageOptions,
  ChatResponse,
} from '@/types/chat';

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY;

if (!supabaseUrl || !supabaseAnonKey) {
  throw new Error('Missing Supabase environment variables');
}

const supabase = createClient(supabaseUrl, supabaseAnonKey);

/**
 * Send message with streaming response
 */
export async function sendMessage(options: SendMessageOptions): Promise<ChatResponse> {
  const { message, sessionId, onChunk, onComplete, onError } = options;

  try {
    // Get current session
    const {
      data: { session },
    } = await supabase.auth.getSession();

    if (!session) {
      throw new Error('Usuário não autenticado');
    }

    const token = session.access_token;

    // Call Edge Function with streaming
    const response = await fetch(`${supabaseUrl}/functions/v1/chat-ai`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        message,
        session_id: sessionId,
      }),
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || errorData.message || 'Erro ao enviar mensagem');
    }

    // Check if response is cached (non-streaming)
    const contentType = response.headers.get('Content-Type');
    if (contentType?.includes('application/json')) {
      const data = (await response.json()) as ChatResponse;
      
      if (onChunk && data.response) {
        onChunk(data.response);
      }
      
      if (onComplete) {
        onComplete({
          done: true,
          session_id: data.session_id,
          remaining: data.remaining,
        });
      }
      
      return data;
    }

    // Handle streaming response
    const reader = response.body?.getReader();
    if (!reader) {
      throw new Error('No reader available');
    }

    const decoder = new TextDecoder();
    let fullResponse = '';
    let finalData: StreamEvent = { session_id: sessionId || '' };

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value);
      const lines = chunk.split('\n').filter((line) => line.trim() !== '');

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6);

          try {
            const parsed = JSON.parse(data) as StreamEvent;

            if (parsed.chunk) {
              fullResponse += parsed.chunk;
              if (onChunk) {
                onChunk(parsed.chunk);
              }
            }

            if (parsed.done) {
              finalData = parsed;
              if (onComplete) {
                onComplete(parsed);
              }
            }

            if (parsed.error) {
              throw new Error(parsed.message || parsed.error);
            }
          } catch (e) {
            console.error('Error parsing SSE data:', e);
          }
        }
      }
    }

    return {
      response: fullResponse,
      session_id: finalData.session_id || sessionId || '',
      remaining: finalData.remaining,
      tokens: finalData.tokens,
      cost: finalData.cost,
    };
  } catch (error) {
    console.error('Error sending message:', error);
    if (onError) {
      onError(error as Error);
    }
    throw error;
  }
}

/**
 * Get user's chat sessions
 */
export async function getSessions(): Promise<ChatSession[]> {
  try {
    const {
      data: { user },
    } = await supabase.auth.getUser();

    if (!user) {
      throw new Error('Usuário não autenticado');
    }

    const { data, error } = await supabase
      .from('chat_sessions')
      .select('*')
      .eq('user_id', user.id)
      .eq('is_active', true)
      .order('last_message_at', { ascending: false });

    if (error) {
      throw error;
    }

    return data || [];
  } catch (error) {
    console.error('Error fetching sessions:', error);
    throw error;
  }
}

/**
 * Get messages for a specific session
 */
export async function getSessionMessages(sessionId: string): Promise<ChatMessage[]> {
  try {
    const {
      data: { user },
    } = await supabase.auth.getUser();

    if (!user) {
      throw new Error('Usuário não autenticado');
    }

    const { data, error } = await supabase
      .from('chat_messages')
      .select('*')
      .eq('session_id', sessionId)
      .order('created_at', { ascending: true });

    if (error) {
      throw error;
    }

    return data || [];
  } catch (error) {
    console.error('Error fetching messages:', error);
    throw error;
  }
}

/**
 * Create a new chat session
 */
export async function createSession(title: string = 'Nova Conversa'): Promise<ChatSession> {
  try {
    const {
      data: { user },
    } = await supabase.auth.getUser();

    if (!user) {
      throw new Error('Usuário não autenticado');
    }

    const { data, error } = await supabase
      .from('chat_sessions')
      .insert({
        user_id: user.id,
        title,
        is_active: true,
      })
      .select()
      .single();

    if (error) {
      throw error;
    }

    return data;
  } catch (error) {
    console.error('Error creating session:', error);
    throw error;
  }
}

/**
 * Update session title
 */
export async function updateSessionTitle(sessionId: string, title: string): Promise<void> {
  try {
    const { error } = await supabase
      .from('chat_sessions')
      .update({ title })
      .eq('id', sessionId);

    if (error) {
      throw error;
    }
  } catch (error) {
    console.error('Error updating session title:', error);
    throw error;
  }
}

/**
 * Delete (deactivate) a session
 */
export async function deleteSession(sessionId: string): Promise<void> {
  try {
    const { error } = await supabase
      .from('chat_sessions')
      .update({ is_active: false })
      .eq('id', sessionId);

    if (error) {
      throw error;
    }
  } catch (error) {
    console.error('Error deleting session:', error);
    throw error;
  }
}

/**
 * Get rate limit info for current user
 */
export async function getRateLimitInfo(): Promise<{ remaining: number; limit: number }> {
  try {
    const {
      data: { user },
    } = await supabase.auth.getUser();

    if (!user) {
      return { remaining: 0, limit: 0 };
    }

    const { data, error } = await supabase
      .from('users')
      .select('messages_today, plan_code')
      .eq('id', user.id)
      .single();

    if (error) {
      throw error;
    }

    const limit = data.plan_code === 'free' ? 20 : 50;
    const remaining = Math.max(0, limit - (data.messages_today || 0));

    return { remaining, limit };
  } catch (error) {
    console.error('Error fetching rate limit:', error);
    return { remaining: 0, limit: 0 };
  }
}