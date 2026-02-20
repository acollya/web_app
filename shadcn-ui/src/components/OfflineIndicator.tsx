import { useOffline } from '@/hooks/useOffline';
import { WifiOff } from 'lucide-react';

export function OfflineIndicator() {
  const isOffline = useOffline();

  if (!isOffline) return null;

  return (
    <div className="fixed top-0 left-0 right-0 z-50 bg-pessego text-azul-salvia px-4 py-2 text-center animate-slide-up">
      <div className="flex items-center justify-center gap-2 text-sm font-medium">
        <WifiOff size={16} />
        <span>Você está offline. Suas alterações serão sincronizadas quando voltar online.</span>
      </div>
    </div>
  );
}