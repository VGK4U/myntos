"use client";

import React, { useState, useEffect, useCallback, useMemo } from "react";
import { useStaffAuth } from "@/contexts/StaffAuthContext";
import api from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useSearchParams } from "next/navigation";
import { Loader2, ChevronRight, ChevronDown, Building, FileInvoiceDollar, ShoppingCart, Barcode, Search, RefreshCw, AlertCircle, Info } from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";

interface Company {
  id: number;
  name: string;
  company_name?: string;
}

interface CompanyTaxData {
  invoice_count: number;
  cgst: number;
  sgst: number;
  igst: number;
  total_tax: number;
}

interface CompanySummary {
  id: string;
  company_name: string;
  output: CompanyTaxData;
  input: CompanyTaxData;
  net_liability: number;
}

interface DutiesSummaryResponse {
  success: boolean;
  total_output_gst: number;
  total_input_gst: number;
  net_gst_liability: number;
  companies: CompanySummary[];
  detail?: string;
}

interface HsnSummary {
  hsn_code: string;
  gst_rate: number;
  inv_count: number;
  taxable: number;
  cgst: number;
  sgst: number;
  igst: number;
  total_tax: number;
}

interface HsnSummaryResponse {
  success: boolean;
  output_hsn: HsnSummary[];
  input_hsn: HsnSummary[];
  detail?: string;
}

interface HsnDetailInvoice {
  invoice_number: string;
  invoice_date: string;
  party_name: string;
  gstin?: string;
  line_count: number;
  total_qty: number;
  taxable: number;
  cgst: number;
  sgst: number;
  igst: number;
  total_tax: number;
}

interface HsnDetailLineItem {
  invoice_number: string;
  invoice_date: string;
  party_name: string;
  item_code: string;
  item_description: string;
  quantity: number;
  uom: string;
  unit_rate: number;
  taxable: number;
  gst_rate: number;
  cgst: number;
  sgst: number;
  igst: number;
  total_tax: number;
  line_total: number;
}

interface HsnDetailResponse {
  success: boolean;
  invoices: HsnDetailInvoice[];
  line_items: HsnDetailLineItem[];
  detail?: string;
}

const formatCurrency = (amount: number | string) => {
  const num = parseFloat(amount as string) || 0;
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(num);
};

const formatDate = (date: Date) => {
  return date.toISOString().split('T')[0];
};

const getFyStart = () => {
  const t = new Date();
  const y = t.getMonth() >= 3 ? t.getFullYear() : t.getFullYear() - 1;
  return new Date(y, 3, 1);
};

export default function DutiesTaxesPage() {
  const { token } = useStaffAuth();
  const searchParams = useSearchParams();
  
  const ctxCompanyId = searchParams?.get('company_id') || '0';
  const ctxAsOn = searchParams?.get('as_on') || searchParams?.get('to_date') || '';
  const ctxFrom = searchParams?.get('from_date') || '';

  const [activeTab, setActiveTab] = useState("company");
  
  // Filters
  const [companyId, setCompanyId] = useState(ctxCompanyId);
  const [fromDate, setFromDate] = useState(ctxFrom || formatDate(getFyStart()));
  const [toDate, setToDate] = useState(ctxAsOn || formatDate(new Date()));
  const [periodFilter, setPeriodFilter] = useState("fy");
  const [companies, setCompanies] = useState<Company[]>([]);
  
  // Data State
  const [summaryData, setSummaryData] = useState<DutiesSummaryResponse | null>(null);
  const [loadingSummary, setLoadingSummary] = useState(false);
  const [summaryError, setSummaryError] = useState("");

  const [hsnData, setHsnData] = useState<HsnSummaryResponse | null>(null);
  const [loadingHsn, setLoadingHsn] = useState(false);
  const [hsnError, setHsnError] = useState("");
  const [hsnLoaded, setHsnLoaded] = useState(false);

  // HSN Detail State
  const [hsnDetails, setHsnDetails] = useState<Record<string, HsnDetailResponse>>({});
  const [loadingHsnDetails, setLoadingHsnDetails] = useState<Record<string, boolean>>({});
  const [expandedHsn, setExpandedHsn] = useState<Record<string, boolean>>({});
  const [hsnDetailTab, setHsnDetailTab] = useState<Record<string, 'inv' | 'li'>>({});

  useEffect(() => {
    if (!token) return;
    fetchCompanies();
  }, [token]);

  useEffect(() => {
    if (!token) return;
    fetchSummaryData();
    if (activeTab === "hsn" && !hsnLoaded) {
      fetchHsnData();
    }
  }, [token, activeTab, hsnLoaded]);

  const fetchCompanies = async () => {
    try {
      const res = await api.get('/staff/accounts/companies');
      setCompanies(res.data.companies || []);
    } catch (err) {
      console.error("Failed to load companies", err);
    }
  };

  const buildParams = useCallback(() => {
    const params = new URLSearchParams();
    if (companyId && companyId !== '0') params.append('company_id', companyId);
    if (fromDate) params.append('from_date', fromDate);
    if (toDate) params.append('to_date', toDate);
    return params;
  }, [companyId, fromDate, toDate]);

  const fetchSummaryData = async () => {
    setLoadingSummary(true);
    setSummaryError("");
    try {
      const res = await api.get(`/staff/accounts/duties-taxes-summary?${buildParams().toString()}`);
      if (res.data.success) {
        setSummaryData(res.data);
      } else {
        setSummaryError(res.data.detail || "Failed to load summary");
      }
    } catch (err: any) {
      setSummaryError(err.response?.data?.detail || err.message || "Failed to fetch summary data");
    } finally {
      setLoadingSummary(false);
    }
  };

  const fetchHsnData = async () => {
    setLoadingHsn(true);
    setHsnError("");
    setHsnLoaded(true);
    try {
      const res = await api.get(`/staff/accounts/duties-taxes-hsn-summary?${buildParams().toString()}`);
      if (res.data.success) {
        setHsnData(res.data);
      } else {
        setHsnError(res.data.detail || "Failed to load HSN data");
      }
    } catch (err: any) {
      setHsnError(err.response?.data?.detail || err.message || "Failed to fetch HSN data");
    } finally {
      setLoadingHsn(false);
    }
  };

  const applyFilters = () => {
    setHsnLoaded(false);
    fetchSummaryData();
    if (activeTab === "hsn") fetchHsnData();
  };

  const handlePeriodChange = (period: string) => {
    setPeriodFilter(period);
    const today = new Date();
    const to = formatDate(today);
    
    if (period === 'month') {
      setFromDate(formatDate(new Date(today.getFullYear(), today.getMonth(), 1)));
      setToDate(to);
    } else if (period === 'quarter') {
      const qm = [0,0,0,3,3,3,6,6,6,9,9,9][today.getMonth()];
      setFromDate(formatDate(new Date(today.getFullYear(), qm, 1)));
      setToDate(to);
    } else if (period === 'fy') {
      setFromDate(formatDate(getFyStart()));
      setToDate(to);
    } else if (period === 'overall') {
      setFromDate('');
      setToDate(to);
    }
    
    if (period !== 'custom') {
      setTimeout(applyFilters, 0);
    }
  };

  const toggleHsnDetail = async (side: 'output' | 'input', hsnCode: string, uid: string) => {
    const isExpanded = !!expandedHsn[uid];
    setExpandedHsn(prev => ({ ...prev, [uid]: !isExpanded }));
    
    if (!isExpanded && !hsnDetails[uid]) {
      setLoadingHsnDetails(prev => ({ ...prev, [uid]: true }));
      try {
        const params = buildParams();
        params.append('hsn_code', hsnCode);
        params.append('side', side);
        const res = await api.get(`/staff/accounts/duties-taxes-hsn-detail?${params.toString()}`);
        if (res.data.success) {
          setHsnDetails(prev => ({ ...prev, [uid]: res.data }));
          setHsnDetailTab(prev => ({ ...prev, [uid]: 'inv' }));
        }
      } catch (err) {
        console.error("Failed to load HSN detail", err);
      } finally {
        setLoadingHsnDetails(prev => ({ ...prev, [uid]: false }));
      }
    }
  };

  const renderCompanySummary = () => {
    if (loadingSummary) return <div className="flex justify-center p-12"><Loader2 className="animate-spin text-indigo-600 h-8 w-8" /></div>;
    if (summaryError) return <Alert variant="destructive"><AlertCircle className="h-4 w-4" /><AlertDescription>{summaryError}</AlertDescription></Alert>;
    if (!summaryData) return null;

    const companiesWithData = (summaryData.companies || []).filter(c => c.output.total_tax > 0 || c.input.total_tax > 0);

    return (
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div className="flex items-center gap-2">
            <Building className="h-5 w-5 text-amber-600" />
            <CardTitle>Company-wise GST Summary</CardTitle>
          </div>
          <span className="text-xs text-muted-foreground">{companiesWithData.length} companies</span>
        </CardHeader>
        <CardContent>
          {companiesWithData.length === 0 ? (
            <div className="text-center p-12 text-muted-foreground">
              <FileInvoiceDollar className="h-12 w-12 mx-auto mb-4 text-gray-300" />
              <h4 className="text-lg font-medium">No GST Data</h4>
              <p>No confirmed invoices in the selected period</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader className="bg-gray-50">
                  <TableRow>
                    <TableHead rowSpan={2} className="align-middle">Company</TableHead>
                    <TableHead colSpan={4} className="text-center bg-red-50 text-red-700 border-b-0">Output Tax (Sales)</TableHead>
                    <TableHead colSpan={4} className="text-center bg-green-50 text-green-700 border-b-0">Input Tax Credit (ITC)</TableHead>
                    <TableHead rowSpan={2} className="text-right align-middle">Net Payable</TableHead>
                  </TableRow>
                  <TableRow>
                    <TableHead className="text-right bg-red-50 text-red-700">CGST</TableHead>
                    <TableHead className="text-right bg-red-50 text-red-700">SGST</TableHead>
                    <TableHead className="text-right bg-red-50 text-red-700">IGST</TableHead>
                    <TableHead className="text-right bg-red-50 text-red-700">Total</TableHead>
                    
                    <TableHead className="text-right bg-green-50 text-green-700">CGST</TableHead>
                    <TableHead className="text-right bg-green-50 text-green-700">SGST</TableHead>
                    <TableHead className="text-right bg-green-50 text-green-700">IGST</TableHead>
                    <TableHead className="text-right bg-green-50 text-green-700">Total</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {companiesWithData.map(co => {
                    const net = Number(co.net_liability) || 0;
                    return (
                      <TableRow key={co.id}>
                        <TableCell>
                          <div className="font-semibold">{co.company_name}</div>
                          <div className="text-xs text-muted-foreground">{co.output.invoice_count} sales | {co.input.invoice_count} purchase</div>
                        </TableCell>
                        <TableCell className="text-right text-red-600">{formatCurrency(co.output.cgst)}</TableCell>
                        <TableCell className="text-right text-red-600">{formatCurrency(co.output.sgst)}</TableCell>
                        <TableCell className="text-right text-red-600">{formatCurrency(co.output.igst)}</TableCell>
                        <TableCell className="text-right font-bold text-red-600">{formatCurrency(co.output.total_tax)}</TableCell>
                        
                        <TableCell className="text-right text-green-600">{formatCurrency(co.input.cgst)}</TableCell>
                        <TableCell className="text-right text-green-600">{formatCurrency(co.input.sgst)}</TableCell>
                        <TableCell className="text-right text-green-600">{formatCurrency(co.input.igst)}</TableCell>
                        <TableCell className="text-right font-bold text-green-600">{formatCurrency(co.input.total_tax)}</TableCell>
                        
                        <TableCell className="text-right">
                          {net > 0.005 ? (
                            <span className="bg-red-100 text-red-700 px-2 py-1 rounded-full text-xs font-bold">{formatCurrency(net)}</span>
                          ) : net < -0.005 ? (
                            <span className="bg-green-100 text-green-700 px-2 py-1 rounded-full text-xs font-bold">{formatCurrency(Math.abs(net))} Cr</span>
                          ) : (
                            <span className="bg-gray-100 text-gray-600 px-2 py-1 rounded-full text-xs font-bold">Nil</span>
                          )}
                        </TableCell>
                      </TableRow>
                    );
                  })}
                  <TableRow className="font-bold bg-gray-50 border-t-2">
                    <TableCell>Total</TableCell>
                    <TableCell className="text-right text-red-600">
                      {formatCurrency(companiesWithData.reduce((s, c) => s + (Number(c.output.cgst) || 0), 0))}
                    </TableCell>
                    <TableCell className="text-right text-red-600">
                      {formatCurrency(companiesWithData.reduce((s, c) => s + (Number(c.output.sgst) || 0), 0))}
                    </TableCell>
                    <TableCell className="text-right text-red-600">
                      {formatCurrency(companiesWithData.reduce((s, c) => s + (Number(c.output.igst) || 0), 0))}
                    </TableCell>
                    <TableCell className="text-right text-red-600">
                      {formatCurrency(companiesWithData.reduce((s, c) => s + (Number(c.output.total_tax) || 0), 0))}
                    </TableCell>
                    
                    <TableCell className="text-right text-green-600">
                      {formatCurrency(companiesWithData.reduce((s, c) => s + (Number(c.input.cgst) || 0), 0))}
                    </TableCell>
                    <TableCell className="text-right text-green-600">
                      {formatCurrency(companiesWithData.reduce((s, c) => s + (Number(c.input.sgst) || 0), 0))}
                    </TableCell>
                    <TableCell className="text-right text-green-600">
                      {formatCurrency(companiesWithData.reduce((s, c) => s + (Number(c.input.igst) || 0), 0))}
                    </TableCell>
                    <TableCell className="text-right text-green-600">
                      {formatCurrency(companiesWithData.reduce((s, c) => s + (Number(c.input.total_tax) || 0), 0))}
                    </TableCell>
                    
                    <TableCell className="text-right">
                      {(() => {
                        const netFin = summaryData.total_output_gst - summaryData.total_input_gst;
                        return netFin > 0.005 ? (
                          <span className="bg-red-100 text-red-700 px-2 py-1 rounded-full text-xs font-bold">{formatCurrency(netFin)}</span>
                        ) : netFin < -0.005 ? (
                          <span className="bg-green-100 text-green-700 px-2 py-1 rounded-full text-xs font-bold">{formatCurrency(Math.abs(netFin))} Cr</span>
                        ) : (
                          <span className="bg-gray-100 text-gray-600 px-2 py-1 rounded-full text-xs font-bold">Nil</span>
                        );
                      })()}
                    </TableCell>
                  </TableRow>
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>
    );
  };

  const renderHsnTable = (data: HsnSummary[], side: 'output' | 'input') => {
    const isOutput = side === 'output';
    const colorClass = isOutput ? 'text-red-600' : 'text-green-600';
    
    if (!data.length) {
      return (
        <div className="text-center p-12 text-muted-foreground border rounded-lg bg-gray-50/50 mt-4">
          <Barcode className="h-12 w-12 mx-auto mb-4 text-gray-300" />
          <h4 className="text-lg font-medium">No {isOutput ? 'Output' : 'Input'} HSN Data</h4>
          <p>No {isOutput ? 'sales' : 'purchase'} invoice line items in the selected period</p>
        </div>
      );
    }

    return (
      <div className="overflow-x-auto border rounded-lg mt-4">
        <Table>
          <TableHeader className="bg-gray-50">
            <TableRow>
              <TableHead className="w-8"></TableHead>
              <TableHead>HSN Code</TableHead>
              <TableHead className="text-right">GST Rate</TableHead>
              <TableHead className="text-right">Invoices</TableHead>
              <TableHead className="text-right">Taxable Value</TableHead>
              <TableHead className="text-right text-blue-600">CGST</TableHead>
              <TableHead className="text-right text-blue-600">SGST</TableHead>
              <TableHead className="text-right text-blue-600">IGST</TableHead>
              <TableHead className={`text-right ${colorClass}`}>Total Tax</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {data.map((row, idx) => {
              const uid = `hsn_${side}_${idx}_${row.hsn_code.replace(/[^a-zA-Z0-9]/g, '_')}`;
              const isExpanded = !!expandedHsn[uid];
              
              return (
                <React.Fragment key={uid}>
                  <TableRow className="cursor-pointer hover:bg-gray-50" onClick={() => toggleHsnDetail(side, row.hsn_code, uid)}>
                    <TableCell>
                      {isExpanded ? <ChevronDown className="h-4 w-4 text-indigo-600" /> : <ChevronRight className="h-4 w-4 text-gray-400" />}
                    </TableCell>
                    <TableCell><span className="bg-indigo-50 text-indigo-700 px-2 py-1 rounded font-mono text-xs font-semibold">{row.hsn_code}</span></TableCell>
                    <TableCell className="text-right"><span className="bg-blue-50 text-blue-700 px-2 py-1 rounded text-xs font-semibold">{Number(row.gst_rate).toFixed(1)}%</span></TableCell>
                    <TableCell className="text-right">{row.inv_count}</TableCell>
                    <TableCell className="text-right">{formatCurrency(row.taxable)}</TableCell>
                    <TableCell className="text-right text-blue-600">{formatCurrency(row.cgst)}</TableCell>
                    <TableCell className="text-right text-blue-600">{formatCurrency(row.sgst)}</TableCell>
                    <TableCell className="text-right text-blue-600">{formatCurrency(row.igst)}</TableCell>
                    <TableCell className={`text-right font-bold ${colorClass}`}>{formatCurrency(row.total_tax)}</TableCell>
                  </TableRow>
                  {isExpanded && (
                    <TableRow className="bg-indigo-50/30">
                      <TableCell colSpan={9} className="p-0 border-b-2 border-indigo-200">
                        <div className="p-4 pl-10">
                          {loadingHsnDetails[uid] ? (
                            <div className="flex items-center gap-2 text-indigo-600 text-sm py-4">
                              <Loader2 className="h-4 w-4 animate-spin" /> Loading invoice details...
                            </div>
                          ) : hsnDetails[uid] ? (
                            <div className="bg-white border rounded-lg shadow-sm">
                              <div className="border-b flex">
                                <button 
                                  className={`px-4 py-2 text-sm font-medium ${hsnDetailTab[uid] === 'inv' ? 'text-indigo-600 border-b-2 border-indigo-600' : 'text-gray-500 hover:text-gray-700'}`}
                                  onClick={(e) => { e.stopPropagation(); setHsnDetailTab(prev => ({ ...prev, [uid]: 'inv' })); }}
                                >
                                  Invoice Summary <span className="bg-indigo-100 text-indigo-700 px-1.5 py-0.5 rounded ml-1 text-xs">{hsnDetails[uid].invoices?.length || 0}</span>
                                </button>
                                <button 
                                  className={`px-4 py-2 text-sm font-medium ${hsnDetailTab[uid] === 'li' ? 'text-indigo-600 border-b-2 border-indigo-600' : 'text-gray-500 hover:text-gray-700'}`}
                                  onClick={(e) => { e.stopPropagation(); setHsnDetailTab(prev => ({ ...prev, [uid]: 'li' })); }}
                                >
                                  All Line Items <span className="bg-indigo-100 text-indigo-700 px-1.5 py-0.5 rounded ml-1 text-xs">{hsnDetails[uid].line_items?.length || 0}</span>
                                </button>
                              </div>
                              <div className="p-4 overflow-x-auto">
                                {hsnDetailTab[uid] === 'inv' ? (
                                  <Table className="text-xs">
                                    <TableHeader className="bg-indigo-50/50">
                                      <TableRow>
                                        <TableHead>Invoice #</TableHead>
                                        <TableHead>Date</TableHead>
                                        <TableHead>{isOutput ? 'Customer' : 'Vendor'}</TableHead>
                                        {isOutput && <TableHead>GSTIN</TableHead>}
                                        <TableHead className="text-right">Lines</TableHead>
                                        <TableHead className="text-right">Qty</TableHead>
                                        <TableHead className="text-right">Taxable</TableHead>
                                        <TableHead className="text-right">CGST</TableHead>
                                        <TableHead className="text-right">SGST</TableHead>
                                        <TableHead className="text-right">IGST</TableHead>
                                        <TableHead className="text-right">Total Tax</TableHead>
                                      </TableRow>
                                    </TableHeader>
                                    <TableBody>
                                      {(hsnDetails[uid].invoices || []).map((inv, i) => (
                                        <TableRow key={i}>
                                          <TableCell><span className="bg-sky-100 text-sky-700 px-1.5 py-0.5 rounded font-mono font-semibold">{inv.invoice_number}</span></TableCell>
                                          <TableCell className="whitespace-nowrap">{inv.invoice_date}</TableCell>
                                          <TableCell>{inv.party_name}</TableCell>
                                          {isOutput && <TableCell className="text-[10px] text-gray-500">{inv.gstin || '—'}</TableCell>}
                                          <TableCell className="text-right">{inv.line_count}</TableCell>
                                          <TableCell className="text-right text-emerald-600 font-semibold">{inv.total_qty}</TableCell>
                                          <TableCell className="text-right">{formatCurrency(inv.taxable)}</TableCell>
                                          <TableCell className="text-right text-blue-600">{formatCurrency(inv.cgst)}</TableCell>
                                          <TableCell className="text-right text-blue-600">{formatCurrency(inv.sgst)}</TableCell>
                                          <TableCell className="text-right text-blue-600">{formatCurrency(inv.igst)}</TableCell>
                                          <TableCell className="text-right font-semibold">{formatCurrency(inv.total_tax)}</TableCell>
                                        </TableRow>
                                      ))}
                                    </TableBody>
                                  </Table>
                                ) : (
                                  <Table className="text-xs">
                                    <TableHeader className="bg-indigo-50/50">
                                      <TableRow>
                                        <TableHead>Invoice #</TableHead>
                                        <TableHead>Date</TableHead>
                                        <TableHead>{isOutput ? 'Customer' : 'Vendor'}</TableHead>
                                        <TableHead>Item Code</TableHead>
                                        <TableHead>Description</TableHead>
                                        <TableHead className="text-right">Qty</TableHead>
                                        <TableHead>UOM</TableHead>
                                        <TableHead className="text-right">Unit Rate</TableHead>
                                        <TableHead className="text-right">Taxable</TableHead>
                                        <TableHead className="text-right">GST%</TableHead>
                                        <TableHead className="text-right">CGST</TableHead>
                                        <TableHead className="text-right">SGST</TableHead>
                                        <TableHead className="text-right">IGST</TableHead>
                                        <TableHead className="text-right">Total Tax</TableHead>
                                      </TableRow>
                                    </TableHeader>
                                    <TableBody>
                                      {(hsnDetails[uid].line_items || []).map((li, i) => (
                                        <TableRow key={i}>
                                          <TableCell><span className="bg-sky-100 text-sky-700 px-1.5 py-0.5 rounded font-mono font-semibold">{li.invoice_number}</span></TableCell>
                                          <TableCell className="whitespace-nowrap">{li.invoice_date}</TableCell>
                                          <TableCell className="max-w-[120px] truncate" title={li.party_name}>{li.party_name}</TableCell>
                                          <TableCell><span className="text-gray-500 font-mono text-[10px]">{li.item_code}</span></TableCell>
                                          <TableCell className="max-w-[150px] truncate" title={li.item_description}>{li.item_description}</TableCell>
                                          <TableCell className="text-right text-emerald-600 font-semibold">{li.quantity}</TableCell>
                                          <TableCell className="text-gray-500">{li.uom || '—'}</TableCell>
                                          <TableCell className="text-right">{formatCurrency(li.unit_rate)}</TableCell>
                                          <TableCell className="text-right">{formatCurrency(li.taxable)}</TableCell>
                                          <TableCell className="text-right"><span className="bg-blue-50 text-blue-700 px-1.5 py-0.5 rounded text-[10px] font-semibold">{li.gst_rate}%</span></TableCell>
                                          <TableCell className="text-right text-blue-600">{formatCurrency(li.cgst)}</TableCell>
                                          <TableCell className="text-right text-blue-600">{formatCurrency(li.sgst)}</TableCell>
                                          <TableCell className="text-right text-blue-600">{formatCurrency(li.igst)}</TableCell>
                                          <TableCell className="text-right font-semibold">{formatCurrency(li.total_tax)}</TableCell>
                                        </TableRow>
                                      ))}
                                    </TableBody>
                                  </Table>
                                )}
                              </div>
                            </div>
                          ) : (
                            <div className="text-red-500 text-sm">Failed to load details.</div>
                          )}
                        </div>
                      </TableCell>
                    </TableRow>
                  )}
                </React.Fragment>
              );
            })}
            <TableRow className="font-bold bg-gray-50 border-t-2">
              <TableCell colSpan={4}>Total</TableCell>
              <TableCell className="text-right">{formatCurrency(data.reduce((s, r) => s + Number(r.taxable), 0))}</TableCell>
              <TableCell className="text-right text-blue-600">{formatCurrency(data.reduce((s, r) => s + Number(r.cgst), 0))}</TableCell>
              <TableCell className="text-right text-blue-600">{formatCurrency(data.reduce((s, r) => s + Number(r.sgst), 0))}</TableCell>
              <TableCell className="text-right text-blue-600">{formatCurrency(data.reduce((s, r) => s + Number(r.igst), 0))}</TableCell>
              <TableCell className={`text-right ${colorClass}`}>{formatCurrency(data.reduce((s, r) => s + Number(r.total_tax), 0))}</TableCell>
            </TableRow>
          </TableBody>
        </Table>
      </div>
    );
  };

  const renderHsnSummary = () => {
    if (loadingHsn) return <div className="flex justify-center p-12"><Loader2 className="animate-spin text-indigo-600 h-8 w-8" /></div>;
    if (hsnError) return <Alert variant="destructive"><AlertCircle className="h-4 w-4" /><AlertDescription>{hsnError}</AlertDescription></Alert>;
    if (!hsnData) return null;

    return (
      <div className="space-y-6">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <div className="flex items-center gap-2">
              <FileInvoiceDollar className="h-5 w-5 text-red-600" />
              <CardTitle>Output Tax — HSN Code-wise (Sales)</CardTitle>
              <span className="bg-red-100 text-red-700 px-2 py-0.5 rounded text-xs font-semibold ml-2">GSTR-1</span>
            </div>
            <span className="text-xs text-muted-foreground">{(hsnData.output_hsn || []).length} HSN codes</span>
          </CardHeader>
          <CardContent>
            {renderHsnTable(hsnData.output_hsn || [], 'output')}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <div className="flex items-center gap-2">
              <ShoppingCart className="h-5 w-5 text-green-600" />
              <CardTitle>Input Tax Credit — HSN Code-wise (Purchases)</CardTitle>
              <span className="bg-green-100 text-green-700 px-2 py-0.5 rounded text-xs font-semibold ml-2">GSTR-2A/2B</span>
            </div>
            <span className="text-xs text-muted-foreground">{(hsnData.input_hsn || []).length} HSN codes</span>
          </CardHeader>
          <CardContent>
            {renderHsnTable(hsnData.input_hsn || [], 'input')}
          </CardContent>
        </Card>
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-gray-50/50 pb-12">
      {/* Enterprise Header */}
      <div className="bg-white border-b border-gray-200 px-8 py-6 sticky top-0 z-10">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 max-w-screen-2xl mx-auto">
          <div>
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-amber-600 rounded-lg flex items-center justify-center shadow-sm">
                <span className="text-white text-lg font-bold">%</span>
              </div>
              <div>
                <h1 className="text-2xl font-bold text-gray-900 tracking-tight">Duties &amp; Taxes (GST)</h1>
                <p className="text-sm text-gray-500 font-medium mt-0.5">Net GST liability = Output Tax (Sales) - Input Tax Credit (Purchases)</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="p-8 max-w-screen-2xl mx-auto space-y-6">
        
        {/* Context Banner */}
        {(ctxAsOn || ctxCompanyId !== '0') && (
          <Alert className="bg-purple-50 border-purple-200 text-purple-800 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>
                Filtered from Consolidated Balance Sheet — {ctxCompanyId !== '0' ? `Company ID: ${ctxCompanyId}` : ''} {ctxAsOn ? `As on: ${ctxAsOn}` : ''}
              </AlertDescription>
            </div>
            <Button variant="ghost" size="sm" className="h-8 text-purple-700 hover:text-purple-900 hover:bg-purple-100" onClick={() => {
              setCompanyId('0');
              setFromDate(formatDate(getFyStart()));
              setToDate(formatDate(new Date()));
              setPeriodFilter('fy');
              setTimeout(applyFilters, 0);
            }}>
              Clear filter
            </Button>
          </Alert>
        )}

        {/* Filters */}
        <div className="bg-white p-4 rounded-xl shadow-sm border flex flex-wrap gap-4 items-end">
          <div className="flex-1 min-w-[200px]">
            <label className="block text-xs font-bold text-gray-500 uppercase mb-1">Company</label>
            <Select value={companyId} onValueChange={setCompanyId}>
              <SelectTrigger>
                <SelectValue placeholder="All Companies" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="0">All Companies</SelectItem>
                {companies.map(c => (
                  <SelectItem key={c.id.toString()} value={c.id.toString()}>{c.company_name || c.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div>
            <label className="block text-xs font-bold text-gray-500 uppercase mb-1">Period</label>
            <div className="flex flex-wrap gap-1">
              {['month', 'quarter', 'fy', 'overall', 'custom'].map((p) => (
                <Button 
                  key={p}
                  variant={periodFilter === p ? "default" : "outline"} 
                  size="sm"
                  className={periodFilter === p ? "bg-blue-700 hover:bg-blue-800 text-white" : ""}
                  onClick={() => handlePeriodChange(p)}
                >
                  {p === 'month' ? 'This Month' : 
                   p === 'quarter' ? 'This Quarter' : 
                   p === 'fy' ? 'This FY' : 
                   p === 'overall' ? 'Overall' : 'Custom'}
                </Button>
              ))}
            </div>
          </div>

          <div>
            <label className="block text-xs font-bold text-gray-500 uppercase mb-1">From Date</label>
            <Input type="date" value={fromDate} onChange={e => { setFromDate(e.target.value); setPeriodFilter('custom'); }} className="w-[150px]" />
          </div>
          <div>
            <label className="block text-xs font-bold text-gray-500 uppercase mb-1">To Date</label>
            <Input type="date" value={toDate} onChange={e => { setToDate(e.target.value); setPeriodFilter('custom'); }} className="w-[150px]" />
          </div>

          <div className="flex gap-2">
            <Button onClick={applyFilters} className="bg-blue-700 hover:bg-blue-800 text-white"><Search className="h-4 w-4 mr-2" /> Apply</Button>
            <Button variant="outline" onClick={() => {
              setCompanyId('0');
              setPeriodFilter('fy');
              handlePeriodChange('fy');
            }}>Reset</Button>
          </div>
        </div>

        {/* Note */}
        <Alert className="bg-emerald-50 border-emerald-200 text-emerald-800">
          <Info className="h-4 w-4 text-emerald-600" />
          <AlertDescription>
            <strong>Standard Accounting:</strong> Output GST (collected on sales) is a <em>liability</em> until remitted to the government. 
            Input Tax Credit reduces that liability. <strong>Net Payable = Output - ITC.</strong> If ITC &gt; Output, the balance is a credit (shown as asset).
          </AlertDescription>
        </Alert>

        {/* Summary Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <Card className="hover:border-red-300 transition-colors">
            <CardHeader className="pb-2">
              <CardTitle className="text-xs font-bold text-gray-500 uppercase tracking-wider">Output Tax (Sales)</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-red-600">{summaryData ? formatCurrency(summaryData.total_output_gst) : '₹0'}</div>
              <p className="text-xs text-gray-400 mt-1">GST collected from customers</p>
            </CardContent>
          </Card>
          
          <Card className="hover:border-emerald-300 transition-colors">
            <CardHeader className="pb-2">
              <CardTitle className="text-xs font-bold text-gray-500 uppercase tracking-wider">Input Tax Credit (ITC)</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-emerald-600">{summaryData ? formatCurrency(summaryData.total_input_gst) : '₹0'}</div>
              <p className="text-xs text-gray-400 mt-1">GST paid to vendors</p>
            </CardContent>
          </Card>

          {(() => {
            const net = summaryData?.net_gst_liability || 0;
            const isLiability = net > 0.005;
            const isAsset = net < -0.005;
            return (
              <Card className={`transition-colors ${isLiability ? 'hover:border-amber-300 border-amber-200 bg-amber-50/30' : isAsset ? 'hover:border-emerald-300 border-emerald-200 bg-emerald-50/30' : ''}`}>
                <CardHeader className="pb-2">
                  <CardTitle className="text-xs font-bold text-gray-500 uppercase tracking-wider">
                    {isLiability ? 'Net GST Payable' : isAsset ? 'ITC Credit Balance' : 'Net GST'}
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className={`text-3xl font-bold ${isLiability ? 'text-amber-600' : isAsset ? 'text-emerald-600' : 'text-gray-900'}`}>
                    {summaryData ? formatCurrency(Math.abs(net)) : '₹0'} {isAsset && 'Cr'}
                  </div>
                  <p className="text-xs text-gray-500 mt-1">
                    {isLiability ? '= Consolidated Balance Sheet (Liability)' : isAsset ? 'ITC exceeds Output — credit available (asset)' : 'Output = ITC (balanced)'}
                  </p>
                </CardContent>
              </Card>
            );
          })()}
        </div>

        {/* Tabs */}
        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList className="mb-4">
            <TabsTrigger value="company" className="flex items-center gap-2">
              <Building className="h-4 w-4" /> Company-wise Summary
              <span className="bg-red-100 text-red-700 px-1.5 py-0.5 rounded text-[10px] ml-1">= Consolidated BS</span>
            </TabsTrigger>
            <TabsTrigger value="hsn" className="flex items-center gap-2">
              <Barcode className="h-4 w-4" /> HSN Code-wise Breakup
              <span className="bg-green-100 text-green-700 px-1.5 py-0.5 rounded text-[10px] ml-1">GST Return Filing</span>
            </TabsTrigger>
          </TabsList>
          
          <TabsContent value="company" className="mt-0">
            {renderCompanySummary()}
          </TabsContent>
          
          <TabsContent value="hsn" className="mt-0">
            {renderHsnSummary()}
          </TabsContent>
        </Tabs>

      </div>
    </div>
  );
}
