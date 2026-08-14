"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useStaffAuth } from "@/contexts/StaffAuthContext";
import { getApiUrl } from "@/lib/api";

interface Vendor {
  id: number;
  vendor_code: string;
  vendor_name: string;
  category: string;
  contact_person: string;
  mobile: string;
  total_purchases: number;
  outstanding_balance: number;
  status: string;
}

export default function VendorsPayablesPage() {
  const { token } = useStaffAuth();
  const [vendors, setVendors] = useState<Vendor[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [searchTerm, setSearchTerm] = useState("");

  useEffect(() => {
    if (!token) return;
    
    // Fallback data in case the endpoint isn't fully ready yet
    const fetchVendors = async () => {
      try {
        setLoading(true);
        // Using generic vendors endpoint
        const res = await fetch(`${getApiUrl()}/api/v1/staff/accounts/vendors`, {
          headers: {
            "Authorization": `Bearer ${token}`
          }
        });
        
        if (res.ok) {
          const data = await res.json();
          setVendors(data.items || []);
        } else {
          setVendors([]); // Fallback to empty
        }
      } catch (err: any) {
        console.warn("Failed to fetch vendors, using empty state", err);
        setVendors([]);
      } finally {
        setLoading(false);
      }
    };

    fetchVendors();
  }, [token]);

  const filteredVendors = vendors.filter(v => 
    v.vendor_name.toLowerCase().includes(searchTerm.toLowerCase()) || 
    v.vendor_code.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="flex justify-between items-end mb-8">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 tracking-tight">Vendors & Payables</h1>
          <p className="text-sm text-gray-500 mt-2">Manage suppliers, accounts payable, and vendor ledgers.</p>
        </div>
        <div className="flex space-x-3">
          <Link href="/staff/accounts/invoices" className="px-4 py-2 bg-white border border-gray-300 text-gray-700 font-medium rounded-lg shadow-sm hover:bg-gray-50 transition-colors">
            <i className="fas fa-file-invoice mr-2"></i> Purchase Invoices
          </Link>
          <button className="px-4 py-2 bg-indigo-600 text-white font-medium rounded-lg shadow-sm hover:bg-indigo-700 transition-colors">
            <i className="fas fa-plus mr-2"></i> Add Vendor
          </button>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <div className="bg-white p-5 rounded-xl shadow-sm border-l-4 border-indigo-500">
          <p className="text-xs font-bold text-gray-500 uppercase">Total Vendors</p>
          <p className="text-2xl font-bold text-gray-900 mt-1">{vendors.length}</p>
        </div>
        <div className="bg-white p-5 rounded-xl shadow-sm border-l-4 border-red-500">
          <p className="text-xs font-bold text-gray-500 uppercase">Total Payables</p>
          <p className="text-2xl font-bold text-red-600 mt-1">
            ₹{vendors.reduce((sum, v) => sum + (v.outstanding_balance > 0 ? v.outstanding_balance : 0), 0).toFixed(2)}
          </p>
        </div>
        <div className="bg-white p-5 rounded-xl shadow-sm border-l-4 border-yellow-500">
          <p className="text-xs font-bold text-gray-500 uppercase">Overdue Amount</p>
          <p className="text-2xl font-bold text-yellow-600 mt-1">₹0.00</p>
        </div>
        <div className="bg-white p-5 rounded-xl shadow-sm border-l-4 border-green-500">
          <p className="text-xs font-bold text-gray-500 uppercase">Advance Given</p>
          <p className="text-2xl font-bold text-green-600 mt-1">
            ₹{vendors.reduce((sum, v) => sum + (v.outstanding_balance < 0 ? Math.abs(v.outstanding_balance) : 0), 0).toFixed(2)}
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
                placeholder="Search vendors..." 
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10 pr-4 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:border-indigo-500 outline-none w-64" 
              />
            </div>
            <select className="px-3 py-2 border border-gray-300 rounded-lg text-sm bg-white text-gray-700 outline-none">
              <option value="">All Categories</option>
              <option value="MATERIAL">Raw Material</option>
              <option value="SERVICE">Services</option>
              <option value="LOGISTICS">Logistics</option>
            </select>
          </div>
          <button className="text-gray-500 hover:text-gray-700">
            <i className="fas fa-file-export mr-1"></i> Export
          </button>
        </div>
        
        {loading ? (
          <div className="p-12 text-center text-gray-500">
            <i className="fas fa-spinner fa-spin text-3xl mb-3 text-indigo-500"></i>
            <p>Loading vendors directory...</p>
          </div>
        ) : error ? (
          <div className="p-8 text-center text-red-500 bg-red-50">
            <i className="fas fa-exclamation-triangle text-2xl mb-2"></i>
            <p>{error}</p>
          </div>
        ) : filteredVendors.length === 0 ? (
          <div className="p-16 text-center text-gray-500 flex flex-col items-center">
            <div className="w-16 h-16 bg-indigo-50 text-indigo-300 rounded-full flex items-center justify-center mb-4">
              <i className="fas fa-store text-2xl"></i>
            </div>
            <h3 className="text-lg font-medium text-gray-900 mb-1">No vendors found</h3>
            <p className="text-gray-500 mb-4">There are currently no suppliers matching your criteria.</p>
            <button className="px-4 py-2 font-medium rounded hover:opacity-90 transition-colors bg-indigo-50 text-indigo-600">
              Add New Vendor
            </button>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-gray-50 border-b border-gray-200">
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Vendor Code</th>
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Vendor Name</th>
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Category</th>
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Contact</th>
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider text-right">YTD Purchases (₹)</th>
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider text-right">Payable Balance (₹)</th>
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider text-center">Status</th>
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider text-center">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {filteredVendors.map(vendor => (
                  <tr key={vendor.id} className="hover:bg-gray-50 transition-colors">
                    <td className="p-4 text-sm font-medium text-indigo-600">{vendor.vendor_code}</td>
                    <td className="p-4 text-sm font-bold text-gray-900">{vendor.vendor_name}</td>
                    <td className="p-4 text-sm text-gray-600">{vendor.category}</td>
                    <td className="p-4">
                      <p className="text-sm font-medium text-gray-900">{vendor.contact_person}</p>
                      <p className="text-xs text-gray-500">{vendor.mobile}</p>
                    </td>
                    <td className="p-4 text-sm font-medium text-gray-900 text-right">{vendor.total_purchases.toFixed(2)}</td>
                    <td className="p-4 text-right">
                      {vendor.outstanding_balance > 0 ? (
                        <span className="text-sm font-bold text-red-600">{vendor.outstanding_balance.toFixed(2)} Cr</span>
                      ) : vendor.outstanding_balance < 0 ? (
                        <span className="text-sm font-bold text-green-600">{Math.abs(vendor.outstanding_balance).toFixed(2)} Dr</span>
                      ) : (
                        <span className="text-sm text-gray-500">0.00</span>
                      )}
                    </td>
                    <td className="p-4 text-center">
                      <span className={`text-[10px] font-bold px-2 py-1 rounded ${
                        vendor.status === "ACTIVE" ? "bg-green-100 text-green-800" : "bg-red-100 text-red-800"
                      }`}>
                        {vendor.status}
                      </span>
                    </td>
                    <td className="p-4 text-center">
                      <Link href={`/staff/accounts/party-ledger?party_id=${vendor.id}`} className="text-indigo-600 hover:text-indigo-800 text-sm font-medium">
                        Ledger
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
