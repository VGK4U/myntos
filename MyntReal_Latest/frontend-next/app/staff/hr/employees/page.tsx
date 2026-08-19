"use client";

import React, { useState, useEffect } from 'react';
import api from '@/lib/api';
import Link from 'next/link';
import { useStaffAuth } from '@/contexts/StaffAuthContext';

export default function StaffEmployeesPage() {
  const { user } = useStaffAuth();
  const [employees, setEmployees] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // Search and filter states
  const [searchTerm, setSearchTerm] = useState("");
  const [departmentFilter, setDepartmentFilter] = useState("ALL");
  const [statusFilter, setStatusFilter] = useState("Active");

  useEffect(() => {
    fetchEmployees();
  }, [statusFilter]);

  const fetchEmployees = async () => {
    setLoading(true);
    setError(null);
    try {
      // Backend: /api/v1/staff/employees
      const res = await api.get(`/staff/employees?status=${statusFilter}`);
      
      if (res.data && res.data.employees) {
        setEmployees(res.data.employees);
      } else if (Array.isArray(res.data)) {
        setEmployees(res.data);
      }
    } catch (err: any) {
      console.error("Failed to fetch employees:", err);
      setError("Could not load employee directory. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  // Client-side filtering
  const filteredEmployees = employees.filter(emp => {
    const matchesSearch = 
      (emp.name || "").toLowerCase().includes(searchTerm.toLowerCase()) || 
      (emp.emp_code || "").toLowerCase().includes(searchTerm.toLowerCase()) ||
      (emp.email || "").toLowerCase().includes(searchTerm.toLowerCase());
      
    const matchesDept = departmentFilter === "ALL" || emp.department === departmentFilter;
    
    return matchesSearch && matchesDept;
  });

  // Extract unique departments for filter
  const departments = ["ALL", ...Array.from(new Set(employees.map(e => e.department).filter(Boolean)))];

  return (
    <div className="p-6 lg:p-10 max-w-[1600px] mx-auto bg-slate-50 min-h-screen">
      
      {/* Header Section */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-6 mb-8">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-50 border border-blue-100 text-blue-700 text-xs font-bold uppercase tracking-wider mb-2">
            Human Resources
          </div>
          <h1 className="text-3xl font-black text-slate-900 tracking-tight">Employee Directory</h1>
          <p className="text-slate-500 mt-1">Manage staff members, roles, and departmental access.</p>
        </div>
        
        <div className="flex gap-3">
          <Link href="/staff/hr/employees/new" className="px-5 py-2.5 bg-blue-600 text-white font-bold rounded-xl shadow-lg shadow-blue-600/20 hover:bg-blue-700 transition-all flex items-center gap-2 text-sm">
            <i className="fas fa-user-plus"></i> Onboard Employee
          </Link>
        </div>
      </div>

      {/* Main Table */}
      <div className="bg-white rounded-3xl border border-slate-200 shadow-sm overflow-hidden flex flex-col">
        <div className="p-5 border-b border-slate-100 flex flex-col lg:flex-row items-start lg:items-center justify-between gap-4">
          <div className="flex gap-2 p-1 bg-slate-100 rounded-lg">
            {['Active', 'Inactive', 'Suspended'].map((tab) => (
              <button
                key={tab}
                onClick={() => setStatusFilter(tab)}
                className={`px-4 py-1.5 text-sm font-bold rounded-md transition-all ${
                  statusFilter === tab 
                    ? 'bg-white text-slate-900 shadow-sm' 
                    : 'text-slate-500 hover:text-slate-700'
                }`}
              >
                {tab}
              </button>
            ))}
          </div>

          <div className="flex flex-col sm:flex-row gap-3 w-full lg:w-auto">
            <div className="relative flex-1 sm:flex-none">
              <i className="fas fa-search absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 text-xs"></i>
              <input 
                type="text" 
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Search code, name, email..." 
                className="pl-9 pr-4 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 w-full sm:w-64" 
              />
            </div>
            <select 
              value={departmentFilter}
              onChange={(e) => setDepartmentFilter(e.target.value)}
              className="py-2 px-3 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 bg-white"
            >
              {departments.map((dept: any) => (
                <option key={dept} value={dept}>{dept === "ALL" ? "All Departments" : dept}</option>
              ))}
            </select>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-slate-50/50 border-b border-slate-100">
                <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider">Employee</th>
                <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider">Department & Role</th>
                <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider">Contact</th>
                <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider">Manager</th>
                <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {loading ? (
                <tr>
                  <td colSpan={5} className="px-6 py-12 text-center text-slate-400">
                    <i className="fas fa-circle-notch fa-spin text-3xl mb-3"></i>
                    <p className="font-medium">Loading Directory...</p>
                  </td>
                </tr>
              ) : error ? (
                <tr>
                  <td colSpan={5} className="px-6 py-12 text-center text-rose-500">
                    <i className="fas fa-exclamation-triangle text-3xl mb-3"></i>
                    <p className="font-medium">{error}</p>
                  </td>
                </tr>
              ) : filteredEmployees.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-6 py-16 text-center text-slate-500">
                    <div className="w-20 h-20 bg-slate-100 rounded-full flex items-center justify-center text-3xl text-slate-400 mx-auto mb-4">
                      <i className="fas fa-users-slash"></i>
                    </div>
                    <p className="font-bold text-slate-700 text-lg mb-1">No employees found</p>
                    <p className="text-sm">Try adjusting your search or filters.</p>
                  </td>
                </tr>
              ) : (
                filteredEmployees.map((emp) => (
                  <tr key={emp.id} className="hover:bg-blue-50/30 transition-colors group">
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-100 to-indigo-100 flex items-center justify-center text-blue-700 font-bold shrink-0">
                          {(emp.name || emp.first_name || "?")[0].toUpperCase()}
                        </div>
                        <div>
                          <p className="font-bold text-slate-900 group-hover:text-blue-700 transition-colors">{emp.name || emp.first_name}</p>
                          <p className="text-xs font-mono text-slate-500 bg-slate-100 inline-block px-1.5 rounded mt-0.5 border border-slate-200">
                            {emp.emp_code}
                          </p>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <p className="font-bold text-slate-700 text-sm">{emp.department || 'N/A'}</p>
                      <p className="text-xs text-slate-500">{emp.role || 'Employee'}</p>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex flex-col gap-1 text-xs">
                        <span className="text-slate-600"><i className="fas fa-envelope text-slate-400 mr-1.5 w-3"></i>{emp.email || 'N/A'}</span>
                        <span className="text-slate-600"><i className="fas fa-phone-alt text-slate-400 mr-1.5 w-3"></i>{emp.phone || 'N/A'}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <span className="text-sm font-semibold text-slate-600">
                        {emp.manager_name ? (
                          <><i className="fas fa-user-tie mr-1 text-slate-400"></i> {emp.manager_name}</>
                        ) : (
                          <span className="text-slate-400 italic">Self-Managed</span>
                        )}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-right">
                      <button className="p-2 text-blue-600 bg-blue-50 hover:bg-blue-100 hover:text-blue-800 rounded-lg transition-colors font-bold text-sm inline-flex items-center gap-2">
                        Profile <i className="fas fa-chevron-right text-xs"></i>
                      </button>
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