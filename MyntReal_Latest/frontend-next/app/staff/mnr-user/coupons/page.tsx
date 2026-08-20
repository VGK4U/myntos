"use client";

import { useState } from "react";
import { toast } from "react-hot-toast";

type Tab = "purchased" | "usage" | "transfers" | "activate" | "buy";

export default function CouponsPage() {
  const [activeTab, setActiveTab] = useState<Tab>("purchased");
  const [searchId, setSearchId] = useState("");
  const [loading, setLoading] = useState(false);
  const [userData, setUserData] = useState<any>(null);

  const handleSearch = async () => {
    if (!searchId.trim()) return;
    setLoading(true);
    try {
      const token = typeof window !== "undefined" ? localStorage.getItem("staff_token") : "";
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/v1/staff/mnr-user/coupons/${searchId}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setUserData(data);
      } else {
        setUserData(null);
        toast.error("Member not found or has no coupons");
      }
    } catch (err) {
      console.warn("Failed to fetch coupons", err);
      setUserData(null);
      toast.error("Failed to fetch coupons");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 mb-2 flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-brand-warning/10 flex items-center justify-center">
              <i className="fas fa-ticket-alt text-brand-warning"></i>
            </div>
            Coupons Management
          </h1>
          <p className="text-gray-500">
            View inventory, process transfers, and activate coupon packages for members.
          </p>
        </div>
      </div>

      {/* Search Card */}
      <div className="p-6 rounded-xl bg-white border border-gray-200 shadow-sm">
        <div className="flex flex-col md:flex-row gap-6 items-end">
          <div className="flex-1 w-full max-w-md">
            <label className="block text-sm font-bold text-gray-900 mb-2">Search Member</label>
            <div className="flex gap-2">
              <div className="relative flex-grow">
                <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 font-medium text-sm">MNR</span>
                <input 
                  type="text" 
                  value={searchId}
                  onChange={(e) => setSearchId(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleSearch()}
                  className="w-full bg-gray-50 border border-gray-200 rounded-lg py-2.5 pl-12 pr-4 text-gray-900 focus:outline-none focus:ring-2 focus:ring-brand-warning/50 focus:border-brand-warning transition-all uppercase"
                  placeholder="Enter member ID..."
                />
              </div>
              <button 
                onClick={handleSearch}
                disabled={loading}
                className="px-6 py-2.5 bg-gray-900 hover:bg-black text-white font-bold rounded-lg transition-colors flex items-center gap-2 disabled:opacity-70 shadow-sm"
              >
                {loading ? <i className="fas fa-spinner fa-spin"></i> : <i className="fas fa-search"></i>}
                Search
              </button>
            </div>
          </div>

          {userData && (
            <div className="flex-1">
              <div className="p-4 rounded-lg bg-brand-warning/5 border border-brand-warning/20 flex items-center gap-4">
                <div className="w-12 h-12 rounded-full bg-white shadow-sm flex items-center justify-center text-xl font-bold text-brand-warning">
                  {userData.member_info.name.charAt(0)}
                </div>
                <div>
                  <h3 className="font-bold text-gray-900">{userData.member_info.name}</h3>
                  <div className="flex items-center gap-2 text-sm text-gray-500">
                    <span>{userData.member_info.id}</span>
                    <span className="w-1 h-1 rounded-full bg-gray-300"></span>
                    <span className="text-emerald-600 font-medium">{userData.member_info.status}</span>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {userData && (
        <div className="animate-in fade-in slide-in-from-bottom-4 duration-500">
          {/* Tabs */}
          <div className="flex overflow-x-auto no-scrollbar border-b border-gray-200 mb-6 bg-white px-2 rounded-t-xl">
            <TabButton active={activeTab === 'purchased'} onClick={() => setActiveTab('purchased')} icon="fas fa-shopping-cart" label="Purchased" />
            <TabButton active={activeTab === 'usage'} onClick={() => setActiveTab('usage')} icon="fas fa-check-circle" label="Usage Status" />
            <TabButton active={activeTab === 'transfers'} onClick={() => setActiveTab('transfers')} icon="fas fa-exchange-alt" label="Transfers" />
            <TabButton active={activeTab === 'activate'} onClick={() => setActiveTab('activate')} icon="fas fa-bolt" label="Activate" />
            <TabButton active={activeTab === 'buy'} onClick={() => setActiveTab('buy')} icon="fas fa-credit-card" label="Buy Coupon" />
          </div>

          {/* Stats based on Tab */}
          {activeTab !== 'activate' && activeTab !== 'buy' && (
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 mb-6">
              {activeTab === 'purchased' && (
                <>
                  <StatCard label="Total Requests" value={userData.summary.total_requests} />
                  <StatCard label="Pending" value={userData.summary.pending} color="text-amber-500" />
                  <StatCard label="Approved" value={userData.summary.approved} color="text-sky-500" />
                  <StatCard label="Fulfilled" value={userData.summary.fulfilled} color="text-emerald-500" />
                  <StatCard label="Rejected" value={userData.summary.rejected} color="text-rose-500" />
                  <StatCard label="Total Value" value={`₹${userData.summary.total_value.toLocaleString('en-IN')}`} />
                </>
              )}
              {activeTab === 'usage' && (
                <>
                  <StatCard label="Total Coupons" value={userData.summary.total_coupons} />
                  <StatCard label="Available" value={userData.summary.available} color="text-emerald-500" />
                  <StatCard label="Used" value={userData.summary.used} color="text-gray-400" />
                  <StatCard label="Transferred" value={userData.summary.transferred} color="text-sky-500" />
                </>
              )}
              {activeTab === 'transfers' && (
                <>
                  <StatCard label="Incoming" value={userData.summary.total_incoming} color="text-emerald-500" />
                  <StatCard label="Outgoing" value={userData.summary.total_outgoing} color="text-amber-500" />
                  <StatCard label="Available" value={userData.summary.available_for_transfer} color="text-sky-500" />
                </>
              )}
            </div>
          )}

          {/* Tab Content Areas */}
          {activeTab === 'purchased' && <PurchasedTab data={userData.purchased} />}
          {activeTab === 'usage' && <UsageTab data={userData.usage_inventory} />}
          {activeTab === 'transfers' && <TransfersTab data={userData.transfers} />}
          {activeTab === 'activate' && <ActivateTab data={userData.activate} />}
          {activeTab === 'buy' && <BuyTab data={userData.packages} />}

        </div>
      )}

      {!userData && !loading && (
        <div className="text-center py-24 text-gray-400">
          <i className="fas fa-ticket-alt fa-3x mb-4 opacity-20"></i>
          <h3 className="text-lg font-medium text-gray-500">Search for a member to view their coupons</h3>
          <p className="text-sm">Enter an MNR ID above to get started</p>
        </div>
      )}
    </div>
  );
}

function TabButton({ active, onClick, icon, label }: { active: boolean, onClick: () => void, icon: string, label: string }) {
  return (
    <button
      onClick={onClick}
      className={`px-6 py-4 font-medium text-sm transition-all relative whitespace-nowrap flex items-center gap-2 ${
        active ? "text-brand-warning bg-gray-50/50" : "text-gray-500 hover:text-gray-900 hover:bg-gray-50"
      }`}
    >
      <i className={icon}></i> {label}
      {active && (
        <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-brand-warning"></div>
      )}
    </button>
  );
}

function StatCard({ label, value, color = "text-gray-900" }: { label: string, value: string | number, color?: string }) {
  return (
    <div className="p-4 rounded-xl bg-white border border-gray-200 shadow-sm text-center">
      <div className={`text-2xl font-bold mb-1 ${color}`}>{value}</div>
      <div className="text-xs font-medium text-gray-500 uppercase tracking-wider">{label}</div>
    </div>
  );
}

function PurchasedTab({ data }: { data: any }) {
  return (
    <div className="bg-white border border-gray-200 rounded-xl overflow-hidden shadow-sm">
      <div className="p-4 border-b border-gray-200 flex justify-between items-center bg-gray-50">
        <h3 className="font-bold text-gray-900"><i className="fas fa-history text-gray-400 mr-2"></i>Purchase History</h3>
        <button className="px-3 py-1 bg-white border border-gray-200 rounded-lg text-sm text-gray-600 hover:bg-gray-50"><i className="fas fa-filter mr-1"></i>Filter</button>
      </div>
      {(!data || data.length === 0) ? (
        <div className="p-12 text-center text-gray-400">
          <i className="fas fa-shopping-cart fa-2x mb-3 text-gray-300"></i>
          <p>No purchase records found for this member.</p>
        </div>
      ) : (
        <div className="p-4 text-center">Data available</div>
      )}
    </div>
  );
}

function UsageTab({ data }: { data: any }) {
  return (
    <div className="bg-white border border-gray-200 rounded-xl overflow-hidden shadow-sm">
      <div className="p-4 border-b border-gray-200 bg-gray-50">
        <h3 className="font-bold text-gray-900"><i className="fas fa-layer-group text-gray-400 mr-2"></i>Coupon Inventory</h3>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead className="bg-gray-50 text-gray-500 text-xs uppercase border-b border-gray-200">
            <tr>
              <th className="px-6 py-3 font-medium">Coupon ID</th>
              <th className="px-6 py-3 font-medium">Package</th>
              <th className="px-6 py-3 font-medium">Status</th>
              <th className="px-6 py-3 font-medium">Generation Date</th>
              <th className="px-6 py-3 font-medium">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {(!data || data.length === 0) ? (
              <tr><td colSpan={5} className="px-6 py-8 text-center text-gray-400">No coupons found.</td></tr>
            ) : (
              data.map((cpn: any, idx: number) => (
                <tr key={idx} className="hover:bg-gray-50 transition-colors">
                  <td className="px-6 py-4 font-medium text-gray-900">{cpn.id}</td>
                  <td className="px-6 py-4"><span className="px-2 py-1 bg-indigo-50 text-indigo-700 text-xs rounded font-medium border border-indigo-100">{cpn.package}</span></td>
                  <td className="px-6 py-4"><span className="px-2 py-1 bg-emerald-50 text-emerald-700 text-xs rounded font-medium border border-emerald-100">{cpn.status}</span></td>
                  <td className="px-6 py-4 text-gray-500">{cpn.date}</td>
                  <td className="px-6 py-4"><button className="text-brand-warning hover:text-amber-600 font-medium">View</button></td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function TransfersTab({ data }: { data: any }) {
  return (
    <div className="bg-white border border-gray-200 rounded-xl overflow-hidden shadow-sm">
      <div className="p-4 border-b border-gray-200 bg-gray-50 flex justify-between items-center">
        <h3 className="font-bold text-gray-900"><i className="fas fa-exchange-alt text-gray-400 mr-2"></i>Transfer Ledger</h3>
        <button className="px-4 py-2 bg-gray-900 text-white rounded-lg text-sm font-medium hover:bg-black transition-colors shadow-sm">
          Initiate Transfer
        </button>
      </div>
      {(!data || data.length === 0) ? (
        <div className="p-12 text-center text-gray-400">
          <i className="fas fa-exchange-alt fa-2x mb-3 text-gray-300"></i>
          <p>No transfers recorded for this member.</p>
        </div>
      ) : (
        <div className="p-4 text-center">Data available</div>
      )}
    </div>
  );
}

function ActivateTab({ data }: { data: any }) {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <div className="bg-white border border-gray-200 rounded-xl overflow-hidden shadow-sm">
        <div className="p-4 border-b border-gray-200 bg-emerald-50 flex items-center gap-2">
          <i className="fas fa-bolt text-emerald-600"></i>
          <h3 className="font-bold text-emerald-900">Activate Coupon</h3>
        </div>
        <div className="p-6 space-y-4">
          <div>
            <label className="block text-sm font-bold text-gray-900 mb-2">Select Coupon <span className="text-rose-500">*</span></label>
            <select className="w-full bg-white border border-gray-300 rounded-lg py-2.5 px-3 text-gray-900 focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-all">
              <option>#CPN-9821-PLT (Platinum)</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-bold text-gray-900 mb-2">Target Member (Inactive Downline)</label>
            <input 
              type="text" 
              className="w-full bg-white border border-gray-300 rounded-lg py-2.5 px-3 text-gray-900 focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-all"
              placeholder="Search by MNR ID or name..."
            />
          </div>
          <div className="p-4 rounded-lg bg-indigo-50 border border-indigo-100 text-indigo-800 text-sm flex gap-3">
            <i className="fas fa-info-circle mt-0.5"></i>
            <p>Activating a coupon will assign points to the sponsor and trigger matching income calculations instantly across the network.</p>
          </div>
          <button className="w-full py-3 bg-emerald-600 hover:bg-emerald-700 text-white font-bold rounded-lg transition-colors shadow-sm mt-4">
            Execute Activation
          </button>
        </div>
      </div>
      
      <div className="space-y-6">
        <div className="bg-white border border-gray-200 rounded-xl overflow-hidden shadow-sm">
          <div className="p-4 border-b border-gray-200 bg-gray-50 flex items-center gap-2">
            <i className="fas fa-history text-gray-500"></i>
            <h3 className="font-bold text-gray-900">Recent Activations</h3>
          </div>
          <div className="p-6 text-center text-gray-400 text-sm">
            No recent activations today.
          </div>
        </div>
      </div>
    </div>
  );
}

function BuyTab({ data }: { data: any }) {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <div className="bg-white border border-gray-200 rounded-xl overflow-hidden shadow-sm">
        <div className="p-4 border-b border-gray-200 bg-brand-warning/10 flex items-center gap-2">
          <i className="fas fa-credit-card text-brand-warning"></i>
          <h3 className="font-bold text-gray-900">Purchase Coupon</h3>
        </div>
        <div className="p-6 space-y-4">
          <div>
            <label className="block text-sm font-bold text-gray-900 mb-2">Package Type <span className="text-rose-500">*</span></label>
            <select className="w-full bg-white border border-gray-300 rounded-lg py-2.5 px-3 text-gray-900 focus:ring-2 focus:ring-brand-warning/20 focus:border-brand-warning transition-all">
              <option value="">Select Package...</option>
              <option value="PLATINUM">Platinum - ₹15,000</option>
              <option value="DIAMOND">Diamond - ₹7,500</option>
              <option value="BLUE">Star (Blue) - ₹1,000</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-bold text-gray-900 mb-2">Quantity <span className="text-rose-500">*</span></label>
            <input 
              type="number" min="1" max="10" defaultValue="1"
              className="w-full bg-white border border-gray-300 rounded-lg py-2.5 px-3 text-gray-900 focus:ring-2 focus:ring-brand-warning/20 focus:border-brand-warning transition-all"
            />
          </div>
          <div className="pt-2">
            <label className="block text-sm font-bold text-gray-900 mb-3">Funding Source</label>
            <div className="space-y-3">
              <label className="flex items-center gap-3 p-3 rounded-lg border border-gray-200 hover:bg-gray-50 cursor-pointer">
                <input type="radio" name="funding" defaultChecked className="text-brand-warning focus:ring-brand-warning" />
                <div>
                  <div className="font-medium text-gray-900"><i className="fas fa-wallet mr-2 text-gray-400"></i>User Wallet</div>
                  <div className="text-xs text-gray-500">Available Balance: ₹14,500</div>
                </div>
              </label>
              <label className="flex items-center gap-3 p-3 rounded-lg border border-gray-200 hover:bg-gray-50 cursor-pointer">
                <input type="radio" name="funding" className="text-brand-warning focus:ring-brand-warning" />
                <div className="font-medium text-gray-900"><i className="fas fa-money-bill mr-2 text-gray-400"></i>Offline Payment (Cash/Bank)</div>
              </label>
            </div>
          </div>
          <button className="w-full py-3 bg-gray-900 hover:bg-black text-white font-bold rounded-lg transition-colors shadow-sm mt-4">
            Complete Purchase
          </button>
        </div>
      </div>
      
      <div className="bg-white border border-gray-200 rounded-xl overflow-hidden shadow-sm h-fit">
        <div className="p-4 border-b border-gray-200 bg-gray-50 flex items-center gap-2">
          <i className="fas fa-info-circle text-gray-500"></i>
          <h3 className="font-bold text-gray-900">Package Information</h3>
        </div>
        <table className="w-full text-left text-sm">
          <thead className="bg-gray-50 text-gray-500 text-xs uppercase border-b border-gray-200">
            <tr>
              <th className="px-4 py-3 font-medium">Package</th>
              <th className="px-4 py-3 font-medium">Price</th>
              <th className="px-4 py-3 font-medium">Points</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            <tr><td className="px-4 py-3 font-medium">Platinum</td><td className="px-4 py-3">₹15,000</td><td className="px-4 py-3">1.0</td></tr>
            <tr><td className="px-4 py-3 font-medium">Diamond</td><td className="px-4 py-3">₹7,500</td><td className="px-4 py-3">0.5</td></tr>
            <tr><td className="px-4 py-3 font-medium">Star (Blue)</td><td className="px-4 py-3">₹1,000</td><td className="px-4 py-3">0</td></tr>
            <tr><td className="px-4 py-3 font-medium">Loyal</td><td className="px-4 py-3">₹500</td><td className="px-4 py-3">0</td></tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}
