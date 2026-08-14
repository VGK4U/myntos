"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useStaffAuth } from "@/contexts/StaffAuthContext";
import { getApiUrl } from "@/lib/api";

interface VGKVendor {
  id: number;
  business_name: string;
  category: string;
  contact_person: string;
  phone: string;
  location: string;
  commission_rate: number; // Percentage
  status: string; // ACTIVE, PENDING, SUSPENDED
  total_sales: number;
}

export default function VGKVendorsPage() {
  const { token } = useStaffAuth();
  const [vendors, setVendors] = useState<VGKVendor[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("");

  useEffect(() => {
    if (!token) return;
    
    const fetchVendors = async () => {
      try {
        setLoading(true);
        // Generic endpoint for Staff to view VGK vendors
        const res = await fetch(`${getApiUrl()}/api/v1/staff/vgk/vendors`, {
          headers: {
            "Authorization": `Bearer ${token}`
          }
        });
        
        if (res.ok) {
          const data = await res.json();
          setVendors(data.items || []);
        } else {
          // Fallback mockup data
          setVendors([
            { id: 1, business_name: "EcoDrive Motors", category: "AUTOMOTIVE", contact_person: "Ramesh Singh", phone: "+91 9123456780", location: "Mumbai Central", commission_rate: 15, status: "ACTIVE", total_sales: 1250000 },
            { id: 2, business_name: "SunPower Solutions", category: "ENERGY", contact_person: "Anita Desai", phone: "+91 9234567801", location: "Pune West", commission_rate: 12, status: "ACTIVE", total_sales: 850000 },
            { id: 3, business_name: "TechFix Center", category: "ELECTRONICS", contact_person: "Vikas P", phone: "+91 9345678012", location: "Andheri East", commission_rate: 10, status: "PENDING", total_sales: 0 },
            { id: 4, business_name: "GreenLife Grocers", category: "RETAIL", contact_person: "Meena K", phone: "+91 9456780123", location: "Bandra", commission_rate: 5, status: "ACTIVE", total_sales: 45000 },
          ]);
        }
      } catch (err) {
        console.warn("Failed to fetch vendors", err);
      } finally {
        setLoading(false);
      }
    };

    fetchVendors();
  }, [token]);

  const filteredVendors = vendors.filter(v => 
    (v.business_name.toLowerCase().includes(searchTerm.toLowerCase()) || 
     v.contact_person.toLowerCase().includes(searchTerm.toLowerCase()) ||
     v.phone.includes(searchTerm)) &&
    (categoryFilter === "" || v.category === categoryFilter)
  );

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="flex justify-between items-end mb-8">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 tracking-tight">VGK Vendor Network</h1>
          <p className="text-sm text-gray-500 mt-2">Onboard and manage partner businesses offering services to VGK members.</p>
        </div>
        <div className="flex space-x-3">
          <button className="px-4 py-2 bg-white border border-gray-300 text-gray-700 font-medium rounded-lg shadow-sm hover:bg-gray-50 transition-colors">
            <i className="fas fa-tags mr-2"></i> Vendor Categories
          </button>
          <button className="px-4 py-2 bg-indigo-600 text-white font-medium rounded-lg shadow-sm hover:bg-indigo-700 transition-colors">
            <i className="fas fa-store mr-2"></i> Onboard Vendor
          </button>
        </div>
      </div>

      {/* Content Area */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
        <div className="p-4 border-b border-gray-100 flex justify-between items-center bg-gray-50 flex-wrap gap-4">
          <div className="flex items-center space-x-4 flex-grow max-w-2xl">
            <div className="relative flex-grow">
              <i className="fas fa-search absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400"></i>
              <input 
                type="text" 
                placeholder="Search business name, contact, or phone..." 
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10 pr-4 py-2 w-full border border-gray-300 rounded-lg text-sm focus:ring-2 focus:border-indigo-500 outline-none" 
              />
            </div>
            <select 
              className="px-3 py-2 border border-gray-300 rounded-lg text-sm bg-white text-gray-700 outline-none w-48"
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value)}
            >
              <option value="">All Categories</option>
              <option value="AUTOMOTIVE">Automotive & EVs</option>
              <option value="ENERGY">Solar & Energy</option>
              <option value="ELECTRONICS">Electronics</option>
              <option value="RETAIL">Retail & Groceries</option>
            </select>
          </div>
          <button className="px-3 py-2 border border-gray-300 text-gray-700 text-sm font-medium rounded-lg hover:bg-gray-50">
            <i className="fas fa-download mr-1"></i> Export List
          </button>
        </div>
        
        {loading ? (
          <div className="p-12 text-center text-gray-500">
            <i className="fas fa-spinner fa-spin text-3xl mb-3 text-indigo-500"></i>
            <p>Loading vendor network...</p>
          </div>
        ) : filteredVendors.length === 0 ? (
          <div className="p-16 text-center text-gray-500 flex flex-col items-center">
            <div className="w-16 h-16 bg-indigo-50 text-indigo-300 rounded-full flex items-center justify-center mb-4">
              <i className="fas fa-store-slash text-2xl"></i>
            </div>
            <h3 className="text-lg font-medium text-gray-900 mb-1">No vendors found</h3>
            <p className="text-gray-500 mb-4">No vendors matched your search criteria.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-gray-50 border-b border-gray-200">
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Business Info</th>
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Contact Details</th>
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Category</th>
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider text-center">Comm. Rate</th>
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider text-right">Total Sales</th>
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider text-center">Status</th>
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider text-center">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {filteredVendors.map(vendor => (
                  <tr key={vendor.id} className="hover:bg-gray-50 transition-colors">
                    <td className="p-4">
                      <p className="text-sm font-bold text-gray-900">{vendor.business_name}</p>
                      <p className="text-xs text-gray-500 mt-0.5"><i className="fas fa-map-marker-alt text-gray-400 mr-1"></i> {vendor.location}</p>
                    </td>
                    <td className="p-4">
                      <p className="text-sm font-medium text-gray-800">{vendor.contact_person}</p>
                      <p className="text-xs text-gray-500">{vendor.phone}</p>
                    </td>
                    <td className="p-4">
                      <span className="inline-block bg-gray-100 text-gray-700 px-2 py-0.5 rounded text-[10px] font-bold">
                        {vendor.category}
                      </span>
                    </td>
                    <td className="p-4 text-center">
                      <span className="text-sm font-bold text-indigo-600">{vendor.commission_rate}%</span>
                    </td>
                    <td className="p-4 text-right">
                      <span className="text-sm font-medium text-gray-900">₹ {(vendor.total_sales / 1000).toFixed(1)}k</span>
                    </td>
                    <td className="p-4 text-center">
                      <span className={`text-[10px] font-bold px-2 py-1 rounded ${
                        vendor.status === "ACTIVE" ? "bg-green-100 text-green-800" :
                        vendor.status === "PENDING" ? "bg-amber-100 text-amber-800" : 
                        "bg-red-100 text-red-800"
                      }`}>
                        {vendor.status}
                      </span>
                    </td>
                    <td className="p-4 text-center space-x-3">
                      <button className="text-indigo-600 hover:text-indigo-800 text-sm font-medium" title="View Details">
                        <i className="fas fa-store"></i>
                      </button>
                      <button className="text-green-600 hover:text-green-800 text-sm font-medium" title="Products">
                        <i className="fas fa-box"></i>
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
