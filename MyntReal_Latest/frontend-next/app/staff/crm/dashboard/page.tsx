"use client";

import Link from "next/link";

export default function CRMDashboardPage() {
  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500 max-w-7xl mx-auto">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-end gap-4">
        <div>
          <h1 className="text-2xl font-extrabold text-gray-900 tracking-tight mb-1">CRM Dashboard</h1>
          <p className="text-gray-500">Overview of your sales pipeline and lead performance.</p>
        </div>
        <div className="flex gap-2">
          <Link href="/staff/crm/import" className="px-4 py-2 bg-white border border-gray-200 text-gray-700 font-bold rounded-lg shadow-sm hover:bg-gray-50 transition-colors text-sm">
            <i className="fas fa-file-import mr-2"></i> Import Leads
          </Link>
          <button className="px-4 py-2 bg-gray-900 text-white font-bold rounded-lg shadow-sm hover:bg-black transition-colors text-sm">
            <i className="fas fa-plus mr-2"></i> New Lead
          </button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5 hover:shadow-md transition-shadow">
          <div className="flex justify-between items-start mb-4">
            <div>
              <p className="text-sm font-bold text-gray-500 mb-1">New Leads Today</p>
              <h3 className="text-2xl font-extrabold text-gray-900">124</h3>
            </div>
            <div className="w-10 h-10 rounded-lg bg-blue-50 flex items-center justify-center text-blue-600">
              <i className="fas fa-user-plus"></i>
            </div>
          </div>
          <div className="text-sm font-medium text-emerald-600 flex items-center gap-1">
            <i className="fas fa-arrow-up"></i> 12% vs yesterday
          </div>
        </div>

        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5 hover:shadow-md transition-shadow">
          <div className="flex justify-between items-start mb-4">
            <div>
              <p className="text-sm font-bold text-gray-500 mb-1">Active Follow-ups</p>
              <h3 className="text-2xl font-extrabold text-gray-900">45</h3>
            </div>
            <div className="w-10 h-10 rounded-lg bg-amber-50 flex items-center justify-center text-amber-600">
              <i className="fas fa-phone-volume"></i>
            </div>
          </div>
          <div className="text-sm font-medium text-rose-600 flex items-center gap-1">
            <i className="fas fa-exclamation-circle"></i> 5 overdue
          </div>
        </div>

        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5 hover:shadow-md transition-shadow">
          <div className="flex justify-between items-start mb-4">
            <div>
              <p className="text-sm font-bold text-gray-500 mb-1">Site Visits Booked</p>
              <h3 className="text-2xl font-extrabold text-gray-900">12</h3>
            </div>
            <div className="w-10 h-10 rounded-lg bg-emerald-50 flex items-center justify-center text-emerald-600">
              <i className="fas fa-calendar-check"></i>
            </div>
          </div>
          <div className="text-sm font-medium text-emerald-600 flex items-center gap-1">
            <i className="fas fa-arrow-up"></i> 3% vs last week
          </div>
        </div>

        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5 hover:shadow-md transition-shadow">
          <div className="flex justify-between items-start mb-4">
            <div>
              <p className="text-sm font-bold text-gray-500 mb-1">Conversion Rate</p>
              <h3 className="text-2xl font-extrabold text-gray-900">8.4%</h3>
            </div>
            <div className="w-10 h-10 rounded-lg bg-purple-50 flex items-center justify-center text-purple-600">
              <i className="fas fa-chart-pie"></i>
            </div>
          </div>
          <div className="text-sm font-medium text-gray-500 flex items-center gap-1">
            <i className="fas fa-minus"></i> No change
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Sales Pipeline Funnel */}
        <div className="lg:col-span-2 bg-white rounded-xl shadow-sm border border-gray-200 flex flex-col">
          <div className="p-5 border-b border-gray-100 flex justify-between items-center bg-gray-50/50 rounded-t-xl">
            <h3 className="font-bold text-gray-900">Sales Pipeline</h3>
            <select className="text-sm border-gray-300 rounded-lg bg-white focus:ring-gray-900 focus:border-gray-900 py-1">
              <option>This Month</option>
              <option>Last Month</option>
            </select>
          </div>
          <div className="p-6 flex-1 flex flex-col justify-center min-h-[300px]">
            {/* Visual Funnel Representation */}
            <div className="space-y-3">
              <div className="relative h-12 w-full bg-blue-100 rounded-lg overflow-hidden group hover:bg-blue-200 transition-colors cursor-pointer">
                <div className="absolute inset-y-0 left-0 bg-blue-500 w-[100%] transition-all duration-1000"></div>
                <div className="absolute inset-0 flex items-center justify-between px-4">
                  <span className="font-bold text-white text-sm z-10 drop-shadow-md">New / Uncontacted</span>
                  <span className="font-bold text-white text-sm z-10 drop-shadow-md">840 Leads</span>
                </div>
              </div>
              
              <div className="relative h-12 w-[85%] mx-auto bg-indigo-100 rounded-lg overflow-hidden group hover:bg-indigo-200 transition-colors cursor-pointer">
                <div className="absolute inset-y-0 left-0 bg-indigo-500 w-[100%] transition-all duration-1000"></div>
                <div className="absolute inset-0 flex items-center justify-between px-4">
                  <span className="font-bold text-white text-sm z-10 drop-shadow-md">Contacted / Follow-up</span>
                  <span className="font-bold text-white text-sm z-10 drop-shadow-md">425 Leads</span>
                </div>
              </div>

              <div className="relative h-12 w-[65%] mx-auto bg-amber-100 rounded-lg overflow-hidden group hover:bg-amber-200 transition-colors cursor-pointer">
                <div className="absolute inset-y-0 left-0 bg-amber-500 w-[100%] transition-all duration-1000"></div>
                <div className="absolute inset-0 flex items-center justify-between px-4">
                  <span className="font-bold text-white text-sm z-10 drop-shadow-md">Site Visit Scheduled</span>
                  <span className="font-bold text-white text-sm z-10 drop-shadow-md">112 Leads</span>
                </div>
              </div>

              <div className="relative h-12 w-[45%] mx-auto bg-orange-100 rounded-lg overflow-hidden group hover:bg-orange-200 transition-colors cursor-pointer">
                <div className="absolute inset-y-0 left-0 bg-orange-500 w-[100%] transition-all duration-1000"></div>
                <div className="absolute inset-0 flex items-center justify-between px-4">
                  <span className="font-bold text-white text-sm z-10 drop-shadow-md">Negotiation</span>
                  <span className="font-bold text-white text-sm z-10 drop-shadow-md">45 Leads</span>
                </div>
              </div>

              <div className="relative h-14 w-[30%] mx-auto bg-emerald-100 rounded-lg overflow-hidden shadow-md group hover:bg-emerald-200 transition-colors cursor-pointer">
                <div className="absolute inset-y-0 left-0 bg-emerald-500 w-[100%] transition-all duration-1000"></div>
                <div className="absolute inset-0 flex items-center justify-between px-4">
                  <span className="font-bold text-white text-sm z-10 drop-shadow-md">Closed Won</span>
                  <span className="font-extrabold text-white text-lg z-10 drop-shadow-md">24</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Recent Activity */}
        <div className="lg:col-span-1 bg-white rounded-xl shadow-sm border border-gray-200 flex flex-col">
          <div className="p-5 border-b border-gray-100 bg-gray-50/50 rounded-t-xl">
            <h3 className="font-bold text-gray-900">Recent Activity</h3>
          </div>
          <div className="p-0 overflow-y-auto max-h-[350px]">
            <ul className="divide-y divide-gray-100">
              <li className="p-4 hover:bg-gray-50 transition-colors cursor-pointer">
                <div className="flex gap-3">
                  <div className="w-8 h-8 rounded-full bg-emerald-100 flex items-center justify-center text-emerald-600 flex-shrink-0">
                    <i className="fas fa-check"></i>
                  </div>
                  <div>
                    <p className="text-sm font-medium text-gray-900">Deal Closed: Riverside Plot 42</p>
                    <p className="text-xs text-gray-500">Agent: Rahul K. • 10 mins ago</p>
                  </div>
                </div>
              </li>
              <li className="p-4 hover:bg-gray-50 transition-colors cursor-pointer">
                <div className="flex gap-3">
                  <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center text-blue-600 flex-shrink-0">
                    <i className="fas fa-phone"></i>
                  </div>
                  <div>
                    <p className="text-sm font-medium text-gray-900">Call Logged: Interested in 3BHK</p>
                    <p className="text-xs text-gray-500">Agent: Priya S. • 45 mins ago</p>
                  </div>
                </div>
              </li>
              <li className="p-4 hover:bg-gray-50 transition-colors cursor-pointer">
                <div className="flex gap-3">
                  <div className="w-8 h-8 rounded-full bg-amber-100 flex items-center justify-center text-amber-600 flex-shrink-0">
                    <i className="fas fa-calendar-alt"></i>
                  </div>
                  <div>
                    <p className="text-sm font-medium text-gray-900">Site Visit Scheduled</p>
                    <p className="text-xs text-gray-500">Client: Rajesh M. • 2 hours ago</p>
                  </div>
                </div>
              </li>
              <li className="p-4 hover:bg-gray-50 transition-colors cursor-pointer">
                <div className="flex gap-3">
                  <div className="w-8 h-8 rounded-full bg-purple-100 flex items-center justify-center text-purple-600 flex-shrink-0">
                    <i className="fab fa-facebook"></i>
                  </div>
                  <div>
                    <p className="text-sm font-medium text-gray-900">New Lead from Meta Ads</p>
                    <p className="text-xs text-gray-500">Campaign: Summer Bonanza • 3 hours ago</p>
                  </div>
                </div>
              </li>
            </ul>
          </div>
          <div className="p-3 border-t border-gray-100 text-center">
            <Link href="/staff/crm/all" className="text-sm font-bold text-gray-900 hover:text-brand-warning transition-colors">
              View All Activity <i className="fas fa-arrow-right ml-1"></i>
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
