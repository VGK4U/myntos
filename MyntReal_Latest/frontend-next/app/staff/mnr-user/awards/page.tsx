"use client";

import { useState } from "react";
import { useStaffAuth } from "@/contexts/StaffAuthContext";

export default function AwardsPage() {
  const [activeTab, setActiveTab] = useState<"lookup" | "admin">("lookup");
  
  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 mb-2 flex items-center gap-3">
            <i className="fas fa-trophy text-brand-warning"></i>
            Awards & Bonanza
          </h1>
          <p className="text-gray-500">
            View and manage member awards, bonanza status, and group performance recognitions.
          </p>
        </div>
      </div>

      {/* Main Tabs */}
      <div className="flex border-b border-gray-200">
        <button
          onClick={() => setActiveTab("lookup")}
          className={`px-6 py-3 font-medium text-sm transition-colors relative ${
            activeTab === "lookup" ? "text-brand-warning" : "text-gray-500 hover:text-gray-900"
          }`}
        >
          <i className="fas fa-user-search me-2"></i> User Lookup
          {activeTab === "lookup" && (
            <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-brand-warning rounded-t-full"></div>
          )}
        </button>
        <button
          onClick={() => setActiveTab("admin")}
          className={`px-6 py-3 font-medium text-sm transition-colors relative ${
            activeTab === "admin" ? "text-brand-warning" : "text-gray-500 hover:text-gray-900"
          }`}
        >
          <i className="fas fa-chart-bar me-2"></i> Admin Overview
          {activeTab === "admin" && (
            <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-brand-warning rounded-t-full"></div>
          )}
        </button>
      </div>

      {activeTab === "lookup" && <UserLookupTab />}
      {activeTab === "admin" && <AdminOverviewTab />}
    </div>
  );
}

// ----------------------------------------------------------------------
// User Lookup Tab (Replaces staff_mnr_user_awards.html)
// ----------------------------------------------------------------------
function UserLookupTab() {
  const [searchId, setSearchId] = useState("");
  const [loading, setLoading] = useState(false);
  const [userData, setUserData] = useState<any>(null);
  const [subTab, setSubTab] = useState<"direct" | "matching" | "bonanza">("direct");

  const handleSearch = async () => {
    if (!searchId.trim()) return;
    setLoading(true);
    
    // Simulate API call based on legacy structure
    setTimeout(() => {
      setUserData({
        member_info: { name: "Anil Kumar", id: searchId.toUpperCase(), package: "DIAMOND", status: "Active" },
        summary: { achieved: 2, received: 1, pending: 1 },
        awards_direct: [
          { rank_name: "Star", award_item: "Smart Watch", required_referrals: 5, current_referrals: 5, achieved: true, remaining: 0, processed_status: "Delivered", status_color: "success" },
          { rank_name: "Silver", award_item: "Tablet", required_referrals: 15, current_referrals: 8, achieved: false, remaining: 7, processed_status: null, status_color: "secondary" },
        ],
        awards_matching: [
          { rank_name: "Gold", award_item: "Laptop", required_matches: 50, current_matches: 50, achieved: true, remaining: 0, processed_status: "Pending Approval", status_color: "warning" },
          { rank_name: "Platinum", award_item: "Car Fund", required_matches: 250, current_matches: 120, achieved: false, remaining: 130, processed_status: null, status_color: "secondary" },
        ],
        bonanzas: [
          { bonanza_name: "Diwali Dhamaka", reward_name: "Dubai Trip", reward_value: 50000, claimed_date: "2023-11-15", processed_status: "Approved", status_color: "primary" }
        ]
      });
      setLoading(false);
    }, 800);
  };

  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="p-6 rounded-xl bg-white border border-brand-warning/30 shadow-[0_0_15px_rgba(255,193,7,0.1)]">
        <label className="block text-brand-warning font-bold mb-2">
          <i className="fas fa-search me-2"></i>Search MNR ID for Awards
        </label>
        <div className="flex gap-2 max-w-md">
          <div className="relative flex-grow">
            <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 font-medium">MNR</span>
            <input 
              type="text" 
              value={searchId}
              onChange={(e) => setSearchId(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSearch()}
              className="w-full bg-white border border-gray-300 rounded-lg py-2.5 pl-12 pr-4 text-gray-900 focus:outline-none focus:border-brand-warning transition-colors uppercase"
              placeholder="Enter member ID..."
            />
          </div>
          <button 
            onClick={handleSearch}
            disabled={loading}
            className="px-6 py-2.5 bg-brand-warning hover:bg-yellow-400 text-black font-bold rounded-lg transition-colors flex items-center gap-2 disabled:opacity-70"
          >
            {loading ? <i className="fas fa-spinner fa-spin"></i> : <i className="fas fa-search"></i>}
            Search
          </button>
        </div>
      </div>

      {!userData && !loading && (
        <div className="text-center py-16 text-gray-400">
          <i className="fas fa-trophy fa-3x mb-4 opacity-30"></i>
          <p className="text-lg">Enter an MNR ID to view their awards and bonanzas</p>
        </div>
      )}

      {userData && (
        <div className="space-y-6">
          <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 bg-white p-4 rounded-xl border border-gray-200">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 rounded-full bg-brand-warning/20 text-brand-warning flex items-center justify-center font-bold text-xl">
                {userData.member_info.name.charAt(0)}
              </div>
              <div>
                <h2 className="text-xl font-bold text-gray-900">{userData.member_info.name}</h2>
                <div className="flex items-center gap-2 text-sm">
                  <span className="text-gray-500">{userData.member_info.id}</span>
                  <span className="text-gray-400">•</span>
                  <span className="text-sky-400">{userData.member_info.package}</span>
                  <span className="text-gray-400">•</span>
                  <span className="text-emerald-400">{userData.member_info.status}</span>
                </div>
              </div>
            </div>
            
            <div className="flex gap-4">
              <div className="text-center px-4 border-r border-gray-200">
                <div className="text-2xl font-bold text-emerald-400">{userData.summary.achieved}</div>
                <div className="text-xs text-gray-400 uppercase">Achieved</div>
              </div>
              <div className="text-center px-4 border-r border-gray-200">
                <div className="text-2xl font-bold text-blue-400">{userData.summary.received}</div>
                <div className="text-xs text-gray-400 uppercase">Received</div>
              </div>
              <div className="text-center px-4">
                <div className="text-2xl font-bold text-amber-500">{userData.summary.pending}</div>
                <div className="text-xs text-gray-400 uppercase">Pending</div>
              </div>
            </div>
          </div>

          <div className="flex gap-2 border-b border-gray-200 pb-2">
            <button
              onClick={() => setSubTab("direct")}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${subTab === "direct" ? "bg-gray-100 text-gray-900" : "text-gray-500 hover:text-gray-600 hover:bg-gray-50"}`}
            >
              <i className="fas fa-user-plus me-2"></i>Direct Facilitations
            </button>
            <button
              onClick={() => setSubTab("matching")}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${subTab === "matching" ? "bg-gray-100 text-gray-900" : "text-gray-500 hover:text-gray-600 hover:bg-gray-50"}`}
            >
              <i className="fas fa-users me-2"></i>Group Performance
            </button>
            <button
              onClick={() => setSubTab("bonanza")}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${subTab === "bonanza" ? "bg-amber-500/20 text-amber-500" : "text-gray-500 hover:text-gray-600 hover:bg-gray-50"}`}
            >
              <i className="fas fa-gift me-2"></i>Bonanza Status
            </button>
          </div>

          {/* Tables */}
          <div className="rounded-xl border border-gray-200 bg-white overflow-hidden">
            <div className="overflow-x-auto">
              {subTab === "direct" && <AwardsTable awards={userData.awards_direct} isMatching={false} />}
              {subTab === "matching" && <AwardsTable awards={userData.awards_matching} isMatching={true} />}
              {subTab === "bonanza" && <BonanzaTable bonanzas={userData.bonanzas} />}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function AwardsTable({ awards, isMatching }: { awards: any[], isMatching: boolean }) {
  return (
    <table className="w-full text-left text-sm">
      <thead className="bg-emerald-50 text-emerald-800 text-xs uppercase border-b border-emerald-200">
        <tr>
          <th className="px-4 py-3 font-medium">Rank & Award</th>
          <th className="px-4 py-3 font-medium text-center">Requirement</th>
          <th className="px-4 py-3 font-medium text-center">Progress</th>
          <th className="px-4 py-3 font-medium text-center">Remaining</th>
          <th className="px-4 py-3 font-medium text-center">Status</th>
          <th className="px-4 py-3 font-medium text-center">Processed</th>
        </tr>
      </thead>
      <tbody className="divide-y divide-slate-700/50">
        {awards.map((a, i) => (
          <tr key={i} className="hover:bg-gray-50 transition-colors">
            <td className="px-4 py-3">
              <div className="font-bold text-gray-900">{a.rank_name}</div>
              <div className="text-xs text-brand-warning">{a.award_item}</div>
            </td>
            <td className="px-4 py-3 text-center text-sky-400 font-bold">
              {isMatching ? a.required_matches : a.required_referrals}
            </td>
            <td className="px-4 py-3 text-center text-sky-400 font-bold">
              {isMatching ? a.current_matches : a.current_referrals}
            </td>
            <td className="px-4 py-3 text-center">
              {a.remaining === 0 ? <span className="text-emerald-500"><i className="fas fa-check"></i> Complete</span> : <span className="text-gray-500">{a.remaining}</span>}
            </td>
            <td className="px-4 py-3 text-center">
              {a.achieved ? (
                <span className="px-2 py-1 bg-emerald-500/20 text-emerald-400 text-xs rounded-full"><i className="fas fa-check me-1"></i>Achieved</span>
              ) : (
                <span className="px-2 py-1 bg-gray-200 text-gray-600 text-xs rounded-full"><i className="fas fa-clock me-1"></i>Pending</span>
              )}
            </td>
            <td className="px-4 py-3 text-center">
              {a.processed_status ? (
                <span className={`px-2 py-1 bg-${a.status_color}-500/20 text-${a.status_color}-400 text-xs rounded`}>{a.processed_status}</span>
              ) : (
                <span className="text-gray-400">-</span>
              )}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function BonanzaTable({ bonanzas }: { bonanzas: any[] }) {
  if (bonanzas.length === 0) {
    return <div className="text-center py-8 text-gray-400">No bonanzas claimed.</div>;
  }
  
  return (
    <table className="w-full text-left text-sm">
      <thead className="bg-amber-50 text-amber-800 text-xs uppercase border-b border-amber-200">
        <tr>
          <th className="px-4 py-3 font-medium">Bonanza Campaign</th>
          <th className="px-4 py-3 font-medium">Reward</th>
          <th className="px-4 py-3 font-medium text-right">Value</th>
          <th className="px-4 py-3 font-medium text-center">Claimed Date</th>
          <th className="px-4 py-3 font-medium text-center">Status</th>
        </tr>
      </thead>
      <tbody className="divide-y divide-slate-700/50">
        {bonanzas.map((b, i) => (
          <tr key={i} className="hover:bg-gray-50 transition-colors">
            <td className="px-4 py-3 font-bold text-gray-900">{b.bonanza_name}</td>
            <td className="px-4 py-3 text-gray-600">{b.reward_name}</td>
            <td className="px-4 py-3 text-right text-brand-warning font-bold">₹{b.reward_value.toLocaleString('en-IN')}</td>
            <td className="px-4 py-3 text-center text-gray-500">{b.claimed_date}</td>
            <td className="px-4 py-3 text-center">
               <span className={`px-2 py-1 bg-${b.status_color}-500/20 text-${b.status_color}-400 text-xs rounded`}>{b.processed_status}</span>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}


// ----------------------------------------------------------------------
// Admin Overview Tab (Replaces staff_mnr_awards_management.html)
// ----------------------------------------------------------------------
function AdminOverviewTab() {
  const [activeSubTab, setActiveSubTab] = useState<"all" | "bonanza">("all");

  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
      
      {/* Sub Tabs */}
      <div className="flex gap-4">
        <button
          onClick={() => setActiveSubTab("all")}
          className={`px-4 py-2 rounded-lg font-medium text-sm transition-colors ${
            activeSubTab === "all" ? "bg-brand-warning text-black" : "bg-gray-100 text-gray-600 hover:bg-gray-200"
          }`}
        >
          <i className="fas fa-list-alt me-2"></i> All Awards Processing
        </button>
        <button
          onClick={() => setActiveSubTab("bonanza")}
          className={`px-4 py-2 rounded-lg font-medium text-sm transition-colors ${
            activeSubTab === "bonanza" ? "bg-brand-warning text-black" : "bg-gray-100 text-gray-600 hover:bg-gray-200"
          }`}
        >
          <i className="fas fa-gift me-2"></i> Bonanza Claims
        </button>
      </div>

      {activeSubTab === "all" && (
        <div className="space-y-6 animate-in fade-in">
          {/* Stats Grid */}
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
            <StatCard label="Pending Elig." value={12} color="border-l-slate-400" />
            <StatCard label="Pending Approval" value={45} color="border-l-amber-500" />
            <StatCard label="Approved" value={89} color="border-l-sky-500" />
            <StatCard label="Processed" value={156} color="border-l-purple-500" />
            <StatCard label="Completed" value={340} color="border-l-emerald-500" />
            <StatCard label="Rejected" value={3} color="border-l-rose-500" />
          </div>

          <div className="p-12 text-center border border-gray-200 rounded-xl bg-white">
            <i className="fas fa-cogs text-4xl text-gray-400 mb-4"></i>
            <h3 className="text-xl font-bold text-gray-900 mb-2">Award Pipeline</h3>
            <p className="text-gray-500 max-w-md mx-auto">
              View, approve, and process awards across all members in the system. Use the filters to find specific groups or pending procurements.
            </p>
            <button className="mt-6 px-6 py-2 bg-brand-warning text-black font-bold rounded-lg hover:bg-yellow-400 transition-colors">
              Refresh Pipeline Data
            </button>
          </div>
        </div>
      )}

      {activeSubTab === "bonanza" && (
        <div className="space-y-6 animate-in fade-in">
          <div className="p-12 text-center border border-gray-200 rounded-xl bg-white relative overflow-hidden">
            <div className="absolute top-0 right-0 p-8 opacity-5">
              <i className="fas fa-gift text-9xl"></i>
            </div>
            <div className="relative z-10">
              <i className="fas fa-gift text-4xl text-amber-500 mb-4"></i>
              <h3 className="text-xl font-bold text-gray-900 mb-2">Bonanza Claims Management</h3>
              <p className="text-gray-500 max-w-md mx-auto">
                Track, verify, and fulfill special time-bound bonanza campaign claims. 
              </p>
              <button className="mt-6 px-6 py-2 border border-brand-warning text-brand-warning hover:bg-brand-warning/10 font-bold rounded-lg transition-colors">
                View Active Campaigns
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function StatCard({ label, value, color }: { label: string, value: number | string, color: string }) {
  return (
    <div className={`p-4 rounded-xl bg-white border-l-4 ${color} border-y border-r border-gray-200`}>
      <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">{label}</p>
      <p className="text-2xl font-bold text-gray-900">{value}</p>
    </div>
  );
}
