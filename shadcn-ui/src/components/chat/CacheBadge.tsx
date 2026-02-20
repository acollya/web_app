/**
 * Cache Badge Component
 * Shows when a response was retrieved from cache
 */

import { Badge } from '@/components/ui/badge';
import { Zap } from 'lucide-react';

export function CacheBadge() {
  return (
    <Badge variant="outline" className="gap-1 bg-green-50 text-green-700 border-green-200">
      <Zap className="h-3 w-3" />
      <span className="text-xs">Resposta em cache</span>
    </Badge>
  );
}