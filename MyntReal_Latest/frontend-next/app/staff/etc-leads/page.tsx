"use client";

import React, { useState, useEffect } from "react";
import api from "@/lib/api";
import { useStaffAuth } from "@/contexts/StaffAuthContext";

export default function GenericCRMPage() {
  const { token } = useStaffAuth();
  const [timeline, setTimeline] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [pageTitle, setPageTitle] = useState("CRM Module");

  useEffect(() => {
    if (typeof window !== "undefined") {
      const path = window.location.pathname.split("/").pop() || "";
      setPageTitle(path.replace(/-/g, " ").replace(/\w/g, l => l.toUpperCase()));
    }
    const fetchData = async () => {
      try {
        // Wire to unified_lead_view (using lead_id 1 as placeholder)
        const res = await api.get(`/api/v1/crm/unified-my-leads/search-partner?q=${encodeURIComponent("")}`);
        if (res.data) {
          setTimeline(res.data);
        }
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [token]);

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6 animate-in fade-in zoom-in duration-500">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900 tracking-tight">{pageTitle}</h1>
      </div>
      
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
        {loading ? (
           <div className="p-12 text-center text-gray-500"><i className="fas fa-spinner fa-spin mr-2"></i>Loading unified timeline...</div>
        ) : (
          <div className="p-6">
            <h2 className="text-xl font-bold mb-4">Unified Lead View (Mock Lead #1)</h2>
            {timeline?.lead ? (
              <div className="grid grid-cols-2 gap-4">
                <div className="p-4 bg-gray-50 rounded-lg">
                  <p className="font-bold text-gray-900">{timeline.lead.name}</p>
                  <p className="text-sm text-gray-600">{timeline.lead.phone} | {timeline.lead.email}</p>
                  <span className="inline-block mt-2 px-2 py-1 bg-indigo-100 text-indigo-700 text-xs font-bold rounded-full">{timeline.lead.status}</span>
                </div>
                <div className="p-4 bg-gray-50 rounded-lg">
                  <p className="font-bold text-gray-900">AI Intelligence</p>
                  <p className="text-sm text-gray-600">Score: {timeline.ai_intelligence?.lead_score}</p>
                  <p className="text-sm text-gray-600">Action: {timeline.ai_intelligence?.recommended_action}</p>
                </div>
              </div>
            ) : (
              <div className="text-gray-500 text-center py-8">No timeline data found for this lead.</div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
