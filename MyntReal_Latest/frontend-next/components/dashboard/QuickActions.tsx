import React from 'react';
import Link from 'next/link';

interface QuickActionsProps {
  mnrId: string | null;
}

export default function QuickActions({ mnrId }: QuickActionsProps) {
  const actions = [
    { label: 'View Profile', href: `/staff/mnr-user/profile?mnr_id=${mnrId}`, icon: '👤' },
    { label: 'Binary Tree View', href: `/staff/mnr-user/members/picture?mnr_id=${mnrId}`, icon: '🌲' },
    { label: 'Earnings Summary', href: `/staff/mnr-user/mnr/earnings?mnr_id=${mnrId}`, icon: '📈' },
    { label: 'Awards Status', href: `/staff/mnr-user/awards/all?mnr_id=${mnrId}`, icon: '🏆' },
  ];

  return (
    <div className="bg-card-start border border-slate-700/50 rounded-lg shadow-sm h-full flex flex-col">
      <div className="px-6 py-4 border-b border-slate-700/50">
        <h3 className="text-lg font-medium text-white">Quick Actions</h3>
      </div>
      <div className="p-6 flex-1 flex flex-col justify-center gap-3">
        {actions.map((action, idx) => {
          const isDisabled = !mnrId;
          const href = isDisabled ? '#' : action.href;
          
          return (
            <Link 
              key={idx} 
              href={href}
              className={`flex items-center gap-3 px-4 py-3 border border-slate-600 rounded-md transition-all
                ${isDisabled 
                  ? 'opacity-50 cursor-not-allowed bg-slate-800' 
                  : 'hover:border-brand-warning hover:bg-brand-warning/5 hover:-translate-y-0.5'}`}
            >
              <span className="text-xl">{action.icon}</span>
              <span className="font-medium text-sm text-slate-200">{action.label}</span>
            </Link>
          );
        })}
      </div>
    </div>
  );
}
