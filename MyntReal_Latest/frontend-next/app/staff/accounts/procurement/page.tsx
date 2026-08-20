"use client";

import React, { useState, useEffect, useMemo } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import api from "@/lib/api";
import { useStaffAuth } from "@/contexts/StaffAuthContext";

import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";

import {
  FileText,
  Layers,
  ClipboardList,
  AlertTriangle,
  Boxes,
  Store,
  Plus,
  Search,
  RefreshCw,
  Download,
  Eye,
  Check,
  CheckCircle2,
  X,
  XCircle,
  Clock,
  Send,
  ShoppingCart,
  Trash2,
  ExternalLink,
  Edit,
  MessageCircle,
  FileSpreadsheet,
  FileCheck,
  ArrowRight,
  Info,
  RotateCcw,
} from "lucide-react";

// ── Types & Interfaces ──────────────────────────────────────────────────────────

interface Company {
  id: number;
  company_name: string;
  company_code?: string;
  gst_number?: string;
}

interface ProcurementRequestItem {
  id?: number;
  request_id?: number;
  item_id?: number;
  stock_item_id?: number;
  item_code?: string;
  stock_item_code?: string;
  item_name?: string;
  stock_item_name?: string;
  required_qty: number;
  unit_of_measure?: string;
  item_category?: string;
  category?: string;
  hsn_code?: string;
  brand?: string;
  model_compat?: string;
  colors?: string | string[];
  specification?: string;
  specifications?: string;
  source_type?: string;
  sl_no?: number;
}

interface VendorQuote {
  id: number;
  request_id: number;
  vendor_id: number;
  vendor_name?: string;
  quote_number?: string;
  quote_date?: string;
  validity_days?: number;
  delivery_days?: number;
  payment_terms?: string;
  subtotal?: number;
  tax_amount?: number;
  other_charges?: number;
  grand_total: number;
  status: string;
  is_selected?: boolean;
  is_lowest?: boolean;
}

interface ProcurementRequest {
  id: number;
  request_number: string;
  company_id: number;
  company_name?: string;
  status: string;
  min_quotes_required: number;
  quotes_received_count: number;
  items_count?: number;
  item_count?: number;
  approved_vendor_id?: number;
  approved_vendor_name?: string;
  approved_vendor_phone?: string;
  request_date?: string;
  created_at?: string;
  updated_at?: string;
  approved_at?: string;
  notes?: string;
  items?: ProcurementRequestItem[];
  quotes?: VendorQuote[];
}

interface MaterialRequirementLine {
  component_id?: number;
  stock_item_id?: number;
  component_code?: string;
  stock_item_code?: string;
  component_name?: string;
  stock_item_name?: string;
  required_qty: number;
  available_qty: number;
  shortage_qty: number;
  status: string;
  unit_of_measure?: string;
}

interface MaterialRequirement {
  id: number;
  requirement_number: string;
  company_id: number;
  company_name?: string;
  source_type: string;
  total_items: number;
  priority: string;
  total_shortage_value: number;
  status: string;
  created_at?: string;
  notes?: string;
  line_items?: MaterialRequirementLine[];
}

interface LowStockItem {
  item_id: number;
  item_code: string;
  item_name: string;
  category?: string;
  company_id?: number;
  company_name?: string;
  available_qty: number;
  reorder_level: number;
  shortage_qty: number;
  unit_of_measure?: string;
  status: string;
}

interface AggregatedShortage {
  component_id: number;
  component_code: string;
  component_name: string;
  total_required: number;
  available_qty: number;
  total_shortage: number;
  unit_of_measure?: string;
  company_id?: number;
  source_orders?: { order_number: string; type: string }[];
}

interface SpareItem {
  item_id: number;
  item_code: string;
  item_name: string;
  unit_of_measure?: string;
  current_stock: number;
  reorder_level?: number;
  req_sources?: string[];
  net_shortage: number;
  stock_status: string;
  vendor_count: number;
  hsn_code?: string;
  model_compat?: string;
  specification?: string;
  purchase_rate?: number;
  demand_manufacturing?: number;
  demand_partner_req?: number;
}

interface SpareVendor {
  vendor_id: number;
  vendor_name: string;
  vendor_code?: string;
  phone?: string;
  city?: string;
  contact_person?: string;
  is_preferred?: boolean;
  last_rate?: number;
  last_date?: string;
}

interface SpareOrderLine {
  id: number;
  order_id?: number;
  vendor_id?: number | null;
  vendor_name?: string;
  item_id: number;
  item_code?: string;
  item_name?: string;
  quantity: number;
  unit_of_measure?: string;
  last_purchase_rate?: number | null;
  last_rate?: number | null;
  demand_source?: string;
  demand_qty?: number;
}

interface SpareOrder {
  id: number;
  order_number: string;
  company_id: number;
  company_name?: string;
  status: "DRAFT" | "WAITING_APPROVAL" | "APPROVED" | "CANCELLED";
  line_count: number;
  created_at?: string;
  updated_at?: string;
  lines?: SpareOrderLine[];
}

interface MarketplaceItem {
  item_id: number;
  item_code: string;
  item_name: string;
  uom?: string;
  source_type: string;
  source_ref?: string;
  qty_needed: number;
  stock_qty: number;
  shortage: number;
  model_compat?: string;
  specification?: string;
}

interface CartItemEntry {
  item_id: number;
  item_code: string;
  item_name: string;
  qty: number;
  uom: string;
  rate: number;
  demand_source: string;
  demand_qty: number;
}

interface CartVendorGroup {
  vendor_id: number | null;
  vendor_name: string;
  vendor_code: string;
  vendor_phone: string;
  items: Record<number, CartItemEntry>;
}

// ── Helpers ────────────────────────────────────────────────────────────────────

function formatNumber(val: any): string {
  if (val === null || val === undefined) return "0";
  const num = parseFloat(val);
  if (isNaN(num)) return "0";
  return num.toLocaleString("en-IN", { minimumFractionDigits: 0, maximumFractionDigits: 2 });
}

function formatDate(dateStr?: string | null): string {
  if (!dateStr) return "—";
  const d = new Date(dateStr);
  if (isNaN(d.getTime())) return "—";
  return d.toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" });
}

const STATUS_BADGES: Record<string, { bg: string; text: string; border: string }> = {
  DRAFT: { bg: "bg-slate-100", text: "text-slate-700", border: "border-slate-200" },
  SENT_TO_VENDORS: { bg: "bg-blue-50", text: "text-blue-700", border: "border-blue-200" },
  QUOTES_RECEIVED: { bg: "bg-purple-50", text: "text-purple-700", border: "border-purple-200" },
  QUOTE_APPROVED: { bg: "bg-emerald-50", text: "text-emerald-700", border: "border-emerald-200" },
  PO_CREATED: { bg: "bg-teal-50", text: "text-teal-700", border: "border-teal-200" },
  COMPLETED: { bg: "bg-green-50", text: "text-green-700", border: "border-green-200" },
  CANCELLED: { bg: "bg-rose-50", text: "text-rose-700", border: "border-rose-200" },
  RETURNED_FOR_QUALITY: { bg: "bg-amber-50", text: "text-amber-700", border: "border-amber-200" },
  PENDING: { bg: "bg-amber-50", text: "text-amber-700", border: "border-amber-200" },
  ACKNOWLEDGED: { bg: "bg-sky-50", text: "text-sky-700", border: "border-sky-200" },
  IN_PROGRESS: { bg: "bg-indigo-50", text: "text-indigo-700", border: "border-indigo-200" },
  WAITING_APPROVAL: { bg: "bg-blue-50", text: "text-blue-700", border: "border-blue-200" },
  APPROVED: { bg: "bg-emerald-50", text: "text-emerald-700", border: "border-emerald-200" },
};

const PRIORITY_BADGES: Record<string, { bg: string; text: string }> = {
  URGENT: { bg: "bg-red-100 text-red-800", text: "Urgent" },
  HIGH: { bg: "bg-amber-100 text-amber-800", text: "High" },
  NORMAL: { bg: "bg-slate-100 text-slate-700", text: "Normal" },
  LOW: { bg: "bg-gray-100 text-gray-600", text: "Low" },
};

const REQ_TAGS: Record<string, { bg: string; text: string }> = {
  Manufacturing: { bg: "bg-amber-100 text-amber-800", text: "Manufacturing" },
  "Low Stock": { bg: "bg-red-100 text-red-800", text: "Low Stock" },
  "Partner Request": { bg: "bg-purple-100 text-purple-800", text: "Partner Request" },
  "Partner Order": { bg: "bg-blue-100 text-blue-800", text: "Partner Order" },
  "Service Ticket": { bg: "bg-emerald-100 text-emerald-800", text: "Service Ticket" },
  "Low Level": { bg: "bg-orange-100 text-orange-800", text: "Low Level" },
};

// ── Main Page Component ────────────────────────────────────────────────────────

export default function AccountsProcurementPage() {
  const { token } = useStaffAuth();
  const router = useRouter();

  // Active Tab
  const [activeTab, setActiveTab] = useState<"requests" | "spareitems" | "requirements" | "lowstock" | "aggregated" | "vgkproc">("requests");

  // Companies List
  const [companies, setCompanies] = useState<Company[]>([]);
  const [selectedCompanyId, setSelectedCompanyId] = useState<string>("");

  // Summary Metrics
  const [urgentCount, setUrgentCount] = useState<number>(0);
  const [pendingCount, setPendingCount] = useState<number>(0);
  const [requestsCount, setRequestsCount] = useState<number>(0);
  const [lowStockCount, setLowStockCount] = useState<number>(0);

  // ── Tab 1: Procurement Requests State ──
  const [procRequests, setProcRequests] = useState<ProcurementRequest[]>([]);
  const [requestStatusFilter, setRequestStatusFilter] = useState<string>("");
  const [requestsLoading, setRequestsLoading] = useState<boolean>(false);

  // ── Tab 2: Spare Items & SPO State ──
  const [spareItems, setSpareItems] = useState<SpareItem[]>([]);
  const [spareStockFilter, setSpareStockFilter] = useState<string>("");
  const [spareReqFromFilter, setSpareReqFromFilter] = useState<string>("");
  const [spareSearch, setSpareSearch] = useState<string>("");
  const [spareSortField, setSpareSortField] = useState<string | null>(null);
  const [spareSortDir, setSpareSortDir] = useState<"asc" | "desc">("asc");
  const [spareLoading, setSpareLoading] = useState<boolean>(false);

  const [spareOrders, setSpareOrders] = useState<SpareOrder[]>([]);
  const [spoStatusFilter, setSpoStatusFilter] = useState<string>("");
  const [spareOrdersLoading, setSpareOrdersLoading] = useState<boolean>(false);

  const [spareCart, setSpareCart] = useState<Record<string, CartVendorGroup>>({});
  const [spareDraftOrderId, setSpareDraftOrderId] = useState<number | null>(null);

  // Vendor selection slide panel
  const [vendorPanelOpen, setVendorPanelOpen] = useState<boolean>(false);
  const [currentSpareItem, setCurrentSpareItem] = useState<SpareItem | null>(null);
  const [itemVendors, setItemVendors] = useState<SpareVendor[]>([]);
  const [itemVendorsLoading, setItemVendorsLoading] = useState<boolean>(false);
  const [selectedVendorForCart, setSelectedVendorForCart] = useState<SpareVendor | null>(null);
  const [vendorOtherItems, setVendorOtherItems] = useState<any[]>([]);
  const [vpQty, setVpQty] = useState<number>(1);
  const [vpRate, setVpRate] = useState<string>("");
  const [vpUom, setVpUom] = useState<string>("PCS");

  // SPO Approve Modal
  const [spoApproveModalOpen, setSpoApproveModalOpen] = useState<boolean>(false);
  const [spoModalOrderId, setSpoModalOrderId] = useState<number | null>(null);
  const [spoModalOrderNum, setSpoModalOrderNum] = useState<string>("");
  const [spoModalLines, setSpoModalLines] = useState<SpareOrderLine[]>([]);
  const [spoModalDeleted, setSpoModalDeleted] = useState<number[]>([]);
  const [spoApproveNotes, setSpoApproveNotes] = useState<string>("");
  const [spoApproving, setSpoApproving] = useState<boolean>(false);
  const [spoVendorSearchResults, setSpoVendorSearchResults] = useState<Record<number, any[]>>({});
  const [spoVendorSearchOpen, setSpoVendorSearchOpen] = useState<Record<number, boolean>>({});

  // ── Tab 3: Material Requirements State ──
  const [requirements, setRequirements] = useState<MaterialRequirement[]>([]);
  const [reqStatusFilter, setReqStatusFilter] = useState<string>("");
  const [reqPriorityFilter, setReqPriorityFilter] = useState<string>("");
  const [selectedReqIds, setSelectedReqIds] = useState<number[]>([]);
  const [reqLoading, setReqLoading] = useState<boolean>(false);

  // View Requirement Modal
  const [viewReqModalOpen, setViewReqModalOpen] = useState<boolean>(false);
  const [activeViewReq, setActiveViewReq] = useState<MaterialRequirement | null>(null);

  // ── Tab 4: Low Stock State ──
  const [lowStockItems, setLowStockItems] = useState<LowStockItem[]>([]);
  const [lowStockCategory, setLowStockCategory] = useState<string>("");
  const [lowStockSearch, setLowStockSearch] = useState<string>("");
  const [selectedLowStockIds, setSelectedLowStockIds] = useState<number[]>([]);
  const [lowStockLoading, setLowStockLoading] = useState<boolean>(false);

  // ── Tab 5: Aggregated Shortages State ──
  const [aggregatedShortages, setAggregatedShortages] = useState<AggregatedShortage[]>([]);
  const [selectedAggIndices, setSelectedAggIndices] = useState<number[]>([]);
  const [aggLoading, setAggLoading] = useState<boolean>(false);

  // ── Tab 6: Market Place State ──
  const [mktItems, setMktItems] = useState<MarketplaceItem[]>([]);
  const [mktSourceFilter, setMktSourceFilter] = useState<string>("");
  const [mktSearch, setMktSearch] = useState<string>("");
  const [mktLoading, setMktLoading] = useState<boolean>(false);

  // ── Modals State ──

  // Create Request Modal
  const [createModalOpen, setCreateModalOpen] = useState<boolean>(false);
  const [createCompanyId, setCreateCompanyId] = useState<string>("");
  const [createMinQuotes, setCreateMinQuotes] = useState<number>(2);
  const [createNotes, setCreateNotes] = useState<string>("");
  const [createItems, setCreateItems] = useState<ProcurementRequestItem[]>([]);
  const [itemSearchTerm, setItemSearchTerm] = useState<string>("");
  const [itemSearchResults, setItemSearchResults] = useState<any[]>([]);
  const [itemQtyToAdd, setItemQtyToAdd] = useState<number>(1);
  const [createSubmitting, setCreateSubmitting] = useState<boolean>(false);

  // View Request Modal
  const [viewRequestModalOpen, setViewRequestModalOpen] = useState<boolean>(false);
  const [viewRequestData, setViewRequestData] = useState<ProcurementRequest | null>(null);

  // Add Quote Modal
  const [addQuoteModalOpen, setAddQuoteModalOpen] = useState<boolean>(false);
  const [quoteTargetReqId, setQuoteTargetReqId] = useState<number | null>(null);
  const [quoteReqData, setQuoteReqData] = useState<ProcurementRequest | null>(null);
  const [availableVendors, setAvailableVendors] = useState<any[]>([]);
  const [quoteVendorId, setQuoteVendorId] = useState<string>("");
  const [quoteNumber, setQuoteNumber] = useState<string>("");
  const [quoteDate, setQuoteDate] = useState<string>(new Date().toISOString().split("T")[0]);
  const [quoteValidity, setQuoteValidity] = useState<number>(30);
  const [quoteDeliveryDays, setQuoteDeliveryDays] = useState<string>("");
  const [quotePaymentTerms, setQuotePaymentTerms] = useState<string>("");
  const [quoteOtherCharges, setQuoteOtherCharges] = useState<number>(0);
  const [quoteItemRates, setQuoteItemRates] = useState<Record<number, { rate: number; gst: number }>>({});
  const [quoteSubmitting, setQuoteSubmitting] = useState<boolean>(false);

  // Status Update Modal
  const [statusModalOpen, setStatusModalOpen] = useState<boolean>(false);
  const [statusTargetReqId, setStatusTargetReqId] = useState<number | null>(null);
  const [newStatusValue, setNewStatusValue] = useState<string>("");
  const [returnType, setReturnType] = useState<"PARTIAL" | "COMPLETE">("PARTIAL");
  const [returnNotes, setReturnNotes] = useState<string>("");
  const [statusGeneralNotes, setStatusGeneralNotes] = useState<string>("");
  const [statusSubmitting, setStatusSubmitting] = useState<boolean>(false);

  // WhatsApp Modal
  const [waModalOpen, setWaModalOpen] = useState<boolean>(false);
  const [waReqData, setWaReqData] = useState<ProcurementRequest | null>(null);
  const [waMessage, setWaMessage] = useState<string>("");
  const [waAttachFormat, setWaAttachFormat] = useState<"excel" | "pdf">("excel");
  const [waSpecOverrides, setWaSpecOverrides] = useState<Record<number, { brand?: string; model_compat?: string; colors?: string; specification?: string }>>({});
  const [waSending, setWaSending] = useState<boolean>(false);

  // Global Toast / Message
  const [toastMessage, setToastMessage] = useState<{ text: string; type: "success" | "error" | "info" } | null>(null);

  const showToast = (text: string, type: "success" | "error" | "info" = "success") => {
    setToastMessage({ text, type });
    setTimeout(() => {
      setToastMessage(null);
    }, 4500);
  };

  // ── Initial Load ─────────────────────────────────────────────────────────────

  useEffect(() => {
    if (!token) return;
    loadCompanies();
  }, [token]);

  useEffect(() => {
    if (!token) return;
    loadData();
  }, [token, activeTab, selectedCompanyId, requestStatusFilter, reqStatusFilter, reqPriorityFilter, lowStockCategory]);

  const loadCompanies = async () => {
    try {
      const res = await api.get("/staff/accounts/companies");
      const list = res.data?.companies || res.data || [];
      setCompanies(list);
    } catch (e) {
      console.error("Error loading companies:", e);
    }
  };

  const loadData = async () => {
    if (activeTab === "requests") {
      loadProcurementRequests();
    } else if (activeTab === "spareitems") {
      loadSpareItems();
      loadSpareOrders();
    } else if (activeTab === "requirements") {
      loadRequirements();
    } else if (activeTab === "lowstock") {
      loadLowStock();
    } else if (activeTab === "aggregated") {
      loadAggregated();
    } else if (activeTab === "vgkproc") {
      loadMarketplaceItems();
    }
  };

  // ── Tab 1: Procurement Requests ──────────────────────────────────────────────

  const loadProcurementRequests = async () => {
    try {
      setRequestsLoading(true);
      let url = `/staff/accounts/procurement/requests?page=1&limit=50`;
      if (selectedCompanyId) url += `&company_id=${selectedCompanyId}`;
      if (requestStatusFilter) url += `&status=${requestStatusFilter}`;

      const res = await api.get(url);
      const data = res.data?.data || res.data?.requests || res.data || [];
      setProcRequests(Array.isArray(data) ? data : []);
      setRequestsCount(res.data?.pagination?.total || data.length || 0);
    } catch (e) {
      console.error("Load procurement requests error:", e);
      setProcRequests([]);
    } finally {
      setRequestsLoading(false);
    }
  };

  const viewRequestDetails = async (id: number) => {
    try {
      setViewRequestModalOpen(true);
      const res = await api.get(`/staff/accounts/procurement/requests/${id}`);
      const r = res.data?.data || res.data;
      setViewRequestData(r);
    } catch (e) {
      console.error("Error viewing request:", e);
      showToast("Failed to load request details", "error");
    }
  };

  const openAddQuoteModal = async (reqId: number) => {
    setQuoteTargetReqId(reqId);
    setQuoteVendorId("");
    setQuoteNumber("");
    setQuoteDate(new Date().toISOString().split("T")[0]);
    setQuoteValidity(30);
    setQuoteDeliveryDays("");
    setQuotePaymentTerms("");
    setQuoteOtherCharges(0);
    setQuoteItemRates({});

    try {
      const [reqRes, vendorsRes] = await Promise.all([
        api.get(`/staff/accounts/procurement/requests/${reqId}`),
        api.get(`/staff/accounts/procurement/requests/${reqId}/available-vendors`),
      ]);
      const r = reqRes.data?.data || reqRes.data;
      const v = vendorsRes.data?.data || vendorsRes.data?.vendors || vendorsRes.data || [];
      setQuoteReqData(r);
      setAvailableVendors(v);

      const initialRates: Record<number, { rate: number; gst: number }> = {};
      (r.items || []).forEach((it: ProcurementRequestItem) => {
        if (it.id) initialRates[it.id] = { rate: 0, gst: 18 };
      });
      setQuoteItemRates(initialRates);

      setAddQuoteModalOpen(true);
    } catch (e) {
      console.error("Failed to load quote dialog data:", e);
      showToast("Failed to load quote form", "error");
    }
  };

  const calculateQuoteTotals = () => {
    let subtotal = 0;
    let totalGst = 0;
    if (!quoteReqData?.items) return { subtotal: 0, totalGst: 0, grandTotal: 0 };

    quoteReqData.items.forEach((it) => {
      if (it.id && quoteItemRates[it.id]) {
        const { rate, gst } = quoteItemRates[it.id];
        const lineTotal = (rate || 0) * (it.required_qty || 0);
        const gstAmount = (lineTotal * (gst || 0)) / 100;
        subtotal += lineTotal;
        totalGst += gstAmount;
      }
    });

    const grandTotal = subtotal + totalGst + (quoteOtherCharges || 0);
    return { subtotal, totalGst, grandTotal };
  };

  const submitQuote = async () => {
    if (!quoteVendorId) {
      showToast("Please select a vendor", "error");
      return;
    }

    const itemsPayload: any[] = [];
    let hasValidRate = false;

    Object.entries(quoteItemRates).forEach(([itemId, data]) => {
      if (data.rate > 0) {
        hasValidRate = true;
        itemsPayload.push({
          request_item_id: parseInt(itemId),
          quoted_rate: data.rate,
          gst_rate: data.gst,
        });
      }
    });

    if (!hasValidRate) {
      showToast("Please enter rate for at least one item", "error");
      return;
    }

    try {
      setQuoteSubmitting(true);
      const payload = {
        vendor_id: parseInt(quoteVendorId),
        quote_data: {
          quote_number: quoteNumber || null,
          quote_date: quoteDate || null,
          validity_days: quoteValidity || 30,
          delivery_days: quoteDeliveryDays ? parseInt(quoteDeliveryDays) : null,
          payment_terms: quotePaymentTerms || null,
          other_charges: quoteOtherCharges || 0,
        },
        quote_items: itemsPayload,
      };

      const res = await api.post(`/staff/accounts/procurement/requests/${quoteTargetReqId}/quotes`, payload);
      if (res.data?.success || res.status === 200 || res.status === 201) {
        showToast("Quote added successfully!");
        setAddQuoteModalOpen(false);
        loadProcurementRequests();
        if (viewRequestModalOpen && quoteTargetReqId) {
          viewRequestDetails(quoteTargetReqId);
        }
      } else {
        showToast(res.data?.message || res.data?.detail || "Failed to add quote", "error");
      }
    } catch (e: any) {
      console.error("Quote submit error:", e);
      showToast(e.response?.data?.detail || "Failed to submit quote", "error");
    } finally {
      setQuoteSubmitting(false);
    }
  };

  const approveQuote = async (quoteId: number) => {
    if (!confirm("Approve this quote? Other quotes for this request will be marked as rejected.")) return;

    try {
      const res = await api.post(`/staff/accounts/procurement/quotes/${quoteId}/approve`, {
        approval_remarks: "Approved from Procurement Portal",
      });
      if (res.data?.success || res.status === 200) {
        showToast("Quote approved successfully!");
        setViewRequestModalOpen(false);
        loadProcurementRequests();
      } else {
        showToast(res.data?.message || "Failed to approve quote", "error");
      }
    } catch (e: any) {
      showToast(e.response?.data?.detail || "Failed to approve quote", "error");
    }
  };

  const generatePO = async (requestId: number) => {
    if (!confirm("Generate Purchase Order from the approved quote?")) return;

    try {
      const res = await api.post(`/staff/accounts/procurement/requests/${requestId}/generate-po`);
      if (res.data?.success || res.status === 200) {
        showToast(`Purchase Order ${res.data?.data?.voucher_number || ""} generated successfully!`);
        setViewRequestModalOpen(false);
        loadProcurementRequests();
      } else {
        showToast(res.data?.message || "Failed to generate PO", "error");
      }
    } catch (e: any) {
      showToast(e.response?.data?.detail || "Failed to generate PO", "error");
    }
  };

  const openStatusModal = (reqId: number) => {
    setStatusTargetReqId(reqId);
    setNewStatusValue("");
    setReturnType("PARTIAL");
    setReturnNotes("");
    setStatusGeneralNotes("");
    setStatusModalOpen(true);
  };

  const submitStatusUpdate = async () => {
    if (!statusTargetReqId || !newStatusValue) {
      showToast("Please select a status", "error");
      return;
    }

    let finalNotes = statusGeneralNotes;
    if (newStatusValue === "RETURNED_FOR_QUALITY") {
      if (!returnNotes.trim()) {
        showToast("Please describe the quality return reason / items returned", "error");
        return;
      }
      finalNotes = `[${returnType} RETURN] ${returnNotes}${statusGeneralNotes ? "\n" + statusGeneralNotes : ""}`;
    }

    try {
      setStatusSubmitting(true);
      const res = await api.put(`/staff/accounts/procurement/requests/${statusTargetReqId}/status`, {
        status: newStatusValue,
        notes: finalNotes || undefined,
      });

      if (res.data?.success || res.status === 200) {
        showToast(`Status updated to ${newStatusValue.replace(/_/g, " ")}`);
        setStatusModalOpen(false);
        loadProcurementRequests();
      } else {
        showToast(res.data?.message || "Failed to update status", "error");
      }
    } catch (e: any) {
      showToast(e.response?.data?.detail || "Failed to update status", "error");
    } finally {
      setStatusSubmitting(false);
    }
  };

  // ── WhatsApp & Export Handlers ──

  const buildWhatsAppMessage = (req: ProcurementRequest, overrides: Record<number, any>) => {
    const items = req.items || [];
    const itemLines = items
      .map((it, i) => {
        const ov = overrides[i] || {};
        const brand = ov.brand || it.brand || "";
        const model = ov.model_compat || it.model_compat || "";
        const spec = ov.specification || it.specification || "";
        const rawCols = ov.colors || it.colors;
        const cols = Array.isArray(rawCols) ? rawCols.join(", ") : typeof rawCols === "string" ? rawCols : "";

        let line = `${i + 1}. *${it.item_name || it.item_code}*`;
        if (it.item_code) line += ` (Code: ${it.item_code})`;
        line += `\n   Quantity Required: ${it.required_qty} ${it.unit_of_measure || "PCS"}`;
        if (it.item_category || it.category) line += `\n   Category: ${it.item_category || it.category}`;
        if (it.hsn_code) line += `\n   HSN Code: ${it.hsn_code}`;
        if (brand) line += `\n   Brand: ${brand}`;
        if (model) line += `\n   Model/Compatible With: ${model}`;
        if (cols) line += `\n   Colour: ${cols}`;
        if (spec) line += `\n   Specification: ${spec}`;
        if (it.specifications) line += `\n   Additional Notes: ${it.specifications}`;
        return line;
      })
      .join("\n\n");

    const today = new Date().toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" });
    return `Dear ${req.approved_vendor_name || "Vendor"},

We have a Procurement Request from *${req.company_name || "MyntReal LLP"}* and would like your best quotation.

Request Details:
• Request No: *${req.request_number}*
• Date: ${req.request_date || today}
• Company: ${req.company_name || "MyntReal LLP"}
${req.notes ? `• Notes: ${req.notes}\n` : ""}
*Items Required:*

${itemLines || "Please refer to the attached document for item details."}

Kindly share your proforma invoice with unit rate, taxes (GST), delivery terms, and expected delivery date at the earliest.

Thank you,
${req.company_name || "MyntReal LLP"} Procurement Team`;
  };

  const openWhatsAppModal = async (reqId: number) => {
    try {
      const res = await api.get(`/staff/accounts/procurement/requests/${reqId}`);
      const r = res.data?.data || res.data;
      setWaReqData(r);
      setWaSpecOverrides({});
      const initialMsg = buildWhatsAppMessage(r, {});
      setWaMessage(initialMsg);
      setWaAttachFormat("excel");
      setWaModalOpen(true);
    } catch (e) {
      showToast("Failed to load request for WhatsApp", "error");
    }
  };

  const updateSpecOverride = (idx: number, field: string, val: string) => {
    setWaSpecOverrides((prev) => {
      const updated = { ...prev, [idx]: { ...(prev[idx] || {}), [field]: val } };
      if (waReqData) {
        setWaMessage(buildWhatsAppMessage(waReqData, updated));
      }
      return updated;
    });
  };

  const downloadProcExcel = (req: ProcurementRequest, overrides: Record<number, any>) => {
    const items = req.items || [];
    if (!items.length) {
      showToast("No items to export", "info");
      return;
    }

    const headers = ["S.No", "Item Code", "Item Name", "Required Qty", "UOM", "Category", "HSN Code", "Brand", "Model / Compatible With", "Colour", "Specification", "Additional Notes"];
    const rows = items.map((it, i) => {
      const ov = overrides[i] || {};
      const rawCols = ov.colors || it.colors;
      const colours = Array.isArray(rawCols) ? rawCols.join(", ") : typeof rawCols === "string" ? rawCols : "";
      return [
        i + 1,
        `"${(it.item_code || "").replace(/"/g, '""')}"`,
        `"${(it.item_name || "").replace(/"/g, '""')}"`,
        it.required_qty || 0,
        `"${(it.unit_of_measure || "PCS").replace(/"/g, '""')}"`,
        `"${(it.item_category || it.category || "").replace(/"/g, '""')}"`,
        `"${(it.hsn_code || "").replace(/"/g, '""')}"`,
        `"${(ov.brand || it.brand || "").replace(/"/g, '""')}"`,
        `"${(ov.model_compat || it.model_compat || "").replace(/"/g, '""')}"`,
        `"${colours.replace(/"/g, '""')}"`,
        `"${(ov.specification || it.specification || "").replace(/"/g, '""')}"`,
        `"${(it.specifications || "").replace(/"/g, '""')}"`,
      ].join(",");
    });

    const csvContent = "data:text/csv;charset=utf-8," + [headers.join(","), ...rows].join("\n");
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `ProcReq_${req.request_number || req.id}_Items.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    showToast(`Items list downloaded for ${req.request_number}`);
  };

  const downloadProcPDF = (req: ProcurementRequest, overrides: Record<number, any>) => {
    const items = req.items || [];
    const today = new Date().toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" });

    const rows = items
      .map((it, i) => {
        const ov = overrides[i] || {};
        const brand = ov.brand || it.brand || "—";
        const model = ov.model_compat || it.model_compat || "—";
        const spec = ov.specification || it.specification || "—";
        const rawCols = ov.colors || it.colors;
        const cols = Array.isArray(rawCols) ? rawCols.join(", ") : (typeof rawCols === "string" ? rawCols : "—") || "—";
        return `<tr>
          <td style="text-align:center;">${i + 1}</td>
          <td><strong>${it.item_name || "—"}</strong><br><code style="font-size:10px;color:#6b7280;">${it.item_code || ""}</code></td>
          <td style="text-align:center;">${it.required_qty} ${it.unit_of_measure || "PCS"}</td>
          <td>${it.item_category || it.category || "—"}</td>
          <td>${it.hsn_code || "—"}</td>
          <td>${brand}</td>
          <td>${model}</td>
          <td>${cols}</td>
          <td>${spec}</td>
          <td>${it.specifications || "—"}</td>
        </tr>`;
      })
      .join("");

    const html = `<!DOCTYPE html><html><head><meta charset="UTF-8">
      <title>Procurement Request ${req.request_number}</title>
      <style>
        body{font-family:Segoe UI,Helvetica,Arial,sans-serif;margin:24px;color:#111;font-size:12px;}
        h1{font-size:18px;color:#1e40af;margin:0 0 4px;font-weight:700;}
        .sub{font-size:12px;color:#6b7280;margin-bottom:16px;}
        .meta-grid{display:grid;grid-template-columns:1fr 1fr;gap:6px 20px;margin-bottom:18px;font-size:12px;}
        .meta-grid span{color:#9ca3af;font-size:10px;font-weight:700;display:block;}
        table{width:100%;border-collapse:collapse;font-size:11px;}
        th{background:#1e40af;color:#fff;padding:7px 8px;text-align:left;font-size:10px;text-transform:uppercase;}
        td{padding:6px 8px;border-bottom:1px solid #e5e7eb;vertical-align:top;}
        tr:nth-child(even) td{background:#f9fafb;}
        .footer{margin-top:20px;font-size:10px;color:#9ca3af;border-top:1px solid #e5e7eb;padding-top:10px;}
        @media print{body{margin:10px;}@page{margin:15mm;}}
      </style></head><body>
      <h1>Procurement Request — ${req.request_number}</h1>
      <div class="sub">Vendor: <strong>${req.approved_vendor_name || "—"}</strong>${req.approved_vendor_phone ? " &nbsp;|&nbsp; 📱 " + req.approved_vendor_phone : ""}</div>
      <div class="meta-grid">
        <div><span>Company</span>${req.company_name || "MyntReal LLP"}</div>
        <div><span>Date</span>${req.request_date || today}</div>
        <div><span>Status</span>${req.status || "—"}</div>
        <div><span>Quotes</span>${req.quotes_received_count || 0} / ${req.min_quotes_required || 2} required</div>
        ${req.notes ? `<div style="grid-column:1/-1"><span>Notes</span>${req.notes}</div>` : ""}
      </div>
      <table>
        <thead><tr>
          <th>#</th><th>Item</th><th>Qty</th><th>Category</th><th>HSN</th>
          <th>Brand</th><th>Model / Compat</th><th>Colour</th><th>Specification</th><th>Additional Notes</th>
        </tr></thead>
        <tbody>${rows}</tbody>
      </table>
      <div class="footer">Generated by MyntReal LLP Procurement System &nbsp;|&nbsp; ${today} &nbsp;|&nbsp; Blind Bidding Protocol (Prices excluded)</div>
      </body></html>`;

    const win = window.open("", "_blank");
    if (!win) {
      showToast("Pop-up blocked — allow pop-ups to print PDF", "info");
      return;
    }
    win.document.write(html);
    win.document.close();
    win.focus();
    setTimeout(() => {
      win.print();
    }, 600);
  };

  const handleOpenWhatsAppWeb = () => {
    if (!waReqData) return;
    if (waAttachFormat === "pdf") {
      downloadProcPDF(waReqData, waSpecOverrides);
    } else {
      downloadProcExcel(waReqData, waSpecOverrides);
    }

    const rawPhone = (waReqData.approved_vendor_phone || "").replace(/\D/g, "");
    setTimeout(() => {
      if (rawPhone) {
        const phone = rawPhone.startsWith("91") ? rawPhone : "91" + rawPhone;
        window.open(`https://wa.me/${phone}?text=${encodeURIComponent(waMessage)}`, "_blank");
        showToast("Attachment downloaded. Opening WhatsApp...", "info");
      } else {
        navigator.clipboard?.writeText(waMessage).catch(() => {});
        window.open("https://web.whatsapp.com", "_blank");
        showToast("Message copied to clipboard. Opening WhatsApp Web...", "info");
      }
    }, 400);
  };

  const handleSendWhatsAppAPI = async () => {
    if (!waReqData) return;
    try {
      setWaSending(true);
      const res = await api.post(`/staff/accounts/procurement/requests/${waReqData.id}/whatsapp`, {
        message: waMessage,
      });
      if (res.data?.success || res.status === 200) {
        showToast("WhatsApp sent to vendor via API!");
        setWaModalOpen(false);
      } else {
        showToast(res.data?.message || "API send failed, falling back to WhatsApp Web", "info");
        handleOpenWhatsAppWeb();
      }
    } catch (e: any) {
      console.warn("WhatsApp API error, falling back to Web:", e);
      handleOpenWhatsAppWeb();
    } finally {
      setWaSending(false);
    }
  };

  const downloadRequestDoc = async (reqId: number) => {
    try {
      const res = await api.get(`/staff/accounts/procurement/requests/${reqId}/download`);
      const d = res.data?.data || res.data;

      let content = `PROCUREMENT REQUEST: ${d.request_number}\n`;
      content += `${"=".repeat(50)}\n\n`;
      content += `Company: ${d.company_name || "-"}\n`;
      content += `Date: ${d.request_date || "-"}\n`;
      content += `Status: ${d.status}\n`;
      content += `GST: ${d.company_gst || "-"}\n\n`;
      content += `ITEMS REQUIRED (${d.total_items || d.items?.length || 0} items):\n`;
      content += `${"-".repeat(50)}\n`;

      (d.items || []).forEach((item: any, idx: number) => {
        content += `\n${item.sl_no || idx + 1}. ${item.item_name}\n`;
        content += `   Code: ${item.item_code}\n`;
        content += `   HSN: ${item.hsn_code || "-"}\n`;
        content += `   Category: ${item.category || item.item_category || "-"}\n`;
        content += `   Quantity: ${item.required_qty} ${item.unit_of_measure || "PCS"}\n`;
        if (item.specifications || item.specification) {
          content += `   Specs: ${item.specifications || item.specification}\n`;
        }
      });

      content += `\n${"-".repeat(50)}\n`;
      content += `\nNOTE: This is a request for quotation. No prices are included.\n`;
      content += `Please submit your best quote with all applicable taxes.\n`;

      const blob = new Blob([content], { type: "text/plain" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${d.request_number || `REQ-${reqId}`}.txt`;
      a.click();
      URL.revokeObjectURL(url);
      showToast(`Downloaded ${d.request_number || `REQ-${reqId}`}.txt`);
    } catch (e) {
      showToast("Failed to download request document", "error");
    }
  };

  // ── Tab 2: Consolidated Spare Parts ──────────────────────────────────────────

  const loadSpareItems = async () => {
    try {
      setSpareLoading(true);
      let url = `/staff/accounts/procurement/spare-items?limit=200`;
      if (selectedCompanyId) url += `&company_id=${selectedCompanyId}`;
      if (spareSearch.trim()) url += `&search=${encodeURIComponent(spareSearch.trim())}`;

      const res = await api.get(url);
      const items = res.data?.items || res.data || [];
      setSpareItems(Array.isArray(items) ? items : []);
    } catch (e) {
      console.error("Load spare items error:", e);
      setSpareItems([]);
    } finally {
      setSpareLoading(false);
    }
  };

  const loadSpareOrders = async () => {
    try {
      setSpareOrdersLoading(true);
      let url = `/staff/accounts/procurement/spare-orders?limit=100`;
      if (selectedCompanyId) url += `&company_id=${selectedCompanyId}`;
      if (spoStatusFilter) url += `&status=${encodeURIComponent(spoStatusFilter)}`;

      const res = await api.get(url);
      const orders = res.data?.orders || res.data || [];
      setSpareOrders(Array.isArray(orders) ? orders : []);
    } catch (e) {
      console.error("Load spare orders error:", e);
      setSpareOrders([]);
    } finally {
      setSpareOrdersLoading(false);
    }
  };

  // Filtered & Sorted Spare Items
  const filteredSortedSpareItems = useMemo(() => {
    let list = [...spareItems];
    if (spareStockFilter) {
      list = list.filter((i) => i.stock_status === spareStockFilter);
    }
    if (spareReqFromFilter) {
      list = list.filter((i) => (i.req_sources || []).includes(spareReqFromFilter));
    }
    if (spareSortField) {
      list.sort((a: any, b: any) => {
        let va = a[spareSortField];
        let vb = b[spareSortField];
        if (spareSortField === "req_sources") {
          va = (va || []).join(",");
          vb = (vb || []).join(",");
        }
        if (va == null) va = "";
        if (vb == null) vb = "";
        const cmp = typeof va === "number" && typeof vb === "number" ? va - vb : String(va).localeCompare(String(vb), undefined, { numeric: true });
        return spareSortDir === "asc" ? cmp : -cmp;
      });
    }
    return list;
  }, [spareItems, spareStockFilter, spareReqFromFilter, spareSortField, spareSortDir]);

  const handleSortSpare = (field: string) => {
    if (spareSortField === field) {
      setSpareSortDir(spareSortDir === "asc" ? "desc" : "asc");
    } else {
      setSpareSortField(field);
      setSpareSortDir("asc");
    }
  };

  // Cart operations
  const pushToSpareCart = (
    vendorId: number | null,
    vendorName: string,
    vendorCode: string,
    vendorPhone: string,
    itemId: number,
    itemCode: string,
    itemName: string,
    qty: number,
    uom: string,
    rate: number,
    demandSource: string,
    demandQty: number
  ) => {
    const key = vendorId !== null && vendorId !== undefined && vendorId !== 0 ? String(vendorId) : "__TBD__";
    setSpareCart((prev) => {
      const updated = { ...prev };
      if (!updated[key]) {
        updated[key] = {
          vendor_id: key === "__TBD__" ? null : vendorId,
          vendor_name: vendorName || "Vendor TBD",
          vendor_code: vendorCode || "",
          vendor_phone: vendorPhone || "",
          items: {},
        };
      }
      updated[key].items[itemId] = {
        item_id: itemId,
        item_code: itemCode,
        item_name: itemName,
        qty: Math.max(1, qty),
        uom: uom || "PCS",
        rate: rate || 0,
        demand_source: demandSource,
        demand_qty: demandQty,
      };
      return updated;
    });
    showToast(`Added ${itemName} to Cart`);
  };

  const quickAddSpareToCart = (item: SpareItem) => {
    const qty = Math.max(1, item.net_shortage || 1);
    const src = (item.req_sources || []).join(", ") || "General";
    pushToSpareCart(null, "Vendor TBD", "", "", item.item_id, item.item_code, item.item_name, qty, item.unit_of_measure || "PCS", item.purchase_rate || 0, src, qty);
  };

  const updateCartItemQty = (cartKey: string, itemId: number, qtyVal: number) => {
    setSpareCart((prev) => {
      const updated = { ...prev };
      if (updated[cartKey]?.items[itemId]) {
        updated[cartKey].items[itemId].qty = Math.max(1, qtyVal);
      }
      return updated;
    });
  };

  const removeCartItem = (cartKey: string, itemId: number) => {
    setSpareCart((prev) => {
      const updated = { ...prev };
      if (updated[cartKey]?.items[itemId]) {
        delete updated[cartKey].items[itemId];
        if (Object.keys(updated[cartKey].items).length === 0) {
          delete updated[cartKey];
        }
      }
      return updated;
    });
  };

  const clearSpareCart = () => {
    setSpareCart({});
    setSpareDraftOrderId(null);
  };

  const saveSpareOrder = async () => {
    const entries = Object.values(spareCart);
    if (!entries.length) {
      showToast("Cart is empty", "error");
      return;
    }
    const co = selectedCompanyId || companies[0]?.id;
    if (!co) {
      showToast("Please select a company first", "error");
      return;
    }

    const lines: any[] = [];
    entries.forEach((v) => {
      Object.values(v.items).forEach((it) => {
        lines.push({
          vendor_id: v.vendor_id,
          item_id: it.item_id,
          quantity: it.qty,
          uom: it.uom,
          last_rate: it.rate,
          demand_source: it.demand_source,
          demand_qty: it.demand_qty,
        });
      });
    });

    try {
      const res = await api.post("/staff/accounts/procurement/spare-orders", {
        company_id: parseInt(String(co)),
        lines,
        order_id: spareDraftOrderId,
      });

      if (res.data?.success || res.status === 200 || res.status === 201) {
        const order = res.data.order;
        setSpareDraftOrderId(order.id);
        showToast(`Draft ${order.order_number} saved! Ready to submit for approval.`);
        loadSpareOrders();
      } else {
        showToast(res.data?.message || "Failed to save draft order", "error");
      }
    } catch (e: any) {
      showToast(e.response?.data?.detail || "Error saving spare order", "error");
    }
  };

  const submitSpareOrder = async () => {
    let orderId = spareDraftOrderId;
    if (!orderId) {
      await saveSpareOrder();
    }
    if (!spareDraftOrderId && !orderId) return;

    if (!confirm("Submit this spare parts order for approval? Approvers will be notified.")) return;

    try {
      const res = await api.put(`/staff/accounts/procurement/spare-orders/${spareDraftOrderId || orderId}/submit`);
      if (res.data?.success || res.status === 200) {
        showToast(`Order ${res.data.order?.order_number || ""} submitted for approval!`);
        clearSpareCart();
        loadSpareOrders();
      } else {
        showToast(res.data?.message || "Failed to submit order", "error");
      }
    } catch (e: any) {
      showToast(e.response?.data?.detail || "Error submitting spare order", "error");
    }
  };

  // Vendor slide panel
  const openVendorPanel = async (item: SpareItem) => {
    setCurrentSpareItem(item);
    setSelectedVendorForCart(null);
    setVendorOtherItems([]);
    setVpQty(Math.max(1, item.net_shortage || 1));
    setVpRate(item.purchase_rate ? String(item.purchase_rate) : "");
    setVpUom(item.unit_of_measure || "PCS");
    setVendorPanelOpen(true);
    setItemVendorsLoading(true);

    try {
      const res = await api.get(`/staff/accounts/procurement/spare-items/${item.item_id}/vendors`);
      setItemVendors(res.data?.vendors || res.data || []);
    } catch (e) {
      console.error("Error loading item vendors:", e);
      setItemVendors([]);
    } finally {
      setItemVendorsLoading(false);
    }
  };

  const handleSelectVendorInPanel = async (vendor: SpareVendor) => {
    setSelectedVendorForCart(vendor);
    if (vendor.last_rate) setVpRate(String(vendor.last_rate));

    if (!currentSpareItem) return;
    try {
      const res = await api.get(`/staff/accounts/procurement/spare-vendors/${vendor.vendor_id}/items?exclude_ids=${currentSpareItem.item_id}`);
      const others = (res.data?.items || res.data || []).filter((oi: any) => oi.item_id !== currentSpareItem.item_id);
      setVendorOtherItems(others);
    } catch (e) {
      setVendorOtherItems([]);
    }
  };

  // SPO Review & Approve Modal
  const openSpoApproveModal = async (orderId: number, orderNumber: string) => {
    setSpoModalOrderId(orderId);
    setSpoModalOrderNum(orderNumber);
    setSpoModalLines([]);
    setSpoModalDeleted([]);
    setSpoApproveNotes("");
    setSpoApproveModalOpen(true);

    try {
      const res = await api.get(`/staff/accounts/procurement/spare-orders/${orderId}`);
      if (res.data?.success || res.status === 200) {
        const lines = (res.data.order?.lines || []).map((l: any) => ({ ...l }));
        setSpoModalLines(lines);
      } else {
        showToast("Failed to load order lines", "error");
      }
    } catch (e) {
      showToast("Network error loading order", "error");
    }
  };

  const handleSpoVendorSearch = async (lineId: number, query: string) => {
    if (!query || query.length < 2) {
      setSpoVendorSearchOpen((prev) => ({ ...prev, [lineId]: false }));
      return;
    }

    try {
      const res = await api.get(`/staff/accounts/vendors?search=${encodeURIComponent(query)}&page_size=8`);
      const vendors = res.data?.vendors || res.data || [];
      setSpoVendorSearchResults((prev) => ({ ...prev, [lineId]: vendors }));
      setSpoVendorSearchOpen((prev) => ({ ...prev, [lineId]: true }));
    } catch (e) {
      setSpoVendorSearchOpen((prev) => ({ ...prev, [lineId]: false }));
    }
  };

  const handleSpoSelectVendor = (lineId: number, vendorId: number, vendorName: string) => {
    setSpoModalLines((prev) =>
      prev.map((l) => {
        if (l.id === lineId) {
          return { ...l, vendor_id: vendorId, vendor_name: vendorName };
        }
        return l;
      })
    );
    setSpoVendorSearchOpen((prev) => ({ ...prev, [lineId]: false }));
  };

  const submitSpoApproval = async () => {
    if (!spoModalOrderId) return;
    const activeLines = spoModalLines.filter((l) => !spoModalDeleted.includes(l.id));

    const missingVendor = activeLines.filter((l) => !l.vendor_id);
    if (missingVendor.length > 0) {
      showToast(`${missingVendor.length} item(s) have no vendor assigned. Assign vendors to all lines.`, "error");
      return;
    }

    try {
      setSpoApproving(true);
      // Step 1: Save line changes
      const linesPayload = activeLines.map((l) => ({
        id: l.id,
        vendor_id: l.vendor_id,
        quantity: l.quantity,
        last_rate: l.last_purchase_rate || l.last_rate || null,
      }));

      const res1 = await api.put(`/staff/accounts/procurement/spare-orders/${spoModalOrderId}/review-update`, {
        lines: linesPayload,
        deleted_line_ids: spoModalDeleted,
      });

      if (!res1.data?.success && res1.status !== 200) {
        showToast(res1.data?.message || "Failed to update lines before approval", "error");
        setSpoApproving(false);
        return;
      }

      // Step 2: Approve
      const res2 = await api.put(`/staff/accounts/procurement/spare-orders/${spoModalOrderId}/approve`, {
        approval_notes: spoApproveNotes,
      });

      if (res2.data?.success || res2.status === 200) {
        showToast(res2.data?.message || "Spare Purchase Order approved!");
        setSpoApproveModalOpen(false);
        loadSpareOrders();
      } else {
        showToast(res2.data?.message || "Approval failed", "error");
      }
    } catch (e: any) {
      showToast(e.response?.data?.detail || "Error during approval", "error");
    } finally {
      setSpoApproving(false);
    }
  };

  const cancelSpareOrder = async (orderId: number, orderNum: string) => {
    if (!confirm(`Cancel Spare Order ${orderNum}?`)) return;
    try {
      const res = await api.put(`/staff/accounts/procurement/spare-orders/${orderId}/cancel`);
      if (res.data?.success || res.status === 200) {
        showToast("Order cancelled");
        loadSpareOrders();
      } else {
        showToast(res.data?.message || "Failed to cancel order", "error");
      }
    } catch (e: any) {
      showToast(e.response?.data?.detail || "Failed to cancel order", "error");
    }
  };

  const downloadSpoPDF = async (orderId: number, vendorId?: number | null) => {
    try {
      if (!vendorId) {
        const r = await api.get(`/staff/accounts/procurement/spare-orders/${orderId}`);
        const vids = [...new Set((r.data?.order?.lines || []).filter((l: any) => l.vendor_id).map((l: any) => l.vendor_id))];
        if (!vids.length) {
          showToast("No vendors assigned to this order yet", "info");
          return;
        }
        for (const vid of vids) {
          await triggerSpoPDFDownload(orderId, vid as number);
        }
        return;
      }
      await triggerSpoPDFDownload(orderId, vendorId);
    } catch (e) {
      showToast("Error downloading PDF", "error");
    }
  };

  const triggerSpoPDFDownload = async (orderId: number, vendorId: number) => {
    try {
      const res = await api.get(`/staff/accounts/procurement/spare-orders/${orderId}/receipt/${vendorId}`, {
        responseType: "blob",
      });
      const blob = new Blob([res.data], { type: "application/pdf" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `SPO-${orderId}-V${vendorId}.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      setTimeout(() => URL.revokeObjectURL(url), 3000);
      showToast("PDF downloaded");
    } catch (e) {
      showToast("Failed to generate PDF for vendor", "error");
    }
  };

  const convertSpoToPurchase = async (orderId: number, vendorId: number, vendorName: string) => {
    try {
      const res = await api.get(`/staff/accounts/procurement/spare-orders/${orderId}/purchase-prefill/${vendorId}`);
      if (res.data?.success || res.status === 200) {
        if (typeof window !== "undefined") {
          sessionStorage.setItem("vendor_txn_prefill", JSON.stringify(res.data.prefill));
        }
        showToast(`Prefill data stored for ${vendorName}. Redirecting...`);
        router.push("/staff/inventory/vendor-transactions?prefill=spare");
      } else {
        showToast(res.data?.message || "Failed to prepare purchase prefill", "error");
      }
    } catch (e: any) {
      showToast(e.response?.data?.detail || "Network error", "error");
    }
  };

  const sendSpoWhatsApp = async (orderId: number, vendorId: number, vendorName: string, orderNumber: string) => {
    try {
      const res = await api.post(`/staff/accounts/procurement/spare-orders/${orderId}/send-whatsapp/${vendorId}`);
      if (res.data?.success || res.status === 200) {
        showToast(`WhatsApp sent to ${vendorName}!`);
      } else {
        const phone = res.data?.phone || "";
        if (phone) {
          const msg = encodeURIComponent(`Dear ${vendorName},\n\nPlease find Spare Purchase Order ${orderNumber} details.\n\nThank you,\nMyntReal LLP`);
          const cleanPhone = phone.replace(/\D/g, "");
          const fullPhone = cleanPhone.startsWith("91") ? cleanPhone : "91" + cleanPhone;
          window.open(`https://wa.me/${fullPhone}?text=${msg}`, "_blank");
        } else {
          window.open("https://web.whatsapp.com", "_blank");
        }
        showToast("Opening WhatsApp Web...", "info");
      }
    } catch (e) {
      window.open("https://web.whatsapp.com", "_blank");
    }
  };

  // ── Tab 3: Material Requirements ─────────────────────────────────────────────

  const loadRequirements = async () => {
    try {
      setReqLoading(true);
      let url = `/staff/accounts/procurement/requirements?page=1&limit=50`;
      if (selectedCompanyId) url += `&company_id=${selectedCompanyId}`;
      if (reqStatusFilter) url += `&status=${reqStatusFilter}`;
      if (reqPriorityFilter) url += `&priority=${reqPriorityFilter}`;

      const res = await api.get(url);
      const list = res.data?.requirements || res.data || [];
      setRequirements(Array.isArray(list) ? list : []);

      const urgent = list.filter((r: MaterialRequirement) => r.priority === "URGENT").length;
      const pending = list.filter((r: MaterialRequirement) => r.status === "PENDING").length;
      setUrgentCount(urgent);
      setPendingCount(pending);
    } catch (e) {
      console.error("Load requirements error:", e);
      setRequirements([]);
    } finally {
      setReqLoading(false);
    }
  };

  const triggerRequirement = async (id: number) => {
    if (!confirm("Mark this requirement as triggered for procurement?")) return;
    try {
      const res = await api.post(`/staff/accounts/procurement/requirements/${id}/trigger`);
      if (res.data?.success || res.status === 200) {
        showToast("Procurement triggered successfully!");
        loadRequirements();
      } else {
        showToast(res.data?.message || "Failed to trigger procurement", "error");
      }
    } catch (e: any) {
      showToast(e.response?.data?.detail || "Failed to trigger", "error");
    }
  };

  const createRequestFromRequirements = () => {
    if (!selectedReqIds.length) {
      showToast("Please select at least one requirement", "error");
      return;
    }

    const itemsToAdd: ProcurementRequestItem[] = [];
    let firstCompany = "";

    selectedReqIds.forEach((id) => {
      const req = requirements.find((r) => r.id === id);
      if (req) {
        if (!firstCompany && req.company_id) firstCompany = String(req.company_id);
        (req.line_items || []).forEach((li) => {
          const itemId = li.component_id || li.stock_item_id;
          const existing = itemsToAdd.find((i) => i.item_id === itemId);
          if (existing) {
            existing.required_qty += li.shortage_qty || 0;
          } else {
            itemsToAdd.push({
              item_id: itemId,
              item_code: li.component_code || li.stock_item_code || "N/A",
              item_name: li.component_name || li.stock_item_name || "Unknown Item",
              required_qty: li.shortage_qty || 1,
              unit_of_measure: li.unit_of_measure || "PCS",
            });
          }
        });
      }
    });

    if (!itemsToAdd.length) {
      showToast("No line items found in selected requirements", "info");
      return;
    }

    setCreateCompanyId(firstCompany || selectedCompanyId || (companies[0] ? String(companies[0].id) : ""));
    setCreateItems(itemsToAdd);
    setCreateMinQuotes(2);
    setCreateNotes("");
    setCreateModalOpen(true);
  };

  // ── Tab 4: Low Stock Items ───────────────────────────────────────────────────

  const loadLowStock = async () => {
    try {
      setLowStockLoading(true);
      let url = `/staff/accounts/procurement/low-stock?page=1&limit=50`;
      if (selectedCompanyId) url += `&company_id=${selectedCompanyId}`;
      if (lowStockCategory) url += `&category=${lowStockCategory}`;
      if (lowStockSearch.trim()) url += `&search=${encodeURIComponent(lowStockSearch.trim())}`;

      const res = await api.get(url);
      const items = res.data?.items || res.data || [];
      setLowStockItems(Array.isArray(items) ? items : []);
      setLowStockCount(res.data?.total || items.length || 0);
    } catch (e) {
      console.error("Load low stock error:", e);
      setLowStockItems([]);
    } finally {
      setLowStockLoading(false);
    }
  };

  const createRequestFromLowStock = () => {
    if (!selectedLowStockIds.length) {
      showToast("Please select at least one low stock item", "error");
      return;
    }

    const itemsToAdd: ProcurementRequestItem[] = [];
    let firstCompany = "";

    selectedLowStockIds.forEach((id) => {
      const it = lowStockItems.find((i) => i.item_id === id);
      if (it) {
        if (!firstCompany && it.company_id) firstCompany = String(it.company_id);
        itemsToAdd.push({
          item_id: it.item_id,
          item_code: it.item_code,
          item_name: it.item_name,
          required_qty: it.shortage_qty || 1,
          unit_of_measure: it.unit_of_measure || "PCS",
        });
      }
    });

    setCreateCompanyId(firstCompany || selectedCompanyId || (companies[0] ? String(companies[0].id) : ""));
    setCreateItems(itemsToAdd);
    setCreateMinQuotes(2);
    setCreateNotes("");
    setCreateModalOpen(true);
  };

  // ── Tab 5: Aggregated Shortages ──────────────────────────────────────────────

  const loadAggregated = async () => {
    try {
      setAggLoading(true);
      let url = `/staff/accounts/procurement/aggregated-shortages`;
      if (selectedCompanyId) url += `?company_id=${selectedCompanyId}`;

      const res = await api.get(url);
      const shortages = res.data?.shortages || res.data || [];
      setAggregatedShortages(Array.isArray(shortages) ? shortages : []);
    } catch (e) {
      console.error("Load aggregated shortages error:", e);
      setAggregatedShortages([]);
    } finally {
      setAggLoading(false);
    }
  };

  const createRequestFromAggregated = () => {
    if (!selectedAggIndices.length) {
      showToast("Please select at least one aggregated shortage", "error");
      return;
    }

    const itemsToAdd: ProcurementRequestItem[] = [];
    selectedAggIndices.forEach((idx) => {
      const it = aggregatedShortages[idx];
      if (it) {
        itemsToAdd.push({
          item_id: it.component_id,
          item_code: it.component_code,
          item_name: it.component_name,
          required_qty: it.total_shortage || 1,
          unit_of_measure: it.unit_of_measure || "PCS",
        });
      }
    });

    setCreateCompanyId(selectedCompanyId || (companies[0] ? String(companies[0].id) : ""));
    setCreateItems(itemsToAdd);
    setCreateMinQuotes(2);
    setCreateNotes("");
    setCreateModalOpen(true);
  };

  // ── Tab 6: Market Place ──────────────────────────────────────────────────────

  const loadMarketplaceItems = async () => {
    try {
      setMktLoading(true);
      let url = `/staff/accounts/procurement/marketplace-items`;
      const params: string[] = [];
      if (selectedCompanyId) params.push(`company_id=${selectedCompanyId}`);
      if (mktSourceFilter) params.push(`source_type=${encodeURIComponent(mktSourceFilter)}`);
      if (params.length) url += "?" + params.join("&");

      const res = await api.get(url);
      const items = res.data?.items || res.data || [];
      setMktItems(Array.isArray(items) ? items : []);
    } catch (e) {
      console.error("Load marketplace items error:", e);
      setMktItems([]);
    } finally {
      setMktLoading(false);
    }
  };

  const filteredMarketplaceItems = useMemo(() => {
    let list = [...mktItems];
    if (mktSearch.trim()) {
      const s = mktSearch.toLowerCase();
      list = list.filter((i) => (i.item_code || "").toLowerCase().includes(s) || (i.item_name || "").toLowerCase().includes(s));
    }
    return list;
  }, [mktItems, mktSearch]);

  // ── Create Procurement Request Logic ──

  const handleSearchStockItems = async (term: string) => {
    setItemSearchTerm(term);
    if (!term || term.length < 2) {
      setItemSearchResults([]);
      return;
    }

    try {
      let url = `/staff/accounts/stock-items?search=${encodeURIComponent(term)}&limit=10`;
      if (createCompanyId) url += `&company_id=${createCompanyId}`;

      const res = await api.get(url);
      const items = res.data?.items || res.data?.data || res.data || [];
      setItemSearchResults(Array.isArray(items) ? items : []);
    } catch (e) {
      setItemSearchResults([]);
    }
  };

  const addItemToCreateList = (item: any) => {
    const existingIdx = createItems.findIndex((i) => i.item_id === item.id);
    if (existingIdx >= 0) {
      setCreateItems((prev) =>
        prev.map((it, idx) => (idx === existingIdx ? { ...it, required_qty: it.required_qty + (itemQtyToAdd || 1) } : it))
      );
    } else {
      setCreateItems((prev) => [
        ...prev,
        {
          item_id: item.id,
          item_code: item.item_code,
          item_name: item.item_name,
          required_qty: itemQtyToAdd || 1,
          unit_of_measure: item.unit_of_measure || "PCS",
          item_category: item.item_category,
        },
      ]);
    }
    setItemSearchTerm("");
    setItemSearchResults([]);
    setItemQtyToAdd(1);
  };

  const submitCreateRequest = async () => {
    if (!createCompanyId) {
      showToast("Please select a company", "error");
      return;
    }
    if (!createItems.length) {
      showToast("Please add at least one item to procure", "error");
      return;
    }

    try {
      setCreateSubmitting(true);
      const payload = {
        company_id: parseInt(createCompanyId),
        min_quotes_required: createMinQuotes || 2,
        notes: createNotes || null,
        items: createItems.map((i) => ({
          item_id: i.item_id,
          required_qty: i.required_qty,
          unit_of_measure: i.unit_of_measure || "PCS",
          specifications: i.specifications || null,
          source_type: "LOW_STOCK",
        })),
      };

      const res = await api.post("/staff/accounts/procurement/requests", payload);
      if (res.data?.success || res.status === 200 || res.status === 201) {
        showToast(`Procurement Request ${res.data?.data?.request_number || ""} created!`);
        setCreateModalOpen(false);
        setCreateItems([]);
        setSelectedReqIds([]);
        setSelectedLowStockIds([]);
        setSelectedAggIndices([]);
        setActiveTab("requests");
        loadProcurementRequests();
      } else {
        showToast(res.data?.message || "Failed to create request", "error");
      }
    } catch (e: any) {
      showToast(e.response?.data?.detail || "Failed to create procurement request", "error");
    } finally {
      setCreateSubmitting(false);
    }
  };

  return (
    <div className="space-y-6 max-w-[1600px] mx-auto pb-16">
      {/* Toast Alert Notification */}
      {toastMessage && (
        <div
          className={`fixed top-6 right-6 z-[9999] flex items-center gap-3 px-5 py-3.5 rounded-xl shadow-2xl font-semibold text-sm transition-all duration-300 ${
            toastMessage.type === "success"
              ? "bg-emerald-600 text-white"
              : toastMessage.type === "error"
              ? "bg-rose-600 text-white"
              : "bg-indigo-600 text-white"
          }`}
        >
          {toastMessage.type === "success" ? (
            <CheckCircle2 className="w-5 h-5" />
          ) : toastMessage.type === "error" ? (
            <XCircle className="w-5 h-5" />
          ) : (
            <Info className="w-5 h-5" />
          )}
          <span>{toastMessage.text}</span>
          <button onClick={() => setToastMessage(null)} className="ml-2 hover:opacity-80">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* ── Page Header ────────────────────────────────────────────────────────── */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 bg-white p-6 rounded-2xl shadow-sm border border-slate-100">
        <div>
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-xl text-white shadow-md shadow-indigo-200">
              <FileText className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Procurement Requirements</h1>
              <p className="text-sm text-slate-500 mt-0.5">Multi-quote procurement workflow with material tracking & blind bidding</p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <Button
            onClick={() => {
              setCreateCompanyId(selectedCompanyId || (companies[0] ? String(companies[0].id) : ""));
              setCreateItems([]);
              setCreateMinQuotes(2);
              setCreateNotes("");
              setCreateModalOpen(true);
            }}
            className="bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-700 hover:to-indigo-700 text-white shadow-md shadow-purple-200 font-semibold px-5 py-2.5 rounded-xl flex items-center gap-2 cursor-pointer transition-all duration-200"
          >
            <Plus className="w-4 h-4" />
            Create Procurement Request
          </Button>
        </div>
      </div>

      {/* ── Summary Stats Cards ────────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card className="border-l-4 border-l-rose-500 shadow-sm hover:shadow transition-shadow">
          <CardContent className="p-4 flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Urgent Requirements</p>
              <h3 className="text-2xl font-bold text-slate-900 mt-1">{urgentCount}</h3>
            </div>
            <div className="p-3 bg-rose-50 text-rose-600 rounded-xl">
              <AlertTriangle className="w-6 h-6" />
            </div>
          </CardContent>
        </Card>

        <Card className="border-l-4 border-l-amber-500 shadow-sm hover:shadow transition-shadow">
          <CardContent className="p-4 flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Pending Requirements</p>
              <h3 className="text-2xl font-bold text-slate-900 mt-1">{pendingCount}</h3>
            </div>
            <div className="p-3 bg-amber-50 text-amber-600 rounded-xl">
              <Clock className="w-6 h-6" />
            </div>
          </CardContent>
        </Card>

        <Card className="border-l-4 border-l-indigo-500 shadow-sm hover:shadow transition-shadow">
          <CardContent className="p-4 flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Active Requests</p>
              <h3 className="text-2xl font-bold text-slate-900 mt-1">{requestsCount}</h3>
            </div>
            <div className="p-3 bg-indigo-50 text-indigo-600 rounded-xl">
              <FileText className="w-6 h-6" />
            </div>
          </CardContent>
        </Card>

        <Card className="border-l-4 border-l-purple-500 shadow-sm hover:shadow transition-shadow">
          <CardContent className="p-4 flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Low Stock Items</p>
              <h3 className="text-2xl font-bold text-slate-900 mt-1">{lowStockCount}</h3>
            </div>
            <div className="p-3 bg-purple-50 text-purple-600 rounded-xl">
              <Boxes className="w-6 h-6" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* ── Navigation Tabs ────────────────────────────────────────────────────── */}
      <div className="bg-white rounded-2xl p-1.5 shadow-sm border border-slate-200 flex flex-wrap gap-1">
        <button
          onClick={() => setActiveTab("requests")}
          className={`flex-1 min-w-[140px] py-3 px-4 rounded-xl text-xs md:text-sm font-semibold transition-all duration-200 flex items-center justify-center gap-2 cursor-pointer ${
            activeTab === "requests"
              ? "bg-gradient-to-r from-purple-600 to-indigo-600 text-white shadow-md shadow-purple-100"
              : "text-slate-600 hover:text-slate-900 hover:bg-slate-50"
          }`}
        >
          <FileText className="w-4 h-4" />
          Procurement Requests
        </button>

        <button
          onClick={() => setActiveTab("spareitems")}
          className={`flex-1 min-w-[140px] py-3 px-4 rounded-xl text-xs md:text-sm font-semibold transition-all duration-200 flex items-center justify-center gap-2 cursor-pointer ${
            activeTab === "spareitems"
              ? "bg-gradient-to-r from-purple-600 to-indigo-600 text-white shadow-md shadow-purple-100"
              : "text-slate-600 hover:text-slate-900 hover:bg-slate-50"
          }`}
        >
          <Layers className="w-4 h-4" />
          Consolidated
        </button>

        <button
          onClick={() => setActiveTab("requirements")}
          className={`flex-1 min-w-[140px] py-3 px-4 rounded-xl text-xs md:text-sm font-semibold transition-all duration-200 flex items-center justify-center gap-2 cursor-pointer ${
            activeTab === "requirements"
              ? "bg-gradient-to-r from-purple-600 to-indigo-600 text-white shadow-md shadow-purple-100"
              : "text-slate-600 hover:text-slate-900 hover:bg-slate-50"
          }`}
        >
          <ClipboardList className="w-4 h-4" />
          Material Requirements
        </button>

        <button
          onClick={() => setActiveTab("lowstock")}
          className={`flex-1 min-w-[140px] py-3 px-4 rounded-xl text-xs md:text-sm font-semibold transition-all duration-200 flex items-center justify-center gap-2 cursor-pointer ${
            activeTab === "lowstock"
              ? "bg-gradient-to-r from-purple-600 to-indigo-600 text-white shadow-md shadow-purple-100"
              : "text-slate-600 hover:text-slate-900 hover:bg-slate-50"
          }`}
        >
          <AlertTriangle className="w-4 h-4" />
          Low Stock Items
        </button>

        <button
          onClick={() => setActiveTab("aggregated")}
          className={`flex-1 min-w-[140px] py-3 px-4 rounded-xl text-xs md:text-sm font-semibold transition-all duration-200 flex items-center justify-center gap-2 cursor-pointer ${
            activeTab === "aggregated"
              ? "bg-gradient-to-r from-purple-600 to-indigo-600 text-white shadow-md shadow-purple-100"
              : "text-slate-600 hover:text-slate-900 hover:bg-slate-50"
          }`}
        >
          <Boxes className="w-4 h-4" />
          Aggregated Shortages
        </button>

        <button
          onClick={() => setActiveTab("vgkproc")}
          className={`flex-1 min-w-[140px] py-3 px-4 rounded-xl text-xs md:text-sm font-semibold transition-all duration-200 flex items-center justify-center gap-2 cursor-pointer ${
            activeTab === "vgkproc"
              ? "bg-gradient-to-r from-purple-600 to-indigo-600 text-white shadow-md shadow-purple-100"
              : "text-slate-600 hover:text-slate-900 hover:bg-slate-50"
          }`}
        >
          <Store className="w-4 h-4" />
          Market Place
        </button>
      </div>

      {/* ── Filters Section ────────────────────────────────────────────────────── */}
      <div className="bg-white p-4 rounded-2xl shadow-sm border border-slate-200 flex flex-wrap gap-4 items-end">
        {/* Company Filter (common across tabs) */}
        <div className="flex flex-col gap-1.5 min-w-[200px]">
          <Label className="text-xs font-semibold text-slate-600">Company</Label>
          <select
            value={selectedCompanyId}
            onChange={(e) => setSelectedCompanyId(e.target.value)}
            className="w-full h-10 px-3 border border-slate-300 rounded-xl text-sm bg-white text-slate-700 outline-none focus:ring-2 focus:ring-purple-500"
          >
            <option value="">All Companies</option>
            {companies.map((c) => (
              <option key={c.id} value={c.id}>
                {c.company_name}
              </option>
            ))}
          </select>
        </div>

        {/* Requests Tab Filters */}
        {activeTab === "requests" && (
          <div className="flex flex-col gap-1.5 min-w-[200px]">
            <Label className="text-xs font-semibold text-slate-600">Request Status</Label>
            <select
              value={requestStatusFilter}
              onChange={(e) => setRequestStatusFilter(e.target.value)}
              className="w-full h-10 px-3 border border-slate-300 rounded-xl text-sm bg-white text-slate-700 outline-none focus:ring-2 focus:ring-purple-500"
            >
              <option value="">All Statuses</option>
              <option value="DRAFT">Draft</option>
              <option value="SENT_TO_VENDORS">Sent to Vendors</option>
              <option value="QUOTES_RECEIVED">Quotes Received</option>
              <option value="QUOTE_APPROVED">Quote Approved</option>
              <option value="PO_CREATED">PO Created</option>
              <option value="COMPLETED">Completed</option>
              <option value="CANCELLED">Cancelled</option>
              <option value="RETURNED_FOR_QUALITY">Returned for Quality</option>
            </select>
          </div>
        )}

        {/* Requirements Tab Filters */}
        {activeTab === "requirements" && (
          <>
            <div className="flex flex-col gap-1.5 min-w-[180px]">
              <Label className="text-xs font-semibold text-slate-600">Status</Label>
              <select
                value={reqStatusFilter}
                onChange={(e) => setReqStatusFilter(e.target.value)}
                className="w-full h-10 px-3 border border-slate-300 rounded-xl text-sm bg-white text-slate-700 outline-none focus:ring-2 focus:ring-purple-500"
              >
                <option value="">All Statuses</option>
                <option value="PENDING">Pending</option>
                <option value="ACKNOWLEDGED">Acknowledged</option>
                <option value="IN_PROGRESS">In Progress</option>
                <option value="COMPLETED">Completed</option>
              </select>
            </div>
            <div className="flex flex-col gap-1.5 min-w-[180px]">
              <Label className="text-xs font-semibold text-slate-600">Priority</Label>
              <select
                value={reqPriorityFilter}
                onChange={(e) => setReqPriorityFilter(e.target.value)}
                className="w-full h-10 px-3 border border-slate-300 rounded-xl text-sm bg-white text-slate-700 outline-none focus:ring-2 focus:ring-purple-500"
              >
                <option value="">All Priorities</option>
                <option value="URGENT">Urgent</option>
                <option value="HIGH">High</option>
                <option value="NORMAL">Normal</option>
                <option value="LOW">Low</option>
              </select>
            </div>
          </>
        )}

        {/* Low Stock Tab Filters */}
        {activeTab === "lowstock" && (
          <>
            <div className="flex flex-col gap-1.5 min-w-[180px]">
              <Label className="text-xs font-semibold text-slate-600">Category</Label>
              <select
                value={lowStockCategory}
                onChange={(e) => setLowStockCategory(e.target.value)}
                className="w-full h-10 px-3 border border-slate-300 rounded-xl text-sm bg-white text-slate-700 outline-none focus:ring-2 focus:ring-purple-500"
              >
                <option value="">All Categories</option>
                <option value="PRODUCT">Product</option>
                <option value="RAW_MATERIAL">Raw Material</option>
                <option value="CONSUMABLE">Consumable</option>
                <option value="SPARE_PART">Spare Part</option>
              </select>
            </div>
            <div className="flex flex-col gap-1.5 min-w-[240px]">
              <Label className="text-xs font-semibold text-slate-600">Search</Label>
              <div className="relative">
                <Search className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
                <Input
                  type="text"
                  placeholder="Item code or name..."
                  value={lowStockSearch}
                  onChange={(e) => setLowStockSearch(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && loadLowStock()}
                  className="pl-9 h-10 rounded-xl"
                />
              </div>
            </div>
            <Button onClick={loadLowStock} variant="outline" className="h-10 rounded-xl">
              Filter
            </Button>
          </>
        )}

        <Button onClick={loadData} variant="ghost" className="h-10 text-slate-600 hover:text-slate-900 ml-auto">
          <RefreshCw className="w-4 h-4 mr-2" />
          Refresh
        </Button>
      </div>

      {/* ══════════════════════════════════════════════════════════════════════════
          TAB 1: PROCUREMENT REQUESTS (MULTI-QUOTE WORKFLOW)
          ══════════════════════════════════════════════════════════════════════════ */}
      {activeTab === "requests" && (
        <Card className="rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
          <CardHeader className="bg-slate-50/50 border-b border-slate-100 flex flex-row items-center justify-between py-4 px-6">
            <div className="flex items-center gap-2">
              <FileText className="w-5 h-5 text-purple-600" />
              <CardTitle className="text-base font-bold text-slate-900">
                Procurement Requests (Multi-Quote Workflow)
              </CardTitle>
            </div>
            <Badge variant="secondary" className="font-semibold text-xs px-2.5 py-1">
              {procRequests.length} requests
            </Badge>
          </CardHeader>

          <CardContent className="p-0">
            {requestsLoading ? (
              <div className="p-16 text-center text-slate-500">
                <RefreshCw className="w-8 h-8 animate-spin mx-auto text-purple-600 mb-3" />
                <p className="text-sm font-medium">Loading procurement requests...</p>
              </div>
            ) : procRequests.length === 0 ? (
              <div className="p-16 text-center text-slate-500 flex flex-col items-center">
                <div className="w-16 h-16 bg-purple-50 text-purple-600 rounded-full flex items-center justify-center mb-4">
                  <FileText className="w-8 h-8" />
                </div>
                <h3 className="text-lg font-bold text-slate-900 mb-1">No Procurement Requests</h3>
                <p className="text-sm text-slate-500 max-w-md mb-6">
                  Create a new request or generate one from Material Requirements to start the multi-quote workflow.
                </p>
                <Button
                  onClick={() => {
                    setCreateCompanyId(selectedCompanyId || (companies[0] ? String(companies[0].id) : ""));
                    setCreateItems([]);
                    setCreateModalOpen(true);
                  }}
                  className="bg-purple-600 hover:bg-purple-700 text-white rounded-xl"
                >
                  <Plus className="w-4 h-4 mr-2" />
                  Create Request
                </Button>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse text-sm">
                  <thead>
                    <tr className="bg-slate-50/75 border-b border-slate-200 text-xs font-bold text-slate-500 uppercase tracking-wider">
                      <th className="py-3.5 px-4">Request #</th>
                      <th className="py-3.5 px-4">Company</th>
                      <th className="py-3.5 px-4">Approved Vendor</th>
                      <th className="py-3.5 px-4 text-center">Items</th>
                      <th className="py-3.5 px-4 text-center">Quotes</th>
                      <th className="py-3.5 px-4">Status</th>
                      <th className="py-3.5 px-4">Updated</th>
                      <th className="py-3.5 px-4 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {procRequests.map((r) => {
                      const statusInfo = STATUS_BADGES[r.status] || {
                        bg: "bg-slate-100",
                        text: "text-slate-700",
                        border: "border-slate-200",
                      };
                      const quotesCount = r.quotes_received_count || 0;
                      const minQuotes = r.min_quotes_required || 2;
                      const quotesSufficient = quotesCount >= minQuotes;

                      return (
                        <tr key={r.id} className="hover:bg-slate-50/60 transition-colors">
                          <td className="py-3.5 px-4 font-mono font-bold text-xs text-purple-700">
                            {r.request_number}
                          </td>
                          <td className="py-3.5 px-4 font-medium text-slate-800">
                            {r.company_name || "—"}
                          </td>
                          <td className="py-3.5 px-4">
                            {r.approved_vendor_name ? (
                              <div>
                                <span className="font-semibold text-blue-600">{r.approved_vendor_name}</span>
                                {r.approved_vendor_phone && (
                                  <span className="block text-xs text-slate-400">📱 {r.approved_vendor_phone}</span>
                                )}
                              </div>
                            ) : (
                              <span className="text-slate-400 text-xs">—</span>
                            )}
                          </td>
                          <td className="py-3.5 px-4 text-center font-semibold text-slate-700">
                            {r.items_count || r.item_count || r.items?.length || 0}
                          </td>
                          <td className="py-3.5 px-4 text-center">
                            <span
                              className={`font-bold text-xs px-2.5 py-0.5 rounded-full ${
                                quotesSufficient ? "bg-emerald-100 text-emerald-800" : "bg-amber-100 text-amber-800"
                              }`}
                            >
                              {quotesCount}/{minQuotes}
                            </span>
                          </td>
                          <td className="py-3.5 px-4">
                            <span
                              className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold border ${statusInfo.bg} ${statusInfo.text} ${statusInfo.border}`}
                            >
                              {r.status.replace(/_/g, " ")}
                            </span>
                          </td>
                          <td className="py-3.5 px-4 text-xs text-slate-500 whitespace-nowrap">
                            {formatDate(r.updated_at || r.created_at)}
                          </td>
                          <td className="py-3.5 px-4 text-right whitespace-nowrap">
                            <div className="flex items-center justify-end gap-1.5">
                              {/* View Details */}
                              <button
                                onClick={() => viewRequestDetails(r.id)}
                                title="View Details"
                                className="p-1.5 bg-blue-50 text-blue-600 hover:bg-blue-100 rounded-lg transition-colors cursor-pointer"
                              >
                                <Eye className="w-4 h-4" />
                              </button>

                              {/* Add Quote (if DRAFT or SENT_TO_VENDORS) */}
                              {(r.status === "DRAFT" || r.status === "SENT_TO_VENDORS") && (
                                <button
                                  onClick={() => openAddQuoteModal(r.id)}
                                  title="Add Vendor Quote"
                                  className="p-1.5 bg-purple-50 text-purple-600 hover:bg-purple-100 rounded-lg transition-colors cursor-pointer"
                                >
                                  <Plus className="w-4 h-4" />
                                </button>
                              )}

                              {/* Review Quotes (if QUOTES_RECEIVED) */}
                              {r.status === "QUOTES_RECEIVED" && (
                                <button
                                  onClick={() => viewRequestDetails(r.id)}
                                  title="Review & Approve Quotes"
                                  className="p-1.5 bg-emerald-50 text-emerald-600 hover:bg-emerald-100 rounded-lg transition-colors cursor-pointer font-bold"
                                >
                                  <Check className="w-4 h-4" />
                                </button>
                              )}

                              {/* Update Status */}
                              <button
                                onClick={() => openStatusModal(r.id)}
                                title="Update Request Status"
                                className="p-1.5 bg-slate-100 text-slate-700 hover:bg-slate-200 rounded-lg transition-colors cursor-pointer"
                              >
                                <Edit className="w-4 h-4" />
                              </button>

                              {/* Send WhatsApp */}
                              <button
                                onClick={() => openWhatsAppModal(r.id)}
                                title={
                                  r.approved_vendor_name
                                    ? `Send WhatsApp to ${r.approved_vendor_name}`
                                    : "WhatsApp (Requires vendor approval)"
                                }
                                className="p-1.5 bg-emerald-50 text-emerald-600 hover:bg-emerald-100 rounded-lg transition-colors cursor-pointer"
                              >
                                <MessageCircle className="w-4 h-4" />
                              </button>

                              {/* Download Text Spec */}
                              <button
                                onClick={() => downloadRequestDoc(r.id)}
                                title="Download Request Spec Document"
                                className="p-1.5 bg-amber-50 text-amber-700 hover:bg-amber-100 rounded-lg transition-colors cursor-pointer"
                              >
                                <Download className="w-4 h-4" />
                              </button>
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* ══════════════════════════════════════════════════════════════════════════
          TAB 2: CONSOLIDATED SPARE PARTS (SPO WORKBENCH + CART)
          ══════════════════════════════════════════════════════════════════════════ */}
      {activeTab === "spareitems" && (
        <div className="space-y-6">
          {/* Spare Purchase Orders List */}
          <Card className="rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
            <CardHeader className="bg-slate-50/50 border-b border-slate-100 flex flex-row items-center justify-between py-4 px-6">
              <div className="flex items-center gap-2">
                <Layers className="w-5 h-5 text-indigo-600" />
                <CardTitle className="text-base font-bold text-slate-900">Spare Purchase Orders</CardTitle>
              </div>

              <div className="flex items-center gap-3">
                <select
                  value={spoStatusFilter}
                  onChange={(e) => {
                    setSpoStatusFilter(e.target.value);
                  }}
                  className="h-9 px-3 border border-slate-300 rounded-xl text-xs bg-white text-slate-700 outline-none"
                >
                  <option value="">All Orders</option>
                  <option value="DRAFT">Draft</option>
                  <option value="WAITING_APPROVAL">Waiting Approval</option>
                  <option value="APPROVED">Approved</option>
                  <option value="CANCELLED">Cancelled</option>
                </select>

                <Button onClick={loadSpareOrders} variant="outline" size="sm" className="h-9 rounded-xl">
                  <RefreshCw className="w-3.5 h-3.5" />
                </Button>
              </div>
            </CardHeader>

            <CardContent className="p-0">
              {spareOrdersLoading ? (
                <div className="p-8 text-center text-slate-500">
                  <RefreshCw className="w-6 h-6 animate-spin mx-auto text-indigo-600 mb-2" />
                  <p className="text-xs">Loading spare orders...</p>
                </div>
              ) : spareOrders.length === 0 ? (
                <div className="p-8 text-center text-slate-500">
                  <p className="text-sm">No spare purchase orders recorded yet.</p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-left border-collapse text-xs">
                    <thead>
                      <tr className="bg-slate-50/75 border-b border-slate-200 font-bold text-slate-500 uppercase tracking-wider">
                        <th className="py-3 px-4">Order #</th>
                        <th className="py-3 px-4">Company</th>
                        <th className="py-3 px-4">Vendor(s)</th>
                        <th className="py-3 px-4 text-center">Items</th>
                        <th className="py-3 px-4">Status</th>
                        <th className="py-3 px-4">Updated</th>
                        <th className="py-3 px-4 text-right">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {spareOrders.map((o) => {
                        const statusInfo = STATUS_BADGES[o.status] || {
                          bg: "bg-slate-100",
                          text: "text-slate-700",
                          border: "border-slate-200",
                        };
                        const vendorIds = [...new Set((o.lines || []).filter((l) => l.vendor_id).map((l) => l.vendor_id))];
                        const vendorNames = vendorIds.map((vid) => {
                          const vl = (o.lines || []).find((l) => l.vendor_id === vid);
                          return vl?.vendor_name || `V${vid}`;
                        });

                        return (
                          <tr key={o.id} className="hover:bg-slate-50/60 transition-colors">
                            <td className="py-3 px-4 font-mono font-bold text-indigo-600">{o.order_number}</td>
                            <td className="py-3 px-4 font-medium text-slate-800">{o.company_name || "—"}</td>
                            <td className="py-3 px-4">
                              {vendorNames.length ? (
                                <div className="flex flex-wrap gap-1">
                                  {vendorNames.map((v, idx) => (
                                    <span
                                      key={idx}
                                      className="px-2 py-0.5 bg-blue-50 text-blue-700 border border-blue-200 rounded-md font-semibold text-[11px]"
                                    >
                                      {v}
                                    </span>
                                  ))}
                                </div>
                              ) : (
                                <span className="text-slate-400">—</span>
                              )}
                            </td>
                            <td className="py-3 px-4 text-center font-semibold text-slate-700">
                              {o.line_count || o.lines?.length || 0} item(s)
                            </td>
                            <td className="py-3 px-4">
                              <span
                                className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold border ${statusInfo.bg} ${statusInfo.text} ${statusInfo.border}`}
                              >
                                {o.status.replace(/_/g, " ")}
                              </span>
                            </td>
                            <td className="py-3 px-4 text-slate-500 whitespace-nowrap">
                              {formatDate(o.updated_at || o.created_at)}
                            </td>
                            <td className="py-3 px-4 text-right whitespace-nowrap">
                              <div className="flex items-center justify-end gap-1.5 flex-wrap">
                                {/* PDF buttons per vendor */}
                                {vendorIds.length === 0 ? (
                                  <button
                                    onClick={() => downloadSpoPDF(o.id, null)}
                                    className="px-2 py-1 bg-slate-100 text-slate-600 hover:bg-slate-200 rounded text-[11px] font-semibold cursor-pointer"
                                  >
                                    PDF
                                  </button>
                                ) : (
                                  vendorIds.map((vid) => {
                                    const vline = (o.lines || []).find((l) => l.vendor_id === vid);
                                    return (
                                      <button
                                        key={String(vid)}
                                        onClick={() => downloadSpoPDF(o.id, vid as number)}
                                        title={`Download PDF for ${vline?.vendor_name || "Vendor"}`}
                                        className="px-2 py-1 bg-blue-50 text-blue-700 hover:bg-blue-100 border border-blue-200 rounded text-[11px] font-semibold cursor-pointer"
                                      >
                                        📄 {(vline?.vendor_name || `V${vid}`).substring(0, 10)}
                                      </button>
                                    );
                                  })
                                )}

                                {/* Review & Approve (if WAITING_APPROVAL) */}
                                {o.status === "WAITING_APPROVAL" && (
                                  <button
                                    onClick={() => openSpoApproveModal(o.id, o.order_number)}
                                    className="px-2.5 py-1 bg-emerald-600 hover:bg-emerald-700 text-white rounded text-[11px] font-bold cursor-pointer"
                                  >
                                    Review & Approve
                                  </button>
                                )}

                                {/* Convert to Purchase (if APPROVED) */}
                                {o.status === "APPROVED" && (
                                  <div className="flex gap-1">
                                    {vendorIds.map((vid) => {
                                      const vname = (o.lines || []).find((l) => l.vendor_id === vid)?.vendor_name || `Vendor ${vid}`;
                                      return (
                                        <button
                                          key={String(vid)}
                                          onClick={() => convertSpoToPurchase(o.id, vid as number, vname)}
                                          className="px-2 py-1 bg-purple-600 hover:bg-purple-700 text-white rounded text-[11px] font-semibold cursor-pointer flex items-center gap-1"
                                        >
                                          Purchase <ArrowRight className="w-3 h-3" />
                                        </button>
                                      );
                                    })}
                                  </div>
                                )}

                                {/* WhatsApp per vendor */}
                                {(o.status === "APPROVED" || o.status === "WAITING_APPROVAL") &&
                                  vendorIds.map((vid) => {
                                    const vl = (o.lines || []).find((l) => l.vendor_id === vid);
                                    return (
                                      <button
                                        key={String(vid)}
                                        onClick={() => sendSpoWhatsApp(o.id, vid as number, vl?.vendor_name || "Vendor", o.order_number)}
                                        title={`Send WA to ${vl?.vendor_name || "Vendor"}`}
                                        className="p-1 bg-emerald-50 text-emerald-600 hover:bg-emerald-100 rounded cursor-pointer"
                                      >
                                        <MessageCircle className="w-3.5 h-3.5" />
                                      </button>
                                    );
                                  })}

                                {/* Cancel Order */}
                                {(o.status === "DRAFT" || o.status === "WAITING_APPROVAL") && (
                                  <button
                                    onClick={() => cancelSpareOrder(o.id, o.order_number)}
                                    className="px-2 py-1 bg-rose-50 text-rose-600 hover:bg-rose-100 border border-rose-200 rounded text-[11px] font-semibold cursor-pointer"
                                  >
                                    Cancel
                                  </button>
                                )}
                              </div>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Cart Section (Active when items are in cart) */}
          {Object.keys(spareCart).length > 0 && (
            <Card className="rounded-2xl shadow-sm border-2 border-indigo-200 overflow-hidden bg-indigo-50/20">
              <CardHeader className="bg-indigo-100/50 border-b border-indigo-200 flex flex-row items-center justify-between py-3.5 px-6">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-indigo-600 text-white rounded-lg">
                    <ShoppingCart className="w-4 h-4" />
                  </div>
                  <div>
                    <CardTitle className="text-sm font-bold text-indigo-950">Purchase Order Draft</CardTitle>
                    <CardDescription className="text-xs text-indigo-700">
                      {Object.values(spareCart).reduce((sum, v) => sum + Object.keys(v.items).length, 0)} item(s) across{" "}
                      {Object.keys(spareCart).length} vendor group(s)
                    </CardDescription>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <Button onClick={clearSpareCart} variant="outline" size="sm" className="h-8 text-xs">
                    Clear
                  </Button>
                  <Button
                    onClick={saveSpareOrder}
                    size="sm"
                    className="h-8 text-xs bg-indigo-600 hover:bg-indigo-700 text-white"
                  >
                    Save Draft
                  </Button>
                  <Button
                    onClick={submitSpareOrder}
                    size="sm"
                    className="h-8 text-xs bg-emerald-600 hover:bg-emerald-700 text-white font-bold"
                  >
                    <Send className="w-3.5 h-3.5 mr-1.5" />
                    Submit for Approval
                  </Button>
                </div>
              </CardHeader>

              <CardContent className="p-4 space-y-4">
                {Object.entries(spareCart).map(([cartKey, v]) => {
                  const isTBD = cartKey === "__TBD__";
                  return (
                    <div key={cartKey} className="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-xs">
                      <div className="bg-slate-50 px-4 py-2.5 border-b border-slate-200 flex justify-between items-center text-xs">
                        <span className="font-bold flex items-center gap-2">
                          <Store className={`w-4 h-4 ${isTBD ? "text-amber-500" : "text-indigo-600"}`} />
                          {isTBD ? (
                            <span className="text-amber-600">Vendor TBD (assigned at approval)</span>
                          ) : (
                            <span className="text-slate-800">{v.vendor_name}</span>
                          )}
                        </span>
                        {!isTBD && v.vendor_phone && (
                          <span className="text-slate-500">📱 {v.vendor_phone}</span>
                        )}
                      </div>

                      <div className="divide-y divide-slate-100">
                        {Object.values(v.items).map((it) => {
                          const estAmount = it.rate ? it.qty * it.rate : 0;
                          return (
                            <div key={it.item_id} className="p-3 flex justify-between items-center text-xs">
                              <div>
                                <h4 className="font-bold text-slate-900">{it.item_name}</h4>
                                <div className="flex items-center gap-2 text-slate-500 mt-0.5">
                                  <code className="text-purple-600">{it.item_code}</code>
                                  {it.demand_source && <span>• {it.demand_source}</span>}
                                </div>
                              </div>

                              <div className="flex items-center gap-4">
                                <div className="flex items-center gap-1.5">
                                  <Label className="text-[11px] text-slate-500">Qty:</Label>
                                  <Input
                                    type="number"
                                    min="1"
                                    value={it.qty}
                                    onChange={(e) => updateCartItemQty(cartKey, it.item_id, parseFloat(e.target.value) || 1)}
                                    className="w-16 h-7 text-xs text-right font-semibold"
                                  />
                                  <span className="text-slate-400 text-[11px]">{it.uom}</span>
                                </div>

                                <div className="text-right min-w-[90px]">
                                  <div className="font-bold text-emerald-700">₹ {formatNumber(estAmount)}</div>
                                  <div className="text-[10px] text-slate-400">@ ₹{it.rate || 0}/unit</div>
                                </div>

                                <button
                                  onClick={() => removeCartItem(cartKey, it.item_id)}
                                  className="p-1 text-rose-500 hover:text-rose-700 hover:bg-rose-50 rounded"
                                >
                                  <Trash2 className="w-4 h-4" />
                                </button>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  );
                })}
              </CardContent>
            </Card>
          )}

          {/* Spare Parts Procurement Workbench */}
          <Card className="rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
            <CardHeader className="bg-slate-50/50 border-b border-slate-100 flex flex-row items-center justify-between py-4 px-6">
              <div className="flex items-center gap-2">
                <Boxes className="w-5 h-5 text-purple-600" />
                <CardTitle className="text-base font-bold text-slate-900">Spare Parts Procurement Workbench</CardTitle>
              </div>

              <div className="flex items-center gap-3">
                <span className="text-xs text-slate-500">{spareItems.length} spare parts</span>
                <Button onClick={loadSpareItems} size="sm" variant="outline" className="h-8 text-xs">
                  <RefreshCw className="w-3.5 h-3.5 mr-1" />
                  Refresh
                </Button>
              </div>
            </CardHeader>

            <CardContent className="p-4 space-y-4">
              {/* Workbench Filter Toolbar */}
              <div className="flex flex-wrap gap-3 items-center">
                <div className="relative flex-1 min-w-[220px]">
                  <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
                  <Input
                    type="text"
                    placeholder="Search item code or name..."
                    value={spareSearch}
                    onChange={(e) => setSpareSearch(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && loadSpareItems()}
                    className="pl-9 h-9 text-xs rounded-xl"
                  />
                </div>

                <select
                  value={spareStockFilter}
                  onChange={(e) => setSpareStockFilter(e.target.value)}
                  className="h-9 px-3 border border-slate-300 rounded-xl text-xs bg-white text-slate-700 outline-none"
                >
                  <option value="">All Stock Statuses</option>
                  <option value="CRITICAL">Critical (No Stock)</option>
                  <option value="LOW">Low (Has Demand)</option>
                  <option value="OK">OK</option>
                </select>

                <select
                  value={spareReqFromFilter}
                  onChange={(e) => setSpareReqFromFilter(e.target.value)}
                  className="h-9 px-3 border border-slate-300 rounded-xl text-xs bg-white text-slate-700 outline-none"
                >
                  <option value="">All Requirement Sources</option>
                  <option value="Manufacturing">Manufacturing</option>
                  <option value="Low Stock">Low Stock</option>
                  <option value="Partner Request">Partner Request</option>
                  <option value="Partner Order">Partner Order</option>
                  <option value="Service Ticket">Service Ticket</option>
                  <option value="Low Level">Low Level</option>
                </select>
              </div>

              {/* Workbench Table */}
              {spareLoading ? (
                <div className="p-12 text-center text-slate-500">
                  <RefreshCw className="w-6 h-6 animate-spin mx-auto text-purple-600 mb-2" />
                  <p className="text-xs">Loading spare parts...</p>
                </div>
              ) : filteredSortedSpareItems.length === 0 ? (
                <div className="p-12 text-center text-slate-500">
                  <p className="text-sm">No spare parts matching the filters.</p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-left border-collapse text-xs">
                    <thead>
                      <tr className="bg-slate-50/75 border-b border-slate-200 font-bold text-slate-500 uppercase tracking-wider">
                        <th
                          className="py-3 px-3 cursor-pointer select-none"
                          onClick={() => handleSortSpare("item_code")}
                        >
                          Item Code {spareSortField === "item_code" && (spareSortDir === "asc" ? "↑" : "↓")}
                        </th>
                        <th
                          className="py-3 px-3 cursor-pointer select-none"
                          onClick={() => handleSortSpare("item_name")}
                        >
                          Item Name {spareSortField === "item_name" && (spareSortDir === "asc" ? "↑" : "↓")}
                        </th>
                        <th
                          className="py-3 px-3 text-center cursor-pointer select-none"
                          onClick={() => handleSortSpare("unit_of_measure")}
                        >
                          UoM
                        </th>
                        <th
                          className="py-3 px-3 text-center cursor-pointer select-none"
                          onClick={() => handleSortSpare("current_stock")}
                        >
                          Stock {spareSortField === "current_stock" && (spareSortDir === "asc" ? "↑" : "↓")}
                        </th>
                        <th className="py-3 px-3">Requirement From</th>
                        <th
                          className="py-3 px-3 text-center cursor-pointer select-none"
                          onClick={() => handleSortSpare("net_shortage")}
                        >
                          Net Shortage {spareSortField === "net_shortage" && (spareSortDir === "asc" ? "↑" : "↓")}
                        </th>
                        <th
                          className="py-3 px-3 text-center cursor-pointer select-none"
                          onClick={() => handleSortSpare("stock_status")}
                        >
                          Status
                        </th>
                        <th className="py-3 px-3 text-center">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {filteredSortedSpareItems.map((item) => {
                        const stockColor =
                          item.current_stock <= 0
                            ? "text-rose-600 font-bold"
                            : item.current_stock < (item.reorder_level || 5)
                            ? "text-amber-600 font-bold"
                            : "text-emerald-600 font-bold";

                        const shortageColor = item.net_shortage > 0 ? "text-rose-600 font-bold" : "text-emerald-600 font-bold";
                        const statusBadge =
                          item.stock_status === "CRITICAL"
                            ? "bg-rose-100 text-rose-800"
                            : item.stock_status === "LOW"
                            ? "bg-amber-100 text-amber-800"
                            : "bg-emerald-100 text-emerald-800";

                        const hasVendor = item.vendor_count > 0;

                        return (
                          <tr key={item.item_id} className="hover:bg-slate-50/60 transition-colors">
                            <td className="py-2.5 px-3 font-mono font-bold text-indigo-600">
                              {item.item_code}
                              {item.hsn_code && <div className="text-[10px] text-slate-400 font-normal">HSN: {item.hsn_code}</div>}
                            </td>
                            <td className="py-2.5 px-3">
                              <div className="font-semibold text-slate-900">{item.item_name}</div>
                              {item.model_compat && (
                                <div className="text-[10px] text-indigo-600 font-medium">Compat: {item.model_compat}</div>
                              )}
                              {item.specification && (
                                <div className="text-[10px] text-slate-500 line-clamp-1">{item.specification}</div>
                              )}
                            </td>
                            <td className="py-2.5 px-3 text-center text-slate-500">{item.unit_of_measure || "—"}</td>
                            <td className={`py-2.5 px-3 text-center ${stockColor}`}>{item.current_stock ?? 0}</td>
                            <td className="py-2.5 px-3">
                              <div className="flex flex-wrap gap-1">
                                {(item.req_sources || []).map((s, idx) => {
                                  const tagStyle = REQ_TAGS[s] || { bg: "bg-slate-100 text-slate-700" };
                                  return (
                                    <span
                                      key={idx}
                                      className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${tagStyle.bg}`}
                                    >
                                      {s}
                                    </span>
                                  );
                                })}
                              </div>
                            </td>
                            <td className={`py-2.5 px-3 text-center ${shortageColor}`}>
                              {item.net_shortage > 0 ? `⚠ ${item.net_shortage}` : "✓ 0"}
                            </td>
                            <td className="py-2.5 px-3 text-center">
                              <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${statusBadge}`}>
                                {item.stock_status}
                              </span>
                            </td>
                            <td className="py-2.5 px-3 text-center whitespace-nowrap">
                              <div className="flex items-center justify-center gap-1.5">
                                <button
                                  onClick={() => quickAddSpareToCart(item)}
                                  className="px-2.5 py-1 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg font-semibold text-[11px] cursor-pointer flex items-center gap-1"
                                >
                                  <Plus className="w-3 h-3" /> Quick Add
                                </button>

                                <button
                                  onClick={() => openVendorPanel(item)}
                                  className={`px-2.5 py-1 rounded-lg font-semibold text-[11px] cursor-pointer flex items-center gap-1 ${
                                    hasVendor
                                      ? "bg-indigo-50 text-indigo-700 hover:bg-indigo-100 border border-indigo-200"
                                      : "bg-slate-100 text-slate-400 cursor-not-allowed"
                                  }`}
                                  disabled={!hasVendor}
                                >
                                  <Store className="w-3 h-3" />
                                  {hasVendor ? `Vendor (${item.vendor_count})` : "No Vendor"}
                                </button>
                              </div>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}

      {/* ══════════════════════════════════════════════════════════════════════════
          TAB 3: MATERIAL REQUIREMENTS
          ══════════════════════════════════════════════════════════════════════════ */}
      {activeTab === "requirements" && (
        <div className="space-y-4">
          {/* Floating Selection Bar */}
          {selectedReqIds.length > 0 && (
            <div className="bg-gradient-to-r from-purple-600 to-indigo-600 text-white p-3 px-5 rounded-xl shadow-lg flex justify-between items-center animate-in fade-in duration-200">
              <span className="font-semibold text-sm">
                <span className="font-bold">{selectedReqIds.length}</span> requirements selected
              </span>
              <div className="flex items-center gap-2">
                <Button
                  onClick={() => setSelectedReqIds([])}
                  variant="outline"
                  size="sm"
                  className="bg-white/10 text-white hover:bg-white/20 border-white/30 h-8 text-xs"
                >
                  Clear Selection
                </Button>
                <Button
                  onClick={createRequestFromRequirements}
                  size="sm"
                  className="bg-white text-purple-700 hover:bg-purple-50 font-bold h-8 text-xs"
                >
                  <Plus className="w-3.5 h-3.5 mr-1" />
                  Create Procurement Request
                </Button>
              </div>
            </div>
          )}

          <Card className="rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
            <CardHeader className="bg-slate-50/50 border-b border-slate-100 flex flex-row items-center justify-between py-4 px-6">
              <div className="flex items-center gap-2">
                <ClipboardList className="w-5 h-5 text-purple-600" />
                <CardTitle className="text-base font-bold text-slate-900">Material Requirements Queue</CardTitle>
              </div>
              <Badge variant="secondary" className="font-semibold text-xs">
                {requirements.length} requirements
              </Badge>
            </CardHeader>

            <CardContent className="p-0">
              {reqLoading ? (
                <div className="p-16 text-center text-slate-500">
                  <RefreshCw className="w-8 h-8 animate-spin mx-auto text-purple-600 mb-3" />
                  <p className="text-sm">Loading material requirements...</p>
                </div>
              ) : requirements.length === 0 ? (
                <div className="p-16 text-center text-slate-500">
                  <ClipboardList className="w-12 h-12 mx-auto text-slate-300 mb-3" />
                  <h3 className="text-base font-bold text-slate-800">No Requirements Found</h3>
                  <p className="text-xs text-slate-400">All current material requirements are satisfied.</p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-left border-collapse text-sm">
                    <thead>
                      <tr className="bg-slate-50/75 border-b border-slate-200 text-xs font-bold text-slate-500 uppercase tracking-wider">
                        <th className="py-3 px-4 w-10 text-center">
                          <input
                            type="checkbox"
                            checked={selectedReqIds.length === requirements.length && requirements.length > 0}
                            onChange={(e) => {
                              if (e.target.checked) setSelectedReqIds(requirements.map((r) => r.id));
                              else setSelectedReqIds([]);
                            }}
                            className="w-4 h-4 rounded text-purple-600 cursor-pointer"
                          />
                        </th>
                        <th className="py-3 px-4">Req #</th>
                        <th className="py-3 px-4">Company</th>
                        <th className="py-3 px-4">Source</th>
                        <th className="py-3 px-4 text-center">Items</th>
                        <th className="py-3 px-4">Priority</th>
                        <th className="py-3 px-4 text-right">Shortage Value</th>
                        <th className="py-3 px-4">Status</th>
                        <th className="py-3 px-4">Created</th>
                        <th className="py-3 px-4 text-right">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {requirements.map((r) => {
                        const isSelected = selectedReqIds.includes(r.id);
                        const priorityInfo = PRIORITY_BADGES[r.priority] || { bg: "bg-slate-100 text-slate-700" };
                        const statusInfo = STATUS_BADGES[r.status] || { bg: "bg-slate-100", text: "text-slate-700" };

                        return (
                          <tr
                            key={r.id}
                            className={`hover:bg-slate-50/60 transition-colors ${isSelected ? "bg-purple-50/50" : ""}`}
                          >
                            <td className="py-3 px-4 text-center">
                              <input
                                type="checkbox"
                                checked={isSelected}
                                onChange={(e) => {
                                  if (e.target.checked) setSelectedReqIds((prev) => [...prev, r.id]);
                                  else setSelectedReqIds((prev) => prev.filter((id) => id !== r.id));
                                }}
                                className="w-4 h-4 rounded text-purple-600 cursor-pointer"
                              />
                            </td>
                            <td className="py-3 px-4 font-mono font-bold text-xs text-purple-700">{r.requirement_number}</td>
                            <td className="py-3 px-4 font-medium text-slate-800">{r.company_name || "—"}</td>
                            <td className="py-3 px-4">
                              <span className="px-2 py-0.5 rounded-full text-xs font-semibold bg-indigo-50 text-indigo-700 border border-indigo-200">
                                {r.source_type.replace(/_/g, " ")}
                              </span>
                            </td>
                            <td className="py-3 px-4 text-center font-semibold text-slate-700">{r.total_items}</td>
                            <td className="py-3 px-4">
                              <span className={`px-2 py-0.5 rounded-full text-xs font-bold ${priorityInfo.bg}`}>
                                {r.priority}
                              </span>
                            </td>
                            <td className="py-3 px-4 text-right font-mono font-semibold text-slate-900">
                              ₹ {formatNumber(r.total_shortage_value)}
                            </td>
                            <td className="py-3 px-4">
                              <span className={`px-2 py-0.5 rounded-full text-xs font-bold ${statusInfo.bg} ${statusInfo.text}`}>
                                {r.status.replace(/_/g, " ")}
                              </span>
                            </td>
                            <td className="py-3 px-4 text-xs text-slate-500 whitespace-nowrap">{formatDate(r.created_at)}</td>
                            <td className="py-3 px-4 text-right whitespace-nowrap">
                              <div className="flex items-center justify-end gap-1.5">
                                <button
                                  onClick={() => {
                                    setActiveViewReq(r);
                                    setViewReqModalOpen(true);
                                  }}
                                  title="View Details"
                                  className="p-1.5 bg-blue-50 text-blue-600 hover:bg-blue-100 rounded-lg cursor-pointer"
                                >
                                  <Eye className="w-4 h-4" />
                                </button>
                                {r.status === "PENDING" && (
                                  <button
                                    onClick={() => triggerRequirement(r.id)}
                                    title="Trigger Procurement"
                                    className="p-1.5 bg-emerald-50 text-emerald-600 hover:bg-emerald-100 rounded-lg cursor-pointer font-bold"
                                  >
                                    <Check className="w-4 h-4" />
                                  </button>
                                )}
                              </div>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}

      {/* ══════════════════════════════════════════════════════════════════════════
          TAB 4: LOW STOCK ITEMS
          ══════════════════════════════════════════════════════════════════════════ */}
      {activeTab === "lowstock" && (
        <div className="space-y-4">
          {/* Floating Selection Bar */}
          {selectedLowStockIds.length > 0 && (
            <div className="bg-gradient-to-r from-purple-600 to-indigo-600 text-white p-3 px-5 rounded-xl shadow-lg flex justify-between items-center animate-in fade-in duration-200">
              <span className="font-semibold text-sm">
                <span className="font-bold">{selectedLowStockIds.length}</span> low stock items selected
              </span>
              <div className="flex items-center gap-2">
                <Button
                  onClick={() => setSelectedLowStockIds([])}
                  variant="outline"
                  size="sm"
                  className="bg-white/10 text-white hover:bg-white/20 border-white/30 h-8 text-xs"
                >
                  Clear Selection
                </Button>
                <Button
                  onClick={createRequestFromLowStock}
                  size="sm"
                  className="bg-white text-purple-700 hover:bg-purple-50 font-bold h-8 text-xs"
                >
                  <Plus className="w-3.5 h-3.5 mr-1" />
                  Create Procurement Request
                </Button>
              </div>
            </div>
          )}

          <Card className="rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
            <CardHeader className="bg-slate-50/50 border-b border-slate-100 flex flex-row items-center justify-between py-4 px-6">
              <div className="flex items-center gap-2">
                <AlertTriangle className="w-5 h-5 text-amber-600" />
                <CardTitle className="text-base font-bold text-slate-900">Low Stock Reorder Items</CardTitle>
              </div>
              <Badge variant="secondary" className="font-semibold text-xs">
                {lowStockItems.length} items
              </Badge>
            </CardHeader>

            <CardContent className="p-0">
              {lowStockLoading ? (
                <div className="p-16 text-center text-slate-500">
                  <RefreshCw className="w-8 h-8 animate-spin mx-auto text-purple-600 mb-3" />
                  <p className="text-sm">Scanning stock levels...</p>
                </div>
              ) : lowStockItems.length === 0 ? (
                <div className="p-16 text-center text-slate-500">
                  <CheckCircle2 className="w-12 h-12 mx-auto text-emerald-500 mb-3" />
                  <h3 className="text-base font-bold text-slate-800">Stock Levels OK</h3>
                  <p className="text-xs text-slate-400">All inventory items are currently above their reorder thresholds.</p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-left border-collapse text-sm">
                    <thead>
                      <tr className="bg-slate-50/75 border-b border-slate-200 text-xs font-bold text-slate-500 uppercase tracking-wider">
                        <th className="py-3 px-4 w-10 text-center">
                          <input
                            type="checkbox"
                            checked={selectedLowStockIds.length === lowStockItems.length && lowStockItems.length > 0}
                            onChange={(e) => {
                              if (e.target.checked) setSelectedLowStockIds(lowStockItems.map((i) => i.item_id));
                              else setSelectedLowStockIds([]);
                            }}
                            className="w-4 h-4 rounded text-purple-600 cursor-pointer"
                          />
                        </th>
                        <th className="py-3 px-4">Item Code</th>
                        <th className="py-3 px-4">Item Name</th>
                        <th className="py-3 px-4">Category</th>
                        <th className="py-3 px-4">Company</th>
                        <th className="py-3 px-4 text-right">Available</th>
                        <th className="py-3 px-4 text-right">Reorder Level</th>
                        <th className="py-3 px-4 text-right">Shortage</th>
                        <th className="py-3 px-4 text-center">Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {lowStockItems.map((i) => {
                        const isSelected = selectedLowStockIds.includes(i.item_id);
                        return (
                          <tr
                            key={i.item_id}
                            className={`hover:bg-slate-50/60 transition-colors ${isSelected ? "bg-purple-50/50" : ""}`}
                          >
                            <td className="py-3 px-4 text-center">
                              <input
                                type="checkbox"
                                checked={isSelected}
                                onChange={(e) => {
                                  if (e.target.checked) setSelectedLowStockIds((prev) => [...prev, i.item_id]);
                                  else setSelectedLowStockIds((prev) => prev.filter((id) => id !== i.item_id));
                                }}
                                className="w-4 h-4 rounded text-purple-600 cursor-pointer"
                              />
                            </td>
                            <td className="py-3 px-4 font-mono font-bold text-xs text-purple-700">{i.item_code}</td>
                            <td className="py-3 px-4 font-semibold text-slate-900">{i.item_name}</td>
                            <td className="py-3 px-4 text-xs text-slate-500">{i.category || "—"}</td>
                            <td className="py-3 px-4 text-xs text-slate-700">{i.company_name || "—"}</td>
                            <td className="py-3 px-4 text-right text-xs font-semibold">
                              {formatNumber(i.available_qty)} {i.unit_of_measure || ""}
                            </td>
                            <td className="py-3 px-4 text-right text-xs text-slate-500">{formatNumber(i.reorder_level)}</td>
                            <td className="py-3 px-4 text-right font-bold text-rose-600 font-mono">
                              {formatNumber(i.shortage_qty)}
                            </td>
                            <td className="py-3 px-4 text-center">
                              <span className="px-2 py-0.5 rounded-full text-xs font-bold bg-amber-100 text-amber-800">
                                {i.status}
                              </span>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}

      {/* ══════════════════════════════════════════════════════════════════════════
          TAB 5: AGGREGATED SHORTAGES
          ══════════════════════════════════════════════════════════════════════════ */}
      {activeTab === "aggregated" && (
        <div className="space-y-4">
          {/* Floating Selection Bar */}
          {selectedAggIndices.length > 0 && (
            <div className="bg-gradient-to-r from-purple-600 to-indigo-600 text-white p-3 px-5 rounded-xl shadow-lg flex justify-between items-center animate-in fade-in duration-200">
              <span className="font-semibold text-sm">
                <span className="font-bold">{selectedAggIndices.length}</span> components selected
              </span>
              <div className="flex items-center gap-2">
                <Button
                  onClick={() => setSelectedAggIndices([])}
                  variant="outline"
                  size="sm"
                  className="bg-white/10 text-white hover:bg-white/20 border-white/30 h-8 text-xs"
                >
                  Clear Selection
                </Button>
                <Button
                  onClick={createRequestFromAggregated}
                  size="sm"
                  className="bg-white text-purple-700 hover:bg-purple-50 font-bold h-8 text-xs"
                >
                  <Plus className="w-3.5 h-3.5 mr-1" />
                  Create Procurement Request
                </Button>
              </div>
            </div>
          )}

          <Card className="rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
            <CardHeader className="bg-slate-50/50 border-b border-slate-100 flex flex-row items-center justify-between py-4 px-6">
              <div className="flex items-center gap-2">
                <Boxes className="w-5 h-5 text-purple-600" />
                <CardTitle className="text-base font-bold text-slate-900">Aggregated Order Material Shortages</CardTitle>
              </div>
              <Badge variant="secondary" className="font-semibold text-xs">
                {aggregatedShortages.length} components
              </Badge>
            </CardHeader>

            <CardContent className="p-0">
              {aggLoading ? (
                <div className="p-16 text-center text-slate-500">
                  <RefreshCw className="w-8 h-8 animate-spin mx-auto text-purple-600 mb-3" />
                  <p className="text-sm">Calculating shortages from active production and sales orders...</p>
                </div>
              ) : aggregatedShortages.length === 0 ? (
                <div className="p-16 text-center text-slate-500">
                  <CheckCircle2 className="w-12 h-12 mx-auto text-emerald-500 mb-3" />
                  <h3 className="text-base font-bold text-slate-800">No Shortages Detected</h3>
                  <p className="text-xs text-slate-400">All active orders have sufficient material coverage.</p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-left border-collapse text-sm">
                    <thead>
                      <tr className="bg-slate-50/75 border-b border-slate-200 text-xs font-bold text-slate-500 uppercase tracking-wider">
                        <th className="py-3 px-4 w-10 text-center">
                          <input
                            type="checkbox"
                            checked={selectedAggIndices.length === aggregatedShortages.length && aggregatedShortages.length > 0}
                            onChange={(e) => {
                              if (e.target.checked) setSelectedAggIndices(aggregatedShortages.map((_, idx) => idx));
                              else setSelectedAggIndices([]);
                            }}
                            className="w-4 h-4 rounded text-purple-600 cursor-pointer"
                          />
                        </th>
                        <th className="py-3 px-4">Component Code</th>
                        <th className="py-3 px-4">Component Name</th>
                        <th className="py-3 px-4 text-right">Total Required</th>
                        <th className="py-3 px-4 text-right">Available</th>
                        <th className="py-3 px-4 text-right">Shortage</th>
                        <th className="py-3 px-4">Source Orders</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {aggregatedShortages.map((s, idx) => {
                        const isSelected = selectedAggIndices.includes(idx);
                        return (
                          <tr
                            key={idx}
                            className={`hover:bg-slate-50/60 transition-colors ${isSelected ? "bg-purple-50/50" : ""}`}
                          >
                            <td className="py-3 px-4 text-center">
                              <input
                                type="checkbox"
                                checked={isSelected}
                                onChange={(e) => {
                                  if (e.target.checked) setSelectedAggIndices((prev) => [...prev, idx]);
                                  else setSelectedAggIndices((prev) => prev.filter((i) => i !== idx));
                                }}
                                className="w-4 h-4 rounded text-purple-600 cursor-pointer"
                              />
                            </td>
                            <td className="py-3 px-4 font-mono font-bold text-xs text-purple-700">{s.component_code}</td>
                            <td className="py-3 px-4 font-semibold text-slate-900">{s.component_name}</td>
                            <td className="py-3 px-4 text-right text-xs font-medium">{formatNumber(s.total_required)}</td>
                            <td className="py-3 px-4 text-right text-xs text-slate-500">{formatNumber(s.available_qty)}</td>
                            <td className="py-3 px-4 text-right font-bold text-rose-600 font-mono">
                              {formatNumber(s.total_shortage)}
                            </td>
                            <td className="py-3 px-4">
                              <div className="flex flex-wrap gap-1 max-w-[280px]">
                                {(s.source_orders || []).slice(0, 3).map((o, oIdx) => (
                                  <span
                                    key={oIdx}
                                    className="px-2 py-0.5 bg-slate-100 text-slate-700 border border-slate-200 rounded text-[11px] font-mono"
                                  >
                                    {o.order_number}
                                  </span>
                                ))}
                                {(s.source_orders || []).length > 3 && (
                                  <span className="text-[11px] text-slate-400">
                                    +{(s.source_orders || []).length - 3} more
                                  </span>
                                )}
                              </div>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}

      {/* ══════════════════════════════════════════════════════════════════════════
          TAB 6: MARKET PLACE (PENDING PROCUREMENT)
          ══════════════════════════════════════════════════════════════════════════ */}
      {activeTab === "vgkproc" && (
        <Card className="rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
          <CardHeader className="bg-slate-50/50 border-b border-slate-100 flex flex-row items-center justify-between py-4 px-6">
            <div>
              <div className="flex items-center gap-2">
                <Store className="w-5 h-5 text-purple-600" />
                <CardTitle className="text-base font-bold text-slate-900">
                  Market Place — Pending Procurement
                </CardTitle>
              </div>
              <p className="text-xs text-slate-500 mt-1">
                Items from Partner Orders and Service Tickets where stock &lt; required quantity. Add to cart to fulfill.
              </p>
            </div>

            <div className="flex items-center gap-3">
              <Link
                href="/staff/vgk4u/purchase-orders"
                className="text-xs font-semibold text-purple-600 hover:text-purple-700 flex items-center gap-1"
              >
                VGK PO Page <ExternalLink className="w-3 h-3" />
              </Link>
              <Button onClick={loadMarketplaceItems} size="sm" variant="outline" className="h-8 text-xs">
                <RefreshCw className="w-3.5 h-3.5 mr-1" />
                Refresh
              </Button>
            </div>
          </CardHeader>

          <CardContent className="p-4 space-y-4">
            {/* Filter Toolbar */}
            <div className="flex flex-wrap gap-3 items-center">
              <div className="relative flex-1 min-w-[220px]">
                <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
                <Input
                  type="text"
                  placeholder="Search item code or name..."
                  value={mktSearch}
                  onChange={(e) => setMktSearch(e.target.value)}
                  className="pl-9 h-9 text-xs rounded-xl"
                />
              </div>

              <select
                value={mktSourceFilter}
                onChange={(e) => setMktSourceFilter(e.target.value)}
                className="h-9 px-3 border border-slate-300 rounded-xl text-xs bg-white text-slate-700 outline-none"
              >
                <option value="">All Sources</option>
                <option value="Partner Order">Partner Orders</option>
                <option value="Service Ticket">Service Tickets</option>
              </select>
            </div>

            {mktLoading ? (
              <div className="p-12 text-center text-slate-500">
                <RefreshCw className="w-6 h-6 animate-spin mx-auto text-purple-600 mb-2" />
                <p className="text-xs">Loading marketplace items...</p>
              </div>
            ) : filteredMarketplaceItems.length === 0 ? (
              <div className="p-12 text-center text-slate-500">
                <CheckCircle2 className="w-10 h-10 mx-auto text-emerald-500 mb-2" />
                <h4 className="text-sm font-bold text-slate-800">No Pending Marketplace Items</h4>
                <p className="text-xs text-slate-400">All partner orders and service tickets have sufficient stock.</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse text-xs">
                  <thead>
                    <tr className="bg-slate-50/75 border-b border-slate-200 font-bold text-slate-500 uppercase tracking-wider">
                      <th className="py-3 px-3">Item Code</th>
                      <th className="py-3 px-3">Item Name</th>
                      <th className="py-3 px-3 text-center">UoM</th>
                      <th className="py-3 px-3">Source</th>
                      <th className="py-3 px-3">Reference</th>
                      <th className="py-3 px-3 text-center">Qty Needed</th>
                      <th className="py-3 px-3 text-center">Stock</th>
                      <th className="py-3 px-3 text-center">Shortage</th>
                      <th className="py-3 px-3 text-center">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {filteredMarketplaceItems.map((it) => {
                      const shortageCls = it.shortage > 0 ? "text-rose-600 font-bold" : "text-slate-500";
                      return (
                        <tr key={it.item_id + it.source_type} className="hover:bg-slate-50/60 transition-colors">
                          <td className="py-2.5 px-3 font-mono font-bold text-indigo-600">{it.item_code}</td>
                          <td className="py-2.5 px-3">
                            <div className="font-semibold text-slate-900">{it.item_name}</div>
                            {it.model_compat && (
                              <div className="text-[10px] text-indigo-600">Compat: {it.model_compat}</div>
                            )}
                          </td>
                          <td className="py-2.5 px-3 text-center text-slate-500">{it.uom || "—"}</td>
                          <td className="py-2.5 px-3">
                            <span
                              className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                                it.source_type === "Partner Order"
                                  ? "bg-blue-50 text-blue-700 border border-blue-200"
                                  : "bg-emerald-50 text-emerald-700 border border-emerald-200"
                              }`}
                            >
                              {it.source_type}
                            </span>
                          </td>
                          <td className="py-2.5 px-3 font-mono text-slate-600">{it.source_ref || "—"}</td>
                          <td className="py-2.5 px-3 text-center font-semibold text-slate-800">{it.qty_needed || 0}</td>
                          <td className="py-2.5 px-3 text-center text-slate-500">{it.stock_qty || 0}</td>
                          <td className={`py-2.5 px-3 text-center ${shortageCls}`}>
                            {it.shortage > 0 ? `⚠ ${it.shortage}` : "—"}
                          </td>
                          <td className="py-2.5 px-3 text-center">
                            <button
                              onClick={() => {
                                pushToSpareCart(
                                  null,
                                  "Vendor TBD",
                                  "",
                                  "",
                                  it.item_id,
                                  it.item_code,
                                  it.item_name,
                                  it.shortage || 1,
                                  it.uom || "PCS",
                                  0,
                                  it.source_type,
                                  it.shortage || 1
                                );
                              }}
                              className="px-2.5 py-1 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg font-semibold text-[11px] cursor-pointer flex items-center gap-1 mx-auto"
                            >
                              <ShoppingCart className="w-3 h-3" /> Add to Cart
                            </button>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* ══════════════════════════════════════════════════════════════════════════
          MODAL: CREATE PROCUREMENT REQUEST
          ══════════════════════════════════════════════════════════════════════════ */}
      {createModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4 overflow-y-auto animate-in fade-in duration-200">
          <div className="bg-white rounded-2xl max-w-2xl w-full shadow-2xl overflow-hidden my-8 max-h-[90vh] flex flex-col">
            <div className="bg-gradient-to-r from-purple-600 to-indigo-600 text-white p-5 px-6 flex justify-between items-center shrink-0">
              <div className="flex items-center gap-2.5">
                <Plus className="w-5 h-5" />
                <h3 className="font-bold text-lg">Create Procurement Request</h3>
              </div>
              <button
                onClick={() => setCreateModalOpen(false)}
                className="text-white/80 hover:text-white p-1 rounded-lg hover:bg-white/10"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6 overflow-y-auto space-y-5">
              <div className="bg-indigo-50/60 border border-indigo-100 p-3 rounded-xl text-xs text-indigo-900 flex items-start gap-2">
                <Info className="w-4 h-4 text-indigo-600 shrink-0 mt-0.5" />
                <span>
                  Multi-quote workflow requires minimum 2 vendor quotes before approval. Vendor quotation requests will use blind bidding (prices are not disclosed to vendors).
                </span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <Label className="text-xs font-bold text-slate-700">Company *</Label>
                  <select
                    value={createCompanyId}
                    onChange={(e) => setCreateCompanyId(e.target.value)}
                    className="w-full h-10 px-3 border border-slate-300 rounded-xl text-sm bg-white text-slate-700 outline-none"
                    required
                  >
                    <option value="">Select Company</option>
                    {companies.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.company_name}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="space-y-1.5">
                  <Label className="text-xs font-bold text-slate-700">Minimum Quotes Required</Label>
                  <select
                    value={createMinQuotes}
                    onChange={(e) => setCreateMinQuotes(parseInt(e.target.value) || 2)}
                    className="w-full h-10 px-3 border border-slate-300 rounded-xl text-sm bg-white text-slate-700 outline-none"
                  >
                    <option value={2}>2 Quotes</option>
                    <option value={3}>3 Quotes</option>
                    <option value={4}>4 Quotes</option>
                  </select>
                </div>
              </div>

              <div className="space-y-1.5">
                <Label className="text-xs font-bold text-slate-700">Procurement Notes</Label>
                <Textarea
                  placeholder="Optional notes for this procurement request..."
                  value={createNotes}
                  onChange={(e) => setCreateNotes(e.target.value)}
                  rows={2}
                  className="rounded-xl text-sm"
                />
              </div>

              {/* Items to Procure Table */}
              <div className="space-y-2">
                <div className="flex justify-between items-center">
                  <Label className="text-xs font-bold text-slate-700 uppercase tracking-wider">
                    Items to Procure ({createItems.length})
                  </Label>
                </div>

                {createItems.length === 0 ? (
                  <div className="p-6 bg-slate-50 rounded-xl text-center text-slate-400 text-xs border border-dashed border-slate-200">
                    No items added yet. Search and add stock items below.
                  </div>
                ) : (
                  <div className="border border-slate-200 rounded-xl overflow-hidden max-h-[260px] overflow-y-auto">
                    <table className="w-full text-left text-xs border-collapse">
                      <thead className="bg-slate-50 sticky top-0 border-b border-slate-200">
                        <tr>
                          <th className="p-2.5 font-bold text-slate-600">Item</th>
                          <th className="p-2.5 font-bold text-slate-600 text-right w-20">Qty</th>
                          <th className="p-2.5 font-bold text-slate-600 w-16">UOM</th>
                          <th className="p-2.5 font-bold text-slate-600">Specifications</th>
                          <th className="p-2.5 w-10"></th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100">
                        {createItems.map((item, idx) => (
                          <tr key={idx}>
                            <td className="p-2.5">
                              <div className="font-bold text-slate-800">{item.item_name}</div>
                              <code className="text-[10px] text-slate-400">{item.item_code}</code>
                            </td>
                            <td className="p-2.5 text-right">
                              <Input
                                type="number"
                                min="1"
                                value={item.required_qty}
                                onChange={(e) => {
                                  const val = parseFloat(e.target.value) || 1;
                                  setCreateItems((prev) =>
                                    prev.map((it, i) => (i === idx ? { ...it, required_qty: val } : it))
                                  );
                                }}
                                className="w-16 h-7 text-xs text-right font-semibold"
                              />
                            </td>
                            <td className="p-2.5 text-slate-500">{item.unit_of_measure || "PCS"}</td>
                            <td className="p-2.5">
                              <Input
                                type="text"
                                placeholder="e.g. 60V 45Ah, Red, Grade A..."
                                value={item.specifications || ""}
                                onChange={(e) => {
                                  const val = e.target.value;
                                  setCreateItems((prev) =>
                                    prev.map((it, i) => (i === idx ? { ...it, specifications: val } : it))
                                  );
                                }}
                                className="h-7 text-xs"
                              />
                            </td>
                            <td className="p-2.5 text-center">
                              <button
                                onClick={() => setCreateItems((prev) => prev.filter((_, i) => i !== idx))}
                                className="p-1 text-rose-500 hover:text-rose-700 hover:bg-rose-50 rounded"
                              >
                                <X className="w-4 h-4" />
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>

              {/* Add Item Row */}
              <div className="p-3 bg-slate-50 rounded-xl border border-slate-200 space-y-3">
                <Label className="text-xs font-bold text-slate-700">Add Item From Stock Directory</Label>
                <div className="flex gap-2 items-start relative">
                  <div className="flex-1 relative">
                    <Input
                      type="text"
                      placeholder="Type item code or name..."
                      value={itemSearchTerm}
                      onChange={(e) => handleSearchStockItems(e.target.value)}
                      className="h-9 text-xs rounded-xl bg-white"
                    />
                    {/* Autocomplete Dropdown */}
                    {itemSearchResults.length > 0 && (
                      <div className="absolute top-10 left-0 right-0 z-50 bg-white border border-slate-200 rounded-xl shadow-xl max-h-48 overflow-y-auto divide-y divide-slate-100">
                        {itemSearchResults.map((it) => (
                          <div
                            key={it.id}
                            onClick={() => addItemToCreateList(it)}
                            className="p-2.5 px-3 hover:bg-purple-50 cursor-pointer transition-colors"
                          >
                            <div className="font-bold text-xs text-slate-800">{it.item_name}</div>
                            <div className="text-[10px] text-slate-400">
                              <code>{it.item_code}</code> • {it.item_category || it.category || "General"}
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>

                  <div className="w-24">
                    <Input
                      type="number"
                      min="1"
                      placeholder="Qty"
                      value={itemQtyToAdd}
                      onChange={(e) => setItemQtyToAdd(parseFloat(e.target.value) || 1)}
                      className="h-9 text-xs text-center rounded-xl bg-white"
                    />
                  </div>
                </div>
              </div>
            </div>

            <div className="p-4 px-6 bg-slate-50 border-t border-slate-200 flex justify-end gap-2 shrink-0">
              <Button onClick={() => setCreateModalOpen(false)} variant="outline" className="rounded-xl text-xs h-9">
                Cancel
              </Button>
              <Button
                onClick={submitCreateRequest}
                disabled={createSubmitting}
                className="bg-purple-600 hover:bg-purple-700 text-white rounded-xl text-xs h-9 font-semibold"
              >
                {createSubmitting ? "Creating..." : "Create Request"}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* ══════════════════════════════════════════════════════════════════════════
          MODAL: VIEW PROCUREMENT REQUEST DETAILS & QUOTES
          ══════════════════════════════════════════════════════════════════════════ */}
      {viewRequestModalOpen && viewRequestData && (
        <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4 overflow-y-auto animate-in fade-in duration-200">
          <div className="bg-white rounded-2xl max-w-4xl w-full shadow-2xl overflow-hidden my-8 max-h-[90vh] flex flex-col">
            <div className="bg-gradient-to-r from-blue-700 to-indigo-700 text-white p-5 px-6 flex justify-between items-center shrink-0">
              <div className="flex items-center gap-2.5">
                <FileText className="w-5 h-5" />
                <div>
                  <h3 className="font-bold text-lg">Procurement Request - {viewRequestData.request_number}</h3>
                  <p className="text-xs text-white/80">{viewRequestData.company_name || "Company"}</p>
                </div>
              </div>
              <button
                onClick={() => setViewRequestModalOpen(false)}
                className="text-white/80 hover:text-white p-1 rounded-lg hover:bg-white/10"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6 overflow-y-auto space-y-6">
              {/* Request Metadata Grid */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 p-4 bg-slate-50 rounded-xl border border-slate-200 text-xs">
                <div>
                  <span className="text-slate-400 block font-semibold">Company</span>
                  <span className="font-bold text-slate-800">{viewRequestData.company_name || "—"}</span>
                </div>
                <div>
                  <span className="text-slate-400 block font-semibold">Status</span>
                  <span
                    className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold border mt-0.5 ${
                      STATUS_BADGES[viewRequestData.status]?.bg || "bg-slate-100"
                    } ${STATUS_BADGES[viewRequestData.status]?.text || "text-slate-700"}`}
                  >
                    {viewRequestData.status.replace(/_/g, " ")}
                  </span>
                </div>
                <div>
                  <span className="text-slate-400 block font-semibold">Quotes Status</span>
                  <span className="font-bold text-slate-800">
                    {viewRequestData.quotes_received_count || 0} / {viewRequestData.min_quotes_required || 2} required
                  </span>
                </div>
                <div>
                  <span className="text-slate-400 block font-semibold">Created Date</span>
                  <span className="font-medium text-slate-700">{formatDate(viewRequestData.created_at)}</span>
                </div>
              </div>

              {viewRequestData.notes && (
                <div className="p-3 bg-purple-50/50 border border-purple-100 rounded-xl text-xs text-purple-900">
                  <span className="font-bold mr-1">Notes:</span> {viewRequestData.notes}
                </div>
              )}

              {/* Requested Items Table */}
              <div>
                <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                  <Boxes className="w-4 h-4 text-indigo-600" />
                  Requested Items ({viewRequestData.items?.length || 0})
                </h4>

                <div className="border border-slate-200 rounded-xl overflow-hidden overflow-x-auto">
                  <table className="w-full text-left text-xs border-collapse">
                    <thead className="bg-slate-50 border-b border-slate-200">
                      <tr>
                        <th className="p-2.5 font-bold text-slate-600">Item</th>
                        <th className="p-2.5 font-bold text-slate-600 text-center">Qty</th>
                        <th className="p-2.5 font-bold text-slate-600">UOM</th>
                        <th className="p-2.5 font-bold text-slate-600">Category</th>
                        <th className="p-2.5 font-bold text-slate-600">HSN</th>
                        <th className="p-2.5 font-bold text-slate-600">Brand</th>
                        <th className="p-2.5 font-bold text-slate-600">Model / Compat</th>
                        <th className="p-2.5 font-bold text-slate-600">Colour</th>
                        <th className="p-2.5 font-bold text-slate-600">Specification</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {(viewRequestData.items || []).map((it, idx) => (
                        <tr key={idx} className="hover:bg-slate-50/50">
                          <td className="p-2.5">
                            <div className="font-bold text-slate-900">{it.item_name || "—"}</div>
                            <code className="text-[10px] text-purple-600">{it.item_code}</code>
                          </td>
                          <td className="p-2.5 text-center font-bold text-slate-800">{it.required_qty}</td>
                          <td className="p-2.5 text-slate-500">{it.unit_of_measure || "PCS"}</td>
                          <td className="p-2.5 text-slate-500">{it.item_category || it.category || "—"}</td>
                          <td className="p-2.5 text-slate-500">{it.hsn_code || "—"}</td>
                          <td className="p-2.5 text-slate-700">{it.brand || "—"}</td>
                          <td className="p-2.5 text-slate-700">{it.model_compat || "—"}</td>
                          <td className="p-2.5 text-slate-700">
                            {Array.isArray(it.colors) ? it.colors.join(", ") : it.colors || "—"}
                          </td>
                          <td className="p-2.5 text-slate-700">{it.specification || it.specifications || "—"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Vendor Quotes Comparison */}
              <div>
                <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wider mb-3 flex items-center gap-1.5">
                  <Store className="w-4 h-4 text-purple-600" />
                  Vendor Quotes ({viewRequestData.quotes?.length || 0})
                </h4>

                {viewRequestData.quotes && viewRequestData.quotes.length > 0 ? (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {viewRequestData.quotes.map((q) => (
                      <div
                        key={q.id}
                        onClick={() => {
                          if (viewRequestData.status === "QUOTES_RECEIVED") {
                            approveQuote(q.id);
                          }
                        }}
                        className={`p-4 rounded-xl border-2 transition-all duration-200 relative ${
                          q.is_selected
                            ? "border-purple-600 bg-purple-50/40 shadow-sm"
                            : q.is_lowest
                            ? "border-emerald-500 bg-emerald-50/20"
                            : "border-slate-200 hover:border-purple-400 bg-white"
                        } ${viewRequestData.status === "QUOTES_RECEIVED" ? "cursor-pointer hover:shadow-md" : ""}`}
                      >
                        {q.is_lowest && (
                          <span className="absolute -top-2.5 right-4 bg-emerald-600 text-white text-[10px] font-bold px-2.5 py-0.5 rounded-full shadow-xs">
                            Lowest Price
                          </span>
                        )}

                        <div className="flex justify-between items-start mb-2">
                          <h5 className="font-bold text-sm text-slate-900">{q.vendor_name || `Vendor #${q.vendor_id}`}</h5>
                          <span
                            className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                              STATUS_BADGES[q.status]?.bg || "bg-slate-100"
                            } ${STATUS_BADGES[q.status]?.text || "text-slate-700"}`}
                          >
                            {q.status}
                          </span>
                        </div>

                        <div className="text-2xl font-bold text-purple-700 mb-3">₹ {formatNumber(q.grand_total)}</div>

                        <div className="grid grid-cols-2 gap-2 text-xs text-slate-500">
                          <div>Quote #: {q.quote_number || "—"}</div>
                          <div>Date: {formatDate(q.quote_date)}</div>
                          <div>Validity: {q.validity_days || 30} days</div>
                          <div>Delivery: {q.delivery_days ? `${q.delivery_days} days` : "—"}</div>
                        </div>

                        {viewRequestData.status === "QUOTES_RECEIVED" && (
                          <div className="mt-3 pt-2 border-t border-slate-100 flex justify-end">
                            <span className="text-xs font-bold text-purple-600 flex items-center gap-1">
                              Click to Approve <Check className="w-3.5 h-3.5" />
                            </span>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="p-6 bg-slate-50 rounded-xl text-center text-slate-400 text-xs border border-slate-200">
                    No vendor quotes submitted yet. Click "Add Quote" below to enter proforma invoices.
                  </div>
                )}
              </div>
            </div>

            <div className="p-4 px-6 bg-slate-50 border-t border-slate-200 flex justify-between items-center shrink-0">
              <Button onClick={() => setViewRequestModalOpen(false)} variant="outline" className="rounded-xl text-xs h-9">
                Close
              </Button>

              <div className="flex items-center gap-2">
                {(viewRequestData.status === "DRAFT" || viewRequestData.status === "SENT_TO_VENDORS") && (
                  <Button
                    onClick={() => {
                      setViewRequestModalOpen(false);
                      openAddQuoteModal(viewRequestData.id);
                    }}
                    className="bg-purple-600 hover:bg-purple-700 text-white rounded-xl text-xs h-9 font-semibold"
                  >
                    <Plus className="w-3.5 h-3.5 mr-1" />
                    Add Quote
                  </Button>
                )}

                {viewRequestData.status === "QUOTE_APPROVED" && (
                  <Button
                    onClick={() => generatePO(viewRequestData.id)}
                    className="bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs h-9 font-bold"
                  >
                    <FileCheck className="w-3.5 h-3.5 mr-1" />
                    Generate Purchase Order
                  </Button>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ══════════════════════════════════════════════════════════════════════════
          MODAL: ADD VENDOR QUOTE (PROFORMA INVOICE)
          ══════════════════════════════════════════════════════════════════════════ */}
      {addQuoteModalOpen && quoteReqData && (
        <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4 overflow-y-auto animate-in fade-in duration-200">
          <div className="bg-white rounded-2xl max-w-3xl w-full shadow-2xl overflow-hidden my-8 max-h-[90vh] flex flex-col">
            <div className="bg-gradient-to-r from-purple-700 to-indigo-700 text-white p-5 px-6 flex justify-between items-center shrink-0">
              <div className="flex items-center gap-2.5">
                <FileSpreadsheet className="w-5 h-5" />
                <h3 className="font-bold text-lg">Add Vendor Quote (Proforma Invoice)</h3>
              </div>
              <button
                onClick={() => setAddQuoteModalOpen(false)}
                className="text-white/80 hover:text-white p-1 rounded-lg hover:bg-white/10"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6 overflow-y-auto space-y-5">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <Label className="text-xs font-bold text-slate-700">Vendor *</Label>
                  <select
                    value={quoteVendorId}
                    onChange={(e) => setQuoteVendorId(e.target.value)}
                    className="w-full h-10 px-3 border border-slate-300 rounded-xl text-sm bg-white text-slate-700 outline-none"
                    required
                  >
                    <option value="">Select Vendor</option>
                    {availableVendors.map((v) => (
                      <option key={v.id} value={v.id}>
                        {v.vendor_name} ({v.vendor_code || "V" + v.id})
                      </option>
                    ))}
                  </select>
                </div>

                <div className="space-y-1.5">
                  <Label className="text-xs font-bold text-slate-700">Quote / PI Number</Label>
                  <Input
                    type="text"
                    placeholder="Vendor's quote or PI number"
                    value={quoteNumber}
                    onChange={(e) => setQuoteNumber(e.target.value)}
                    className="rounded-xl text-sm h-10"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="space-y-1.5">
                  <Label className="text-xs font-bold text-slate-700">Quote Date</Label>
                  <Input
                    type="date"
                    value={quoteDate}
                    onChange={(e) => setQuoteDate(e.target.value)}
                    className="rounded-xl text-sm h-10"
                  />
                </div>

                <div className="space-y-1.5">
                  <Label className="text-xs font-bold text-slate-700">Validity (Days)</Label>
                  <Input
                    type="number"
                    min="1"
                    value={quoteValidity}
                    onChange={(e) => setQuoteValidity(parseInt(e.target.value) || 30)}
                    className="rounded-xl text-sm h-10"
                  />
                </div>

                <div className="space-y-1.5">
                  <Label className="text-xs font-bold text-slate-700">Delivery (Days)</Label>
                  <Input
                    type="number"
                    placeholder="Est. delivery days"
                    value={quoteDeliveryDays}
                    onChange={(e) => setQuoteDeliveryDays(e.target.value)}
                    className="rounded-xl text-sm h-10"
                  />
                </div>
              </div>

              <div className="space-y-1.5">
                <Label className="text-xs font-bold text-slate-700">Payment Terms</Label>
                <Input
                  type="text"
                  placeholder="e.g. 30% advance, 70% on dispatch"
                  value={quotePaymentTerms}
                  onChange={(e) => setQuotePaymentTerms(e.target.value)}
                  className="rounded-xl text-sm h-10"
                />
              </div>

              {/* Item Pricing Matrix */}
              <div className="space-y-2">
                <Label className="text-xs font-bold text-slate-700 uppercase tracking-wider">Item Rates & Taxes</Label>
                <div className="border border-slate-200 rounded-xl overflow-hidden overflow-x-auto">
                  <table className="w-full text-left text-xs border-collapse">
                    <thead className="bg-slate-50 border-b border-slate-200">
                      <tr>
                        <th className="p-2.5 font-bold text-slate-600">Item</th>
                        <th className="p-2.5 font-bold text-slate-600 text-center w-16">Qty</th>
                        <th className="p-2.5 font-bold text-slate-600 text-right w-28">Unit Rate (₹) *</th>
                        <th className="p-2.5 font-bold text-slate-600 text-center w-20">GST %</th>
                        <th className="p-2.5 font-bold text-slate-600 text-right w-28">Amount</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {(quoteReqData.items || []).map((it) => {
                        const rateData = (it.id && quoteItemRates[it.id]) || { rate: 0, gst: 18 };
                        const amount = (rateData.rate || 0) * (it.required_qty || 0);

                        return (
                          <tr key={it.id}>
                            <td className="p-2.5">
                              <div className="font-bold text-slate-800">{it.item_name}</div>
                              <code className="text-[10px] text-purple-600">{it.item_code}</code>
                            </td>
                            <td className="p-2.5 text-center font-semibold text-slate-700">{it.required_qty}</td>
                            <td className="p-2.5 text-right">
                              <Input
                                type="number"
                                min="0"
                                step="0.01"
                                placeholder="0.00"
                                value={rateData.rate || ""}
                                onChange={(e) => {
                                  const val = parseFloat(e.target.value) || 0;
                                  if (it.id) {
                                    setQuoteItemRates((prev) => ({
                                      ...prev,
                                      [it.id!]: { ...rateData, rate: val },
                                    }));
                                  }
                                }}
                                className="h-7 text-xs text-right font-semibold"
                              />
                            </td>
                            <td className="p-2.5 text-center">
                              <Input
                                type="number"
                                min="0"
                                max="28"
                                value={rateData.gst}
                                onChange={(e) => {
                                  const val = parseFloat(e.target.value) || 0;
                                  if (it.id) {
                                    setQuoteItemRates((prev) => ({
                                      ...prev,
                                      [it.id!]: { ...rateData, gst: val },
                                    }));
                                  }
                                }}
                                className="h-7 text-xs text-center"
                              />
                            </td>
                            <td className="p-2.5 text-right font-mono font-bold text-slate-900">
                              ₹ {formatNumber(amount)}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                    <tfoot className="bg-slate-50/80 border-t border-slate-200">
                      <tr>
                        <td colSpan={3}></td>
                        <td className="p-2 text-right font-semibold text-slate-600">Subtotal:</td>
                        <td className="p-2 text-right font-mono font-semibold text-slate-800">
                          ₹ {formatNumber(calculateQuoteTotals().subtotal)}
                        </td>
                      </tr>
                      <tr>
                        <td colSpan={3}></td>
                        <td className="p-2 text-right font-semibold text-slate-600">Total GST:</td>
                        <td className="p-2 text-right font-mono font-semibold text-slate-800">
                          ₹ {formatNumber(calculateQuoteTotals().totalGst)}
                        </td>
                      </tr>
                      <tr className="bg-purple-50/40">
                        <td colSpan={3}></td>
                        <td className="p-2.5 text-right font-bold text-slate-900">Grand Total:</td>
                        <td className="p-2.5 text-right font-mono font-bold text-purple-700 text-sm">
                          ₹ {formatNumber(calculateQuoteTotals().grandTotal)}
                        </td>
                      </tr>
                    </tfoot>
                  </table>
                </div>
              </div>

              <div className="space-y-1.5 max-w-xs ml-auto">
                <Label className="text-xs font-bold text-slate-700">Other Charges (Freight / Handling)</Label>
                <Input
                  type="number"
                  min="0"
                  step="0.01"
                  value={quoteOtherCharges || ""}
                  onChange={(e) => setQuoteOtherCharges(parseFloat(e.target.value) || 0)}
                  className="rounded-xl text-sm h-9 text-right"
                  placeholder="0.00"
                />
              </div>
            </div>

            <div className="p-4 px-6 bg-slate-50 border-t border-slate-200 flex justify-end gap-2 shrink-0">
              <Button onClick={() => setAddQuoteModalOpen(false)} variant="outline" className="rounded-xl text-xs h-9">
                Cancel
              </Button>
              <Button
                onClick={submitQuote}
                disabled={quoteSubmitting}
                className="bg-purple-600 hover:bg-purple-700 text-white rounded-xl text-xs h-9 font-semibold"
              >
                {quoteSubmitting ? "Saving..." : "Save Quote"}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* ══════════════════════════════════════════════════════════════════════════
          MODAL: SPO REVIEW & APPROVE (FOR CONSOLIDATED SPARE ORDERS)
          ══════════════════════════════════════════════════════════════════════════ */}
      {spoApproveModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4 overflow-y-auto animate-in fade-in duration-200">
          <div className="bg-white rounded-2xl max-w-4xl w-full shadow-2xl overflow-hidden my-8 max-h-[90vh] flex flex-col">
            <div className="bg-gradient-to-r from-blue-700 to-indigo-700 text-white p-5 px-6 flex justify-between items-center shrink-0">
              <div>
                <h3 className="font-bold text-lg flex items-center gap-2">
                  <CheckCircle2 className="w-5 h-5" />
                  Review & Approve Spare Order
                </h3>
                <p className="text-xs text-white/80 mt-0.5">{spoModalOrderNum}</p>
              </div>
              <button
                onClick={() => setSpoApproveModalOpen(false)}
                className="text-white/80 hover:text-white p-1 rounded-lg hover:bg-white/10"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6 overflow-y-auto space-y-4">
              <div className="border border-slate-200 rounded-xl overflow-hidden overflow-x-auto">
                <table className="w-full text-left text-xs border-collapse">
                  <thead className="bg-slate-50 border-b border-slate-200">
                    <tr>
                      <th className="p-2.5 font-bold text-slate-600">Item</th>
                      <th className="p-2.5 font-bold text-slate-600 text-center w-20">Qty</th>
                      <th className="p-2.5 font-bold text-slate-600 text-center w-16">UoM</th>
                      <th className="p-2.5 font-bold text-slate-600 text-right w-28">Rate (₹)</th>
                      <th className="p-2.5 font-bold text-slate-600 min-w-[200px]">Assigned Vendor</th>
                      <th className="p-2.5 w-10"></th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {spoModalLines
                      .filter((l) => !spoModalDeleted.includes(l.id))
                      .map((l) => (
                        <tr key={l.id}>
                          <td className="p-2.5">
                            <div className="font-bold text-slate-900">{l.item_name}</div>
                            <code className="text-[10px] text-indigo-600">{l.item_code}</code>
                            {l.demand_source && <span className="text-[10px] text-slate-400 ml-2">({l.demand_source})</span>}
                          </td>
                          <td className="p-2.5 text-center">
                            <Input
                              type="number"
                              min="1"
                              value={l.quantity}
                              onChange={(e) => {
                                const val = parseFloat(e.target.value) || 1;
                                setSpoModalLines((prev) =>
                                  prev.map((line) => (line.id === l.id ? { ...line, quantity: val } : line))
                                );
                              }}
                              className="w-16 h-7 text-xs text-center font-semibold"
                            />
                          </td>
                          <td className="p-2.5 text-center text-slate-500">{l.unit_of_measure || "PCS"}</td>
                          <td className="p-2.5 text-right">
                            <Input
                              type="number"
                              min="0"
                              step="0.01"
                              value={l.last_purchase_rate || l.last_rate || ""}
                              onChange={(e) => {
                                const val = parseFloat(e.target.value) || 0;
                                setSpoModalLines((prev) =>
                                  prev.map((line) => (line.id === l.id ? { ...line, last_purchase_rate: val } : line))
                                );
                              }}
                              className="w-24 h-7 text-xs text-right"
                              placeholder="0.00"
                            />
                          </td>
                          <td className="p-2.5 relative">
                            <div className="relative">
                              <Input
                                type="text"
                                placeholder="🔍 Type to search vendor..."
                                defaultValue={l.vendor_name && l.vendor_name !== "Vendor TBD" ? l.vendor_name : ""}
                                onChange={(e) => handleSpoVendorSearch(l.id, e.target.value)}
                                className={`h-7 text-xs ${
                                  l.vendor_id ? "border-emerald-500" : "border-amber-400 bg-amber-50/30"
                                }`}
                              />

                              {/* Dropdown */}
                              {spoVendorSearchOpen[l.id] && spoVendorSearchResults[l.id]?.length > 0 && (
                                <div className="absolute top-8 left-0 right-0 z-50 bg-white border border-slate-200 rounded-xl shadow-xl max-h-40 overflow-y-auto divide-y divide-slate-100">
                                  {spoVendorSearchResults[l.id].map((v: any) => (
                                    <div
                                      key={v.id}
                                      onClick={() => handleSpoSelectVendor(l.id, v.id, v.vendor_name)}
                                      className="p-2 hover:bg-blue-50 cursor-pointer"
                                    >
                                      <div className="font-bold text-xs text-slate-800">{v.vendor_name}</div>
                                      <div className="text-[10px] text-slate-400">
                                        {v.vendor_code || ""} • {v.phone || ""}
                                      </div>
                                    </div>
                                  ))}
                                </div>
                              )}
                            </div>
                            <div className="text-[10px] mt-0.5">
                              {l.vendor_id ? (
                                <span className="text-emerald-600 font-semibold">✓ {l.vendor_name}</span>
                              ) : (
                                <span className="text-amber-600 font-semibold">⚠ No vendor assigned</span>
                              )}
                            </div>
                          </td>
                          <td className="p-2.5 text-center">
                            <button
                              onClick={() => setSpoModalDeleted((prev) => [...prev, l.id])}
                              className="p-1 text-rose-500 hover:text-rose-700 hover:bg-rose-50 rounded"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          </td>
                        </tr>
                      ))}
                  </tbody>
                </table>
              </div>

              <div className="space-y-1.5">
                <Label className="text-xs font-bold text-slate-700">Approval Remarks / Notes</Label>
                <Textarea
                  placeholder="Optional notes or conditions for this approval..."
                  value={spoApproveNotes}
                  onChange={(e) => setSpoApproveNotes(e.target.value)}
                  rows={2}
                  className="rounded-xl text-sm"
                />
              </div>
            </div>

            <div className="p-4 px-6 bg-slate-50 border-t border-slate-200 flex justify-end gap-2 shrink-0">
              <Button onClick={() => setSpoApproveModalOpen(false)} variant="outline" className="rounded-xl text-xs h-9">
                Cancel
              </Button>
              <Button
                onClick={submitSpoApproval}
                disabled={spoApproving}
                className="bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs h-9 font-bold"
              >
                <CheckCircle2 className="w-3.5 h-3.5 mr-1" />
                {spoApproving ? "Approving..." : "Confirm Approval"}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* ══════════════════════════════════════════════════════════════════════════
          SLIDE-OVER: VENDOR SELECTION PANEL (FOR SPARE PARTS)
          ══════════════════════════════════════════════════════════════════════════ */}
      {vendorPanelOpen && currentSpareItem && (
        <div className="fixed inset-0 z-50 bg-black/50 flex justify-end animate-in fade-in duration-200">
          <div className="bg-white w-full max-w-lg h-full shadow-2xl overflow-y-auto flex flex-col animate-in slide-in-from-right duration-300">
            <div className="bg-gradient-to-br from-slate-900 to-indigo-900 text-white p-5 px-6 shrink-0 flex justify-between items-start">
              <div>
                <h3 className="font-bold text-base flex items-center gap-2">
                  <Store className="w-4 h-4 text-purple-400" />
                  Select Vendor for Item
                </h3>
                <p className="text-sm font-semibold text-white/90 mt-1">{currentSpareItem.item_name}</p>
                <p className="text-xs text-white/70 font-mono">{currentSpareItem.item_code}</p>
                <div className="flex gap-3 text-xs text-white/80 mt-2">
                  <span>Stock: <strong>{currentSpareItem.current_stock}</strong></span>
                  <span>Net Shortage: <strong className="text-amber-300">{currentSpareItem.net_shortage}</strong></span>
                </div>
              </div>

              <button
                onClick={() => setVendorPanelOpen(false)}
                className="text-white/80 hover:text-white p-1 rounded-lg hover:bg-white/10"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-5 overflow-y-auto space-y-5 flex-1">
              <Label className="text-xs font-bold text-slate-700 uppercase tracking-wider block">
                Linked Vendors ({itemVendors.length})
              </Label>

              {itemVendorsLoading ? (
                <div className="p-8 text-center text-slate-500">
                  <RefreshCw className="w-6 h-6 animate-spin mx-auto text-indigo-600 mb-2" />
                  <p className="text-xs">Loading linked vendors...</p>
                </div>
              ) : itemVendors.length === 0 ? (
                <div className="p-6 bg-slate-50 rounded-xl text-center text-slate-500 text-xs border border-slate-200">
                  No linked vendors found for this item in Vendor Master.
                </div>
              ) : (
                <div className="space-y-2">
                  {itemVendors.map((v) => (
                    <div
                      key={v.vendor_id}
                      onClick={() => handleSelectVendorInPanel(v)}
                      className={`p-3.5 rounded-xl border transition-all duration-200 cursor-pointer ${
                        selectedVendorForCart?.vendor_id === v.vendor_id
                          ? "border-indigo-600 bg-indigo-50/50 shadow-xs"
                          : "border-slate-200 hover:border-indigo-300 bg-white"
                      }`}
                    >
                      <div className="flex justify-between items-start">
                        <div>
                          <div className="font-bold text-sm text-slate-900">
                            {v.is_preferred && <span className="text-amber-500 mr-1">⭐</span>}
                            {v.vendor_name}
                          </div>
                          <div className="text-xs text-slate-500 mt-0.5">
                            {v.vendor_code || ""} {v.city ? `• ${v.city}` : ""}
                          </div>
                          {v.phone && <div className="text-xs text-slate-400">📱 {v.phone}</div>}
                        </div>
                        <div className="text-right">
                          {v.last_rate ? (
                            <div className="font-bold text-emerald-700 text-sm">₹ {formatNumber(v.last_rate)}</div>
                          ) : (
                            <span className="text-[10px] text-slate-400">No rate on file</span>
                          )}
                          {v.last_date && <div className="text-[10px] text-slate-400">Last: {formatDate(v.last_date)}</div>}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* Add to Order Inputs (When vendor selected) */}
              {selectedVendorForCart && (
                <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 space-y-3">
                  <h4 className="font-bold text-xs text-slate-800">
                    Configure Order for <span className="text-indigo-600">{selectedVendorForCart.vendor_name}</span>
                  </h4>

                  <div className="grid grid-cols-3 gap-2">
                    <div>
                      <Label className="text-[11px] text-slate-500">Qty</Label>
                      <Input
                        type="number"
                        min="1"
                        value={vpQty}
                        onChange={(e) => setVpQty(parseFloat(e.target.value) || 1)}
                        className="h-8 text-xs bg-white"
                      />
                    </div>
                    <div>
                      <Label className="text-[11px] text-slate-500">Rate (₹)</Label>
                      <Input
                        type="number"
                        min="0"
                        step="0.01"
                        value={vpRate}
                        onChange={(e) => setVpRate(e.target.value)}
                        placeholder="Rate"
                        className="h-8 text-xs bg-white"
                      />
                    </div>
                    <div>
                      <Label className="text-[11px] text-slate-500">UOM</Label>
                      <Input
                        type="text"
                        value={vpUom}
                        onChange={(e) => setVpUom(e.target.value)}
                        className="h-8 text-xs bg-white"
                      />
                    </div>
                  </div>

                  <Button
                    onClick={() => {
                      pushToSpareCart(
                        selectedVendorForCart.vendor_id,
                        selectedVendorForCart.vendor_name,
                        selectedVendorForCart.vendor_code || "",
                        selectedVendorForCart.phone || "",
                        currentSpareItem.item_id,
                        currentSpareItem.item_code,
                        currentSpareItem.item_name,
                        vpQty,
                        vpUom,
                        parseFloat(vpRate) || 0,
                        (currentSpareItem.req_sources || []).join(", ") || "General",
                        currentSpareItem.net_shortage || 1
                      );
                      setVendorPanelOpen(false);
                    }}
                    className="w-full bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-xs h-9 font-semibold"
                  >
                    <Plus className="w-3.5 h-3.5 mr-1" />
                    Add to Purchase Order Draft
                  </Button>
                </div>
              )}

              {/* Other Items from this vendor */}
              {selectedVendorForCart && vendorOtherItems.length > 0 && (
                <div className="space-y-2">
                  <Label className="text-xs font-bold text-slate-700 uppercase tracking-wider block">
                    Other Spare Items From {selectedVendorForCart.vendor_name}
                  </Label>
                  <div className="divide-y divide-slate-100 border border-slate-200 rounded-xl overflow-hidden">
                    {vendorOtherItems.map((oi) => (
                      <div key={oi.item_id} className="p-2.5 flex justify-between items-center text-xs bg-white">
                        <div>
                          <div className="font-semibold text-slate-800">{oi.item_name}</div>
                          <div className="text-[10px] text-slate-400">
                            <code>{oi.item_code}</code> • Stock: {oi.current_stock ?? 0}
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          {oi.last_rate && <span className="font-bold text-emerald-700">₹ {formatNumber(oi.last_rate)}</span>}
                          <Button
                            onClick={() => {
                              pushToSpareCart(
                                selectedVendorForCart.vendor_id,
                                selectedVendorForCart.vendor_name,
                                selectedVendorForCart.vendor_code || "",
                                selectedVendorForCart.phone || "",
                                oi.item_id,
                                oi.item_code,
                                oi.item_name,
                                1,
                                oi.unit_of_measure || "PCS",
                                oi.last_rate || 0,
                                "General",
                                0
                              );
                            }}
                            variant="outline"
                            size="sm"
                            className="h-6 text-[10px] px-2"
                          >
                            + Add
                          </Button>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ══════════════════════════════════════════════════════════════════════════
          MODAL: UPDATE REQUEST STATUS
          ══════════════════════════════════════════════════════════════════════════ */}
      {statusModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4 overflow-y-auto animate-in fade-in duration-200">
          <div className="bg-white rounded-2xl max-w-md w-full shadow-2xl overflow-hidden my-8">
            <div className="bg-gradient-to-r from-blue-700 to-indigo-700 text-white p-4 px-6 flex justify-between items-center">
              <h3 className="font-bold text-base flex items-center gap-2">
                <Edit className="w-4 h-4" />
                Update Request Status
              </h3>
              <button
                onClick={() => setStatusModalOpen(false)}
                className="text-white/80 hover:text-white p-1 rounded-lg hover:bg-white/10"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6 space-y-4">
              <div className="space-y-1.5">
                <Label className="text-xs font-bold text-slate-700">New Status *</Label>
                <select
                  value={newStatusValue}
                  onChange={(e) => setNewStatusValue(e.target.value)}
                  className="w-full h-10 px-3 border border-slate-300 rounded-xl text-sm bg-white text-slate-700 outline-none"
                >
                  <option value="">— Select Status —</option>
                  <option value="COMPLETED">✅ Completed — Delivery Accepted</option>
                  <option value="CANCELLED">❌ Cancelled — Request Withdrawn</option>
                  <option value="RETURNED_FOR_QUALITY">↩ Returned for Quality — Items Sent Back</option>
                </select>
              </div>

              {newStatusValue === "RETURNED_FOR_QUALITY" && (
                <div className="p-4 bg-amber-50/70 border border-amber-200 rounded-xl space-y-3">
                  <h4 className="font-bold text-xs text-amber-900 flex items-center gap-1.5">
                    <RotateCcw className="w-3.5 h-3.5" /> Quality Return Details
                  </h4>

                  <div className="flex gap-4 text-xs font-semibold text-slate-700">
                    <label className="flex items-center gap-1.5 cursor-pointer">
                      <input
                        type="radio"
                        name="returnType"
                        value="PARTIAL"
                        checked={returnType === "PARTIAL"}
                        onChange={() => setReturnType("PARTIAL")}
                        className="text-amber-600"
                      />
                      Partial Return (some items)
                    </label>
                    <label className="flex items-center gap-1.5 cursor-pointer">
                      <input
                        type="radio"
                        name="returnType"
                        value="COMPLETE"
                        checked={returnType === "COMPLETE"}
                        onChange={() => setReturnType("COMPLETE")}
                        className="text-amber-600"
                      />
                      Complete Return (all items)
                    </label>
                  </div>

                  <div className="space-y-1">
                    <Label className="text-[11px] font-bold text-amber-900">Reason / Items Returned *</Label>
                    <Textarea
                      placeholder="Describe the defect, returned item codes, and quantities..."
                      value={returnNotes}
                      onChange={(e) => setReturnNotes(e.target.value)}
                      rows={3}
                      className="rounded-xl text-xs bg-white"
                    />
                  </div>
                </div>
              )}

              <div className="space-y-1.5">
                <Label className="text-xs font-bold text-slate-700">Additional Remarks</Label>
                <Textarea
                  placeholder="Optional remarks..."
                  value={statusGeneralNotes}
                  onChange={(e) => setStatusGeneralNotes(e.target.value)}
                  rows={2}
                  className="rounded-xl text-sm"
                />
              </div>
            </div>

            <div className="p-4 px-6 bg-slate-50 border-t border-slate-200 flex justify-end gap-2">
              <Button onClick={() => setStatusModalOpen(false)} variant="outline" className="rounded-xl text-xs h-9">
                Cancel
              </Button>
              <Button
                onClick={submitStatusUpdate}
                disabled={statusSubmitting}
                className="bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-xs h-9 font-semibold"
              >
                {statusSubmitting ? "Updating..." : "Update Status"}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* ══════════════════════════════════════════════════════════════════════════
          MODAL: SEND WHATSAPP TO VENDOR
          ══════════════════════════════════════════════════════════════════════════ */}
      {waModalOpen && waReqData && (
        <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4 overflow-y-auto animate-in fade-in duration-200">
          <div className="bg-white rounded-2xl max-w-2xl w-full shadow-2xl overflow-hidden my-8 max-h-[90vh] flex flex-col">
            <div className="bg-gradient-to-r from-emerald-600 to-teal-600 text-white p-4 px-6 flex justify-between items-center shrink-0">
              <h3 className="font-bold text-base flex items-center gap-2">
                <MessageCircle className="w-5 h-5" />
                Send Quotation Request via WhatsApp
              </h3>
              <button
                onClick={() => setWaModalOpen(false)}
                className="text-white/80 hover:text-white p-1 rounded-lg hover:bg-white/10"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6 overflow-y-auto space-y-4">
              {/* Vendor Info Header */}
              <div className="p-3.5 bg-emerald-50/70 border border-emerald-200 rounded-xl flex justify-between items-center text-xs">
                <div>
                  <span className="text-[10px] uppercase font-bold text-emerald-800 tracking-wider">Vendor Recipient</span>
                  <div className="font-bold text-sm text-slate-900">{waReqData.approved_vendor_name || "Unknown Vendor"}</div>
                  <div className="text-slate-500">
                    {waReqData.approved_vendor_phone ? `📱 ${waReqData.approved_vendor_phone}` : "No phone number recorded"}
                  </div>
                </div>

                <Badge variant={waReqData.approved_vendor_phone ? "secondary" : "destructive"}>
                  {waReqData.approved_vendor_phone ? "Phone on file" : "No Phone"}
                </Badge>
              </div>

              {/* Missing Specs Detector */}
              {(() => {
                const missing = (waReqData.items || [])
                  .map((it, idx) => {
                    const noColors = !it.colors || (Array.isArray(it.colors) && !it.colors.length);
                    return {
                      idx,
                      it,
                      noSpec: !it.specification,
                      noBrand: !it.brand,
                      noModel: !it.model_compat,
                      noColours: noColors,
                    };
                  })
                  .filter((x) => x.noSpec || x.noBrand || x.noModel || x.noColours);

                if (!missing.length) return null;

                return (
                  <div className="p-3.5 bg-amber-50 border border-amber-200 rounded-xl space-y-3">
                    <div className="flex justify-between items-center">
                      <span className="text-xs font-bold text-amber-900 flex items-center gap-1.5">
                        <AlertTriangle className="w-4 h-4 text-amber-600" />
                        Missing specifications detected — fill before sending
                      </span>
                    </div>

                    <div className="space-y-2 max-h-48 overflow-y-auto">
                      {missing.map(({ idx, it, noBrand, noModel, noColours, noSpec }) => (
                        <div key={idx} className="p-2.5 bg-white border border-amber-200 rounded-lg text-xs space-y-2">
                          <div className="font-bold text-slate-800">
                            {idx + 1}. {it.item_name} <code className="text-[10px] text-slate-400">({it.item_code})</code>
                          </div>
                          <div className="grid grid-cols-2 gap-2">
                            {noBrand && (
                              <Input
                                type="text"
                                placeholder="Brand (e.g. Exide)"
                                onChange={(e) => updateSpecOverride(idx, "brand", e.target.value)}
                                className="h-7 text-xs"
                              />
                            )}
                            {noModel && (
                              <Input
                                type="text"
                                placeholder="Model / Compatible With"
                                onChange={(e) => updateSpecOverride(idx, "model_compat", e.target.value)}
                                className="h-7 text-xs"
                              />
                            )}
                            {noColours && (
                              <Input
                                type="text"
                                placeholder="Colour (e.g. Red, Black)"
                                onChange={(e) => updateSpecOverride(idx, "colors", e.target.value)}
                                className="h-7 text-xs"
                              />
                            )}
                            {noSpec && (
                              <Input
                                type="text"
                                placeholder="Specification (e.g. 60V 45Ah)"
                                onChange={(e) => updateSpecOverride(idx, "specification", e.target.value)}
                                className="h-7 text-xs"
                              />
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                );
              })()}

              {/* Message Editor */}
              <div className="space-y-1.5">
                <Label className="text-xs font-bold text-slate-700">Message Preview (Editable)</Label>
                <Textarea
                  value={waMessage}
                  onChange={(e) => setWaMessage(e.target.value)}
                  rows={10}
                  className="font-mono text-xs rounded-xl"
                />
              </div>

              {/* Attachment Format Selection */}
              <div className="p-3.5 bg-slate-50 border border-slate-200 rounded-xl flex justify-between items-center text-xs">
                <span className="font-bold text-slate-700 flex items-center gap-1.5">
                  <Download className="w-4 h-4 text-purple-600" />
                  Attachment Format:
                </span>
                <div className="flex gap-4">
                  <label className="flex items-center gap-1.5 cursor-pointer font-semibold">
                    <input
                      type="radio"
                      name="waAttachFormat"
                      value="excel"
                      checked={waAttachFormat === "excel"}
                      onChange={() => setWaAttachFormat("excel")}
                      className="text-emerald-600"
                    />
                    Excel Spreadsheet (.csv/.xlsx)
                  </label>
                  <label className="flex items-center gap-1.5 cursor-pointer font-semibold">
                    <input
                      type="radio"
                      name="waAttachFormat"
                      value="pdf"
                      checked={waAttachFormat === "pdf"}
                      onChange={() => setWaAttachFormat("pdf")}
                      className="text-rose-600"
                    />
                    PDF Document
                  </label>
                </div>
              </div>
            </div>

            <div className="p-4 px-6 bg-slate-50 border-t border-slate-200 flex justify-between items-center shrink-0">
              <Button onClick={() => setWaModalOpen(false)} variant="outline" className="rounded-xl text-xs h-9">
                Close
              </Button>

              <div className="flex items-center gap-2">
                <Button
                  onClick={() => {
                    if (waAttachFormat === "pdf") downloadProcPDF(waReqData, waSpecOverrides);
                    else downloadProcExcel(waReqData, waSpecOverrides);
                  }}
                  variant="outline"
                  className="rounded-xl text-xs h-9 font-semibold"
                >
                  <Download className="w-3.5 h-3.5 mr-1" />
                  Download {waAttachFormat.toUpperCase()}
                </Button>

                <Button
                  onClick={handleOpenWhatsAppWeb}
                  className="bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs h-9 font-bold"
                >
                  <MessageCircle className="w-3.5 h-3.5 mr-1" />
                  Open WhatsApp Web
                </Button>

                <Button
                  onClick={handleSendWhatsAppAPI}
                  disabled={waSending}
                  className="bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-xs h-9 font-bold"
                >
                  <Send className="w-3.5 h-3.5 mr-1" />
                  {waSending ? "Sending..." : "Send via API"}
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ══════════════════════════════════════════════════════════════════════════
          MODAL: VIEW REQUIREMENT DETAILS
          ══════════════════════════════════════════════════════════════════════════ */}
      {viewReqModalOpen && activeViewReq && (
        <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4 overflow-y-auto animate-in fade-in duration-200">
          <div className="bg-white rounded-2xl max-w-2xl w-full shadow-2xl overflow-hidden my-8">
            <div className="bg-gradient-to-r from-purple-700 to-indigo-700 text-white p-4 px-6 flex justify-between items-center">
              <h3 className="font-bold text-base flex items-center gap-2">
                <ClipboardList className="w-5 h-5" />
                Requirement Details — {activeViewReq.requirement_number}
              </h3>
              <button
                onClick={() => setViewReqModalOpen(false)}
                className="text-white/80 hover:text-white p-1 rounded-lg hover:bg-white/10"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6 space-y-4">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 p-3.5 bg-slate-50 rounded-xl border border-slate-200 text-xs">
                <div>
                  <span className="text-slate-400 block font-semibold">Company</span>
                  <span className="font-bold text-slate-800">{activeViewReq.company_name || "—"}</span>
                </div>
                <div>
                  <span className="text-slate-400 block font-semibold">Source</span>
                  <span className="font-bold text-indigo-600">{activeViewReq.source_type.replace(/_/g, " ")}</span>
                </div>
                <div>
                  <span className="text-slate-400 block font-semibold">Priority</span>
                  <span className="font-bold text-slate-800">{activeViewReq.priority}</span>
                </div>
                <div>
                  <span className="text-slate-400 block font-semibold">Shortage Value</span>
                  <span className="font-bold text-emerald-700">₹ {formatNumber(activeViewReq.total_shortage_value)}</span>
                </div>
              </div>

              <div className="border border-slate-200 rounded-xl overflow-hidden">
                <table className="w-full text-left text-xs border-collapse">
                  <thead className="bg-slate-50 border-b border-slate-200">
                    <tr>
                      <th className="p-2.5 font-bold text-slate-600">Component</th>
                      <th className="p-2.5 font-bold text-slate-600 text-right">Required</th>
                      <th className="p-2.5 font-bold text-slate-600 text-right">Available</th>
                      <th className="p-2.5 font-bold text-slate-600 text-right">Shortage</th>
                      <th className="p-2.5 font-bold text-slate-600 text-center">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {(activeViewReq.line_items || []).map((l, idx) => (
                      <tr key={idx}>
                        <td className="p-2.5">
                          <div className="font-bold text-slate-900">{l.component_name || l.stock_item_name}</div>
                          <code className="text-[10px] text-purple-600">{l.component_code || l.stock_item_code}</code>
                        </td>
                        <td className="p-2.5 text-right font-medium">{formatNumber(l.required_qty)}</td>
                        <td className="p-2.5 text-right text-slate-500">{formatNumber(l.available_qty)}</td>
                        <td className="p-2.5 text-right font-bold text-rose-600">{formatNumber(l.shortage_qty)}</td>
                        <td className="p-2.5 text-center">
                          <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-100 text-amber-800">
                            {l.status}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            <div className="p-4 px-6 bg-slate-50 border-t border-slate-200 flex justify-end">
              <Button onClick={() => setViewReqModalOpen(false)} variant="outline" className="rounded-xl text-xs h-9">
                Close
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
