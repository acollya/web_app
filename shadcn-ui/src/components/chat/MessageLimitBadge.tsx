/**
 * Message Limit Badge Component
 * Shows remaining messages for rate limiting
 */

import { Badge } from '@/components/ui/badge';
import { MessageCircle } from 'lucide-react';

interface MessageLimitBadgeProps {
  remaining: number;
  limit: number;
}

export function MessageLimitBadge({ remaining, limit }: MessageLimitBadgeProps) {
  const percentage = (remaining / limit) * 100;
  
  // Color based on remaining messages
  const variant = percentage > 50 ? 'default' : percentage > 20 ? 'secondary' : 'destructive';

  return (
    <Badge variant={variant} className="gap-1">
      <MessageCircle className="h-3 w-3" />
      <span className="text-xs">
        {remaining}/{limit} mensagens
      </span>
    </Badge>
  );
}