/**
 * Streaming Indicator Component
 * Shows "Acollya está digitando..." animation
 */

import { Loader2 } from 'lucide-react';

export function StreamingIndicator() {
  return (
    <div className="flex items-center gap-2 text-muted-foreground animate-pulse">
      <Loader2 className="h-4 w-4 animate-spin" />
      <span className="text-sm">Acollya está digitando...</span>
    </div>
  );
}