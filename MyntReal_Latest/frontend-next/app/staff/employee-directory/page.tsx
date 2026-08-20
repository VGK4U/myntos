"use client";

import React, { useState, useEffect } from 'react';
import { useStaffAuth } from "@/contexts/StaffAuthContext";
import api from "@/lib/api";
import { 
  Card, CardContent, CardHeader, CardTitle, CardDescription 
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue
} from "@/components/ui/select";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow
} from "@/components/ui/table";
import {
  Users, UserCheck, UserClock, UserX, Search, Filter, 
  MapPin, Mail, Phone, Briefcase, Building, Key, CircleDollarSign
} from 'lucide-react';

export default function EmployeeDirectoryPage() {
  const { user } = useStaffAuth();
  
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<any>({
    employees: [],
    stats: { total: 0, approved: 0, pending: 0, rejected: 0 },
    filters: { departments: [], roles: [] },
    pagination: { page: 1, limit: 50, total: 0, pages: 0 }
  });

  const [search, setSearch] = useState('');
  const [deptFilter, setDeptFilter] = useState<string>('all');
  const [roleFilter, setRoleFilter] = useState<string>('all');
  const [staffTypeFilter, setStaffTypeFilter] = useState<string>('all');
  const [kycFilter, setKycFilter] = useState<string>('all');

  const fetchDirectory = async () => {
    try {
      setLoading(true);
      const params = new URLSearchParams();
      if (search) params.append('search', search);
      if (deptFilter && deptFilter !== 'all') params.append('department_id', deptFilter);
      if (roleFilter && roleFilter !== 'all') params.append('role_id', roleFilter);
      if (staffTypeFilter && staffTypeFilter !== 'all') params.append('staff_type', staffTypeFilter);
      if (kycFilter && kycFilter !== 'all') params.append('kyc_status', kycFilter);
      
      const res = await api.get(`/staff/employees/directory?${params.toString()}`);
      if (res.data?.success) {
        setData(res.data);
      }
    } catch (err) {
      console.error("Failed to fetch employee directory", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    // Debounce search
    const delayDebounceFn = setTimeout(() => {
      fetchDirectory();
    }, 400);
    return () => clearTimeout(delayDebounceFn);
  }, [search, deptFilter, roleFilter, staffTypeFilter, kycFilter]);

  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSearch(e.target.value);
  };

  // Helper to get status badge styling
  const getStatusBadge = (status: string) => {
    switch (status?.toLowerCase()) {
      case 'active':
        return <Badge className="bg-emerald-100 text-emerald-700 hover:bg-emerald-200 border-none">Active</Badge>;
      case 'inactive':
        return <Badge className="bg-amber-100 text-amber-700 hover:bg-amber-200 border-none">Inactive</Badge>;
      case 'deactivated':
        return <Badge className="bg-red-100 text-red-700 hover:bg-red-200 border-none">Deactivated</Badge>;
      case 'resigned':
        return <Badge className="bg-slate-200 text-slate-700 hover:bg-slate-300 border-none">Resigned</Badge>;
      default:
        return <Badge className="bg-slate-100 text-slate-700 border-none">{status}</Badge>;
    }
  };

  const getKycBadge = (status: string) => {
    switch (status?.toLowerCase()) {
      case 'approved':
        return <Badge className="bg-emerald-100 text-emerald-700 hover:bg-emerald-200 border-none text-[10px]">KYC Approved</Badge>;
      case 'pending':
      case 'submitted':
        return <Badge className="bg-amber-100 text-amber-700 hover:bg-amber-200 border-none text-[10px]">KYC Pending</Badge>;
      case 'rejected':
        return <Badge className="bg-red-100 text-red-700 hover:bg-red-200 border-none text-[10px]">KYC Rejected</Badge>;
      default:
        return <Badge className="bg-slate-100 text-slate-500 border-none text-[10px]">KYC Not Started</Badge>;
    }
  };

  return (
    <div className="p-6 lg:p-8 max-w-[1600px] mx-auto min-h-screen bg-slate-50">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-slate-900 tracking-tight">Employee Directory</h1>
        <p className="text-slate-500 mt-2">Manage and view all staff members across the organization.</p>
      </div>

      {/* KPI Dashboard */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <Card className="shadow-sm border-slate-200">
          <CardContent className="p-6 flex items-center gap-5">
            <div className="w-14 h-14 rounded-xl bg-indigo-100 text-indigo-600 flex items-center justify-center text-2xl shadow-inner shrink-0">
              <Users />
            </div>
            <div>
              <p className="text-sm font-semibold text-slate-500 uppercase tracking-wider">Total Active</p>
              <h3 className="text-3xl font-black text-slate-800">{data.stats.total}</h3>
            </div>
          </CardContent>
        </Card>
        <Card className="shadow-sm border-slate-200">
          <CardContent className="p-6 flex items-center gap-5">
            <div className="w-14 h-14 rounded-xl bg-emerald-100 text-emerald-600 flex items-center justify-center text-2xl shadow-inner shrink-0">
              <UserCheck />
            </div>
            <div>
              <p className="text-sm font-semibold text-slate-500 uppercase tracking-wider">KYC Approved</p>
              <h3 className="text-3xl font-black text-slate-800">{data.stats.approved}</h3>
            </div>
          </CardContent>
        </Card>
        <Card className="shadow-sm border-slate-200">
          <CardContent className="p-6 flex items-center gap-5">
            <div className="w-14 h-14 rounded-xl bg-amber-100 text-amber-600 flex items-center justify-center text-2xl shadow-inner shrink-0">
              <UserClock />
            </div>
            <div>
              <p className="text-sm font-semibold text-slate-500 uppercase tracking-wider">KYC Pending</p>
              <h3 className="text-3xl font-black text-slate-800">{data.stats.pending}</h3>
            </div>
          </CardContent>
        </Card>
        <Card className="shadow-sm border-slate-200">
          <CardContent className="p-6 flex items-center gap-5">
            <div className="w-14 h-14 rounded-xl bg-red-100 text-red-600 flex items-center justify-center text-2xl shadow-inner shrink-0">
              <UserX />
            </div>
            <div>
              <p className="text-sm font-semibold text-slate-500 uppercase tracking-wider">KYC Rejected</p>
              <h3 className="text-3xl font-black text-slate-800">{data.stats.rejected}</h3>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card className="shadow-sm border-slate-200 bg-white">
        <CardHeader className="border-b border-slate-100 bg-slate-50/50 py-4 px-6 flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-center gap-2 text-slate-800 font-semibold">
            <Briefcase className="w-5 h-5 text-indigo-500" />
            <span>Staff Directory</span>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <div className="relative">
              <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
              <Input 
                placeholder="Search name, code, email..." 
                className="pl-9 w-[250px] bg-white"
                value={search}
                onChange={handleSearchChange}
              />
            </div>
            <Select value={deptFilter} onValueChange={setDeptFilter}>
              <SelectTrigger className="w-[180px] bg-white">
                <SelectValue placeholder="Department" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Departments</SelectItem>
                {data.filters?.departments?.map((d: any) => (
                  <SelectItem key={d.id} value={d.id.toString()}>{d.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select value={roleFilter} onValueChange={setRoleFilter}>
              <SelectTrigger className="w-[160px] bg-white">
                <SelectValue placeholder="Role" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Roles</SelectItem>
                {data.filters?.roles?.map((r: any) => (
                  <SelectItem key={r.id} value={r.id.toString()}>{r.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select value={staffTypeFilter} onValueChange={setStaffTypeFilter}>
              <SelectTrigger className="w-[160px] bg-white">
                <SelectValue placeholder="Staff Type" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Staff Types</SelectItem>
                <SelectItem value="MN_STAFF">MN Staff</SelectItem>
                <SelectItem value="MN_EMPLOYEE">MN Employee</SelectItem>
                <SelectItem value="FREELANCER">Freelancer</SelectItem>
                <SelectItem value="MYNT_REAL">Mynt Real</SelectItem>
              </SelectContent>
            </Select>
            <Select value={kycFilter} onValueChange={setKycFilter}>
              <SelectTrigger className="w-[150px] bg-white">
                <SelectValue placeholder="KYC Status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All KYC Status</SelectItem>
                <SelectItem value="approved">Approved</SelectItem>
                <SelectItem value="pending">Pending</SelectItem>
                <SelectItem value="rejected">Rejected</SelectItem>
                <SelectItem value="not_started">Not Started</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <Table>
              <TableHeader className="bg-slate-50">
                <TableRow className="hover:bg-transparent">
                  <TableHead className="font-semibold text-slate-600">Employee</TableHead>
                  <TableHead className="font-semibold text-slate-600">Contact Info</TableHead>
                  <TableHead className="font-semibold text-slate-600">Role & Department</TableHead>
                  <TableHead className="font-semibold text-slate-600">Reports To</TableHead>
                  <TableHead className="font-semibold text-slate-600">Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {loading ? (
                  <TableRow>
                    <TableCell colSpan={5} className="h-48 text-center text-slate-500">
                      <i className="fas fa-spinner fa-spin mr-2"></i> Loading directory...
                    </TableCell>
                  </TableRow>
                ) : data.employees.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={5} className="h-48 text-center text-slate-500">
                      No employees found matching the filters.
                    </TableCell>
                  </TableRow>
                ) : (
                  data.employees.map((emp: any) => (
                    <TableRow key={emp.id} className="hover:bg-slate-50 transition-colors group">
                      <TableCell>
                        <div className="flex items-center gap-3">
                          <div className="w-10 h-10 rounded-full bg-indigo-100 text-indigo-700 flex items-center justify-center font-bold uppercase shrink-0">
                            {emp.full_name?.substring(0, 2) || 'U'}
                          </div>
                          <div>
                            <div className="font-bold text-slate-800 group-hover:text-indigo-600 transition-colors">
                              {emp.salutation ? `${emp.salutation} ` : ''}{emp.full_name}
                            </div>
                            <div className="text-xs text-slate-500 flex items-center gap-1 mt-0.5 font-mono bg-slate-100 px-1.5 py-0.5 rounded w-fit">
                              <Key className="w-3 h-3" /> {emp.emp_code}
                            </div>
                          </div>
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="flex flex-col gap-1 text-sm">
                          {emp.email ? (
                            <div className="flex items-center gap-1.5 text-slate-600">
                              <Mail className="w-3.5 h-3.5 text-slate-400" /> {emp.email}
                            </div>
                          ) : (
                            <div className="text-slate-400 text-xs italic">No email</div>
                          )}
                          {emp.phone ? (
                            <div className="flex items-center gap-1.5 text-slate-600">
                              <Phone className="w-3.5 h-3.5 text-slate-400" /> {emp.phone}
                            </div>
                          ) : null}
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="font-medium text-slate-700 text-sm">{emp.designation || 'No Designation'}</div>
                        <div className="text-xs text-slate-500 mt-1 flex flex-col gap-1">
                          <span className="flex items-center gap-1">
                            <Briefcase className="w-3 h-3" /> {emp.role?.role_name || 'No Role'}
                          </span>
                          <span className="flex items-center gap-1">
                            <Building className="w-3 h-3" /> {emp.department?.name || 'No Department'}
                          </span>
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="text-sm text-slate-600">
                          {emp.reporting_manager?.full_name || <span className="text-slate-400 italic">No Manager</span>}
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="flex flex-col gap-2 items-start">
                          {getStatusBadge(emp.status)}
                          {getKycBadge(emp.kyc?.status)}
                        </div>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
