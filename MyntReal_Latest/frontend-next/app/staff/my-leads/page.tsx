"use client";

import React, { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import api from '@/lib/api';
import Link from 'next/link';
import { useStaffAuth } from '@/contexts/StaffAuthContext';
import { AddLeadModal } from '@/components/AddLeadModal';
import { CRMLeadEditor } from '@/components/CRMLeadEditor';
import { WALeadModal } from '@/components/WALeadModal';
import { Card, CardContent } from '@/components/ui/card';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';

interface Lead {
  id: number;
  name: string;
  phone: string;
  email: string | null;
  status: string;
  priority: string;
  source: string;
  created_at: string;
  handler_name?: string;
  company_id?: number;
  company_name?: string;
  category?: string;
  guru_name?: string;
  z_guru_name?: string;
  core_name?: string;
}

export default function MyLeadsPage() {
  const router = useRouter();
  const { user } = useStaffAuth();
  
  const [activeTab, setActiveTab] = useState<'my_leads' | 'mnr_lookup'>('my_leads');

  // Leads state
  const [leads, setLeads] = useState<Lead[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // Stats state
  const [stats, setStats] = useState({
    my: 0,
    assigned: 0,
    fresh: 0,
    won: 0,
    team: 0,
  });
  const [isManager, setIsManager] = useState(false);
  
  // Filters for My Leads
  const [segment, setSegment] = useState<"my" | "assigned" | "fresh" | "team">("assigned");
  const [statusFilter, setStatusFilter] = useState('');
  const [priorityFilter, setPriorityFilter] = useState('');
  const [handlerTypeFilter, setHandlerTypeFilter] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalLeads, setTotalLeads] = useState(0);

  // Modals state
  const [isAddOpen, setIsAddOpen] = useState(false);
  const [editLeadId, setEditLeadId] = useState<number | null>(null);
  const [waModalData, setWaModalData] = useState<any>(null);

  // MNR Lookup state
  const [memberSearchQuery, setMemberSearchQuery] = useState('');
  const [memberSearchResults, setMemberSearchResults] = useState<any[]>([]);
  const [selectedMember, setSelectedMember] = useState<any>(null);
  const [memberSegment, setMemberSegment] = useState<'assigned'|'my'>('assigned');
  const [memberLeads, setMemberLeads] = useState<Lead[]>([]);
  const [memberLeadsLoading, setMemberLeadsLoading] = useState(false);

  const fetchStats = useCallback(async () => {
    try {
      const [rMy, rAssigned, rFresh, rWon, rTeam] = await Promise.allSettled([
        api.get('/crm/unified-my-leads?segment=my&role=mnr&page=1&per_page=1'),
        api.get('/crm/unified-my-leads?segment=assigned&role=mnr&page=1&per_page=1'),
        api.get('/crm/unified-my-leads?segment=fresh&role=mnr&page=1&per_page=1'),
        api.get('/crm/unified-my-leads?segment=my&role=mnr&status=won&page=1&per_page=1'),
        api.get('/crm/unified-my-leads?segment=team&role=mnr&page=1&per_page=1')
      ]);
      
      const getValue = (res: any) => res.status === 'fulfilled' ? (res.value.data?.total || res.value.data?.pagination?.total || 0) : 0;
      
      const teamCount = getValue(rTeam);
      if (teamCount > 0 && !isManager) {
        setIsManager(true);
        if (segment === 'assigned') setSegment('team');
      }

      setStats({
        my: getValue(rMy),
        assigned: getValue(rAssigned),
        fresh: getValue(rFresh),
        won: getValue(rWon),
        team: teamCount,
      });
    } catch(err) {
      console.error("Stats fetch error", err);
    }
  }, [isManager, segment]);

  useEffect(() => {
    fetchStats();
  }, [fetchStats]);

  useEffect(() => {
    if (activeTab === 'my_leads') {
      fetchLeads();
    }
  }, [page, segment, statusFilter, priorityFilter, handlerTypeFilter, activeTab]);

  useEffect(() => {
    const delayDebounceFn = setTimeout(() => {
      if (activeTab === 'my_leads') fetchLeads();
    }, 500);
    return () => clearTimeout(delayDebounceFn);
  }, [searchQuery, activeTab]);

  const fetchLeads = async () => {
    setLoading(true);
    setError(null);
    try {
      let url = `/crm/unified-my-leads?segment=${segment}&role=mnr&page=${page}&per_page=20`;
      if (statusFilter) url += `&status=${statusFilter}`;
      if (priorityFilter) url += `&priority=${priorityFilter}`;
      if (handlerTypeFilter) url += `&handler_type=${handlerTypeFilter}`;
      if (searchQuery) url += `&search=${encodeURIComponent(searchQuery)}`;

      const res = await api.get(url);
      if (res.data && res.data.leads) {
        setLeads(res.data.leads);
        setTotalPages(res.data.pagination?.total_pages || res.data.total_pages || 1);
        setTotalLeads(res.data.pagination?.total || res.data.total || res.data.leads.length);
      } else if (Array.isArray(res.data)) {
        setLeads(res.data);
        setTotalLeads(res.data.length);
      } else if (res.data && res.data.data) {
        setLeads(res.data.data);
        setTotalPages(res.data.pagination?.total_pages || 1);
        setTotalLeads(res.data.pagination?.total || res.data.data.length);
      }
    } catch (err: any) {
      console.error("Failed to fetch leads:", err);
      setError("Could not load leads. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleMemberSearch = async () => {
    if (!memberSearchQuery || memberSearchQuery.length < 2) return;
    try {
      const res = await api.get(`/staff/network/search?q=${encodeURIComponent(memberSearchQuery)}`);
      setMemberSearchResults(res.data?.results || []);
    } catch (e) {
      console.error("Member search failed", e);
    }
  };

  const selectMember = (member: any) => {
    setSelectedMember(member);
    setMemberSearchResults([]);
    setMemberSearchQuery('');
    fetchMemberLeads(member.id, memberSegment);
  };

  const fetchMemberLeads = async (memberId: string, seg: string) => {
    setMemberLeadsLoading(true);
    try {
      const res = await api.get(`/crm/unified-team-leads?member_id=${memberId}&segment=${seg}`);
      setMemberLeads(res.data?.leads || res.data?.data || []);
    } catch (e) {
      console.error(e);
    } finally {
      setMemberLeadsLoading(false);
    }
  };

  const getStatusBadge = (status: string) => {
    const s = (status || "").toLowerCase();
    if (s === 'new') return <span className="px-2 py-1 bg-slate-100 text-slate-700 rounded text-[10px] font-bold uppercase tracking-wider">New</span>;
    if (s === 'contacted') return <span className="px-2 py-1 bg-cyan-100 text-cyan-700 rounded text-[10px] font-bold uppercase tracking-wider">Contacted</span>;
    if (s === 'interested') return <span className="px-2 py-1 bg-blue-100 text-blue-700 rounded text-[10px] font-bold uppercase tracking-wider">Interested</span>;
    if (s === 'negotiation') return <span className="px-2 py-1 bg-amber-100 text-amber-700 rounded text-[10px] font-bold uppercase tracking-wider">Negotiation</span>;
    if (s === 'processing') return <span className="px-2 py-1 bg-purple-100 text-purple-700 rounded text-[10px] font-bold uppercase tracking-wider">Processing</span>;
    if (s === 'won' || s === 'converted') return <span className="px-2 py-1 bg-emerald-100 text-emerald-700 rounded text-[10px] font-bold uppercase tracking-wider">Won</span>;
    if (s === 'lost' || s === 'dead') return <span className="px-2 py-1 bg-rose-100 text-rose-700 rounded text-[10px] font-bold uppercase tracking-wider">Lost</span>;
    return <span className="px-2 py-1 bg-slate-100 text-slate-700 rounded text-[10px] font-bold uppercase tracking-wider">{status}</span>;
  };

  const getPriorityBadge = (priority: string) => {
    const p = (priority || "").toLowerCase();
    if (p === 'high') return <span className="px-2 py-1 bg-rose-100 text-rose-700 rounded text-[10px] font-bold uppercase tracking-wider">High</span>;
    if (p === 'medium') return <span className="px-2 py-1 bg-amber-100 text-amber-700 rounded text-[10px] font-bold uppercase tracking-wider">Medium</span>;
    if (p === 'low') return <span className="px-2 py-1 bg-emerald-100 text-emerald-700 rounded text-[10px] font-bold uppercase tracking-wider">Low</span>;
    return <span className="px-2 py-1 bg-slate-100 text-slate-700 rounded text-[10px] font-bold uppercase tracking-wider">{priority || '-'}</span>;
  };

  const renderLeadsTable = (data: Lead[], isLoading: boolean) => (
    <div className="overflow-x-auto bg-white rounded-xl border border-slate-200 shadow-sm mt-4">
      <table className="w-full text-left border-collapse">
        <thead>
          <tr className="bg-slate-50 border-b border-slate-200">
            <th className="px-4 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider">Lead</th>
            <th className="px-4 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider">Contact</th>
            <th className="px-4 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider">Category</th>
            <th className="px-4 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider">Status</th>
            <th className="px-4 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider">Handlers</th>
            <th className="px-4 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider text-right">Actions</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100 text-sm">
          {isLoading ? (
            <tr><td colSpan={6} className="text-center py-12 text-slate-500"><i className="fas fa-spinner fa-spin fa-2x mb-3 text-indigo-500 block"></i>Loading leads...</td></tr>
          ) : data.length === 0 ? (
            <tr><td colSpan={6} className="text-center py-12 text-slate-500"><div className="text-4xl mb-3">📭</div>No leads found.</td></tr>
          ) : (
            data.map(lead => (
              <tr key={lead.id} className="hover:bg-slate-50/80 transition-colors group">
                <td className="px-4 py-3">
                  <div className="font-bold text-indigo-700 group-hover:text-indigo-800 transition-colors">{lead.name}</div>
                  <div className="text-xs text-slate-500 font-medium">ID: {lead.id}</div>
                </td>
                <td className="px-4 py-3">
                  <div className="font-medium text-slate-700">{lead.phone}</div>
                  {lead.email && <div className="text-xs text-slate-500">{lead.email}</div>}
                </td>
                <td className="px-4 py-3 text-xs font-medium text-slate-600">
                  {lead.category || '-'}
                </td>
                <td className="px-4 py-3">
                  <div className="flex flex-col gap-2 items-start">
                    {getStatusBadge(lead.status)}
                    {getPriorityBadge(lead.priority)}
                  </div>
                </td>
                <td className="px-4 py-3">
                  <div className="text-[11px] text-slate-600 space-y-1">
                    {lead.guru_name && <div><span className="font-bold text-slate-700">Senior:</span> {lead.guru_name}</div>}
                    {lead.z_guru_name && <div><span className="font-bold text-slate-700">Extended:</span> {lead.z_guru_name}</div>}
                    {lead.core_name && <div><span className="font-bold text-slate-700">Core:</span> {lead.core_name}</div>}
                    {!lead.guru_name && !lead.z_guru_name && !lead.core_name && <span className="text-slate-400 italic">No specific handlers</span>}
                  </div>
                </td>
                <td className="px-4 py-3 text-right">
                  <div className="flex justify-end gap-2 opacity-80 group-hover:opacity-100 transition-opacity">
                    <button onClick={() => setWaModalData({ leadId: lead.id, phone: lead.phone, name: lead.name, companyId: lead.company_id })} className="w-8 h-8 rounded-full bg-green-50 text-green-600 hover:bg-green-100 hover:scale-110 flex items-center justify-center transition-all shadow-sm" title="WhatsApp">
                      <i className="fab fa-whatsapp"></i>
                    </button>
                    <button onClick={() => setEditLeadId(lead.id)} className="w-8 h-8 rounded-full bg-indigo-50 text-indigo-600 hover:bg-indigo-100 hover:scale-110 flex items-center justify-center transition-all shadow-sm" title="Edit">
                      <i className="fas fa-edit"></i>
                    </button>
                  </div>
                </td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );

  return (
    <div className="p-4 md:p-6 lg:p-8 max-w-[1600px] mx-auto bg-slate-50/50 min-h-screen">
      <div className="bg-gradient-to-r from-indigo-600 to-purple-700 rounded-2xl p-6 md:p-8 text-white shadow-lg mb-8 flex flex-col md:flex-row justify-between items-start md:items-center gap-4 relative overflow-hidden">
        <div className="absolute top-0 right-0 -mt-4 -mr-4 w-32 h-32 bg-white opacity-10 rounded-full blur-2xl"></div>
        <div className="relative z-10">
          <h1 className="text-3xl font-black mb-2 flex items-center"><i className="fas fa-user-friends mr-3 opacity-90"></i>My Leads</h1>
          <p className="text-indigo-100 font-medium">Manage your MNR leads and view team performance</p>
        </div>
        <div className="relative z-10 flex gap-3">
          <button onClick={() => setIsAddOpen(true)} className="px-5 py-2.5 bg-white text-indigo-700 text-sm font-bold rounded-xl shadow-sm hover:bg-indigo-50 hover:shadow transition-all flex items-center">
            <i className="fas fa-plus mr-2"></i> Add Lead
          </button>
          <Link href="/staff/dashboard" className="px-5 py-2.5 bg-indigo-800/40 border border-indigo-500/30 text-white text-sm font-bold rounded-xl hover:bg-indigo-800/60 transition-all flex items-center backdrop-blur-sm">
            <i className="fas fa-home mr-2"></i> Dashboard
          </Link>
        </div>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-slate-200 mb-8 p-1">
        <Tabs defaultValue={activeTab} onValueChange={(v) => setActiveTab(v as any)} className="w-full">
          <TabsList className="w-full justify-start h-auto p-0 bg-transparent border-b border-slate-100 rounded-none">
            <TabsTrigger value="my_leads" className="data-[state=active]:bg-transparent data-[state=active]:border-b-2 data-[state=active]:border-indigo-600 data-[state=active]:text-indigo-700 rounded-none px-6 py-4 font-bold text-slate-500">
              <i className="fas fa-user mr-2"></i> My MNR Leads
            </TabsTrigger>
            <TabsTrigger value="mnr_lookup" className="data-[state=active]:bg-transparent data-[state=active]:border-b-2 data-[state=active]:border-indigo-600 data-[state=active]:text-indigo-700 rounded-none px-6 py-4 font-bold text-slate-500">
              <i className="fas fa-search-plus mr-2"></i> MNR Member Lookup
            </TabsTrigger>
          </TabsList>
        </Tabs>
      </div>

      {activeTab === 'my_leads' && (
        <div className="animate-in fade-in slide-in-from-bottom-4 duration-500">
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-4 mb-8">
            <div className="bg-gradient-to-br from-teal-400 to-emerald-500 rounded-2xl p-5 text-white shadow-md relative overflow-hidden group">
              <div className="absolute right-0 top-0 w-24 h-24 bg-white opacity-10 rounded-bl-full transform translate-x-8 -translate-y-8 group-hover:scale-110 transition-transform"></div>
              <i className="fas fa-briefcase text-3xl opacity-80 mb-3 block"></i>
              <h3 className="text-4xl font-black mb-1 tracking-tight">{stats.my}</h3>
              <p className="text-xs font-bold uppercase tracking-widest opacity-90">Total Leads</p>
            </div>
            
            <div className="bg-gradient-to-br from-violet-500 to-purple-600 rounded-2xl p-5 text-white shadow-md relative overflow-hidden group">
              <div className="absolute right-0 top-0 w-24 h-24 bg-white opacity-10 rounded-bl-full transform translate-x-8 -translate-y-8 group-hover:scale-110 transition-transform"></div>
              <i className="fas fa-user-check text-3xl opacity-80 mb-3 block"></i>
              <h3 className="text-4xl font-black mb-1 tracking-tight">{stats.assigned}</h3>
              <p className="text-xs font-bold uppercase tracking-widest opacity-90">Assigned To Me</p>
            </div>
            
            <div className="bg-gradient-to-br from-rose-400 to-pink-500 rounded-2xl p-5 text-white shadow-md relative overflow-hidden group">
              <div className="absolute right-0 top-0 w-24 h-24 bg-white opacity-10 rounded-bl-full transform translate-x-8 -translate-y-8 group-hover:scale-110 transition-transform"></div>
              <i className="fas fa-seedling text-3xl opacity-80 mb-3 block"></i>
              <h3 className="text-4xl font-black mb-1 tracking-tight">{stats.fresh}</h3>
              <p className="text-xs font-bold uppercase tracking-widest opacity-90">Fresh Pool</p>
            </div>
            
            <div className="bg-gradient-to-br from-sky-400 to-blue-500 rounded-2xl p-5 text-white shadow-md relative overflow-hidden group">
              <div className="absolute right-0 top-0 w-24 h-24 bg-white opacity-10 rounded-bl-full transform translate-x-8 -translate-y-8 group-hover:scale-110 transition-transform"></div>
              <i className="fas fa-trophy text-3xl opacity-80 mb-3 block"></i>
              <h3 className="text-4xl font-black mb-1 tracking-tight">{stats.won}</h3>
              <p className="text-xs font-bold uppercase tracking-widest opacity-90">Won Deals</p>
            </div>
            
            {isManager && (
              <div className="bg-gradient-to-br from-amber-400 to-orange-500 rounded-2xl p-5 text-white shadow-md relative overflow-hidden group col-span-2 md:col-span-4 lg:col-span-1">
                <div className="absolute right-0 top-0 w-24 h-24 bg-white opacity-10 rounded-bl-full transform translate-x-8 -translate-y-8 group-hover:scale-110 transition-transform"></div>
                <i className="fas fa-users text-3xl opacity-80 mb-3 block"></i>
                <h3 className="text-4xl font-black mb-1 tracking-tight">{stats.team}</h3>
                <p className="text-xs font-bold uppercase tracking-widest opacity-90">Team Leads</p>
              </div>
            )}
          </div>

          <div className="bg-white rounded-xl shadow-sm border border-slate-200 mb-6 p-2">
            <div className="flex flex-wrap gap-2">
              <button onClick={() => setSegment('assigned')} className={`px-4 py-2.5 rounded-lg text-sm font-bold transition-all ${segment === 'assigned' ? 'bg-indigo-50 text-indigo-700 shadow-sm' : 'text-slate-600 hover:bg-slate-50'}`}>
                <i className="fas fa-user-check mr-2"></i> Assigned Leads
              </button>
              <button onClick={() => setSegment('my')} className={`px-4 py-2.5 rounded-lg text-sm font-bold transition-all ${segment === 'my' ? 'bg-indigo-50 text-indigo-700 shadow-sm' : 'text-slate-600 hover:bg-slate-50'}`}>
                <i className="fas fa-briefcase mr-2"></i> Direct Leads
              </button>
              <button onClick={() => setSegment('fresh')} className={`px-4 py-2.5 rounded-lg text-sm font-bold transition-all ${segment === 'fresh' ? 'bg-indigo-50 text-indigo-700 shadow-sm' : 'text-slate-600 hover:bg-slate-50'}`}>
                <i className="fas fa-seedling mr-2"></i> Fresh Leads
              </button>
              {isManager && (
                <button onClick={() => setSegment('team')} className={`px-4 py-2.5 rounded-lg text-sm font-bold transition-all flex items-center ${segment === 'team' ? 'bg-indigo-50 text-indigo-700 shadow-sm' : 'text-slate-600 hover:bg-slate-50'}`}>
                  <i className="fas fa-users mr-2"></i> Team Leads 
                  <span className="ml-2 bg-indigo-100 text-indigo-700 px-2 py-0.5 rounded-full text-[10px]">{stats.team}</span>
                </button>
              )}
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-12 gap-4 mb-4 bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
            <div className="md:col-span-4 relative">
              <i className="fas fa-search absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400"></i>
              <input type="text" placeholder="Search leads by name, phone..." value={searchQuery} onChange={e => setSearchQuery(e.target.value)} className="w-full pl-10 pr-4 py-2.5 bg-slate-50 border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none transition-all" />
            </div>
            <div className="md:col-span-2">
              <select value={statusFilter} onChange={e => {setStatusFilter(e.target.value); setPage(1);}} className="w-full px-3 py-2.5 bg-slate-50 border border-slate-200 rounded-lg text-sm font-medium focus:ring-2 focus:ring-indigo-500 outline-none cursor-pointer">
                <option value="">All Statuses</option>
                <option value="new">New</option>
                <option value="contacted">Contacted</option>
                <option value="interested">Interested</option>
                <option value="negotiation">Negotiation</option>
                <option value="processing">Processing</option>
                <option value="won">Won / Converted</option>
                <option value="lost">Lost / Dead</option>
              </select>
            </div>
            <div className="md:col-span-2">
              <select value={priorityFilter} onChange={e => {setPriorityFilter(e.target.value); setPage(1);}} className="w-full px-3 py-2.5 bg-slate-50 border border-slate-200 rounded-lg text-sm font-medium focus:ring-2 focus:ring-indigo-500 outline-none cursor-pointer">
                <option value="">All Priorities</option>
                <option value="high">High</option>
                <option value="medium">Medium</option>
                <option value="low">Low</option>
              </select>
            </div>
            <div className="md:col-span-2">
              <select value={handlerTypeFilter} onChange={e => {setHandlerTypeFilter(e.target.value); setPage(1);}} className="w-full px-3 py-2.5 bg-slate-50 border border-slate-200 rounded-lg text-sm font-medium focus:ring-2 focus:ring-indigo-500 outline-none cursor-pointer">
                <option value="">All Handlers</option>
                <option value="VGK4U">VGK4U</option>
                <option value="Walk-In">Walk-In</option>
                <option value="Showroom">Showroom</option>
                <option value="Direct">Direct</option>
              </select>
            </div>
            <div className="md:col-span-2 flex justify-end gap-2">
              <button onClick={() => { setSearchQuery(''); setStatusFilter(''); setPriorityFilter(''); setHandlerTypeFilter(''); setPage(1); }} className="px-4 py-2.5 bg-slate-100 text-slate-600 rounded-lg text-sm font-bold hover:bg-slate-200 transition-colors w-full">
                Reset
              </button>
            </div>
          </div>
          
          {renderLeadsTable(leads, loading)}
        </div>
      )}

      {activeTab === 'mnr_lookup' && (
        <div className="animate-in fade-in slide-in-from-bottom-4 duration-500">
          <div className="bg-gradient-to-br from-sky-50 to-blue-50 border border-sky-100 rounded-2xl p-6 md:p-8 mb-8 shadow-sm">
            <h2 className="text-lg font-bold text-sky-800 mb-4 flex items-center"><i className="fas fa-search-plus mr-2"></i> Search MNR Member</h2>
            <div className="max-w-2xl relative">
              <div className="flex gap-3">
                <div className="relative flex-1">
                  <i className="fas fa-user absolute left-4 top-1/2 transform -translate-y-1/2 text-sky-500"></i>
                  <input type="text" value={memberSearchQuery} onChange={e => setMemberSearchQuery(e.target.value)} onKeyDown={e => e.key === 'Enter' && handleMemberSearch()} placeholder="Type Member ID, Code, or Name..." className="w-full pl-12 pr-4 py-3 bg-white border-2 border-sky-200 rounded-xl text-sm focus:ring-0 focus:border-sky-400 outline-none transition-all shadow-sm" />
                </div>
                <button onClick={handleMemberSearch} className="px-6 py-3 bg-sky-600 text-white rounded-xl font-bold text-sm shadow-sm hover:bg-sky-700 hover:shadow transition-all whitespace-nowrap">
                  <i className="fas fa-search mr-2"></i> Search
                </button>
              </div>
              
              {memberSearchResults.length > 0 && (
                <div className="absolute top-full mt-2 left-0 right-0 bg-white shadow-xl border border-slate-100 rounded-xl z-20 max-h-80 overflow-y-auto overflow-hidden">
                  {memberSearchResults.map(m => (
                    <div key={m.id} onClick={() => selectMember(m)} className="p-4 border-b border-slate-50 hover:bg-sky-50 cursor-pointer flex justify-between items-center transition-colors group">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 bg-sky-100 text-sky-600 rounded-full flex items-center justify-center font-bold">
                          {m.name?.[0]?.toUpperCase()}
                        </div>
                        <div>
                          <div className="font-bold text-slate-800 group-hover:text-sky-700 transition-colors">{m.name}</div>
                          <div className="text-xs font-medium text-slate-500">{m.code || m.id}</div>
                        </div>
                      </div>
                      <div className="flex gap-2 items-center">
                        <span className="px-2.5 py-1 bg-slate-100 text-slate-600 rounded-lg text-[10px] font-bold tracking-wider uppercase">{m.type}</span>
                        <i className="fas fa-chevron-right text-slate-300 group-hover:text-sky-500 transition-colors"></i>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {!selectedMember && (
            <div className="text-center py-24 bg-white rounded-2xl border border-slate-200 border-dashed">
              <div className="w-20 h-20 bg-slate-50 rounded-full flex items-center justify-center mx-auto mb-4">
                <i className="fas fa-users fa-2x text-slate-300"></i>
              </div>
              <h3 className="text-lg font-bold text-slate-600 mb-1">No Member Selected</h3>
              <p className="text-slate-400 text-sm max-w-sm mx-auto">Use the search box above to find an MNR member and view their assigned and direct leads.</p>
            </div>
          )}

          {selectedMember && (
            <div className="animate-in fade-in duration-500">
              <Card className="mb-6 bg-white border-slate-200 shadow-sm overflow-hidden">
                <div className="h-2 bg-gradient-to-r from-sky-400 to-blue-500 w-full"></div>
                <CardContent className="p-6">
                  <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
                    <div className="flex items-center gap-5">
                      <div className="w-16 h-16 bg-gradient-to-br from-sky-500 to-blue-600 text-white rounded-2xl shadow-sm flex items-center justify-center font-black text-2xl">
                        {selectedMember.name?.[0]?.toUpperCase()}
                      </div>
                      <div>
                        <h3 className="font-black text-xl text-slate-800 mb-1">{selectedMember.name}</h3>
                        <div className="flex flex-wrap gap-3 items-center text-sm font-medium text-slate-500">
                          <span className="flex items-center"><i className="fas fa-id-card mr-1.5 opacity-70"></i>{selectedMember.code || selectedMember.id}</span>
                          <span className="w-1 h-1 rounded-full bg-slate-300"></span>
                          <span className="flex items-center"><i className="fas fa-phone mr-1.5 opacity-70"></i>{selectedMember.phone}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <div className="bg-white rounded-xl shadow-sm border border-slate-200 mb-6 p-2">
                <div className="flex gap-2">
                  <button onClick={() => {setMemberSegment('assigned'); fetchMemberLeads(selectedMember.id, 'assigned')}} className={`flex-1 md:flex-none px-6 py-3 rounded-lg text-sm font-bold transition-all ${memberSegment === 'assigned' ? 'bg-sky-50 text-sky-700 shadow-sm' : 'text-slate-600 hover:bg-slate-50'}`}>
                    <i className="fas fa-user-check mr-2"></i> Assigned Leads
                  </button>
                  <button onClick={() => {setMemberSegment('my'); fetchMemberLeads(selectedMember.id, 'my')}} className={`flex-1 md:flex-none px-6 py-3 rounded-lg text-sm font-bold transition-all ${memberSegment === 'my' ? 'bg-sky-50 text-sky-700 shadow-sm' : 'text-slate-600 hover:bg-slate-50'}`}>
                    <i className="fas fa-briefcase mr-2"></i> Direct Leads
                  </button>
                </div>
              </div>

              {renderLeadsTable(memberLeads, memberLeadsLoading)}
            </div>
          )}
        </div>
      )}

      {isAddOpen && <AddLeadModal isOpen={isAddOpen} onClose={() => setIsAddOpen(false)} onSave={() => { activeTab === 'my_leads' && fetchLeads(); fetchStats(); }} />}
      {editLeadId && <CRMLeadEditor isOpen={true} onClose={() => setEditLeadId(null)} leadId={editLeadId} onSave={() => { activeTab === 'my_leads' ? fetchLeads() : selectedMember && fetchMemberLeads(selectedMember.id, memberSegment); fetchStats(); }} />}
      {waModalData && <WALeadModal isOpen={true} onClose={() => setWaModalData(null)} {...waModalData} />}

    </div>
  );
}
}
