"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useStaffAuth } from "@/contexts/StaffAuthContext";
import { getApiUrl } from "@/lib/api";

interface BOMEntry {
  id: number;
  bom_number: string;
  product_name: string;
  product_code: string;
  total_cost: number;
  created_at: string;
  status: string;
  components_count: number;
}

export default function BOMPage() {
  const { token } = useStaffAuth();
  const [boms, setBoms] = useState<BOMEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [searchTerm, setSearchTerm] = useState("");

  useEffect(() => {
    if (!token) return;
    
    const fetchBOMs = async () => {
      try {
        setLoading(true);
        // Using generic BOM endpoint
        const res = await fetch(`${getApiUrl()}/api/v1/staff/inventory/boms`, {
          headers: {
            "Authorization": `Bearer ${token}`
          }
        });
        
        if (res.ok) {
          const data = await res.json();
          setBoms(data.items || []);
        } else {
          setBoms([]); // Fallback to empty
        }
      } catch (err: any) {
        console.warn("Failed to fetch BOMs, using empty state", err);
        setBoms([]);
      } finally {
        setLoading(false);
      }
    };

    fetchBOMs();
  }, [token]);

  const filteredBOMs = boms.filter(b => 
    b.product_name.toLowerCase().includes(searchTerm.toLowerCase()) || 
    b.bom_number.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="flex justify-between items-end mb-8">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 tracking-tight">Bill of Materials (BOM)</h1>
          <p className="text-sm text-gray-500 mt-2">Manage recipes, component lists, and standard costs for manufactured items.</p>
        </div>
        <div className="flex space-x-3">
          <Link href="/staff/accounts/manufacturing" className="px-4 py-2 bg-white border border-gray-300 text-gray-700 font-medium rounded-lg shadow-sm hover:bg-gray-50 transition-colors">
            <i className="fas fa-industry mr-2"></i> Manufacturing
          </Link>
          <button className="px-4 py-2 bg-indigo-600 text-white font-medium rounded-lg shadow-sm hover:bg-indigo-700 transition-colors">
            <i className="fas fa-plus mr-2"></i> Create BOM
          </button>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <div className="bg-white p-5 rounded-xl shadow-sm border-l-4 border-indigo-500">
          <p className="text-xs font-bold text-gray-500 uppercase">Total Active BOMs</p>
          <p className="text-2xl font-bold text-gray-900 mt-1">{boms.length}</p>
        </div>
        <div className="bg-white p-5 rounded-xl shadow-sm border-l-4 border-amber-500">
          <p className="text-xs font-bold text-gray-500 uppercase">Avg. Components per BOM</p>
          <p className="text-2xl font-bold text-amber-600 mt-1">
            {boms.length > 0 ? (boms.reduce((sum, b) => sum + b.components_count, 0) / boms.length).toFixed(1) : 0}
          </p>
        </div>
        <div className="bg-white p-5 rounded-xl shadow-sm border-l-4 border-green-500">
          <p className="text-xs font-bold text-gray-500 uppercase">Recently Updated</p>
          <p className="text-2xl font-bold text-green-600 mt-1">
            {boms.filter(b => new Date(b.created_at).getTime() > Date.now() - 7 * 24 * 60 * 60 * 1000).length}
          </p>
        </div>
      </div>

      {/* Content Area */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
        <div className="p-4 border-b border-gray-100 flex justify-between items-center bg-gray-50">
          <div className="flex items-center space-x-4">
            <div className="relative">
              <i className="fas fa-search absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400"></i>
              <input 
                type="text" 
                placeholder="Search BOMs..." 
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10 pr-4 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:border-indigo-500 outline-none w-64" 
              />
            </div>
            <select className="px-3 py-2 border border-gray-300 rounded-lg text-sm bg-white text-gray-700 outline-none">
              <option value="">All Statuses</option>
              <option value="ACTIVE">Active</option>
              <option value="DRAFT">Draft</option>
              <option value="ARCHIVED">Archived</option>
            </select>
          </div>
          <button className="text-gray-500 hover:text-gray-700">
            <i className="fas fa-filter mr-1"></i> Filter
          </button>
        </div>
        
        {loading ? (
          <div className="p-12 text-center text-gray-500">
            <i className="fas fa-spinner fa-spin text-3xl mb-3 text-indigo-500"></i>
            <p>Loading Bill of Materials...</p>
          </div>
        ) : error ? (
          <div className="p-8 text-center text-red-500 bg-red-50">
            <i className="fas fa-exclamation-triangle text-2xl mb-2"></i>
            <p>{error}</p>
          </div>
        ) : filteredBOMs.length === 0 ? (
          <div className="p-16 text-center text-gray-500 flex flex-col items-center">
            <div className="w-16 h-16 bg-indigo-50 text-indigo-300 rounded-full flex items-center justify-center mb-4">
              <i className="fas fa-sitemap text-2xl"></i>
            </div>
            <h3 className="text-lg font-medium text-gray-900 mb-1">No BOMs found</h3>
            <p className="text-gray-500 mb-4">There are currently no Bill of Materials configured.</p>
            <button className="px-4 py-2 font-medium rounded hover:opacity-90 transition-colors bg-indigo-50 text-indigo-600">
              Create New BOM
            </button>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-gray-50 border-b border-gray-200">
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider">BOM No.</th>
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Product</th>
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider text-center">Components</th>
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider text-right">Standard Cost (₹)</th>
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Created / Modified</th>
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider text-center">Status</th>
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider text-center">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {filteredBOMs.map(bom => (
                  <tr key={bom.id} className="hover:bg-gray-50 transition-colors">
                    <td className="p-4 text-sm font-medium text-indigo-600">{bom.bom_number}</td>
                    <td className="p-4">
                      <p className="text-sm font-bold text-gray-900">{bom.product_name}</p>
                      <p className="text-xs text-gray-500">{bom.product_code}</p>
                    </td>
                    <td className="p-4 text-center">
                      <span className="bg-gray-100 text-gray-700 px-2 py-1 rounded-full text-xs font-bold">
                        {bom.components_count} items
                      </span>
                    </td>
                    <td className="p-4 text-right">
                      <p className="text-sm font-bold text-gray-900">{bom.total_cost.toFixed(2)}</p>
                    </td>
                    <td className="p-4 text-sm text-gray-600">
                      {new Date(bom.created_at).toLocaleDateString()}
                    </td>
                    <td className="p-4 text-center">
                      <span className={`text-[10px] font-bold px-2 py-1 rounded ${
                        bom.status === "ACTIVE" ? "bg-green-100 text-green-800" : 
                        bom.status === "DRAFT" ? "bg-amber-100 text-amber-800" :
                        "bg-gray-100 text-gray-800"
                      }`}>
                        {bom.status}
                      </span>
                    </td>
                    <td className="p-4 text-center">
                      <Link href={`/staff/accounts/bom/${bom.id}`} className="text-indigo-600 hover:text-indigo-800 text-sm font-medium mx-2">
                        View/Edit
                      </Link>
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
