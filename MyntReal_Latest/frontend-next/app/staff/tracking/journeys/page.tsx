"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useStaffAuth } from "@/contexts/StaffAuthContext";

interface Journey {
  id: number;
  start_location: string;
  end_location: string;
  start_time: string;
  end_time: string;
  distance_km: number;
  purpose: string;
  status: string; // COMPLETED, IN_PROGRESS
}

export default function TravelJourneysPage() {
  const { token, hasRole } = useStaffAuth();
  const [journeys, setJourneys] = useState<Journey[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchJourneys = async () => {
      setLoading(true);
      setTimeout(() => {
        setJourneys([
          { id: 1, start_location: "Office (Andheri)", end_location: "Client Site (Bandra)", start_time: "2026-08-14T10:00:00", end_time: "2026-08-14T10:45:00", distance_km: 12.5, purpose: "Solar Installation Site Visit", status: "COMPLETED" },
          { id: 2, start_location: "Client Site (Bandra)", end_location: "Meeting Hub (BKC)", start_time: "2026-08-14T12:00:00", end_time: "2026-08-14T12:20:00", distance_km: 4.2, purpose: "Lunch Meeting with Vendor", status: "COMPLETED" },
          { id: 3, start_location: "Meeting Hub (BKC)", end_location: "Pending...", start_time: "2026-08-14T14:30:00", end_time: "", distance_km: 0, purpose: "Return to Office", status: "IN_PROGRESS" },
        ]);
        setLoading(false);
      }, 600);
    };

    fetchJourneys();
  }, [token]);

  return (
    <div className="p-6 max-w-7xl mx-auto flex flex-col h-[calc(100vh-80px)]">
      <div className="flex justify-between items-end mb-6 shrink-0">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 tracking-tight">Travel Journeys</h1>
          <p className="text-sm text-gray-500 mt-2">Log and track your field visits for expense reimbursement and tracking.</p>
        </div>
        <div className="flex space-x-3">
          <Link href="/staff/tracking/location" className="px-4 py-2 bg-white border border-gray-300 text-gray-700 font-medium rounded-lg shadow-sm hover:bg-gray-50 transition-colors">
            <i className="fas fa-map-marker-alt mr-2"></i> Location History
          </Link>
          <button className="px-4 py-2 bg-indigo-600 text-white font-medium rounded-lg shadow-sm hover:bg-indigo-700 transition-colors flex items-center">
            <i className="fas fa-play mr-2"></i> Start Journey
          </button>
        </div>
      </div>

      {/* Stats Summary */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-6 shrink-0">
        <div className="bg-white p-5 rounded-xl shadow-sm border border-gray-100">
          <p className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-1">Today's Distance</p>
          <h3 className="text-2xl font-bold text-gray-900">16.7 <span className="text-sm text-gray-500 font-medium">km</span></h3>
        </div>
        <div className="bg-white p-5 rounded-xl shadow-sm border border-gray-100">
          <p className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-1">Journeys Logged</p>
          <h3 className="text-2xl font-bold text-gray-900">3</h3>
        </div>
        <div className="bg-white p-5 rounded-xl shadow-sm border border-gray-100">
          <p className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-1">Total Travel Time</p>
          <h3 className="text-2xl font-bold text-gray-900">1<span className="text-sm text-gray-500 font-medium">h</span> 5<span className="text-sm text-gray-500 font-medium">m</span></h3>
        </div>
        <div className="bg-white p-5 rounded-xl shadow-sm border border-gray-100">
          <p className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-1">Pending Claims</p>
          <h3 className="text-2xl font-bold text-gray-900">₹ 350</h3>
        </div>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-gray-100 flex-1 overflow-hidden flex flex-col min-h-0">
        <div className="p-4 border-b border-gray-100 bg-gray-50 flex justify-between items-center">
          <h2 className="font-bold text-gray-900">Today's Logs</h2>
          <button className="text-sm text-indigo-600 font-medium hover:text-indigo-800">
            View All History
          </button>
        </div>
        
        <div className="flex-1 overflow-y-auto p-6">
          {loading ? (
            <div className="text-center text-gray-500 py-12">
              <i className="fas fa-spinner fa-spin text-3xl text-indigo-500 mb-3"></i>
              <p>Loading journeys...</p>
            </div>
          ) : journeys.length === 0 ? (
             <div className="text-center text-gray-500 py-12">
               <i className="fas fa-car text-3xl mb-3 text-gray-300"></i>
               <p>No journeys logged today.</p>
             </div>
          ) : (
            <div className="space-y-6">
              {journeys.map((journey) => (
                <div key={journey.id} className="border border-gray-200 rounded-xl overflow-hidden shadow-sm hover:shadow-md transition-shadow">
                  {/* Journey Header */}
                  <div className={`p-4 border-b border-gray-100 flex justify-between items-center ${journey.status === 'IN_PROGRESS' ? 'bg-indigo-50' : 'bg-gray-50'}`}>
                    <div className="flex items-center gap-2">
                      <span className={`w-2.5 h-2.5 rounded-full ${journey.status === 'IN_PROGRESS' ? 'bg-indigo-500 animate-pulse' : 'bg-green-500'}`}></span>
                      <h3 className="font-bold text-gray-900">{journey.purpose}</h3>
                    </div>
                    <span className={`text-[10px] font-bold px-2 py-1 rounded-full border ${journey.status === 'IN_PROGRESS' ? 'bg-indigo-100 text-indigo-700 border-indigo-200' : 'bg-green-100 text-green-700 border-green-200'}`}>
                      {journey.status}
                    </span>
                  </div>
                  
                  {/* Journey Details */}
                  <div className="p-5 grid grid-cols-1 md:grid-cols-3 gap-6">
                    <div className="relative pl-6 border-l-2 border-dashed border-gray-300 ml-3 space-y-4">
                      {/* Start Point */}
                      <div className="relative">
                        <div className="absolute -left-[30px] top-0 w-3.5 h-3.5 rounded-full bg-blue-500 border-2 border-white"></div>
                        <p className="text-xs font-bold text-gray-500 uppercase">Start</p>
                        <p className="text-sm font-medium text-gray-900">{journey.start_location}</p>
                        <p className="text-xs text-gray-500">{new Date(journey.start_time).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</p>
                      </div>
                      {/* End Point */}
                      <div className="relative">
                        <div className="absolute -left-[30px] top-0 w-3.5 h-3.5 rounded-full bg-red-500 border-2 border-white"></div>
                        <p className="text-xs font-bold text-gray-500 uppercase">End</p>
                        <p className="text-sm font-medium text-gray-900">{journey.end_location}</p>
                        <p className="text-xs text-gray-500">{journey.end_time ? new Date(journey.end_time).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'}) : '--:--'}</p>
                      </div>
                    </div>
                    
                    <div className="md:col-span-2 flex flex-col justify-center">
                      <div className="grid grid-cols-2 gap-4">
                        <div className="bg-gray-50 p-4 rounded-lg border border-gray-100">
                          <p className="text-xs text-gray-500 font-medium mb-1"><i className="fas fa-road mr-1"></i> Distance</p>
                          <p className="text-lg font-bold text-gray-900">{journey.distance_km} km</p>
                        </div>
                        <div className="bg-gray-50 p-4 rounded-lg border border-gray-100">
                          <p className="text-xs text-gray-500 font-medium mb-1"><i className="fas fa-rupee-sign mr-1"></i> Est. Claim (₹10/km)</p>
                          <p className="text-lg font-bold text-gray-900">₹ {(journey.distance_km * 10).toFixed(0)}</p>
                        </div>
                      </div>
                      
                      {journey.status === 'IN_PROGRESS' && (
                        <div className="mt-4 flex gap-3">
                          <button className="flex-1 py-2 bg-red-50 text-red-600 font-medium rounded-lg border border-red-200 hover:bg-red-100 transition-colors">
                            <i className="fas fa-stop mr-2"></i> End Journey
                          </button>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
