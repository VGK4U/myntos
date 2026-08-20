"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useStaffAuth } from "@/contexts/StaffAuthContext";
import api from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { 
  Users, UserCheck, Building, Calendar, ListTodo, PhoneCall, 
  Trophy, Clock, PieChart, Zap, UserPlus, PlusCircle, 
  RefreshCw, Key, UserCircle, ExternalLink 
} from "lucide-react";

export default function StaffDashboardPage() {
  const { user } = useStaffAuth();
  
  const [loading, setLoading] = useState(true);
  const [employees, setEmployees] = useState<any[]>([]);
  const [departments, setDepartments] = useState<any[]>([]);
  
  const [freelancerData, setFreelancerData] = useState<any>(null);
  const [incentiveData, setIncentiveData] = useState<any>(null);
  const [incentiveLoading, setIncentiveLoading] = useState(false);
  const [incentiveError, setIncentiveError] = useState(false);

  // Derive if user is a restricted freelancer
  const isRestrictedFreelancer = user?.staff_type === 'FREELANCER' && user?.freelancer_access_mode === 'only_leads';

  const fetchDashboardData = async () => {
    setLoading(true);
    
    try {
      if (isRestrictedFreelancer) {
        const res = await api.get('/crm/dashboard-v2');
        setFreelancerData(res.data?.my_performance?.summary || {});
      } else {
        const [empRes, deptRes] = await Promise.all([
          api.get('/staff/employees?status=active').catch(() => null),
          api.get('/staff/departments').catch(() => null)
        ]);
        if (empRes?.data?.employees) setEmployees(empRes.data.employees);
        if (deptRes?.data?.departments) setDepartments(deptRes.data.departments);
      }
    } catch (err) {
      console.warn("Failed to fetch dashboard data", err);
    } finally {
      setLoading(false);
    }
  };

  const fetchIncentives = async () => {
    try {
      setIncentiveLoading(true);
      const now = new Date();
      const month = now.getMonth() + 1;
      const year = now.getFullYear();
      const res = await api.get(`/staff/performance/my-incentive-achievements?month=${month}&year=${year}`);
      const empData = (res.data?.data || [])[0];
      if (empData && empData.total_incentive_earned) {
        setIncentiveData(empData);
      } else {
        setIncentiveError(true);
      }
    } catch (err) {
      setIncentiveError(true);
    } finally {
      setIncentiveLoading(false);
    }
  };

  useEffect(() => {
    if (!user) return;
    fetchDashboardData();
    fetchIncentives();
  }, [user, isRestrictedFreelancer]);

  const activeEmployees = employees.filter(e => e.is_active).length;
  const lastLogin = new Date().toLocaleDateString('en-IN', { day: 'numeric', month: 'short' });

  const renderSkeletons = () => (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
      {[1, 2, 3, 4].map((i) => (
        <Card key={i} className="shadow-sm border-slate-200">
          <CardContent className="p-6 flex items-center gap-5">
            <Skeleton className="w-14 h-14 rounded-xl shrink-0" />
            <div className="space-y-2 w-full">
              <Skeleton className="h-8 w-20" />
              <Skeleton className="h-4 w-28" />
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );

  const renderIncentiveWidget = () => {
    const now = new Date();
    const monthName = ['','January','February','March','April','May','June','July','August','September','October','November','December'][now.getMonth() + 1];
    const year = now.getFullYear();

    const formatCurrency = (n: number) => '₹' + Number(n || 0).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    const formatCurrencyShort = (n: number) => '₹' + Number(n || 0).toLocaleString('en-IN', { minimumFractionDigits: 0, maximumFractionDigits: 0 });

    const CAT_LABELS: Record<string, string> = { training: 'ETC Students', solar: 'Solar', ev_b2c: 'B2C', ev_b2b: 'B2B', insurance: 'Insurance', real_estate: 'Real Estate' };
    const CAT_UNITS: Record<string, string> = { training: 'students', solar: 'deals', ev_b2c: 'deals', ev_b2b: 'deals', insurance: '₹', real_estate: '₹' };

    let totalSelf = 0, totalCo = 0;
    let activeCats: any[] = [];
    if (incentiveData && incentiveData.categories) {
      activeCats = incentiveData.categories.filter((c: any) => c.incentive_earned > 0);
      activeCats.forEach((c: any) => {
        totalSelf += (c.self_incentive || 0);
        totalCo += (c.company_incentive_base || 0) + (c.bonus_applied ? (c.incentive_earned - c.self_incentive - c.company_incentive_base) : 0);
      });
    }

    return (
      <Card className="mb-8 overflow-hidden border-slate-200 shadow-sm transition-all hover:shadow-md">
        <CardHeader className="bg-slate-50/50 border-b border-slate-100 flex flex-row items-center justify-between py-4">
          <CardTitle className="text-lg flex items-center gap-2 font-bold text-slate-800">
            <Trophy className="w-5 h-5 text-amber-500" /> 
            My Incentive Earnings — <span className="text-indigo-600 ml-1">{monthName} {year}</span>
          </CardTitle>
          <Link href="/staff/my-lead-incentives" className="text-sm text-indigo-600 hover:text-indigo-800 font-medium flex items-center gap-1.5 border border-indigo-200 px-3 py-1.5 rounded-lg bg-white shadow-sm transition-colors hover:bg-indigo-50">
            Full Details <ExternalLink className="w-3.5 h-3.5" />
          </Link>
        </CardHeader>
        <CardContent className="p-6">
          {incentiveLoading ? (
            <div className="space-y-4">
              <Skeleton className="h-28 w-full rounded-xl" />
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {[1, 2, 3, 4].map((i) => <Skeleton key={i} className="h-24 rounded-xl" />)}
              </div>
            </div>
          ) : incentiveError || !activeCats.length ? (
            <div className="text-center py-10 text-slate-400 bg-slate-50/50 rounded-xl border border-dashed border-slate-200">
              <div className="w-12 h-12 rounded-full bg-slate-100 flex items-center justify-center mx-auto mb-3">
                <PieChart className="w-6 h-6 text-slate-300" />
              </div>
              <p className="font-medium text-slate-500">No incentive activity recorded this month yet.</p>
            </div>
          ) : (
            <div className="animate-in fade-in slide-in-from-bottom-2 duration-500">
              <div className="bg-gradient-to-br from-indigo-600 via-purple-600 to-indigo-800 rounded-xl p-6 text-white mb-6 flex flex-col md:flex-row items-start md:items-center justify-between gap-6 shadow-lg relative overflow-hidden">
                <div className="absolute top-0 right-0 w-64 h-64 bg-white opacity-5 rounded-full -translate-y-1/2 translate-x-1/3 blur-2xl"></div>
                
                <div className="relative z-10">
                  <div className="text-xs uppercase tracking-widest text-indigo-200 font-semibold mb-1.5">Total Earned This Month</div>
                  <div className="text-4xl md:text-5xl font-black tracking-tight">{formatCurrency(incentiveData.total_incentive_earned)}</div>
                </div>
                
                <div className="flex gap-8 relative z-10 bg-white/10 p-4 rounded-xl backdrop-blur-sm border border-white/10">
                  <div>
                    <div className="text-[10px] uppercase tracking-wider text-indigo-200 font-semibold mb-1">Self Leads</div>
                    <div className="text-xl font-bold">{formatCurrencyShort(totalSelf)}</div>
                  </div>
                  <div className="w-px bg-white/20"></div>
                  <div>
                    <div className="text-[10px] uppercase tracking-wider text-indigo-200 font-semibold mb-1">Company Leads</div>
                    <div className="text-xl font-bold">{formatCurrencyShort(totalCo)}</div>
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
                {['training', 'solar', 'ev_b2c', 'ev_b2b', 'insurance', 'real_estate']
                  .map(slug => activeCats.find((c: any) => c.slug === slug))
                  .filter(Boolean)
                  .map((c: any) => {
                    const unit = CAT_UNITS[c.slug] || '';
                    const count = (c.self_count || 0) + (c.company_count || 0);
                    const achDisp = unit === '₹' ? formatCurrencyShort(c.achieved_amount) : count + ' ' + unit;
                    
                    return (
                      <div key={c.slug} className={`rounded-xl p-4 border-l-[4px] shadow-sm transition-transform hover:-translate-y-1 ${c.bonus_applied ? 'border-l-amber-500 bg-amber-50/40' : 'border-l-indigo-500 bg-white border border-slate-100'}`}>
                        <div className="text-xs font-bold text-slate-500 uppercase tracking-wide flex justify-between items-center">
                          {CAT_LABELS[c.slug] || c.slug} 
                          <Zap className={`w-3.5 h-3.5 ${c.bonus_applied ? 'text-amber-500' : 'text-indigo-400 opacity-50'}`} />
                        </div>
                        <div className="text-xl font-bold text-slate-800 mt-2 flex items-center gap-1.5 flex-wrap">
                          {formatCurrency(c.incentive_earned)}
                          {c.bonus_applied && <Badge variant="secondary" className="bg-amber-500 hover:bg-amber-600 text-white text-[9px] px-1.5 py-0 rounded">×{c.bonus_multiplier} BONUS</Badge>}
                        </div>
                        <div className="text-[11px] text-slate-500 mt-1 font-medium bg-slate-100/50 inline-block px-1.5 py-0.5 rounded">{achDisp} achieved</div>
                      </div>
                    );
                  })}
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    );
  };

  return (
    <div className="p-6 lg:p-8 max-w-[1600px] mx-auto min-h-screen bg-slate-50/30">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-slate-800 tracking-tight">Dashboard Overview</h1>
        <p className="text-slate-500 text-sm mt-1">Welcome back, {user?.name || user?.full_name || 'Staff Member'}</p>
      </div>

      {loading ? renderSkeletons() : !isRestrictedFreelancer ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 mb-8 animate-in fade-in duration-500">
          <Card className="shadow-sm border-slate-200 hover:shadow-md transition-shadow">
            <CardContent className="p-6 flex items-center gap-5">
              <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-blue-500 to-blue-700 text-white flex items-center justify-center shadow-inner shrink-0">
                <Users className="w-6 h-6" />
              </div>
              <div>
                <h3 className="text-3xl font-black text-slate-800">{employees.length}</h3>
                <p className="text-sm font-medium text-slate-500">Total Employees</p>
              </div>
            </CardContent>
          </Card>
          <Card className="shadow-sm border-slate-200 hover:shadow-md transition-shadow">
            <CardContent className="p-6 flex items-center gap-5">
              <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-emerald-500 to-emerald-700 text-white flex items-center justify-center shadow-inner shrink-0">
                <UserCheck className="w-6 h-6" />
              </div>
              <div>
                <h3 className="text-3xl font-black text-slate-800">{activeEmployees}</h3>
                <p className="text-sm font-medium text-slate-500">Active Employees</p>
              </div>
            </CardContent>
          </Card>
          <Card className="shadow-sm border-slate-200 hover:shadow-md transition-shadow">
            <CardContent className="p-6 flex items-center gap-5">
              <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-purple-500 to-purple-700 text-white flex items-center justify-center shadow-inner shrink-0">
                <Building className="w-6 h-6" />
              </div>
              <div>
                <h3 className="text-3xl font-black text-slate-800">{departments.length}</h3>
                <p className="text-sm font-medium text-slate-500">Departments</p>
              </div>
            </CardContent>
          </Card>
          <Card className="shadow-sm border-slate-200 hover:shadow-md transition-shadow">
            <CardContent className="p-6 flex items-center gap-5">
              <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-amber-500 to-amber-700 text-white flex items-center justify-center shadow-inner shrink-0">
                <Calendar className="w-6 h-6" />
              </div>
              <div>
                <h3 className="text-3xl font-black text-slate-800">{lastLogin}</h3>
                <p className="text-sm font-medium text-slate-500">Last Login</p>
              </div>
            </CardContent>
          </Card>
        </div>
      ) : (
        <div className="animate-in fade-in duration-500">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
            <Card className="shadow-sm border-slate-200 hover:shadow-md transition-shadow">
              <CardContent className="p-6 flex items-center gap-5">
                <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-blue-500 to-blue-700 text-white flex items-center justify-center shadow-inner shrink-0">
                  <ListTodo className="w-6 h-6" />
                </div>
                <div>
                  <h3 className="text-3xl font-black text-slate-800">{freelancerData?.total_leads || 0}</h3>
                  <p className="text-sm font-medium text-slate-500">Assigned Leads</p>
                </div>
              </CardContent>
            </Card>
            <Card className="shadow-sm border-slate-200 hover:shadow-md transition-shadow">
              <CardContent className="p-6 flex items-center gap-5">
                <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-amber-500 to-amber-700 text-white flex items-center justify-center shadow-inner shrink-0">
                  <PhoneCall className="w-6 h-6" />
                </div>
                <div>
                  <h3 className="text-3xl font-black text-slate-800">{freelancerData?.contacted || freelancerData?.contacted_today || 0}</h3>
                  <p className="text-sm font-medium text-slate-500">Contacted</p>
                </div>
              </CardContent>
            </Card>
            <Card className="shadow-sm border-slate-200 hover:shadow-md transition-shadow">
              <CardContent className="p-6 flex items-center gap-5">
                <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-emerald-500 to-emerald-700 text-white flex items-center justify-center shadow-inner shrink-0">
                  <Trophy className="w-6 h-6" />
                </div>
                <div>
                  <h3 className="text-3xl font-black text-slate-800">{freelancerData?.won || 0}</h3>
                  <p className="text-sm font-medium text-slate-500">Won Deals</p>
                </div>
              </CardContent>
            </Card>
            <Card className="shadow-sm border-slate-200 hover:shadow-md transition-shadow">
              <CardContent className="p-6 flex items-center gap-5">
                <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-red-500 to-red-700 text-white flex items-center justify-center shadow-inner shrink-0">
                  <Clock className="w-6 h-6" />
                </div>
                <div>
                  <h3 className="text-3xl font-black text-slate-800">{freelancerData?.overdue || 0}</h3>
                  <p className="text-sm font-medium text-slate-500">Overdue</p>
                </div>
              </CardContent>
            </Card>
          </div>

          <Card className="mb-8 border-slate-200 shadow-sm">
            <CardHeader className="border-b border-slate-100 bg-slate-50/50 py-4">
              <CardTitle className="text-base font-semibold text-slate-700 flex items-center gap-2">
                <PieChart className="w-5 h-5 text-blue-500" /> Lead Status Breakdown
              </CardTitle>
            </CardHeader>
            <CardContent className="p-6">
              <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-4">
                {[
                  { id: 'new', label: 'New', color: 'text-blue-600', bg: 'bg-blue-50' },
                  { id: 'contacted', label: 'Contacted', color: 'text-cyan-600', bg: 'bg-cyan-50' },
                  { id: 'interested', label: 'Interested', color: 'text-amber-500', bg: 'bg-amber-50' },
                  { id: 'qualified', label: 'Qualified', color: 'text-emerald-500', bg: 'bg-emerald-50' },
                  { id: 'proposal', label: 'Proposal', color: 'text-purple-500', bg: 'bg-purple-50' },
                  { id: 'on_hold', label: 'On Hold', color: 'text-slate-600', bg: 'bg-slate-100' },
                  { id: 'won', label: 'Won', color: 'text-emerald-600 font-bold', bg: 'bg-emerald-100/50' },
                  { id: 'lost', label: 'Lost', color: 'text-red-500', bg: 'bg-red-50' }
                ].map(s => (
                  <div key={s.id} className={`${s.bg} rounded-xl p-4 text-center transition-transform hover:-translate-y-1`}>
                    <div className="text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-1.5">{s.label}</div>
                    <div className={`text-2xl font-black ${s.color}`}>{freelancerData?.[s.id] || 0}</div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {renderIncentiveWidget()}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <Card className="shadow-sm border-slate-200 hover:shadow-md transition-shadow">
          <CardHeader className="border-b border-slate-100 py-4">
            <CardTitle className="text-base font-semibold flex items-center gap-2 text-slate-800">
              <Zap className="w-5 h-5 text-amber-500" /> Quick Actions
            </CardTitle>
          </CardHeader>
          <CardContent className="p-6">
            <div className="grid grid-cols-2 gap-4">
              {!isRestrictedFreelancer && (
                <>
                  <Link href="/staff/employees" className="flex items-center gap-3 p-3.5 rounded-xl border border-slate-200 hover:border-blue-300 hover:bg-blue-50/80 transition-all group shadow-sm hover:shadow">
                    <div className="w-9 h-9 rounded-lg bg-blue-100 text-blue-600 flex items-center justify-center group-hover:bg-blue-600 group-hover:text-white transition-colors"><UserPlus className="w-4 h-4" /></div>
                    <span className="font-medium text-slate-700 text-sm group-hover:text-blue-900">Add Employee</span>
                  </Link>
                  <Link href="/staff/departments" className="flex items-center gap-3 p-3.5 rounded-xl border border-slate-200 hover:border-purple-300 hover:bg-purple-50/80 transition-all group shadow-sm hover:shadow">
                    <div className="w-9 h-9 rounded-lg bg-purple-100 text-purple-600 flex items-center justify-center group-hover:bg-purple-600 group-hover:text-white transition-colors"><PlusCircle className="w-4 h-4" /></div>
                    <span className="font-medium text-slate-700 text-sm group-hover:text-purple-900">Add Department</span>
                  </Link>
                </>
              )}
              <button onClick={() => fetchDashboardData()} className="flex items-center gap-3 p-3.5 rounded-xl border border-slate-200 hover:border-emerald-300 hover:bg-emerald-50/80 transition-all group text-left shadow-sm hover:shadow">
                <div className="w-9 h-9 rounded-lg bg-emerald-100 text-emerald-600 flex items-center justify-center group-hover:bg-emerald-600 group-hover:text-white transition-colors">
                  <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
                </div>
                <span className="font-medium text-slate-700 text-sm group-hover:text-emerald-900">Refresh Data</span>
              </button>
              <Link href="/staff/change-password" className="flex items-center gap-3 p-3.5 rounded-xl border border-slate-200 hover:border-slate-300 hover:bg-slate-50/80 transition-all group shadow-sm hover:shadow">
                <div className="w-9 h-9 rounded-lg bg-slate-200 text-slate-600 flex items-center justify-center group-hover:bg-slate-600 group-hover:text-white transition-colors"><Key className="w-4 h-4" /></div>
                <span className="font-medium text-slate-700 text-sm group-hover:text-slate-900">Change Password</span>
              </Link>
            </div>
          </CardContent>
        </Card>

        <Card className="shadow-sm border-slate-200 hover:shadow-md transition-shadow">
          <CardHeader className="border-b border-slate-100 py-4 bg-slate-50/30">
            <CardTitle className="text-base font-semibold flex items-center gap-2 text-slate-800">
              <UserCircle className="w-5 h-5 text-blue-500" /> Your Profile
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <div className="divide-y divide-slate-100">
              <div className="flex justify-between items-center px-6 py-4 hover:bg-slate-50 transition-colors">
                <span className="text-sm text-slate-500 font-medium">Employee Code</span>
                <span className="text-sm font-bold text-slate-800 bg-slate-100 px-2 py-1 rounded">{user?.emp_code || user?.employee_code || '-'}</span>
              </div>
              <div className="flex justify-between items-center px-6 py-4 hover:bg-slate-50 transition-colors">
                <span className="text-sm text-slate-500 font-medium">Email</span>
                <span className="text-sm font-medium text-slate-800">{user?.email || '-'}</span>
              </div>
              <div className="flex justify-between items-center px-6 py-4 hover:bg-slate-50 transition-colors">
                <span className="text-sm text-slate-500 font-medium">Department</span>
                <span className="text-sm font-medium text-slate-800">{user?.department_name || '-'}</span>
              </div>
              <div className="flex justify-between items-center px-6 py-4 hover:bg-slate-50 transition-colors">
                <span className="text-sm text-slate-500 font-medium">Designation</span>
                <span className="text-sm font-medium text-slate-800">{user?.designation || '-'}</span>
              </div>
              <div className="flex justify-between items-center px-6 py-4 hover:bg-slate-50 transition-colors">
                <span className="text-sm text-slate-500 font-medium">2FA Status</span>
                {user?.is_2fa_enabled || user?.totp_enabled ? (
                  <Badge variant="default" className="bg-emerald-100 text-emerald-700 hover:bg-emerald-200 border-none shadow-none font-bold">Enabled</Badge>
                ) : (
                  <Badge variant="destructive" className="bg-red-100 text-red-700 hover:bg-red-200 border-none shadow-none font-bold">Disabled</Badge>
                )}
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
