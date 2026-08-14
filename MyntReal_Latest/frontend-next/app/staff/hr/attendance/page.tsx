"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useStaffAuth } from "@/contexts/StaffAuthContext";
import { getApiUrl } from "@/lib/api";

interface AttendanceRecord {
  id: number;
  date: string;
  employee_name: string;
  employee_id: string;
  check_in: string;
  check_out: string | null;
  status: string; // PRESENT, ABSENT, HALF_DAY, LATE
  working_hours: number;
}

export default function AttendancePage() {
  const { token } = useStaffAuth();
  const [records, setRecords] = useState<AttendanceRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [searchTerm, setSearchTerm] = useState("");
  const [dateFilter, setDateFilter] = useState(new Date().toISOString().split('T')[0]);

  useEffect(() => {
    if (!token) return;
    
    const fetchAttendance = async () => {
      try {
        setLoading(true);
        // Using generic HR attendance endpoint, filtered by date
        const res = await fetch(`${getApiUrl()}/api/v1/staff/hr/attendance?date=${dateFilter}`, {
          headers: {
            "Authorization": `Bearer ${token}`
          }
        });
        
        if (res.ok) {
          const data = await res.json();
          setRecords(data.items || []);
        } else {
          setRecords([]); // Fallback
        }
      } catch (err: any) {
        console.warn("Failed to fetch attendance, using empty state", err);
        setRecords([]);
      } finally {
        setLoading(false);
      }
    };

    fetchAttendance();
  }, [token, dateFilter]);

  const filteredRecords = records.filter(r => 
    r.employee_name.toLowerCase().includes(searchTerm.toLowerCase()) || 
    r.employee_id.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="flex justify-between items-end mb-8">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 tracking-tight">Attendance & Timesheets</h1>
          <p className="text-sm text-gray-500 mt-2">Monitor daily check-ins, working hours, and timesheet approvals.</p>
        </div>
        <div className="flex space-x-3">
          <Link href="/staff/hr/leaves" className="px-4 py-2 bg-white border border-gray-300 text-gray-700 font-medium rounded-lg shadow-sm hover:bg-gray-50 transition-colors">
            <i className="fas fa-calendar-times mr-2"></i> Leave Requests
          </Link>
          <button className="px-4 py-2 bg-indigo-600 text-white font-medium rounded-lg shadow-sm hover:bg-indigo-700 transition-colors">
            <i className="fas fa-file-export mr-2"></i> Export Timesheet
          </button>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <div className="bg-white p-5 rounded-xl shadow-sm border-l-4 border-indigo-500">
          <p className="text-xs font-bold text-gray-500 uppercase">Total Expected</p>
          <p className="text-2xl font-bold text-gray-900 mt-1">
            {records.length > 0 ? records.length : '-'}
          </p>
        </div>
        <div className="bg-white p-5 rounded-xl shadow-sm border-l-4 border-green-500">
          <p className="text-xs font-bold text-gray-500 uppercase">Present</p>
          <p className="text-2xl font-bold text-green-600 mt-1">
            {records.filter(r => r.status === "PRESENT" || r.status === "LATE").length}
          </p>
        </div>
        <div className="bg-white p-5 rounded-xl shadow-sm border-l-4 border-amber-500">
          <p className="text-xs font-bold text-gray-500 uppercase">Late Check-ins</p>
          <p className="text-2xl font-bold text-amber-600 mt-1">
            {records.filter(r => r.status === "LATE").length}
          </p>
        </div>
        <div className="bg-white p-5 rounded-xl shadow-sm border-l-4 border-red-500">
          <p className="text-xs font-bold text-gray-500 uppercase">Absent</p>
          <p className="text-2xl font-bold text-red-600 mt-1">
            {records.filter(r => r.status === "ABSENT").length}
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
                placeholder="Search employee..." 
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10 pr-4 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:border-indigo-500 outline-none w-64" 
              />
            </div>
            <input 
              type="date"
              value={dateFilter}
              onChange={(e) => setDateFilter(e.target.value)}
              className="px-3 py-2 border border-gray-300 rounded-lg text-sm bg-white text-gray-700 outline-none"
            />
          </div>
        </div>
        
        {loading ? (
          <div className="p-12 text-center text-gray-500">
            <i className="fas fa-spinner fa-spin text-3xl mb-3 text-indigo-500"></i>
            <p>Loading attendance records...</p>
          </div>
        ) : error ? (
          <div className="p-8 text-center text-red-500 bg-red-50">
            <i className="fas fa-exclamation-triangle text-2xl mb-2"></i>
            <p>{error}</p>
          </div>
        ) : filteredRecords.length === 0 ? (
          <div className="p-16 text-center text-gray-500 flex flex-col items-center">
            <div className="w-16 h-16 bg-indigo-50 text-indigo-300 rounded-full flex items-center justify-center mb-4">
              <i className="fas fa-user-clock text-2xl"></i>
            </div>
            <h3 className="text-lg font-medium text-gray-900 mb-1">No attendance records</h3>
            <p className="text-gray-500 mb-4">No records found for the selected date or search criteria.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-gray-50 border-b border-gray-200">
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Employee</th>
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Date</th>
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider text-center">Check In</th>
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider text-center">Check Out</th>
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider text-center">Working Hours</th>
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider text-center">Status</th>
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider text-center">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {filteredRecords.map(r => (
                  <tr key={r.id} className="hover:bg-gray-50 transition-colors">
                    <td className="p-4">
                      <p className="text-sm font-bold text-gray-900">{r.employee_name}</p>
                      <p className="text-xs text-gray-500">{r.employee_id}</p>
                    </td>
                    <td className="p-4 text-sm text-gray-600">
                      {new Date(r.date).toLocaleDateString()}
                    </td>
                    <td className="p-4 text-center text-sm font-medium text-green-600">
                      {r.check_in || "--:--"}
                    </td>
                    <td className="p-4 text-center text-sm font-medium text-gray-600">
                      {r.check_out || "--:--"}
                    </td>
                    <td className="p-4 text-center">
                      <span className="text-sm font-bold text-gray-900">{r.working_hours.toFixed(1)} hrs</span>
                    </td>
                    <td className="p-4 text-center">
                      <span className={`text-[10px] font-bold px-2 py-1 rounded ${
                        r.status === "PRESENT" ? "bg-green-100 text-green-800" : 
                        r.status === "LATE" ? "bg-amber-100 text-amber-800" :
                        "bg-red-100 text-red-800"
                      }`}>
                        {r.status}
                      </span>
                    </td>
                    <td className="p-4 text-center">
                      <button className="text-indigo-600 hover:text-indigo-800 text-sm font-medium mx-2">
                        Adjust
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
