"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useStaffAuth } from "@/contexts/StaffAuthContext";
import { getApiUrl } from "@/lib/api";

interface StockItem {
  id: number;
  item_code: string;
  item_name: string;
  category: string;
  unit: string;
  current_stock: number;
  reorder_level: number;
  purchase_price: number;
  selling_price: number;
  status: string;
}

export default function StockItemsPage() {
  const { token } = useStaffAuth();
  const [items, setItems] = useState<StockItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [searchTerm, setSearchTerm] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("");

  useEffect(() => {
    if (!token) return;
    
    // Fallback data in case the endpoint isn't fully ready yet
    const fetchStockItems = async () => {
      try {
        setLoading(true);
        // Using generic inventory/stock-items endpoint
        const res = await fetch(`${getApiUrl()}/api/v1/staff/inventory/stock-items`, {
          headers: {
            "Authorization": `Bearer ${token}`
          }
        });
        
        if (res.ok) {
          const data = await res.json();
          setItems(data.items || []);
        } else {
          setItems([]); // Fallback to empty
        }
      } catch (err: any) {
        console.warn("Failed to fetch stock items, using empty state", err);
        setItems([]);
      } finally {
        setLoading(false);
      }
    };

    fetchStockItems();
  }, [token]);

  const filteredItems = items.filter(i => 
    (i.item_name.toLowerCase().includes(searchTerm.toLowerCase()) || 
     i.item_code.toLowerCase().includes(searchTerm.toLowerCase())) &&
    (categoryFilter === "" || i.category === categoryFilter)
  );

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="flex justify-between items-end mb-8">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 tracking-tight">Stock Items Master</h1>
          <p className="text-sm text-gray-500 mt-2">Manage raw materials, work-in-progress, and finished goods inventory.</p>
        </div>
        <div className="flex space-x-3">
          <Link href="/staff/accounts/bom" className="px-4 py-2 bg-white border border-gray-300 text-gray-700 font-medium rounded-lg shadow-sm hover:bg-gray-50 transition-colors">
            <i className="fas fa-sitemap mr-2"></i> Bill of Materials
          </Link>
          <button className="px-4 py-2 bg-indigo-600 text-white font-medium rounded-lg shadow-sm hover:bg-indigo-700 transition-colors">
            <i className="fas fa-plus mr-2"></i> Add Item
          </button>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <div className="bg-white p-5 rounded-xl shadow-sm border-l-4 border-indigo-500">
          <p className="text-xs font-bold text-gray-500 uppercase">Total Items</p>
          <p className="text-2xl font-bold text-gray-900 mt-1">{items.length}</p>
        </div>
        <div className="bg-white p-5 rounded-xl shadow-sm border-l-4 border-green-500">
          <p className="text-xs font-bold text-gray-500 uppercase">Total Inventory Value</p>
          <p className="text-2xl font-bold text-green-600 mt-1">
            ₹{items.reduce((sum, item) => sum + (item.current_stock * item.purchase_price), 0).toFixed(2)}
          </p>
        </div>
        <div className="bg-white p-5 rounded-xl shadow-sm border-l-4 border-red-500">
          <p className="text-xs font-bold text-gray-500 uppercase">Low Stock Alerts</p>
          <p className="text-2xl font-bold text-red-600 mt-1">
            {items.filter(item => item.current_stock <= item.reorder_level).length}
          </p>
        </div>
        <div className="bg-white p-5 rounded-xl shadow-sm border-l-4 border-blue-500">
          <p className="text-xs font-bold text-gray-500 uppercase">Categories</p>
          <p className="text-2xl font-bold text-blue-600 mt-1">
            {new Set(items.map(item => item.category)).size}
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
                placeholder="Search items by name or code..." 
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10 pr-4 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:border-indigo-500 outline-none w-64" 
              />
            </div>
            <select 
              className="px-3 py-2 border border-gray-300 rounded-lg text-sm bg-white text-gray-700 outline-none"
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value)}
            >
              <option value="">All Categories</option>
              <option value="RAW_MATERIAL">Raw Material</option>
              <option value="WIP">Work in Progress</option>
              <option value="FINISHED_GOODS">Finished Goods</option>
              <option value="CONSUMABLES">Consumables</option>
            </select>
          </div>
          <div className="flex space-x-2">
            <button className="text-gray-500 hover:text-gray-700 px-2 py-1">
              <i className="fas fa-file-import mr-1"></i> Import
            </button>
            <button className="text-gray-500 hover:text-gray-700 px-2 py-1">
              <i className="fas fa-file-export mr-1"></i> Export
            </button>
          </div>
        </div>
        
        {loading ? (
          <div className="p-12 text-center text-gray-500">
            <i className="fas fa-spinner fa-spin text-3xl mb-3 text-indigo-500"></i>
            <p>Loading inventory...</p>
          </div>
        ) : error ? (
          <div className="p-8 text-center text-red-500 bg-red-50">
            <i className="fas fa-exclamation-triangle text-2xl mb-2"></i>
            <p>{error}</p>
          </div>
        ) : filteredItems.length === 0 ? (
          <div className="p-16 text-center text-gray-500 flex flex-col items-center">
            <div className="w-16 h-16 bg-indigo-50 text-indigo-300 rounded-full flex items-center justify-center mb-4">
              <i className="fas fa-boxes text-2xl"></i>
            </div>
            <h3 className="text-lg font-medium text-gray-900 mb-1">No items found</h3>
            <p className="text-gray-500 mb-4">There are currently no items matching your criteria.</p>
            <button className="px-4 py-2 font-medium rounded hover:opacity-90 transition-colors bg-indigo-50 text-indigo-600">
              Add New Stock Item
            </button>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-gray-50 border-b border-gray-200">
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Item Code</th>
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Item Name</th>
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Category</th>
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider text-right">Current Stock</th>
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider text-right">Unit Price (₹)</th>
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider text-center">Status</th>
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider text-center">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {filteredItems.map(item => (
                  <tr key={item.id} className="hover:bg-gray-50 transition-colors">
                    <td className="p-4 text-sm font-medium text-indigo-600">{item.item_code}</td>
                    <td className="p-4">
                      <p className="text-sm font-bold text-gray-900">{item.item_name}</p>
                    </td>
                    <td className="p-4 text-sm text-gray-600">
                      <span className="bg-gray-100 text-gray-700 px-2 py-0.5 rounded text-xs font-medium">
                        {item.category.replace('_', ' ')}
                      </span>
                    </td>
                    <td className="p-4 text-right">
                      <p className={`text-sm font-bold ${item.current_stock <= item.reorder_level ? 'text-red-600' : 'text-gray-900'}`}>
                        {item.current_stock} {item.unit}
                      </p>
                      {item.current_stock <= item.reorder_level && (
                        <p className="text-[10px] text-red-500 font-semibold uppercase mt-0.5">Reorder Alert</p>
                      )}
                    </td>
                    <td className="p-4 text-right">
                      <p className="text-sm font-medium text-gray-900">{item.purchase_price.toFixed(2)}</p>
                      <p className="text-xs text-gray-500">Sell: {item.selling_price.toFixed(2)}</p>
                    </td>
                    <td className="p-4 text-center">
                      <span className={`text-[10px] font-bold px-2 py-1 rounded ${
                        item.status === "ACTIVE" ? "bg-green-100 text-green-800" : "bg-red-100 text-red-800"
                      }`}>
                        {item.status}
                      </span>
                    </td>
                    <td className="p-4 text-center">
                      <Link href={`/staff/accounts/stock-items/${item.id}`} className="text-indigo-600 hover:text-indigo-800 text-sm font-medium mx-2">
                        Edit
                      </Link>
                      <button className="text-gray-500 hover:text-gray-800 text-sm font-medium mx-2">
                        History
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
