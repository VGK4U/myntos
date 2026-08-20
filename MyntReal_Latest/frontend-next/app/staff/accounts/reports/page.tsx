"use client";

import React, { useState, useEffect, useMemo, useCallback } from "react";
import Link from "next/link";
import {
  FileText,
  FileSpreadsheet,
  Download,
  Printer,
  Calendar,
  Building2,
  Filter,
  RefreshCw,
  Search,
  ArrowLeft,
  DollarSign,
  TrendingUp,
  Receipt,
  Hash,
  Layers,
  ChevronLeft,
  ChevronRight,
  Eye,
  CheckCircle2,
  Clock,
  FileEdit,
  XCircle,
  AlertCircle,
  Copy,
  Check,
  Percent,
  Sparkles,
  Info,
  ShieldCheck,
  ChevronDown
} from "lucide-react";
import toast, { Toaster } from "react-hot-toast";

import api from "@/lib/api";
import { useStaffAuth } from "@/contexts/StaffAuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";

// ── Types ────────────────────────────────────────────────────────────

interface Company {
  id: number | string;
  company_name?: string;
  name?: string;
  gstin?: string;
  gst_number?: string;
  pan_number?: string;
  is_active?: boolean;
}

interface InvoiceRecord {
  id: number | string;
  invoice_number: string;
  invoice_date?: string | null;
  customer_name?: string | null;
  customer_type?: string | null;
  vendor_id?: number | null;
  vendor_name?: string | null;
  vendor_gstin?: string | null;
  status: string;
  subtotal?: number;
  discount_amount?: number;
  taxable_amount: number;
  cgst_amount: number;
  sgst_amount: number;
  igst_amount: number;
  total_tax: number;
  grand_total: number;
  payment_status?: string | null;
}

interface HSNRecord {
  hsn_code: string;
  description?: string | null;
  gst_rate: number;
  quantity: number;
  taxable_value: number;
  cgst_rate: number;
  cgst_amount: number;
  sgst_rate: number;
  sgst_amount: number;
  igst_rate: number;
  igst_amount: number;
  total_tax: number;
  total_value: number;
}

interface ReportSummary {
  total_invoices?: number;
  total_taxable: number;
  total_cgst: number;
  total_sgst: number;
  total_igst: number;
  total_tax: number;
  grand_total: number;
}

interface PaginationMeta {
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
}

type ReportTab = "sales-invoices" | "purchase-invoices" | "hsn-sales" | "hsn-purchases";

// ── Helpers ──────────────────────────────────────────────────────────

const formatINR = (val: number | string | null | undefined): string => {
  if (val === null || val === undefined || val === "") return "0.00";
  const num = Number(val);
  if (isNaN(num)) return "0.00";
  return num.toLocaleString("en-IN", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
};

const formatDate = (dateStr: string | null | undefined): string => {
  if (!dateStr) return "-";
  try {
    const d = new Date(dateStr);
    if (isNaN(d.getTime())) return dateStr;
    return d.toLocaleDateString("en-IN", {
      day: "2-digit",
      month: "short",
      year: "numeric",
    });
  } catch {
    return dateStr;
  }
};

export default function AccountsReportsPage() {
  const { token, isAuthenticated } = useStaffAuth();

  // Companies State
  const [companies, setCompanies] = useState<Company[]>([]);
  const [selectedCompanyId, setSelectedCompanyId] = useState<string>("");
  const [loadingCompanies, setLoadingCompanies] = useState<boolean>(true);

  // Active Report Tab
  const [activeTab, setActiveTab] = useState<ReportTab>("sales-invoices");

  // Filters State
  const [dateFrom, setDateFrom] = useState<string>("");
  const [dateTo, setDateTo] = useState<string>("");
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [activePreset, setActivePreset] = useState<string>("month");

  // Report Data State
  const [invoices, setInvoices] = useState<InvoiceRecord[]>([]);
  const [hsnData, setHsnData] = useState<HSNRecord[]>([]);
  const [summary, setSummary] = useState<ReportSummary>({
    total_invoices: 0,
    total_taxable: 0,
    total_cgst: 0,
    total_sgst: 0,
    total_igst: 0,
    total_tax: 0,
    grand_total: 0,
  });
  const [pagination, setPagination] = useState<PaginationMeta>({
    page: 1,
    page_size: 50,
    total: 0,
    total_pages: 1,
  });

  // UI / Async State
  const [loading, setLoading] = useState<boolean>(false);
  const [copiedText, setCopiedText] = useState<string | null>(null);
  const [selectedInvoice, setSelectedInvoice] = useState<InvoiceRecord | null>(null);
  const [isDetailOpen, setIsDetailOpen] = useState<boolean>(false);

  // Sorting
  const [sortField, setSortField] = useState<string>("invoice_date");
  const [sortAsc, setSortAsc] = useState<boolean>(false);

  // ── Preset Date Handlers ───────────────────────────────────────────
  const applyDatePreset = useCallback((preset: string) => {
    setActivePreset(preset);
    const today = new Date();
    const toIso = (d: Date) => d.toISOString().split("T")[0];
    const endOfMonth = (d: Date) => new Date(d.getFullYear(), d.getMonth() + 1, 0);

    if (preset === "today") {
      setDateFrom(toIso(today));
      setDateTo(toIso(today));
    } else if (preset === "month") {
      setDateFrom(toIso(new Date(today.getFullYear(), today.getMonth(), 1)));
      setDateTo(toIso(today));
    } else if (preset === "last_month") {
      const prevMonth = new Date(today.getFullYear(), today.getMonth() - 1, 1);
      setDateFrom(toIso(prevMonth));
      setDateTo(toIso(endOfMonth(prevMonth)));
    } else if (preset === "quarter") {
      const qStartMonth = Math.floor(today.getMonth() / 3) * 3;
      setDateFrom(toIso(new Date(today.getFullYear(), qStartMonth, 1)));
      setDateTo(toIso(today));
    } else if (preset === "fy") {
      const m = today.getMonth();
      const fyStartYear = m >= 3 ? today.getFullYear() : today.getFullYear() - 1;
      setDateFrom(toIso(new Date(fyStartYear, 3, 1)));
      setDateTo(toIso(today));
    } else if (preset === "all") {
      setDateFrom("");
      setDateTo(toIso(today));
    }
  }, []);

  // ── Load Companies on Mount ────────────────────────────────────────
  useEffect(() => {
    const fetchCompanies = async () => {
      setLoadingCompanies(true);
      try {
        const res = await api.get("/staff/accounts/companies?page_size=100");
        const list: Company[] =
          res.data?.companies || res.data?.items || (Array.isArray(res.data) ? res.data : []);
        const activeList = list.filter((c) => c.is_active !== false);
        setCompanies(activeList);

        if (activeList.length > 0) {
          // Default to company 20 if available, else first active
          const co20 = activeList.find((c) => Number(c.id) === 20);
          setSelectedCompanyId(String(co20 ? co20.id : activeList[0].id));
        }
      } catch (err: any) {
        console.error("Failed to load companies:", err);
        toast.error("Failed to load companies for accounts reports.");
      } finally {
        setLoadingCompanies(false);
      }
    };

    fetchCompanies();
    applyDatePreset("month");
  }, [applyDatePreset]);

  // ── Fetch Report Data ──────────────────────────────────────────────
  const fetchReport = useCallback(
    async (targetPage: number = 1) => {
      if (!selectedCompanyId) {
        setInvoices([]);
        setHsnData([]);
        setSummary({
          total_invoices: 0,
          total_taxable: 0,
          total_cgst: 0,
          total_sgst: 0,
          total_igst: 0,
          total_tax: 0,
          grand_total: 0,
        });
        return;
      }

      setLoading(true);
      try {
        const isHsn = activeTab.startsWith("hsn");
        const params: Record<string, string | number> = {
          company_id: selectedCompanyId,
        };

        if (dateFrom) params.date_from = dateFrom;
        if (dateTo) params.date_to = dateTo;

        if (!isHsn) {
          if (statusFilter) params.status = statusFilter;
          params.page = targetPage;
          params.page_size = pagination.page_size;
        }

        const endpoint = `/staff/accounts/reports/${activeTab}`;
        const res = await api.get(endpoint, { params });
        const data = res.data || {};

        if (isHsn) {
          setHsnData(data.hsn_data || []);
          setInvoices([]);
          setSummary(
            data.summary || {
              total_taxable: 0,
              total_cgst: 0,
              total_sgst: 0,
              total_igst: 0,
              total_tax: 0,
              grand_total: 0,
            }
          );
        } else {
          setInvoices(data.invoices || []);
          setHsnData([]);
          setSummary(
            data.summary || {
              total_invoices: 0,
              total_taxable: 0,
              total_cgst: 0,
              total_sgst: 0,
              total_igst: 0,
              total_tax: 0,
              grand_total: 0,
            }
          );
          if (data.pagination) {
            setPagination({
              page: data.pagination.page || targetPage,
              page_size: data.pagination.page_size || 50,
              total: data.pagination.total || 0,
              total_pages: data.pagination.total_pages || 1,
            });
          }
        }
      } catch (err: any) {
        console.error("Report fetch error:", err);
        const msg =
          err.response?.data?.detail ||
          err.response?.data?.message ||
          err.message ||
          "Failed to load report data";
        toast.error(msg);
      } finally {
        setLoading(false);
      }
    },
    [selectedCompanyId, activeTab, dateFrom, dateTo, statusFilter, pagination.page_size]
  );

  // Trigger report fetch on dependencies change
  useEffect(() => {
    if (selectedCompanyId) {
      fetchReport(1);
    }
  }, [selectedCompanyId, activeTab, statusFilter, dateFrom, dateTo, fetchReport]);

  // ── Selected Company Object ────────────────────────────────────────
  const currentCompany = useMemo(() => {
    return companies.find((c) => String(c.id) === String(selectedCompanyId));
  }, [companies, selectedCompanyId]);

  // ── Filtered & Sorted Invoices ─────────────────────────────────────
  const displayedInvoices = useMemo(() => {
    let list = [...invoices];
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase().trim();
      list = list.filter(
        (inv) =>
          inv.invoice_number?.toLowerCase().includes(q) ||
          inv.customer_name?.toLowerCase().includes(q) ||
          inv.vendor_name?.toLowerCase().includes(q) ||
          inv.status?.toLowerCase().includes(q)
      );
    }

    list.sort((a, b) => {
      let valA: any = (a as any)[sortField];
      let valB: any = (b as any)[sortField];

      if (typeof valA === "string") valA = valA.toLowerCase();
      if (typeof valB === "string") valB = valB.toLowerCase();

      if (valA < valB) return sortAsc ? -1 : 1;
      if (valA > valB) return sortAsc ? 1 : -1;
      return 0;
    });

    return list;
  }, [invoices, searchQuery, sortField, sortAsc]);

  // ── Filtered & Sorted HSN Data ─────────────────────────────────────
  const displayedHsnData = useMemo(() => {
    let list = [...hsnData];
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase().trim();
      list = list.filter(
        (item) =>
          item.hsn_code?.toLowerCase().includes(q) ||
          item.description?.toLowerCase().includes(q)
      );
    }
    return list;
  }, [hsnData, searchQuery]);

  // ── Copy to Clipboard ──────────────────────────────────────────────
  const handleCopy = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedText(text);
    toast.success(`Copied: ${text}`);
    setTimeout(() => setCopiedText(null), 2000);
  };

  // ── Status Badge Styler ────────────────────────────────────
  const renderStatusBadge = (status: string) => {
    const s = (status || "PENDING").toUpperCase();
    switch (s) {
      case "CONFIRMED":
      case "PAID":
        return (
          <Badge className="bg-emerald-50 text-emerald-700 border-emerald-200 hover:bg-emerald-100 flex items-center gap-1">
            <CheckCircle2 className="w-3 h-3" />
            <span>{s}</span>
          </Badge>
        );
      case "PENDING":
      case "REVIEWED":
      case "EXTRACTED":
      case "UPLOADED":
        return (
          <Badge className="bg-amber-50 text-amber-700 border-amber-200 hover:bg-amber-100 flex items-center gap-1">
            <Clock className="w-3 h-3" />
            <span>{s}</span>
          </Badge>
        );
      case "DRAFT":
        return (
          <Badge className="bg-slate-100 text-slate-700 border-slate-200 hover:bg-slate-200 flex items-center gap-1">
            <FileEdit className="w-3 h-3" />
            <span>{s}</span>
          </Badge>
        );
      case "CANCELLED":
        return (
          <Badge className="bg-rose-50 text-rose-700 border-rose-200 hover:bg-rose-100 flex items-center gap-1">
            <XCircle className="w-3 h-3" />
            <span>{s}</span>
          </Badge>
        );
      default:
        return (
          <Badge variant="outline" className="text-gray-700">
            {s}
          </Badge>
        );
    }
  };

  // ── Export CSV Handler ─────────────────────────────────────────────
  const exportCSV = () => {
    const isHsn = activeTab.startsWith("hsn");
    const dataToExport = isHsn ? displayedHsnData : displayedInvoices;

    if (!dataToExport || dataToExport.length === 0) {
      toast.error("No data available to export.");
      return;
    }

    let csvContent = "";
    if (isHsn) {
      const headers = [
        "HSN/SAC Code",
        "Description",
        "Quantity",
        "Taxable Value (INR)",
        "CGST Rate (%)",
        "CGST Amount (INR)",
        "SGST Rate (%)",
        "SGST Amount (INR)",
        "IGST Rate (%)",
        "IGST Amount (INR)",
        "Total Tax (INR)",
        "Total Value (INR)",
      ];
      csvContent += headers.join(",") + "\n";

      displayedHsnData.forEach((row) => {
        const cleanDesc = `"${(row.description || "").replace(/"/g, '""')}"`;
        const line = [
          `"${row.hsn_code}"`,
          cleanDesc,
          row.quantity || 0,
          row.taxable_value || 0,
          row.cgst_rate || 0,
          row.cgst_amount || 0,
          row.sgst_rate || 0,
          row.sgst_amount || 0,
          row.igst_rate || 0,
          row.igst_amount || 0,
          row.total_tax || 0,
          row.total_value || 0,
        ];
        csvContent += line.join(",") + "\n";
      });
    } else {
      const isSales = activeTab === "sales-invoices";
      const headers = [
        "Invoice Number",
        "Invoice Date",
        isSales ? "Customer Name" : "Vendor Name",
        isSales ? "Customer Type" : "Vendor GSTIN",
        "Status",
        "Taxable Amount (INR)",
        "CGST (INR)",
        "SGST (INR)",
        "IGST (INR)",
        "Total Tax (INR)",
        "Grand Total (INR)",
      ];
      csvContent += headers.join(",") + "\n";

      displayedInvoices.forEach((row) => {
        const partyName = `"${(isSales ? row.customer_name : row.vendor_name || "").replace(/"/g, '""')}"`;
        const partySub = `"${(isSales ? row.customer_type : row.vendor_gstin || "").replace(/"/g, '""')}"`;
        const line = [
          `"${row.invoice_number || ""}"`,
          `"${row.invoice_date || ""}"`,
          partyName,
          partySub,
          `"${row.status || ""}"`,
          row.taxable_amount || 0,
          row.cgst_amount || 0,
          row.sgst_amount || 0,
          row.igst_amount || 0,
          row.total_tax || 0,
          row.grand_total || 0,
        ];
        csvContent += line.join(",") + "\n";
      });
    }

    const coName = (currentCompany?.company_name || currentCompany?.name || "Company").replace(/\s+/g, "_");
    const filename = `${activeTab}_${coName}_${new Date().toISOString().split("T")[0]}.csv`;

    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
    toast.success("CSV export downloaded successfully!");
  };

  // ── Export Excel Handler ───────────────────────────────────────────
  const exportExcel = () => {
    const isHsn = activeTab.startsWith("hsn");
    const dataToExport = isHsn ? displayedHsnData : displayedInvoices;

    if (!dataToExport || dataToExport.length === 0) {
      toast.error("No data available to export.");
      return;
    }

    let tableHtml = `
      <html xmlns:o="urn:schemas-microsoft-com:office:office" xmlns:x="urn:schemas-microsoft-com:office:excel" xmlns="http://www.w3.org/TR/REC-html40">
      <head>
        <!--[if gte mso 9]><xml><x:ExcelWorkbook><x:ExcelWorksheets><x:ExcelWorksheet><x:Name>Report</x:Name><x:WorksheetOptions><x:DisplayGridlines/></x:WorksheetOptions></x:ExcelWorksheet></x:ExcelWorksheets></x:ExcelWorkbook></xml><![endif]-->
        <meta http-equiv="content-type" content="text/plain; charset=UTF-8"/>
        <style>
          table { border-collapse: collapse; width: 100%; font-family: Calibri, sans-serif; }
          th { background-color: #1e3a8a; color: #ffffff; font-weight: bold; border: 1px solid #94a3b8; padding: 8px; text-align: left; }
          td { border: 1px solid #cbd5e1; padding: 6px 8px; }
          .num { text-align: right; }
          .center { text-align: center; }
          .total { background-color: #e2e8f0; font-weight: bold; }
        </style>
      </head>
      <body>
        <h3>${currentCompany?.company_name || currentCompany?.name || "Company"} - ${activeTab.toUpperCase().replace("-", " ")}</h3>
        <p>Generated: ${new Date().toLocaleString("en-IN")} | Period: ${dateFrom || "All"} to ${dateTo || "Today"}</p>
        <table>
          <thead>
            <tr>
    `;

    if (isHsn) {
      tableHtml += `
        <th>HSN/SAC Code</th>
        <th>Description</th>
        <th class="num">Quantity</th>
        <th class="num">Taxable Value</th>
        <th class="center">CGST Rate</th>
        <th class="num">CGST Amount</th>
        <th class="center">SGST Rate</th>
        <th class="num">SGST Amount</th>
        <th class="num">IGST Amount</th>
        <th class="num">Total Tax</th>
        <th class="num">Total Value</th>
      </tr></thead><tbody>
      `;

      displayedHsnData.forEach((r) => {
        tableHtml += `
          <tr>
            <td>${r.hsn_code}</td>
            <td>${r.description || ""}</td>
            <td class="num">${r.quantity || 0}</td>
            <td class="num">${formatINR(r.taxable_value)}</td>
            <td class="center">${r.cgst_rate}%</td>
            <td class="num">${formatINR(r.cgst_amount)}</td>
            <td class="center">${r.sgst_rate}%</td>
            <td class="num">${formatINR(r.sgst_amount)}</td>
            <td class="num">${formatINR(r.igst_amount)}</td>
            <td class="num">${formatINR(r.total_tax)}</td>
            <td class="num">${formatINR(r.total_value)}</td>
          </tr>
        `;
      });

      tableHtml += `
        </tbody>
        <tfoot>
          <tr class="total">
            <td colspan="3">Total</td>
            <td class="num">${formatINR(summary.total_taxable)}</td>
            <td class="center">-</td>
            <td class="num">${formatINR(summary.total_cgst)}</td>
            <td class="center">-</td>
            <td class="num">${formatINR(summary.total_sgst)}</td>
            <td class="num">${formatINR(summary.total_igst)}</td>
            <td class="num">${formatINR(summary.total_tax)}</td>
            <td class="num">${formatINR(summary.grand_total)}</td>
          </tr>
        </tfoot>
      `;
    } else {
      const isSales = activeTab === "sales-invoices";
      tableHtml += `
        <th>Invoice #</th>
        <th>Date</th>
        <th>${isSales ? "Customer Name" : "Vendor Name"}</th>
        <th class="center">Status</th>
        <th class="num">Taxable Amount</th>
        <th class="num">CGST</th>
        <th class="num">SGST</th>
        <th class="num">IGST</th>
        <th class="num">Total Tax</th>
        <th class="num">Grand Total</th>
      </tr></thead><tbody>
      `;

      displayedInvoices.forEach((r) => {
        tableHtml += `
          <tr>
            <td>${r.invoice_number}</td>
            <td>${formatDate(r.invoice_date)}</td>
            <td>${isSales ? r.customer_name || "" : r.vendor_name || ""}</td>
            <td class="center">${r.status || "PENDING"}</td>
            <td class="num">${formatINR(r.taxable_amount)}</td>
            <td class="num">${formatINR(r.cgst_amount)}</td>
            <td class="num">${formatINR(r.sgst_amount)}</td>
            <td class="num">${formatINR(r.igst_amount)}</td>
            <td class="num">${formatINR(r.total_tax)}</td>
            <td class="num">${formatINR(r.grand_total)}</td>
          </tr>
        `;
      });

      tableHtml += `
        </tbody>
        <tfoot>
          <tr class="total">
            <td colspan="4">Total (${summary.total_invoices || displayedInvoices.length} Invoices)</td>
            <td class="num">${formatINR(summary.total_taxable)}</td>
            <td class="num">${formatINR(summary.total_cgst)}</td>
            <td class="num">${formatINR(summary.total_sgst)}</td>
            <td class="num">${formatINR(summary.total_igst)}</td>
            <td class="num">${formatINR(summary.total_tax)}</td>
            <td class="num">${formatINR(summary.grand_total)}</td>
          </tr>
        </tfoot>
      `;
    }

    tableHtml += `</table></body></html>`;

    const coName = (currentCompany?.company_name || currentCompany?.name || "Company").replace(/\s+/g, "_");
    const filename = `${activeTab}_${coName}_${new Date().toISOString().split("T")[0]}.xls`;

    const blob = new Blob([tableHtml], { type: "application/vnd.ms-excel;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
    toast.success("Excel report exported successfully!");
  };

  // ── Print Handler ──────────────────────────────────────────────────
  const handlePrint = () => {
    window.print();
  };

  // ── Tab Title & Subtitle Resolver ──────────────────────────────────
  const getTabDetails = (tab: ReportTab) => {
    switch (tab) {
      case "sales-invoices":
        return {
          title: "Sales Invoices Report",
          description: "Detailed customer invoices, sales tax, CGST/SGST/IGST breakdown and payment statuses.",
          icon: Receipt,
        };
      case "purchase-invoices":
        return {
          title: "Purchase Invoices Report",
          description: "Vendor procurement invoices, input tax credit (ITC) tax distributions, and verification logs.",
          icon: FileText,
        };
      case "hsn-sales":
        return {
          title: "HSN Code-wise Sales Summary",
          description: "Aggregated outward supply turnover classified by Harmonized System Nomenclature (HSN/SAC).",
          icon: Hash,
        };
      case "hsn-purchases":
        return {
          title: "HSN Code-wise Purchase Summary",
          description: "Aggregated inward supply procurement categorized by HSN/SAC codes and GST rate tiers.",
          icon: Layers,
        };
    }
  };

  const currentTabMeta = getTabDetails(activeTab);

  return (
    <div className="min-h-screen bg-slate-50/50 p-4 sm:p-6 lg:p-8 max-w-7xl mx-auto space-y-6">
      <Toaster position="top-right" />

      {/* Top Breadcrumb & Page Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-gray-200 pb-5">
        <div>
          <div className="flex items-center gap-2 text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1.5">
            <Link
              href="/staff/accounts"
              className="hover:text-blue-600 transition-colors flex items-center gap-1 text-gray-600"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              Accounts Dashboard
            </Link>
            <span>/</span>
            <span className="text-blue-600">Reports</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-gray-900 tracking-tight flex items-center gap-2.5">
            <span className="p-2 rounded-xl bg-gradient-to-br from-blue-600 to-indigo-700 text-white shadow-sm">
              <FileSpreadsheet className="w-6 h-6" />
            </span>
            SFMS Financial &amp; Invoice Reports
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            Company-wise sales, purchase registers, HSN code breakdowns, and GST audit schedules with strict data segregation.
          </p>
        </div>

        {/* Global Action Buttons */}
        <div className="flex items-center gap-2.5 flex-wrap">
          <Button
            variant="outline"
            size="sm"
            onClick={() => fetchReport(pagination.page)}
            disabled={loading || !selectedCompanyId}
            className="border-gray-200 text-gray-700 hover:bg-gray-100 flex items-center gap-1.5 shadow-2xs"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin text-blue-600" : ""}`} />
            <span>Refresh</span>
          </Button>

          <Button
            variant="outline"
            size="sm"
            onClick={handlePrint}
            className="border-gray-200 text-gray-700 hover:bg-gray-100 flex items-center gap-1.5 shadow-2xs"
          >
            <Printer className="w-4 h-4 text-slate-600" />
            <span className="hidden sm:inline">Print</span>
          </Button>

          <Button
            variant="outline"
            size="sm"
            onClick={exportCSV}
            disabled={loading || (!invoices.length && !hsnData.length)}
            className="border-emerald-200 text-emerald-700 hover:bg-emerald-50 flex items-center gap-1.5 shadow-2xs"
          >
            <Download className="w-4 h-4 text-emerald-600" />
            <span>CSV</span>
          </Button>

          <Button
            size="sm"
            onClick={exportExcel}
            disabled={loading || (!invoices.length && !hsnData.length)}
            className="bg-emerald-600 hover:bg-emerald-700 text-white shadow-xs font-semibold flex items-center gap-1.5"
          >
            <FileSpreadsheet className="w-4 h-4" />
            <span>Excel (.xls)</span>
          </Button>
        </div>
      </div>

      {/* Company Selection & Filters Card */}
      <div className="bg-white rounded-2xl border border-gray-200 p-5 shadow-xs space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-12 gap-4 items-end">
          {/* Company Filter (Mandatory) */}
          <div className="md:col-span-4 space-y-1.5">
            <Label className="text-xs font-bold text-gray-700 flex items-center justify-between">
              <span className="flex items-center gap-1.5">
                <Building2 className="w-4 h-4 text-blue-600" />
                Company (Mandatory)
              </span>
              {currentCompany && (
                <span className="text-[11px] font-normal text-emerald-600 font-mono">
                  {currentCompany.gstin || currentCompany.gst_number || "Active"}
                </span>
              )}
            </Label>
            <select
              value={selectedCompanyId}
              onChange={(e) => setSelectedCompanyId(e.target.value)}
              className="w-full h-10 px-3 py-2 bg-gray-50/70 border border-gray-300 rounded-xl text-sm font-medium text-gray-900 focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-600 transition-all shadow-2xs"
            >
              <option value="">-- Select Company --</option>
              {companies.map((co) => (
                <option key={co.id} value={co.id}>
                  {co.company_name || co.name || `Company #${co.id}`}
                </option>
              ))}
            </select>
          </div>

          {/* Date From */}
          <div className="md:col-span-3 space-y-1.5">
            <Label className="text-xs font-bold text-gray-700 flex items-center gap-1.5">
              <Calendar className="w-3.5 h-3.5 text-slate-500" />
              From Date
            </Label>
            <Input
              type="date"
              value={dateFrom}
              onChange={(e) => {
                setDateFrom(e.target.value);
                setActivePreset("custom");
              }}
              className="h-10 bg-gray-50/70 border-gray-300 rounded-xl text-sm focus:bg-white focus-visible:ring-blue-500/20"
            />
          </div>

          {/* Date To */}
          <div className="md:col-span-3 space-y-1.5">
            <Label className="text-xs font-bold text-gray-700 flex items-center gap-1.5">
              <Calendar className="w-3.5 h-3.5 text-slate-500" />
              To Date
            </Label>
            <Input
              type="date"
              value={dateTo}
              onChange={(e) => {
                setDateTo(e.target.value);
                setActivePreset("custom");
              }}
              className="h-10 bg-gray-50/70 border-gray-300 rounded-xl text-sm focus:bg-white focus-visible:ring-blue-500/20"
            />
          </div>

          {/* Status Filter (Invoice only) */}
          <div className="md:col-span-2 space-y-1.5">
            <Label className="text-xs font-bold text-gray-700 flex items-center gap-1.5">
              <Filter className="w-3.5 h-3.5 text-slate-500" />
              Status
            </Label>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              disabled={activeTab.startsWith("hsn")}
              className="w-full h-10 px-3 py-2 bg-gray-50/70 border border-gray-300 rounded-xl text-sm font-medium text-gray-900 focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-600 transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-2xs"
            >
              <option value="">All Statuses</option>
              <option value="CONFIRMED">Confirmed</option>
              <option value="PENDING">Pending / Review</option>
              <option value="DRAFT">Draft</option>
              <option value="CANCELLED">Cancelled</option>
            </select>
          </div>
        </div>

        {/* Date Quick Presets & Search */}
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 pt-3 border-t border-gray-100">
          <div className="flex items-center gap-1.5 flex-wrap">
            <span className="text-xs font-medium text-gray-500 mr-1">Period Presets:</span>
            {[
              { id: "today", label: "Today" },
              { id: "month", label: "This Month" },
              { id: "last_month", label: "Last Month" },
              { id: "quarter", label: "This Quarter" },
              { id: "fy", label: "Financial Year" },
              { id: "all", label: "All Time" },
            ].map((p) => (
              <button
                key={p.id}
                type="button"
                onClick={() => applyDatePreset(p.id)}
                className={`px-2.5 py-1 rounded-lg text-xs font-medium transition-all ${
                  activePreset === p.id
                    ? "bg-blue-600 text-white shadow-2xs font-semibold"
                    : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                }`}
              >
                {p.label}
              </button>
            ))}
          </div>

          {/* Table Search */}
          <div className="relative w-full sm:w-72">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <Input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search in table..."
              className="h-9 pl-9 pr-4 bg-gray-50/70 border-gray-200 rounded-lg text-xs focus-visible:ring-blue-500/20"
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery("")}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 text-xs"
              >
                ×
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Report Switcher Tabs */}
      <div className="flex items-center gap-2 p-1.5 bg-gray-200/70 rounded-2xl border border-gray-200 overflow-x-auto shadow-2xs">
        {[
          { id: "sales-invoices", label: "Sales Invoices", icon: Receipt },
          { id: "purchase-invoices", label: "Purchase Invoices", icon: FileText },
          { id: "hsn-sales", label: "HSN-wise Sales", icon: Hash },
          { id: "hsn-purchases", label: "HSN-wise Purchases", icon: Layers },
        ].map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as ReportTab)}
              className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-semibold whitespace-nowrap transition-all ${
                isActive
                  ? "bg-white text-blue-700 shadow-sm border border-gray-200/80"
                  : "text-gray-600 hover:text-gray-900 hover:bg-gray-100/60"
              }`}
            >
              <Icon className={`w-4 h-4 ${isActive ? "text-blue-600" : "text-gray-400"}`} />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </div>

      {/* Mandatory Company Selection State */}
      {!selectedCompanyId ? (
        <div className="bg-white rounded-2xl border border-dashed border-gray-300 p-12 text-center shadow-xs">
          <div className="w-16 h-16 bg-blue-50 text-blue-600 rounded-2xl flex items-center justify-center mx-auto mb-4 border border-blue-100">
            <Building2 className="w-8 h-8" />
          </div>
          <h3 className="text-lg font-bold text-gray-900">Select a Company</h3>
          <p className="text-sm text-gray-500 max-w-md mx-auto mt-1">
            Under DC Protocol, company selection is required to segregate multi-entity accounting ledgers and GST statements.
          </p>
          <div className="mt-5 flex justify-center gap-2 flex-wrap">
            {companies.slice(0, 3).map((c) => (
              <Button
                key={c.id}
                variant="outline"
                size="sm"
                onClick={() => setSelectedCompanyId(String(c.id))}
                className="border-gray-300"
              >
                {c.company_name || c.name}
              </Button>
            ))}
          </div>
        </div>
      ) : (
        <>
          {/* Summary KPI Cards Grid */}
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 sm:gap-4">
            {/* Total Count / Taxable */}
            <div className="bg-white rounded-2xl border border-gray-200 p-4 shadow-xs hover:shadow-md transition-all">
              <div className="flex items-center justify-between text-gray-500 text-xs font-semibold uppercase">
                <span>{activeTab.startsWith("hsn") ? "HSN Items" : "Total Invoices"}</span>
                <Receipt className="w-4 h-4 text-blue-600" />
              </div>
              <div className="mt-2 flex items-baseline justify-between">
                <span className="text-2xl font-bold text-gray-900 font-mono">
                  {loading
                    ? "..."
                    : activeTab.startsWith("hsn")
                    ? hsnData.length
                    : summary.total_invoices ?? invoices.length}
                </span>
                <span className="text-[10px] font-semibold text-blue-700 bg-blue-50 px-2 py-0.5 rounded-full">
                  Count
                </span>
              </div>
            </div>

            {/* Taxable Amount */}
            <div className="bg-white rounded-2xl border border-indigo-100 p-4 shadow-xs hover:shadow-md transition-all border-l-4 border-l-indigo-600">
              <div className="flex items-center justify-between text-indigo-700 text-xs font-semibold uppercase">
                <span>Taxable Value</span>
                <Percent className="w-4 h-4 text-indigo-600" />
              </div>
              <div className="mt-2 flex items-baseline justify-between">
                <span className="text-xl sm:text-2xl font-bold text-indigo-950 font-mono">
                  ₹{loading ? "..." : formatINR(summary.total_taxable)}
                </span>
              </div>
            </div>

            {/* CGST */}
            <div className="bg-white rounded-2xl border border-emerald-100 p-4 shadow-xs hover:shadow-md transition-all border-l-4 border-l-emerald-600">
              <div className="flex items-center justify-between text-emerald-700 text-xs font-semibold uppercase">
                <span>Total CGST</span>
                <span className="text-[10px] text-emerald-600 font-mono">Central</span>
              </div>
              <div className="mt-2 flex items-baseline justify-between">
                <span className="text-xl sm:text-2xl font-bold text-emerald-950 font-mono">
                  ₹{loading ? "..." : formatINR(summary.total_cgst)}
                </span>
              </div>
            </div>

            {/* SGST */}
            <div className="bg-white rounded-2xl border border-amber-100 p-4 shadow-xs hover:shadow-md transition-all border-l-4 border-l-amber-500">
              <div className="flex items-center justify-between text-amber-700 text-xs font-semibold uppercase">
                <span>Total SGST</span>
                <span className="text-[10px] text-amber-600 font-mono">State</span>
              </div>
              <div className="mt-2 flex items-baseline justify-between">
                <span className="text-xl sm:text-2xl font-bold text-amber-950 font-mono">
                  ₹{loading ? "..." : formatINR(summary.total_sgst)}
                </span>
              </div>
            </div>

            {/* IGST */}
            <div className="bg-white rounded-2xl border border-rose-100 p-4 shadow-xs hover:shadow-md transition-all border-l-4 border-l-rose-500">
              <div className="flex items-center justify-between text-rose-700 text-xs font-semibold uppercase">
                <span>Total IGST</span>
                <span className="text-[10px] text-rose-600 font-mono">Integrated</span>
              </div>
              <div className="mt-2 flex items-baseline justify-between">
                <span className="text-xl sm:text-2xl font-bold text-rose-950 font-mono">
                  ₹{loading ? "..." : formatINR(summary.total_igst)}
                </span>
              </div>
            </div>

            {/* Grand Total */}
            <div className="bg-gradient-to-br from-blue-700 to-indigo-900 rounded-2xl p-4 shadow-md text-white border border-blue-800">
              <div className="flex items-center justify-between text-blue-200 text-xs font-semibold uppercase">
                <span>Grand Total</span>
                <Sparkles className="w-4 h-4 text-amber-300" />
              </div>
              <div className="mt-2 flex items-baseline justify-between">
                <span className="text-xl sm:text-2xl font-black text-white font-mono">
                  ₹{loading ? "..." : formatINR(summary.grand_total)}
                </span>
              </div>
            </div>
          </div>

          {/* Main Data Section Card */}
          <div className="bg-white rounded-2xl border border-gray-200 shadow-xs overflow-hidden">
            {/* Table Header & Controls */}
            <div className="p-4 sm:p-5 border-b border-gray-200 flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-gray-50/50">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-blue-100/70 text-blue-700 flex items-center justify-center font-bold">
                  <currentTabMeta.icon className="w-5 h-5" />
                </div>
                <div>
                  <h2 className="text-base font-bold text-gray-900">{currentTabMeta.title}</h2>
                  <p className="text-xs text-gray-500">{currentTabMeta.description}</p>
                </div>
              </div>

              <div className="flex items-center gap-2 text-xs font-medium text-gray-600">
                <span className="bg-white px-3 py-1 rounded-lg border border-gray-200 shadow-2xs">
                  {currentCompany?.company_name || currentCompany?.name}
                </span>
                <span className="bg-blue-50 text-blue-700 px-3 py-1 rounded-lg border border-blue-200 font-mono">
                  {dateFrom || "Start"} → {dateTo || "Today"}
                </span>
              </div>
            </div>

            {/* Table Container */}
            {loading ? (
              <div className="p-16 text-center text-gray-500 space-y-3">
                <RefreshCw className="w-8 h-8 animate-spin text-blue-600 mx-auto" />
                <p className="text-sm font-medium">Loading report records...</p>
              </div>
            ) : activeTab.startsWith("hsn") ? (
              /* ── HSN TABLE VIEW ── */
              displayedHsnData.length === 0 ? (
                <div className="p-16 text-center text-gray-500 space-y-3">
                  <Hash className="w-12 h-12 text-gray-300 mx-auto" />
                  <h4 className="text-base font-bold text-gray-800">No HSN Data Found</h4>
                  <p className="text-xs text-gray-500 max-w-sm mx-auto">
                    No confirmed invoices with HSN codes exist for the chosen company and date range.
                  </p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-left border-collapse text-xs">
                    <thead>
                      <tr className="bg-slate-100/80 border-b border-gray-200 text-gray-700 font-bold uppercase tracking-wider">
                        <th className="py-3 px-4">HSN / SAC</th>
                        <th className="py-3 px-4">Description</th>
                        <th className="py-3 px-4 text-right">Quantity</th>
                        <th className="py-3 px-4 text-right">Taxable Value</th>
                        <th className="py-3 px-4 text-center">CGST</th>
                        <th className="py-3 px-4 text-center">SGST</th>
                        <th className="py-3 px-4 text-right">IGST Amount</th>
                        <th className="py-3 px-4 text-right">Total Tax</th>
                        <th className="py-3 px-4 text-right font-black">Total Value</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">
                      {displayedHsnData.map((row, idx) => (
                        <tr key={idx} className="hover:bg-blue-50/40 transition-colors">
                          <td className="py-3 px-4 font-mono font-bold text-blue-900">
                            <span className="inline-flex items-center px-2 py-0.5 rounded bg-blue-50 border border-blue-200">
                              {row.hsn_code}
                            </span>
                          </td>
                          <td className="py-3 px-4 font-medium text-gray-800 max-w-xs truncate">
                            {row.description || "—"}
                          </td>
                          <td className="py-3 px-4 text-right font-mono text-gray-700">
                            {row.quantity ? Number(row.quantity).toFixed(2) : "1.00"}
                          </td>
                          <td className="py-3 px-4 text-right font-mono font-semibold text-gray-900">
                            ₹{formatINR(row.taxable_value)}
                          </td>
                          <td className="py-3 px-4 text-center font-mono">
                            <span className="text-gray-500 text-[11px] mr-1">({row.cgst_rate}%)</span>
                            <span className="text-emerald-700 font-semibold">₹{formatINR(row.cgst_amount)}</span>
                          </td>
                          <td className="py-3 px-4 text-center font-mono">
                            <span className="text-gray-500 text-[11px] mr-1">({row.sgst_rate}%)</span>
                            <span className="text-amber-700 font-semibold">₹{formatINR(row.sgst_amount)}</span>
                          </td>
                          <td className="py-3 px-4 text-right font-mono font-semibold text-rose-700">
                            ₹{formatINR(row.igst_amount)}
                          </td>
                          <td className="py-3 px-4 text-right font-mono font-bold text-gray-900">
                            ₹{formatINR(row.total_tax)}
                          </td>
                          <td className="py-3 px-4 text-right font-mono font-black text-blue-900">
                            ₹{formatINR(row.total_value)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                    <tfoot>
                      <tr className="bg-slate-200/70 font-bold border-t-2 border-slate-300 text-gray-900 text-xs">
                        <td className="py-3 px-4" colSpan={3}>
                          Total ({displayedHsnData.length} HSN Codes)
                        </td>
                        <td className="py-3 px-4 text-right font-mono">₹{formatINR(summary.total_taxable)}</td>
                        <td className="py-3 px-4 text-center font-mono text-emerald-800">
                          ₹{formatINR(summary.total_cgst)}
                        </td>
                        <td className="py-3 px-4 text-center font-mono text-amber-800">
                          ₹{formatINR(summary.total_sgst)}
                        </td>
                        <td className="py-3 px-4 text-right font-mono text-rose-800">
                          ₹{formatINR(summary.total_igst)}
                        </td>
                        <td className="py-3 px-4 text-right font-mono text-purple-900">
                          ₹{formatINR(summary.total_tax)}
                        </td>
                        <td className="py-3 px-4 text-right font-mono font-black text-blue-950">
                          ₹{formatINR(summary.grand_total)}
                        </td>
                      </tr>
                    </tfoot>
                  </table>
                </div>
              )
            ) : (
              /* ── INVOICES TABLE VIEW (Sales / Purchase) ── */
              displayedInvoices.length === 0 ? (
                <div className="p-16 text-center text-gray-500 space-y-3">
                  <Receipt className="w-12 h-12 text-gray-300 mx-auto" />
                  <h4 className="text-base font-bold text-gray-800">No Invoices Found</h4>
                  <p className="text-xs text-gray-500 max-w-sm mx-auto">
                    No invoice transactions match the chosen filters or status for this period.
                  </p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-left border-collapse text-xs">
                    <thead>
                      <tr className="bg-slate-100/80 border-b border-gray-200 text-gray-700 font-bold uppercase tracking-wider">
                        <th
                          className="py-3 px-4 cursor-pointer hover:bg-slate-200/70"
                          onClick={() => {
                            if (sortField === "invoice_number") setSortAsc(!sortAsc);
                            else {
                              setSortField("invoice_number");
                              setSortAsc(true);
                            }
                          }}
                        >
                          Invoice #
                        </th>
                        <th
                          className="py-3 px-4 cursor-pointer hover:bg-slate-200/70"
                          onClick={() => {
                            if (sortField === "invoice_date") setSortAsc(!sortAsc);
                            else {
                              setSortField("invoice_date");
                              setSortAsc(true);
                            }
                          }}
                        >
                          Date
                        </th>
                        <th className="py-3 px-4">
                          {activeTab === "sales-invoices" ? "Customer" : "Vendor"}
                        </th>
                        <th className="py-3 px-4 text-center">Status</th>
                        <th className="py-3 px-4 text-right">Taxable</th>
                        <th className="py-3 px-4 text-right">CGST</th>
                        <th className="py-3 px-4 text-right">SGST</th>
                        <th className="py-3 px-4 text-right">IGST</th>
                        <th className="py-3 px-4 text-right">Total Tax</th>
                        <th className="py-3 px-4 text-right font-black">Grand Total</th>
                        <th className="py-3 px-4 text-center">Action</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">
                      {displayedInvoices.map((inv) => {
                        const isSales = activeTab === "sales-invoices";
                        const party = isSales ? inv.customer_name : inv.vendor_name;
                        const partySub = isSales ? inv.customer_type : inv.vendor_gstin;

                        return (
                          <tr key={inv.id} className="hover:bg-blue-50/40 transition-colors">
                            <td className="py-3 px-4 font-mono font-bold text-blue-900">
                              <div className="flex items-center gap-1.5">
                                <span>{inv.invoice_number || `INV-${inv.id}`}</span>
                                <button
                                  onClick={() => handleCopy(inv.invoice_number)}
                                  className="text-gray-400 hover:text-gray-700"
                                  title="Copy invoice number"
                                >
                                  {copiedText === inv.invoice_number ? (
                                    <Check className="w-3 h-3 text-emerald-600" />
                                  ) : (
                                    <Copy className="w-3 h-3" />
                                  )}
                                </button>
                              </div>
                            </td>
                            <td className="py-3 px-4 font-medium text-gray-600 whitespace-nowrap">
                              {formatDate(inv.invoice_date)}
                            </td>
                            <td className="py-3 px-4">
                              <div className="font-semibold text-gray-900">{party || "—"}</div>
                              {partySub && (
                                <div className="text-[11px] text-gray-500 font-mono">{partySub}</div>
                              )}
                            </td>
                            <td className="py-3 px-4 text-center">{renderStatusBadge(inv.status)}</td>
                            <td className="py-3 px-4 text-right font-mono font-medium text-gray-800">
                              ₹{formatINR(inv.taxable_amount)}
                            </td>
                            <td className="py-3 px-4 text-right font-mono text-emerald-700">
                              ₹{formatINR(inv.cgst_amount)}
                            </td>
                            <td className="py-3 px-4 text-right font-mono text-amber-700">
                              ₹{formatINR(inv.sgst_amount)}
                            </td>
                            <td className="py-3 px-4 text-right font-mono text-rose-700">
                              ₹{formatINR(inv.igst_amount)}
                            </td>
                            <td className="py-3 px-4 text-right font-mono font-bold text-gray-900">
                              ₹{formatINR(inv.total_tax)}
                            </td>
                            <td className="py-3 px-4 text-right font-mono font-black text-blue-950">
                              ₹{formatINR(inv.grand_total)}
                            </td>
                            <td className="py-3 px-4 text-center">
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => {
                                  setSelectedInvoice(inv);
                                  setIsDetailOpen(true);
                                }}
                                className="h-7 w-7 p-0 text-blue-600 hover:text-blue-800 hover:bg-blue-50"
                                title="View details"
                              >
                                <Eye className="w-3.5 h-3.5" />
                              </Button>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                    <tfoot>
                      <tr className="bg-slate-200/70 font-bold border-t-2 border-slate-300 text-gray-900 text-xs">
                        <td className="py-3 px-4" colSpan={4}>
                          Page Total ({displayedInvoices.length} Invoices)
                        </td>
                        <td className="py-3 px-4 text-right font-mono">₹{formatINR(summary.total_taxable)}</td>
                        <td className="py-3 px-4 text-right font-mono text-emerald-800">
                          ₹{formatINR(summary.total_cgst)}
                        </td>
                        <td className="py-3 px-4 text-right font-mono text-amber-800">
                          ₹{formatINR(summary.total_sgst)}
                        </td>
                        <td className="py-3 px-4 text-right font-mono text-rose-800">
                          ₹{formatINR(summary.total_igst)}
                        </td>
                        <td className="py-3 px-4 text-right font-mono text-purple-900">
                          ₹{formatINR(summary.total_tax)}
                        </td>
                        <td className="py-3 px-4 text-right font-mono font-black text-blue-950">
                          ₹{formatINR(summary.grand_total)}
                        </td>
                        <td></td>
                      </tr>
                    </tfoot>
                  </table>
                </div>
              )
            )}

            {/* Pagination Controls (Invoices only) */}
            {!activeTab.startsWith("hsn") && pagination.total_pages > 1 && (
              <div className="p-4 border-t border-gray-200 flex flex-col sm:flex-row items-center justify-between gap-3 bg-gray-50/50">
                <div className="text-xs text-gray-500 font-medium">
                  Showing {(pagination.page - 1) * pagination.page_size + 1} to{" "}
                  {Math.min(pagination.page * pagination.page_size, pagination.total)} of{" "}
                  {pagination.total} records
                </div>

                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => fetchReport(pagination.page - 1)}
                    disabled={pagination.page <= 1 || loading}
                    className="h-8 px-3 text-xs border-gray-300"
                  >
                    <ChevronLeft className="w-3.5 h-3.5 mr-1" />
                    Previous
                  </Button>

                  <span className="text-xs font-semibold text-gray-700 px-2">
                    Page {pagination.page} of {pagination.total_pages}
                  </span>

                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => fetchReport(pagination.page + 1)}
                    disabled={pagination.page >= pagination.total_pages || loading}
                    className="h-8 px-3 text-xs border-gray-300"
                  >
                    Next
                    <ChevronRight className="w-3.5 h-3.5 ml-1" />
                  </Button>
                </div>
              </div>
            )}
          </div>

          {/* HSN Tax Summary Section (Rate Tier Aggregator) */}
          {activeTab.startsWith("hsn") && displayedHsnData.length > 0 && (
            <div className="bg-white rounded-2xl border border-gray-200 p-5 shadow-xs space-y-4">
              <div className="flex items-center justify-between border-b border-gray-100 pb-3">
                <div className="flex items-center gap-2">
                  <ShieldCheck className="w-5 h-5 text-emerald-600" />
                  <h3 className="text-sm font-bold text-gray-900">
                    GST Rate-wise Summary Breakdown ({activeTab === "hsn-sales" ? "Sales" : "Purchases"})
                  </h3>
                </div>
                <Badge variant="outline" className="text-xs bg-emerald-50 text-emerald-800 border-emerald-200">
                  DC Protocol Verified
                </Badge>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-2">
                  <span className="text-xs font-semibold text-gray-600 uppercase">Intra-State Supply (CGST + SGST)</span>
                  <div className="flex justify-between items-baseline">
                    <span className="text-sm text-gray-500">Total Intra Tax:</span>
                    <span className="text-base font-bold text-emerald-700 font-mono">
                      ₹{formatINR(summary.total_cgst + summary.total_sgst)}
                    </span>
                  </div>
                  <div className="text-[11px] text-gray-400 flex justify-between">
                    <span>CGST: ₹{formatINR(summary.total_cgst)}</span>
                    <span>SGST: ₹{formatINR(summary.total_sgst)}</span>
                  </div>
                </div>

                <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-2">
                  <span className="text-xs font-semibold text-gray-600 uppercase">Inter-State Supply (IGST)</span>
                  <div className="flex justify-between items-baseline">
                    <span className="text-sm text-gray-500">Total IGST Tax:</span>
                    <span className="text-base font-bold text-rose-700 font-mono">
                      ₹{formatINR(summary.total_igst)}
                    </span>
                  </div>
                  <div className="text-[11px] text-gray-400 flex justify-between">
                    <span>Applicable across state borders</span>
                  </div>
                </div>

                <div className="p-4 rounded-xl bg-blue-50/70 border border-blue-200 space-y-2">
                  <span className="text-xs font-semibold text-blue-900 uppercase">Total Tax Liability / Credit</span>
                  <div className="flex justify-between items-baseline">
                    <span className="text-sm text-blue-700">Combined Tax:</span>
                    <span className="text-lg font-black text-blue-950 font-mono">
                      ₹{formatINR(summary.total_tax)}
                    </span>
                  </div>
                  <div className="text-[11px] text-blue-600 flex justify-between">
                    <span>On Taxable Value: ₹{formatINR(summary.total_taxable)}</span>
                  </div>
                </div>
              </div>
            </div>
          )}
        </>
      )}

      {/* Invoice Details Dialog Modal */}
      <Dialog open={isDetailOpen} onOpenChange={setIsDetailOpen}>
        <DialogContent className="sm:max-w-xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="text-lg font-bold flex items-center gap-2">
              <Receipt className="w-5 h-5 text-blue-600" />
              Invoice Details: {selectedInvoice?.invoice_number}
            </DialogTitle>
            <DialogDescription className="text-xs text-gray-500">
              Complete invoice breakdown and tax distribution record.
            </DialogDescription>
          </DialogHeader>

          {selectedInvoice && (
            <div className="space-y-4 py-2 text-xs">
              {/* Metadata Grid */}
              <div className="grid grid-cols-2 gap-3 bg-slate-50 p-3.5 rounded-xl border border-slate-200">
                <div>
                  <span className="text-gray-500 font-medium">Invoice Number:</span>
                  <p className="font-bold text-gray-900 font-mono mt-0.5">{selectedInvoice.invoice_number}</p>
                </div>
                <div>
                  <span className="text-gray-500 font-medium">Invoice Date:</span>
                  <p className="font-bold text-gray-900 mt-0.5">{formatDate(selectedInvoice.invoice_date)}</p>
                </div>
                <div>
                  <span className="text-gray-500 font-medium">Party Name:</span>
                  <p className="font-bold text-gray-900 mt-0.5">
                    {selectedInvoice.customer_name || selectedInvoice.vendor_name || "—"}
                  </p>
                </div>
                <div>
                  <span className="text-gray-500 font-medium">Status:</span>
                  <div className="mt-0.5">{renderStatusBadge(selectedInvoice.status)}</div>
                </div>
              </div>

              {/* Amount Breakdown Table */}
              <div className="border border-gray-200 rounded-xl overflow-hidden">
                <table className="w-full text-xs">
                  <tbody className="divide-y divide-gray-100">
                    <tr className="bg-gray-50/50">
                      <td className="py-2 px-3 text-gray-600 font-medium">Taxable Amount</td>
                      <td className="py-2 px-3 text-right font-mono font-semibold text-gray-900">
                        ₹{formatINR(selectedInvoice.taxable_amount)}
                      </td>
                    </tr>
                    <tr>
                      <td className="py-2 px-3 text-gray-600">Central GST (CGST)</td>
                      <td className="py-2 px-3 text-right font-mono text-emerald-700">
                        ₹{formatINR(selectedInvoice.cgst_amount)}
                      </td>
                    </tr>
                    <tr>
                      <td className="py-2 px-3 text-gray-600">State GST (SGST)</td>
                      <td className="py-2 px-3 text-right font-mono text-amber-700">
                        ₹{formatINR(selectedInvoice.sgst_amount)}
                      </td>
                    </tr>
                    <tr>
                      <td className="py-2 px-3 text-gray-600">Integrated GST (IGST)</td>
                      <td className="py-2 px-3 text-right font-mono text-rose-700">
                        ₹{formatINR(selectedInvoice.igst_amount)}
                      </td>
                    </tr>
                    <tr className="bg-slate-100/60 font-semibold">
                      <td className="py-2 px-3 text-gray-800">Total Tax Amount</td>
                      <td className="py-2 px-3 text-right font-mono text-purple-900">
                        ₹{formatINR(selectedInvoice.total_tax)}
                      </td>
                    </tr>
                    <tr className="bg-blue-50 font-bold text-sm">
                      <td className="py-2.5 px-3 text-blue-950">Grand Total</td>
                      <td className="py-2.5 px-3 text-right font-mono font-black text-blue-950">
                        ₹{formatINR(selectedInvoice.grand_total)}
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          )}

          <DialogFooter className="gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setIsDetailOpen(false)}
              className="text-xs"
            >
              Close
            </Button>
            <Button
              size="sm"
              onClick={() => {
                if (selectedInvoice) {
                  handleCopy(selectedInvoice.invoice_number);
                }
              }}
              className="bg-blue-600 hover:bg-blue-700 text-white text-xs"
            >
              Copy Invoice #
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

