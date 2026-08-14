"use client";

import React, { useState } from "react";
import { useSuperAdminAuth } from "@/contexts/SuperAdminAuthContext";

export default function SuperAdminRedIDOversight() {
  const { user } = useSuperAdminAuth();

  const redIds = [
    { id: 'VGK00299', name: 'Karthik Raja', joinDate: '2026-06-10', reason: 'Zero Sales in 60 Days', riskLevel: 'HIGH', status: 'FLAGGED' },
    { id: 'VGK00450', name: 'Nisha Verma', joinDate: '2026-05-15', reason: 'KYC Expired', riskLevel: 'MEDIUM', status: 'WARNING_SENT' },
    { id: 'VGK00511', name: 'Tariq Ahmed', joinDate: '2026-01-20', reason: 'Compliance Violation', riskLevel: 'CRITICAL', status: 'SUSPENDED' },
  ];

  return (
    <div className="p-6 max-w-7xl mx-auto flex flex-col h-[calc(100vh-64px)]">
      <div className="flex justify-between items-end mb-6 shrink-0">
        <div>
          <h1 className="text-3xl font-black text-gray-900 tracking-tight uppercase">Red ID Oversight</h1>
          <p className="text-xs text-gray-500 mt-2 font-bold uppercase tracking-widest">Identify, Manage, and Purge Inactive or Non-Compliant Members</p>
        </div>
        <div className="flex space-x-3">
          <button className="px-4 py-2 bg-red-600 text-white font-bold rounded shadow-sm hover:bg-red-700 transition-colors uppercase text-xs tracking-wider">
            <i className="fas fa-trash-alt mr-2"></i> Purge Selected (0)
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6 shrink-0">
        <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200 flex items-center justify-between border-l-4 border-l-yellow-500">
          <div>
            <p className="text-[10px] font-black text-gray-400 uppercase tracking-widest mb-1">Warning State</p>
            <h3 className="text-3xl font-black text-gray-900">45</h3>
          </div>
          <i className="fas fa-exclamation-triangle text-4xl text-yellow-100"></i>
        </div>

        <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200 flex items-center justify-between border-l-4 border-l-red-500">
          <div>
            <p className="text-[10px] font-black text-gray-400 uppercase tracking-widest mb-1">Flagged (Red IDs)</p>
            <h3 className="text-3xl font-black text-gray-900">12</h3>
          </div>
          <i className="fas fa-flag text-4xl text-red-100"></i>
        </div>

        <div className="bg-[#111827] p-6 rounded-lg shadow-sm flex items-center justify-between border-l-4 border-l-gray-600">
          <div>
            <p className="text-[10px] font-black text-gray-400 uppercase tracking-widest mb-1">Suspended Accounts</p>
            <h3 className="text-3xl font-black text-white">3</h3>
          </div>
          <i className="fas fa-ban text-4xl text-gray-800"></i>
        </div>
      </div>

      <div className="bg-white rounded-lg shadow-sm border border-gray-200 flex-1 overflow-hidden flex flex-col min-h-0">
        <div className="p-4 border-b border-gray-100 bg-gray-50 flex justify-between items-center">
          <h3 className="text-sm font-bold text-gray-900 uppercase tracking-wider">Flagged Roster</h3>
          <button className="text-gray-500 hover:text-gray-900 text-xs font-bold uppercase tracking-wider bg-white border border-gray-300 px-3 py-1.5 rounded">
            Run ID Audit Scan
          </button>
        </div>

        <div className="flex-1 overflow-auto p-0">
          <table className="w-full text-left">
            <thead className="bg-white sticky top-0 z-10">
              <tr className="border-b border-gray-200">
                <th className="p-4 w-12 text-center">
                  <input type="checkbox" className="rounded border-gray-300 text-red-600 focus:ring-red-500" />
                </th>
                <th className="p-4 text-[10px] font-black text-gray-500 uppercase tracking-widest">Member Info</th>
                <th className="p-4 text-[10px] font-black text-gray-500 uppercase tracking-widest">Flag Reason</th>
                <th className="p-4 text-[10px] font-black text-gray-500 uppercase tracking-widest">Risk Level</th>
                <th className="p-4 text-[10px] font-black text-gray-500 uppercase tracking-widest">System Status</th>
                <th className="p-4 text-[10px] font-black text-gray-500 uppercase tracking-widest text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {redIds.map((member, idx) => (
                <tr key={idx} className="hover:bg-red-50/30 transition-colors">
                  <td className="p-4 text-center">
                    <input type="checkbox" className="rounded border-gray-300 text-red-600 focus:ring-red-500" />
                  </td>
                  <td className="p-4">
                    <p className="font-bold text-gray-900">{member.name}</p>
                    <div className="flex gap-2 mt-1">
                      <p className="text-[10px] text-gray-500 font-mono bg-gray-100 px-1.5 rounded">{member.id}</p>
                      <p className="text-[10px] text-gray-500">Joined: {new Date(member.joinDate).toLocaleDateString()}</p>
                    </div>
                  </td>
                  <td className="p-4 text-sm font-bold text-gray-700">
                    {member.reason}
                  </td>
                  <td className="p-4">
                    <span className={`text-[9px] font-black px-2 py-1 rounded uppercase tracking-wider ${
                      member.riskLevel === 'CRITICAL' ? 'bg-red-100 text-red-700 border border-red-200' :
                      member.riskLevel === 'HIGH' ? 'bg-orange-100 text-orange-700 border border-orange-200' :
                      'bg-yellow-100 text-yellow-700 border border-yellow-200'
                    }`}>
                      {member.riskLevel}
                    </span>
                  </td>
                  <td className="p-4">
                    <span className={`text-[9px] font-black px-2 py-1 rounded uppercase tracking-wider ${
                      member.status === 'SUSPENDED' ? 'bg-gray-800 text-white' :
                      member.status === 'FLAGGED' ? 'bg-red-600 text-white' :
                      'bg-gray-200 text-gray-600'
                    }`}>
                      {member.status}
                    </span>
                  </td>
                  <td className="p-4 text-right">
                    <button className="text-gray-400 hover:text-gray-900 px-2 py-1">
                      <i className="fas fa-ellipsis-v"></i>
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
