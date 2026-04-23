"use client";

interface CzPageHeaderProps {
  title: string;
  subtitle?: string;
  children?: React.ReactNode; // action buttons
}

export function CzPageHeader({ title, subtitle, children }: CzPageHeaderProps) {
  return (
    <div className="cz-page-header">
      <div>
        <h1 className="cz-page-title">{title}</h1>
        {subtitle && <p className="cz-page-subtitle">{subtitle}</p>}
      </div>
      {children && <div className="cz-flex cz-gap-8 cz-flex-wrap">{children}</div>}
    </div>
  );
}
