import { cn } from '@/lib/utils';
import { EmotionLevel } from '@/types/mood';

interface EmotionIconProps {
  emotion: EmotionLevel;
  label: string;
  icon: string;
  selected?: boolean;
  onClick?: () => void;
}

export function EmotionIcon({ emotion, label, icon, selected, onClick }: EmotionIconProps) {
  return (
    <button
      onClick={onClick}
      className={cn(
        'flex flex-col items-center gap-2 p-4 rounded-2xl transition-all duration-300',
        'hover:scale-105 active:scale-95',
        selected
          ? 'bg-lavanda-profunda text-white shadow-lg scale-105'
          : 'bg-white text-azul-salvia hover:bg-lavanda-serenidade/30'
      )}
    >
      <span className="text-4xl">{icon}</span>
      <span className="text-sm font-medium">{label}</span>
    </button>
  );
}