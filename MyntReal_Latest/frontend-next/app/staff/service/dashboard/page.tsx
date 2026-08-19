"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useStaffAuth } from "@/contexts/StaffAuthContext";
import { getApiUrl } from "@/lib/api";
import { Line, Bar } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  Filler
} from 'chart.js';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

export default function ServiceDashboardPage() {
  const { token } = useStaffAuth();
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!token) return;
    
    const fetchStats = async () => {
      try {
        setLoading(true);
        // Using generic Service endpoint
        const res = await fetch(`${getApiUrl()}/api/v1/staff/service/dashboard`, {
          headers: {
            "Authorization": `Bearer ${token}`
          }
        });
        
        if (res.ok) {
          const data = await res.json();
          setStats(data);
        } else {
          setStats(null);
        }
      } catch (err: any) {
        console.warn("Failed to fetch Service stats", err);
      } finally {
        setLoading(false);
      }
    };

    fetchStats();
  }, [token]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="flex flex-col items-center text-indigo-500">
          <i className="fas fa-circle-notch fa-spin text-4xl mb-3"></i>
          <p className="text-sm font-medium">Loading Service Analytics...</p>
        </div>
      </div>
    );
  }

  const volumeData = {
    labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
    datasets: [
      {
        label: 'New Tickets',
        data: [12, 19, 15, 22, 18, 5, 8],
        borderColor: 'rgba(99, 102, 241, 1)',
        backgroundColor: 'rgba(99, 102, 241, 0.1)',
        tension: 0.4,
        fill: true,
      },
      {
        label: 'Resolved',
        data: [10, 15, 18, 20, 22, 10, 12],
        borderColor: 'rgba(16, 185, 129, 1)',
        backgroundColor: 'transparent',
        tension: 0.4,
        borderDash: [5, 5],
      }
    ],
  };

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      <div className="flex justify-between items-end">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 tracking-tight">Service & Support Dashboard</h1>
          <p className="text-sm text-gray-500 mt-2">Monitor ticket volumes, resolution times, and customer satisfaction.</p>
        </div>
        <div className="flex space-x-3">
          <Link href="/staff/service/tickets/new" className="px-4 py-2 bg-indigo-600 text-white font-medium rounded-lg shadow-sm hover:bg-indigo-700 transition-colors">
            <i className="fas fa-plus mr-2"></i> Raise Ticket
          </Link>
          <Link href="/staff/service/tickets" className="px-4 py-2 bg-white border border-gray-300 text-gray-700 font-medium rounded-lg shadow-sm hover:bg-gray-50 transition-colors">
            <i className="fas fa-list mr-2"></i> View Queue
          </Link>
        </div>
      </div>

      {/* Top Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white p-5 rounded-xl shadow-sm border border-gray-100 flex items-center justify-between group cursor-pointer hover:border-indigo-300 transition-colors">
          <div>
            <p className="text-sm font-medium text-gray-500">Open Tickets</p>
            <p className="text-3xl font-bold text-gray-900 mt-1">{stats?.open_tickets || 0}</p>
          </div>
          <div className="w-12 h-12 bg-indigo-50 text-indigo-600 rounded-full flex items-center justify-center text-xl group-hover:bg-indigo-500 group-hover:text-white transition-colors">
            <i className="fas fa-ticket-alt"></i>
          </div>
        </div>
        
        <div className="bg-white p-5 rounded-xl shadow-sm border border-gray-100 flex items-center justify-between group cursor-pointer hover:border-red-300 transition-colors">
          <div>
            <p className="text-sm font-medium text-gray-500">Unassigned</p>
            <p className="text-3xl font-bold text-red-600 mt-1">{stats?.unassigned_tickets || 0}</p>
          </div>
          <div className="w-12 h-12 bg-red-50 text-red-600 rounded-full flex items-center justify-center text-xl group-hover:bg-red-500 group-hover:text-white transition-colors">
            <i className="fas fa-exclamation-circle"></i>
          </div>
        </div>

        <div className="bg-white p-5 rounded-xl shadow-sm border border-gray-100 flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-gray-500">Avg Resolution</p>
            <p className="text-3xl font-bold text-gray-900 mt-1">{stats?.avg_resolution_time || "N/A"}</p>
          </div>
          <div className="w-12 h-12 bg-blue-50 text-blue-600 rounded-full flex items-center justify-center text-xl">
            <i className="fas fa-stopwatch"></i>
          </div>
        </div>

        <div className="bg-white p-5 rounded-xl shadow-sm border border-gray-100 flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-gray-500">CSAT Score</p>
            <div className="flex items-end mt-1">
              <p className="text-3xl font-bold text-green-600">{stats?.csat_score || "0.0"}</p>
              <p className="text-sm text-gray-400 ml-1 mb-1">/ 5.0</p>
            </div>
          </div>
          <div className="w-12 h-12 bg-green-50 text-green-600 rounded-full flex items-center justify-center text-xl">
            <i className="fas fa-smile"></i>
          </div>
        </div>
      </div>

      {/* Charts Section */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 bg-white p-6 rounded-xl shadow-sm border border-gray-100">
          <h2 className="text-lg font-bold text-gray-900 mb-4">Ticket Volume (Last 7 Days)</h2>
          <div className="h-72">
            <Line 
              data={volumeData} 
              options={{
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { position: 'top' } },
                scales: {
                  y: { beginAtZero: true, grid: { color: '#f3f4f6' } },
                  x: { grid: { display: false } }
                }
              }} 
            />
          </div>
        </div>
        
        <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100 flex flex-col">
          <h2 className="text-lg font-bold text-gray-900 mb-4">Recent Activity</h2>
          <div className="flex-1 overflow-y-auto pr-2 space-y-4">
            {(stats?.recent_activity || []).map((activity: any) => (
              <div key={activity.id} className="flex gap-3">
                <div className={`mt-1 w-2 h-2 rounded-full bg-${activity.color}-500 shrink-0`}></div>
                <div>
                  <p className="text-sm font-medium text-gray-900">{activity.action}</p>
                  <p className="text-xs text-gray-500">{activity.user} • {activity.time}</p>
                </div>
              </div>
            ))}
          </div>
          <button className="mt-4 w-full py-2 text-sm text-indigo-600 font-medium hover:bg-indigo-50 rounded-lg transition-colors border border-transparent hover:border-indigo-100">
            View All Activity
          </button>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Link href="/staff/service/tracking" className="group bg-white p-5 rounded-xl shadow-sm border border-gray-100 hover:border-blue-500 hover:shadow-md transition-all flex items-center space-x-4 cursor-pointer">
          <div className="w-12 h-12 bg-blue-50 text-blue-500 rounded-full flex items-center justify-center text-xl group-hover:bg-blue-500 group-hover:text-white transition-colors">
            <i className="fas fa-map-marker-alt"></i>
          </div>
          <div>
            <h3 className="font-bold text-gray-900">Service Center Tracking</h3>
            <p className="text-xs text-gray-500">Monitor in-shop repairs</p>
          </div>
        </Link>
        
        <Link href="/staff/service/procurement" className="group bg-white p-5 rounded-xl shadow-sm border border-gray-100 hover:border-purple-500 hover:shadow-md transition-all flex items-center space-x-4 cursor-pointer">
          <div className="w-12 h-12 bg-purple-50 text-purple-500 rounded-full flex items-center justify-center text-xl group-hover:bg-purple-500 group-hover:text-white transition-colors">
            <i className="fas fa-boxes"></i>
          </div>
          <div>
            <h3 className="font-bold text-gray-900">Spares Procurement</h3>
            <p className="text-xs text-gray-500">Request parts for service</p>
          </div>
        </Link>

        <div className="group bg-white p-5 rounded-xl shadow-sm border border-gray-100 hover:border-amber-500 hover:shadow-md transition-all flex items-center space-x-4 cursor-pointer">
          <div className="w-12 h-12 bg-amber-50 text-amber-500 rounded-full flex items-center justify-center text-xl group-hover:bg-amber-500 group-hover:text-white transition-colors">
            <i className="fas fa-chart-line"></i>
          </div>
          <div>
            <h3 className="font-bold text-gray-900">Performance Reports</h3>
            <p className="text-xs text-gray-500">Agent & SLA analytics</p>
          </div>
        </div>
      </div>

    </div>
  );
}
