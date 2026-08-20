"use client";
import React, { useState, useEffect, useCallback } from "react";
import api from "@/lib/api";
import { useStaffAuth } from "@/contexts/StaffAuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Search, RefreshCw, Phone, User, Clock, ChevronLeft, ChevronRight, Loader2, AlertCircle, Eye } from "lucide-react";
import Link from "next/link";

interface Lead { id: number; name?: string; phone?: string; status?: string; priority?: string; category_name?: string; owner_name?: string; next_followup_date?: string; }
const SC: Record<string,string> = { new:"bg-blue-100 text-blue-800", contacted:"bg-cyan-100 text-cyan-800", interested:"bg-green-100 text-green-800", not_interested:"bg-red-100 text-red-800", follow_up:"bg-yellow-100 text-yellow-800", closed_won:"bg-emerald-100 text-emerald-800", closed_lost:"bg-gray-100 text-gray-700" };
const PC: Record<string,string> = { high:"bg-red-100 text-red-700", medium:"bg-yellow-100 text-yellow-700", low:"bg-gray-100 text-gray-600" };

export default function Page() {
  const { token } = useStaffAuth();
  const [leads, setLeads] = useState<Lead[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [page, setPage] = useState(1);
  const [totalCount, setTotalCount] = useState(0);
  const perPage = 20;

  const fetchLeads = useCallback(async () => {
    if (!token) return;
    setLoading(true); setError("");
    try {
      const params = new URLSearchParams();
      if (search) params.set("search", search);
      if (statusFilter) params.set("status", statusFilter);
      params.set("page", String(page));
      params.set("per_page", String(perPage));
      
      
      const res = await api.get(`/crm/master-leads?${params.toString()}`);
      const data = res.data;
      setLeads(data?.leads || data?.data || data?.items || (Array.isArray(data) ? data : []));
      setTotalCount(data?.total || data?.count || 0);
    } catch (err: any) { setError(err?.response?.data?.detail || "Failed to load leads"); }
    finally { setLoading(false); }
  }, [token, search, statusFilter, page]);

  useEffect(() => { fetchLeads(); }, [fetchLeads]);

  const totalPages = Math.max(1, Math.ceil(totalCount / perPage));
  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">MNR Leads</h1>
          <p className="text-gray-500 mt-1">MNR master leads overview</p>
        </div>
        <Button onClick={fetchLeads} variant="outline" size="sm"><RefreshCw className="w-4 h-4 mr-2" />Refresh</Button>
      </div>
      <Card><CardContent className="pt-4"><div className="flex flex-wrap gap-3">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <Input className="pl-9" placeholder="Search..." value={search} onChange={(e) => { setSearch(e.target.value); setPage(1); }} />
        </div>
        <Select value={statusFilter || "all"} onValueChange={(v) => { setStatusFilter(v === "all" ? "" : v); setPage(1); }}>
          <SelectTrigger className="w-[160px]"><SelectValue placeholder="All Statuses" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Statuses</SelectItem>
            <SelectItem value="new">New</SelectItem><SelectItem value="contacted">Contacted</SelectItem>
            <SelectItem value="interested">Interested</SelectItem><SelectItem value="follow_up">Follow Up</SelectItem>
            <SelectItem value="closed_won">Closed Won</SelectItem><SelectItem value="closed_lost">Closed Lost</SelectItem>
          </SelectContent>
        </Select>
      </div></CardContent></Card>
      {error && <div className="flex items-center gap-2 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700"><AlertCircle className="w-5 h-5" />{error}</div>}
      <Card>
        <CardHeader><CardTitle>{loading ? "Loading..." : \ Leads}</CardTitle></CardHeader>
        <CardContent className="p-0">
          {loading ? (<div className="flex items-center justify-center py-16"><Loader2 className="w-8 h-8 animate-spin text-blue-600" /><span className="ml-3 text-gray-500">Loading...</span></div>)
          : leads.length === 0 ? (<div className="flex flex-col items-center justify-center py-16 text-gray-400"><p className="font-medium">No leads found</p></div>)
          : (<div className="overflow-x-auto"><table className="w-full text-sm">
            <thead className="bg-gray-50 border-b"><tr>
              <th className="text-left px-4 py-3 font-semibold text-gray-600">Lead</th>
              <th className="text-left px-4 py-3 font-semibold text-gray-600">Status</th>
              <th className="text-left px-4 py-3 font-semibold text-gray-600">Priority</th>
              <th className="text-left px-4 py-3 font-semibold text-gray-600">Category</th>
              <th className="text-left px-4 py-3 font-semibold text-gray-600">Owner</th>
              <th className="text-left px-4 py-3 font-semibold text-gray-600">Follow-up</th>
              <th className="text-left px-4 py-3 font-semibold text-gray-600">Actions</th>
            </tr></thead>
            <tbody className="divide-y divide-gray-100">
              {leads.map((lead, idx) => (<tr key={lead.id || idx} className="hover:bg-gray-50 transition-colors">
                <td className="px-4 py-3"><div className="flex items-center gap-2"><User className="w-4 h-4 text-gray-400 flex-shrink-0" /><div><p className="font-medium text-gray-900">{lead.name || "—"}</p><p className="text-xs text-gray-500 flex items-center gap-1"><Phone className="w-3 h-3" />{lead.phone || "—"}</p></div></div></td>
                <td className="px-4 py-3"><span className={px-2 py-1 rounded-full text-xs font-semibold \}>{(lead.status || "—").replace(/_/g," ")}</span></td>
                <td className="px-4 py-3"><span className={px-2 py-1 rounded-full text-xs font-semibold \}>{lead.priority || "—"}</span></td>
                <td className="px-4 py-3 text-gray-600 text-xs">{lead.category_name || "—"}</td>
                <td className="px-4 py-3 text-gray-600 text-xs">{lead.owner_name || "—"}</td>
                <td className="px-4 py-3">{lead.next_followup_date ? (<div className="flex items-center gap-1 text-xs text-gray-500"><Clock className="w-3 h-3" />{new Date(lead.next_followup_date).toLocaleDateString("en-IN")}</div>) : "—"}</td>
                <td className="px-4 py-3"><Link href={/staff/crm/leads/\}><Button size="sm" variant="ghost" className="h-7 px-2 text-xs"><Eye className="w-3 h-3 mr-1" />View</Button></Link></td>
              </tr>))}
            </tbody>
          </table></div>)}
        </CardContent>
      </Card>
      {totalCount > perPage && (<div className="flex items-center justify-between">
        <p className="text-sm text-gray-500">Showing {((page-1)*perPage)+1}–{Math.min(page*perPage,totalCount)} of {totalCount}</p>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" disabled={page<=1} onClick={() => setPage(p=>p-1)}><ChevronLeft className="w-4 h-4" /></Button>
          <span className="px-3 py-2 text-sm font-medium">{page}/{totalPages}</span>
          <Button variant="outline" size="sm" disabled={page>=totalPages} onClick={() => setPage(p=>p+1)}><ChevronRight className="w-4 h-4" /></Button>
        </div>
      </div>)}
    </div>
  );
}

