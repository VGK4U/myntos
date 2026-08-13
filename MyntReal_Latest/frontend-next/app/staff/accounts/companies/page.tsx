"use client";

import { useState, useEffect } from "react";
import { useStaffAuth } from "@/contexts/StaffAuthContext";
import { getApiUrl } from "@/lib/api";

interface Company {
  id: number;
  name: string;
  registration_number: string;
  gstin: string;
  pan: string;
  is_active: boolean;
}

export default function CompaniesPage() {
  const { token } = useStaffAuth();
  const [companies, setCompanies] = useState<Company[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const fetchCompanies = async () => {
    if (!token) return;
    setLoading(true);
    try {
      const res = await fetch(`${getApiUrl()}/api/v1/staff/accounts/companies`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Failed to fetch companies");
      setCompanies(data.companies || []);
    } catch (err: any) {
      // Fallback for demo
      setCompanies([
        { id: 1, name: "MyntReal Tech", registration_number: "CIN12345678", gstin: "29AABCU9603R1ZX", pan: "AABCU9603R", is_active: true }
      ]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCompanies();
  }, [token]);

  return (
    <div className="p-6 max-w-7xl mx-auto animate-in fade-in zoom-in duration-500">
      <div className="flex flex-col md:flex-row md:items-center justify-between mb-8 gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <i className="fas fa-building text-indigo-600"></i>
            Internal Companies
          </h1>
          <p className="text-sm text-gray-500 mt-1">Manage multiple entity profiles for accounting.</p>
        </div>
        <div className="flex gap-2">
          <button className="px-4 py-2 bg-indigo-600 text-white font-semibold rounded-lg shadow hover:bg-indigo-700 transition-colors flex items-center gap-2 text-sm">
            <i className="fas fa-plus"></i> Add Company
          </button>
        </div>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
        {loading ? (
          <div className="p-10 text-center text-gray-500"><i className="fas fa-spinner fa-spin text-2xl mb-2"></i><p>Loading...</p></div>
        ) : error && companies.length === 0 ? (
          <div className="p-6 text-red-500">{error}</div>
        ) : companies.length === 0 ? (
          <div className="p-10 text-center text-gray-500">No companies configured.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-gray-50 border-b border-gray-200">
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Company Name</th>
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Registration #</th>
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider">GSTIN</th>
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider">PAN</th>
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Status</th>
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {companies.map(comp => (
                  <tr key={comp.id} className="hover:bg-gray-50 transition-colors">
                    <td className="p-4 text-sm font-semibold text-gray-900">{comp.name}</td>
                    <td className="p-4 text-sm text-gray-600">{comp.registration_number || "-"}</td>
                    <td className="p-4 text-sm font-medium text-gray-900">{comp.gstin || "-"}</td>
                    <td className="p-4 text-sm font-medium text-gray-900">{comp.pan || "-"}</td>
                    <td className="p-4">
                      <span className={`text-[10px] font-bold px-2 py-1 rounded ${comp.is_active ? "bg-green-100 text-green-800" : "bg-red-100 text-red-800"}`}>
                        {comp.is_active ? "ACTIVE" : "INACTIVE"}
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
