"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useStaffAuth } from "@/contexts/StaffAuthContext";
import { getApiUrl } from "@/lib/api";

interface Promotion {
  id: number;
  code: string;
  type: string; // FLAT, PERCENTAGE
  value: number;
  min_purchase: number;
  max_discount: number | null;
  valid_from: string;
  valid_until: string;
  usage_limit: number;
  times_used: number;
  status: string; // ACTIVE, EXPIRED, DISABLED
}

export default function VGKPromotionsPage() {
  const { token } = useStaffAuth();
  const [promos, setPromos] = useState<Promotion[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");

  useEffect(() => {
    if (!token) return;
    
    const fetchPromos = async () => {
      try {
        setLoading(true);
        // Generic endpoint for Staff to view VGK promotions
        const res = await fetch(`${getApiUrl()}/api/v1/staff/vgk/promotions`, {
          headers: {
            "Authorization": `Bearer ${token}`
          }
        });
        
        if (res.ok) {
          const data = await res.json();
          setPromos(data.items || []);
        } else {
          setPromos([]);
        }
      } catch (err) {
        console.warn("Failed to fetch promos", err);
      } finally {
        setLoading(false);
      }
    };

    fetchPromos();
  }, [token]);

  const filteredPromos = promos.filter(p => 
    p.code.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="flex justify-between items-end mb-8">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 tracking-tight">Coupons & Promotions</h1>
          <p className="text-sm text-gray-500 mt-2">Create and manage discount codes for the VGK network and partnered vendors.</p>
        </div>
        <div className="flex space-x-3">
          <button className="px-4 py-2 bg-indigo-600 text-white font-medium rounded-lg shadow-sm hover:bg-indigo-700 transition-colors">
            <i className="fas fa-plus mr-2"></i> Create Promo Code
          </button>
        </div>
      </div>

      {/* Content Area */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
        <div className="p-4 border-b border-gray-100 flex justify-between items-center bg-gray-50 flex-wrap gap-4">
          <div className="flex items-center space-x-4 flex-grow max-w-xl">
            <div className="relative flex-grow">
              <i className="fas fa-search absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400"></i>
              <input 
                type="text" 
                placeholder="Search promo code..." 
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10 pr-4 py-2 w-full border border-gray-300 rounded-lg text-sm focus:ring-2 focus:border-indigo-500 outline-none uppercase" 
              />
            </div>
          </div>
        </div>
        
        {loading ? (
          <div className="p-12 text-center text-gray-500">
            <i className="fas fa-spinner fa-spin text-3xl mb-3 text-indigo-500"></i>
            <p>Loading promotions...</p>
          </div>
        ) : filteredPromos.length === 0 ? (
          <div className="p-16 text-center text-gray-500 flex flex-col items-center">
            <div className="w-16 h-16 bg-indigo-50 text-indigo-300 rounded-full flex items-center justify-center mb-4">
              <i className="fas fa-ticket-alt text-2xl"></i>
            </div>
            <h3 className="text-lg font-medium text-gray-900 mb-1">No promos found</h3>
            <p className="text-gray-500 mb-4">No promotional codes matched your search.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-gray-50 border-b border-gray-200">
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Promo Code</th>
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Discount Value</th>
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Conditions</th>
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Validity Period</th>
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider text-center">Usage</th>
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider text-center">Status</th>
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider text-center">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {filteredPromos.map(promo => (
                  <tr key={promo.id} className="hover:bg-gray-50 transition-colors">
                    <td className="p-4">
                      <span className="inline-block border-2 border-dashed border-indigo-300 bg-indigo-50 text-indigo-700 font-bold px-3 py-1 rounded text-sm font-mono">
                        {promo.code}
                      </span>
                    </td>
                    <td className="p-4">
                      {promo.type === "FLAT" ? (
                        <span className="text-sm font-bold text-green-600">₹ {promo.value} OFF</span>
                      ) : (
                        <div>
                          <span className="text-sm font-bold text-green-600">{promo.value}% OFF</span>
                          {promo.max_discount && <p className="text-[10px] text-gray-500 mt-0.5">Max ₹ {promo.max_discount}</p>}
                        </div>
                      )}
                    </td>
                    <td className="p-4">
                      <p className="text-xs text-gray-700">Min. Spend: ₹ {promo.min_purchase}</p>
                    </td>
                    <td className="p-4">
                      <p className="text-xs text-gray-900 font-medium">{new Date(promo.valid_from).toLocaleDateString()} to</p>
                      <p className="text-xs text-gray-900 font-medium">{new Date(promo.valid_until).toLocaleDateString()}</p>
                    </td>
                    <td className="p-4 text-center">
                      <div className="w-full bg-gray-200 rounded-full h-1.5 mb-1">
                        <div 
                          className={`h-1.5 rounded-full ${promo.times_used >= promo.usage_limit ? 'bg-red-500' : 'bg-indigo-500'}`} 
                          style={{ width: `${Math.min(100, (promo.times_used / promo.usage_limit) * 100)}%` }}
                        ></div>
                      </div>
                      <span className="text-[10px] text-gray-500 font-medium">{promo.times_used} / {promo.usage_limit}</span>
                    </td>
                    <td className="p-4 text-center">
                      <span className={`text-[10px] font-bold px-2 py-1 rounded ${
                        promo.status === "ACTIVE" ? "bg-green-100 text-green-800" :
                        promo.status === "EXPIRED" ? "bg-gray-200 text-gray-800" : 
                        "bg-red-100 text-red-800"
                      }`}>
                        {promo.status}
                      </span>
                    </td>
                    <td className="p-4 text-center space-x-3">
                      <button className="text-indigo-600 hover:text-indigo-800 text-sm font-medium" title="Edit">
                        <i className="fas fa-edit"></i>
                      </button>
                      {promo.status === "ACTIVE" && (
                        <button className="text-red-600 hover:text-red-800 text-sm font-medium" title="Disable">
                          <i className="fas fa-ban"></i>
                        </button>
                      )}
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
