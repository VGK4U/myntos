"use client";

import { useState, useEffect } from "react";

export default function MyAttendance() {
  const [currentTime, setCurrentTime] = useState("");
  const [isPunchedIn, setIsPunchedIn] = useState(false);

  useEffect(() => {
    const timer = setInterval(() => {
      const now = new Date();
      setCurrentTime(now.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit' }));
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  const togglePunch = () => {
    setIsPunchedIn(!isPunchedIn);
  };

  const weekLog = [
    { date: "Mon, Aug 10", in: "09:02 AM", out: "06:15 PM", hours: "9h 13m", status: "Present" },
    { date: "Tue, Aug 11", in: "08:55 AM", out: "06:05 PM", hours: "9h 10m", status: "Present" },
    { date: "Wed, Aug 12", in: "09:15 AM", out: "06:30 PM", hours: "9h 15m", status: "Late" },
    { date: "Thu, Aug 13", in: "09:00 AM", out: "-", hours: "-", status: "Active" },
    { date: "Fri, Aug 14", in: "-", out: "-", hours: "-", status: "Upcoming" },
  ];

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 tracking-tight">My Attendance</h1>
          <p className="text-sm text-gray-500 mt-1">Track your daily In/Out times and leave balances.</p>
        </div>
        <div className="flex items-center gap-3">
          <button className="px-4 py-2 bg-white border border-gray-200 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-50 transition-colors shadow-sm">
            <i className="fas fa-calendar-alt mr-2"></i> Apply Leave
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Punch In Card */}
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden flex flex-col items-center p-8 relative">
          <div className="absolute top-4 right-4 flex items-center gap-2">
            <span className="relative flex h-3 w-3">
              <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${isPunchedIn ? 'bg-emerald-400' : 'bg-rose-400'}`}></span>
              <span className={`relative inline-flex rounded-full h-3 w-3 ${isPunchedIn ? 'bg-emerald-500' : 'bg-rose-500'}`}></span>
            </span>
            <span className="text-xs font-bold text-gray-500 uppercase tracking-wide">
              {isPunchedIn ? 'On Duty' : 'Off Duty'}
            </span>
          </div>

          <p className="text-sm font-bold text-gray-400 uppercase tracking-widest mt-4">Current Time</p>
          <h2 className="text-5xl font-extrabold text-gray-900 my-4 font-mono tracking-tight">{currentTime || "00:00:00"}</h2>
          <p className="text-sm text-gray-500 mb-8">{new Date().toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}</p>

          <button 
            onClick={togglePunch}
            className={`w-48 h-48 rounded-full flex flex-col items-center justify-center gap-3 text-white transition-all shadow-xl hover:scale-105 active:scale-95 ${
              isPunchedIn 
                ? 'bg-gradient-to-b from-rose-500 to-rose-700 shadow-rose-500/30' 
                : 'bg-gradient-to-b from-emerald-500 to-emerald-700 shadow-emerald-500/30'
            }`}
          >
            <i className={`fas fa-fingerprint text-5xl opacity-90`}></i>
            <span className="text-xl font-bold">{isPunchedIn ? 'PUNCH OUT' : 'PUNCH IN'}</span>
          </button>
          
          <div className="mt-8 grid grid-cols-2 gap-8 w-full border-t border-gray-100 pt-6">
            <div className="text-center">
              <p className="text-xs font-medium text-gray-500 uppercase">In Time</p>
              <p className="text-lg font-bold text-gray-900 mt-1">{isPunchedIn ? '09:00 AM' : '--:--'}</p>
            </div>
            <div className="text-center">
              <p className="text-xs font-medium text-gray-500 uppercase">Total Hours</p>
              <p className="text-lg font-bold text-gray-900 mt-1">{isPunchedIn ? '4h 12m' : '0h 0m'}</p>
            </div>
          </div>
        </div>

        {/* Right Side: Week Log & Leave Balances */}
        <div className="lg:col-span-2 space-y-6 flex flex-col">
          
          {/* Leave Balances */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm text-center">
              <h4 className="text-sm font-medium text-gray-500 mb-1">Casual Leave</h4>
              <p className="text-2xl font-bold text-gray-900">4.5</p>
            </div>
            <div className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm text-center">
              <h4 className="text-sm font-medium text-gray-500 mb-1">Sick Leave</h4>
              <p className="text-2xl font-bold text-gray-900">2.0</p>
            </div>
            <div className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm text-center">
              <h4 className="text-sm font-medium text-gray-500 mb-1">Earned Leave</h4>
              <p className="text-2xl font-bold text-gray-900">12.0</p>
            </div>
            <div className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm text-center">
              <h4 className="text-sm font-medium text-gray-500 mb-1">Comp Off</h4>
              <p className="text-2xl font-bold text-gray-900">0.0</p>
            </div>
          </div>

          {/* Week Log */}
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden flex-1">
            <div className="px-6 py-4 border-b border-gray-200 bg-gray-50 flex justify-between items-center">
              <h3 className="text-sm font-bold text-gray-900 uppercase tracking-wider">This Week's Log</h3>
              <a href="#" className="text-sm font-medium text-brand-warning hover:text-amber-600 transition-colors">View Month</a>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="bg-white border-b border-gray-100">
                    <th className="px-6 py-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Date</th>
                    <th className="px-6 py-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Punch In</th>
                    <th className="px-6 py-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Punch Out</th>
                    <th className="px-6 py-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Total Hrs</th>
                    <th className="px-6 py-4 text-xs font-bold text-gray-500 uppercase tracking-wider text-right">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {weekLog.map((log, idx) => (
                    <tr key={idx} className="hover:bg-gray-50/50 transition-colors">
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{log.date}</td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">{log.in}</td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">{log.out}</td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 font-medium">{log.hours}</td>
                      <td className="px-6 py-4 whitespace-nowrap text-right">
                        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold ${
                          log.status === 'Present' ? 'bg-emerald-100 text-emerald-800' :
                          log.status === 'Late' ? 'bg-amber-100 text-amber-800' :
                          log.status === 'Active' ? 'bg-blue-100 text-blue-800' :
                          'bg-gray-100 text-gray-800'
                        }`}>
                          {log.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
          
        </div>
      </div>
    </div>
  );
}
