"use client";

import React, { useState, useEffect } from 'react';
import api from '@/lib/api';
import Link from 'next/link';

export default function StockLedgerPage() {
  const [activeCategory, setActiveCategory] = useState("helmet"); // helmet, battery, charger, controller, motor, spare_parts
  const [sheetData, setSheetData] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState("");

  const categories = [
    { id: "helmet", label: "Helmets", icon: "fa-hard-hat" },
    { id: "battery", label: "Batteries", icon: "fa-battery-full" },
    { id: "charger", label: "Chargers", icon: "fa-plug" },
    { id: "controller", label: "Controllers", icon: "fa-microchip" },
    { id: "motor", label: "Motors", icon: "fa-cogs" },
    { id: "spare_parts", label: "Spares", icon: "fa-tools" }
  ];

  useEffect(() => {
    fetchStockSheet();
  }, [activeCategory]);

  const fetchStockSheet = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.get(`/staff/inventory/accessories/${activeCategory}/sheet`);
      if (res.data) {
        setSheetData(Array.isArray(res.data) ? res.data : res.data.sheet || []);
      }
    } catch (err: any) {
      console.error("Failed to fetch stock sheet:", err);
      setError("Could not load inventory ledger. Please check backend connection.");
    } finally {
      setLoading(false);
    }
  };

  const filteredData = sheetData.filter((item: any) => {
    if (!searchTerm) return true;
    const s = searchTerm.toLowerCase();
    return (
      (item.item_name || "").toLowerCase().includes(s) ||
      (item.brand_name || "").toLowerCase().includes(s) ||
      (item.hsn_code || "").toLowerCase().includes(s)
    );
  });

  return (
    <div className="p-6 lg:p-10 max-w-[1600px] mx-auto bg-slate-50 min-h-screen">
      
      {/* Header Section */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-6 mb-8">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-50 border border-emerald-100 text-emerald-700 text-xs font-bold uppercase tracking-wider mb-2">
            Logistics & Procurement
          </div>
          <h1 className="text-3xl font-black text-slate-900 tracking-tight">Master Stock Ledger</h1>
          <p className="text-slate-500 mt-1">Real-time inventory tracking for all EV accessories and parts.</p>
        </div>
        
        <div className="flex gap-3">
          <button className="px-5 py-2.5 bg-slate-900 text-white font-bold rounded-xl shadow-lg shadow-slate-900/20 hover:bg-slate-800 transition-all flex items-center gap-2 text-sm">
            <i className="fas fa-file-excel"></i> Export CSV
          </button>
        </div>
      </div>

      {/* Category Navigation */}
      <div className="bg-white p-2 rounded-2xl border border-slate-200 shadow-sm flex flex-wrap gap-2 mb-6">
        {categories.map(c => (
          <button 
            key={c.id}
            onClick={() => setActiveCategory(c.id)}
            className={`flex-1 min-w-[120px] px-4 py-3 rounded-xl text-sm font-bold transition-all flex items-center justify-center gap-2 ${
              activeCategory === c.id 
                ? 'bg-emerald-50 text-emerald-700 shadow-sm border border-emerald-100' 
                : 'text-slate-500 hover:bg-slate-50 border border-transparent'
            }`}
          >
            <i className={`fas ${c.icon}`}></i> {c.label}
          </button>
        ))}
      </div>

      {/* Main Table */}
      <div className="bg-white rounded-3xl border border-slate-200 shadow-sm overflow-hidden flex flex-col">
        <div className="p-5 border-b border-slate-100 flex items-center justify-between">
          <h2 className="font-bold text-slate-800 flex items-center gap-2">
            Current Inventory Status
          </h2>
          <div className="relative">
            <i className="fas fa-search absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 text-xs"></i>
            <input 
              type="text" 
              placeholder="Search items, brands, HSN..." 
              value={searchTerm}
              onChange={e => setSearchTerm(e.target.value)}
              className="pl-9 pr-4 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 w-64 bg-slate-50" 
            />
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-slate-50/50 border-b border-slate-100">
                <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider">SKU / Item</th>
                <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider">HSN Code</th>
                <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider text-right">IN (Qty)</th>
                <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider text-right">OUT (Qty)</th>
                <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider text-right">Current Stock</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {loading ? (
                <tr>
                  <td colSpan={5} className="px-6 py-12 text-center text-slate-400">
                    <i className="fas fa-circle-notch fa-spin text-3xl mb-3"></i>
                    <p className="font-medium">Syncing Warehouse Data...</p>
                  </td>
                </tr>
              ) : error ? (
                <tr>
                  <td colSpan={5} className="px-6 py-12 text-center text-rose-500">
                    <i className="fas fa-exclamation-triangle text-3xl mb-3"></i>
                    <p className="font-medium">{error}</p>
                  </td>
                </tr>
              ) : filteredData.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-6 py-16 text-center text-slate-500">
                    <div className="w-20 h-20 bg-slate-100 rounded-full flex items-center justify-center text-3xl text-slate-400 mx-auto mb-4">
                      <i className="fas fa-box-open"></i>
                    </div>
                    <p className="font-bold text-slate-700 text-lg mb-1">No items found</p>
                    <p className="text-sm">There is no stock data for this category.</p>
                  </td>
                </tr>
              ) : (
                filteredData.map((item, idx) => (
                  <tr key={idx} className="hover:bg-emerald-50/30 transition-colors group">
                    <td className="px-6 py-4">
                      <p className="font-bold text-slate-900 group-hover:text-emerald-700 transition-colors">{item.item_name || 'Unknown Item'}</p>
                      <p className="text-xs text-slate-500 mt-0.5">{item.brand_name || 'Generic'}</p>
                    </td>
                    <td className="px-6 py-4">
                      <span className="text-xs font-mono text-slate-600 bg-slate-100 border border-slate-200 px-2 py-1 rounded">
                        {item.hsn_code || 'N/A'}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-right">
                      <span className="font-bold text-blue-600">+{item.total_in || 0}</span>
                    </td>
                    <td className="px-6 py-4 text-right">
                      <span className="font-bold text-rose-600">-{item.total_out || 0}</span>
                    </td>
                    <td className="px-6 py-4 text-right">
                      <span className={`font-black text-lg ${
                        (item.current_stock || 0) <= (item.min_threshold || 5) ? 'text-amber-600' : 'text-emerald-600'
                      }`}>
                        {item.current_stock || 0}
                      </span>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
