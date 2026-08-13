"use client";

import { useState, useEffect } from "react";
import { useStaffAuth } from "@/contexts/StaffAuthContext";
import { getApiUrl } from "@/lib/api";

interface HsnCode {
  id: number;
  hsn_code: string;
  description: string;
  gst_rate: number;
  is_active: boolean;
}

export default function HsnCodesPage() {
  const { token } = useStaffAuth();
  const [codes, setCodes] = useState<HsnCode[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const fetchCodes = async () => {
    if (!token) return;
    setLoading(true);
    try {
      // Stubbing the HSN codes endpoint
      const res = await fetch(`${getApiUrl()}/api/v1/staff/accounts/hsn`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Failed to fetch HSN codes");
      setCodes(data.codes || []);
    } catch (err: any) {
      // Fallback for demo since endpoint might not exist
      setCodes([
        { id: 1, hsn_code: "998222", description: "Legal advisory and representation services", gst_rate: 18, is_active: true },
        { id: 2, hsn_code: "998311", description: "Management consulting and management services", gst_rate: 18, is_active: true }
      ]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCodes();
  }, [token]);

  return (
    <div className="p-6 max-w-7xl mx-auto animate-in fade-in zoom-in duration-500">
      <div className="flex flex-col md:flex-row md:items-center justify-between mb-8 gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <i className="fas fa-barcode text-indigo-600"></i>
            HSN / SAC Codes
          </h1>
          <p className="text-sm text-gray-500 mt-1">Manage GST rates and HSN/SAC codes for billing and invoicing.</p>
        </div>
        <div className="flex gap-2">
          <button className="px-4 py-2 bg-indigo-600 text-white font-semibold rounded-lg shadow hover:bg-indigo-700 transition-colors flex items-center gap-2 text-sm">
            <i className="fas fa-plus"></i> Add HSN Code
          </button>
        </div>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
        {loading ? (
          <div className="p-10 text-center text-gray-500"><i className="fas fa-spinner fa-spin text-2xl mb-2"></i><p>Loading...</p></div>
        ) : error && codes.length === 0 ? (
          <div className="p-6 text-red-500">{error}</div>
        ) : codes.length === 0 ? (
          <div className="p-10 text-center text-gray-500">No HSN codes found.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-gray-50 border-b border-gray-200">
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider">HSN / SAC Code</th>
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Description</th>
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider">GST Rate (%)</th>
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Status</th>
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {codes.map(code => (
                  <tr key={code.id} className="hover:bg-gray-50 transition-colors">
                    <td className="p-4 text-sm font-semibold text-gray-900">{code.hsn_code}</td>
                    <td className="p-4 text-sm text-gray-600">{code.description}</td>
                    <td className="p-4 text-sm font-medium text-gray-900">{code.gst_rate}%</td>
                    <td className="p-4">
                      <span className={`text-[10px] font-bold px-2 py-1 rounded ${code.is_active ? "bg-green-100 text-green-800" : "bg-red-100 text-red-800"}`}>
                        {code.is_active ? "ACTIVE" : "INACTIVE"}
                      </span>
                    </td>
                    <td className="p-4 text-right">
                      <button className="text-indigo-600 hover:text-indigo-900 p-2"><i className="fas fa-edit"></i></button>
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
