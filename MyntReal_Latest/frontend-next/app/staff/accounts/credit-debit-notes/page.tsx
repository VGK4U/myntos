"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useStaffAuth } from "@/contexts/StaffAuthContext";
import { getApiUrl } from "@/lib/api";

interface NoteEntry {
  id: number;
  note_number: string;
  date: string;
  party_name: string;
  original_invoice: string;
  amount: number;
  status: string;
  type: "CREDIT" | "DEBIT";
  reason: string;
}

export default function CreditDebitNotesPage() {
  const { token } = useStaffAuth();
  const [activeTab, setActiveTab] = useState<"CREDIT" | "DEBIT">("CREDIT");
  const [notes, setNotes] = useState<NoteEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!token) return;
    
    // Fallback data in case the endpoint isn't fully ready yet
    const fetchNotes = async () => {
      try {
        setLoading(true);
        // Using a generic notes endpoint
        const endpoint = `${getApiUrl()}/api/v1/staff/accounts/notes?type=${activeTab}`;
          
        const res = await fetch(endpoint, {
          headers: {
            "Authorization": `Bearer ${token}`
          }
        });
        
        if (res.ok) {
          const data = await res.json();
          setNotes(data.items || []);
        } else {
          setNotes([]); // Fallback to empty if 404
        }
      } catch (err: any) {
        console.warn(`Failed to fetch ${activeTab} notes, using empty state`, err);
        setNotes([]);
      } finally {
        setLoading(false);
      }
    };

    fetchNotes();
  }, [token, activeTab]);

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="flex justify-between items-end mb-8">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 tracking-tight">Credit & Debit Notes</h1>
          <p className="text-sm text-gray-500 mt-2">Manage adjustments, returns, and discounts for sales and purchases.</p>
        </div>
        <div className="flex space-x-3">
          <Link href="/staff/accounts/invoices" className="px-4 py-2 bg-white border border-gray-300 text-gray-700 font-medium rounded-lg shadow-sm hover:bg-gray-50 transition-colors">
            <i className="fas fa-file-invoice mr-2"></i> Invoices
          </Link>
          <button className="px-4 py-2 bg-indigo-600 text-white font-medium rounded-lg shadow-sm hover:bg-indigo-700 transition-colors">
            <i className="fas fa-plus mr-2"></i> Create Note
          </button>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="flex gap-6 border-b border-gray-200 mb-6 overflow-x-auto">
        <button onClick={() => setActiveTab("CREDIT")} className={`pb-3 font-semibold text-sm transition-colors whitespace-nowrap border-b-2 flex items-center ${activeTab === "CREDIT" ? "border-indigo-600 text-indigo-600" : "border-transparent text-gray-500 hover:text-gray-700"}`}>
          <div className={`w-8 h-8 rounded-full flex items-center justify-center mr-2 ${activeTab === "CREDIT" ? "bg-indigo-100 text-indigo-600" : "bg-gray-100 text-gray-500"}`}>
            <i className="fas fa-arrow-down"></i>
          </div>
          Credit Notes (Sales)
        </button>
        <button onClick={() => setActiveTab("DEBIT")} className={`pb-3 font-semibold text-sm transition-colors whitespace-nowrap border-b-2 flex items-center ${activeTab === "DEBIT" ? "border-amber-600 text-amber-600" : "border-transparent text-gray-500 hover:text-gray-700"}`}>
          <div className={`w-8 h-8 rounded-full flex items-center justify-center mr-2 ${activeTab === "DEBIT" ? "bg-amber-100 text-amber-600" : "bg-gray-100 text-gray-500"}`}>
            <i className="fas fa-arrow-up"></i>
          </div>
          Debit Notes (Purchases)
        </button>
      </div>

      {/* Content Area */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
        <div className={`p-4 border-b border-gray-100 flex justify-between items-center ${activeTab === 'CREDIT' ? 'bg-indigo-50/50' : 'bg-amber-50/50'}`}>
          <div className="flex items-center space-x-4">
            <div className="relative">
              <i className="fas fa-search absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400"></i>
              <input type="text" placeholder={`Search ${activeTab.toLowerCase()} notes...`} className="pl-10 pr-4 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:border-indigo-500 outline-none w-64" />
            </div>
            <select className="px-3 py-2 border border-gray-300 rounded-lg text-sm bg-white text-gray-700 outline-none">
              <option value="">All Reasons</option>
              <option value="RETURN">Sales / Purchase Return</option>
              <option value="DISCOUNT">Discount Given / Received</option>
              <option value="RATE_DIFF">Rate Difference</option>
            </select>
          </div>
          <button className="text-gray-500 hover:text-gray-700">
            <i className="fas fa-filter mr-1"></i> Filter
          </button>
        </div>
        
        {loading ? (
          <div className="p-12 text-center text-gray-500">
            <i className={`fas fa-spinner fa-spin text-3xl mb-3 ${activeTab === 'CREDIT' ? 'text-indigo-500' : 'text-amber-500'}`}></i>
            <p>Loading {activeTab.toLowerCase()} notes...</p>
          </div>
        ) : error ? (
          <div className="p-8 text-center text-red-500 bg-red-50">
            <i className="fas fa-exclamation-triangle text-2xl mb-2"></i>
            <p>{error}</p>
          </div>
        ) : notes.length === 0 ? (
          <div className="p-16 text-center text-gray-500 flex flex-col items-center">
            <div className={`w-16 h-16 rounded-full flex items-center justify-center mb-4 ${activeTab === 'CREDIT' ? 'bg-indigo-50 text-indigo-300' : 'bg-amber-50 text-amber-300'}`}>
              <i className={`fas ${activeTab === 'CREDIT' ? 'fa-arrow-down' : 'fa-arrow-up'} text-2xl`}></i>
            </div>
            <h3 className="text-lg font-medium text-gray-900 mb-1">No {activeTab.toLowerCase()} notes found</h3>
            <p className="text-gray-500 mb-4">There are currently no {activeTab.toLowerCase()} notes in this view.</p>
            <button className={`px-4 py-2 font-medium rounded hover:opacity-90 transition-colors ${activeTab === 'CREDIT' ? 'bg-indigo-50 text-indigo-600' : 'bg-amber-50 text-amber-600'}`}>
              Create New {activeTab === 'CREDIT' ? 'Credit Note' : 'Debit Note'}
            </button>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-gray-50 border-b border-gray-200">
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Date</th>
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Note No.</th>
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Party</th>
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Against Invoice</th>
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Reason</th>
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider text-right">Amount (₹)</th>
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider text-center">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {notes.map(note => (
                  <tr key={note.id} className="hover:bg-gray-50 transition-colors">
                    <td className="p-4 text-sm text-gray-600">{new Date(note.date).toLocaleDateString()}</td>
                    <td className="p-4 text-sm font-medium text-gray-900">{note.note_number}</td>
                    <td className="p-4">
                      <span className="text-sm font-semibold text-gray-900">{note.party_name}</span>
                    </td>
                    <td className="p-4 text-sm text-indigo-600 hover:underline cursor-pointer">{note.original_invoice}</td>
                    <td className="p-4 text-sm text-gray-600">{note.reason}</td>
                    <td className="p-4 text-sm font-bold text-gray-900 text-right">{note.amount.toFixed(2)}</td>
                    <td className="p-4 text-center">
                      <span className={`text-[10px] font-bold px-2 py-1 rounded ${
                        note.status === "ADJUSTED" ? "bg-green-100 text-green-800" : "bg-yellow-100 text-yellow-800"
                      }`}>
                        {note.status}
                      </span>
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
