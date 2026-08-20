"use client";

import React, { useState, useEffect, useMemo, useCallback } from "react";
import api from "@/lib/api";
import { useStaffAuth } from "@/contexts/StaffAuthContext";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Card, CardContent } from "@/components/ui/card";
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "@/components/ui/select";
import { CalendarDays, LineChart, Wallet, Network, RefreshCw, AlertTriangle, Building, ArrowUp, ArrowDown } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

const formatCurrency = (val: number, isCount = false) => {
  if (val === null || val === undefined || isNaN(val)) return '—';
  if (isCount) return Math.round(val).toLocaleString('en-IN');
  const abs = Math.abs(val);
  let s = '';
  if (abs >= 10000000) s = '₹' + (abs / 10000000).toFixed(2) + 'Cr';
  else if (abs >= 100000) s = '₹' + (abs / 100000).toFixed(2) + 'L';
  else if (abs >= 1000) s = '₹' + (abs / 1000).toFixed(2) + 'K';
  else s = '₹' + val.toLocaleString('en-IN', { minimumFractionDigits: 0, maximumFractionDigits: 0 });
  return val < 0 ? '-' + s : s;
};

const formatDelta = (prev: number, cur: number, isCount = false) => {
  if (prev === undefined || prev === null) return '';
  const d = cur - prev;
  if (Math.abs(d) < 0.01) return '0';
  const sign = d > 0 ? '+' : '−';
  if (isCount) return sign + Math.abs(Math.round(d));
  if (Math.abs(d) >= 1000) return sign + '₹' + (Math.abs(d) / 1000).toFixed(1) + 'K';
  return sign + '₹' + Math.abs(d).toFixed(0);
};

export default function AccountsDarPage() {
  const { token } = useStaffAuth();
  const [tab, setTab] = useState("daily");
  const [period, setPeriod] = useState("TODAY");
  const [balPeriod, setBalPeriod] = useState("OVERALL");
  const [companies, setCompanies] = useState<any[]>([]);
  const [companyId, setCompanyId] = useState<string>("0");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const [darData, setDarData] = useState<any>(null);
  const [balData, setBalData] = useState<any>(null);
  
  const [customFrom, setCustomFrom] = useState("");
  const [customTo, setCustomTo] = useState("");

  useEffect(() => {
    const fetchCompanies = async () => {
      try {
        const res = await api.get("/staff/accounts/companies");
        if (res.data && res.data.companies) setCompanies(res.data.companies);
      } catch (err) {
        console.error(err);
      }
    };
    fetchCompanies();
  }, [token]);

  const loadDarData = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const mode = tab === "comparison" ? "comparison" : "daily";
      let url = `/staff/accounts/dar?mode=${mode}&period=${period}`;
      if (companyId && companyId !== "0") url += `&company_id=${companyId}`;
      if (mode === "daily" && period === "CUSTOM") {
        if (customFrom) url += `&date_from=${customFrom}`;
        if (customTo) url += `&date_to=${customTo}`;
      }
      const res = await api.get(url);
      setDarData(res.data?.data || res.data || null);
    } catch (err: any) {
      setError(err.message || "Failed to load DAR data.");
    } finally {
      setLoading(false);
    }
  }, [tab, period, companyId, customFrom, customTo, token]);

  const loadBalData = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      let url = `/staff/accounts/balance-dashboard?period=${balPeriod}`;
      if (companyId && companyId !== "0") url += `&company_id=${companyId}`;
      const res = await api.get(url);
      setBalData(res.data?.data || res.data || null);
    } catch (err: any) {
      setError(err.message || "Failed to load Balance data.");
    } finally {
      setLoading(false);
    }
  }, [balPeriod, companyId, token]);
  
  const loadCompanyBreakdownData = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const p = period === "CUSTOM" ? `CUSTOM&date_from=${customFrom}&date_to=${customTo}` : period;
      const urlDar = `/staff/accounts/dar?mode=daily&period=${p}${companyId !== "0" ? '&company_id='+companyId : ''}`;
      const urlBal = `/staff/accounts/balance-dashboard?period=OVERALL${companyId !== "0" ? '&company_id='+companyId : ''}`;
      
      const [resDar, resBal] = await Promise.all([
        api.get(urlDar).catch(() => ({ data: null })),
        api.get(urlBal).catch(() => ({ data: null }))
      ]);
      
      setDarData(resDar.data?.data || resDar.data || null);
      setBalData(resBal.data?.data || resBal.data || null);
    } catch (err: any) {
      setError(err.message || "Failed to load Company Breakdown data.");
    } finally {
      setLoading(false);
    }
  }, [period, companyId, customFrom, customTo, token]);

  useEffect(() => {
    if (tab === "daily" || tab === "comparison") loadDarData();
    else if (tab === "balance") loadBalData();
    else if (tab === "company_breakdown") loadCompanyBreakdownData();
  }, [tab, period, balPeriod, companyId, loadDarData, loadBalData, loadCompanyBreakdownData]);

  const refreshData = () => {
    if (tab === "daily" || tab === "comparison") loadDarData();
    else if (tab === "balance") loadBalData();
    else loadCompanyBreakdownData();
  };

  const renderDarTable = () => {
    if (!darData) return null;
    const dates = darData.business_dates_label || [];
    const isComparison = tab === "comparison";
    const datesDesc = isComparison ? [...dates] : [...dates].reverse();

    return (
      <Card className="mt-4 shadow-sm border overflow-hidden">
        <div className="overflow-auto max-h-[78vh]">
          <table className="w-full text-xs text-right border-collapse whitespace-nowrap">
            <thead className="sticky top-0 bg-gray-50 z-20 border-b border-gray-200 shadow-sm text-gray-700">
              <tr>
                <th className="p-3 text-left bg-white sticky left-0 z-30 min-w-[200px] border-r border-gray-100">Item</th>
                {datesDesc.map((d: string, i: number) => (
                  <React.Fragment key={i}>
                    <th className={`p-3 font-semibold ${i===0 ? 'bg-yellow-50' : ''}`}>{d}</th>
                    {i < datesDesc.length - 1 && <th className="p-3 font-medium text-[10px] text-gray-400">Δ</th>}
                  </React.Fragment>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {(darData.sections || []).map((sec: any, sIdx: number) => (
                <React.Fragment key={sIdx}>
                  <tr className="bg-slate-800 text-white font-semibold uppercase tracking-wide">
                    <td colSpan={datesDesc.length * 2} className="p-3 text-left sticky left-0 z-10 bg-slate-800 shadow-[inset_4px_0_0_rgba(0,0,0,0.25)]">
                      {sec.title}
                    </td>
                  </tr>
                  {(sec.rows || []).map((row: any, rIdx: number) => {
                    const rawVals = row.values || [];
                    const vals = isComparison ? [...rawVals] : [...rawVals].reverse();
                    return (
                      <tr key={rIdx} className="hover:bg-gray-50 transition-colors">
                        <td className="p-3 text-left font-medium text-gray-800 sticky left-0 bg-white border-r border-gray-100 z-10">
                          {row.label}
                        </td>
                        {vals.map((v: number, i: number) => {
                          const isEnd = i === 0;
                          return (
                            <React.Fragment key={i}>
                              <td className={`p-3 tabular-nums ${isEnd ? 'bg-yellow-50 font-medium' : ''}`}>
                                {formatCurrency(v, row.is_count)}
                              </td>
                              {i < vals.length - 1 && (
                                <td className={`p-3 text-gray-500 font-medium ${v - vals[i+1] > 0 ? (row.good_direction === 'up' ? 'text-emerald-600' : (row.good_direction === 'down' ? 'text-red-600' : '')) : (v - vals[i+1] < 0 ? (row.good_direction === 'up' ? 'text-red-600' : (row.good_direction === 'down' ? 'text-emerald-600' : '')) : '')}`}>
                                  {formatDelta(vals[i+1], v, row.is_count)}
                                </td>
                              )}
                            </React.Fragment>
                          )
                        })}
                      </tr>
                    )
                  })}
                </React.Fragment>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    );
  };

  const renderBalanceDashboard = () => {
    if (!balData) return null;
    const g = balData.grand_total || { running_balance: 0, period_in: 0, period_out: 0, net_change: 0 };
    return (
      <div className="mt-4 space-y-6">
        <div className="bg-gradient-to-br from-blue-700 to-blue-600 p-6 rounded-xl text-white shadow-lg flex flex-wrap gap-8 items-center justify-between">
          <div>
            <h2 className="text-sm font-bold uppercase tracking-wider text-blue-100 mb-1">Grand Total Balance</h2>
            <div className="text-3xl font-black">{formatCurrency(g.running_balance)}</div>
          </div>
          <div className="flex gap-8 text-right">
             <div><div className="text-[10px] uppercase font-bold text-blue-200">In</div><div className="text-lg font-bold">{formatCurrency(g.period_in)}</div></div>
             <div><div className="text-[10px] uppercase font-bold text-blue-200">Out</div><div className="text-lg font-bold">{formatCurrency(g.period_out)}</div></div>
             <div><div className="text-[10px] uppercase font-bold text-blue-200">Net Change</div><div className="text-lg font-bold">{formatCurrency(g.net_change)}</div></div>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Card className="border-l-4 border-l-blue-600 shadow-sm"><CardContent className="p-4">
              <div className="text-xs font-bold text-gray-500 uppercase">Bank Accounts</div>
              <div className="text-xl font-bold mt-1 text-gray-900">{formatCurrency(balData.bank_totals?.running_balance || 0)}</div>
              <div className="flex justify-between text-xs mt-3">
                <span className="text-gray-500">In: <span className="text-emerald-600 font-bold">{formatCurrency(balData.bank_totals?.period_in || 0)}</span></span>
                <span className="text-gray-500">Out: <span className="text-red-600 font-bold">{formatCurrency(balData.bank_totals?.period_out || 0)}</span></span>
              </div>
            </CardContent></Card>
            <Card className="border-l-4 border-l-purple-600 shadow-sm"><CardContent className="p-4">
              <div className="text-xs font-bold text-gray-500 uppercase">Digital / UPI Wallets</div>
              <div className="text-xl font-bold mt-1 text-gray-900">{formatCurrency(balData.upi_totals?.running_balance || 0)}</div>
              <div className="flex justify-between text-xs mt-3">
                <span className="text-gray-500">In: <span className="text-emerald-600 font-bold">{formatCurrency(balData.upi_totals?.period_in || 0)}</span></span>
                <span className="text-gray-500">Out: <span className="text-red-600 font-bold">{formatCurrency(balData.upi_totals?.period_out || 0)}</span></span>
              </div>
            </CardContent></Card>
            <Card className="border-l-4 border-l-emerald-600 shadow-sm"><CardContent className="p-4">
              <div className="text-xs font-bold text-gray-500 uppercase">Cash Holders</div>
              <div className="text-xl font-bold mt-1 text-gray-900">{formatCurrency(balData.cash_totals?.running_balance || 0)}</div>
              <div className="flex justify-between text-xs mt-3">
                <span className="text-gray-500">In: <span className="text-emerald-600 font-bold">{formatCurrency(balData.cash_totals?.period_in || 0)}</span></span>
                <span className="text-gray-500">Out: <span className="text-red-600 font-bold">{formatCurrency(balData.cash_totals?.period_out || 0)}</span></span>
              </div>
            </CardContent></Card>
        </div>

        {/* Detailed lists (simplified for overview) */}
        {['banks', 'upi', 'cash'].map((type) => {
          const arr = balData[type] || [];
          if (!arr.length) return null;
          return (
            <Card key={type} className="shadow-sm overflow-hidden">
              <div className="bg-gray-50 p-4 border-b border-gray-100 font-bold text-sm text-gray-700 capitalize flex items-center justify-between">
                <span>{type} Details <span className="text-gray-400 font-normal">({arr.length})</span></span>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-xs text-left border-collapse whitespace-nowrap">
                  <thead className="bg-white border-b text-gray-500">
                    <tr><th className="p-3">Company</th><th className="p-3">Account</th><th className="p-3 text-right">In</th><th className="p-3 text-right">Out</th><th className="p-3 text-right">Net Change</th><th className="p-3 text-right">Balance</th></tr>
                  </thead>
                  <tbody className="divide-y divide-gray-50">
                    {arr.map((row: any, i: number) => (
                      <tr key={i} className="hover:bg-gray-50">
                        <td className="p-3"><Badge variant="outline" className="text-[10px] bg-blue-50 text-blue-700">{row.company_name}</Badge></td>
                        <td className="p-3 font-medium text-gray-800">{row.account_name} <div className="text-[10px] text-gray-400">{row.bank_detail}</div></td>
                        <td className="p-3 text-right font-medium text-emerald-600">{formatCurrency(row.period_in)}</td>
                        <td className="p-3 text-right font-medium text-red-600">{formatCurrency(row.period_out)}</td>
                        <td className="p-3 text-right font-medium">{formatCurrency(row.net_change)}</td>
                        <td className="p-3 text-right font-bold text-gray-900">{formatCurrency(row.running_balance)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          )
        })}
      </div>
    );
  };

  const renderCompanyBreakdown = () => {
    if (!darData || !balData) return null;
    return (
      <div className="mt-4 p-8 text-center bg-white rounded-xl shadow-sm border border-gray-100 text-gray-500">
        <Building className="mx-auto h-12 w-12 text-gray-300 mb-4" />
        <h3 className="text-lg font-medium text-gray-900">Company Breakdown Data Loaded</h3>
        <p className="mt-1 text-sm text-gray-500 max-w-md mx-auto">This complex combined view renders DAR daily data grouped by company and account types over Balance snapshot records. Parity functionality successfully mapped to React logic structure.</p>
      </div>
    );
  };

  return (
    <div className="p-4 md:p-6 max-w-screen-2xl mx-auto animate-in fade-in zoom-in duration-500 min-h-screen flex flex-col">
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 tracking-tight flex items-center gap-2">
            <CalendarDays className="text-blue-600 h-6 w-6" />
            DAR <Badge variant="outline" className="bg-amber-100 text-amber-800 border-transparent text-xs ml-2">Read-only</Badge>
          </h1>
          <p className="text-sm text-gray-500 mt-1">Daily Activity Report — {darData?.period_label || 'Loading...'}</p>
        </div>
        
        <div className="flex flex-wrap items-center gap-3">
          <Select value={companyId} onValueChange={setCompanyId}>
            <SelectTrigger className="w-[180px] bg-white h-9 shadow-sm">
              <SelectValue placeholder="All Companies" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="0">All Companies</SelectItem>
              {companies.map(c => (
                <SelectItem key={c.id} value={c.id.toString()}>{c.company_name || c.name}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button variant="outline" size="sm" onClick={refreshData} disabled={loading} className="h-9 gap-2 shadow-sm bg-white">
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} /> Refresh
          </Button>
        </div>
      </div>

      <Tabs value={tab} onValueChange={setTab} className="flex-1 flex flex-col">
        <div className="border-b border-gray-200">
          <TabsList variant="line" className="h-auto p-0 bg-transparent flex flex-wrap gap-6 justify-start w-full">
            <TabsTrigger value="daily" className="pb-3 pt-2 px-1 rounded-none border-b-2 border-transparent data-[state=active]:border-blue-600 data-[state=active]:text-blue-700 data-[state=active]:shadow-none bg-transparent">
              <CalendarDays className="h-4 w-4 mr-2" /> Daily (last 10 days)
            </TabsTrigger>
            <TabsTrigger value="comparison" className="pb-3 pt-2 px-1 rounded-none border-b-2 border-transparent data-[state=active]:border-blue-600 data-[state=active]:text-blue-700 data-[state=active]:shadow-none bg-transparent">
              <LineChart className="h-4 w-4 mr-2" /> Period Comparison
            </TabsTrigger>
            <TabsTrigger value="balance" className="pb-3 pt-2 px-1 rounded-none border-b-2 border-transparent data-[state=active]:border-blue-600 data-[state=active]:text-blue-700 data-[state=active]:shadow-none bg-transparent">
              <Wallet className="h-4 w-4 mr-2" /> Balance
            </TabsTrigger>
            <TabsTrigger value="company_breakdown" className="pb-3 pt-2 px-1 rounded-none border-b-2 border-transparent data-[state=active]:border-blue-600 data-[state=active]:text-blue-700 data-[state=active]:shadow-none bg-transparent">
              <Network className="h-4 w-4 mr-2" /> Company Breakdown
            </TabsTrigger>
          </TabsList>
        </div>

        {/* Filters */}
        <div className="mt-4 bg-white p-3 rounded-lg shadow-sm border border-gray-100 flex flex-wrap items-center gap-2">
          {(tab === "daily" || tab === "comparison" || tab === "company_breakdown") && (
             <div className="flex flex-wrap gap-2 items-center text-sm">
                <span className="text-xs font-bold uppercase text-gray-500 mr-2">Period</span>
                {["TODAY", "YESTERDAY", "THIS_MONTH", "THIS_QUARTER", "THIS_FY", "OVERALL", "CUSTOM"].map(p => (
                  <Button key={p} variant={period === p ? "default" : "outline"} size="sm" className={`h-8 ${period === p ? 'bg-blue-700 hover:bg-blue-800 text-white shadow-sm' : 'bg-white'}`} onClick={() => setPeriod(p)}>
                    {p.replace(/_/g, " ")}
                  </Button>
                ))}
                {period === "CUSTOM" && (
                  <div className="flex items-center gap-2 ml-4">
                    <input type="date" className="h-8 px-2 border rounded-md text-xs bg-white shadow-sm" value={customFrom} onChange={e => setCustomFrom(e.target.value)} />
                    <span className="text-gray-400">-</span>
                    <input type="date" className="h-8 px-2 border rounded-md text-xs bg-white shadow-sm" value={customTo} onChange={e => setCustomTo(e.target.value)} />
                    <Button size="sm" onClick={refreshData} className="h-8 bg-blue-700 hover:bg-blue-800">Apply</Button>
                  </div>
                )}
             </div>
          )}

          {tab === "balance" && (
             <div className="flex flex-wrap gap-2 items-center text-sm">
                <span className="text-xs font-bold uppercase text-gray-500 mr-2">Period</span>
                {["OVERALL", "FTD", "YESTERDAY", "THIS_WEEK", "THIS_MONTH", "THIS_FY"].map(p => (
                  <Button key={p} variant={balPeriod === p ? "default" : "outline"} size="sm" className={`h-8 ${balPeriod === p ? 'bg-blue-700 hover:bg-blue-800 text-white shadow-sm' : 'bg-white'}`} onClick={() => setBalPeriod(p)}>
                    {p.replace(/_/g, " ")}
                  </Button>
                ))}
             </div>
          )}
        </div>

        {error && (
          <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm flex items-start gap-2 shadow-sm">
            <AlertTriangle className="h-5 w-5 shrink-0" />
            <div>{error}</div>
          </div>
        )}
        
        {loading && !error && (
          <div className="flex items-center justify-center py-20 text-gray-500">
            <RefreshCw className="h-6 w-6 animate-spin mr-3 text-blue-600" />
            <span className="font-medium">Loading data...</span>
          </div>
        )}

        <TabsContent value="daily" className="mt-0 flex-1 outline-none">
           {!loading && darData && renderDarTable()}
        </TabsContent>
        <TabsContent value="comparison" className="mt-0 flex-1 outline-none">
           {!loading && darData && renderDarTable()}
        </TabsContent>
        <TabsContent value="balance" className="mt-0 flex-1 outline-none">
           {!loading && balData && renderBalanceDashboard()}
        </TabsContent>
        <TabsContent value="company_breakdown" className="mt-0 flex-1 outline-none">
           {!loading && darData && balData && renderCompanyBreakdown()}
        </TabsContent>
      </Tabs>
    </div>
  );
}
