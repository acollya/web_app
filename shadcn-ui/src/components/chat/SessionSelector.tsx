/**
 * Session Selector Component
 * Allows users to switch between chat sessions
 */

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { MessageSquare, Plus, Trash2 } from 'lucide-react';
import { getSessions, createSession, deleteSession } from '@/services/chatService';
import type { ChatSession } from '@/types/chat';
import { toast } from 'sonner';

interface SessionSelectorProps {
  currentSessionId?: string;
  onSessionChange: (sessionId: string) => void;
}

export function SessionSelector({ currentSessionId, onSessionChange }: SessionSelectorProps) {
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadSessions();
  }, []);

  const loadSessions = async () => {
    try {
      setLoading(true);
      const data = await getSessions();
      setSessions(data);
    } catch (error) {
      console.error('Error loading sessions:', error);
      toast.error('Erro ao carregar conversas');
    } finally {
      setLoading(false);
    }
  };

  const handleNewSession = async () => {
    try {
      const newSession = await createSession();
      setSessions([newSession, ...sessions]);
      onSessionChange(newSession.id);
      toast.success('Nova conversa criada');
    } catch (error) {
      console.error('Error creating session:', error);
      toast.error('Erro ao criar nova conversa');
    }
  };

  const handleDeleteSession = async (sessionId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    
    try {
      await deleteSession(sessionId);
      setSessions(sessions.filter((s) => s.id !== sessionId));
      
      if (currentSessionId === sessionId) {
        const remainingSessions = sessions.filter((s) => s.id !== sessionId);
        if (remainingSessions.length > 0) {
          onSessionChange(remainingSessions[0].id);
        }
      }
      
      toast.success('Conversa excluída');
    } catch (error) {
      console.error('Error deleting session:', error);
      toast.error('Erro ao excluir conversa');
    }
  };

  const currentSession = sessions.find((s) => s.id === currentSessionId);

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="outline" className="gap-2">
          <MessageSquare className="h-4 w-4" />
          <span className="max-w-[150px] truncate">
            {currentSession?.title || 'Selecionar conversa'}
          </span>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start" className="w-[300px]">
        <DropdownMenuLabel>Suas conversas</DropdownMenuLabel>
        <DropdownMenuSeparator />
        
        <DropdownMenuItem onClick={handleNewSession} className="gap-2">
          <Plus className="h-4 w-4" />
          <span>Nova conversa</span>
        </DropdownMenuItem>
        
        <DropdownMenuSeparator />
        
        {loading ? (
          <DropdownMenuItem disabled>Carregando...</DropdownMenuItem>
        ) : sessions.length === 0 ? (
          <DropdownMenuItem disabled>Nenhuma conversa ainda</DropdownMenuItem>
        ) : (
          sessions.map((session) => (
            <DropdownMenuItem
              key={session.id}
              onClick={() => onSessionChange(session.id)}
              className="flex items-center justify-between gap-2"
            >
              <div className="flex-1 min-w-0">
                <div className="font-medium truncate">{session.title}</div>
                <div className="text-xs text-muted-foreground">
                  {new Date(session.last_message_at).toLocaleDateString('pt-BR')}
                </div>
              </div>
              <Button
                variant="ghost"
                size="icon"
                className="h-6 w-6 shrink-0"
                onClick={(e) => handleDeleteSession(session.id, e)}
              >
                <Trash2 className="h-3 w-3" />
              </Button>
            </DropdownMenuItem>
          ))
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}