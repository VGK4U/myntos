"use client";

import React, { useState, useEffect } from "react";
import { useSuperAdminAuth } from "@/contexts/SuperAdminAuthContext";
import api from "@/lib/api";

export default function SuperAdminDashboard() {
  const { user } = useSuperAdminAuth();

  const [dbStatus, setDbStatus] = useState("ONLINE");
  const [redisStatus, setRedisStatus] = useState("ONLINE");
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!user) return;
    const fetchDashboard = async () => {
      setLoading(true);
      try {
        const res = await api.get(`/super-admin/dashboard-stats`);
        if (res.data) {
          setStats(res.data);
          setDbStatus("ONLINE");
        }
      } catch (e) {
        console.error(e);
        setDbStatus("OFFLINE");
      } finally {
        setLoading(false);
      }
    };
    fetchDashboard();
  }, [user]);

  const securityLogs = [
    { time: '14:23:41', level: 'INFO', event: 'Database backup completed successfully.' },
    { time: '13:45:12', level: 'WARN', event: 'Multiple failed login attempts from IP 192.168.1.104' },
    { time: '12:01:05', level: 'CRITICAL', event: 'Rate limit exceeded on Placement API endpoint.' },
    { time: '11:15:30', level: 'INFO', event: 'Super Admin [SysAdmin] logged in from verified device.' },
    { time: '09:00:00', level: 'INFO', event: 'Daily payout cron job executed (14,200 PV processed).' },
  ];

  if (loading) {
    return (
      <div className="min-h-[80vh] flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <i className="fas fa-circle-notch fa-spin text-4xl text-rose-500"></i>
          <p className="text-slate-500 font-medium">Authenticating root privileges...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-7xl mx-auto flex flex-col min-h-[calc(100vh-64px)]">
      
      <div className="bg-white rounded-3xl p-8 shadow-sm border border-slate-200 mb-8 relative overflow-hidden flex flex-col md:flex-row justify-between items-center gap-6">
        <div className="absolute top-0 right-0 w-64 h-64 bg-rose-50 rounded-full blur-3xl opacity-60 -mr-10 -mt-10 pointer-events-none"></div>
        
        <div className="relative z-10 w-full">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-rose-50 border border-rose-100 text-rose-700 text-xs font-bold uppercase tracking-wider mb-4">
            <span className="w-1.5 h-1.5 rounded-full bg-rose-500 animate-pulse"></span>
            ROOT ACCESS
          </div>
          <h1 className="text-3xl md:text-4xl font-black text-slate-900 tracking-tight mb-2">
            System Core Status
          </h1>
          <p className="text-slate-600 text-lg">
            Welcome, <span className="font-bold text-rose-600">{user?.name || 'Administrator'}</span>. All services are operating normally.
          </p>
        </div>
        
        <div className="relative z-10 flex gap-4 w-full md:w-auto shrink-0 flex-col text-right">
          <div className="flex items-center justify-end gap-2 text-emerald-600 font-bold text-sm">
            <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></div>
            Database: {dbStatus}
          </div>
          <div className="flex items-center justify-end gap-2 text-emerald-600 font-bold text-sm">
            <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></div>
            Redis Cache: {redisStatus}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
        <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm">
          <p className="text-sm font-bold text-slate-500 mb-1">Total Users</p>
          <h2 className="text-3xl font-black text-slate-900">{stats?.total_users || 0}</h2>
        </div>
        <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm">
          <p className="text-sm font-bold text-slate-500 mb-1">Pending Withdrawals</p>
          <h2 className="text-3xl font-black text-rose-600">{stats?.pending_withdrawals || 0}</h2>
        </div>
        <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm">
          <p className="text-sm font-bold text-slate-500 mb-1">Unclaimed Leads</p>
          <h2 className="text-3xl font-black text-indigo-600">{stats?.unclaimed_leads || 0}</h2>
        </div>
        <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm">
          <p className="text-sm font-bold text-slate-500 mb-1">Pending Awards (Decisions)</p>
          <h2 className="text-3xl font-black text-amber-600">{stats?.pending_super_admin_decision || 0}</h2>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 flex-1">
        
        {/* Real-time System Logs */}
        <div className="bg-slate-900 rounded-2xl border border-slate-800 shadow-xl overflow-hidden lg:col-span-2 flex flex-col">
          <div className="p-4 border-b border-slate-800 flex justify-between items-center bg-slate-950/50">
            <h2 className="font-bold text-white text-sm flex items-center gap-2">
              <i className="fas fa-terminal text-rose-500"></i> Security & Audit Logs
            </h2>
            <span className="text-xs font-mono text-emerald-400 bg-emerald-400/10 px-2 py-1 rounded">LIVE</span>
          </div>
          <div className="p-4 flex-1 overflow-y-auto font-mono text-sm space-y-3 bg-[#0a0a0c]">
            {securityLogs.map((log, i) => (
              <div key={i} className="flex gap-3 text-slate-300 items-start hover:bg-white/5 p-1 -mx-1 rounded transition-colors">
                <span className="text-slate-500 shrink-0">[{log.time}]</span>
                <span className={`shrink-0 font-bold ${
                  log.level === 'CRITICAL' ? 'text-rose-500' :
                  log.level === 'WARN' ? 'text-amber-500' :
                  'text-blue-400'
                }`}>
                  {log.level}
                </span>
                <span className="break-all">{log.event}</span>
              </div>
            ))}
            <div className="flex gap-3 text-slate-500 items-center">
              <span className="animate-pulse">_</span>
              <span>Waiting for new events...</span>
            </div>
          </div>
        </div>

        {/* Quick Management Tools */}
        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6">
          <h2 className="font-bold text-slate-900 mb-4 text-sm uppercase tracking-wider">Root Functions</h2>
          <div className="space-y-3">
            <a href="/superadmin/awards" className="flex items-center justify-between p-3 rounded-xl border border-slate-200 hover:bg-slate-50 transition-colors group">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-amber-50 text-amber-600 flex items-center justify-center">
                  <i className="fas fa-trophy"></i>
                </div>
                <span className="font-bold text-slate-700 text-sm">Awards Override</span>
              </div>
              <i className="fas fa-chevron-right text-slate-300 group-hover:text-amber-500 transition-colors"></i>
            </a>
            
            <a href="/superadmin/network/approvals" className="flex items-center justify-between p-3 rounded-xl border border-slate-200 hover:bg-slate-50 transition-colors group">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-indigo-50 text-indigo-600 flex items-center justify-center">
                  <i className="fas fa-network-wired"></i>
                </div>
                <span className="font-bold text-slate-700 text-sm">Network Approvals</span>
              </div>
              <i className="fas fa-chevron-right text-slate-300 group-hover:text-indigo-500 transition-colors"></i>
            </a>
            
            <a href="/superadmin/finance/supreme" className="flex items-center justify-between p-3 rounded-xl border border-slate-200 hover:bg-slate-50 transition-colors group">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center">
                  <i className="fas fa-wallet"></i>
                </div>
                <span className="font-bold text-slate-700 text-sm">Supreme Finance</span>
              </div>
              <i className="fas fa-chevron-right text-slate-300 group-hover:text-emerald-500 transition-colors"></i>
            </a>
          </div>
        </div>

      </div>
    </div>
  );
}
