import { ButtonHTMLAttributes, forwardRef } from 'react';
import { cn } from '@/lib/utils';

export const TertiaryButton = forwardRef<HTMLButtonElement, ButtonHTMLAttributes<HTMLButtonElement>>(
  ({ className, children, ...props }, ref) => {
    return (
      <button
        ref={ref}
        className={cn(
          'px-4 py-2 font-body font-medium text-azul-salvia',
          'hover:text-lavanda-profunda hover:underline',
          'transition-colors duration-200',
          'focus:outline-none focus:ring-2 focus:ring-lavanda-profunda focus:ring-offset-2 rounded',
          className
        )}
        {...props}
      >
        {children}
      </button>
    );
  }
);

TertiaryButton.displayName = 'TertiaryButton';