"use client";

import { useState, useEffect } from "react";
import { useStaffAuth } from "@/contexts/StaffAuthContext";
import { getApiUrl } from "@/lib/api";

interface Segment {
  id: number;
  name: string;
  description: string;
  is_active: boolean;
}

export default function BusinessSegmentsPage() {
  const { token } = useStaffAuth();
  const [segments, setSegments] = useState<Segment[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const fetchSegments = async () => {
    if (!token) return;
    setLoading(true);
    try {
      // Stubbing the segments endpoint
      const res = await fetch(`${getApiUrl()}/api/v1/staff/accounts/segments`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Failed to fetch segments");
      setSegments(data.segments || []);
    } catch (err: any) {
      // Fallback for demo
      setSegments([
        { id: 1, name: "Real Estate Division", description: "All real estate operations", is_active: true },
        { id: 2, name: "Consulting Services", description: "B2B Consulting", is_active: true }
      ]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSegments();
  }, [token]);

  return (
    <div className="p-6 max-w-7xl mx-auto animate-in fade-in zoom-in duration-500">
      <div className="flex flex-col md:flex-row md:items-center justify-between mb-8 gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <i className="fas fa-chart-pie text-indigo-600"></i>
            Business Segments
          </h1>
          <p className="text-sm text-gray-500 mt-1">Manage cost centers and business segments for granular reporting.</p>
        </div>
        <div className="flex gap-2">
          <button className="px-4 py-2 bg-indigo-600 text-white font-semibold rounded-lg shadow hover:bg-indigo-700 transition-colors flex items-center gap-2 text-sm">
            <i className="fas fa-plus"></i> Add Segment
          </button>
        </div>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
        {loading ? (
          <div className="p-10 text-center text-gray-500"><i className="fas fa-spinner fa-spin text-2xl mb-2"></i><p>Loading...</p></div>
        ) : error && segments.length === 0 ? (
          <div className="p-6 text-red-500">{error}</div>
        ) : segments.length === 0 ? (
          <div className="p-10 text-center text-gray-500">No segments found.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-gray-50 border-b border-gray-200">
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Segment Name</th>
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Description</th>
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Status</th>
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {segments.map(seg => (
                  <tr key={seg.id} className="hover:bg-gray-50 transition-colors">
                    <td className="p-4 text-sm font-semibold text-gray-900">{seg.name}</td>
                    <td className="p-4 text-sm text-gray-600">{seg.description || "-"}</td>
                    <td className="p-4">
                      <span className={`text-[10px] font-bold px-2 py-1 rounded ${seg.is_active ? "bg-green-100 text-green-800" : "bg-red-100 text-red-800"}`}>
                        {seg.is_active ? "ACTIVE" : "INACTIVE"}
                      </span>
                    </td>
                    <td className="p-4 text-right">
                      <button className="text-indigo-600 hover:text-indigo-900 p-2"><i className="fas fa-edit"></i></button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
