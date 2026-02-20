import { cn } from '@/lib/utils';
import { MessageRole } from '@/types/chat';

interface ChatBubbleProps {
  role: MessageRole;
  content: string;
  timestamp?: string;
}

export function ChatBubble({ role, content, timestamp }: ChatBubbleProps) {
  const isAI = role === 'ai';

  return (
    <div className={cn('flex w-full mb-4', isAI ? 'justify-start' : 'justify-end')}>
      <div className={cn('max-w-[80%] animate-slide-up')}>
        <div
          className={cn(
            'rounded-[18px] px-4 py-3 shadow-sm',
            isAI
              ? 'bg-lavanda-serenidade text-azul-salvia'
              : 'bg-lavanda-profunda text-white'
          )}
        >
          <p className="text-[15px] leading-relaxed whitespace-pre-wrap">{content}</p>
        </div>
        {timestamp && (
          <p className="text-xs text-cinza-calmo mt-1 px-2">
            {new Date(timestamp).toLocaleTimeString('pt-BR', {
              hour: '2-digit',
              minute: '2-digit',
            })}
          </p>
        )}
      </div>
    </div>
  );
}