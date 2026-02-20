import { ReactNode } from 'react';
import { BottomNav } from './BottomNav';
import { OfflineIndicator } from './OfflineIndicator';

interface LayoutProps {
  children: ReactNode;
  showBottomNav?: boolean;
}

export function Layout({ children, showBottomNav = true }: LayoutProps) {
  return (
    <div className="min-h-screen bg-offwhite">
      <OfflineIndicator />
      <main className={cn('pb-safe', showBottomNav && 'pb-20')}>
        {children}
      </main>
      {showBottomNav && <BottomNav />}
    </div>
  );
}

function cn(...classes: (string | boolean | undefined)[]) {
  return classes.filter(Boolean).join(' ');
}