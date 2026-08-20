"use client";

import React, { useState, useEffect, useMemo } from 'react';
import { useStaffAuth } from '@/context/StaffAuthContext';
import { api } from '@/lib/api';
import { format, addDays, parseISO } from 'date-fns';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Badge } from '@/components/ui/badge';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { toast } from 'sonner';
import { 
  CheckCircle, 
  Clock, 
  Send, 
  Spinner, 
  ListTodo, 
  Ban, 
  FastForward,
  Edit,
  Search,
  Filter,
  Users,
  MessageCircle,
  Activity
} from 'lucide-react';

const PAGE_SIZE = 25;

export default function MyKrasPage() {
  const { user } = useStaffAuth();
  
  const [activeTab, setActiveTab] = useState("my-kras");

  // My KRAs State
  const [myKras, setMyKras] = useState([]);
  const [myDateFrom, setMyDateFrom] = useState(format(new Date(), 'yyyy-MM-dd'));
  const [myDateTo, setMyDateTo] = useState(format(addDays(new Date(), 3), 'yyyy-MM-dd'));
  const [myStatusFilter, setMyStatusFilter] = useState("all");
  const [myReviewFilter, setMyReviewFilter] = useState("all");
  const [mySearchQuery, setMySearchQuery] = useState("");
  const [myCurrentPage, setMyCurrentPage] = useState(1);
  const [mySortCol, setMySortCol] = useState("instance_date");
  const [mySortDir, setMySortDir] = useState<"asc" | "desc">("desc");
  const [isLoadingMyKras, setIsLoadingMyKras] = useState(false);

  // Modals
  const [isUpdateModalOpen, setIsUpdateModalOpen] = useState(false);
  const [isSubmitModalOpen, setIsSubmitModalOpen] = useState(false);
  const [selectedInstance, setSelectedInstance] = useState<any>(null);

  // Update Modal Form
  const [updateStatus, setUpdateStatus] = useState("pending");
  const [updatePercentage, setUpdatePercentage] = useState(0);
  const [updateTimeSpent, setUpdateTimeSpent] = useState(0);
  const [updateNotes, setUpdateNotes] = useState("");

  // Submit Modal Form
  const [submitRating, setSubmitRating] = useState("3");
  const [submitRemarks, setSubmitRemarks] = useState("");
  const [submitTimeSpent, setSubmitTimeSpent] = useState(0);

  // Team State
  const [hasTeamAccess, setHasTeamAccess] = useState(false);
  const [teamMembers, setTeamMembers] = useState([]);
  const [selectedMemberId, setSelectedMemberId] = useState<string | null>(null);
  const [teamSearchQuery, setTeamSearchQuery] = useState("");
  const [teamDeptFilter, setTeamDeptFilter] = useState("all");
  const [teamTypeFilter, setTeamTypeFilter] = useState("all");

  const [teamKras, setTeamKras] = useState([]);
  const [teamDateFrom, setTeamDateFrom] = useState(format(new Date(), 'yyyy-MM-dd'));
  const [teamDateTo, setTeamDateTo] = useState(format(addDays(new Date(), 2), 'yyyy-MM-dd'));
  const [teamStatusFilter, setTeamStatusFilter] = useState("all");
  const [teamReviewFilter, setTeamReviewFilter] = useState("all");
  const [teamKraSearch, setTeamKraSearch] = useState("");
  const [teamCurrentPage, setTeamCurrentPage] = useState(1);
  const [teamSortCol, setTeamSortCol] = useState("instance_date");
  const [teamSortDir, setTeamSortDir] = useState<"asc" | "desc">("asc");
  const [isLoadingTeamKras, setIsLoadingTeamKras] = useState(false);

  useEffect(() => {
    loadMyKras();
    checkTeamAccess();
  }, []);

  // Update dateTo automatically when dateFrom changes for My KRAs
  useEffect(() => {
    if (myDateFrom) {
      setMyDateTo(format(addDays(new Date(myDateFrom), 3), 'yyyy-MM-dd'));
    }
  }, [myDateFrom]);

  const loadMyKras = async () => {
    setIsLoadingMyKras(true);
    try {
      const res = await api.get(\`/staff/kra/my-kras?date_from=\${myDateFrom}&date_to=\${myDateTo}\`);
      setMyKras(res.kras || []);
      setMyCurrentPage(1);
    } catch (err: any) {
      toast.error(err.message || "Failed to load KRAs");
    } finally {
      setIsLoadingMyKras(false);
    }
  };

  const checkTeamAccess = async () => {
    try {
      let res = await api.get(\`/staff/kra/team-summary?scope=all&date_from=\${myDateFrom}&date_to=\${myDateTo}\`).catch(() => null);
      if (!res || !res.summary) {
        res = await api.get(\`/staff/kra/team-summary?scope=team&date_from=\${myDateFrom}&date_to=\${myDateTo}\`).catch(() => null);
      }
      if (res && res.summary) {
        setHasTeamAccess(true);
        setTeamMembers(res.summary);
      }
    } catch (err) {
      // No team access
    }
  };

  const loadTeamMemberKras = async () => {
    if (!selectedMemberId) return;
    setIsLoadingTeamKras(true);
    try {
      const res = await api.get(\`/staff/kra/instances?employee_id=\${selectedMemberId}&date_from=\${teamDateFrom}&date_to=\${teamDateTo}\`);
      setTeamKras(res.instances || []);
      setTeamCurrentPage(1);
    } catch (err: any) {
      toast.error(err.message || "Failed to load team member KRAs");
    } finally {
      setIsLoadingTeamKras(false);
    }
  };

  useEffect(() => {
    if (selectedMemberId) {
      loadTeamMemberKras();
    }
  }, [selectedMemberId]);

  // Handle Updates
  const handleOpenUpdate = (kra: any) => {
    setSelectedInstance(kra);
    setUpdateStatus(kra.completion_status || "pending");
    setUpdatePercentage(kra.completion_status === 'completed' ? 100 : (kra.completion_status === 'pending' ? 0 : 50));
    setUpdateTimeSpent(kra.time_spent_minutes || 0);
    setUpdateNotes(kra.self_remarks || kra.staff_notes || "");
    setIsUpdateModalOpen(true);
  };

  const handleSaveUpdate = async () => {
    if (updateTimeSpent < 1) {
      toast.error("Please enter at least 1 minute for time spent");
      return;
    }
    try {
      await api.put(\`/staff/kra/instances/\${selectedInstance.id}\`, {
        completion_status: updateStatus,
        completion_percentage: updatePercentage,
        time_spent_minutes: updateTimeSpent,
        time_source: 'manual',
        staff_notes: updateNotes || null
      });
      toast.success("KRA updated successfully");
      setIsUpdateModalOpen(false);
      loadMyKras();
    } catch (err: any) {
      toast.error(err.message || "Failed to update KRA");
    }
  };

  const handleOpenSubmit = (kra: any) => {
    setSelectedInstance(kra);
    setSubmitTimeSpent(kra.time_spent_minutes || 0);
    setSubmitRating("3");
    setSubmitRemarks("");
    setIsSubmitModalOpen(true);
  };

  const handleSaveSubmit = async () => {
    if (submitTimeSpent < 1) {
      toast.error("Please enter at least 1 minute for time spent");
      return;
    }
    try {
      await api.post(\`/staff/kra/my-kras/\${selectedInstance.id}/submit\`, {
        self_rating: parseInt(submitRating),
        self_remarks: submitRemarks,
        time_spent_minutes: submitTimeSpent
      });
      toast.success("Submitted for review");
      setIsSubmitModalOpen(false);
      loadMyKras();
    } catch (err: any) {
      toast.error(err.message || "Failed to submit");
    }
  };

  const openWhatsApp = (title: string, date: string, status: string) => {
    const msg = \`📊 *KRA Update*\\n\\nKRA: \${title}\\nDate: \${date}\\nStatus: \${status.replace(/_/g,' ')}\\n\\nPlease review and take action.\`;
    let ph = window.prompt("Enter WhatsApp number (e.g. 919876543210):", "91");
    if (!ph) return;
    ph = ph.replace(/\\D/g, '');
    if (ph.length >= 10) {
      window.open(\`https://wa.me/\${ph}?text=\${encodeURIComponent(msg)}\`, '_blank');
    }
  };

  // Helper functions for tables and formatting
  const getStatusBadge = (status: string, submittedAt: string) => {
    if (submittedAt) return <Badge className="bg-indigo-100 text-indigo-800 hover:bg-indigo-200">Submitted</Badge>;
    const map: any = { 
      completed: { label: 'Completed', class: 'bg-emerald-100 text-emerald-800 hover:bg-emerald-200' },
      pending: { label: 'Pending', class: 'bg-amber-100 text-amber-800 hover:bg-amber-200' },
      in_progress: { label: 'In Progress', class: 'bg-blue-100 text-blue-800 hover:bg-blue-200' },
      partial: { label: 'Partial', class: 'bg-orange-100 text-orange-800 hover:bg-orange-200' },
      skipped: { label: 'Skipped', class: 'bg-red-100 text-red-800 hover:bg-red-200' },
      na: { label: 'NA', class: 'bg-gray-100 text-gray-800 border-dashed border-2 hover:bg-gray-200' }
    };
    const c = map[status] || map['pending'];
    return <Badge className={c.class}>{c.label}</Badge>;
  };

  const getReviewBadge = (status: string) => {
    if (status === 'approved' || status === 'edited_by_manager') return <Badge className="bg-emerald-100 text-emerald-800 hover:bg-emerald-200">Approved ✓</Badge>;
    if (status === 'rejected') return <Badge className="bg-red-100 text-red-800 hover:bg-red-200">Rejected</Badge>;
    if (status === 'pending_review') return <Badge className="bg-amber-100 text-amber-800 hover:bg-amber-200">Pending Review</Badge>;
    return <Badge className="bg-amber-100 text-amber-800 hover:bg-amber-200">{status || 'Pending'}</Badge>;
  };

  const filteredMyKras = useMemo(() => {
    let filtered = [...myKras];
    if (myStatusFilter === 'submitted') {
      filtered = filtered.filter((k: any) => !!k.submitted_at);
    } else if (myStatusFilter === 'completed') {
      filtered = filtered.filter((k: any) => k.completion_status === 'completed' && !k.submitted_at);
    } else if (myStatusFilter !== 'all') {
      filtered = filtered.filter((k: any) => k.completion_status === myStatusFilter);
    }
    
    if (myReviewFilter !== 'all') {
      if (myReviewFilter === 'approved') {
        filtered = filtered.filter((k: any) => k.manager_review_status === 'approved' || k.manager_review_status === 'edited_by_manager');
      } else {
        filtered = filtered.filter((k: any) => k.manager_review_status === myReviewFilter);
      }
    }
    
    if (mySearchQuery) {
      filtered = filtered.filter((k: any) => ((k.title || k.kra_title || '')).toLowerCase().includes(mySearchQuery.toLowerCase()));
    }
    
    filtered.sort((a: any, b: any) => {
      let va = a[mySortCol], vb = b[mySortCol];
      if (mySortCol === 'instance_date') {
        const da = new Date(va || '1970-01-01').getTime();
        const db = new Date(vb || '1970-01-01').getTime();
        if (da === db) {
          return (a.completion_status === 'pending' ? 0 : 1) - (b.completion_status === 'pending' ? 0 : 1);
        }
        return mySortDir === 'asc' ? da - db : db - da;
      }
      if (typeof va === 'number' && typeof vb === 'number') return mySortDir === 'asc' ? va - vb : vb - va;
      va = (va || '').toString().toLowerCase();
      vb = (vb || '').toString().toLowerCase();
      if (va < vb) return mySortDir === 'asc' ? -1 : 1;
      if (va > vb) return mySortDir === 'asc' ? 1 : -1;
      return 0;
    });
    return filtered;
  }, [myKras, myStatusFilter, myReviewFilter, mySearchQuery, mySortCol, mySortDir]);

  const myPaginated = filteredMyKras.slice((myCurrentPage - 1) * PAGE_SIZE, myCurrentPage * PAGE_SIZE);

  const getSummaryCounts = (data: any[]) => {
    const counts = { total: 0, completed: 0, submitted: 0, pending: 0, in_progress: 0, partial: 0, skipped: 0, na: 0 };
    data.forEach(k => {
      counts.total++;
      if (k.submitted_at) counts.submitted++;
      else {
        const s = k.completion_status || 'pending';
        if ((counts as any)[s] !== undefined) (counts as any)[s]++;
      }
    });
    return counts;
  };

  const myCounts = getSummaryCounts(myKras);
  const teamCounts = getSummaryCounts(teamKras);

  return (
    <div className="p-6 max-w-7xl mx-auto flex flex-col gap-6">
      <h1 className="text-2xl font-bold tracking-tight">My KRAs</h1>

      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <TabsList>
          <TabsTrigger value="my-kras">
            <Activity className="w-4 h-4 mr-2" />
            My KRAs
          </TabsTrigger>
          {hasTeamAccess && (
            <TabsTrigger value="team">
              <Users className="w-4 h-4 mr-2" />
              Team
            </TabsTrigger>
          )}
        </TabsList>

        <TabsContent value="my-kras" className="space-y-6 mt-6">
          {/* Summary Cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-4">
             <SummaryCard title="Total" count={myCounts.total} icon={<ListTodo className="w-5 h-5" />} color="bg-indigo-50 text-indigo-600 border-indigo-200" />
             <SummaryCard title="Completed" count={myCounts.completed} icon={<CheckCircle className="w-5 h-5" />} color="bg-emerald-50 text-emerald-600 border-emerald-200" />
             <SummaryCard title="Submitted" count={myCounts.submitted} icon={<Send className="w-5 h-5" />} color="bg-blue-50 text-blue-600 border-blue-200" />
             <SummaryCard title="Pending" count={myCounts.pending} icon={<Clock className="w-5 h-5" />} color="bg-amber-50 text-amber-600 border-amber-200" />
             <SummaryCard title="In Progress" count={myCounts.in_progress} icon={<Spinner className="w-5 h-5" />} color="bg-sky-50 text-sky-600 border-sky-200" />
             <SummaryCard title="Partial" count={myCounts.partial} icon={<Activity className="w-5 h-5" />} color="bg-orange-50 text-orange-600 border-orange-200" />
             <SummaryCard title="Skipped" count={myCounts.skipped} icon={<FastForward className="w-5 h-5" />} color="bg-red-50 text-red-600 border-red-200" />
             <SummaryCard title="NA" count={myCounts.na} icon={<Ban className="w-5 h-5" />} color="bg-gray-50 text-gray-600 border-gray-200" />
          </div>

          {/* Filters */}
          <Card>
            <CardHeader className="py-4">
              <CardTitle className="text-sm font-medium flex items-center">
                <Filter className="w-4 h-4 mr-2" /> Filters
              </CardTitle>
            </CardHeader>
            <CardContent className="flex flex-wrap gap-4">
              <div className="space-y-1">
                <Label>Date From</Label>
                <Input type="date" value={myDateFrom} onChange={e => setMyDateFrom(e.target.value)} />
              </div>
              <div className="space-y-1">
                <Label>Date To <span className="text-xs text-muted-foreground">(auto +3 days)</span></Label>
                <Input type="date" value={myDateTo} readOnly className="bg-muted" />
              </div>
              <div className="space-y-1 min-w-[150px]">
                <Label>Status</Label>
                <Select value={myStatusFilter} onValueChange={setMyStatusFilter}>
                  <SelectTrigger><SelectValue placeholder="All" /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All</SelectItem>
                    <SelectItem value="pending">Pending</SelectItem>
                    <SelectItem value="completed">Completed</SelectItem>
                    <SelectItem value="submitted">Submitted</SelectItem>
                    <SelectItem value="in_progress">In Progress</SelectItem>
                    <SelectItem value="partial">Partial</SelectItem>
                    <SelectItem value="skipped">Skipped</SelectItem>
                    <SelectItem value="na">NA</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1 min-w-[150px]">
                <Label>Review Status</Label>
                <Select value={myReviewFilter} onValueChange={setMyReviewFilter}>
                  <SelectTrigger><SelectValue placeholder="All" /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All</SelectItem>
                    <SelectItem value="pending_review">Pending Review</SelectItem>
                    <SelectItem value="approved">Approved</SelectItem>
                    <SelectItem value="rejected">Rejected</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1 flex-1 min-w-[200px]">
                <Label>Search KRA</Label>
                <Input placeholder="Search KRA title..." value={mySearchQuery} onChange={e => setMySearchQuery(e.target.value)} />
              </div>
              <div className="flex items-end">
                <Button onClick={loadMyKras} disabled={isLoadingMyKras}>
                  Load
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* Table */}
          <Card>
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="cursor-pointer" onClick={() => { setMySortCol("instance_date"); setMySortDir(d => d === 'asc' ? 'desc' : 'asc') }}>
                      Date {mySortCol === 'instance_date' && (mySortDir === 'asc' ? '▲' : '▼')}
                    </TableHead>
                    <TableHead className="cursor-pointer min-w-[200px]" onClick={() => { setMySortCol("title"); setMySortDir(d => d === 'asc' ? 'desc' : 'asc') }}>
                      KRA Title {mySortCol === 'title' && (mySortDir === 'asc' ? '▲' : '▼')}
                    </TableHead>
                    <TableHead>KRA Code</TableHead>
                    <TableHead>Frequency</TableHead>
                    <TableHead>Target Time</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Completed At</TableHead>
                    <TableHead>Review Status</TableHead>
                    <TableHead>Time Spent</TableHead>
                    <TableHead>Notes</TableHead>
                    <TableHead>Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {myPaginated.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={11} className="text-center h-24 text-muted-foreground">
                        No KRAs found for selected filters
                      </TableCell>
                    </TableRow>
                  ) : myPaginated.map((k: any) => {
                    const isSubmitted = !!k.submitted_at;
                    const canSubmit = !isSubmitted && k.completion_status !== 'pending';
                    const notes = k.self_remarks || k.staff_notes || '';
                    
                    return (
                      <TableRow key={k.id}>
                        <TableCell className="whitespace-nowrap">
                          {format(new Date(k.instance_date), 'dd MMM yyyy')}
                          {k.is_late && <Badge variant="destructive" className="ml-2 text-[10px] uppercase">Overdue</Badge>}
                        </TableCell>
                        <TableCell className="font-medium max-w-[250px] truncate" title={k.title}>{k.title || '-'}</TableCell>
                        <TableCell>{k.kra_code || '-'}</TableCell>
                        <TableCell className="capitalize">{k.frequency || '-'}</TableCell>
                        <TableCell>{k.target_time || '-'}</TableCell>
                        <TableCell>{getStatusBadge(k.completion_status, k.submitted_at)}</TableCell>
                        <TableCell className="whitespace-nowrap">
                          {k.completed_at ? format(new Date(k.completed_at), 'dd MMM hh:mm a') : '-'}
                          {k.is_delayed && <Badge variant="destructive" className="ml-2 text-[10px] uppercase">Delayed</Badge>}
                        </TableCell>
                        <TableCell>{getReviewBadge(k.manager_review_status)}</TableCell>
                        <TableCell>{k.time_spent_minutes || 0} mins</TableCell>
                        <TableCell className="max-w-[150px] truncate" title={notes}>{notes}</TableCell>
                        <TableCell className="whitespace-nowrap space-x-2">
                          {!isSubmitted && (
                            <Button size="sm" variant="outline" onClick={() => handleOpenUpdate(k)}>
                              <Edit className="w-4 h-4 mr-1" /> Update
                            </Button>
                          )}
                          {canSubmit && (
                            <Button size="sm" className="bg-emerald-600 hover:bg-emerald-700 text-white" onClick={() => handleOpenSubmit(k)}>
                              <Send className="w-4 h-4 mr-1" /> Submit
                            </Button>
                          )}
                          <Button size="icon" variant="outline" className="text-green-600 border-green-600 hover:bg-green-50" onClick={() => openWhatsApp(k.title, k.instance_date, k.completion_status)}>
                            <MessageCircle className="w-4 h-4" />
                          </Button>
                        </TableCell>
                      </TableRow>
                    )
                  })}
                </TableBody>
              </Table>
            </div>
            
            {/* Pagination */}
            {filteredMyKras.length > 0 && (
              <div className="flex items-center justify-center p-4 gap-4">
                <Button variant="outline" disabled={myCurrentPage <= 1} onClick={() => setMyCurrentPage(p => p - 1)}>Prev</Button>
                <span className="text-sm text-muted-foreground">
                  Page {myCurrentPage} of {Math.ceil(filteredMyKras.length / PAGE_SIZE)}
                </span>
                <Button variant="outline" disabled={myCurrentPage >= Math.ceil(filteredMyKras.length / PAGE_SIZE)} onClick={() => setMyCurrentPage(p => p + 1)}>Next</Button>
              </div>
            )}
          </Card>
        </TabsContent>

        <TabsContent value="team" className="mt-6">
          <div className="flex flex-col lg:flex-row gap-6">
            {/* Team Sidebar */}
            <div className="w-full lg:w-1/3 xl:w-1/4 space-y-4">
              <Input 
                placeholder="Search member..." 
                value={teamSearchQuery} 
                onChange={e => setTeamSearchQuery(e.target.value)} 
              />
              <div className="flex gap-2">
                <Select value={teamDeptFilter} onValueChange={setTeamDeptFilter}>
                  <SelectTrigger><SelectValue placeholder="All Depts" /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Departments</SelectItem>
                    {Array.from(new Set(teamMembers.map((m: any) => m.department).filter(Boolean))).map((d: any) => (
                      <SelectItem key={d} value={d}>{d}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2 max-h-[600px] overflow-y-auto pr-2">
                {teamMembers.filter((m: any) => {
                  if (teamSearchQuery && !m.employee_name?.toLowerCase().includes(teamSearchQuery.toLowerCase())) return false;
                  if (teamDeptFilter !== 'all' && m.department !== teamDeptFilter) return false;
                  return true;
                }).map((m: any) => (
                  <div 
                    key={m.employee_id} 
                    className={\`p-3 border rounded-lg cursor-pointer transition-colors \${selectedMemberId === m.employee_id ? 'border-primary bg-primary/5' : 'hover:border-primary/50'}\`}
                    onClick={() => setSelectedMemberId(m.employee_id)}
                  >
                    <div className="font-semibold text-sm">{m.employee_name}</div>
                    <div className="text-xs text-muted-foreground">{m.department || '-'}</div>
                    <div className="flex justify-between text-xs mt-2">
                      <span className="text-primary font-bold">{m.performance_percentage || 0}%</span>
                      <span>Assigned: {m.assigned_kras || 0}</span>
                      <span>Done: {m.completed_kras || 0}</span>
                    </div>
                  </div>
                ))}
                {teamMembers.length === 0 && (
                  <div className="text-center py-8 text-muted-foreground text-sm">
                    No team members found
                  </div>
                )}
              </div>
            </div>

            {/* Team Content */}
            <div className="w-full lg:w-2/3 xl:w-3/4 space-y-6">
              {!selectedMemberId ? (
                <Card>
                  <CardContent className="flex flex-col items-center justify-center h-64 text-muted-foreground">
                    <Users className="w-12 h-12 mb-4 opacity-20" />
                    <p>Select a team member to view their KRAs</p>
                  </CardContent>
                </Card>
              ) : (
                <>
                  <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-4">
                     <SummaryCard title="Total" count={teamCounts.total} icon={<ListTodo className="w-4 h-4" />} color="bg-indigo-50 text-indigo-600 border-indigo-200" />
                     <SummaryCard title="Completed" count={teamCounts.completed} icon={<CheckCircle className="w-4 h-4" />} color="bg-emerald-50 text-emerald-600 border-emerald-200" />
                     <SummaryCard title="Submitted" count={teamCounts.submitted} icon={<Send className="w-4 h-4" />} color="bg-blue-50 text-blue-600 border-blue-200" />
                     <SummaryCard title="Pending" count={teamCounts.pending} icon={<Clock className="w-4 h-4" />} color="bg-amber-50 text-amber-600 border-amber-200" />
                  </div>

                  <Card>
                    <CardHeader className="py-4">
                      <CardTitle className="text-sm font-medium flex items-center">
                        <Filter className="w-4 h-4 mr-2" /> Team Member KRA Filters
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="flex flex-wrap gap-4">
                      <div className="space-y-1">
                        <Label>Date From</Label>
                        <Input type="date" value={teamDateFrom} onChange={e => setTeamDateFrom(e.target.value)} />
                      </div>
                      <div className="space-y-1">
                        <Label>Date To</Label>
                        <Input type="date" value={teamDateTo} onChange={e => setTeamDateTo(e.target.value)} />
                      </div>
                      <div className="space-y-1 min-w-[150px]">
                        <Label>Status</Label>
                        <Select value={teamStatusFilter} onValueChange={setTeamStatusFilter}>
                          <SelectTrigger><SelectValue placeholder="All" /></SelectTrigger>
                          <SelectContent>
                            <SelectItem value="all">All</SelectItem>
                            <SelectItem value="pending">Pending</SelectItem>
                            <SelectItem value="completed">Completed</SelectItem>
                            <SelectItem value="submitted">Submitted</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                      <div className="space-y-1 flex-1 min-w-[200px]">
                        <Label>Search KRA</Label>
                        <Input placeholder="Search KRA title..." value={teamKraSearch} onChange={e => setTeamKraSearch(e.target.value)} />
                      </div>
                      <div className="flex items-end">
                        <Button onClick={loadTeamMemberKras} disabled={isLoadingTeamKras}>
                          Load
                        </Button>
                      </div>
                    </CardContent>
                  </Card>

                  <Card>
                    <div className="overflow-x-auto">
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead>Date</TableHead>
                            <TableHead>KRA Title</TableHead>
                            <TableHead>Status</TableHead>
                            <TableHead>Review</TableHead>
                            <TableHead>Time Spent</TableHead>
                            <TableHead>Notes</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {teamKras.length === 0 ? (
                            <TableRow>
                              <TableCell colSpan={6} className="text-center h-24 text-muted-foreground">
                                No KRAs found
                              </TableCell>
                            </TableRow>
                          ) : teamKras.map((k: any) => (
                            <TableRow key={k.id}>
                              <TableCell>{format(new Date(k.instance_date), 'dd MMM yyyy')}</TableCell>
                              <TableCell className="max-w-[200px] truncate" title={k.title || k.kra_title}>{k.title || k.kra_title}</TableCell>
                              <TableCell>{getStatusBadge(k.completion_status, k.submitted_at)}</TableCell>
                              <TableCell>{getReviewBadge(k.manager_review_status)}</TableCell>
                              <TableCell>{k.time_spent_minutes || 0} mins</TableCell>
                              <TableCell className="max-w-[150px] truncate">{k.staff_notes || k.self_remarks || '-'}</TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </div>
                  </Card>
                </>
              )}
            </div>
          </div>
        </TabsContent>
      </Tabs>

      {/* Update Modal */}
      <Dialog open={isUpdateModalOpen} onOpenChange={setIsUpdateModalOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Update KRA Instance</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>KRA Title</Label>
              <Input value={selectedInstance?.title || ''} readOnly className="bg-muted" />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Status</Label>
                <Select value={updateStatus} onValueChange={setUpdateStatus}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="pending">Pending</SelectItem>
                    <SelectItem value="completed">Completed</SelectItem>
                    <SelectItem value="in_progress">In Progress</SelectItem>
                    <SelectItem value="partial">Partial</SelectItem>
                    <SelectItem value="skipped">Skipped</SelectItem>
                    <SelectItem value="na">NA / Exempted</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Completion %</Label>
                <Input type="number" min={0} max={100} value={updatePercentage} onChange={e => setUpdatePercentage(Number(e.target.value))} />
              </div>
            </div>
            <div className="space-y-2">
              <Label>Time Spent (minutes)</Label>
              <Input type="number" min={0} value={updateTimeSpent} onChange={e => setUpdateTimeSpent(Number(e.target.value))} />
            </div>
            <div className="space-y-2">
              <Label>Staff Notes</Label>
              <Textarea value={updateNotes} onChange={e => setUpdateNotes(e.target.value)} rows={3} />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsUpdateModalOpen(false)}>Cancel</Button>
            <Button onClick={handleSaveUpdate}>Save Update</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Submit Modal */}
      <Dialog open={isSubmitModalOpen} onOpenChange={setIsSubmitModalOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Submit for Manager Review</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>KRA Title</Label>
              <Input value={selectedInstance?.title || ''} readOnly className="bg-muted" />
            </div>
            <div className="space-y-2">
              <Label>Self Rating (1-5)</Label>
              <Select value={submitRating} onValueChange={setSubmitRating}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="1">1 - Needs Improvement</SelectItem>
                  <SelectItem value="2">2 - Below Average</SelectItem>
                  <SelectItem value="3">3 - Average</SelectItem>
                  <SelectItem value="4">4 - Good</SelectItem>
                  <SelectItem value="5">5 - Excellent</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Time Spent (minutes)</Label>
              <Input type="number" min={0} value={submitTimeSpent} onChange={e => setSubmitTimeSpent(Number(e.target.value))} />
            </div>
            <div className="space-y-2">
              <Label>Self Remarks</Label>
              <Textarea value={submitRemarks} onChange={e => setSubmitRemarks(e.target.value)} rows={3} />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsSubmitModalOpen(false)}>Cancel</Button>
            <Button onClick={handleSaveSubmit} className="bg-emerald-600 hover:bg-emerald-700 text-white">Submit KRA</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function SummaryCard({ title, count, icon, color }: { title: string, count: number, icon: React.ReactNode, color: string }) {
  return (
    <div className={\`p-4 rounded-xl border flex flex-col items-center justify-center shadow-sm \${color}\`}>
      <div className="mb-2 opacity-80">{icon}</div>
      <div className="text-2xl font-bold">{count}</div>
      <div className="text-[10px] uppercase font-semibold tracking-wider mt-1 opacity-80">{title}</div>
    </div>
  );
}
