"use client";

import React, { useState, useEffect, useCallback } from "react";
import { useStaffAuth } from "@/contexts/StaffAuthContext";
import api from "@/lib/api";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Calendar, BriefcaseMedical, Star, CalendarX2, Plus, Eye, X, Loader2, Umbrella, History, AlertTriangle, Paperclip } from "lucide-react";

interface LeaveBalance {
  leave_type_id: number;
  leave_type_code: string;
  leave_type_name: string;
  available: number;
  used: number;
  pending: number;
}

interface LeaveType {
  id: number;
  name: string;
  code: string;
  requires_document: boolean;
  min_advance_days: number;
  max_consecutive_days: number | null;
  allow_half_day: boolean;
}

interface LeaveDay {
  date: string;
  is_half_day: boolean;
  half_day_type: string | null;
}

interface LeaveRequest {
  id: number;
  leave_type_name: string;
  total_days: number;
  reason: string;
  status: string;
  applied_at: string;
  can_cancel: boolean;
  days: LeaveDay[];
  approval_history?: any[];
}

export default function MyLeavesPage() {
  const { token } = useStaffAuth();
  
  const [balances, setBalances] = useState<LeaveBalance[]>([]);
  const [leaveTypes, setLeaveTypes] = useState<LeaveType[]>([]);
  const [requests, setRequests] = useState<LeaveRequest[]>([]);
  const [totalRequests, setTotalRequests] = useState(0);
  
  const [statusFilter, setStatusFilter] = useState("");
  const [yearFilter, setYearFilter] = useState("2026");
  
  const [loadingBalances, setLoadingBalances] = useState(true);
  const [loadingRequests, setLoadingRequests] = useState(true);
  
  // Apply Modal State
  const [isApplyModalOpen, setIsApplyModalOpen] = useState(false);
  const [applyForm, setApplyForm] = useState({
    leaveTypeId: "",
    reason: "",
  });
  const [selectedDates, setSelectedDates] = useState<LeaveDay[]>([]);
  const [conflictWarning, setConflictWarning] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  
  // View Details Modal
  const [viewRequest, setViewRequest] = useState<LeaveRequest | null>(null);

  const fetchBalances = useCallback(async () => {
    try {
      setLoadingBalances(true);
      const res = await api.get("/staff/leaves/my-balance");
      if (res.data.success) {
        setBalances(res.data.balances);
      }
    } catch (err) {
      console.error("Failed to fetch balances", err);
    } finally {
      setLoadingBalances(false);
    }
  }, []);

  const fetchLeaveTypes = useCallback(async () => {
    try {
      const res = await api.get("/staff/leaves/leave-types");
      if (res.data.success) {
        setLeaveTypes(res.data.leave_types);
      }
    } catch (err) {
      console.error("Failed to fetch leave types", err);
    }
  }, []);

  const fetchRequests = useCallback(async () => {
    try {
      setLoadingRequests(true);
      let url = `/staff/leaves/my-requests?year=${yearFilter}`;
      if (statusFilter) url += `&status=${statusFilter}`;
      
      const res = await api.get(url);
      if (res.data.success) {
        setRequests(res.data.requests);
        setTotalRequests(res.data.total);
      }
    } catch (err) {
      console.error("Failed to fetch requests", err);
    } finally {
      setLoadingRequests(false);
    }
  }, [statusFilter, yearFilter]);

  useEffect(() => {
    if (token) {
      fetchBalances();
      fetchLeaveTypes();
    }
  }, [token, fetchBalances, fetchLeaveTypes]);

  useEffect(() => {
    if (token) {
      fetchRequests();
    }
  }, [token, fetchRequests]);

  const getBalanceIcon = (code: string) => {
    switch (code) {
      case "casual_leave": return <Umbrella className="w-5 h-5 text-emerald-600" />;
      case "sick_leave": return <BriefcaseMedical className="w-5 h-5 text-red-600" />;
      case "approved_leave": return <Star className="w-5 h-5 text-blue-600" />;
      case "unpaid_leave": return <CalendarX2 className="w-5 h-5 text-gray-600" />;
      default: return <Calendar className="w-5 h-5 text-emerald-600" />;
    }
  };

  const getBalanceColor = (code: string) => {
    switch (code) {
      case "casual_leave": return "border-emerald-500";
      case "sick_leave": return "border-red-500";
      case "approved_leave": return "border-blue-500";
      case "unpaid_leave": return "border-gray-500";
      default: return "border-emerald-500";
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "pending_manager":
      case "pending_hr":
        return <Badge variant="outline" className="bg-amber-100 text-amber-800 border-amber-200">Pending</Badge>;
      case "approved":
        return <Badge variant="outline" className="bg-emerald-100 text-emerald-800 border-emerald-200">Approved</Badge>;
      case "rejected_manager":
      case "rejected_hr":
        return <Badge variant="outline" className="bg-red-100 text-red-800 border-red-200">Rejected</Badge>;
      case "cancelled":
        return <Badge variant="outline" className="bg-gray-100 text-gray-800 border-gray-200">Cancelled</Badge>;
      default:
        return <Badge variant="outline">{status}</Badge>;
    }
  };

  const handleAddDate = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    if (!val) return;
    if (selectedDates.find((d) => d.date === val)) {
      alert("This date is already selected");
      return;
    }
    setSelectedDates([...selectedDates, { date: val, is_half_day: false, half_day_type: null }]);
    e.target.value = "";
  };

  const handleRemoveDate = (index: number) => {
    setSelectedDates(selectedDates.filter((_, i) => i !== index));
  };

  const handleDateTypeChange = (index: number, val: string) => {
    const updated = [...selectedDates];
    if (val === "full") {
      updated[index].is_half_day = false;
      updated[index].half_day_type = null;
    } else {
      updated[index].is_half_day = true;
      updated[index].half_day_type = val;
    }
    setSelectedDates(updated);
  };

  useEffect(() => {
    const checkConflicts = async () => {
      if (!selectedDates.length) {
        setConflictWarning("");
        return;
      }
      try {
        const datesStr = selectedDates.map((d) => d.date).join(",");
        const res = await api.get(`/staff/leaves/check-conflicts?dates=${datesStr}`);
        if (res.data.success && res.data.has_any_conflict) {
          const conflictDates = res.data.conflicts.filter((c: any) => c.has_conflict).map((c: any) => c.date);
          setConflictWarning(`Attendance exists for: ${conflictDates.join(", ")}. These may be skipped or replaced.`);
        } else {
          setConflictWarning("");
        }
      } catch (err) {
        console.error("Conflict check failed", err);
      }
    };
    checkConflicts();
  }, [selectedDates]);

  const getLeaveTypeInfo = () => {
    if (!applyForm.leaveTypeId) return null;
    const lt = leaveTypes.find((l) => l.id === parseInt(applyForm.leaveTypeId));
    if (!lt) return null;
    const info = [];
    if (lt.requires_document) info.push("Document required for >2 days");
    if (lt.min_advance_days > 0) info.push(`${lt.min_advance_days} day(s) advance notice required`);
    if (lt.max_consecutive_days) info.push(`Max ${lt.max_consecutive_days} consecutive days`);
    if (lt.allow_half_day) info.push("Half-day allowed");
    return info.join(" | ");
  };

  const getAvailableBalance = () => {
    if (!applyForm.leaveTypeId) return "N/A";
    const balance = balances.find((b) => b.leave_type_id === parseInt(applyForm.leaveTypeId));
    if (balance) {
      if (balance.available <= 0) return "0 days available - LOP will be marked";
      return `${balance.available} days available`;
    }
    return "N/A";
  };

  const submitLeaveRequest = async (markAsLop = false) => {
    if (!applyForm.leaveTypeId) return alert("Please select a leave type");
    if (!selectedDates.length) return alert("Please select at least one date");
    if (applyForm.reason.trim().length < 10) return alert("Reason must be at least 10 characters");

    setIsSubmitting(true);
    const payload = {
      leave_type_id: parseInt(applyForm.leaveTypeId),
      reason: applyForm.reason.trim(),
      days: selectedDates.map((d) => ({
        leave_date: d.date,
        is_half_day: d.is_half_day,
        half_day_type: d.half_day_type,
      })),
      conflict_resolution: "skip",
      mark_as_lop: markAsLop,
    };

    try {
      const res = await api.post("/staff/leaves/apply", payload);
      if (res.data.success) {
        setIsApplyModalOpen(false);
        const lopMsg = markAsLop ? " (Marked as Loss of Pay)" : "";
        alert(`Leave request submitted successfully!${lopMsg} Request ID: #${res.data.leave_request_id}`);
        fetchBalances();
        fetchRequests();
      } else if (res.data.requires_lop_acknowledgment) {
        const confirmLop = window.confirm(
          `WARNING: Loss of Pay (LOP) will be marked!\n\nYour available balance is ${res.data.available_balance} days, but you requested ${res.data.requested_days} days.\nIf you proceed, this leave will be marked as Loss of Pay and salary deduction will apply.\n\nDo you want to continue?`
        );
        if (confirmLop) {
          submitLeaveRequest(true);
        }
      } else if (res.data.requires_conflict_resolution) {
        alert("Attendance conflicts found. Please resolve and try again.");
      } else {
        alert(res.data.detail || res.data.message || "Failed to submit leave request");
      }
    } catch (err: any) {
      console.error(err);
      alert(err.response?.data?.detail || "Failed to submit leave request.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const cancelLeaveRequest = async (id: number) => {
    if (!window.confirm("Are you sure you want to cancel this leave request?")) return;
    try {
      const res = await api.post(`/staff/leaves/cancel/${id}`);
      if (res.data.success) {
        alert("Leave request cancelled successfully");
        fetchBalances();
        fetchRequests();
      } else {
        alert(res.data.detail || "Failed to cancel leave request");
      }
    } catch (err) {
      console.error(err);
      alert("Failed to cancel leave request");
    }
  };

  const fetchViewDetails = async (id: number) => {
    try {
      const res = await api.get(`/staff/leaves/request/${id}`);
      if (res.data.success) {
        setViewRequest(res.data.request);
      }
    } catch (err) {
      console.error("Failed to fetch details", err);
      alert("Failed to load leave details");
    }
  };

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-8 animate-in fade-in duration-500">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-slate-900">My Leaves</h1>
          <p className="text-slate-500 mt-1">Manage your leave balances and requests.</p>
        </div>
        <div className="flex items-center gap-3">
          <Button 
            className="bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-700 hover:to-violet-700 text-white shadow-lg shadow-indigo-200 transition-all hover:-translate-y-0.5"
            onClick={() => {
              setApplyForm({ leaveTypeId: "", reason: "" });
              setSelectedDates([]);
              setConflictWarning("");
              setIsApplyModalOpen(true);
            }}
          >
            <Plus className="w-4 h-4 mr-2" />
            Apply for Leave
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {loadingBalances ? (
          Array.from({ length: 4 }).map((_, i) => (
            <Card key={i} className="border-l-4 border-slate-200">
              <CardContent className="p-6">
                <div className="animate-pulse flex space-x-4">
                  <div className="flex-1 space-y-4 py-1">
                    <div className="h-4 bg-slate-200 rounded w-3/4"></div>
                    <div className="h-8 bg-slate-200 rounded w-1/2"></div>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))
        ) : balances.map((b) => (
          <Card key={b.leave_type_id} className={`border-l-4 ${getBalanceColor(b.leave_type_code)} shadow-sm hover:shadow-md transition-shadow`}>
            <CardContent className="p-5">
              <div className="flex justify-between items-start mb-2">
                <h3 className="font-semibold text-slate-700">{b.leave_type_name}</h3>
                <div className="p-2 rounded-lg bg-slate-50">
                  {getBalanceIcon(b.leave_type_code)}
                </div>
              </div>
              <div className="text-3xl font-bold text-slate-900 mb-2">{b.available}</div>
              <div className="flex items-center text-xs text-slate-500 gap-4">
                <span>Used: {b.used}</span>
                <span>Pending: {b.pending}</span>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <Card className="shadow-sm border-slate-200 overflow-hidden">
        <CardHeader className="bg-slate-50 border-b border-slate-100 py-4 px-6 flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <History className="w-5 h-5 text-slate-500" />
            <CardTitle className="text-lg text-slate-800">Leave History</CardTitle>
            <Badge variant="secondary" className="ml-2 bg-white text-slate-600">{totalRequests} requests</Badge>
          </div>
          <div className="flex items-center gap-3">
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="w-[180px] bg-white">
                <SelectValue placeholder="All Status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Status</SelectItem>
                <SelectItem value="pending_manager">Pending Manager</SelectItem>
                <SelectItem value="pending_hr">Pending HR</SelectItem>
                <SelectItem value="approved">Approved</SelectItem>
                <SelectItem value="rejected_manager">Rejected (Manager)</SelectItem>
                <SelectItem value="rejected_hr">Rejected (HR)</SelectItem>
                <SelectItem value="cancelled">Cancelled</SelectItem>
              </SelectContent>
            </Select>
            <Select value={yearFilter} onValueChange={setYearFilter}>
              <SelectTrigger className="w-[120px] bg-white">
                <SelectValue placeholder="Year" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="2026">2026</SelectItem>
                <SelectItem value="2025">2025</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          <Table>
            <TableHeader className="bg-slate-50/50">
              <TableRow className="hover:bg-transparent">
                <TableHead className="font-semibold text-slate-600">ID</TableHead>
                <TableHead className="font-semibold text-slate-600">Type</TableHead>
                <TableHead className="font-semibold text-slate-600">Dates</TableHead>
                <TableHead className="font-semibold text-slate-600">Days</TableHead>
                <TableHead className="font-semibold text-slate-600">Reason</TableHead>
                <TableHead className="font-semibold text-slate-600">Status</TableHead>
                <TableHead className="font-semibold text-slate-600">Applied On</TableHead>
                <TableHead className="font-semibold text-slate-600 text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {loadingRequests ? (
                <TableRow>
                  <TableCell colSpan={8} className="h-24 text-center">
                    <Loader2 className="w-6 h-6 animate-spin text-indigo-600 mx-auto" />
                  </TableCell>
                </TableRow>
              ) : requests.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={8} className="h-32 text-center text-slate-500">
                    <div className="flex flex-col items-center justify-center gap-2">
                      <Calendar className="w-8 h-8 text-slate-300" />
                      <p>No leave requests found</p>
                    </div>
                  </TableCell>
                </TableRow>
              ) : (
                requests.map((req) => (
                  <TableRow key={req.id} className="group">
                    <TableCell className="font-medium text-slate-700">#{req.id}</TableCell>
                    <TableCell>
                      <Badge variant="outline" className="bg-slate-50 text-slate-700 border-slate-200">
                        {req.leave_type_name}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-slate-600 max-w-[200px] truncate" title={req.days.map(d => d.date).join(', ')}>
                      {req.days.map((d) => d.date).join(", ")}
                    </TableCell>
                    <TableCell className="text-slate-600">{req.total_days}</TableCell>
                    <TableCell className="max-w-[200px] truncate text-slate-600" title={req.reason}>
                      {req.reason}
                    </TableCell>
                    <TableCell>{getStatusBadge(req.status)}</TableCell>
                    <TableCell className="text-slate-600">
                      {req.applied_at ? new Date(req.applied_at).toLocaleDateString("en-IN") : "-"}
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex justify-end gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                        <Button 
                          variant="ghost" 
                          size="icon" 
                          className="h-8 w-8 text-indigo-600 hover:text-indigo-700 hover:bg-indigo-50"
                          onClick={() => {
                            fetchViewDetails(req.id);
                            setViewRequest(req); // Optimistic show
                          }}
                        >
                          <Eye className="w-4 h-4" />
                        </Button>
                        {req.can_cancel && (
                          <Button 
                            variant="ghost" 
                            size="icon" 
                            className="h-8 w-8 text-red-600 hover:text-red-700 hover:bg-red-50"
                            onClick={() => cancelLeaveRequest(req.id)}
                          >
                            <X className="w-4 h-4" />
                          </Button>
                        )}
                      </div>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Apply Leave Modal */}
      <Dialog open={isApplyModalOpen} onOpenChange={setIsApplyModalOpen}>
        <DialogContent className="sm:max-w-[600px]">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-xl">
              <CalendarMinus className="w-5 h-5 text-indigo-600" />
              Apply for Leave
            </DialogTitle>
            <DialogDescription>Submit a new leave application.</DialogDescription>
          </DialogHeader>
          <div className="space-y-6 py-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="leaveType">Leave Type</Label>
                <Select value={applyForm.leaveTypeId} onValueChange={(val) => setApplyForm({ ...applyForm, leaveTypeId: val })}>
                  <SelectTrigger id="leaveType">
                    <SelectValue placeholder="Select leave type" />
                  </SelectTrigger>
                  <SelectContent>
                    {leaveTypes.map((lt) => (
                      <SelectItem key={lt.id} value={lt.id.toString()}>{lt.name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                {getLeaveTypeInfo() && (
                  <p className="text-[11px] text-slate-500 mt-1">{getLeaveTypeInfo()}</p>
                )}
              </div>
              <div className="space-y-2">
                <Label htmlFor="availableBal">Available Balance</Label>
                <Input 
                  id="availableBal" 
                  readOnly 
                  value={getAvailableBalance()} 
                  className={`bg-slate-50 text-slate-700 ${getAvailableBalance().includes("LOP") ? "bg-amber-50 text-amber-800 border-amber-200" : ""}`}
                />
              </div>
            </div>

            <div className="space-y-3">
              <Label htmlFor="leaveDate">Select Date(s)</Label>
              <Input id="leaveDate" type="date" onChange={handleAddDate} />
              
              {selectedDates.length > 0 && (
                <div className="flex flex-wrap gap-2 mt-3 p-3 bg-slate-50 rounded-lg border border-slate-100">
                  {selectedDates.map((d, idx) => {
                    const allowHalfDay = leaveTypes.find((lt) => lt.id === parseInt(applyForm.leaveTypeId))?.allow_half_day ?? true;
                    return (
                      <Badge key={idx} variant="secondary" className="px-3 py-1.5 flex items-center gap-2 bg-indigo-50 text-indigo-700 hover:bg-indigo-100">
                        {new Date(d.date).toLocaleDateString("en-IN", { weekday: "short", month: "short", day: "numeric" })}
                        {allowHalfDay && (
                          <select 
                            className="bg-transparent text-xs font-medium border-none outline-none cursor-pointer"
                            value={d.is_half_day ? d.half_day_type || "first_half" : "full"}
                            onChange={(e) => handleDateTypeChange(idx, e.target.value)}
                          >
                            <option value="full">Full Day</option>
                            <option value="first_half">First Half</option>
                            <option value="second_half">Second Half</option>
                          </select>
                        )}
                        <X className="w-3 h-3 cursor-pointer hover:text-red-500" onClick={() => handleRemoveDate(idx)} />
                      </Badge>
                    );
                  })}
                </div>
              )}

              {conflictWarning && (
                <Alert variant="destructive" className="bg-amber-50 text-amber-800 border-amber-200">
                  <AlertTriangle className="h-4 w-4" />
                  <AlertTitle>Conflict Detected</AlertTitle>
                  <AlertDescription className="text-xs">{conflictWarning}</AlertDescription>
                </Alert>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="reason">Reason for Leave</Label>
              <Textarea 
                id="reason" 
                rows={3} 
                placeholder="Please provide a detailed reason (minimum 10 characters)"
                value={applyForm.reason}
                onChange={(e) => setApplyForm({ ...applyForm, reason: e.target.value })}
              />
              <p className="text-xs text-slate-500 text-right">{applyForm.reason.length}/500 characters</p>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsApplyModalOpen(false)}>Cancel</Button>
            <Button 
              className="bg-indigo-600 hover:bg-indigo-700 text-white" 
              onClick={() => submitLeaveRequest(false)} 
              disabled={isSubmitting}
            >
              {isSubmitting && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
              Submit Request
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* View Request Modal */}
      <Dialog open={!!viewRequest} onOpenChange={(open) => !open && setViewRequest(null)}>
        <DialogContent className="sm:max-w-[500px]">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <FileText className="w-5 h-5 text-indigo-600" />
              Leave Request Details
            </DialogTitle>
          </DialogHeader>
          {viewRequest && (
            <div className="space-y-4 py-4 text-sm text-slate-700">
              <div className="grid grid-cols-3 gap-2 py-2 border-b border-slate-100">
                <span className="font-semibold text-slate-500">Request ID</span>
                <span className="col-span-2 font-medium">#{viewRequest.id}</span>
              </div>
              <div className="grid grid-cols-3 gap-2 py-2 border-b border-slate-100">
                <span className="font-semibold text-slate-500">Leave Type</span>
                <span className="col-span-2">{viewRequest.leave_type_name}</span>
              </div>
              <div className="grid grid-cols-3 gap-2 py-2 border-b border-slate-100">
                <span className="font-semibold text-slate-500">Total Days</span>
                <span className="col-span-2">{viewRequest.total_days}</span>
              </div>
              <div className="grid grid-cols-3 gap-2 py-2 border-b border-slate-100">
                <span className="font-semibold text-slate-500">Dates</span>
                <div className="col-span-2 space-y-1">
                  {viewRequest.days.map((d, i) => (
                    <div key={i}>
                      {new Date(d.date).toLocaleDateString("en-IN")} {d.is_half_day ? `(${d.half_day_type})` : ""}
                    </div>
                  ))}
                </div>
              </div>
              <div className="grid grid-cols-3 gap-2 py-2 border-b border-slate-100">
                <span className="font-semibold text-slate-500">Reason</span>
                <span className="col-span-2">{viewRequest.reason}</span>
              </div>
              <div className="grid grid-cols-3 gap-2 py-2 border-b border-slate-100">
                <span className="font-semibold text-slate-500">Status</span>
                <span className="col-span-2">{getStatusBadge(viewRequest.status)}</span>
              </div>
              <div className="grid grid-cols-3 gap-2 py-2 border-b border-slate-100">
                <span className="font-semibold text-slate-500">Applied On</span>
                <span className="col-span-2">{new Date(viewRequest.applied_at).toLocaleString("en-IN")}</span>
              </div>
              
              {viewRequest.approval_history && viewRequest.approval_history.length > 0 && (
                <div className="mt-6">
                  <h4 className="font-semibold text-slate-900 mb-3 flex items-center gap-2">
                    <History className="w-4 h-4" /> Approval History
                  </h4>
                  <div className="space-y-3">
                    {viewRequest.approval_history.map((a: any, i: number) => (
                      <div key={i} className="pl-4 border-l-2 border-indigo-100 text-xs">
                        <div className="font-medium text-slate-800">
                          {a.stage.toUpperCase()}: <span className={a.action === "Approved" ? "text-emerald-600" : "text-slate-600"}>{a.action}</span> by {a.approved_by}
                        </div>
                        {a.remarks && <div className="text-slate-500 mt-1">"{a.remarks}"</div>}
                        <div className="text-slate-400 mt-1">{new Date(a.action_at).toLocaleString("en-IN")}</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setViewRequest(null)}>Close</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
