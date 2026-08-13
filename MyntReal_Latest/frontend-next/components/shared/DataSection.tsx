import React from 'react';

interface DataField {
  label: string;
  value: React.ReactNode;
  isMasked?: boolean;
}

interface DataSectionProps {
  title: string;
  icon: React.ReactNode;
  fields: DataField[];
}

export default function DataSection({ title, icon, fields }: DataSectionProps) {
  return (
    <div className="bg-card-start border border-slate-700/50 rounded-lg p-6 shadow-sm">
      <h3 className="text-lg font-medium text-brand-warning flex items-center gap-2 mb-4">
        {icon}
        {title}
      </h3>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {fields.map((field, idx) => (
          <div key={idx} className="flex flex-col gap-1">
            <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">
              {field.label}
            </span>
            <span className={`text-sm ${field.isMasked ? 'text-slate-500 font-mono tracking-widest' : 'text-slate-200'} font-medium break-words`}>
              {field.value || '-'}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
