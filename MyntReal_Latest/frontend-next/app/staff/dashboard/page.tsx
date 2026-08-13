"use client";

import Link from "next/link";

export default function Home() {
  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-end gap-4 mb-8">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 mb-2">Welcome to Mynt Real</h1>
          <p className="text-gray-500">Your central command center for all Mynt Real operations.</p>
        </div>
        <div className="text-right">
          <p className="text-sm text-gray-500">System Status</p>
          <div className="flex items-center gap-2 text-emerald-600 font-bold">
            <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></div>
            All Systems Operational
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {/* Core Modules */}
        <DashboardCard 
          title="Earnings Dashboard" 
          description="View your direct facilitation, matching, Guru Dakshina, and wallet details."
          icon="fas fa-coins text-amber-500"
          href="/staff/mnr-user/earnings"
        />
        <DashboardCard 
          title="Company Financials" 
          description="Macro-level financial metrics, revenue vs. payout, and system health."
          icon="fas fa-chart-line text-blue-500"
          href="/staff/financials/statement"
        />
        <DashboardCard 
          title="Income Management" 
          description="Manage pending incomes, bulk approvals, and transaction verification."
          icon="fas fa-money-bill-wave text-emerald-500"
          href="/staff/financials/incomes"
        />
        
        {/* MNR User Specific */}
        <DashboardCard 
          title="Member Network" 
          description="Explore your direct members, downline hierarchy, and team picture."
          icon="fas fa-users text-purple-500"
          href="/staff/mnr-user/members"
        />
        <DashboardCard 
          title="My Profile" 
          description="Manage your KYC, bank details, and personal settings."
          icon="fas fa-user-circle text-sky-500"
          href="/staff/mnr-user/profile"
        />
        <DashboardCard 
          title="Announcements" 
          description="Read the latest updates, popups, and history logs from Mynt Real."
          icon="fas fa-bullhorn text-rose-500"
          href="/staff/mnr-user/announcements"
        />

        {/* Allowances & Awards (Iteration 4) */}
        <DashboardCard 
          title="Allowances" 
          description="Track your field allowances, travel reimbursements, and claims."
          icon="fas fa-car text-indigo-500"
          href="/staff/mnr-user/allowances"
        />
        <DashboardCard 
          title="Awards & Bonanza" 
          description="Track your eligibility for laptops, cars, and special bonanza campaigns."
          icon="fas fa-trophy text-yellow-500"
          href="/staff/mnr-user/awards"
        />
        <DashboardCard 
          title="Task Planner" 
          description="Organize your day, manage assigned tasks, and track team activities."
          icon="fas fa-tasks text-teal-500"
          href="/staff/tasks/day-planner"
        />
      </div>

      <div className="mt-12 p-6 rounded-xl bg-white border border-gray-200 shadow-sm flex flex-col md:flex-row items-center justify-between gap-6 relative overflow-hidden">
        <div className="absolute top-0 right-0 p-8 opacity-[0.03]">
           <i className="fas fa-shield-alt text-9xl"></i>
        </div>
        <div className="relative z-10">
          <h2 className="text-xl font-bold text-gray-900 mb-2">Secure Workspace</h2>
          <p className="text-gray-500 max-w-2xl">
            You are logged into the Mynt Real securely. Ensure you lock your screen when away. Use the comprehensive sidebar on the left to navigate through all your authorized modules.
          </p>
        </div>
        <Link 
          href="/staff/mnr-user/profile"
          className="relative z-10 px-6 py-3 bg-brand-warning/10 hover:bg-brand-warning/20 text-brand-warning font-bold rounded-lg transition-colors whitespace-nowrap"
        >
          Review Security Settings
        </Link>
      </div>
    </div>
  );
}

function DashboardCard({ title, description, icon, href }: { title: string, description: string, icon: string, href: string }) {
  return (
    <Link href={href} className="group flex flex-col p-6 rounded-xl bg-white border border-gray-200 hover:border-brand-warning/50 transition-all hover:-translate-y-1 hover:shadow-lg shadow-sm">
      <div className="w-12 h-12 rounded-lg bg-gray-50 border border-gray-100 flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
        <i className={`${icon} text-xl`}></i>
      </div>
      <h3 className="text-lg font-bold text-gray-900 mb-2 group-hover:text-brand-warning transition-colors">{title}</h3>
      <p className="text-sm text-gray-500 flex-grow">{description}</p>
      
      <div className="mt-6 flex items-center text-sm font-bold text-brand-warning opacity-0 -translate-x-4 group-hover:opacity-100 group-hover:translate-x-0 transition-all">
        Access Module <i className="fas fa-arrow-right ml-2 text-xs"></i>
      </div>
    </Link>
  );
}
