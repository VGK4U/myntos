"use client";

import React, { useState, useEffect, useCallback } from "react";
import api from "@/lib/api";
import { useStaffAuth } from "@/contexts/StaffAuthContext";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import {
  Landmark, Search, RefreshCw, Phone, User, Calendar, Building2,
  ChevronLeft, ChevronRight, Loader2, AlertCircle, TrendingUp,
} from "lucide-react";

interface Lead {
  id: number;
  customer_name?: string;
  name?: string;
  phone?: string;
  district?: string;
  bank_name?: string;
  stage?: string;
  stage_days?: number;
  bucket?: string;
  deal_value?: number;
  ground_source?: string;
  telecaller?: string;
  handler?: string;
  company_name?: string;
}

const STAGE_COLORS: Record<string, string> = {
  pending_with_bank: "bg-yellow-100 text-yellow-800",
  balance_pending: "bg-orange-100 text-orange-800",
  approved: "bg-green-100 text-green-800",
  rejected: "bg-red-100 text-red-800",
  disbursed: "bg-blue-100 text-blue-800",
  closed: "bg-gray-100 text-gray-700",
};

const BUCKET_LABELS: Record<string, string> = {
  b_0_7: "0-7 days",
  b_8_15: "8-15 days",
  b_16_30: "16-30 days",
  b_31_60: "31-60 days",
  b_gt_60: "60+ days",
};

export default function BankWiseLeadsPage() {
  const { token } = useStaffAuth();
  const [leads, setLeads] = useState<Lead[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [stageFilter, setStageFilter] = useState("");
  const [bucketFilter, setBucketFilter] = useState("");
  const [bankFilter, setBankFilter] = useState("");
  const [sortBy, setSortBy] = useState("stage_days_desc");
  const [page, setPage] = useState(1);
  const [totalCount, setTotalCount] = useState(0);
  const perPage = 20;

  const fetchLeads = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setError("");
    try {
      const params = new URLSearchParams();
      if (search) params.set("search", search);
      if (stageFilter) params.set("stage_filter", stageFilter);
      if (bucketFilter) params.set("bucket_filter", bucketFilter);
      if (bankFilter) params.set("bank_name", bankFilter);
      if (sortBy) params.set("sort_by", sortBy);
      const res = await api.get(`/crm/bank-wise-leads?${params.toString()}`);
      const data = res.data;
      setLeads(data?.leads || data?.data || data?.items || (Array.isArray(data) ? data : []));
      setTotalCount(data?.total || data?.count || 0);
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Failed to load bank-wise leads");
    } finally {
      setLoading(false);
    }
  }, [token, search, stageFilter, bucketFilter, bankFilter, sortBy, page]);

  useEffect(() => { fetchLeads(); }, [fetchLeads]);

  const totalPages = Math.max(1, Math.ceil(totalCount / perPage));

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-3">
            <Landmark className="w-8 h-8 text-amber-600" />
            Bank-Wise Leads
          </h1>
          <p className="text-gray-500 mt-1">Manage and track bank loan application pipeline</p>
        </div>
        <Button onClick={fetchLeads} variant="outline" size="sm">
          <RefreshCw className="w-4 h-4 mr-2" /> Refresh
        </Button>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="pt-4">
          <div className="flex flex-wrap gap-3">
            <div className="relative flex-1 min-w-[200px]">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <Input
                className="pl-9"
                placeholder="Search by name, phone, bank..."
                value={search}
                onChange={(e) => { setSearch(e.target.value); setPage(1); }}
              />
            </div>
            <Select value={stageFilter || "all"} onValueChange={(v) => { setStageFilter(v === "all" ? "" : v); setPage(1); }}>
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="All Stages" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Stages</SelectItem>
                <SelectItem value="pending_with_bank">Pending With Bank</SelectItem>
                <SelectItem value="balance_pending">Balance Pending</SelectItem>
                <SelectItem value="approved">Approved</SelectItem>
                <SelectItem value="rejected">Rejected</SelectItem>
                <SelectItem value="disbursed">Disbursed</SelectItem>
                <SelectItem value="closed">Closed</SelectItem>
              </SelectContent>
            </Select>
            <Select value={bucketFilter || "all"} onValueChange={(v) => { setBucketFilter(v === "all" ? "" : v); setPage(1); }}>
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="All Buckets" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Buckets</SelectItem>
                <SelectItem value="b_0_7">0-7 Days</SelectItem>
                <SelectItem value="b_8_15">8-15 Days</SelectItem>
                <SelectItem value="b_16_30">16-30 Days</SelectItem>
                <SelectItem value="b_31_60">31-60 Days</SelectItem>
                <SelectItem value="b_gt_60">60+ Days</SelectItem>
              </SelectContent>
            </Select>
            <Select value={sortBy} onValueChange={setSortBy}>
              <SelectTrigger className="w-[200px]">
                <SelectValue placeholder="Sort By" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="stage_days_desc">Days in Stage (High→Low)</SelectItem>
                <SelectItem value="stage_days_asc">Days in Stage (Low→High)</SelectItem>
                <SelectItem value="customer_name">Customer Name</SelectItem>
                <SelectItem value="bank">Bank Name</SelectItem>
                <SelectItem value="deal_value">Deal Value</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Error */}
      {error && (
        <div className="flex items-center gap-2 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
          <AlertCircle className="w-5 h-5" />
          {error}
        </div>
      )}

      {/* Table */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="text-lg font-semibold">
            {loading ? "Loading..." : `${totalCount || leads.length} Leads`}
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {loading ? (
            <div className="flex items-center justify-center py-16">
              <Loader2 className="w-8 h-8 animate-spin text-amber-600" />
              <span className="ml-3 text-gray-500">Loading leads...</span>
            </div>
          ) : leads.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 text-gray-400">
              <Landmark className="w-12 h-12 mb-3 opacity-30" />
              <p className="font-medium">No leads found</p>
              <p className="text-sm">Try adjusting filters or search terms</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 border-b">
                  <tr>
                    <th className="text-left px-4 py-3 font-semibold text-gray-600">Customer</th>
                    <th className="text-left px-4 py-3 font-semibold text-gray-600">Bank</th>
                    <th className="text-left px-4 py-3 font-semibold text-gray-600">Stage</th>
                    <th className="text-left px-4 py-3 font-semibold text-gray-600">Days</th>
                    <th className="text-left px-4 py-3 font-semibold text-gray-600">Bucket</th>
                    <th className="text-left px-4 py-3 font-semibold text-gray-600">Deal Value</th>
                    <th className="text-left px-4 py-3 font-semibold text-gray-600">Handlers</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {leads.map((lead, idx) => (
                    <tr key={lead.id || idx} className="hover:bg-gray-50 transition-colors">
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <User className="w-4 h-4 text-gray-400 flex-shrink-0" />
                          <div>
                            <p className="font-medium text-gray-900">{lead.customer_name || lead.name || "—"}</p>
                            <p className="text-xs text-gray-500 flex items-center gap-1">
                              <Phone className="w-3 h-3" /> {lead.phone || "—"}
                            </p>
                          </div>
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-1 text-gray-700">
                          <Building2 className="w-4 h-4 text-gray-400" />
                          {lead.bank_name || "—"}
                        </div>
                        {lead.district && <p className="text-xs text-gray-400">{lead.district}</p>}
                      </td>
                      <td className="px-4 py-3">
                        <span className={`px-2 py-1 rounded-full text-xs font-semibold ${STAGE_COLORS[lead.stage || ""] || "bg-gray-100 text-gray-600"}`}>
                          {(lead.stage || "unknown").replace(/_/g, " ")}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-1">
                          <Calendar className="w-3 h-3 text-gray-400" />
                          <span className={`font-semibold ${(lead.stage_days || 0) > 30 ? "text-red-600" : (lead.stage_days || 0) > 15 ? "text-orange-600" : "text-green-600"}`}>
                            {lead.stage_days ?? "—"}
                          </span>
                        </div>
                      </td>
                      <td className="px-4 py-3 text-gray-600 text-xs">
                        {BUCKET_LABELS[lead.bucket || ""] || lead.bucket || "—"}
                      </td>
                      <td className="px-4 py-3">
                        {lead.deal_value ? (
                          <div className="flex items-center gap-1 font-semibold text-emerald-700">
                            <TrendingUp className="w-3 h-3" />
                            ₹{lead.deal_value.toLocaleString("en-IN")}
                          </div>
                        ) : "—"}
                      </td>
                      <td className="px-4 py-3 text-xs text-gray-500">
                        {lead.telecaller && <div>TC: {lead.telecaller}</div>}
                        {lead.ground_source && <div>GS: {lead.ground_source}</div>}
                        {lead.handler && <div>H: {lead.handler}</div>}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Pagination */}
      {totalCount > perPage && (
        <div className="flex items-center justify-between">
          <p className="text-sm text-gray-500">
            Showing {((page - 1) * perPage) + 1}–{Math.min(page * perPage, totalCount)} of {totalCount}
          </p>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage(p => p - 1)}>
              <ChevronLeft className="w-4 h-4" />
            </Button>
            <span className="px-3 py-2 text-sm font-medium">{page} / {totalPages}</span>
            <Button variant="outline" size="sm" disabled={page >= totalPages} onClick={() => setPage(p => p + 1)}>
              <ChevronRight className="w-4 h-4" />
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
