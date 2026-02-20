import { Loader2, Sparkles } from 'lucide-react';

interface AILoadingStateProps {
  message?: string;
  className?: string;
}

export function AILoadingState({
  message = 'IA está pensando',
  className = '',
}: AILoadingStateProps) {
  return (
    <div className={`flex items-center gap-3 p-4 ${className}`}>
      <div className="relative">
        <Sparkles className="w-5 h-5 text-purple-500 animate-pulse" />
        <Loader2 className="w-5 h-5 text-purple-500 animate-spin absolute top-0 left-0 opacity-50" />
      </div>

      <div className="flex-1">
        <p className="text-sm font-medium text-foreground">{message}</p>
        <div className="flex gap-1 mt-1">
          <span className="w-2 h-2 bg-purple-500 rounded-full animate-bounce [animation-delay:-0.3s]"></span>
          <span className="w-2 h-2 bg-purple-500 rounded-full animate-bounce [animation-delay:-0.15s]"></span>
          <span className="w-2 h-2 bg-purple-500 rounded-full animate-bounce"></span>
        </div>
      </div>
    </div>
  );
}

// Variante para uso em chat (mensagem da IA digitando)
export function AITypingIndicator({ className = '' }: { className?: string }) {
  return (
    <div className={`flex items-start gap-3 ${className}`}>
      <div className="w-8 h-8 rounded-full bg-gradient-to-br from-purple-500 to-blue-500 flex items-center justify-center flex-shrink-0">
        <Sparkles className="w-4 h-4 text-white" />
      </div>

      <div className="bg-muted rounded-2xl rounded-tl-none px-4 py-3">
        <div className="flex gap-1">
          <span className="w-2 h-2 bg-foreground/40 rounded-full animate-bounce [animation-delay:-0.3s]"></span>
          <span className="w-2 h-2 bg-foreground/40 rounded-full animate-bounce [animation-delay:-0.15s]"></span>
          <span className="w-2 h-2 bg-foreground/40 rounded-full animate-bounce"></span>
        </div>
      </div>
    </div>
  );
}