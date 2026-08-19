"use client";

import React, { useState } from "react";
import { useSuperAdminAuth } from "@/contexts/SuperAdminAuthContext";
import { ShieldAlert, AlertTriangle, Flag, Ban, Search, UserMinus, MoreVertical, ScanSearch } from "lucide-react";

export default function SuperAdminRedIDOversight() {
  const { user } = useSuperAdminAuth();

  const redIds = [
    { id: 'VGK00299', name: 'Karthik Raja', joinDate: '2026-06-10', reason: 'Zero Sales in 60 Days', riskLevel: 'HIGH', status: 'FLAGGED' },
    { id: 'VGK00450', name: 'Nisha Verma', joinDate: '2026-05-15', reason: 'KYC Expired', riskLevel: 'MEDIUM', status: 'WARNING_SENT' },
    { id: 'VGK00511', name: 'Tariq Ahmed', joinDate: '2026-01-20', reason: 'Compliance Violation', riskLevel: 'CRITICAL', status: 'SUSPENDED' },
  ];

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8 bg-slate-50 min-h-[calc(100vh-64px)]">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-slate-900 tracking-tight">Red ID Oversight</h1>
          <p className="text-sm text-slate-500 mt-1">Identify, Manage, and Purge Inactive or Non-Compliant Members</p>
        </div>
        <div className="flex items-center gap-3">
          <button className="inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors bg-rose-600 text-white hover:bg-rose-700 h-9 px-4 py-2 shadow">
            <UserMinus className="mr-2 h-4 w-4" /> Purge Selected (0)
          </button>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <div className="rounded-xl border border-l-4 border-l-amber-500 bg-white shadow-sm flex items-center justify-between p-6">
          <div>
            <h3 className="text-sm font-medium text-slate-500 mb-1">Warning State</h3>
            <div className="text-4xl font-bold text-slate-900">45</div>
          </div>
          <AlertTriangle className="h-12 w-12 text-amber-100" />
        </div>

        <div className="rounded-xl border border-l-4 border-l-rose-500 bg-white shadow-sm flex items-center justify-between p-6">
          <div>
            <h3 className="text-sm font-medium text-slate-500 mb-1">Flagged (Red IDs)</h3>
            <div className="text-4xl font-bold text-slate-900">12</div>
          </div>
          <Flag className="h-12 w-12 text-rose-100" />
        </div>

        <div className="rounded-xl border border-l-4 border-l-slate-600 bg-slate-900 shadow-sm flex items-center justify-between p-6">
          <div>
            <h3 className="text-sm font-medium text-slate-400 mb-1">Suspended Accounts</h3>
            <div className="text-4xl font-bold text-white">3</div>
          </div>
          <Ban className="h-12 w-12 text-slate-800" />
        </div>
      </div>

      <div className="rounded-xl border bg-white text-slate-950 shadow-sm overflow-hidden flex flex-col">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between p-6 border-b gap-4 bg-slate-50/50">
          <div className="flex items-center gap-2">
            <ShieldAlert className="h-5 w-5 text-rose-500" />
            <h3 className="font-semibold text-slate-800">Flagged Roster</h3>
          </div>
          <button className="inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors border border-slate-200 bg-white hover:bg-slate-100 hover:text-slate-900 h-9 px-4 py-2">
            <ScanSearch className="mr-2 h-4 w-4" /> Run ID Audit Scan
          </button>
        </div>

        <div className="relative w-full overflow-auto">
          <table className="w-full caption-bottom text-sm">
            <thead className="[&_tr]:border-b">
              <tr className="border-b transition-colors hover:bg-slate-50">
                <th className="h-12 px-6 w-12 text-center align-middle">
                  <input type="checkbox" className="rounded border-slate-300 text-rose-600 focus:ring-rose-500 h-4 w-4" />
                </th>
                <th className="h-12 px-6 text-left align-middle font-medium text-slate-500">Member Info</th>
                <th className="h-12 px-6 text-left align-middle font-medium text-slate-500">Flag Reason</th>
                <th className="h-12 px-6 text-left align-middle font-medium text-slate-500">Risk Level</th>
                <th className="h-12 px-6 text-left align-middle font-medium text-slate-500">System Status</th>
                <th className="h-12 px-6 text-right align-middle font-medium text-slate-500">Actions</th>
              </tr>
            </thead>
            <tbody className="[&_tr:last-child]:border-0">
              {redIds.map((member, idx) => (
                <tr key={idx} className="border-b transition-colors hover:bg-rose-50/30">
                  <td className="p-6 text-center align-middle">
                    <input type="checkbox" className="rounded border-slate-300 text-rose-600 focus:ring-rose-500 h-4 w-4" />
                  </td>
                  <td className="p-6 align-middle">
                    <div className="font-semibold text-slate-900">{member.name}</div>
                    <div className="flex gap-2 mt-1 items-center">
                      <div className="text-xs text-slate-700 font-mono bg-slate-100 px-1.5 py-0.5 rounded border border-slate-200">{member.id}</div>
                      <div className="text-xs text-slate-500">Joined: {new Date(member.joinDate).toLocaleDateString()}</div>
                    </div>
                  </td>
                  <td className="p-6 align-middle">
                    <div className="font-medium text-slate-700">{member.reason}</div>
                  </td>
                  <td className="p-6 align-middle">
                    <div className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ${
                      member.riskLevel === 'CRITICAL' ? 'bg-rose-100 text-rose-800 border border-rose-200' :
                      member.riskLevel === 'HIGH' ? 'bg-orange-100 text-orange-800 border border-orange-200' :
                      'bg-amber-100 text-amber-800 border border-amber-200'
                    }`}>
                      {member.riskLevel}
                    </div>
                  </td>
                  <td className="p-6 align-middle">
                    <div className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ${
                      member.status === 'SUSPENDED' ? 'bg-slate-800 text-white' :
                      member.status === 'FLAGGED' ? 'bg-rose-600 text-white' :
                      'bg-slate-200 text-slate-700'
                    }`}>
                      {member.status.replace('_', ' ')}
                    </div>
                  </td>
                  <td className="p-6 align-middle text-right">
                    <button className="inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors hover:bg-slate-100 h-8 w-8 text-slate-500 hover:text-slate-900">
                      <MoreVertical className="h-4 w-4" />
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
