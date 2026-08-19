import React from 'react';

interface IncomeTypePillProps {
  type: string;
}

export default function IncomeTypePill({ type }: IncomeTypePillProps) {
  const baseClasses = "px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider whitespace-nowrap ";
  let colorClasses = "";

  const t = type.toLowerCase();

  switch (true) {
    case t.includes('direct'):
      colorClasses = "bg-[#065f46] text-[#6ee7b7]";
      break;
    case t.includes('matching') || t.includes('group'):
      colorClasses = "bg-[#1e3a8a] text-[#93c5fd]";
      break;
    case t.includes('ved'):
      colorClasses = "bg-[#4c1d95] text-[#c4b5fd]";
      break;
    case t.includes('guru') || t.includes('mentorship'):
      colorClasses = "bg-[#7c2d12] text-[#fdba74]";
      break;
    default:
      colorClasses = "bg-slate-700 text-slate-300";
  }

  // Rebrand mapping (matches legacy code getIncomeDisplayName)
  const rebrandMap: Record<string, string> = {
    'Direct Referral': 'Direct Facilitation',
    'Matching Referral': 'Group Performance Recognition',
    'Ved Income': 'VED Leadership Recognition',
    'Guru Dakshina': 'Mentorship Contribution Benefit'
  };

  const displayName = rebrandMap[type] || type;

  return (
    <span className={`${baseClasses} ${colorClasses}`}>
      {displayName}
    </span>
  );
}
