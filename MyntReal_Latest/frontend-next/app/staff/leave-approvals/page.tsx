"use client";

import React, { useState, useEffect, useCallback } from 'react';
import api from '@/lib/api';
import { useStaffAuth } from '@/contexts/StaffAuthContext';
import { Button } from '@/components/ui/button';
import { 
  Users, UserCheck, Clock, Check, X, AlertCircle, FileText, Calendar
} from 'lucide-react';

interface LeaveRequestDay {
  date: string;
  is_half_day: boolean;
  half_day_type: string | null;
}

interface LeaveRequest {
  id: number;
  employee_id: number;
  employee_name: string;
  employee_code: string;
  department?: string;
  leave_type_id: number;
  leave_type_name: string;
  reason: string;
  total_days: number;
  applied_at: string;
  manager_approved_at?: string;
  manager_remarks?: string;
  is_skip_level?: boolean;
  days: LeaveRequestDay[];
}

export default function LeaveApprovalsPage() {
  const { user } = useStaffAuth();
  
  const [activeTab, setActiveTab] = useState<'manager' | 'hr'>('manager');
  const [requests, setRequests] = useState<LeaveRequest[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [hrCount, setHrCount] = useState(0);
  const [managerCount, setManagerCount] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const [modalOpen, setModalOpen] = useState(false);
  const [selectedRequest, setSelectedRequest] = useState<LeaveRequest | null>(null);
  const [actionType, setActionType] = useState<'approve' | 'reject'>('approve');
  const [remarks, setRemarks] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const roleCode = user?.role?.role_code || user?.role_code || '';
  const isHR = ['hr', 'ea', 'vgk4u'].includes(roleCode.toLowerCase());

  const fetchQueue = useCallback(async (tab: 'manager' | 'hr') => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await api.get(`/staff/leaves/pending-approvals/${tab}`);
      if (response.data.success) {
        setRequests(response.data.requests);
        if (tab === 'manager') setManagerCount(response.data.total);
        if (tab === 'hr') setHrCount(response.data.total);
      } else {
        setError(response.data.detail || 'Failed to load requests');
        setRequests([]);
      }
    } catch (err: any) {
      if (err.response?.status === 403) {
        setError("You do not have access to this queue.");
      } else {
        setError('An error occurred while fetching requests.');
      }
      setRequests([]);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const fetchCounts = useCallback(async () => {
    try {
      const mgrRes = await api.get('/staff/leaves/pending-approvals/manager');
      if (mgrRes.data.success) setManagerCount(mgrRes.data.total);
      
      if (isHR) {
        const hrRes = await api.get('/staff/leaves/pending-approvals/hr');
        if (hrRes.data.success) setHrCount(hrRes.data.total);
      }
    } catch (e) {
      // Silently fail for background counts
    }
  }, [isHR]);

  useEffect(() => {
    if (user) {
      fetchQueue(activeTab);
      fetchCounts();
    }
  }, [user, activeTab, fetchQueue, fetchCounts]);

  const handleActionClick = (request: LeaveRequest, action: 'approve' | 'reject') => {
    setSelectedRequest(request);
    setActionType(action);
    setRemarks('');
    setModalOpen(true);
  };

  const submitAction = async () => {
    if (!selectedRequest) return;
    if (actionType === 'reject' && !remarks.trim()) {
      alert("Remarks are required when rejecting.");
      return;
    }

    setIsSubmitting(true);
    try {
      const response = await api.post(`/staff/leaves/approve/${activeTab}/${selectedRequest.id}`, {
        action: actionType,
        remarks: remarks.trim() || null
      });

      if (response.data.success) {
        setModalOpen(false);
        fetchQueue(activeTab);
        fetchCounts();
      } else {
        alert(response.data.detail || 'Action failed');
      }
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to process action. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const getLeaveTypeColor = (typeName: string) => {
    const name = typeName.toLowerCase();
    if (name.includes('casual')) return 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400';
    if (name.includes('sick')) return 'bg-rose-100 text-rose-700 dark:bg-rose-900/30 dark:text-rose-400';
    if (name.includes('privilege')) return 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400';
    return 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300';
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('en-IN', { month: 'short', day: 'numeric', year: 'numeric' });
  };

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Leave Approvals</h1>
          <p className="text-muted-foreground">Manage and review employee leave requests</p>
        </div>
        <Button variant="outline" onClick={() => fetchQueue(activeTab)} disabled={isLoading}>
          <Clock className="w-4 h-4 mr-2" />
          Refresh
        </Button>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 p-1 bg-muted/50 rounded-lg w-fit">
        <button
          onClick={() => setActiveTab('manager')}
          className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-colors ${
            activeTab === 'manager' 
              ? 'bg-background shadow-sm text-foreground' 
              : 'text-muted-foreground hover:text-foreground hover:bg-background/50'
          }`}
        >
          <Users className="w-4 h-4" />
          Manager Queue
          <span className={`ml-1.5 py-0.5 px-2 rounded-full text-xs ${
            activeTab === 'manager' ? 'bg-primary/10 text-primary' : 'bg-muted-foreground/20'
          }`}>
            {managerCount}
          </span>
        </button>
        {isHR && (
          <button
            onClick={() => setActiveTab('hr')}
            className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-colors ${
              activeTab === 'hr' 
                ? 'bg-background shadow-sm text-foreground' 
                : 'text-muted-foreground hover:text-foreground hover:bg-background/50'
            }`}
          >
            <UserCheck className="w-4 h-4" />
            HR Queue
            <span className={`ml-1.5 py-0.5 px-2 rounded-full text-xs ${
              activeTab === 'hr' ? 'bg-primary/10 text-primary' : 'bg-muted-foreground/20'
            }`}>
              {hrCount}
            </span>
          </button>
        )}
      </div>

      {/* Stats Row */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-card border rounded-xl p-6 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-muted-foreground">Pending in Queue</p>
            <h3 className="text-3xl font-bold mt-1">{activeTab === 'manager' ? managerCount : hrCount}</h3>
          </div>
          <div className="w-12 h-12 bg-amber-100 text-amber-600 dark:bg-amber-900/30 dark:text-amber-500 rounded-full flex items-center justify-center">
            <Clock className="w-6 h-6" />
          </div>
        </div>
      </div>

      {/* Requests List */}
      <div className="bg-card border rounded-xl shadow-sm overflow-hidden">
        <div className="border-b px-6 py-4">
          <h2 className="font-semibold flex items-center gap-2">
            <FileText className="w-4 h-4 text-muted-foreground" />
            Pending Requests
          </h2>
        </div>
        
        <div className="p-6">
          {isLoading ? (
            <div className="flex justify-center items-center py-12">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
            </div>
          ) : error ? (
            <div className="text-center py-12 text-muted-foreground flex flex-col items-center">
              <AlertCircle className="w-10 h-10 mb-3 text-red-400" />
              <p>{error}</p>
            </div>
          ) : requests.length === 0 ? (
            <div className="text-center py-16 text-muted-foreground flex flex-col items-center">
              <Check className="w-12 h-12 mb-4 text-emerald-400 opacity-50" />
              <h3 className="text-lg font-medium text-foreground mb-1">All caught up!</h3>
              <p>No pending leave requests in the {activeTab === 'manager' ? 'manager' : 'HR'} queue.</p>
            </div>
          ) : (
            <div className="space-y-4">
              {requests.map(req => (
                <div key={req.id} className="border rounded-lg p-5 hover:shadow-md transition-shadow bg-background">
                  <div className="flex flex-col md:flex-row md:items-start justify-between gap-4 mb-4">
                    <div className="flex items-center gap-3">
                      <div className="w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center text-primary font-bold text-lg">
                        {req.employee_name.split(' ').map(n => n[0]).join('').substring(0,2).toUpperCase()}
                      </div>
                      <div>
                        <h4 className="font-semibold text-foreground text-lg">{req.employee_name}</h4>
                        <div className="text-sm text-muted-foreground flex items-center gap-2">
                          <span>{req.employee_code}</span>
                          {req.department && (
                            <>
                              <span className="w-1 h-1 rounded-full bg-muted-foreground/50"></span>
                              <span>{req.department}</span>
                            </>
                          )}
                        </div>
                      </div>
                    </div>
                    <span className={`px-3 py-1 rounded-full text-xs font-medium border ${getLeaveTypeColor(req.leave_type_name)}`}>
                      {req.leave_type_name}
                    </span>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-4">
                    <div className="space-y-4">
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <p className="text-xs text-muted-foreground uppercase tracking-wider mb-1">Total Days</p>
                          <p className="font-medium">{req.total_days}</p>
                        </div>
                        <div>
                          <p className="text-xs text-muted-foreground uppercase tracking-wider mb-1">Applied On</p>
                          <p className="font-medium">{req.applied_at ? formatDate(req.applied_at) : '-'}</p>
                        </div>
                      </div>

                      {activeTab === 'hr' && req.manager_approved_at && (
                        <div>
                          <p className="text-xs text-muted-foreground uppercase tracking-wider mb-1">Manager Approved</p>
                          <p className="font-medium">{formatDate(req.manager_approved_at)}</p>
                        </div>
                      )}

                      <div>
                        <p className="text-xs text-muted-foreground uppercase tracking-wider mb-2">Leave Dates</p>
                        <div className="flex flex-wrap gap-2">
                          {req.days.map((d, i) => (
                            <span key={i} className={`inline-flex items-center px-2.5 py-0.5 rounded text-xs font-medium ${
                              d.is_half_day ? 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400' : 'bg-primary/10 text-primary'
                            }`}>
                              <Calendar className="w-3 h-3 mr-1.5" />
                              {formatDate(d.date)} {d.is_half_day && `(${d.half_day_type === 'first_half' ? 'First Half' : 'Second Half'})`}
                            </span>
                          ))}
                        </div>
                      </div>
                    </div>

                    <div className="space-y-4">
                      <div className="bg-muted/30 p-4 rounded-lg">
                        <p className="text-xs text-muted-foreground uppercase tracking-wider mb-1">Reason</p>
                        <p className="text-sm whitespace-pre-wrap">{req.reason}</p>
                      </div>

                      {activeTab === 'hr' && req.manager_remarks && (
                        <div className="bg-muted/30 p-4 rounded-lg">
                          <p className="text-xs text-muted-foreground uppercase tracking-wider mb-1">Manager Remarks</p>
                          <p className="text-sm whitespace-pre-wrap">{req.manager_remarks}</p>
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="flex gap-3 justify-end border-t pt-4 mt-2">
                    <Button 
                      variant="outline" 
                      className="text-red-600 hover:text-red-700 hover:bg-red-50 dark:hover:bg-red-950/30 border-red-200"
                      onClick={() => handleActionClick(req, 'reject')}
                    >
                      <X className="w-4 h-4 mr-1.5" />
                      Reject
                    </Button>
                    <Button 
                      className="bg-emerald-600 hover:bg-emerald-700 text-white"
                      onClick={() => handleActionClick(req, 'approve')}
                    >
                      <Check className="w-4 h-4 mr-1.5" />
                      Approve
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Approval Modal */}
      {modalOpen && selectedRequest && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4 animate-in fade-in duration-200">
          <div className="bg-background border shadow-xl rounded-xl w-full max-w-lg overflow-hidden animate-in zoom-in-95 duration-200">
            <div className="px-6 py-4 border-b flex justify-between items-center bg-muted/20">
              <h3 className="text-lg font-semibold flex items-center gap-2">
                {actionType === 'approve' ? (
                  <><Check className="w-5 h-5 text-emerald-500" /> Approve Leave</>
                ) : (
                  <><X className="w-5 h-5 text-red-500" /> Reject Leave</>
                )}
              </h3>
              <button 
                onClick={() => setModalOpen(false)}
                className="text-muted-foreground hover:bg-muted p-1.5 rounded-full transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
            
            <div className="p-6 space-y-4">
              <p className="text-sm text-foreground">
                You are about to <strong className={actionType === 'approve' ? 'text-emerald-600' : 'text-red-600'}>
                  {actionType}
                </strong> the leave request for <strong>{selectedRequest.employee_name}</strong>.
              </p>
              
              <div className="space-y-2">
                <label className="text-sm font-medium">
                  Remarks {actionType === 'approve' ? '(Optional)' : '(Required)'}
                </label>
                <textarea 
                  className="w-full min-h-[100px] p-3 rounded-md border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
                  placeholder="Enter your remarks here..."
                  value={remarks}
                  onChange={(e) => setRemarks(e.target.value)}
                />
              </div>
            </div>
            
            <div className="px-6 py-4 border-t bg-muted/20 flex justify-end gap-3">
              <Button variant="outline" onClick={() => setModalOpen(false)} disabled={isSubmitting}>
                Cancel
              </Button>
              <Button 
                onClick={submitAction} 
                disabled={isSubmitting}
                className={actionType === 'approve' ? 'bg-emerald-600 hover:bg-emerald-700 text-white' : 'bg-red-600 hover:bg-red-700 text-white'}
              >
                {isSubmitting ? 'Processing...' : `Confirm ${actionType}`}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
