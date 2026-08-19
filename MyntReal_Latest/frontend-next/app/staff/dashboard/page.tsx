"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useStaffAuth } from "@/contexts/StaffAuthContext";
import api from "@/lib/api";

export default function StaffDashboardPage() {
  const { user } = useStaffAuth();
  const [snapshot, setSnapshot] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!user) return;

    const fetchSnapshot = async () => {
      try {
        setLoading(true);
        // Uses the Snapshot backend router which aggregates overall metrics
        const res = await api.get(`/staff/snapshot/overview?from_date=${new Date().toISOString().split('T')[0]}`);
        if (res.data) {
          // If the endpoint returns an array for all employees, find current user
          if (Array.isArray(res.data)) {
            const me = res.data.find(x => x.employee_id === user.id) || res.data[0];
            setSnapshot(me);
          } else {
            setSnapshot(res.data);
          }
        }
      } catch (err) {
        console.warn("Failed to fetch ops snapshot", err);
      } finally {
        setLoading(false);
      }
    };

    fetchSnapshot();
  }, [user]);

  if (loading) {
    return (
      <div className="min-h-[80vh] flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <i className="fas fa-circle-notch fa-spin text-4xl text-blue-500"></i>
          <p className="text-slate-500 font-medium">Loading Operations Snapshot...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 lg:p-10 max-w-[1600px] mx-auto bg-slate-50 min-h-screen">
      
      {/* Header */}
      <div className="bg-white rounded-3xl p-8 shadow-sm border border-slate-200 mb-8 relative overflow-hidden flex flex-col md:flex-row justify-between items-center gap-6">
        <div className="absolute top-0 left-0 w-64 h-64 bg-blue-50 rounded-full blur-3xl opacity-60 -ml-10 -mt-10 pointer-events-none"></div>
        <div className="absolute bottom-0 right-10 w-48 h-48 bg-purple-50 rounded-full blur-3xl opacity-60 -mb-10 pointer-events-none"></div>
        
        <div className="relative z-10 w-full">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-50 border border-blue-100 text-blue-700 text-xs font-bold uppercase tracking-wider mb-4">
            <span className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse"></span>
            Ops Command Center
          </div>
          <h1 className="text-3xl md:text-4xl font-black text-slate-900 tracking-tight mb-2">
            Welcome back, {user?.name || user?.first_name || 'Staff Member'}!
          </h1>
          <p className="text-slate-600 text-lg">
            Role: <span className="font-bold text-blue-600 uppercase text-sm tracking-widest">{user?.role || 'Staff'}</span> 
            <span className="mx-2 text-slate-300">|</span> 
            Department: <span className="font-bold text-slate-700">{user?.department || 'Operations'}</span>
          </p>
        </div>
        
        <div className="relative z-10 flex gap-4 w-full md:w-auto shrink-0">
          <Link href="/staff/tasks" className="px-6 py-3.5 bg-slate-900 text-white font-bold rounded-xl shadow-lg shadow-slate-900/20 hover:bg-slate-800 transition-all flex items-center justify-center gap-2">
            <i className="fas fa-check-square"></i> My Tasks
          </Link>
        </div>
      </div>

      {/* KPI Grid from Snapshot */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-10">
        
        <div className="bg-white rounded-2xl p-6 shadow-sm border border-slate-200 relative overflow-hidden group">
          <div className="flex justify-between items-start mb-4 relative z-10">
            <div className="w-12 h-12 bg-blue-100 text-blue-600 rounded-xl flex items-center justify-center text-xl shadow-inner group-hover:scale-110 transition-transform">
              <i className="fas fa-bullseye"></i>
            </div>
          </div>
          <h3 className="text-slate-500 font-semibold text-sm mb-1 relative z-10">KRA Score Today</h3>
          <p className="text-3xl font-black text-slate-900 relative z-10">{snapshot?.kra_score || 0}%</p>
        </div>

        <div className="bg-white rounded-2xl p-6 shadow-sm border border-slate-200 relative overflow-hidden group">
          <div className="flex justify-between items-start mb-4 relative z-10">
            <div className="w-12 h-12 bg-indigo-100 text-indigo-600 rounded-xl flex items-center justify-center text-xl shadow-inner group-hover:scale-110 transition-transform">
              <i className="fas fa-phone-alt"></i>
            </div>
          </div>
          <h3 className="text-slate-500 font-semibold text-sm mb-1 relative z-10">Calls Made</h3>
          <p className="text-3xl font-black text-slate-900 relative z-10">{snapshot?.calls_made || 0}</p>
        </div>

        <div className="bg-white rounded-2xl p-6 shadow-sm border border-slate-200 relative overflow-hidden group">
          <div className="flex justify-between items-start mb-4 relative z-10">
            <div className="w-12 h-12 bg-emerald-100 text-emerald-600 rounded-xl flex items-center justify-center text-xl shadow-inner group-hover:scale-110 transition-transform">
              <i className="fas fa-hand-holding-usd"></i>
            </div>
          </div>
          <h3 className="text-slate-500 font-semibold text-sm mb-1 relative z-10">Deals Closed</h3>
          <p className="text-3xl font-black text-slate-900 relative z-10">{snapshot?.deals_closed || 0}</p>
        </div>

        <div className="bg-white rounded-2xl p-6 shadow-sm border border-slate-200 relative overflow-hidden group">
          <div className="flex justify-between items-start mb-4 relative z-10">
            <div className="w-12 h-12 bg-amber-100 text-amber-600 rounded-xl flex items-center justify-center text-xl shadow-inner group-hover:scale-110 transition-transform">
              <i className="fas fa-tasks"></i>
            </div>
          </div>
          <h3 className="text-slate-500 font-semibold text-sm mb-1 relative z-10">Tasks Completed</h3>
          <p className="text-3xl font-black text-slate-900 relative z-10">{snapshot?.tasks_completed || 0}</p>
        </div>

      </div>

      <h2 className="text-2xl font-black text-slate-900 tracking-tight mb-6">Quick Actions</h2>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Link href="/staff/my-leads" className="bg-white border border-slate-200 rounded-2xl p-6 hover:shadow-md hover:border-blue-300 transition-all block">
          <div className="w-10 h-10 bg-blue-50 text-blue-600 rounded-lg flex items-center justify-center text-lg mb-4">
            <i className="fas fa-users"></i>
          </div>
          <h3 className="font-bold text-slate-900 mb-1">CRM Hub</h3>
          <p className="text-sm text-slate-500">Manage leads, calls, and sales pipeline.</p>
        </Link>
        <Link href="/staff/hr/attendance" className="bg-white border border-slate-200 rounded-2xl p-6 hover:shadow-md hover:border-purple-300 transition-all block">
          <div className="w-10 h-10 bg-purple-50 text-purple-600 rounded-lg flex items-center justify-center text-lg mb-4">
            <i className="fas fa-clock"></i>
          </div>
          <h3 className="font-bold text-slate-900 mb-1">Attendance & Leave</h3>
          <p className="text-sm text-slate-500">Log time, request leaves, and view shifts.</p>
        </Link>
        <Link href="/staff/accounts/general-ledger" className="bg-white border border-slate-200 rounded-2xl p-6 hover:shadow-md hover:border-emerald-300 transition-all block">
          <div className="w-10 h-10 bg-emerald-50 text-emerald-600 rounded-lg flex items-center justify-center text-lg mb-4">
            <i className="fas fa-file-invoice-dollar"></i>
          </div>
          <h3 className="font-bold text-slate-900 mb-1">Finance & Accounts</h3>
          <p className="text-sm text-slate-500">Access vouchers, ledgers, and payables.</p>
        </Link>
      </div>

    </div>
  );
}
