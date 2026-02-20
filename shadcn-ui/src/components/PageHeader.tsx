import { BackButton } from './BackButton';

interface PageHeaderProps {
  title: string;
  subtitle?: string;
  backTo?: string;
}

export function PageHeader({ title, subtitle, backTo }: PageHeaderProps) {
  return (
    <div className="flex items-center gap-4 mb-6">
      <BackButton to={backTo} />
      <div>
        <h1 className="text-2xl font-heading font-bold text-azul-salvia">
          {title}
        </h1>
        {subtitle && (
          <p className="text-sm text-azul-salvia/70">
            {subtitle}
          </p>
        )}
      </div>
    </div>
  );
}