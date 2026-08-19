"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useVendorAuth } from "@/contexts/VendorAuthContext";
import api from "@/lib/api";

export default function VendorDashboardPage() {
  const { user } = useVendorAuth();
  
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!user) return;
    
    setLoading(true);
    // Use proper partner dashboard stats endpoint
    api.get('/partner/dashboard/stats')
      .then(res => {
        if (res.data) {
          setStats(res.data);
        }
      })
      .catch(err => console.error("Failed to fetch dashboard stats", err))
      .finally(() => setLoading(false));
  }, [user]);

  if (loading) {
    return (
      <div className="min-h-[80vh] flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <i className="fas fa-circle-notch fa-spin text-4xl text-emerald-500"></i>
          <p className="text-slate-500 font-medium">Loading Vendor Overview...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 lg:p-10 max-w-[1600px] mx-auto bg-slate-50 min-h-screen">
      
      {/* Header */}
      <div className="bg-white rounded-3xl p-8 shadow-sm border border-slate-200 mb-8 relative overflow-hidden flex flex-col md:flex-row justify-between items-center gap-6">
        <div className="absolute top-0 right-0 w-64 h-64 bg-emerald-50 rounded-full blur-3xl opacity-60 -mr-10 -mt-10 pointer-events-none"></div>
        
        <div className="relative z-10 w-full">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-50 border border-emerald-100 text-emerald-700 text-xs font-bold uppercase tracking-wider mb-4">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
            Partner Portal
          </div>
          <h1 className="text-3xl md:text-4xl font-black text-slate-900 tracking-tight mb-2">
            Welcome back, {user?.name || user?.first_name || 'Partner'}!
          </h1>
          <p className="text-slate-600 text-lg">
            Manage your orders, inventory, and walk-ins.
          </p>
        </div>
        
        <div className="relative z-10 flex gap-4 w-full md:w-auto shrink-0">
          <Link href="/vendor/scan" className="px-6 py-3.5 bg-slate-900 text-white font-bold rounded-xl shadow-lg shadow-slate-900/20 hover:bg-slate-800 transition-all flex items-center justify-center gap-2">
            <i className="fas fa-qrcode"></i> Scan Customer
          </Link>
        </div>
      </div>

      {/* KPI Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-10">
        
        <div className="bg-white rounded-2xl p-6 shadow-sm border border-slate-200 relative overflow-hidden group">
          <div className="flex justify-between items-start mb-4 relative z-10">
            <div className="w-12 h-12 bg-emerald-100 text-emerald-600 rounded-xl flex items-center justify-center text-xl shadow-inner group-hover:scale-110 transition-transform">
              <i className="fas fa-shopping-cart"></i>
            </div>
          </div>
          <h3 className="text-slate-500 font-semibold text-sm mb-1 relative z-10">Total Orders</h3>
          <p className="text-3xl font-black text-slate-900 relative z-10">{stats?.total_orders || 0}</p>
        </div>

        <div className="bg-white rounded-2xl p-6 shadow-sm border border-slate-200 relative overflow-hidden group">
          <div className="flex justify-between items-start mb-4 relative z-10">
            <div className="w-12 h-12 bg-blue-100 text-blue-600 rounded-xl flex items-center justify-center text-xl shadow-inner group-hover:scale-110 transition-transform">
              <i className="fas fa-boxes"></i>
            </div>
          </div>
          <h3 className="text-slate-500 font-semibold text-sm mb-1 relative z-10">Pending Fulfillment</h3>
          <p className="text-3xl font-black text-slate-900 relative z-10">{stats?.pending_orders || 0}</p>
        </div>

        <div className="bg-white rounded-2xl p-6 shadow-sm border border-slate-200 relative overflow-hidden group">
          <div className="flex justify-between items-start mb-4 relative z-10">
            <div className="w-12 h-12 bg-indigo-100 text-indigo-600 rounded-xl flex items-center justify-center text-xl shadow-inner group-hover:scale-110 transition-transform">
              <i className="fas fa-file-invoice-dollar"></i>
            </div>
          </div>
          <h3 className="text-slate-500 font-semibold text-sm mb-1 relative z-10">Total Invoices</h3>
          <p className="text-3xl font-black text-slate-900 relative z-10">{stats?.total_invoices || 0}</p>
        </div>

        <div className="bg-white rounded-2xl p-6 shadow-sm border border-slate-200 relative overflow-hidden group">
          <div className="flex justify-between items-start mb-4 relative z-10">
            <div className="w-12 h-12 bg-amber-100 text-amber-600 rounded-xl flex items-center justify-center text-xl shadow-inner group-hover:scale-110 transition-transform">
              <i className="fas fa-exclamation-circle"></i>
            </div>
          </div>
          <h3 className="text-slate-500 font-semibold text-sm mb-1 relative z-10">Low Stock Items</h3>
          <p className="text-3xl font-black text-slate-900 relative z-10">{stats?.low_stock_items || 0}</p>
        </div>

      </div>

      <h2 className="text-2xl font-black text-slate-900 tracking-tight mb-6">Quick Actions</h2>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <button className="bg-white border border-slate-200 rounded-2xl p-6 hover:shadow-md hover:border-emerald-300 transition-all block text-left">
          <div className="w-10 h-10 bg-emerald-50 text-emerald-600 rounded-lg flex items-center justify-center text-lg mb-4">
            <i className="fas fa-box-open"></i>
          </div>
          <h3 className="font-bold text-slate-900 mb-1">Orders & Invoices</h3>
          <p className="text-sm text-slate-500">View and manage customer orders and sales.</p>
        </button>
        <button className="bg-white border border-slate-200 rounded-2xl p-6 hover:shadow-md hover:border-blue-300 transition-all block text-left">
          <div className="w-10 h-10 bg-blue-50 text-blue-600 rounded-lg flex items-center justify-center text-lg mb-4">
            <i className="fas fa-warehouse"></i>
          </div>
          <h3 className="font-bold text-slate-900 mb-1">Stock Management</h3>
          <p className="text-sm text-slate-500">Check inventory levels and request procurement.</p>
        </button>
        <button className="bg-white border border-slate-200 rounded-2xl p-6 hover:shadow-md hover:border-indigo-300 transition-all block text-left">
          <div className="w-10 h-10 bg-indigo-50 text-indigo-600 rounded-lg flex items-center justify-center text-lg mb-4">
            <i className="fas fa-walking"></i>
          </div>
          <h3 className="font-bold text-slate-900 mb-1">Walk-In Customers</h3>
          <p className="text-sm text-slate-500">Manage direct showroom leads and conversions.</p>
        </button>
      </div>

    </div>
  );
}
