import React from 'react';

interface EmptyStateProps {
  icon?: string;
  title: string;
  description: string;
  actionLabel?: string;
  onAction?: () => void;
  className?: string;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  icon = '📂',
  title,
  description,
  actionLabel,
  onAction,
  className = '',
}) => {
  return (
    <div className={`p-8 text-center rounded-3xl border border-dashed border-slate-300 dark:border-slate-700 bg-slate-50/60 dark:bg-slate-900/30 flex flex-col items-center justify-center space-y-3 ${className}`}>
      <div className="w-12 h-12 rounded-2xl bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 shadow-sm flex items-center justify-center text-2xl">
        {icon}
      </div>
      <div className="max-w-md">
        <h4 className="text-sm font-bold text-brand-dark dark:text-white">{title}</h4>
        <p className="text-xs text-brand-slate dark:text-slate-400 mt-1 leading-relaxed">{description}</p>
      </div>
      {actionLabel && onAction && (
        <button
          onClick={onAction}
          className="mt-2 px-4 py-2 bg-brand-coral hover:bg-orange-600 text-white rounded-xl text-xs font-bold transition shadow-sm focus:outline-none focus:ring-2 focus:ring-brand-coral focus:ring-offset-2"
        >
          {actionLabel}
        </button>
      )}
    </div>
  );
};
