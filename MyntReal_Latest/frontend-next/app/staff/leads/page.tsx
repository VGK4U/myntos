"use client";

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import api from '@/lib/api';
import { useStaffAuth } from '@/contexts/StaffAuthContext';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { AddLeadModal } from '@/components/AddLeadModal';
import { CRMLeadEditor } from '@/components/CRMLeadEditor';
import { WALeadModal } from '@/components/WALeadModal';
import { 
  Users, PhoneCall, UserCheck, Search, Filter, RefreshCcw, 
  DollarSign, Calendar, Clock, CheckCircle, Trophy, 
  Handshake, AlertTriangle, UserPlus, PauseCircle, Building, Edit
} from 'lucide-react';

export default function StaffLeadsPage() {
  const { user } = useStaffAuth();
  const router = useRouter();

  const [companies, setCompanies] = useState<any[]>([]);
  const [selectedCompanyId, setSelectedCompanyId] = useState<string>('');
  
  const [dashboard, setDashboard] = useState<any>(null);
  const [leads, setLeads] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [statsLoading, setStatsLoading] = useState(false);
  
  const [handlerRole, setHandlerRole] = useState('any');
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('');

  // Modals
  const [isAddOpen, setIsAddOpen] = useState(false);
  const [editLeadId, setEditLeadId] = useState<number | null>(null);
  const [waModalData, setWaModalData] = useState<any>(null);

  useEffect(() => {
    fetchCompanies();
  }, []);

  useEffect(() => {
    if (selectedCompanyId) {
      fetchDashboard();
      fetchLeads();
    } else {
      setDashboard(null);
      setLeads([]);
      setLoading(false);
    }
  }, [selectedCompanyId, handlerRole, statusFilter]);

  useEffect(() => {
    const delay = setTimeout(() => {
      if (selectedCompanyId) fetchLeads();
    }, 500);
    return () => clearTimeout(delay);
  }, [searchQuery]);

  const fetchCompanies = async () => {
    try {
      const res = await api.get('/crm/my-companies');
      if (res.data?.success && res.data.companies) {
        setCompanies(res.data.companies);
        if (res.data.companies.length > 0) {
          setSelectedCompanyId(res.data.companies[0].id.toString());
        }
      }
    } catch (err) {
      console.error('Error fetching companies:', err);
    }
  };

  const fetchDashboard = async () => {
    setStatsLoading(true);
    try {
      // Depending on the api implementation we use a simplified version, assuming stats come through if we call dashboard endpoint
      // Using scope based on handlerRole to emulate HTML behaviour
      let scope = 'all';
      if (handlerRole === 'self') scope = 'primary';
      else if (['telecaller', 'field_staff', 'mnr_handler'].includes(handlerRole)) scope = 'handler';
      
      const res = await api.get(`/crm/dashboard?company_id=${selectedCompanyId}&scope=${scope}&team_member_id=${user?.id || ''}`);
      setDashboard(res.data);
    } catch (err) {
      console.error('Error fetching dashboard:', err);
    } finally {
      setStatsLoading(false);
    }
  };

  const fetchLeads = async () => {
    setLoading(true);
    try {
      let url = `/crm/unified-my-leads?company_id=${selectedCompanyId}&page=1&per_page=50`;
      
      if (handlerRole === 'telecaller') url += '&handler_type=telecaller';
      else if (handlerRole === 'field_staff') url += '&handler_type=field_staff';
      else if (handlerRole === 'mnr_handler') url += '&handler_type=mnr_handler';
      else if (handlerRole === 'unassigned') url += '&segment=fresh';
      else if (handlerRole === 'self') url += '&segment=my';
      else url += '&segment=assigned'; // default any

      if (statusFilter) url += `&status=${statusFilter}`;
      if (searchQuery) url += `&search=${encodeURIComponent(searchQuery)}`;

      const res = await api.get(url);
      const d = res.data;
      const extracted = d?.leads ?? d?.data ?? d?.items ?? (Array.isArray(d) ? d : null);
      setLeads(Array.isArray(extracted) ? extracted : []);
    } catch (err) {
      console.error('Error fetching leads:', err);
    } finally {
      setLoading(false);
    }
  };

  const getStatusBadge = (status: string) => {
    const s = (status || "").toLowerCase();
    if (s === 'new') return <Badge className="bg-blue-100 text-blue-700 hover:bg-blue-100">New</Badge>;
    if (s === 'contacted') return <Badge className="bg-amber-100 text-amber-700 hover:bg-amber-100">Contacted</Badge>;
    if (s === 'interested') return <Badge className="bg-indigo-100 text-indigo-700 hover:bg-indigo-100">Interested</Badge>;
    if (s === 'won') return <Badge className="bg-emerald-100 text-emerald-700 hover:bg-emerald-100">Won</Badge>;
    if (s === 'lost') return <Badge className="bg-rose-100 text-rose-700 hover:bg-rose-100">Lost</Badge>;
    return <Badge className="bg-slate-100 text-slate-700 hover:bg-slate-100 uppercase">{status}</Badge>;
  };

  const StatCard = ({ title, value, icon: Icon, colorClass, bgColorClass }: any) => (
    <Card className="border-none shadow-sm flex-1 min-w-[140px] hover:shadow-md transition-shadow">
      <CardContent className="p-4 flex flex-col items-center justify-center text-center">
        <div className={`w-10 h-10 rounded-xl flex items-center justify-center mb-2 ${bgColorClass} ${colorClass}`}>
          <Icon size={20} />
        </div>
        <div className="text-2xl font-bold text-slate-800">{value || 0}</div>
        <div className="text-xs font-medium text-slate-500 mt-1">{title}</div>
      </CardContent>
    </Card>
  );

  return (
    <div className="p-4 md:p-6 lg:p-8 max-w-[1600px] mx-auto bg-slate-50/50 min-h-screen">
      {/* Header Banner */}
      <div className="bg-gradient-to-r from-sky-500 to-indigo-600 rounded-2xl p-6 mb-6 text-white shadow-lg relative overflow-hidden">
        <div className="absolute top-0 right-0 opacity-10 pointer-events-none transform translate-x-1/4 -translate-y-1/4">
          <Users size={200} />
        </div>
        <div className="relative z-10 flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
          <div>
            <h1 className="text-3xl font-black flex items-center gap-3">
              <Users className="text-white/90" size={32} />
              Staff Leads Manager
            </h1>
            <p className="text-white/80 mt-2 text-sm md:text-base font-medium">
              View and manage leads assigned to you across all roles
            </p>
          </div>
          <div className="flex items-center gap-3 bg-white/10 backdrop-blur-md p-3 rounded-xl border border-white/20">
            <Building size={18} className="text-white/80" />
            <select 
              value={selectedCompanyId} 
              onChange={e => setSelectedCompanyId(e.target.value)}
              className="bg-transparent text-white font-semibold outline-none cursor-pointer [&>option]:text-slate-800"
            >
              <option value="">Select Company</option>
              {companies.map(c => (
                <option key={c.id} value={c.id}>{c.company_name}</option>
              ))}
            </select>
          </div>
        </div>

        {/* Role Tabs */}
        <div className="flex flex-wrap gap-2 mt-6 relative z-10">
          {[
            { id: 'any', label: 'All My Leads', icon: Users },
            { id: 'telecaller', label: 'As Telecaller', icon: PhoneCall },
            { id: 'field_staff', label: 'As Field Staff', icon: UserCheck },
            { id: 'mnr_handler', label: 'As Ground Source', icon: Users },
            { id: 'unassigned', label: 'Fresh Leads', icon: UserPlus },
            { id: 'self', label: 'Self Leads', icon: UserCheck },
          ].map(role => (
            <button
              key={role.id}
              onClick={() => setHandlerRole(role.id)}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-bold transition-all ${
                handlerRole === role.id 
                  ? 'bg-white text-indigo-600 shadow-md transform scale-105' 
                  : 'bg-white/20 text-white hover:bg-white/30'
              }`}
            >
              <role.icon size={16} />
              {role.label}
            </button>
          ))}
        </div>
      </div>

      {!selectedCompanyId ? (
        <div className="text-center py-20 bg-white rounded-2xl shadow-sm border border-slate-200">
          <Building className="mx-auto text-slate-300 mb-4" size={64} />
          <h3 className="text-xl font-bold text-slate-700">No Company Selected</h3>
          <p className="text-slate-500 mt-2">Please select a company from the top right to view leads.</p>
        </div>
      ) : (
        <>
          {/* Stats Dashboard */}
          <div className="flex flex-wrap gap-4 mb-8">
            <StatCard title="Total Leads" value={dashboard?.total_leads} icon={Users} bgColorClass="bg-blue-100" colorClass="text-blue-600" />
            <StatCard title="New" value={dashboard?.status_counts?.new} icon={UserPlus} bgColorClass="bg-cyan-100" colorClass="text-cyan-600" />
            <StatCard title="In Progress" value={dashboard?.status_counts?.contacted} icon={Handshake} bgColorClass="bg-purple-100" colorClass="text-purple-600" />
            <StatCard title="Won" value={dashboard?.status_counts?.won} icon={Trophy} bgColorClass="bg-emerald-100" colorClass="text-emerald-600" />
            <StatCard title="Lost" value={dashboard?.status_counts?.lost} icon={AlertTriangle} bgColorClass="bg-rose-100" colorClass="text-rose-600" />
            <StatCard title="On Hold" value={dashboard?.status_counts?.on_hold} icon={PauseCircle} bgColorClass="bg-amber-100" colorClass="text-amber-600" />
          </div>

          {/* Leads Table Section */}
          <Card className="border-none shadow-sm rounded-2xl overflow-hidden">
            <CardHeader className="bg-white border-b border-slate-100 px-6 py-4 flex flex-col md:flex-row md:items-center justify-between gap-4">
              <CardTitle className="text-xl font-bold text-slate-800 flex items-center gap-2">
                <Users className="text-indigo-500" /> 
                Leads Directory
              </CardTitle>
              <div className="flex items-center gap-3">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={16} />
                  <Input 
                    placeholder="Search name, phone..." 
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="pl-9 bg-slate-50 border-slate-200 focus-visible:ring-indigo-500 w-[200px]"
                  />
                </div>
                <select 
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value)}
                  className="h-10 px-3 rounded-md bg-slate-50 border border-slate-200 text-sm font-medium outline-none focus:ring-2 focus:ring-indigo-500"
                >
                  <option value="">All Status</option>
                  <option value="new">New</option>
                  <option value="contacted">Contacted</option>
                  <option value="interested">Interested</option>
                  <option value="won">Won</option>
                  <option value="lost">Lost</option>
                </select>
                <Button onClick={() => setIsAddOpen(true)} className="bg-indigo-600 hover:bg-indigo-700 text-white font-semibold">
                  <UserPlus size={16} className="mr-2" /> Add Lead
                </Button>
              </div>
            </CardHeader>
            <CardContent className="p-0">
              {loading ? (
                <div className="py-20 flex flex-col items-center justify-center text-slate-400">
                  <RefreshCcw className="animate-spin mb-4 text-indigo-500" size={32} />
                  <p className="font-medium text-slate-600">Loading leads...</p>
                </div>
              ) : leads.length === 0 ? (
                <div className="py-20 flex flex-col items-center justify-center text-slate-400">
                  <Users size={48} className="mb-4 opacity-50" />
                  <h3 className="text-lg font-bold text-slate-600">No leads found</h3>
                  <p className="text-sm">Try adjusting your filters or add a new lead.</p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader className="bg-slate-50">
                      <TableRow>
                        <TableHead className="font-bold text-slate-500 py-4">Lead Info</TableHead>
                        <TableHead className="font-bold text-slate-500 py-4">Contact</TableHead>
                        <TableHead className="font-bold text-slate-500 py-4">Status & Priority</TableHead>
                        <TableHead className="font-bold text-slate-500 py-4">Dates</TableHead>
                        <TableHead className="text-right font-bold text-slate-500 py-4">Actions</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {leads.map((lead: any) => (
                        <TableRow key={lead.id} className="hover:bg-indigo-50/30 transition-colors cursor-pointer" onClick={() => setEditLeadId(lead.id)}>
                          <TableCell className="py-4">
                            <div className="font-bold text-slate-800">{lead.name}</div>
                            <div className="text-xs text-slate-500 mt-1 flex items-center gap-1">
                              ID: {lead.id} {lead.category && `• ${lead.category}`}
                            </div>
                          </TableCell>
                          <TableCell className="py-4">
                            <div className="flex items-center gap-2 text-sm font-medium text-slate-700">
                              <Phone size={14} className="text-slate-400" /> {lead.phone || '-'}
                            </div>
                            {lead.email && (
                              <div className="flex items-center gap-2 text-xs text-slate-500 mt-1">
                                <Mail size={12} className="text-slate-400" /> {lead.email}
                              </div>
                            )}
                          </TableCell>
                          <TableCell className="py-4">
                            <div className="flex flex-col gap-2 items-start">
                              {getStatusBadge(lead.status)}
                              <span className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-sm ${
                                lead.priority === 'high' ? 'bg-orange-100 text-orange-700' :
                                lead.priority === 'medium' ? 'bg-blue-50 text-blue-600' : 'bg-slate-100 text-slate-600'
                              }`}>
                                {lead.priority || 'Normal'}
                              </span>
                            </div>
                          </TableCell>
                          <TableCell className="py-4">
                            <div className="text-xs text-slate-600 flex flex-col gap-1">
                              <div><span className="font-semibold">Created:</span> {new Date(lead.created_at).toLocaleDateString()}</div>
                              {lead.next_followup_date && (
                                <div><span className="font-semibold text-indigo-600">Followup:</span> {new Date(lead.next_followup_date).toLocaleDateString()}</div>
                              )}
                            </div>
                          </TableCell>
                          <TableCell className="py-4 text-right">
                            <div className="flex justify-end gap-2" onClick={(e) => e.stopPropagation()}>
                              <Button 
                                variant="outline" 
                                size="icon"
                                className="h-8 w-8 text-green-600 border-green-200 hover:bg-green-50 hover:text-green-700"
                                onClick={() => setWaModalData({ leadId: lead.id, phone: lead.phone, name: lead.name, companyId: lead.company_id })}
                              >
                                <PhoneCall size={14} />
                              </Button>
                              <Button 
                                variant="outline" 
                                size="icon"
                                className="h-8 w-8 text-indigo-600 border-indigo-200 hover:bg-indigo-50 hover:text-indigo-700"
                                onClick={() => setEditLeadId(lead.id)}
                              >
                                <Edit size={14} />
                              </Button>
                            </div>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              )}
            </CardContent>
          </Card>
        </>
      )}

      {/* Modals */}
      {isAddOpen && (
        <AddLeadModal 
          isOpen={isAddOpen} 
          onClose={() => setIsAddOpen(false)} 
          onSave={() => { fetchLeads(); fetchDashboard(); }} 
        />
      )}
      
      {editLeadId && (
        <CRMLeadEditor 
          isOpen={true} 
          onClose={() => setEditLeadId(null)} 
          leadId={editLeadId} 
          onSave={() => { fetchLeads(); fetchDashboard(); }} 
        />
      )}
      
      {waModalData && (
        <WALeadModal 
          isOpen={true} 
          onClose={() => setWaModalData(null)} 
          {...waModalData} 
        />
      )}
    </div>
  );
}
