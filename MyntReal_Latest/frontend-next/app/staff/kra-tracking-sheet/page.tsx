"use client";

import React, { useState, useEffect, useMemo } from 'react';
import api from '@/lib/api';
import { useStaffAuth } from '@/contexts/StaffAuthContext';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Label } from '@/components/ui/label';
import { Search, Info, Users, Filter, Loader2, ArrowUpDown, RefreshCw, CheckCircle, Clock, AdjustmentsHorizontal, Forward, Ban, ListChecks } from 'lucide-react';

interface TeamMember {
  employee_id: number;
  employee_name: string;
  department: string | null;
  performance_percentage: number;
  assigned_kras: number;
  completed_kras: number;
}

interface KRAInstance {
  id: number;
  instance_date: string;
  kra_title: string;
  completion_status: string;
  submitted_at: string | null;
  manager_review_status: string;
  time_spent_minutes: number;
  staff_notes: string | null;
  manager_remarks: string | null;
}

const PAGE_SIZE = 25;

export default function KraTrackingSheetPage() {
  const { user } = useStaffAuth();
  
  const [teamMembers, setTeamMembers] = useState<TeamMember[]>([]);
  const [selectedMemberId, setSelectedMemberId] = useState<number | null>(null);
  const [krasData, setKrasData] = useState<KRAInstance[]>([]);
  const [loadingTeam, setLoadingTeam] = useState(true);
  const [loadingKras, setLoadingKras] = useState(false);
  const [memberSearch, setMemberSearch] = useState('');

  // Filters
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [reviewFilter, setReviewFilter] = useState('all');
  const [searchKRA, setSearchKRA] = useState('');

  // Pagination & Sort
  const [currentPage, setCurrentPage] = useState(1);
  const [sortCol, setSortCol] = useState<keyof KRAInstance>('instance_date');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc');

  useEffect(() => {
    const today = new Date();
    const fromStr = today.toISOString().split('T')[0];
    const toDate = new Date(today);
    toDate.setDate(toDate.getDate() + 3);
    const toStr = toDate.toISOString().split('T')[0];
    setDateFrom(fromStr);
    setDateTo(toStr);
  }, []);

  const handleDateFromChange = (val: string) => {
    setDateFrom(val);
    if (val) {
      const f = new Date(val);
      f.setDate(f.getDate() + 3);
      setDateTo(f.toISOString().split('T')[0]);
    }
  };

  useEffect(() => {
    if (dateFrom && dateTo) {
      loadTeamMembers();
    }
  }, [dateFrom, dateTo]);

  useEffect(() => {
    if (selectedMemberId && dateFrom && dateTo) {
      loadMemberKras();
    }
  }, [selectedMemberId, dateFrom, dateTo]);

  const loadTeamMembers = async () => {
    setLoadingTeam(true);
    try {
      let res = await api.get(`/staff/kra/team-summary`, { params: { scope: 'all', date_from: dateFrom, date_to: dateTo }});
      if (res.data?.summary) {
        setTeamMembers(res.data.summary);
      }
    } catch (e: any) {
      if (e.response?.status === 403) {
         try {
           let res2 = await api.get(`/staff/kra/team-summary`, { params: { scope: 'team', date_from: dateFrom, date_to: dateTo }});
           setTeamMembers(res2.data?.summary || []);
         } catch (err) {
           console.error("No team access", err);
           setTeamMembers([]);
         }
      } else {
        console.error(e);
        setTeamMembers([]);
      }
    } finally {
      setLoadingTeam(false);
    }
  };

  const loadMemberKras = async () => {
    if (!selectedMemberId) return;
    setLoadingKras(true);
    try {
      const res = await api.get(`/staff/kra/instances`, {
        params: { employee_id: selectedMemberId, date_from: dateFrom, date_to: dateTo }
      });
      setKrasData(res.data?.instances || []);
      setCurrentPage(1);
    } catch (e) {
      console.error(e);
    } finally {
      setLoadingKras(false);
    }
  };

  const filteredMembers = useMemo(() => {
    if (!memberSearch) return teamMembers;
    const lower = memberSearch.toLowerCase();
    return teamMembers.filter(m => m.employee_name?.toLowerCase().includes(lower));
  }, [teamMembers, memberSearch]);

  const filteredKras = useMemo(() => {
    let data = [...krasData];
    if (statusFilter !== 'all') {
      data = data.filter(k => (k.completion_status || 'pending') === statusFilter);
    }
    if (reviewFilter !== 'all') {
      if (reviewFilter === 'approved') {
         data = data.filter(k => k.manager_review_status === 'approved' || k.manager_review_status === 'edited_by_manager');
      } else {
         data = data.filter(k => k.manager_review_status === reviewFilter);
      }
    }
    if (searchKRA) {
      const lSearch = searchKRA.toLowerCase();
      data = data.filter(k => (k.kra_title || '').toLowerCase().includes(lSearch));
    }
    
    // sorting
    data.sort((a, b) => {
      let va = a[sortCol];
      let vb = b[sortCol];
      
      if (sortCol === 'instance_date') {
         const da = new Date(va as string || '1970-01-01').getTime();
         const db = new Date(vb as string || '1970-01-01').getTime();
         if (da === db) {
            const pa = a.completion_status === 'pending' ? 0 : 1;
            const pb = b.completion_status === 'pending' ? 0 : 1;
            return pa - pb;
         }
         return sortDir === 'asc' ? da - db : db - da;
      }
      
      if (typeof va === 'number' && typeof vb === 'number') {
        return sortDir === 'asc' ? va - vb : vb - va;
      }
      
      va = (va || '').toString().toLowerCase();
      vb = (vb || '').toString().toLowerCase();
      if (va < vb) return sortDir === 'asc' ? -1 : 1;
      if (va > vb) return sortDir === 'asc' ? 1 : -1;
      return 0;
    });
    
    return data;
  }, [krasData, statusFilter, reviewFilter, searchKRA, sortCol, sortDir]);

  const paginatedKras = useMemo(() => {
    const start = (currentPage - 1) * PAGE_SIZE;
    return filteredKras.slice(start, start + PAGE_SIZE);
  }, [filteredKras, currentPage]);

  const totalPages = Math.max(1, Math.ceil(filteredKras.length / PAGE_SIZE));

  const toggleSort = (col: keyof KRAInstance) => {
    if (sortCol === col) {
      setSortDir(sortDir === 'asc' ? 'desc' : 'asc');
    } else {
      setSortCol(col);
      setSortDir('asc');
    }
  };

  const getStatusBadge = (s: string, submittedAt: string | null) => {
    if (submittedAt) return <Badge className="bg-indigo-100 text-indigo-700 hover:bg-indigo-100 border-none shadow-none">Submitted</Badge>;
    const map: Record<string, {label: string, className: string}> = {
      completed: { label: 'Completed', className: 'bg-emerald-100 text-emerald-700' },
      pending: { label: 'Pending', className: 'bg-amber-100 text-amber-700' },
      in_progress: { label: 'In Progress', className: 'bg-blue-100 text-blue-700' },
      partial: { label: 'Partial', className: 'bg-orange-100 text-orange-700' },
      skipped: { label: 'Skipped', className: 'bg-red-100 text-red-700' },
      na: { label: 'NA', className: 'bg-gray-100 text-gray-500 border-dashed border-2 border-gray-300' }
    };
    const mapped = map[s] || { label: s, className: 'bg-gray-100 text-gray-700' };
    return <Badge className={`${mapped.className} hover:${mapped.className} border-none shadow-none`}>{mapped.label}</Badge>;
  };

  const getReviewBadge = (s: string) => {
    if (s === 'approved' || s === 'edited_by_manager') return <Badge className="bg-emerald-100 text-emerald-700 hover:bg-emerald-100 border-none shadow-none">Approved ✓</Badge>;
    if (s === 'rejected') return <Badge className="bg-red-100 text-red-700 hover:bg-red-100 border-none shadow-none">Rejected</Badge>;
    if (s === 'pending_review') return <Badge className="bg-amber-100 text-amber-700 hover:bg-amber-100 border-none shadow-none">Pending Review</Badge>;
    return <Badge className="bg-amber-100 text-amber-700 hover:bg-amber-100 border-none shadow-none">{s || 'Pending'}</Badge>;
  };

  const formatDate = (dateStr: string) => {
    if (!dateStr) return '-';
    try {
      const d = new Date(dateStr + 'T00:00:00');
      const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
      return `${d.getDate()} ${months[d.getMonth()]} ${d.getFullYear()}`;
    } catch {
      return dateStr;
    }
  };

  const getSummaryCounts = () => {
    const counts = { total: 0, completed: 0, pending: 0, in_progress: 0, partial: 0, skipped: 0, na: 0 };
    krasData.forEach(k => {
      const s = k.completion_status || 'pending';
      counts.total++;
      if ((counts as any)[s] !== undefined) (counts as any)[s]++;
    });
    return counts;
  };

  const summary = getSummaryCounts();

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6 bg-gray-50 min-h-screen">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-gray-900">KRA Tracking Sheet</h1>
          <p className="text-sm text-gray-500 mt-1">View team KRA tracking across all staff members.</p>
        </div>
      </div>

      <div className="bg-sky-50 border border-sky-200 rounded-lg p-4 flex items-center gap-3">
        <Info className="text-sky-600 w-5 h-5" />
        <span className="text-sky-900 text-sm">Select a member to see their daily KRA details.</span>
      </div>

      <div className="flex flex-col lg:flex-row gap-6">
        {/* Left Panel: Team Members */}
        <div className="lg:w-1/3 w-full flex-shrink-0">
          <Card className="h-full border-none shadow-sm overflow-hidden flex flex-col">
            <div className="bg-gradient-to-r from-indigo-500 to-purple-500 p-4">
              <h3 className="text-white font-medium flex items-center gap-2">
                <Users className="w-5 h-5" /> Team Members
              </h3>
            </div>
            <CardContent className="p-4 flex-1 flex flex-col min-h-0">
              <div className="relative mb-4">
                <Search className="absolute left-3 top-2.5 h-4 w-4 text-gray-400" />
                <Input 
                  placeholder="Search member..." 
                  className="pl-9 bg-gray-50"
                  value={memberSearch}
                  onChange={(e) => setMemberSearch(e.target.value)}
                />
              </div>
              
              <div className="flex-1 overflow-y-auto space-y-2 pr-2" style={{ maxHeight: '600px' }}>
                {loadingTeam ? (
                  <div className="flex flex-col items-center justify-center h-32 text-gray-400">
                    <Loader2 className="w-8 h-8 animate-spin mb-2" />
                    <p className="text-sm">Loading team...</p>
                  </div>
                ) : filteredMembers.length === 0 ? (
                  <div className="flex flex-col items-center justify-center h-32 text-gray-400">
                    <Users className="w-8 h-8 mb-2 opacity-50" />
                    <p className="text-sm">No team members found</p>
                  </div>
                ) : (
                  filteredMembers.map(m => (
                    <div 
                      key={m.employee_id} 
                      onClick={() => setSelectedMemberId(m.employee_id)}
                      className={`p-3 rounded-lg border-2 cursor-pointer transition-all ${selectedMemberId === m.employee_id ? 'border-indigo-500 bg-indigo-50' : 'border-transparent bg-white hover:border-indigo-200 shadow-sm'}`}
                    >
                      <div className="font-semibold text-sm text-gray-900">{m.employee_name || 'Unknown'}</div>
                      <div className="text-xs text-gray-500 mt-0.5">{m.department || '-'}</div>
                      <div className="flex gap-3 mt-2 text-[11px] text-gray-600">
                        <span className="font-bold text-indigo-600">{m.performance_percentage || 0}%</span>
                        <span>Assigned: {m.assigned_kras || 0}</span>
                        <span>Done: {m.completed_kras || 0}</span>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Right Panel: KRA Details */}
        <div className="lg:w-2/3 w-full flex flex-col gap-6">
          
          {/* Summary Cards */}
          {selectedMemberId && (
            <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-3">
              {[
                { key: 'total', label: 'Total', icon: <ListChecks className="w-5 h-5"/>, color: 'text-indigo-600', border: 'border-l-indigo-500' },
                { key: 'completed', label: 'Completed', icon: <CheckCircle className="w-5 h-5"/>, color: 'text-emerald-500', border: 'border-l-emerald-500' },
                { key: 'pending', label: 'Pending', icon: <Clock className="w-5 h-5"/>, color: 'text-amber-500', border: 'border-l-amber-500' },
                { key: 'in_progress', label: 'In Progress', icon: <Loader2 className="w-5 h-5"/>, color: 'text-blue-500', border: 'border-l-blue-500' },
                { key: 'partial', label: 'Partial', icon: <AdjustmentsHorizontal className="w-5 h-5"/>, color: 'text-orange-500', border: 'border-l-orange-500' },
                { key: 'skipped', label: 'Skipped', icon: <Forward className="w-5 h-5"/>, color: 'text-red-500', border: 'border-l-red-500' },
                { key: 'na', label: 'NA', icon: <Ban className="w-5 h-5"/>, color: 'text-gray-400', border: 'border-l-gray-400' },
              ].map(c => (
                <div key={c.key} className={`bg-white rounded-lg p-3 text-center shadow-sm border-l-4 ${c.border}`}>
                  <div className={`flex justify-center mb-1 ${c.color}`}>{c.icon}</div>
                  <div className={`text-xl font-bold ${c.color}`}>{(summary as any)[c.key]}</div>
                  <div className="text-[10px] text-gray-500 font-semibold uppercase tracking-wider mt-1">{c.label}</div>
                </div>
              ))}
            </div>
          )}

          {/* Filters */}
          <Card className="border-none shadow-sm overflow-hidden">
            <div className="bg-gradient-to-r from-indigo-500 to-purple-500 p-4">
              <h3 className="text-white font-medium flex items-center gap-2">
                <Filter className="w-5 h-5" /> Filters
              </h3>
            </div>
            <CardContent className="p-4">
              <div className="flex flex-wrap gap-4 items-end">
                <div className="space-y-1 flex-1 min-w-[140px]">
                  <Label className="text-xs font-semibold text-gray-600">Date From</Label>
                  <Input type="date" value={dateFrom} onChange={e => handleDateFromChange(e.target.value)} className="bg-gray-50" />
                </div>
                <div className="space-y-1 flex-1 min-w-[140px]">
                  <Label className="text-xs font-semibold text-gray-600">Date To <span className="text-[10px] text-gray-400 font-normal">(auto +3 days)</span></Label>
                  <Input type="date" value={dateTo} readOnly className="bg-gray-100 text-gray-500 cursor-not-allowed" />
                </div>
                <div className="space-y-1 flex-1 min-w-[140px]">
                  <Label className="text-xs font-semibold text-gray-600">Status</Label>
                  <Select value={statusFilter} onValueChange={setStatusFilter}>
                    <SelectTrigger className="bg-gray-50"><SelectValue placeholder="All" /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All</SelectItem>
                      <SelectItem value="pending">Pending</SelectItem>
                      <SelectItem value="completed">Completed</SelectItem>
                      <SelectItem value="in_progress">In Progress</SelectItem>
                      <SelectItem value="partial">Partial</SelectItem>
                      <SelectItem value="skipped">Skipped</SelectItem>
                      <SelectItem value="na">NA</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-1 flex-1 min-w-[140px]">
                  <Label className="text-xs font-semibold text-gray-600">Review Status</Label>
                  <Select value={reviewFilter} onValueChange={setReviewFilter}>
                    <SelectTrigger className="bg-gray-50"><SelectValue placeholder="All" /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All</SelectItem>
                      <SelectItem value="pending_review">Pending Review</SelectItem>
                      <SelectItem value="approved">Approved</SelectItem>
                      <SelectItem value="rejected">Rejected</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-1 flex-1 min-w-[180px]">
                  <Label className="text-xs font-semibold text-gray-600">Search KRA</Label>
                  <Input placeholder="Search title..." value={searchKRA} onChange={e => setSearchKRA(e.target.value)} className="bg-gray-50" />
                </div>
                <div className="space-y-1">
                  <Button 
                    onClick={loadMemberKras} 
                    className="bg-indigo-600 hover:bg-indigo-700"
                    disabled={!selectedMemberId || loadingKras}
                  >
                    {loadingKras ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <RefreshCw className="w-4 h-4 mr-2" />}
                    Load
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Table */}
          <Card className="border-none shadow-sm flex-1 flex flex-col">
            <div className="overflow-x-auto flex-1">
              <Table>
                <TableHeader className="bg-gray-50">
                  <TableRow>
                    <TableHead className="cursor-pointer whitespace-nowrap text-center font-semibold text-gray-700" onClick={() => toggleSort('instance_date')}>
                      Date {sortCol === 'instance_date' && <ArrowUpDown className="inline w-3 h-3 ml-1" />}
                    </TableHead>
                    <TableHead className="cursor-pointer min-w-[200px] font-semibold text-gray-700" onClick={() => toggleSort('kra_title')}>
                      KRA Title {sortCol === 'kra_title' && <ArrowUpDown className="inline w-3 h-3 ml-1" />}
                    </TableHead>
                    <TableHead className="cursor-pointer text-center font-semibold text-gray-700" onClick={() => toggleSort('completion_status')}>
                      Status {sortCol === 'completion_status' && <ArrowUpDown className="inline w-3 h-3 ml-1" />}
                    </TableHead>
                    <TableHead className="cursor-pointer text-center font-semibold text-gray-700" onClick={() => toggleSort('manager_review_status')}>
                      Review {sortCol === 'manager_review_status' && <ArrowUpDown className="inline w-3 h-3 ml-1" />}
                    </TableHead>
                    <TableHead className="cursor-pointer text-center whitespace-nowrap font-semibold text-gray-700" onClick={() => toggleSort('time_spent_minutes')}>
                      Time {sortCol === 'time_spent_minutes' && <ArrowUpDown className="inline w-3 h-3 ml-1" />}
                    </TableHead>
                    <TableHead className="text-left font-semibold text-gray-700">Notes</TableHead>
                    <TableHead className="text-left font-semibold text-gray-700">Remarks</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {!selectedMemberId ? (
                    <TableRow>
                      <TableCell colSpan={7} className="h-48 text-center text-gray-400">
                        <Users className="w-10 h-10 mx-auto mb-3 opacity-20" />
                        <p>Select a team member to view their KRAs</p>
                      </TableCell>
                    </TableRow>
                  ) : loadingKras ? (
                    <TableRow>
                      <TableCell colSpan={7} className="h-48 text-center text-gray-400">
                        <Loader2 className="w-10 h-10 mx-auto mb-3 animate-spin opacity-50" />
                        <p>Loading KRAs...</p>
                      </TableCell>
                    </TableRow>
                  ) : paginatedKras.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={7} className="h-48 text-center text-gray-400">
                        <ListChecks className="w-10 h-10 mx-auto mb-3 opacity-20" />
                        <p>No KRAs found for selected filters</p>
                      </TableCell>
                    </TableRow>
                  ) : (
                    paginatedKras.map(k => (
                      <TableRow key={k.id} className="hover:bg-indigo-50/50">
                        <TableCell className="text-center whitespace-nowrap text-sm text-gray-600">{formatDate(k.instance_date)}</TableCell>
                        <TableCell className="font-medium text-gray-900 text-sm max-w-[200px] truncate" title={k.kra_title}>{k.kra_title}</TableCell>
                        <TableCell className="text-center">{getStatusBadge(k.completion_status, k.submitted_at)}</TableCell>
                        <TableCell className="text-center">{getReviewBadge(k.manager_review_status)}</TableCell>
                        <TableCell className="text-center text-sm text-gray-600">{k.time_spent_minutes || 0}m</TableCell>
                        <TableCell className="text-sm text-gray-500 max-w-[150px] truncate" title={k.staff_notes || ''}>{k.staff_notes || '-'}</TableCell>
                        <TableCell className="text-sm text-gray-500 max-w-[150px] truncate" title={k.manager_remarks || ''}>{k.manager_remarks || '-'}</TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </div>
            
            {/* Pagination */}
            {paginatedKras.length > 0 && (
              <div className="p-4 border-t border-gray-100 flex items-center justify-center gap-4 bg-gray-50/50">
                <Button 
                  variant="outline" 
                  size="sm"
                  onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                  disabled={currentPage <= 1}
                  className="bg-white"
                >
                  Previous
                </Button>
                <span className="text-sm text-gray-600 font-medium">
                  Page {currentPage} of {totalPages}
                </span>
                <Button 
                  variant="outline" 
                  size="sm"
                  onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                  disabled={currentPage >= totalPages}
                  className="bg-white"
                >
                  Next
                </Button>
              </div>
            )}
          </Card>
          
        </div>
      </div>
    </div>
  );
}
