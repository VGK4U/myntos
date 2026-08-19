"use client";

import React, { useState, useEffect } from "react";

export default function ProgressDashboard() {
  const [activeTab, setActiveTab] = useState("overview");

  const [kpis, setKpis] = useState<any[]>([]);
  const [recentActivities, setRecentActivities] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchProgress = async () => {
      try {
        const token = typeof window !== "undefined" ? localStorage.getItem("staff_token") : "";
        if (!token) return;
        const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/v1/staff/progress/dashboard`, {
          headers: { Authorization: `Bearer ${token}` }
        });
        if (res.ok) {
          const data = await res.json();
          if (data.kpis) setKpis(data.kpis);
          if (data.recentActivities) setRecentActivities(data.recentActivities);
        }
      } catch (err) {
        console.warn("Failed to fetch progress data", err);
      } finally {
        setLoading(false);
      }
    };
    fetchProgress();
  }, []);

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 tracking-tight">Progress Dashboard</h1>
          <p className="text-sm text-gray-500 mt-1">Track your performance metrics, KRAs, and recent activities.</p>
        </div>
        <div className="flex items-center gap-3">
          <button className="px-4 py-2 bg-white border border-gray-200 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-50 transition-colors shadow-sm">
            <i className="fas fa-download mr-2"></i> Export Report
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <nav className="-mb-px flex space-x-8">
          {["overview", "kra-metrics", "team-performance"].map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`
                whitespace-nowrap pb-4 px-1 border-b-2 font-medium text-sm transition-colors capitalize
                ${activeTab === tab
                  ? "border-brand-warning text-brand-warning"
                  : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"}
              `}
            >
              {tab.replace("-", " ")}
            </button>
          ))}
        </nav>
      </div>

      {activeTab === "overview" && (
        <div className="space-y-6 animate-in fade-in slide-in-from-bottom-2 duration-500">
          
          {/* KPI Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {kpis.map((kpi, idx) => (
              <div key={idx} className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm hover:shadow-md transition-shadow relative overflow-hidden group">
                <div className={`absolute top-0 right-0 w-2 h-full ${
                  kpi.status === "success" ? "bg-emerald-500" :
                  kpi.status === "warning" ? "bg-amber-500" :
                  kpi.status === "alert" ? "bg-rose-500" : "bg-blue-500"
                }`}></div>
                <p className="text-sm font-medium text-gray-500 mb-1">{kpi.label}</p>
                <div className="flex items-baseline gap-2">
                  <h3 className="text-2xl font-bold text-gray-900">{kpi.value}</h3>
                  <span className={`text-xs font-semibold ${
                    kpi.trend.startsWith("+") ? "text-emerald-600" : 
                    kpi.trend.startsWith("-") ? "text-rose-600" : "text-gray-400"
                  }`}>
                    {kpi.trend}
                  </span>
                </div>
              </div>
            ))}
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            
            {/* Chart Area Placeholder */}
            <div className="lg:col-span-2 bg-white rounded-xl border border-gray-200 shadow-sm p-6 flex flex-col">
              <div className="flex items-center justify-between mb-6">
                <h3 className="text-lg font-bold text-gray-900">Task Completion Trend</h3>
                <select className="text-sm border-gray-300 rounded-lg text-gray-600 shadow-sm focus:ring-brand-warning focus:border-brand-warning">
                  <option>Last 7 Days</option>
                  <option>Last 30 Days</option>
                  <option>This Quarter</option>
                </select>
              </div>
              <div className="flex-1 bg-gray-50 rounded-lg border border-dashed border-gray-200 flex items-center justify-center min-h-[300px]">
                <div className="text-center">
                  <i className="fas fa-chart-line text-4xl text-gray-300 mb-3"></i>
                  <p className="text-sm text-gray-500">Interactive Line Chart visualization will render here.</p>
                </div>
              </div>
            </div>

            {/* Recent Activity */}
            <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
              <h3 className="text-lg font-bold text-gray-900 mb-6">Recent Activity</h3>
              <div className="space-y-6 relative before:absolute before:inset-0 before:ml-5 before:-translate-x-px md:before:mx-auto md:before:translate-x-0 before:h-full before:w-0.5 before:bg-gradient-to-b before:from-transparent before:via-slate-300 before:to-transparent">
                {recentActivities.map((activity) => (
                  <div key={activity.id} className="relative flex items-center justify-between md:justify-normal md:odd:flex-row-reverse group is-active">
                    <div className="flex items-center justify-center w-10 h-10 rounded-full border border-white bg-slate-100 group-hover:bg-brand-warning/10 text-slate-500 group-hover:text-brand-warning shadow shrink-0 md:order-1 md:group-odd:-translate-x-1/2 md:group-even:translate-x-1/2 z-10 transition-colors">
                      <i className={`fas text-sm ${
                        activity.type === 'task' ? 'fa-check' :
                        activity.type === 'update' ? 'fa-pen' :
                        activity.type === 'hr' ? 'fa-calendar-check' : 'fa-exclamation-triangle'
                      }`}></i>
                    </div>
                    <div className="w-[calc(100%-4rem)] md:w-[calc(50%-2.5rem)] bg-white p-4 rounded-xl border border-gray-100 shadow-sm group-hover:shadow-md transition-shadow">
                      <h4 className="text-sm font-semibold text-gray-900">{activity.title}</h4>
                      <span className="text-xs font-medium text-gray-500 mt-1 block">{activity.time}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

          </div>
        </div>
      )}

    </div>
  );
}
