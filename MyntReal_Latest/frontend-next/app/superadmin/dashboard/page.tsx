"use client";

import React, { useState, useEffect } from "react";
import { useSuperAdminAuth } from "@/contexts/SuperAdminAuthContext";
import api from "@/lib/api";
import { Shield, Activity, Users, CreditCard, UserPlus, FileText, ChevronRight, Terminal, Server, Database, Key } from "lucide-react";

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
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="flex flex-col items-center gap-4">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-rose-600"></div>
          <p className="text-slate-500 font-medium animate-pulse">Authenticating root privileges...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8 bg-slate-50 min-h-[calc(100vh-64px)]">
      
      <div className="rounded-2xl bg-white border border-slate-200 p-8 shadow-sm relative overflow-hidden flex flex-col md:flex-row justify-between items-center gap-6">
        <div className="absolute top-0 right-0 w-96 h-96 bg-rose-50 rounded-full blur-3xl opacity-60 -mr-20 -mt-20 pointer-events-none"></div>
        
        <div className="relative z-10 w-full">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-rose-50 border border-rose-100 text-rose-700 text-xs font-bold uppercase tracking-wider mb-4">
            <span className="w-2 h-2 rounded-full bg-rose-500 animate-pulse"></span>
            ROOT ACCESS GRANTED
          </div>
          <h1 className="text-4xl font-extrabold text-slate-900 tracking-tight mb-2">
            System Core Status
          </h1>
          <p className="text-slate-600 text-lg">
            Welcome back, <span className="font-semibold text-rose-600">Administrator</span>. All critical services are online.
          </p>
        </div>
        
        <div className="relative z-10 flex flex-col gap-3 w-full md:w-auto shrink-0 bg-slate-50 p-4 rounded-xl border border-slate-100">
          <div className="flex items-center justify-between gap-6 text-sm">
            <div className="flex items-center gap-2 text-slate-600 font-medium"><Database className="h-4 w-4" /> Primary DB</div>
            <div className={`font-bold ${dbStatus === 'ONLINE' ? 'text-emerald-600' : 'text-rose-600'}`}>{dbStatus}</div>
          </div>
          <div className="flex items-center justify-between gap-6 text-sm">
            <div className="flex items-center gap-2 text-slate-600 font-medium"><Server className="h-4 w-4" /> Redis Cache</div>
            <div className={`font-bold ${redisStatus === 'ONLINE' ? 'text-emerald-600' : 'text-rose-600'}`}>{redisStatus}</div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {[
          { title: "Total Users", value: stats?.total_users || 0, icon: Users, color: "text-blue-600" },
          { title: "Pending Withdrawals", value: stats?.pending_withdrawals || 0, icon: CreditCard, color: "text-rose-600" },
          { title: "Unclaimed Leads", value: stats?.unclaimed_leads || 0, icon: UserPlus, color: "text-indigo-600" },
          { title: "Pending Awards", value: stats?.pending_super_admin_decision || 0, icon: FileText, color: "text-amber-600" }
        ].map((stat, i) => (
          <div key={i} className="rounded-xl border bg-white p-6 shadow-sm hover:shadow-md transition-shadow">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-medium text-slate-500">{stat.title}</h3>
              <stat.icon className={`h-5 w-5 ${stat.color}`} />
            </div>
            <div className="text-3xl font-bold text-slate-900">{stat.value}</div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 flex-1">
        
        <div className="lg:col-span-2 rounded-2xl bg-[#0B0F19] border border-slate-800 shadow-xl overflow-hidden flex flex-col h-[400px]">
          <div className="p-4 border-b border-slate-800 flex justify-between items-center bg-[#0B0F19]/50 backdrop-blur">
            <h2 className="font-semibold text-slate-200 text-sm flex items-center gap-2">
              <Terminal className="h-4 w-4 text-rose-500" /> Security & Audit Trail
            </h2>
            <div className="inline-flex items-center gap-2 text-xs font-mono text-emerald-400 bg-emerald-400/10 px-2 py-1 rounded">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span> LIVE
            </div>
          </div>
          <div className="p-4 flex-1 overflow-y-auto font-mono text-sm space-y-3">
            {securityLogs.map((log, i) => (
              <div key={i} className="flex gap-3 text-slate-400 items-start hover:bg-white/5 p-1.5 -mx-1.5 rounded transition-colors">
                <span className="text-slate-600 shrink-0">[{log.time}]</span>
                <span className={`shrink-0 font-semibold ${
                  log.level === 'CRITICAL' ? 'text-rose-500' :
                  log.level === 'WARN' ? 'text-amber-500' :
                  'text-blue-400'
                }`}>
                  {log.level.padEnd(8)}
                </span>
                <span className="break-all text-slate-300">{log.event}</span>
              </div>
            ))}
            <div className="flex gap-3 text-slate-600 items-center mt-4">
              <span className="animate-pulse font-bold text-lg leading-none">_</span>
              <span>Awaiting new events...</span>
            </div>
          </div>
        </div>

        <div className="rounded-2xl border bg-white shadow-sm p-6 flex flex-col h-[400px]">
          <h2 className="font-bold text-slate-900 mb-6 text-sm uppercase tracking-wider flex items-center gap-2">
            <Key className="h-4 w-4 text-slate-400" /> Root Functions
          </h2>
          <div className="space-y-3 flex-1 overflow-auto pr-2">
            {[
              { label: 'Awards Override', href: '/superadmin/awards', icon:  color: 'text-amber-600', bg: 'bg-amber-50' },
              { label: 'Network Approvals', href: '/superadmin/network/approvals', icon: Users, color: 'text-indigo-600', bg: 'bg-indigo-50' },
              { label: 'Supreme Finance', href: '/superadmin/finance/supreme', icon: CreditCard, color: 'text-emerald-600', bg: 'bg-emerald-50' },
              { label: 'Global Config', href: '/superadmin/config/popups', icon: Shield, color: 'text-rose-600', bg: 'bg-rose-50' }
            ].map((link, i) => (
              <a key={i} href={link.href} className="flex items-center justify-between p-4 rounded-xl border border-slate-100 hover:border-slate-200 hover:bg-slate-50 transition-all group shadow-sm">
                <div className="flex items-center gap-4">
                  <div className={`w-10 h-10 rounded-lg ${link.bg} ${link.color} flex items-center justify-center`}>
                    <link.icon className="h-5 w-5" />
                  </div>
                  <span className="font-semibold text-slate-700 text-sm">{link.label}</span>
                </div>
                <ChevronRight className="h-5 w-5 text-slate-300 group-hover:text-slate-600 transition-colors" />
              </a>
            ))}
          </div>
        </div>

      </div>
    </div>
  );
}
