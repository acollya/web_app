/**
 * Chat Page - Acollya AI Chat Interface
 * Features: Streaming responses, session management, rate limiting
 */

import { useState, useEffect, useRef } from 'react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Send, Sparkles } from 'lucide-react';
import { toast } from 'sonner';
import { sendMessage, getSessionMessages, getRateLimitInfo } from '@/services/chatService';
import { StreamingIndicator } from '@/components/chat/StreamingIndicator';
import { MessageLimitBadge } from '@/components/chat/MessageLimitBadge';
import { CacheBadge } from '@/components/chat/CacheBadge';
import { SessionSelector } from '@/components/chat/SessionSelector';
import type { ChatMessage } from '@/types/chat';

export default function Chat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingContent, setStreamingContent] = useState('');
  const [currentSessionId, setCurrentSessionId] = useState<string | undefined>();
  const [isCached, setIsCached] = useState(false);
  const [rateLimit, setRateLimit] = useState({ remaining: 20, limit: 20 });
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    loadRateLimit();
  }, []);

  useEffect(() => {
    if (currentSessionId) {
      loadMessages(currentSessionId);
    }
  }, [currentSessionId]);

  useEffect(() => {
    // Auto-scroll to bottom when new messages arrive
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, streamingContent]);

  const loadMessages = async (sessionId: string) => {
    try {
      const data = await getSessionMessages(sessionId);
      setMessages(data);
    } catch (error) {
      console.error('Error loading messages:', error);
      toast.error('Erro ao carregar mensagens');
    }
  };

  const loadRateLimit = async () => {
    try {
      const data = await getRateLimitInfo();
      setRateLimit(data);
    } catch (error) {
      console.error('Error loading rate limit:', error);
    }
  };

  const handleSendMessage = async () => {
    if (!input.trim() || isStreaming) return;

    const userMessage = input.trim();
    setInput('');
    setIsStreaming(true);
    setStreamingContent('');
    setIsCached(false);

    // Add user message to UI immediately
    const tempUserMessage: ChatMessage = {
      id: `temp-${Date.now()}`,
      session_id: currentSessionId || '',
      user_id: '',
      role: 'user',
      content: userMessage,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, tempUserMessage]);

    try {
      const response = await sendMessage({
        message: userMessage,
        sessionId: currentSessionId,
        onChunk: (chunk) => {
          setStreamingContent((prev) => prev + chunk);
        },
        onComplete: (data) => {
          setIsStreaming(false);
          
          // Update session ID if new session was created
          if (data.session_id && !currentSessionId) {
            setCurrentSessionId(data.session_id);
          }

          // Check if response was cached
          if (data.done) {
            setIsCached(false);
          }

          // Update rate limit
          if (data.remaining !== undefined) {
            setRateLimit((prev) => ({ ...prev, remaining: data.remaining! }));
          }

          // Reload messages to get final state from DB
          if (data.session_id) {
            loadMessages(data.session_id);
          }

          setStreamingContent('');
        },
        onError: (error) => {
          setIsStreaming(false);
          setStreamingContent('');
          toast.error(error.message || 'Erro ao enviar mensagem');
          
          // Remove temporary user message on error
          setMessages((prev) => prev.filter((m) => m.id !== tempUserMessage.id));
        },
      });

      // Handle cached response (non-streaming)
      if (response.cached) {
        setIsCached(true);
        
        const assistantMessage: ChatMessage = {
          id: `temp-assistant-${Date.now()}`,
          session_id: response.session_id,
          user_id: '',
          role: 'assistant',
          content: response.response || '',
          created_at: new Date().toISOString(),
        };
        
        setMessages((prev) => [...prev, assistantMessage]);
        
        if (response.remaining !== undefined) {
          setRateLimit((prev) => ({ ...prev, remaining: response.remaining! }));
        }
      }
    } catch (error) {
      console.error('Error sending message:', error);
      // Error already handled in onError callback
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const handleSessionChange = (sessionId: string) => {
    setCurrentSessionId(sessionId);
    setMessages([]);
    setStreamingContent('');
    setIsCached(false);
  };

  return (
    <div className="container mx-auto max-w-4xl p-4 h-screen flex flex-col">
      <Card className="flex-1 flex flex-col">
        <CardHeader className="border-b">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Sparkles className="h-6 w-6 text-primary" />
              <CardTitle>Chat com Acollya</CardTitle>
            </div>
            <div className="flex items-center gap-2">
              <MessageLimitBadge remaining={rateLimit.remaining} limit={rateLimit.limit} />
              <SessionSelector
                currentSessionId={currentSessionId}
                onSessionChange={handleSessionChange}
              />
            </div>
          </div>
        </CardHeader>

        <CardContent className="flex-1 flex flex-col p-0">
          {/* Messages Area */}
          <ScrollArea className="flex-1 p-4" ref={scrollRef}>
            <div className="space-y-4">
              {messages.length === 0 && !isStreaming && (
                <div className="text-center text-muted-foreground py-12">
                  <Sparkles className="h-12 w-12 mx-auto mb-4 text-primary/50" />
                  <p className="text-lg font-medium mb-2">Olá! Sou a Acollya 💙</p>
                  <p className="text-sm">
                    Estou aqui para te ouvir e ajudar. Como você está se sentindo hoje?
                  </p>
                </div>
              )}

              {messages.map((message) => (
                <div
                  key={message.id}
                  className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <div
                    className={`max-w-[80%] rounded-lg px-4 py-3 ${
                      message.role === 'user'
                        ? 'bg-primary text-primary-foreground'
                        : 'bg-muted'
                    }`}
                  >
                    <p className="whitespace-pre-wrap">{message.content}</p>
                    <div className="text-xs opacity-70 mt-1">
                      {new Date(message.created_at).toLocaleTimeString('pt-BR', {
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                    </div>
                  </div>
                </div>
              ))}

              {/* Streaming message */}
              {isStreaming && streamingContent && (
                <div className="flex justify-start">
                  <div className="max-w-[80%] rounded-lg px-4 py-3 bg-muted">
                    <p className="whitespace-pre-wrap">{streamingContent}</p>
                  </div>
                </div>
              )}

              {/* Streaming indicator */}
              {isStreaming && !streamingContent && (
                <div className="flex justify-start">
                  <StreamingIndicator />
                </div>
              )}

              {/* Cache badge */}
              {isCached && (
                <div className="flex justify-center">
                  <CacheBadge />
                </div>
              )}
            </div>
          </ScrollArea>

          {/* Input Area */}
          <div className="border-t p-4">
            <div className="flex gap-2">
              <Textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Digite sua mensagem... (Shift+Enter para nova linha)"
                className="min-h-[60px] max-h-[200px] resize-none"
                disabled={isStreaming || rateLimit.remaining === 0}
              />
              <Button
                onClick={handleSendMessage}
                disabled={!input.trim() || isStreaming || rateLimit.remaining === 0}
                size="icon"
                className="h-[60px] w-[60px] shrink-0"
              >
                <Send className="h-5 w-5" />
              </Button>
            </div>
            
            {rateLimit.remaining === 0 && (
              <p className="text-sm text-destructive mt-2">
                Você atingiu o limite de mensagens. Aguarde ou faça upgrade do seu plano.
              </p>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}