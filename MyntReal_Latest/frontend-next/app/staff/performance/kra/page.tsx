"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useStaffAuth } from "@/contexts/StaffAuthContext";

interface KRA {
  id: number;
  title: string;
  weight: number; // percentage
  target: number;
  achieved: number;
  unit: string;
  status: string; // ON_TRACK, AT_RISK, ACHIEVED, MISSED
}

export default function KRADashboardPage() {
  const { token, hasRole } = useStaffAuth();
  const [kras, setKras] = useState<KRA[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchKRAs = async () => {
      try {
        const tokenStr = typeof window !== "undefined" ? localStorage.getItem("staff_token") : "";
        const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/v1/staff/performance/kra`, {
          headers: { Authorization: `Bearer ${tokenStr}` }
        });
        if (res.ok) {
          const data = await res.json();
          setKras(data.items || []);
        } else {
          setKras([]);
        }
      } catch (err) {
        console.warn("Failed to fetch KRA data", err);
        setKras([]);
      } finally {
        setLoading(false);
      }
    };

    fetchKRAs();
  }, [token]);

  const calculateTotalProgress = () => {
    if (kras.length === 0) return 0;
    let score = 0;
    kras.forEach(kra => {
      const percentage = Math.min(100, (kra.achieved / kra.target) * 100);
      score += (percentage * kra.weight) / 100;
    });
    return Math.round(score);
  };

  const formatNumber = (num: number, unit: string) => {
    if (unit === "INR") return `₹ ${(num / 100000).toFixed(1)}L`;
    if (unit === "%") return `${num}%`;
    return num.toString();
  };

  const overallScore = calculateTotalProgress();

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="flex justify-between items-end mb-8">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 tracking-tight">Key Result Areas (KRA)</h1>
          <p className="text-sm text-gray-500 mt-2">Track your performance metrics, quarterly targets, and appraisal scores.</p>
        </div>
        <div className="flex space-x-3">
          {hasRole(['MANAGER', 'ADMIN']) && (
            <button className="px-4 py-2 bg-white border border-gray-300 text-gray-700 font-medium rounded-lg shadow-sm hover:bg-gray-50 transition-colors">
              <i className="fas fa-users-cog mr-2"></i> Team Reviews
            </button>
          )}
          <button className="px-4 py-2 bg-indigo-600 text-white font-medium rounded-lg shadow-sm hover:bg-indigo-700 transition-colors">
            <i className="fas fa-bullseye mr-2"></i> Update Metrics
          </button>
        </div>
      </div>

      {/* Overview Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100 flex items-center">
          <div className="w-16 h-16 rounded-full flex items-center justify-center mr-4 relative">
            <svg viewBox="0 0 36 36" className="w-16 h-16 transform -rotate-90">
              <path className="text-gray-100" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" fill="none" stroke="currentColor" strokeWidth="3" />
              <path className={`${overallScore >= 80 ? 'text-green-500' : overallScore >= 50 ? 'text-amber-500' : 'text-red-500'}`} strokeDasharray={`${overallScore}, 100`} d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" fill="none" stroke="currentColor" strokeWidth="3" />
            </svg>
            <div className="absolute flex items-center justify-center font-bold text-gray-900 text-lg">
              {overallScore}%
            </div>
          </div>
          <div>
            <h3 className="text-sm font-bold text-gray-500 uppercase tracking-wider">Overall Q3 Score</h3>
            <p className="text-sm text-gray-600 mt-1">Based on weighted averages</p>
          </div>
        </div>

        <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100 flex flex-col justify-center">
          <h3 className="text-sm font-bold text-gray-500 uppercase tracking-wider mb-2">Review Cycle</h3>
          <div className="flex items-end space-x-2">
            <p className="text-3xl font-bold text-gray-900">Q3 2026</p>
            <p className="text-sm text-indigo-600 font-medium mb-1 border-l border-gray-200 pl-2">45 days left</p>
          </div>
        </div>

        <div className="bg-gradient-to-br from-indigo-500 to-indigo-700 p-6 rounded-xl shadow-sm text-white flex flex-col justify-center relative overflow-hidden">
          <i className="fas fa-chart-line absolute right-[-20px] bottom-[-20px] text-8xl opacity-10"></i>
          <h3 className="text-sm font-bold text-indigo-100 uppercase tracking-wider mb-2">Manager Feedback</h3>
          <p className="font-medium text-lg leading-tight">"Great progress on lead conversions. Let's focus on closing the high-value deals."</p>
        </div>
      </div>

      {/* KRA Breakdown */}
      <h2 className="text-xl font-bold text-gray-900 mb-4">Detailed Metrics</h2>
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
        {loading ? (
          <div className="p-12 text-center text-gray-500">
            <i className="fas fa-spinner fa-spin text-3xl mb-3 text-indigo-500"></i>
            <p>Loading your KRA metrics...</p>
          </div>
        ) : (
          <div className="divide-y divide-gray-100">
            {kras.map(kra => {
              const percentage = Math.min(100, Math.round((kra.achieved / kra.target) * 100));
              
              return (
                <div key={kra.id} className="p-6 hover:bg-gray-50 transition-colors flex flex-col md:flex-row gap-6 items-center">
                  <div className="w-full md:w-1/3">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="bg-gray-100 text-gray-700 text-[10px] font-bold px-2 py-0.5 rounded">Weight: {kra.weight}%</span>
                      <span className={`text-[10px] font-bold px-2 py-0.5 rounded border ${
                        kra.status === 'ACHIEVED' ? 'border-green-200 bg-green-50 text-green-700' :
                        kra.status === 'ON_TRACK' ? 'border-blue-200 bg-blue-50 text-blue-700' :
                        'border-red-200 bg-red-50 text-red-700'
                      }`}>
                        {kra.status.replace('_', ' ')}
                      </span>
                    </div>
                    <h3 className="font-bold text-gray-900 text-lg leading-tight">{kra.title}</h3>
                  </div>
                  
                  <div className="w-full md:w-2/3 flex items-center gap-6">
                    <div className="flex-1">
                      <div className="flex justify-between text-sm mb-1">
                        <span className="font-bold text-gray-900">{formatNumber(kra.achieved, kra.unit)}</span>
                        <span className="text-gray-500 font-medium">Target: {formatNumber(kra.target, kra.unit)}</span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-2">
                        <div 
                          className={`h-2 rounded-full ${kra.status === 'AT_RISK' ? 'bg-red-500' : 'bg-indigo-500'}`} 
                          style={{ width: `${percentage}%` }}
                        ></div>
                      </div>
                    </div>
                    <div className="w-16 text-right shrink-0">
                      <span className="text-xl font-bold text-gray-900">{percentage}%</span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
