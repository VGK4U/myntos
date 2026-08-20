"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useStaffAuth } from "@/contexts/StaffAuthContext";

interface NDA {
  id: number;
  title: string;
  version: string;
  status: string; // PENDING, ACCEPTED, REJECTED
  assigned_date: string;
  due_date: string;
  accepted_date: string | null;
}

export default function NDACompliancePage() {
  const { token, hasRole } = useStaffAuth();
  
  const [ndas, setNdas] = useState<NDA[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState("my_ndas"); // my_ndas, manage (admin)

  useEffect(() => {
    // Simulating API fetch
    const fetchNDAs = async () => {
      try {
        const tokenStr = typeof window !== "undefined" ? localStorage.getItem("staff_token") : "";
        const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/v1/staff/compliance/nda`, {
          headers: { Authorization: `Bearer ${tokenStr}` }
        });
        if (res.ok) {
          const data = await res.json();
          setNdas(data.items || []);
        } else {
          setNdas([]);
        }
      } catch (err) {
        console.warn("Failed to fetch NDA data", err);
        setNdas([]);
      } finally {
        setLoading(false);
      }
    };

    fetchNDAs();
  }, [token]);

  return (
    <div className="p-6 max-w-7xl mx-auto flex flex-col h-[calc(100vh-80px)]">
      <div className="flex justify-between items-end mb-6 shrink-0">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 tracking-tight">NDA & Compliance</h1>
          <p className="text-sm text-gray-500 mt-2">Review, accept, and track mandatory Non-Disclosure Agreements and company policies.</p>
        </div>
        <div className="flex space-x-3">
          {hasRole(['HR', 'ADMIN']) && (
            <button className="px-4 py-2 bg-white border border-gray-300 text-gray-700 font-medium rounded-lg shadow-sm hover:bg-gray-50 transition-colors">
              <i className="fas fa-file-contract mr-2"></i> NDA Editor
            </button>
          )}
          {hasRole(['HR', 'ADMIN']) && (
            <button className="px-4 py-2 bg-indigo-600 text-white font-medium rounded-lg shadow-sm hover:bg-indigo-700 transition-colors">
              <i className="fas fa-clipboard-check mr-2"></i> Audit Compliance
            </button>
          )}
        </div>
      </div>

      <div className="flex space-x-6 mb-6 shrink-0 border-b border-gray-200">
        <button 
          onClick={() => setActiveTab("my_ndas")}
          className={`pb-3 font-medium text-sm transition-colors border-b-2 ${activeTab === 'my_ndas' ? 'border-indigo-600 text-indigo-600' : 'border-transparent text-gray-500 hover:text-gray-700'}`}
        >
          <i className="fas fa-file-signature mr-2"></i> My Documents
        </button>
        {hasRole(['HR', 'ADMIN']) && (
          <button 
            onClick={() => setActiveTab("manage")}
            className={`pb-3 font-medium text-sm transition-colors border-b-2 ${activeTab === 'manage' ? 'border-indigo-600 text-indigo-600' : 'border-transparent text-gray-500 hover:text-gray-700'}`}
          >
            <i className="fas fa-users-cog mr-2"></i> Team Status
          </button>
        )}
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-gray-100 flex-1 overflow-hidden flex flex-col min-h-0">
        <div className="p-4 border-b border-gray-100 bg-gray-50 flex justify-between items-center">
          <h2 className="font-bold text-gray-900">Required Documents</h2>
          <span className="text-sm text-amber-600 font-bold px-3 py-1 bg-amber-50 rounded-full border border-amber-200">
            {ndas.filter(n => n.status === 'PENDING').length} Action Required
          </span>
        </div>
        
        <div className="flex-1 overflow-y-auto p-6">
          {loading ? (
            <div className="text-center text-gray-500 py-12">
              <i className="fas fa-spinner fa-spin text-3xl text-indigo-500 mb-3"></i>
              <p>Loading your documents...</p>
            </div>
          ) : ndas.length === 0 ? (
             <div className="text-center text-gray-500 py-12">
               <i className="fas fa-check-circle text-4xl mb-3 text-green-300"></i>
               <p className="font-medium text-gray-900">You're all caught up!</p>
               <p className="text-sm">No pending NDAs or compliance documents to review.</p>
             </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {ndas.map((nda) => (
                <div key={nda.id} className={`border rounded-xl overflow-hidden shadow-sm transition-shadow ${nda.status === 'PENDING' ? 'border-amber-300 hover:shadow-md' : 'border-gray-200'}`}>
                  {/* Card Header */}
                  <div className={`p-4 border-b flex justify-between items-start ${nda.status === 'PENDING' ? 'bg-amber-50 border-amber-100' : 'bg-gray-50 border-gray-100'}`}>
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-xs font-bold text-gray-500 uppercase">{nda.version}</span>
                        <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                          nda.status === 'PENDING' ? 'bg-amber-100 text-amber-700' : 'bg-green-100 text-green-700'
                        }`}>
                          {nda.status}
                        </span>
                      </div>
                      <h3 className="font-bold text-gray-900 leading-tight">{nda.title}</h3>
                    </div>
                    <div className="w-10 h-10 rounded-full bg-white flex items-center justify-center shadow-sm text-gray-400 shrink-0">
                      <i className={`fas ${nda.status === 'PENDING' ? 'fa-file-signature text-amber-500' : 'fa-file-contract text-green-500'}`}></i>
                    </div>
                  </div>
                  
                  {/* Card Details */}
                  <div className="p-5">
                    <div className="grid grid-cols-2 gap-4 mb-5">
                      <div>
                        <p className="text-xs text-gray-500 mb-1">Assigned Date</p>
                        <p className="text-sm font-medium text-gray-900">{new Date(nda.assigned_date).toLocaleDateString()}</p>
                      </div>
                      <div>
                        <p className="text-xs text-gray-500 mb-1">Due Date</p>
                        <p className={`text-sm font-bold ${nda.status === 'PENDING' && new Date(nda.due_date).getTime() - new Date().getTime() < 86400000 * 7 ? 'text-red-600' : 'text-gray-900'}`}>
                          {new Date(nda.due_date).toLocaleDateString()}
                        </p>
                      </div>
                    </div>
                    
                    {nda.status === 'PENDING' ? (
                      <button className="w-full py-2.5 bg-indigo-600 text-white font-medium rounded-lg shadow-sm hover:bg-indigo-700 transition-colors">
                        Review & Accept Document
                      </button>
                    ) : (
                      <div className="flex justify-between items-center bg-green-50 p-3 rounded-lg border border-green-100">
                        <div>
                          <p className="text-xs text-green-700 font-bold mb-0.5">Accepted On</p>
                          <p className="text-sm text-green-900">{nda.accepted_date ? new Date(nda.accepted_date).toLocaleString() : 'N/A'}</p>
                        </div>
                        <button className="text-green-700 hover:text-green-900">
                          <i className="fas fa-download"></i> PDF
                        </button>
                      </div>
                    )}
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
