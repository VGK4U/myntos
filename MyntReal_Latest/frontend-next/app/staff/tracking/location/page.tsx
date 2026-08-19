"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useStaffAuth } from "@/contexts/StaffAuthContext";
import { getApiUrl } from "@/lib/api";

interface LocationPoint {
  id: number;
  latitude: number;
  longitude: number;
  timestamp: string;
  accuracy: number;
  battery_level: number;
}

export default function LocationHistoryPage() {
  const { token, hasRole } = useStaffAuth();
  const [points, setPoints] = useState<LocationPoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedDate, setSelectedDate] = useState(new Date().toISOString().split('T')[0]);

  useEffect(() => {
    const fetchLocations = async () => {
      if (!token) return;
      try {
        setLoading(true);
        const res = await fetch(`${getApiUrl()}/api/v1/staff/attendance/location/my/history?date=${selectedDate}`, {
          headers: {
            "Authorization": `Bearer ${token}`
          }
        });
        if (res.ok) {
          const data = await res.json();
          // Map backend location format to LocationPoint
          // Assuming backend returns a list of items or an object with items
          const items = Array.isArray(data) ? data : (data.items || data.data || []);
          const mapped = items.map((item: any, index: number) => ({
            id: item.id || index + 1,
            latitude: item.latitude || 0,
            longitude: item.longitude || 0,
            timestamp: item.timestamp || item.created_at || new Date().toISOString(),
            accuracy: item.accuracy || 10,
            battery_level: item.battery_level || 100
          }));
          setPoints(mapped);
        } else {
          setPoints([]);
        }
      } catch (err) {
        console.error("Failed to fetch location history", err);
        setPoints([]);
      } finally {
        setLoading(false);
      }
    };

    fetchLocations();
  }, [token, selectedDate]);

  return (
    <div className="p-6 max-w-7xl mx-auto h-[calc(100vh-80px)] flex flex-col">
      <div className="flex justify-between items-end mb-6 shrink-0">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 tracking-tight">Location History</h1>
          <p className="text-sm text-gray-500 mt-2">Track your daily field movements, GPS pings, and battery health.</p>
        </div>
        <div className="flex space-x-3">
          <Link href="/staff/tracking/journeys" className="px-4 py-2 bg-white border border-gray-300 text-gray-700 font-medium rounded-lg shadow-sm hover:bg-gray-50 transition-colors">
            <i className="fas fa-route mr-2"></i> Travel Journeys
          </Link>
          {hasRole(['MANAGER', 'ADMIN']) && (
            <button className="px-4 py-2 bg-indigo-600 text-white font-medium rounded-lg shadow-sm hover:bg-indigo-700 transition-colors">
              <i className="fas fa-users mr-2"></i> Team Tracker
            </button>
          )}
        </div>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-gray-100 flex flex-1 overflow-hidden min-h-0 flex-col md:flex-row">
        
        {/* Sidebar / Timeline */}
        <div className="w-full md:w-80 border-r border-gray-100 flex flex-col bg-gray-50/50 shrink-0">
          <div className="p-4 border-b border-gray-100 bg-white">
            <label className="block text-xs font-bold text-gray-500 uppercase tracking-wider mb-2">Select Date</label>
            <input 
              type="date" 
              value={selectedDate}
              onChange={(e) => setSelectedDate(e.target.value)}
              className="w-full border border-gray-300 rounded-lg p-2.5 text-sm focus:ring-2 focus:border-indigo-500 outline-none"
            />
          </div>
          
          <div className="flex-1 overflow-y-auto p-4">
            <h3 className="text-sm font-bold text-gray-900 mb-4">Location Pings ({points.length})</h3>
            
            {loading ? (
              <div className="text-center text-gray-500 py-8">
                <i className="fas fa-spinner fa-spin text-2xl text-indigo-500 mb-2"></i>
              </div>
            ) : points.length === 0 ? (
              <div className="text-center text-gray-500 py-8 text-sm">
                No location data for this date.
              </div>
            ) : (
              <div className="relative border-l-2 border-indigo-200 ml-3 pl-4 space-y-6">
                {points.map((point, index) => (
                  <div key={point.id} className="relative">
                    <div className="absolute -left-[23px] top-1 w-4 h-4 rounded-full bg-indigo-500 border-2 border-white shadow-sm"></div>
                    <p className="text-sm font-bold text-gray-900">{new Date(point.timestamp).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</p>
                    <p className="text-xs text-gray-500 font-mono mt-0.5">{point.latitude.toFixed(4)}, {point.longitude.toFixed(4)}</p>
                    <div className="flex space-x-3 mt-1 text-[10px] text-gray-400 font-medium">
                      <span><i className="fas fa-crosshairs"></i> ±{point.accuracy}m</span>
                      <span className={point.battery_level < 20 ? 'text-red-500' : ''}><i className="fas fa-battery-half"></i> {point.battery_level}%</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Map Area Mockup */}
        <div className="flex-1 bg-gray-200 relative flex items-center justify-center overflow-hidden">
          {/* Map placeholder */}
          <div className="absolute inset-0 opacity-30" style={{
            backgroundImage: 'url("https://www.transparenttextures.com/patterns/cubes.png")',
            backgroundSize: '100px'
          }}></div>
          
          <div className="z-10 bg-white p-6 rounded-xl shadow-lg border border-gray-200 text-center max-w-sm mx-4">
            <i className="fas fa-map-marked-alt text-4xl text-indigo-300 mb-4"></i>
            <h2 className="text-lg font-bold text-gray-900 mb-2">Interactive Map</h2>
            <p className="text-sm text-gray-500 mb-4">The Google Maps / Mapbox integration would display the polyline journey here.</p>
            <div className="flex justify-center space-x-2">
              <span className="w-3 h-3 rounded-full bg-green-500 block"></span>
              <span className="w-3 h-3 rounded-full bg-indigo-500 block"></span>
              <span className="w-3 h-3 rounded-full bg-red-500 block"></span>
            </div>
          </div>
        </div>
        
      </div>
    </div>
  );
}
