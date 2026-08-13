"use client";

import React, { useState } from 'react';

interface MemberSearchHeaderProps {
  onSearch: (mnrId: string) => void;
  isSearching: boolean;
  memberInfo?: {
    name: string;
    id: string;
    status?: string;
  } | null;
  title: string;
  icon: React.ReactNode;
  subtitle: string;
}

export default function MemberSearchHeader({ 
  onSearch, 
  isSearching, 
  memberInfo,
  title,
  icon,
  subtitle
}: MemberSearchHeaderProps) {
  const [inputValue, setInputValue] = useState('');

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (inputValue.trim()) {
      onSearch(inputValue.trim().toUpperCase());
    }
  };

  return (
    <div className="mb-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-slate-100 flex items-center gap-3">
          <span className="text-brand-warning">{icon}</span>
          {title}
        </h1>
        <p className="text-slate-400 mt-1">{subtitle}</p>
      </div>

      <div className="bg-card-start border border-slate-700/50 rounded-lg p-6 shadow-sm">
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
          
          <div className="w-full md:w-1/2">
            <label className="block text-sm font-medium text-slate-300 mb-2">
              Search MNR ID
            </label>
            <form onSubmit={handleSearch} className="flex gap-3">
              <div className="relative flex-1">
                <span className="absolute inset-y-0 left-0 pl-3 flex items-center text-slate-500 pointer-events-none text-sm">
                  MNR
                </span>
                <input
                  type="text"
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  placeholder="Enter member ID (e.g., 1800001)"
                  className="block w-full pl-12 pr-3 py-2 border border-slate-600 rounded-md bg-slate-800/50 text-white placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-brand-warning focus:border-brand-warning sm:text-sm uppercase transition-colors"
                />
              </div>
              <button
                type="submit"
                disabled={isSearching}
                className="px-4 py-2 bg-brand-warning text-slate-900 font-medium rounded-md hover:bg-yellow-400 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-brand-warning focus:ring-offset-slate-900 disabled:opacity-50 transition-all"
              >
                {isSearching ? 'Searching...' : 'Search'}
              </button>
            </form>
          </div>

          {memberInfo && (
            <div className="w-full md:w-1/2 flex items-center gap-4 bg-slate-800/30 border border-slate-700/50 p-4 rounded-md">
              <div className="w-12 h-12 rounded-full bg-slate-700 flex items-center justify-center text-slate-300 shrink-0">
                <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z" />
                </svg>
              </div>
              <div>
                <h3 className="text-lg font-medium text-white m-0 leading-tight">
                  {memberInfo.name || '-'}
                </h3>
                <div className="flex items-center gap-2 mt-1">
                  <span className="text-sm text-slate-400 font-mono">{memberInfo.id}</span>
                  {memberInfo.status && (
                    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                      memberInfo.status.toLowerCase() === 'active' 
                        ? 'bg-green-500/10 text-green-400 border border-green-500/20' 
                        : 'bg-slate-500/10 text-slate-400 border border-slate-500/20'
                    }`}>
                      {memberInfo.status.toUpperCase()}
                    </span>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
