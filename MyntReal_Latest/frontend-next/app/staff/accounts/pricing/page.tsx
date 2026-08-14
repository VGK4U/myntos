"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useStaffAuth } from "@/contexts/StaffAuthContext";
import { getApiUrl } from "@/lib/api";

interface PricingRule {
  id: number;
  rule_name: string;
  target: "ALL_CUSTOMERS" | "CUSTOMER_CATEGORY" | "SPECIFIC_CUSTOMER";
  target_value: string; // e.g. 'WHOLESALE' or customer ID
  product_category: string;
  discount_percentage: number;
  valid_from: string;
  valid_until: string;
  status: string;
}

export default function PricingRulesPage() {
  const { token } = useStaffAuth();
  const [rules, setRules] = useState<PricingRule[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [searchTerm, setSearchTerm] = useState("");

  useEffect(() => {
    if (!token) return;
    
    const fetchRules = async () => {
      try {
        setLoading(true);
        // Using generic pricing endpoint
        const res = await fetch(`${getApiUrl()}/api/v1/staff/inventory/pricing-rules`, {
          headers: {
            "Authorization": `Bearer ${token}`
          }
        });
        
        if (res.ok) {
          const data = await res.json();
          setRules(data.items || []);
        } else {
          setRules([]); // Fallback
        }
      } catch (err: any) {
        console.warn("Failed to fetch pricing rules, using empty state", err);
        setRules([]);
      } finally {
        setLoading(false);
      }
    };

    fetchRules();
  }, [token]);

  const filteredRules = rules.filter(r => 
    r.rule_name.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="flex justify-between items-end mb-8">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 tracking-tight">Pricing & Discount Rules</h1>
          <p className="text-sm text-gray-500 mt-2">Configure conditional pricing, promotional discounts, and custom rate lists.</p>
        </div>
        <div className="flex space-x-3">
          <Link href="/staff/accounts/stock-items" className="px-4 py-2 bg-white border border-gray-300 text-gray-700 font-medium rounded-lg shadow-sm hover:bg-gray-50 transition-colors">
            <i className="fas fa-boxes mr-2"></i> Stock Items
          </Link>
          <button className="px-4 py-2 bg-indigo-600 text-white font-medium rounded-lg shadow-sm hover:bg-indigo-700 transition-colors">
            <i className="fas fa-plus mr-2"></i> Add Rule
          </button>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <div className="bg-white p-5 rounded-xl shadow-sm border-l-4 border-indigo-500">
          <p className="text-xs font-bold text-gray-500 uppercase">Active Rules</p>
          <p className="text-2xl font-bold text-gray-900 mt-1">
            {rules.filter(r => r.status === "ACTIVE").length}
          </p>
        </div>
        <div className="bg-white p-5 rounded-xl shadow-sm border-l-4 border-amber-500">
          <p className="text-xs font-bold text-gray-500 uppercase">Expiring Soon</p>
          <p className="text-2xl font-bold text-amber-600 mt-1">
            {rules.filter(r => {
              if (!r.valid_until) return false;
              const daysUntil = (new Date(r.valid_until).getTime() - Date.now()) / (1000 * 3600 * 24);
              return daysUntil > 0 && daysUntil <= 7;
            }).length}
          </p>
        </div>
        <div className="bg-white p-5 rounded-xl shadow-sm border-l-4 border-gray-500">
          <p className="text-xs font-bold text-gray-500 uppercase">Inactive / Expired</p>
          <p className="text-2xl font-bold text-gray-600 mt-1">
            {rules.filter(r => r.status === "INACTIVE" || r.status === "EXPIRED").length}
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
                placeholder="Search rules..." 
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10 pr-4 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:border-indigo-500 outline-none w-64" 
              />
            </div>
            <select className="px-3 py-2 border border-gray-300 rounded-lg text-sm bg-white text-gray-700 outline-none">
              <option value="">All Statuses</option>
              <option value="ACTIVE">Active</option>
              <option value="INACTIVE">Inactive</option>
              <option value="EXPIRED">Expired</option>
            </select>
          </div>
        </div>
        
        {loading ? (
          <div className="p-12 text-center text-gray-500">
            <i className="fas fa-spinner fa-spin text-3xl mb-3 text-indigo-500"></i>
            <p>Loading pricing rules...</p>
          </div>
        ) : error ? (
          <div className="p-8 text-center text-red-500 bg-red-50">
            <i className="fas fa-exclamation-triangle text-2xl mb-2"></i>
            <p>{error}</p>
          </div>
        ) : filteredRules.length === 0 ? (
          <div className="p-16 text-center text-gray-500 flex flex-col items-center">
            <div className="w-16 h-16 bg-indigo-50 text-indigo-300 rounded-full flex items-center justify-center mb-4">
              <i className="fas fa-tags text-2xl"></i>
            </div>
            <h3 className="text-lg font-medium text-gray-900 mb-1">No pricing rules</h3>
            <p className="text-gray-500 mb-4">There are currently no active pricing or discount rules configured.</p>
            <button className="px-4 py-2 font-medium rounded hover:opacity-90 transition-colors bg-indigo-50 text-indigo-600">
              Create Pricing Rule
            </button>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-gray-50 border-b border-gray-200">
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Rule Name</th>
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Applies To (Target)</th>
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Product Category</th>
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider text-right">Discount %</th>
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider text-center">Validity</th>
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider text-center">Status</th>
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider text-center">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {filteredRules.map(rule => (
                  <tr key={rule.id} className="hover:bg-gray-50 transition-colors">
                    <td className="p-4 font-medium text-gray-900">{rule.rule_name}</td>
                    <td className="p-4">
                      <p className="text-sm font-bold text-indigo-600">{rule.target.replace('_', ' ')}</p>
                      {rule.target !== 'ALL_CUSTOMERS' && (
                        <p className="text-xs text-gray-500">{rule.target_value}</p>
                      )}
                    </td>
                    <td className="p-4 text-sm text-gray-600">
                      <span className="bg-gray-100 text-gray-700 px-2 py-1 rounded text-xs font-medium">
                        {rule.product_category === '*' ? 'All Categories' : rule.product_category}
                      </span>
                    </td>
                    <td className="p-4 text-right">
                      <span className="text-sm font-bold text-green-600">
                        {rule.discount_percentage}% OFF
                      </span>
                    </td>
                    <td className="p-4 text-center">
                      <p className="text-xs text-gray-600">From: {new Date(rule.valid_from).toLocaleDateString()}</p>
                      {rule.valid_until ? (
                        <p className="text-xs text-gray-600">To: {new Date(rule.valid_until).toLocaleDateString()}</p>
                      ) : (
                        <p className="text-xs text-indigo-600 font-medium">No Expiry</p>
                      )}
                    </td>
                    <td className="p-4 text-center">
                      <span className={`text-[10px] font-bold px-2 py-1 rounded ${
                        rule.status === "ACTIVE" ? "bg-green-100 text-green-800" : 
                        rule.status === "EXPIRED" ? "bg-red-100 text-red-800" :
                        "bg-gray-100 text-gray-800"
                      }`}>
                        {rule.status}
                      </span>
                    </td>
                    <td className="p-4 text-center">
                      <button className="text-indigo-600 hover:text-indigo-800 text-sm font-medium">
                        Edit
                      </button>
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
