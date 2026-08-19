"use client";

import React, { useState, useEffect } from "react";
import api from "@/lib/api";
import { useStaffAuth } from "@/contexts/StaffAuthContext";

export default function GenericAccountsPage() {
  const { token } = useStaffAuth();
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [pageTitle, setPageTitle] = useState("Accounts Module");

  useEffect(() => {
    if (typeof window !== "undefined") {
      const path = window.location.pathname.split("/").pop() || "";
      setPageTitle(path.replace(/-/g, " ").replace(/\w/g, l => l.toUpperCase()));
    }
    const fetchData = async () => {
      try {
        const res = await api.get("/staff/accounts/companies");
        if (res.data) {
          setData(res.data.companies || []);
        }
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [token]);

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6 animate-in fade-in zoom-in duration-500">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900 tracking-tight">{pageTitle}</h1>
      </div>
      
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
        {loading ? (
           <div className="p-12 text-center text-gray-500"><i className="fas fa-spinner fa-spin mr-2"></i>Loading data...</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-gray-50 border-b border-gray-100 text-sm font-bold text-gray-900 uppercase tracking-wider">
                  <th className="p-4">ID</th>
                  <th className="p-4">Details</th>
                  <th className="p-4">Status</th>
                  <th className="p-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {data.length === 0 ? (
                  <tr><td colSpan={4} className="p-8 text-center text-gray-500">No records found.</td></tr>
                ) : (
                  data.map((item, i) => (
                    <tr key={i} className="hover:bg-gray-50 transition-colors">
                      <td className="p-4 text-sm text-gray-600">#{item.id || i+1}</td>
                      <td className="p-4">
                        <div className="font-medium text-gray-900">{item.company_name || item.name || "Record"}</div>
                      </td>
                      <td className="p-4">
                        <span className="px-2 py-1 bg-emerald-100 text-emerald-700 text-xs font-bold rounded-full">Active</span>
                      </td>
                      <td className="p-4 text-right">
                        <button className="text-indigo-600 hover:text-indigo-800 text-sm font-medium">View</button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
