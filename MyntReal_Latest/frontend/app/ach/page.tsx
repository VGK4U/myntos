'use client';

import React, { useEffect, useState } from 'react';

export default function AchArchitecturePage() {
  const [activeTab, setActiveTab] = useState<'structure' | 'program' | 'gaps' | 'roadmap'>('structure');

  useEffect(() => {
    // Dynamic import of mermaid to run client-side
    import('mermaid').then((mermaid) => {
      mermaid.default.initialize({ startOnLoad: true, theme: 'dark' });
      mermaid.default.contentLoaded();
    });
  }, [activeTab]);

  return (
    <main className="p-6 max-w-7xl mx-auto">
      {/* Investor Header */}
      <div className="bg-gradient-to-r from-slate-800 to-slate-900 border border-slate-700 rounded-2xl p-6 mb-7 shadow-2xl flex flex-wrap justify-between items-center">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <h1 className="text-2xl font-bold text-white">Mynt OS — Master Architecture Blueprint</h1>
            <span className="bg-emerald-950 text-emerald-300 border border-emerald-500 px-3 py-1 rounded-full text-xs font-bold uppercase">
              <i className="fa-solid fa-circle-check mr-1"></i>Next.js 14 SSR
            </span>
            <span className="bg-purple-950 text-purple-300 border border-purple-500 px-3 py-1 rounded-full text-xs font-bold uppercase">
              <i className="fa-solid fa-code mr-1"></i>TypeScript
            </span>
          </div>
          <p className="text-slate-300 text-sm font-medium">
            End-to-End Enterprise Architecture, Segment Structure, Program Topology, Identified Gaps, and Growth Roadmap
          </p>
        </div>
        <div className="flex items-center gap-2 mt-3 md:mt-0">
          <span className="bg-blue-900 text-blue-200 border border-blue-400 px-3 py-1 rounded-full text-xs font-bold uppercase">
            <i className="fa-brands fa-aws mr-1"></i>AWS Ready (152.57 MB)
          </span>
          <span className="bg-orange-950 text-orange-300 border border-orange-500 px-3 py-1 rounded-full text-xs font-bold uppercase">
            <i className="fa-solid fa-bolt mr-1"></i>v2026.08
          </span>
        </div>
      </div>

      {/* Tabs Header */}
      <div className="flex flex-wrap gap-2 mb-6 border-b border-slate-700 pb-3">
        <button
          onClick={() => setActiveTab('structure')}
          className={`px-4 py-2.5 rounded-lg text-sm font-bold transition-all border ${
            activeTab === 'structure'
              ? 'bg-blue-600 border-blue-500 text-white shadow-lg shadow-blue-600/40'
              : 'bg-slate-800 border-slate-700 text-slate-300 hover:bg-slate-700'
          }`}
        >
          <i className="fa-solid fa-bars-staggered mr-2"></i>1. Full Program Menu & Module Structure
        </button>
        <button
          onClick={() => setActiveTab('program')}
          className={`px-4 py-2.5 rounded-lg text-sm font-bold transition-all border ${
            activeTab === 'program'
              ? 'bg-blue-600 border-blue-500 text-white shadow-lg shadow-blue-600/40'
              : 'bg-slate-800 border-slate-700 text-slate-300 hover:bg-slate-700'
          }`}
        >
          <i className="fa-solid fa-microchip mr-2"></i>2. Technical Program Architecture
        </button>
        <button
          onClick={() => setActiveTab('gaps')}
          className={`px-4 py-2.5 rounded-lg text-sm font-bold transition-all border ${
            activeTab === 'gaps'
              ? 'bg-blue-600 border-blue-500 text-white shadow-lg shadow-blue-600/40'
              : 'bg-slate-800 border-slate-700 text-slate-300 hover:bg-slate-700'
          }`}
        >
          <i className="fa-solid fa-triangle-exclamation mr-2"></i>3. Identified System Gaps
        </button>
        <button
          onClick={() => setActiveTab('roadmap')}
          className={`px-4 py-2.5 rounded-lg text-sm font-bold transition-all border ${
            activeTab === 'roadmap'
              ? 'bg-blue-600 border-blue-500 text-white shadow-lg shadow-blue-600/40'
              : 'bg-slate-800 border-slate-700 text-slate-300 hover:bg-slate-700'
          }`}
        >
          <i className="fa-solid fa-rocket mr-2"></i>4. Strategic Scale Suggestions
        </button>
      </div>

      {/* Tab 1: Structure */}
      {activeTab === 'structure' && (
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
            <h2 className="text-lg font-bold text-sky-400 mb-4 flex items-center gap-2">
              <i className="fa-solid fa-crown"></i> 1. MNR (MyntReal Core & Brand Ecosystem)
            </h2>
            <div className="bg-slate-950 border border-slate-800 rounded-lg p-4 mb-4">
              <h3 className="text-sm font-bold text-blue-400 mb-2">Executive Dashboard & Segments</h3>
              <ul className="space-y-2 text-sm text-slate-200">
                <li className="flex justify-between items-center border-b border-slate-800/80 pb-1">
                  <span>Executive Dashboard & Trends</span>
                  <code className="text-xs bg-slate-800 px-2 py-0.5 rounded text-sky-300 font-mono">/staff/executive-dashboard</code>
                </li>
                <li className="flex justify-between items-center border-b border-slate-800/80 pb-1">
                  <span>Solar Energy Segment Pipeline</span>
                  <code className="text-xs bg-slate-800 px-2 py-0.5 rounded text-sky-300 font-mono">/staff/solar-leads</code>
                </li>
                <li className="flex justify-between items-center border-b border-slate-800/80 pb-1">
                  <span>EV B2B & EV B2C Vehicles</span>
                  <code className="text-xs bg-slate-800 px-2 py-0.5 rounded text-sky-300 font-mono">/staff/ev-b2b-leads</code>
                </li>
              </ul>
            </div>
          </div>

          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
            <h2 className="text-lg font-bold text-emerald-400 mb-4 flex items-center gap-2">
              <i className="fa-solid fa-city"></i> 2. VGK4U Enterprise & Vendor Ecosystem
            </h2>
            <div className="bg-slate-950 border border-slate-800 rounded-lg p-4 mb-4">
              <h3 className="text-sm font-bold text-emerald-400 mb-2">Vendor Master & Marketplace</h3>
              <ul className="space-y-2 text-sm text-slate-200">
                <li className="flex justify-between items-center border-b border-slate-800/80 pb-1">
                  <span>Vendor Master & Categories</span>
                  <code className="text-xs bg-slate-800 px-2 py-0.5 rounded text-sky-300 font-mono">/staff/vgk/vendors</code>
                </li>
                <li className="tree-item flex justify-between items-center border-b border-slate-800/80 pb-1">
                  <span>Vendor Products Marketplace</span>
                  <code className="text-xs bg-slate-800 px-2 py-0.5 rounded text-sky-300 font-mono">/staff/vgk/vendor-products</code>
                </li>
              </ul>
            </div>
          </div>
        </div>
      )}

      {/* Tab 2: Program */}
      {activeTab === 'program' && (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
          <h2 className="text-lg font-bold text-blue-400 mb-4">
            System Architecture Diagram (Dual-Stack Next.js 14 + FastAPI)
          </h2>
          <div className="mermaid bg-slate-950 p-6 rounded-xl border border-slate-800">
            {`graph TD
              Client["Web / Mobile Browser"] --> NextJS["Next.js 14 App Router (Port 5000)"]
              NextJS -->|API Proxy /api/v1| FastAPI["Python FastAPI Backend (Port 8000)"]
              FastAPI --> DB[("PostgreSQL Database")]
              FastAPI --> S3["AWS S3 Object Storage"]`}
          </div>
        </div>
      )}

      {/* Tab 3: Gaps */}
      {activeTab === 'gaps' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="bg-red-950/20 border-l-4 border-red-500 border border-red-900/40 rounded-xl p-5">
            <h3 className="text-md font-bold text-white mb-2">1. Legacy Monolithic HTML</h3>
            <p className="text-sm text-slate-200">Preloading 400+ HTML files in memory in `server.js` vs React components.</p>
          </div>
          <div className="bg-amber-950/20 border-l-4 border-amber-500 border border-amber-900/40 rounded-xl p-5">
            <h3 className="text-md font-bold text-white mb-2">2. AWS 1GB RAM Budget</h3>
            <p className="text-sm text-slate-200">Restricting Uvicorn to single worker process to stay under micro RAM limit.</p>
          </div>
        </div>
      )}

      {/* Tab 4: Roadmap */}
      {activeTab === 'roadmap' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="bg-emerald-950/20 border-l-4 border-emerald-500 border border-emerald-900/40 rounded-xl p-5">
            <h3 className="text-md font-bold text-white mb-2">1. Next.js 14 SSR Migration (Active Phase)</h3>
            <p className="text-sm text-slate-200">Migrating high-traffic routes to React Server Components with TypeScript.</p>
          </div>
        </div>
      )}
    </main>
  );
}
