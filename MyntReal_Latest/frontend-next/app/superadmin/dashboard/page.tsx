"use client";

import React, { useState, useEffect } from "react";
import { useSuperAdminAuth } from "@/contexts/SuperAdminAuthContext";
import { getApiUrl } from "@/lib/api";

export default function SuperAdminDashboard() {
  const { user } = useSuperAdminAuth();

  const [dbStatus, setDbStatus] = useState("ONLINE");
  const [redisStatus, setRedisStatus] = useState("ONLINE");
  const [activeUsers, setActiveUsers] = useState(0);
  const [cpuLoad, setCpuLoad] = useState(24);
  const [memoryUsage, setMemoryUsage] = useState(62);
  const { token } = useSuperAdminAuth();

  useEffect(() => {
    if (!token) return;
    const fetchDashboard = async () => {
      try {
        const res = await fetch(`${getApiUrl()}/api/v1/super-admin/dashboard`, {
          headers: { "Authorization": `Bearer ${token}` }
        });
        if (res.ok) {
          const json = await res.json();
          if (json.data) {
            setActiveUsers(json.data.users?.active || json.data.users?.total || 0);
            setDbStatus(json.data.system?.database_status === "Connected" ? "ONLINE" : "OFFLINE");
          }
        }
      } catch (e) {
        console.error(e);
      }
    };
    fetchDashboard();
  }, [token]);

  const securityLogs = [
    { time: '14:23:41', level: 'INFO', event: 'Database backup completed successfully.' },
    { time: '13:45:12', level: 'WARN', event: 'Multiple failed login attempts from IP 192.168.1.104' },
    { time: '12:01:05', level: 'CRITICAL', event: 'Rate limit exceeded on Placement API endpoint.' },
    { time: '11:15:30', level: 'INFO', event: 'Super Admin [SysAdmin] logged in from verified device.' },
    { time: '09:00:00', level: 'INFO', event: 'Daily payout cron job executed (14,200 PV processed).' },
  ];

  return (
    <div className="p-6 max-w-7xl mx-auto flex flex-col h-[calc(100vh-64px)]">
      <div className="flex justify-between items-end mb-6 shrink-0">
        <div>
          <h1 className="text-3xl font-black text-gray-900 tracking-tight uppercase">System Core Status</h1>
          <p className="text-xs text-gray-500 mt-2 font-bold uppercase tracking-widest">Global Overview & Health Metrics</p>
        </div>
        <div className="flex space-x-3">
          <button className="px-4 py-2 bg-red-600 text-white font-bold rounded shadow-sm hover:bg-red-700 transition-colors uppercase text-xs tracking-wider">
            <i className="fas fa-power-off mr-2"></i> Maintenance Mode
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4 mb-6 shrink-0">
        
        {/* Status Panels */}
        <div className="bg-[#111827] border border-[#1F2937] p-5 rounded-lg text-white shadow-sm flex flex-col justify-between">
          <div className="flex justify-between items-center mb-2">
            <span className="text-[10px] font-bold text-gray-400 uppercase tracking-widest">Main Database</span>
            <i className="fas fa-database text-gray-500"></i>
          </div>
          <div className="flex items-center">
            <span className="w-2 h-2 rounded-full bg-green-500 mr-2 animate-pulse"></span>
            <span className="text-xl font-bold tracking-widest text-green-400">{dbStatus}</span>
          </div>
          <p className="text-[9px] text-gray-500 mt-2 font-mono">Ping: 12ms | Queries: 450/s</p>
        </div>

        <div className="bg-[#111827] border border-[#1F2937] p-5 rounded-lg text-white shadow-sm flex flex-col justify-between">
          <div className="flex justify-between items-center mb-2">
            <span className="text-[10px] font-bold text-gray-400 uppercase tracking-widest">Redis Cache</span>
            <i className="fas fa-memory text-gray-500"></i>
          </div>
          <div className="flex items-center">
            <span className="w-2 h-2 rounded-full bg-green-500 mr-2 animate-pulse"></span>
            <span className="text-xl font-bold tracking-widest text-green-400">{redisStatus}</span>
          </div>
          <p className="text-[9px] text-gray-500 mt-2 font-mono">Hit Rate: 98.4%</p>
        </div>

        <div className="bg-white border border-gray-200 p-5 rounded-lg shadow-sm flex flex-col justify-between">
          <div className="flex justify-between items-center mb-2">
            <span className="text-[10px] font-bold text-gray-500 uppercase tracking-widest">Active Users</span>
            <i className="fas fa-users text-gray-400"></i>
          </div>
          <span className="text-3xl font-black text-gray-900">{activeUsers}</span>
          <p className="text-[9px] text-gray-500 mt-2 font-mono">+12% from last hour</p>
        </div>

        <div className="bg-white border border-gray-200 p-5 rounded-lg shadow-sm flex flex-col justify-between">
          <div className="flex justify-between items-center mb-2">
            <span className="text-[10px] font-bold text-gray-500 uppercase tracking-widest">CPU Load</span>
            <i className="fas fa-microchip text-gray-400"></i>
          </div>
          <div className="flex items-baseline gap-1">
            <span className="text-3xl font-black text-gray-900">{cpuLoad}</span>
            <span className="text-sm font-bold text-gray-500">%</span>
          </div>
          <div className="w-full bg-gray-200 h-1 mt-2 rounded-full">
            <div className={`h-1 rounded-full ${cpuLoad > 80 ? 'bg-red-500' : 'bg-green-500'}`} style={{ width: `${cpuLoad}%` }}></div>
          </div>
        </div>

        <div className="bg-white border border-gray-200 p-5 rounded-lg shadow-sm flex flex-col justify-between">
          <div className="flex justify-between items-center mb-2">
            <span className="text-[10px] font-bold text-gray-500 uppercase tracking-widest">Memory Usage</span>
            <i className="fas fa-server text-gray-400"></i>
          </div>
          <div className="flex items-baseline gap-1">
            <span className="text-3xl font-black text-gray-900">{memoryUsage}</span>
            <span className="text-sm font-bold text-gray-500">%</span>
          </div>
          <div className="w-full bg-gray-200 h-1 mt-2 rounded-full">
            <div className={`h-1 rounded-full ${memoryUsage > 85 ? 'bg-red-500' : memoryUsage > 60 ? 'bg-yellow-500' : 'bg-green-500'}`} style={{ width: `${memoryUsage}%` }}></div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 flex-1 min-h-0">
        
        {/* Real-time System Logs Terminal */}
        <div className="lg:col-span-2 bg-[#0B0F19] rounded-lg border border-[#1F2937] flex flex-col shadow-xl overflow-hidden">
          <div className="bg-[#111827] px-4 py-3 flex justify-between items-center border-b border-[#1F2937]">
            <div className="flex items-center gap-2">
              <i className="fas fa-terminal text-gray-500 text-xs"></i>
              <span className="text-xs font-bold text-gray-300 uppercase tracking-widest">Live Security Feed</span>
            </div>
            <div className="flex gap-1.5">
              <div className="w-2.5 h-2.5 rounded-full bg-gray-600"></div>
              <div className="w-2.5 h-2.5 rounded-full bg-gray-600"></div>
              <div className="w-2.5 h-2.5 rounded-full bg-gray-600"></div>
            </div>
          </div>
          
          <div className="flex-1 p-4 overflow-y-auto font-mono text-[11px] leading-relaxed">
            {securityLogs.map((log, idx) => (
              <div key={idx} className="mb-2 flex">
                <span className="text-gray-500 mr-3 w-16 shrink-0">[{log.time}]</span>
                <span className={`font-bold mr-3 w-16 shrink-0 ${
                  log.level === 'INFO' ? 'text-blue-400' : 
                  log.level === 'WARN' ? 'text-yellow-400' : 
                  'text-red-500'
                }`}>
                  {log.level}
                </span>
                <span className="text-gray-300">{log.event}</span>
              </div>
            ))}
            <div className="mt-4 flex items-center text-green-400 animate-pulse">
              <span className="mr-2">&gt;</span>
              <span>_</span>
            </div>
          </div>
        </div>

        {/* Action Center */}
        <div className="bg-white rounded-lg border border-gray-200 shadow-sm flex flex-col p-6">
          <h3 className="text-sm font-black text-gray-900 uppercase tracking-widest mb-6 border-b border-gray-100 pb-2">
            Critical Actions
          </h3>
          
          <div className="space-y-4">
            <button className="w-full text-left p-4 rounded bg-gray-50 border border-gray-200 hover:border-gray-300 hover:bg-gray-100 transition-colors group">
              <div className="flex items-center justify-between mb-1">
                <span className="font-bold text-gray-900 text-sm">Force Sync Tree</span>
                <i className="fas fa-sync-alt text-gray-400 group-hover:text-gray-600"></i>
              </div>
              <p className="text-xs text-gray-500">Recalculate PV and matching bonuses for all members immediately.</p>
            </button>

            <button className="w-full text-left p-4 rounded bg-gray-50 border border-gray-200 hover:border-gray-300 hover:bg-gray-100 transition-colors group">
              <div className="flex items-center justify-between mb-1">
                <span className="font-bold text-gray-900 text-sm">Clear Cache</span>
                <i className="fas fa-broom text-gray-400 group-hover:text-gray-600"></i>
              </div>
              <p className="text-xs text-gray-500">Flush Redis cache to resolve state inconsistencies.</p>
            </button>

            <button className="w-full text-left p-4 rounded bg-red-50 border border-red-200 hover:bg-red-100 transition-colors group mt-auto">
              <div className="flex items-center justify-between mb-1">
                <span className="font-bold text-red-900 text-sm">Emergency Lockdown</span>
                <i className="fas fa-lock text-red-500"></i>
              </div>
              <p className="text-xs text-red-700">Suspend all member logins and transactions immediately.</p>
            </button>
          </div>
        </div>

      </div>
    </div>
  );
}
