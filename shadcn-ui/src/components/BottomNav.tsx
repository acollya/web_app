import { Link, useLocation } from 'react-router-dom';
import { Home, Heart, MessageCircle, BookOpen, User } from 'lucide-react';
import { cn } from '@/lib/utils';

const navItems = [
  { path: '/home', icon: Home, label: 'Início' },
  { path: '/mood-checkin', icon: Heart, label: 'Humor' },
  { path: '/chat', icon: MessageCircle, label: 'Chat' },
  { path: '/journal', icon: BookOpen, label: 'Diário' },
  { path: '/profile', icon: User, label: 'Perfil' },
];

export function BottomNav() {
  const location = useLocation();

  return (
    <nav className="fixed bottom-0 left-0 right-0 bg-white border-t border-cinza-neutro z-40 safe-area-inset-bottom">
      <div className="flex justify-around items-center h-16 max-w-lg mx-auto px-2">
        {navItems.map(({ path, icon: Icon, label }) => {
          const isActive = location.pathname === path;
          return (
            <Link
              key={path}
              to={path}
              className={cn(
                'flex flex-col items-center justify-center gap-1 px-3 py-2 rounded-lg transition-colors',
                isActive
                  ? 'text-lavanda-profunda'
                  : 'text-cinza-calmo hover:text-azul-salvia'
              )}
            >
              <Icon size={24} strokeWidth={isActive ? 2.5 : 2} />
              <span className="text-xs font-medium">{label}</span>
            </Link>
          );
        })}
      </div>
    </nav>
  );
}