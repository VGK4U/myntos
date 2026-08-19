"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useStaffAuth } from "@/contexts/StaffAuthContext";
import { getApiUrl } from "@/lib/api";

interface VGKMember {
  id: number;
  vgk_id: string; // e.g. VGK-8921
  name: string;
  phone: string;
  level: string; // BRONZE, SILVER, GOLD, PLATINUM
  join_date: string;
  total_referrals: number;
  wallet_balance: number;
  status: string; // ACTIVE, INACTIVE, SUSPENDED
}

export default function VGKMembersPage() {
  const { token, hasRole } = useStaffAuth();
  const [members, setMembers] = useState<VGKMember[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [levelFilter, setLevelFilter] = useState("");

  useEffect(() => {
    if (!token) return;
    
    const fetchMembers = async () => {
      try {
        setLoading(true);
        // Generic endpoint for Staff to view VGK members
        const res = await fetch(`${getApiUrl()}/api/v1/staff/vgk/members`, {
          headers: {
            "Authorization": `Bearer ${token}`
          }
        });
        
        if (res.ok) {
          const data = await res.json();
          setMembers(data.items || []);
        } else {
          setMembers([]);
        }
      } catch (err) {
        console.warn("Failed to fetch members", err);
      } finally {
        setLoading(false);
      }
    };

    fetchMembers();
  }, [token]);

  const filteredMembers = members.filter(m => 
    (m.name.toLowerCase().includes(searchTerm.toLowerCase()) || 
     m.vgk_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
     m.phone.includes(searchTerm)) &&
    (levelFilter === "" || m.level === levelFilter)
  );

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="flex justify-between items-end mb-8">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 tracking-tight">VGK Members Directory</h1>
          <p className="text-sm text-gray-500 mt-2">Manage all registered VGK Network Members, their tiers, and wallet balances.</p>
        </div>
        <div className="flex space-x-3">
          <Link href="/staff/vgk/income" className="px-4 py-2 bg-white border border-gray-300 text-gray-700 font-medium rounded-lg shadow-sm hover:bg-gray-50 transition-colors">
            <i className="fas fa-wallet mr-2"></i> Payouts
          </Link>
          <button className="px-4 py-2 bg-indigo-600 text-white font-medium rounded-lg shadow-sm hover:bg-indigo-700 transition-colors">
            <i className="fas fa-user-plus mr-2"></i> Register Member
          </button>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <div className="bg-gradient-to-br from-indigo-500 to-indigo-700 p-5 rounded-xl shadow-sm text-white">
          <p className="text-xs font-bold uppercase opacity-80">Total Members</p>
          <p className="text-3xl font-bold mt-1">{members.length}</p>
        </div>
        <div className="bg-gradient-to-br from-gray-700 to-gray-900 p-5 rounded-xl shadow-sm text-white relative overflow-hidden">
          <i className="fas fa-crown absolute right-[-10px] bottom-[-10px] text-5xl opacity-10"></i>
          <p className="text-xs font-bold uppercase opacity-80">Platinum Members</p>
          <p className="text-3xl font-bold mt-1">{members.filter(m => m.level === "PLATINUM").length}</p>
        </div>
        <div className="bg-white p-5 rounded-xl shadow-sm border border-gray-100">
          <p className="text-xs font-bold text-gray-500 uppercase">Avg Referrals/Member</p>
          <p className="text-3xl font-bold text-indigo-600 mt-1">
            {members.length > 0 ? (members.reduce((acc, m) => acc + m.total_referrals, 0) / members.length).toFixed(1) : "0.0"}
          </p>
        </div>
        <div className="bg-white p-5 rounded-xl shadow-sm border border-gray-100">
          <p className="text-xs font-bold text-gray-500 uppercase">Total Wallet Liability</p>
          <p className="text-3xl font-bold text-green-600 mt-1">₹ {members.reduce((acc, m) => acc + m.wallet_balance, 0).toLocaleString()}</p>
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
                placeholder="Search by name, ID, or phone..." 
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10 pr-4 py-2 w-full border border-gray-300 rounded-lg text-sm focus:ring-2 focus:border-indigo-500 outline-none" 
              />
            </div>
            <select 
              className="px-3 py-2 border border-gray-300 rounded-lg text-sm bg-white text-gray-700 outline-none w-48"
              value={levelFilter}
              onChange={(e) => setLevelFilter(e.target.value)}
            >
              <option value="">All Tiers</option>
              <option value="BRONZE">Bronze</option>
              <option value="SILVER">Silver</option>
              <option value="GOLD">Gold</option>
              <option value="PLATINUM">Platinum</option>
            </select>
          </div>
          <button className="px-3 py-2 border border-gray-300 text-gray-700 text-sm font-medium rounded-lg hover:bg-gray-50">
            <i className="fas fa-download mr-1"></i> Export CSV
          </button>
        </div>
        
        {loading ? (
          <div className="p-12 text-center text-gray-500">
            <i className="fas fa-spinner fa-spin text-3xl mb-3 text-indigo-500"></i>
            <p>Loading members...</p>
          </div>
        ) : filteredMembers.length === 0 ? (
          <div className="p-16 text-center text-gray-500 flex flex-col items-center">
            <div className="w-16 h-16 bg-indigo-50 text-indigo-300 rounded-full flex items-center justify-center mb-4">
              <i className="fas fa-users text-2xl"></i>
            </div>
            <h3 className="text-lg font-medium text-gray-900 mb-1">No members found</h3>
            <p className="text-gray-500 mb-4">No VGK members matched your search criteria.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-gray-50 border-b border-gray-200">
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Member Details</th>
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Contact</th>
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider text-center">Tier Level</th>
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider text-center">Network</th>
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider text-right">Wallet Bal.</th>
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider text-center">Status</th>
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider text-center">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {filteredMembers.map(member => (
                  <tr key={member.id} className="hover:bg-gray-50 transition-colors">
                    <td className="p-4">
                      <p className="text-sm font-bold text-indigo-600">{member.vgk_id}</p>
                      <p className="text-sm font-medium text-gray-900">{member.name}</p>
                      <p className="text-xs text-gray-500 mt-0.5">Joined: {new Date(member.join_date).toLocaleDateString()}</p>
                    </td>
                    <td className="p-4">
                      <p className="text-sm text-gray-700">{member.phone}</p>
                    </td>
                    <td className="p-4 text-center">
                      <span className={`text-[10px] font-bold px-2 py-1 rounded-full border ${
                        member.level === "PLATINUM" ? "border-gray-800 bg-gray-900 text-white" :
                        member.level === "GOLD" ? "border-yellow-500 bg-yellow-50 text-yellow-700" : 
                        member.level === "SILVER" ? "border-gray-400 bg-gray-100 text-gray-700" : 
                        "border-amber-700 bg-amber-50 text-amber-800"
                      }`}>
                        {member.level}
                      </span>
                    </td>
                    <td className="p-4 text-center">
                      <span className="text-sm font-bold text-gray-900">{member.total_referrals}</span>
                      <p className="text-[10px] text-gray-500">Referrals</p>
                    </td>
                    <td className="p-4 text-right">
                      <span className="text-sm font-bold text-green-600">₹ {member.wallet_balance.toLocaleString()}</span>
                    </td>
                    <td className="p-4 text-center">
                      <span className={`text-[10px] font-bold px-2 py-1 rounded ${
                        member.status === "ACTIVE" ? "bg-green-100 text-green-800" :
                        member.status === "INACTIVE" ? "bg-gray-200 text-gray-800" : 
                        "bg-red-100 text-red-800"
                      }`}>
                        {member.status}
                      </span>
                    </td>
                    <td className="p-4 text-center space-x-3">
                      <button className="text-indigo-600 hover:text-indigo-800 text-sm font-medium" title="View Profile">
                        <i className="fas fa-eye"></i>
                      </button>
                      <button className="text-amber-600 hover:text-amber-800 text-sm font-medium" title="Add Funds">
                        <i className="fas fa-plus-circle"></i>
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
