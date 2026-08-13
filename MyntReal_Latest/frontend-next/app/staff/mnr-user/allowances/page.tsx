"use client";

import { useState } from "react";
import { useStaffAuth } from "@/contexts/StaffAuthContext";
import { toast } from "react-hot-toast";

// Types derived from legacy templates
type AllowanceType = "standard" | "car";

export default function AllowancesPage() {
  const [activeTab, setActiveTab] = useState<"lookup" | "admin">("lookup");
  
  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 mb-2 flex items-center gap-3">
            <i className="fas fa-hand-holding-usd text-brand-warning"></i>
            Field Allowances
          </h1>
          <p className="text-gray-500">
            Manage field allowance eligibility and payment history.
          </p>
        </div>
      </div>

      {/* Tabs */}
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
          <i className="fas fa-users-cog me-2"></i> Admin Dashboard
          {activeTab === "admin" && (
            <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-brand-warning rounded-t-full"></div>
          )}
        </button>
      </div>

      {activeTab === "lookup" && <UserLookupTab />}
      {activeTab === "admin" && <AdminDashboardTab />}
    </div>
  );
}

// ----------------------------------------------------------------------
// User Lookup Tab (Replaces staff_mnr_user_allowances.html)
// ----------------------------------------------------------------------
function UserLookupTab() {
  const [searchId, setSearchId] = useState("");
  const [loading, setLoading] = useState(false);
  const [userData, setUserData] = useState<any>(null);

  const handleSearch = async () => {
    if (!searchId.trim()) return;
    setLoading(true);
    
    // Simulate API call based on legacy structure
    // Original: fetch(`/api/v1/staff/mnr-user/allowances/${currentMnrId}`)
    setTimeout(() => {
      setUserData({
        member_info: { name: "John Doe", id: searchId.toUpperCase() },
        allowance_status: {
          current_active: "standard",
          standard_allowance: {
            status: { overall_status: "Active", months_completed: 4, total_paid: 40000 },
            initial_requirements: { direct_referrals: { current: 7, required: 7, progress_percentage: 100 } },
            monthly_requirements: { matching_pairs: { current: 15, required: 20, progress_percentage: 75 } },
            total_value: 180000
          },
          car_allowance: {
            status: { overall_status: "Not Eligible", months_completed: 0, total_paid: 0 },
            initial_requirements: { matching_points: { current: 120, required: 250, progress_percentage: 48 } },
            monthly_requirements: { matching_pairs: { current: 0, required: 40, progress_percentage: 0 } },
            total_value: 1800000
          }
        },
        payment_history: [
          { description: "Standard Field Allowance (Month 4)", timestamp: "2023-10-01", amount: 10000 },
          { description: "Standard Field Allowance (Month 3)", timestamp: "2023-09-01", amount: 10000 },
          { description: "Standard Field Allowance (Month 2)", timestamp: "2023-08-01", amount: 10000 },
          { description: "Standard Field Allowance (Month 1)", timestamp: "2023-07-01", amount: 10000 },
        ],
        total_paid: 40000
      });
      setLoading(false);
    }, 800);
  };

  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="p-6 rounded-xl bg-white border border-brand-warning/30 shadow-[0_0_15px_rgba(255,193,7,0.1)]">
        <label className="block text-brand-warning font-bold mb-2">
          <i className="fas fa-search me-2"></i>Search MNR ID
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
          <i className="fas fa-search fa-3x mb-4 opacity-30"></i>
          <p className="text-lg">Enter an MNR ID to view their field allowances</p>
        </div>
      )}

      {userData && (
        <div className="space-y-6">
          <div className="flex items-center gap-4 bg-white p-4 rounded-xl border border-gray-200">
            <div className="w-12 h-12 rounded-full bg-brand-warning/20 text-brand-warning flex items-center justify-center font-bold text-xl">
              {userData.member_info.name.charAt(0)}
            </div>
            <div>
              <h2 className="text-xl font-bold text-gray-900">{userData.member_info.name}</h2>
              <p className="text-gray-500">{userData.member_info.id}</p>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Standard Allowance Card */}
            <AllowanceCard 
              title="Standard Field Allowance"
              subtitle="₹10,000/month × 18 months"
              icon="fas fa-wallet"
              type="standard"
              data={userData.allowance_status.standard_allowance}
            />
            {/* Car Allowance Card */}
            <AllowanceCard 
              title="Car Allowance (Premium)"
              subtitle="₹25,000/month × 72 months"
              icon="fas fa-car"
              type="car"
              data={userData.allowance_status.car_allowance}
            />
          </div>

          {/* Payment History */}
          <div className="p-6 rounded-xl bg-white border border-gray-200">
            <h3 className="text-lg font-bold text-gray-900 mb-4 border-b border-gray-200 pb-4">
              <i className="fas fa-history text-brand-warning me-2"></i>
              Payment History
            </h3>
            
            <div className="space-y-3">
              {userData.payment_history.map((pay: any, idx: number) => (
                <div key={idx} className="flex justify-between items-center p-3 rounded-lg bg-gray-50 border border-gray-200">
                  <div>
                    <div className="font-medium text-gray-900">{pay.description}</div>
                    <div className="text-xs text-gray-500">{pay.timestamp}</div>
                  </div>
                  <div className="font-bold text-emerald-400">
                    ₹{pay.amount.toLocaleString('en-IN')}
                  </div>
                </div>
              ))}
            </div>

            <div className="mt-6 pt-4 border-t border-gray-200 flex justify-between items-center">
              <span className="text-gray-500 font-medium">Total Paid:</span>
              <span className="text-xl font-bold text-emerald-400">₹{userData.total_paid.toLocaleString('en-IN')}</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function AllowanceCard({ title, subtitle, icon, type, data }: { title: string, subtitle: string, icon: string, type: "standard"|"car", data: any }) {
  const isCar = type === "car";
  const color = isCar ? "info" : "warning";
  const hexColor = isCar ? "#0ea5e9" : "#f59e0b"; // sky-500 vs amber-500
  const bgClass = isCar ? "bg-sky-500" : "bg-amber-500";
  const textClass = isCar ? "text-sky-500" : "text-amber-500";

  return (
    <div className={`p-6 rounded-xl bg-white border-l-4 ${isCar ? 'border-sky-500' : 'border-amber-500'} border-y border-r border-gray-200 relative overflow-hidden group hover:bg-gray-100/80 transition-colors`}>
      <div className="absolute top-0 right-0 p-8 opacity-[0.03] group-hover:opacity-[0.08] transition-opacity">
        <i className={`${icon} text-9xl`}></i>
      </div>

      <div className="flex justify-between items-start mb-6 relative z-10 border-b border-gray-200 pb-4">
        <div>
          <h3 className="text-lg font-bold text-gray-900 flex items-center gap-2">
            <i className={`${icon} ${textClass}`}></i> {title}
          </h3>
          <p className="text-sm text-gray-500">{subtitle}</p>
        </div>
        <div className="text-right">
          <span className={`font-bold ${data.status.overall_status === 'Active' ? 'text-emerald-400' : textClass}`}>
            {data.status.overall_status}
          </span>
          <p className="text-xs text-gray-400">Status</p>
        </div>
      </div>

      <div className="space-y-4 relative z-10">
        <div>
          <div className="flex justify-between text-sm mb-1">
            <span className="text-gray-600">Initial Eligibility Requirements</span>
            <span className={textClass}>
              {type === 'standard' ? data.initial_requirements.direct_referrals.current : data.initial_requirements.matching_points.current}/
              {type === 'standard' ? data.initial_requirements.direct_referrals.required : data.initial_requirements.matching_points.required}
            </span>
          </div>
          <div className="h-2 w-full bg-gray-200 rounded-full overflow-hidden">
            <div 
              className={`h-full ${bgClass} rounded-full transition-all duration-1000`} 
              style={{ width: `${type === 'standard' ? data.initial_requirements.direct_referrals.progress_percentage : data.initial_requirements.matching_points.progress_percentage}%` }}
            ></div>
          </div>
        </div>

        <div>
          <div className="flex justify-between text-sm mb-1">
            <span className="text-gray-600">Monthly Requirements</span>
            <span className={textClass}>
              {data.monthly_requirements.matching_pairs.current}/{data.monthly_requirements.matching_pairs.required}
            </span>
          </div>
          <div className="h-2 w-full bg-gray-200 rounded-full overflow-hidden">
            <div 
              className={`h-full ${bgClass} rounded-full transition-all duration-1000`} 
              style={{ width: `${data.monthly_requirements.matching_pairs.progress_percentage}%` }}
            ></div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-4 mt-6 pt-4 border-t border-gray-200 relative z-10 text-center">
        <div>
          <p className="text-xs text-gray-500 mb-1">Months</p>
          <p className="font-bold text-gray-900">{data.status.months_completed}/{isCar ? '72' : '18'}</p>
        </div>
        <div>
          <p className="text-xs text-gray-500 mb-1">Total Paid</p>
          <p className="font-bold text-emerald-400">₹{data.status.total_paid.toLocaleString('en-IN')}</p>
        </div>
        <div>
          <p className="text-xs text-gray-500 mb-1">Remaining</p>
          <p className={textClass + " font-bold"}>₹{(data.total_value - data.status.total_paid).toLocaleString('en-IN')}</p>
        </div>
      </div>
    </div>
  );
}


// ----------------------------------------------------------------------
// Admin Dashboard Tab (Replaces staff_mnr_field_allowances.html)
// ----------------------------------------------------------------------
function AdminDashboardTab() {
  const [activeSubTab, setActiveSubTab] = useState<"eligibility" | "payouts">("eligibility");

  // Mock data for Admin overview
  const mockStats = {
    total: 1245,
    stdEligible: 850,
    carEligible: 120,
    stdActive: 600,
    carActive: 85,
    notEligible: 395
  };

  const mockUsers = [
    { id: "MNR10001", name: "Rahul Sharma", pkg: "DIAMOND", stdProg: 100, carProg: 45, elig: "Pass", active: "Standard" },
    { id: "MNR10002", name: "Priya Singh", pkg: "GOLD", stdProg: 80, carProg: 10, elig: "Partial", active: "None" },
    { id: "MNR10003", name: "Amit Kumar", pkg: "PLATINUM", stdProg: 100, carProg: 100, elig: "Pass", active: "Car" },
    { id: "MNR10004", name: "Neha Verma", pkg: "SILVER", stdProg: 40, carProg: 0, elig: "Fail", active: "None" },
  ];

  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
      
      {/* Sub Tabs */}
      <div className="flex gap-4">
        <button
          onClick={() => setActiveSubTab("eligibility")}
          className={`px-4 py-2 rounded-lg font-medium text-sm transition-colors ${
            activeSubTab === "eligibility" ? "bg-brand-warning text-black" : "bg-gray-100 text-gray-600 hover:bg-gray-200"
          }`}
        >
          <i className="fas fa-clipboard-check me-2"></i> Eligibility Status
        </button>
        <button
          onClick={() => setActiveSubTab("payouts")}
          className={`px-4 py-2 rounded-lg font-medium text-sm transition-colors ${
            activeSubTab === "payouts" ? "bg-brand-warning text-black" : "bg-gray-100 text-gray-600 hover:bg-gray-200"
          }`}
        >
          <i className="fas fa-money-check-alt me-2"></i> Monthly Payouts
        </button>
      </div>

      {activeSubTab === "eligibility" && (
        <div className="space-y-6 animate-in fade-in">
          {/* Stats Grid */}
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
            <StatCard label="Total Users" value={mockStats.total} color="border-l-slate-400" />
            <StatCard label="Std Eligible" value={mockStats.stdEligible} color="border-l-amber-500" />
            <StatCard label="Car Eligible" value={mockStats.carEligible} color="border-l-sky-500" />
            <StatCard label="Active Std" value={mockStats.stdActive} color="border-l-emerald-500" />
            <StatCard label="Active Car" value={mockStats.carActive} color="border-l-emerald-500" />
            <StatCard label="Not Eligible" value={mockStats.notEligible} color="border-l-rose-500" />
          </div>

          {/* Filters */}
          <div className="p-4 rounded-xl bg-white border border-gray-200 flex flex-wrap gap-4 items-end">
            <div className="flex-1 min-w-[200px]">
              <label className="block text-xs font-medium text-gray-500 mb-1">Search User</label>
              <input type="text" className="w-full bg-white border border-gray-300 rounded-lg py-2 px-3 text-sm text-gray-900" placeholder="MNR ID or Name..." />
            </div>
            <div className="w-[150px]">
              <label className="block text-xs font-medium text-gray-500 mb-1">Type</label>
              <select className="w-full bg-white border border-gray-300 rounded-lg py-2 px-3 text-sm text-gray-900">
                <option>All Types</option>
                <option>Standard</option>
                <option>Car</option>
              </select>
            </div>
            <button className="px-4 py-2 bg-gray-200 hover:bg-slate-600 text-gray-900 rounded-lg text-sm font-medium transition-colors">
              Filter
            </button>
          </div>

          {/* Data Table */}
          <div className="rounded-xl border border-gray-200 bg-white overflow-hidden">
            <div className="p-4 bg-gray-50 border-b border-gray-200 flex justify-between items-center">
              <h3 className="font-bold text-gray-900"><i className="fas fa-users me-2 text-gray-500"></i>Eligibility Overview</h3>
              <span className="text-xs text-gray-500">Total: {mockUsers.length} shown</span>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="bg-gray-100 text-gray-500 text-xs uppercase">
                  <tr>
                    <th className="px-4 py-3 font-medium">User</th>
                    <th className="px-4 py-3 font-medium">Package</th>
                    <th className="px-4 py-3 font-medium">Standard (10K)</th>
                    <th className="px-4 py-3 font-medium">Car (25K)</th>
                    <th className="px-4 py-3 font-medium">Eligibility</th>
                    <th className="px-4 py-3 font-medium">Active</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-700/50">
                  {mockUsers.map((user) => (
                    <tr key={user.id} className="hover:bg-gray-50 transition-colors">
                      <td className="px-4 py-3">
                        <div className="font-medium text-gray-900">{user.name}</div>
                        <div className="text-xs text-brand-warning">{user.id}</div>
                      </td>
                      <td className="px-4 py-3">
                        <span className="px-2 py-1 bg-gray-200 text-xs rounded text-gray-600">{user.pkg}</span>
                      </td>
                      <td className="px-4 py-3">
                        <div className="w-full bg-gray-200 h-2 rounded-full mt-1 mb-1">
                          <div className={`h-full rounded-full ${user.stdProg === 100 ? 'bg-emerald-500' : 'bg-amber-500'}`} style={{ width: `${user.stdProg}%` }}></div>
                        </div>
                        <span className="text-xs text-gray-500">{user.stdProg}% Qualified</span>
                      </td>
                      <td className="px-4 py-3">
                        <div className="w-full bg-gray-200 h-2 rounded-full mt-1 mb-1">
                          <div className={`h-full rounded-full ${user.carProg === 100 ? 'bg-emerald-500' : 'bg-sky-500'}`} style={{ width: `${user.carProg}%` }}></div>
                        </div>
                        <span className="text-xs text-gray-500">{user.carProg}% Qualified</span>
                      </td>
                      <td className="px-4 py-3">
                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                          user.elig === 'Pass' ? 'bg-emerald-500/20 text-emerald-400' :
                          user.elig === 'Partial' ? 'bg-amber-500/20 text-amber-400' :
                          'bg-rose-500/20 text-rose-400'
                        }`}>
                          {user.elig}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-gray-600">
                        {user.active !== 'None' ? (
                          <span className={`px-2 py-1 rounded text-xs font-bold ${user.active === 'Car' ? 'bg-sky-500 text-gray-900' : 'bg-amber-500 text-black'}`}>
                            {user.active} Active
                          </span>
                        ) : '-'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {activeSubTab === "payouts" && (
        <div className="space-y-6 animate-in fade-in">
          {/* Similar structure for Payouts, simplified for demonstration */}
          <div className="p-12 text-center border border-gray-200 rounded-xl bg-white">
            <i className="fas fa-money-check-alt text-4xl text-gray-400 mb-4"></i>
            <h3 className="text-xl font-bold text-gray-900 mb-2">Monthly Payouts Processing</h3>
            <p className="text-gray-500 max-w-md mx-auto">
              Run bulk payout validations and completions for all eligible field allowances here.
            </p>
            <button className="mt-6 px-6 py-2 bg-brand-warning text-black font-bold rounded-lg hover:bg-yellow-400 transition-colors">
              Generate Current Month Batch
            </button>
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
