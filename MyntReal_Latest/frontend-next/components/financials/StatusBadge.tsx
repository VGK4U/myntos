import React from 'react';

interface StatusBadgeProps {
  status: string;
}

export default function StatusBadge({ status }: StatusBadgeProps) {
  let baseClasses = "px-2.5 py-1 rounded-md text-xs font-semibold whitespace-nowrap border ";
  let colorClasses = "";

  const s = status.toLowerCase();

  switch (true) {
    case s === 'pending':
      colorClasses = "bg-yellow-500/10 text-yellow-500 border-yellow-500/20";
      break;
    case s === 'staff validated' || s === 'validated':
      colorClasses = "bg-blue-500/10 text-blue-400 border-blue-500/20";
      break;
    case s === 'completed':
      colorClasses = "bg-purple-500/10 text-purple-400 border-purple-500/20";
      break;
    case s === 'cleared' || s === 'active' || s === 'success':
      colorClasses = "bg-green-500/10 text-green-400 border-green-500/20";
      break;
    case s === 'exception' || s === 'failed' || s === 'rejected':
      colorClasses = "bg-red-500/10 text-red-400 border-red-500/20";
      break;
    default:
      colorClasses = "bg-slate-500/10 text-slate-400 border-slate-500/20";
  }

  return (
    <span className={`${baseClasses} ${colorClasses}`}>
      {status}
    </span>
  );
}
