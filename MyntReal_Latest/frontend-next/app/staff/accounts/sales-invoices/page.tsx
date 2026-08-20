"use client";

import React, { useState, useEffect, useMemo, useCallback, useRef } from "react";
import api, { getApiUrl } from "@/lib/api";
import { useStaffAuth } from "@/contexts/StaffAuthContext";
import toast, { Toaster } from "react-hot-toast";
import {
  FileText,
  Plus,
  Search,
  RefreshCw,
  Eye,
  FileCheck,
  Truck,
  DollarSign,
  Trash2,
  Edit,
  CheckCircle,
  XCircle,
  RotateCcw,
  Ban,
  Clock,
  Building,
  Package,
  Calendar,
  User,
  Phone,
  Mail,
  MapPin,
  Percent,
  Download,
  Printer,
  ChevronDown,
  ChevronRight,
  ShieldCheck,
  Barcode,
  Layers,
  Sparkles,
  Ticket,
  AlertCircle,
  HelpCircle,
  X,
  ExternalLink,
  ChevronUp
} from "lucide-react";

// Types & Interfaces
interface Company {
  id: number;
  company_name: string;
  state?: string;
  gstin?: string;
  [key: string]: any;
}

interface BillingCompany {
  id: number;
  name: string;
}

interface HsnCode {
  id: number;
  hsn_code: string;
  description?: string;
  cgst_rate?: number;
  sgst_rate?: number;
  igst_rate?: number;
  is_active?: boolean;
}

interface StockItem {
  id: number | string;
  _source?: "STOCK" | "CATALOG";
  item_name: string;
  item_code?: string;
  sku?: string;
  selling_rate?: number;
  effective_selling_rate?: number;
  default_gst_rate?: number;
  gst_rate?: number;
  specification?: string;
  colors?: string[] | string;
  hsn_code?: string;
  hsn_id?: number;
  unit_of_measure?: string;
  uom?: string;
  warranty_details?: string;
  size?: string;
}

interface LineItemForm {
  id?: number | null;
  item_id: number | null;
  item_description: string;
  hsn_id: number | null;
  hsn_code: string;
  quantity: number;
  unit_rate: number;
  discount_percent: number;
  gst_rate: number;
  specification: string;
  color: string;
  warranty_details: string;
  batch_number: string;
  serial_numbers: string;
  is_custom?: boolean;
}

interface SalesInvoice {
  id: number;
  invoice_number: string;
  invoice_date: string;
  document_type: "tax_invoice" | "estimate" | "credit_note";
  return_reference?: string | null;
  company_id: number;
  company_name?: string;
  billing_company_id?: number | null;
  billing_company_name?: string;
  customer_type: string;
  customer_id?: number | null;
  customer_real_type?: string;
  customer_name: string;
  customer_phone?: string;
  customer_state?: string;
  customer_gstin?: string;
  customer_email?: string;
  billing_address?: string;
  shipping_address?: string;
  remarks?: string;
  so_number?: string;
  is_igst: boolean;
  status: "DRAFT" | "CONFIRMED" | "CANCELLED" | "VOIDED";
  payment_status: "PAID" | "PARTIAL" | "PENDING" | "OVERDUE";
  amount_received?: number;
  balance_due?: number;
  subtotal?: number;
  total_discount?: number;
  taxable_amount?: number;
  cgst_amount?: number;
  sgst_amount?: number;
  igst_amount?: number;
  courier_amount?: number;
  courier_hsn_code?: string;
  courier_hsn_id?: number;
  courier_gst_rate?: number;
  courier_cgst_amount?: number;
  courier_sgst_amount?: number;
  courier_igst_amount?: number;
  transport_amount?: number;
  transport_hsn_code?: string;
  transport_hsn_id?: number;
  transport_gst_rate?: number;
  transport_cgst_amount?: number;
  transport_sgst_amount?: number;
  transport_igst_amount?: number;
  coupon_code?: string;
  coupon_discount_pct?: number;
  coupon_discount_amount?: number;
  manual_discount_amount?: number;
  manual_discount_note?: string;
  round_off?: number;
  grand_total?: number;
  net_payable?: number;
  line_items?: any[];
  track_physical_dispatch?: boolean;
  cancelled_by_name?: string;
  cancelled_by_id?: number;
  cancelled_at?: string;
  cancellation_reason?: string;
}

interface PendingDispatchLine {
  id: number;
  line_number: number;
  item_description: string;
  item_code?: string;
  unit_of_measure: string;
  invoiced_qty: number;
  configured_pending_qty: number;
  dispatched_qty: number;
  pending_qty: number;
  sale_rate?: number;
}

interface PendingDispatchExtraItem {
  id: number;
  item_description: string;
  item_code?: string;
  unit_of_measure: string;
  pending_qty: number;
  dispatched_qty: number;
  remaining_qty: number;
  notes?: string;
}

interface PendingDispatchInvoice {
  id: number;
  invoice_number: string;
  customer_name: string;
  invoice_date: string;
  dispatch_status: "NOT_DISPATCHED" | "PARTIALLY_DISPATCHED" | "DISPATCHED";
  total_pending_qty: number;
  total_pending_value: number;
  lines: PendingDispatchLine[];
  extra_items?: PendingDispatchExtraItem[];
}

interface PaymentRecord {
  id: number;
  payment_date: string;
  payment_mode: string;
  amount: number;
  reference_number?: string;
  notes?: string;
  created_by?: string;
}

interface Coupon {
  id: number;
  coupon_code: string;
  discount_percentage: number;
  valid_from?: string;
  valid_until?: string;
  times_used?: number;
  max_uses?: number;
  is_active: boolean;
  description?: string;
}

interface NarrationEntry {
  id?: number;
  narration: string;
  created_by_name?: string;
  created_at?: string;
}

const INDIAN_STATES = [
  "Andhra Pradesh",
  "Arunachal Pradesh",
  "Assam",
  "Bihar",
  "Chhattisgarh",
  "Goa",
  "Gujarat",
  "Haryana",
  "Himachal Pradesh",
  "Jharkhand",
  "Karnataka",
  "Kerala",
  "Madhya Pradesh",
  "Maharashtra",
  "Manipur",
  "Meghalaya",
  "Mizoram",
  "Nagaland",
  "Odisha",
  "Punjab",
  "Rajasthan",
  "Sikkim",
  "Tamil Nadu",
  "Telangana",
  "Tripura",
  "Uttar Pradesh",
  "Uttarakhand",
  "West Bengal",
  "Andaman and Nicobar Islands",
  "Chandigarh",
  "Dadra and Nagar Haveli and Daman and Diu",
  "Delhi",
  "Jammu and Kashmir",
  "Ladakh",
  "Lakshadweep",
  "Puducherry",
  "Other"
];

const PARTY_TYPE_COLORS: Record<string, string> = {
  VENDOR: "bg-amber-100 text-amber-800 border-amber-300",
  DEALER: "bg-blue-100 text-blue-800 border-blue-300",
  DISTRIBUTOR: "bg-purple-100 text-purple-800 border-purple-300",
  VGK_MEMBER: "bg-emerald-100 text-emerald-800 border-emerald-300",
  MNR_MEMBER: "bg-sky-100 text-sky-800 border-sky-300",
  PARTNER: "bg-gray-100 text-gray-800 border-gray-300",
  STAFF: "bg-amber-100 text-amber-900 border-amber-400",
  COMPANY: "bg-slate-100 text-slate-800 border-slate-300",
  EXTERNAL: "bg-zinc-100 text-zinc-800 border-zinc-300",
  PARTNER_VENDOR: "bg-amber-100 text-amber-800 border-amber-300",
  RD_PARTNER: "bg-pink-100 text-pink-800 border-pink-300",
  SERVICE_CENTER: "bg-orange-100 text-orange-800 border-orange-300"
};

export default function SalesInvoicesPage() {
  const { user, token } = useStaffAuth();

  // Navigation tabs
  const [activeTab, setActiveTab] = useState<"invoices" | "pending" | "summary">("invoices");

  // Master Data
  const [companies, setCompanies] = useState<Company[]>([]);
  const [billingCompanies, setBillingCompanies] = useState<BillingCompany[]>([]);
  const [stockItems, setStockItems] = useState<StockItem[]>([]);
  const [hsnCodes, setHsnCodes] = useState<HsnCode[]>([]);

  // Filters
  const [selectedCompanyId, setSelectedCompanyId] = useState<string>("");
  const [filterStatus, setFilterStatus] = useState<string>("");
  const [filterCustomerType, setFilterCustomerType] = useState<string>("");
  const [filterFromDate, setFilterFromDate] = useState<string>("");
  const [filterToDate, setFilterToDate] = useState<string>("");
  const [activePeriod, setActivePeriod] = useState<string>("month");

  // Invoice List State
  const [invoices, setInvoices] = useState<SalesInvoice[]>([]);
  const [loadingInvoices, setLoadingInvoices] = useState<boolean>(false);

  // Computed KPI Stats
  const stats = useMemo(() => {
    const total = invoices.length;
    const draft = invoices.filter((i) => i.status === "DRAFT").length;
    const confirmed = invoices.filter((i) => i.status === "CONFIRMED").length;
    const cancelled = invoices.filter((i) => i.status === "CANCELLED").length;
    const voided = invoices.filter((i) => i.status === "VOIDED").length;
    const confirmedVal = invoices
      .filter((i) => i.status === "CONFIRMED")
      .reduce((sum, i) => sum + Number((i.manual_discount_amount && i.manual_discount_amount > 0) ? i.net_payable || 0 : i.grand_total || 0), 0);

    return { total, draft, confirmed, cancelled, voided, confirmedVal };
  }, [invoices]);

  // Selected Company Object
  const currentCompany = useMemo(() => {
    return companies.find((c) => String(c.id) === String(selectedCompanyId));
  }, [companies, selectedCompanyId]);

  // Role Gate
  const canDelete = useMemo(() => {
    if (!user) return false;
    const rn = (user.role_name || "").toLowerCase();
    const rc = (user.role_code || "").toLowerCase();
    const dn = (user.department_name || "").toLowerCase();
    return (
      rn.includes("vgk") ||
      rn.includes("executive") ||
      rn.includes("accounts") ||
      rn === "ea" ||
      rc === "vgk4u" ||
      rc === "ea" ||
      rc === "accounts" ||
      dn.includes("accounts") ||
      dn.includes("finance")
    );
  }, [user]);

  // Modals & Panels State
  const [isCreateModalOpen, setIsCreateModalOpen] = useState<boolean>(false);
  const [isViewModalOpen, setIsViewModalOpen] = useState<boolean>(false);
  const [isConfirmModalOpen, setIsConfirmModalOpen] = useState<boolean>(false);
  const [isPaymentModalOpen, setIsPaymentModalOpen] = useState<boolean>(false);
  const [isCouponManagerOpen, setIsCouponManagerOpen] = useState<boolean>(false);
  const [isQuickCreateOpen, setIsQuickCreateOpen] = useState<boolean>(false);
  const [quickCreateType, setQuickCreateType] = useState<"stockitem" | "hsn" | "partner">("stockitem");
  const [isAddPendingModalOpen, setIsAddPendingModalOpen] = useState<boolean>(false);
  const [isPdfViewerOpen, setIsPdfViewerOpen] = useState<boolean>(false);
  const [pdfBlobUrl, setPdfBlobUrl] = useState<string | null>(null);
  const [pdfViewerTitle, setPdfViewerTitle] = useState<string>("");
  const [pdfViewerFilename, setPdfViewerFilename] = useState<string>("");

  // Create/Edit Invoice Form State
  const [editingInvoiceId, setEditingInvoiceId] = useState<number | null>(null);
  const [editingInvoiceStatus, setEditingInvoiceStatus] = useState<string>("DRAFT");
  const [docType, setDocType] = useState<"tax_invoice" | "estimate" | "credit_note">("tax_invoice");
  const [creditNoteRef, setCreditNoteRef] = useState<string>("");
  const [billingCompanyId, setBillingCompanyId] = useState<string>("");
  const [invoiceDate, setInvoiceDate] = useState<string>(new Date().toISOString().split("T")[0]);
  const [soNumber, setSoNumber] = useState<string>("");
  const [customerType, setCustomerType] = useState<"WALK_IN" | "REGISTERED">("WALK_IN");
  const [customerName, setCustomerName] = useState<string>("");
  const [customerId, setCustomerId] = useState<number | null>(null);
  const [customerPhone, setCustomerPhone] = useState<string>("");
  const [customerState, setCustomerState] = useState<string>("");
  const [customerGstin, setCustomerGstin] = useState<string>("");
  const [customerEmail, setCustomerEmail] = useState<string>("");
  const [billingAddress, setBillingAddress] = useState<string>("");
  const [shippingAddress, setShippingAddress] = useState<string>("");
  const [shipSameAsBilling, setShipSameAsBilling] = useState<boolean>(true);
  const [invoiceRemarks, setInvoiceRemarks] = useState<string>("");
  const [gstTypeOverride, setGstTypeOverride] = useState<"auto" | "igst" | "cgst_sgst">("auto");

  // Party search in Create Modal
  const [partySearchQuery, setPartySearchQuery] = useState<string>("");
  const [partySearchResults, setPartySearchResults] = useState<any[]>([]);
  const [isSearchingParty, setIsSearchingParty] = useState<boolean>(false);
  const [selectedPartyBadge, setSelectedPartyBadge] = useState<any | null>(null);
  const partySearchTimer = useRef<NodeJS.Timeout | null>(null);

  // Line items
  const [lineItems, setLineItems] = useState<LineItemForm[]>([]);
  const [stockSearchQuery, setStockSearchQuery] = useState<string>("");
  const [isStockSearchOpen, setIsStockSearchOpen] = useState<boolean>(false);

  // Additional Charges
  const [courierAmount, setCourierAmount] = useState<number>(0);
  const [courierHsnCode, setCourierHsnCode] = useState<string>("");
  const [courierHsnId, setCourierHsnId] = useState<number | null>(null);
  const [courierGstRate, setCourierGstRate] = useState<number>(0);

  const [transportAmount, setTransportAmount] = useState<number>(0);
  const [transportHsnCode, setTransportHsnCode] = useState<string>("");
  const [transportHsnId, setTransportHsnId] = useState<number | null>(null);
  const [transportGstRate, setTransportGstRate] = useState<number>(0);

  // Coupons & Manual Discount
  const [couponCodeInput, setCouponCodeInput] = useState<string>("");
  const [appliedCouponCode, setAppliedCouponCode] = useState<string>("");
  const [appliedCouponPct, setAppliedCouponPct] = useState<number>(0);
  const [manualDiscountAmount, setManualDiscountAmount] = useState<number>(0);
  const [manualDiscountNote, setManualDiscountNote] = useState<string>("");

  // Narration History
  const [narrations, setNarrations] = useState<NarrationEntry[]>([]);
  const [loadingNarrations, setLoadingNarrations] = useState<boolean>(false);

  // View Invoice Detail Modal State
  const [viewInvoiceData, setViewInvoiceData] = useState<SalesInvoice | null>(null);
  const [viewGstToggle, setViewGstToggle] = useState<boolean>(false);
  const [invoicePayments, setInvoicePayments] = useState<PaymentRecord[]>([]);
  const [loadingPayments, setLoadingPayments] = useState<boolean>(false);

  // Inline Record Payment form in View Modal & Payment Modal
  const [payAmount, setPayAmount] = useState<string>("");
  const [payMode, setPayMode] = useState<string>("CASH");
  const [payDate, setPayDate] = useState<string>(new Date().toISOString().split("T")[0]);
  const [payRef, setPayRef] = useState<string>("");
  const [payNotes, setPayNotes] = useState<string>("");
  const [submittingPayment, setSubmittingPayment] = useState<boolean>(false);

  // Confirm Invoice State
  const [confirmInvoiceId, setConfirmInvoiceId] = useState<number | null>(null);
  const [confirmStatus, setConfirmStatus] = useState<string>("DRAFT");
  const [confirmAmountReceived, setConfirmAmountReceived] = useState<number>(0);
  const [submittingConfirm, setSubmittingConfirm] = useState<boolean>(false);

  // Coupon Manager State
  const [couponsList, setCouponsList] = useState<Coupon[]>([]);
  const [newCouponCode, setNewCouponCode] = useState<string>("");
  const [newCouponPct, setNewCouponPct] = useState<number>(0);
  const [newCouponFrom, setNewCouponFrom] = useState<string>("");
  const [newCouponUntil, setNewCouponUntil] = useState<string>("");
  const [newCouponMaxUses, setNewCouponMaxUses] = useState<string>("");
  const [newCouponDesc, setNewCouponDesc] = useState<string>("");
  const [loadingCoupons, setLoadingCoupons] = useState<boolean>(false);

  // Quick Create State
  const [qcCode, setQcCode] = useState<string>("");
  const [qcName, setQcName] = useState<string>("");
  const [qcCategory, setQcCategory] = useState<string>("FINISHED_GOODS");
  const [qcHsnId, setQcHsnId] = useState<string>("");
  const [qcUom, setQcUom] = useState<string>("PCS");
  const [qcPurchaseRate, setQcPurchaseRate] = useState<number>(0);
  const [qcMarkupPct, setQcMarkupPct] = useState<number>(27);
  const [qcSaleRate, setQcSaleRate] = useState<number>(0);
  const [qcDesc, setQcDesc] = useState<string>("");
  const [qcHsnGstRate, setQcHsnGstRate] = useState<number>(18);
  const [qcHsnCess, setQcHsnCess] = useState<number>(0);
  const [submittingQuickCreate, setSubmittingQuickCreate] = useState<boolean>(false);

  // Pending Dispatch State
  const [pendingDispatches, setPendingDispatches] = useState<PendingDispatchInvoice[]>([]);
  const [loadingPending, setLoadingPending] = useState<boolean>(false);
  const [expandedPendingCard, setExpandedPendingCard] = useState<number | null>(null);
  const [dispatchFormDates, setDispatchFormDates] = useState<Record<number, string>>({});
  const [dispatchFormNarrs, setDispatchFormNarrs] = useState<Record<number, string>>({});
  const [dispatchFormQtys, setDispatchFormQtys] = useState<Record<string, number>>({});

  // Add Pending Modal State
  const [addPendingSearch, setAddPendingSearch] = useState<string>("");
  const [addPendingInvoices, setAddPendingInvoices] = useState<any[]>([]);
  const [selectedAddPendingInvoice, setSelectedAddPendingInvoice] = useState<any | null>(null);
  const [addPendingLineQtys, setAddPendingLineQtys] = useState<Record<number, number>>({});
  const [addPendingExtraItems, setAddPendingExtraItems] = useState<any[]>([]);

  // Summary Tab State
  const [summarySubTab, setSummarySubTab] = useState<"item" | "day" | "customer">("item");
  const [itemWiseSummary, setItemWiseSummary] = useState<any[]>([]);
  const [dayWiseSummary, setDayWiseSummary] = useState<any[]>([]);
  const [customerWiseSummary, setCustomerWiseSummary] = useState<any[]>([]);
  const [loadingSummary, setLoadingSummary] = useState<boolean>(false);

  // -------------------------------------------------------------
  // INITIAL DATA FETCHING
  // -------------------------------------------------------------
  useEffect(() => {
    const savedCompanyId = typeof window !== "undefined" ? localStorage.getItem("sfms_selected_company_sales") : null;
    if (savedCompanyId) setSelectedCompanyId(savedCompanyId);

    handleSetPeriod("month");

    fetchCompanies();
    fetchStockItems();
    fetchHsnCodes();
    fetchBillingCompanies();
  }, [token]);

  useEffect(() => {
    if (selectedCompanyId) {
      localStorage.setItem("sfms_selected_company_sales", selectedCompanyId);
      loadInvoices();
      if (activeTab === "pending") loadPendingDispatches();
      if (activeTab === "summary") loadSummaryData();
    } else {
      setInvoices([]);
    }
  }, [selectedCompanyId, filterStatus, filterCustomerType, filterFromDate, filterToDate]);

  const fetchCompanies = async () => {
    try {
      const res = await api.get("/staff/accounts/companies");
      const list = res.data.companies || res.data || [];
      setCompanies(list);
      if (!selectedCompanyId && list.length > 0) {
        const saved = localStorage.getItem("sfms_selected_company_sales");
        const match = list.find((c: any) => String(c.id) === String(saved));
        setSelectedCompanyId(match ? String(match.id) : String(list[0].id));
      }
    } catch (err) {
      console.error("Error fetching companies:", err);
    }
  };

  const fetchBillingCompanies = async () => {
    try {
      const res = await api.get("/staff/accounts/sales-invoices/billing-companies");
      setBillingCompanies(res.data.companies || []);
    } catch (err) {
      console.error("Error fetching billing companies:", err);
    }
  };

  const fetchStockItems = async (skipCache = false) => {
    try {
      const cacheParam = skipCache ? "&skip_cache=true" : "";
      const [stockRes, catalogRes] = await Promise.allSettled([
        api.get(`/staff/accounts/stock-items?is_active=true&page_size=2000&include_summary=false${cacheParam}`),
        api.get(`/marketplace/catalog-search?limit=500`)
      ]);

      let combined: StockItem[] = [];

      if (stockRes.status === "fulfilled" && stockRes.value?.data) {
        const raw = stockRes.value.data.stock_items || stockRes.value.data.items || stockRes.value.data || [];
        combined = combined.concat(
          raw.map((i: any) => ({
            _source: "STOCK",
            id: i.id,
            item_name: i.item_name || i.name || "",
            item_code: i.item_code || "",
            sku: i.sku || i.item_code || "",
            selling_rate: i.selling_rate || i.effective_selling_rate || 0,
            default_gst_rate: i.default_gst_rate || i.gst_rate || 18,
            specification: i.specification || "",
            colors: i.colors || [],
            hsn_code: i.hsn_code || "",
            hsn_id: i.hsn_id || null,
            unit_of_measure: i.unit_of_measure || "PCS"
          }))
        );
      }

      if (catalogRes.status === "fulfilled" && catalogRes.value?.data) {
        const catalog = catalogRes.value.data;
        const raw = Array.isArray(catalog) ? catalog : catalog.data || [];
        combined = combined.concat(
          raw.map((i: any) => ({
            _source: "CATALOG",
            id: "CAT_" + i.id,
            item_name: i.name || "",
            item_code: i.sku || "",
            sku: i.sku || "",
            selling_rate: i.dealer_price || i.net_before_tax || 0,
            default_gst_rate: i.gst_percent || 18,
            specification: i.specifications || "",
            colors: i.color ? [i.color] : [],
            hsn_code: i.hsn_code || "",
            warranty_details: i.warranty_details || "",
            unit_of_measure: "PCS"
          }))
        );
      }

      setStockItems(combined);
    } catch (err) {
      console.error("Error fetching stock items:", err);
    }
  };

  const fetchHsnCodes = async () => {
    try {
      const res = await api.get("/staff/accounts/hsn");
      setHsnCodes(res.data.hsn_codes || res.data || []);
    } catch (err) {
      console.error("Error fetching HSN codes:", err);
    }
  };

  // -------------------------------------------------------------
  // INVOICES LIST & ACTIONS
  // -------------------------------------------------------------
  const loadInvoices = async () => {
    if (!selectedCompanyId) return;
    setLoadingInvoices(true);
    try {
      let url = `/staff/accounts/sales-invoices?limit=100&company_id=${selectedCompanyId}`;
      if (filterStatus) url += `&status=${filterStatus}`;
      if (filterCustomerType) url += `&customer_type=${filterCustomerType}`;
      if (filterFromDate) url += `&from_date=${filterFromDate}`;
      if (filterToDate) url += `&to_date=${filterToDate}`;

      const res = await api.get(url);
      setInvoices(res.data.invoices || []);
    } catch (err: any) {
      console.error("Error loading invoices:", err);
      toast.error(err.response?.data?.detail || "Failed to load sales invoices");
    } finally {
      setLoadingInvoices(false);
    }
  };

  const handleSetPeriod = (period: string) => {
    setActivePeriod(period);
    const today = new Date();
    const fmt = (d: Date) => d.toISOString().split("T")[0];
    const endOfMonth = (d: Date) => new Date(d.getFullYear(), d.getMonth() + 1, 0);
    const endOfQuarter = (d: Date) => {
      const q = [2, 2, 2, 5, 5, 5, 8, 8, 8, 11, 11, 11][d.getMonth()];
      return new Date(d.getFullYear(), q + 1, 0);
    };
    const fyStart = () => {
      const m = today.getMonth();
      const y = m >= 3 ? today.getFullYear() : today.getFullYear() - 1;
      return new Date(y, 3, 1);
    };

    if (period === "month") {
      setFilterFromDate(fmt(new Date(today.getFullYear(), today.getMonth(), 1)));
      setFilterToDate(fmt(endOfMonth(today)));
    } else if (period === "quarter") {
      const qStart = [0, 0, 0, 3, 3, 3, 6, 6, 6, 9, 9, 9][today.getMonth()];
      setFilterFromDate(fmt(new Date(today.getFullYear(), qStart, 1)));
      setFilterToDate(fmt(endOfQuarter(today)));
    } else if (period === "fy") {
      setFilterFromDate(fmt(fyStart()));
      setFilterToDate(fmt(today));
    } else if (period === "overall") {
      setFilterFromDate("");
      setFilterToDate(fmt(today));
    }
  };

  // -------------------------------------------------------------
  // CREATE / EDIT INVOICE LOGIC & GST CALCULATION
  // -------------------------------------------------------------
  const isIgstActive = useMemo(() => {
    if (gstTypeOverride === "igst") return true;
    if (gstTypeOverride === "cgst_sgst") return false;
    if (!currentCompany) return false;
    const sellerState = currentCompany.state || "";
    const buyerState = customerState || "";
    return !!(buyerState && sellerState && buyerState.toLowerCase() !== sellerState.toLowerCase());
  }, [gstTypeOverride, currentCompany, customerState]);

  const invoiceCalculations = useMemo(() => {
    let subtotal = 0;
    let totalDiscount = 0;
    let taxableAmount = 0;
    let totalCgst = 0;
    let totalSgst = 0;
    let totalIgst = 0;

    lineItems.forEach((item) => {
      const gross = (item.quantity || 0) * (item.unit_rate || 0);
      const effDiscPct = appliedCouponPct > 0 ? appliedCouponPct : item.discount_percent || 0;
      const disc = gross * (effDiscPct / 100);
      const taxable = gross - disc;
      const gstAmt = docType === "estimate" ? 0 : taxable * ((item.gst_rate || 0) / 100);

      subtotal += gross;
      totalDiscount += disc;
      taxableAmount += taxable;

      if (docType !== "estimate") {
        if (isIgstActive) {
          totalIgst += gstAmt;
        } else {
          totalCgst += gstAmt / 2;
          totalSgst += gstAmt / 2;
        }
      }
    });

    const courierGstTotal = docType === "estimate" ? 0 : courierAmount * (courierGstRate / 100);
    const courierCgst = isIgstActive ? 0 : courierGstTotal / 2;
    const courierSgst = isIgstActive ? 0 : courierGstTotal / 2;
    const courierIgst = isIgstActive ? courierGstTotal : 0;

    const transportGstTotal = docType === "estimate" ? 0 : transportAmount * (transportGstRate / 100);
    const transportCgst = isIgstActive ? 0 : transportGstTotal / 2;
    const transportSgst = isIgstActive ? 0 : transportGstTotal / 2;
    const transportIgst = isIgstActive ? transportGstTotal : 0;

    const totalTax = totalCgst + totalSgst + totalIgst + courierGstTotal + transportGstTotal;
    const totalAdditional = courierAmount + transportAmount;

    let grandTotal = taxableAmount + totalTax + totalAdditional;
    const roundOff = Math.round(grandTotal) - grandTotal;
    grandTotal = Math.round(grandTotal);

    const netPayable = Math.max(0, grandTotal - (manualDiscountAmount || 0));

    return {
      subtotal,
      totalDiscount,
      taxableAmount,
      totalCgst: totalCgst + courierCgst + transportCgst,
      totalSgst: totalSgst + courierSgst + transportSgst,
      totalIgst: totalIgst + courierIgst + transportIgst,
      courierCgst,
      courierSgst,
      courierIgst,
      transportCgst,
      transportSgst,
      transportIgst,
      courierGstTotal,
      transportGstTotal,
      roundOff,
      grandTotal,
      netPayable
    };
  }, [
    lineItems,
    appliedCouponPct,
    docType,
    isIgstActive,
    courierAmount,
    courierGstRate,
    transportAmount,
    transportGstRate,
    manualDiscountAmount
  ]);

  const handleOpenCreateModal = () => {
    if (!selectedCompanyId) {
      toast.error("Please select a company first");
      return;
    }
    setEditingInvoiceId(null);
    setEditingInvoiceStatus("DRAFT");
    setDocType("tax_invoice");
    setCreditNoteRef("");
    setBillingCompanyId(selectedCompanyId);
    setInvoiceDate(new Date().toISOString().split("T")[0]);
    setSoNumber("");
    setCustomerType("WALK_IN");
    setCustomerName("");
    setCustomerId(null);
    setCustomerPhone("");
    setCustomerState("");
    setCustomerGstin("");
    setCustomerEmail("");
    setBillingAddress("");
    setShippingAddress("");
    setShipSameAsBilling(true);
    setInvoiceRemarks("");
    setGstTypeOverride("auto");
    setSelectedPartyBadge(null);

    setCourierAmount(0);
    setCourierHsnCode("");
    setCourierHsnId(null);
    setCourierGstRate(0);
    setTransportAmount(0);
    setTransportHsnCode("");
    setTransportHsnId(null);
    setTransportGstRate(0);

    setCouponCodeInput("");
    setAppliedCouponCode("");
    setAppliedCouponPct(0);
    setManualDiscountAmount(0);
    setManualDiscountNote("");
    setNarrations([]);

    setLineItems([
      {
        item_id: null,
        item_description: "",
        hsn_id: null,
        hsn_code: "",
        quantity: 1,
        unit_rate: 0,
        discount_percent: 0,
        gst_rate: 18,
        specification: "",
        color: "",
        warranty_details: "",
        batch_number: "",
        serial_numbers: "",
        is_custom: true
      }
    ]);

    setIsCreateModalOpen(true);
  };

  const handleOpenEditModal = async (invId: number, isConfirmed = false) => {
    if (isConfirmed) {
      const proceed = confirm(
        "Editing this confirmed invoice will require re-confirmation after saving.\n\n" +
          "After saving changes, use the Re-confirm button (↺) to recreate updated stock and ledger entries.\n\nProceed?"
      );
      if (!proceed) return;
    }

    try {
      const res = await api.get(`/staff/accounts/sales-invoices/${invId}?company_id=${selectedCompanyId}`);
      const inv = res.data.invoice || res.data;

      setEditingInvoiceId(inv.id);
      setEditingInvoiceStatus(inv.status);
      setDocType(inv.document_type || "tax_invoice");
      setCreditNoteRef(inv.return_reference || "");
      setBillingCompanyId(inv.billing_company_id ? String(inv.billing_company_id) : String(inv.company_id || selectedCompanyId));
      setInvoiceDate(inv.invoice_date || new Date().toISOString().split("T")[0]);
      setSoNumber(inv.so_number || "");
      const mappedType = ["PARTNER", "CORPORATE"].includes(inv.customer_type) ? "REGISTERED" : inv.customer_type || "WALK_IN";
      setCustomerType(mappedType as any);
      setCustomerName(inv.customer_name || "");
      setCustomerId(inv.customer_id || null);
      setCustomerPhone(inv.customer_phone || "");
      setCustomerState(inv.customer_state || "");
      setCustomerGstin(inv.customer_gstin || "");
      setCustomerEmail(inv.customer_email || "");
      setBillingAddress(inv.billing_address || inv.customer_address || "");
      setShippingAddress(inv.shipping_address || "");
      setShipSameAsBilling(
        !inv.shipping_address || inv.shipping_address === (inv.billing_address || inv.customer_address || "")
      );
      setInvoiceRemarks(inv.remarks || "");

      const autoIgst =
        currentCompany && inv.customer_state
          ? currentCompany.state?.toLowerCase() !== inv.customer_state?.toLowerCase()
          : false;
      if (inv.is_igst === autoIgst) {
        setGstTypeOverride("auto");
      } else {
        setGstTypeOverride(inv.is_igst ? "igst" : "cgst_sgst");
      }

      if (mappedType === "REGISTERED" && inv.customer_id) {
        setSelectedPartyBadge({
          id: inv.customer_id,
          name: inv.customer_name,
          type: "REGISTERED",
          phone: inv.customer_phone
        });
      } else {
        setSelectedPartyBadge(null);
      }

      setCourierAmount(inv.courier_amount || 0);
      setCourierHsnCode(inv.courier_hsn_code || "");
      setCourierHsnId(inv.courier_hsn_id || null);
      setCourierGstRate(inv.courier_gst_rate || 0);

      setTransportAmount(inv.transport_amount || 0);
      setTransportHsnCode(inv.transport_hsn_code || "");
      setTransportHsnId(inv.transport_hsn_id || null);
      setTransportGstRate(inv.transport_gst_rate || 0);

      setAppliedCouponCode(inv.coupon_code || "");
      setAppliedCouponPct(inv.coupon_discount_pct || 0);
      setCouponCodeInput(inv.coupon_code || "");
      setManualDiscountAmount(inv.manual_discount_amount || 0);
      setManualDiscountNote(inv.manual_discount_note || "");

      const loadedLines: LineItemForm[] = (inv.line_items || []).map((li: any) => ({
        id: li.id,
        item_id: li.item_id || null,
        item_description: li.item_description || "",
        hsn_id: li.hsn_id || null,
        hsn_code: li.hsn_code || "",
        quantity: parseFloat(li.quantity || 1),
        unit_rate: parseFloat(li.unit_rate || 0),
        discount_percent: parseFloat(li.discount_percent || 0),
        gst_rate: parseFloat(li.gst_rate || 18),
        specification: li.specification || "",
        color: li.color || "",
        warranty_details: li.warranty_details || (li.warranty_months ? `${li.warranty_months} months` : ""),
        batch_number: li.batch_number || "",
        serial_numbers: Array.isArray(li.serial_numbers) ? li.serial_numbers.join(", ") : li.serial_numbers || "",
        is_custom: !li.item_id
      }));

      setLineItems(loadedLines.length ? loadedLines : [
        {
          item_id: null,
          item_description: "",
          hsn_id: null,
          hsn_code: "",
          quantity: 1,
          unit_rate: 0,
          discount_percent: 0,
          gst_rate: 18,
          specification: "",
          color: "",
          warranty_details: "",
          batch_number: "",
          serial_numbers: "",
          is_custom: true
        }
      ]);

      loadNarrationHistory(inv.id);

      setIsCreateModalOpen(true);
    } catch (err: any) {
      console.error("Error loading invoice for edit:", err);
      toast.error(err.response?.data?.detail || "Failed to load invoice details");
    }
  };

  const handlePartySearch = (q: string) => {
    setCustomerName(q);
    if (customerType !== "REGISTERED" || !q || q.trim().length < 2) {
      setPartySearchResults([]);
      return;
    }

    if (partySearchTimer.current) clearTimeout(partySearchTimer.current);
    partySearchTimer.current = setTimeout(async () => {
      setIsSearchingParty(true);
      try {
        const res = await api.get(`/staff/accounts/party-search?q=${encodeURIComponent(q.trim())}&limit=25`);
        setPartySearchResults(res.data.results || []);
      } catch (err) {
        console.error("Party search error:", err);
      } finally {
        setIsSearchingParty(false);
      }
    }, 300);
  };

  const handleSelectParty = (party: any) => {
    setCustomerId(party.id || null);
    setCustomerName(party.name || "");
    if (party.phone) setCustomerPhone(party.phone);
    if (party.state) setCustomerState(party.state);
    if (party.gst_number) setCustomerGstin(party.gst_number);
    if (party.email) setCustomerEmail(party.email);
    if (party.address) setBillingAddress(party.address);

    setSelectedPartyBadge({
      id: party.id,
      name: party.name,
      type: party.type || "VENDOR",
      sub: party.sub,
      phone: party.phone
    });
    setPartySearchResults([]);
  };

  const handleClearParty = () => {
    setCustomerId(null);
    setSelectedPartyBadge(null);
    setPartySearchResults([]);
  };

  const handleAddStockItem = (item: StockItem) => {
    const colorStr = Array.isArray(item.colors) ? item.colors.join(", ") : item.colors || "";
    setLineItems((prev) => [
      ...prev,
      {
        item_id: typeof item.id === "string" ? null : item.id,
        item_description: item.item_name,
        hsn_id: item.hsn_id || null,
        hsn_code: item.hsn_code || "",
        quantity: 1,
        unit_rate: item.selling_rate || item.effective_selling_rate || 0,
        discount_percent: appliedCouponPct > 0 ? appliedCouponPct : 0,
        gst_rate: item.default_gst_rate || item.gst_rate || 18,
        specification: item.specification || "",
        color: colorStr,
        warranty_details: item.warranty_details || "",
        batch_number: "",
        serial_numbers: "",
        is_custom: item._source === "CATALOG"
      }
    ]);
    setIsStockSearchOpen(false);
    setStockSearchQuery("");
  };

  const handleAddCustomLine = () => {
    setLineItems((prev) => [
      ...prev,
      {
        item_id: null,
        item_description: "",
        hsn_id: null,
        hsn_code: "",
        quantity: 1,
        unit_rate: 0,
        discount_percent: appliedCouponPct > 0 ? appliedCouponPct : 0,
        gst_rate: 18,
        specification: "",
        color: "",
        warranty_details: "",
        batch_number: "",
        serial_numbers: "",
        is_custom: true
      }
    ]);
  };

  const handleRemoveLine = (index: number) => {
    setLineItems((prev) => prev.filter((_, i) => i !== index));
  };

  const handleUpdateLine = (index: number, field: keyof LineItemForm, value: any) => {
    setLineItems((prev) => {
      const updated = [...prev];
      updated[index] = { ...updated[index], [field]: value };
      return updated;
    });
  };

  const handleSaveInvoice = async () => {
    if (!selectedCompanyId) {
      toast.error("Please select a company");
      return;
    }
    if (!customerName.trim()) {
      toast.error("Customer name is required");
      return;
    }
    if (!customerPhone.trim()) {
      toast.error("Customer phone number is required");
      return;
    }

    const validLines = lineItems.filter((l) => l.item_description.trim() && l.quantity > 0);
    if (validLines.length === 0) {
      toast.error("Please add at least one valid line item with description and quantity > 0");
      return;
    }

    const payloadLineItems = validLines.map((l) => ({
      item_id: l.item_id,
      item_description: l.item_description.trim(),
      hsn_id: l.hsn_id,
      hsn_code: l.hsn_code.trim() || null,
      quantity: Number(l.quantity),
      unit_rate: Number(l.unit_rate),
      discount_percent: appliedCouponPct > 0 ? appliedCouponPct : Number(l.discount_percent || 0),
      gst_rate: Number(l.gst_rate || 0),
      unit_of_measure: "PCS",
      specification: l.specification.trim() || null,
      color: l.color.trim() || null,
      warranty_details: l.warranty_details.trim() || null,
      batch_number: l.batch_number.trim() || null,
      serial_numbers: l.serial_numbers.trim()
        ? l.serial_numbers
            .split(/[,\n;\r]+/)
            .map((s) => s.trim())
            .filter(Boolean)
        : null
    }));

    const finalShippingAddress = shipSameAsBilling ? billingAddress : shippingAddress;

    const payload: any = {
      company_id: parseInt(selectedCompanyId),
      invoice_date: invoiceDate,
      document_type: docType,
      return_reference: docType === "credit_note" ? creditNoteRef.trim().toUpperCase() || null : null,
      billing_company_id: billingCompanyId ? parseInt(billingCompanyId) : null,
      customer_type: customerType,
      customer_id: customerType === "REGISTERED" ? customerId : null,
      customer_real_type: customerType === "REGISTERED" ? "VENDOR" : "CUSTOMER",
      customer_name: customerName.trim(),
      customer_phone: customerPhone.trim(),
      customer_state: customerState || null,
      customer_gstin: customerGstin.trim().toUpperCase() || null,
      customer_email: customerEmail.trim() || null,
      billing_address: billingAddress.trim() || null,
      shipping_address: finalShippingAddress.trim() || null,
      remarks: invoiceRemarks.trim() || null,
      so_number: soNumber.trim().toUpperCase() || null,
      is_igst: isIgstActive,
      courier_amount: Number(courierAmount || 0),
      courier_hsn_code: courierHsnCode || null,
      courier_hsn_id: courierHsnId || null,
      courier_gst_rate: Number(courierGstRate || 0),
      courier_cgst_amount: invoiceCalculations.courierCgst,
      courier_sgst_amount: invoiceCalculations.courierSgst,
      courier_igst_amount: invoiceCalculations.courierIgst,
      transport_amount: Number(transportAmount || 0),
      transport_hsn_code: transportHsnCode || null,
      transport_hsn_id: transportHsnId || null,
      transport_gst_rate: Number(transportGstRate || 0),
      transport_cgst_amount: invoiceCalculations.transportCgst,
      transport_sgst_amount: invoiceCalculations.transportSgst,
      transport_igst_amount: invoiceCalculations.transportIgst,
      line_items: payloadLineItems
    };

    const isEdit = !!editingInvoiceId;
    const savePromise = isEdit
      ? api.put(`/staff/accounts/sales-invoices/${editingInvoiceId}/line-items`, {
          company_id: payload.company_id,
          line_items: payload.line_items,
          header_data: payload
        })
      : api.post("/staff/accounts/sales-invoices", payload);

    toast.promise(savePromise, {
      loading: isEdit ? "Updating sales invoice..." : "Creating sales invoice...",
      success: (res) => {
        const saved = res.data.invoice || res.data;
        setEditingInvoiceId(saved.id);
        setEditingInvoiceStatus(saved.status);
        loadInvoices();
        loadNarrationHistory(saved.id);
        return isEdit ? "Invoice updated successfully!" : `Draft Invoice ${saved.invoice_number} created!`;
      },
      error: (err) => err.response?.data?.detail || "Failed to save invoice"
    });
  };

  const handleApplyCoupon = async () => {
    if (!editingInvoiceId) {
      toast.error("Please save the invoice as a draft first before applying coupon.");
      return;
    }
    if (!couponCodeInput.trim()) {
      toast.error("Please enter a coupon code");
      return;
    }

    try {
      const res = await api.post(`/staff/accounts/sales-invoices/${editingInvoiceId}/apply-coupon`, {
        company_id: parseInt(selectedCompanyId),
        coupon_code: couponCodeInput.trim().toUpperCase()
      });
      const updated = res.data.invoice;
      setAppliedCouponCode(updated.coupon_code);
      setAppliedCouponPct(updated.coupon_discount_pct);
      toast.success(`Coupon "${updated.coupon_code}" applied (${updated.coupon_discount_pct}% off)!`);
      loadInvoices();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Failed to apply coupon");
    }
  };

  const handleRemoveCoupon = async () => {
    if (!editingInvoiceId) return;
    try {
      await api.delete(`/staff/accounts/sales-invoices/${editingInvoiceId}/coupon?company_id=${selectedCompanyId}`);
      setAppliedCouponCode("");
      setAppliedCouponPct(0);
      setCouponCodeInput("");
      toast.success("Coupon removed");
      loadInvoices();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Failed to remove coupon");
    }
  };

  const handleApplyManualDiscount = async () => {
    if (!editingInvoiceId) {
      toast.error("Please save invoice as draft first");
      return;
    }
    try {
      await api.patch(`/staff/accounts/sales-invoices/${editingInvoiceId}/manual-discount`, {
        company_id: parseInt(selectedCompanyId),
        amount: Number(manualDiscountAmount || 0),
        note: manualDiscountNote.trim() || null
      });
      toast.success("Manual discount updated");
      loadInvoices();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Failed to apply manual discount");
    }
  };

  const loadNarrationHistory = async (invId: number) => {
    setLoadingNarrations(true);
    try {
      const res = await api.get(`/staff/accounts/invoice-narration-log?invoice_type=SALES&invoice_id=${invId}`);
      setNarrations(res.data.entries || []);
    } catch (err) {
      console.error("Error loading narrations:", err);
    } finally {
      setLoadingNarrations(false);
    }
  };

  const handleAddNarrationEntry = async () => {
    if (!editingInvoiceId) {
      toast.error("Please save the invoice first");
      return;
    }
    if (!invoiceRemarks.trim()) {
      toast.error("Type remarks/narration before adding to history");
      return;
    }

    try {
      await api.post("/staff/accounts/invoice-narration-log", {
        invoice_type: "SALES",
        invoice_id: editingInvoiceId,
        company_id: parseInt(selectedCompanyId),
        narration: invoiceRemarks.trim()
      });
      toast.success("Narration logged");
      loadNarrationHistory(editingInvoiceId);
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Failed to add narration log");
    }
  };

  // -------------------------------------------------------------
  // VIEW INVOICE & PDF HANDLING
  // -------------------------------------------------------------
  const handleViewInvoice = async (invId: number, compId?: number) => {
    const cId = compId || selectedCompanyId;
    try {
      const res = await api.get(`/staff/accounts/sales-invoices/${invId}?company_id=${cId}`);
      const inv = res.data.invoice || res.data;
      setViewInvoiceData(inv);
      setViewGstToggle(inv.document_type === "tax_invoice");
      setIsViewModalOpen(true);

      loadInvoicePayments(invId, cId);
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Failed to load invoice details");
    }
  };

  const loadInvoicePayments = async (invId: number, compId?: any) => {
    setLoadingPayments(true);
    try {
      const cId = compId || selectedCompanyId;
      const res = await api.get(`/staff/accounts/sales-invoices/${invId}/payments?company_id=${cId}`);
      setInvoicePayments(res.data.payments || []);
    } catch (err) {
      console.error("Error loading payments:", err);
    } finally {
      setLoadingPayments(false);
    }
  };

  const handleDownloadPdf = async (invId: number, mode: "estimate" | "tax_invoice", invoiceNum?: string) => {
    try {
      const url = `/staff/accounts/sales-invoices/${invId}/pdf?company_id=${selectedCompanyId}&mode=${mode}`;
      const res = await api.get(url, { responseType: "blob" });
      const blob = new Blob([res.data], { type: "application/pdf" });
      const blobUrl = URL.createObjectURL(blob);
      const filename = `${invoiceNum || "INV-" + invId}-${mode === "estimate" ? "estimate" : "tax-invoice"}.pdf`;

      setPdfBlobUrl(blobUrl);
      setPdfViewerTitle(mode === "estimate" ? "Estimate PDF" : "Tax Invoice PDF");
      setPdfViewerFilename(filename);
      setIsPdfViewerOpen(true);
    } catch (err: any) {
      toast.error("Failed to generate PDF document");
    }
  };

  // -------------------------------------------------------------
  // CONFIRM, CANCEL, VOID, DELETE & POST AGAIN
  // -------------------------------------------------------------
  const handleOpenConfirm = (invId: number, status: string, netAmount: number) => {
    setConfirmInvoiceId(invId);
    setConfirmStatus(status);
    setConfirmAmountReceived(0);
    setIsConfirmModalOpen(true);
  };

  const handleSubmitConfirm = async () => {
    if (!confirmInvoiceId || !selectedCompanyId) return;
    setSubmittingConfirm(true);
    try {
      await api.post(`/staff/accounts/sales-invoices/${confirmInvoiceId}/confirm`, {
        company_id: parseInt(selectedCompanyId),
        amount_received: Number(confirmAmountReceived || 0)
      });
      toast.success(
        confirmStatus === "CONFIRMED"
          ? "Invoice re-confirmed! Previous entries reversed and new entries posted."
          : "Invoice confirmed successfully!"
      );
      setIsConfirmModalOpen(false);
      loadInvoices();
      if (isViewModalOpen && viewInvoiceData?.id === confirmInvoiceId) {
        handleViewInvoice(confirmInvoiceId);
      }
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Failed to confirm invoice");
    } finally {
      setSubmittingConfirm(false);
    }
  };

  const handleCancelInvoice = async (invId: number) => {
    const reason = prompt("Enter cancellation reason for DRAFT invoice:");
    if (!reason) return;

    try {
      const res = await api.post(`/staff/accounts/sales-invoices/${invId}/cancel`, {
        reason: reason.trim(),
        company_id: parseInt(selectedCompanyId)
      });
      toast.success(res.data.status === "VOIDED" ? "Invoice voided" : "Invoice cancelled");
      loadInvoices();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Failed to cancel invoice");
    }
  };

  const handleVoidInvoice = async (invId: number, invoiceNum: string) => {
    const reason = prompt(
      `Void invoice ${invoiceNum}?\n\nThis will PERMANENTLY REVERSE all stock movements, AR schedules, and ledger entries.\nEnter void reason:`
    );
    if (!reason || reason.trim().length < 5) {
      if (reason !== null) toast.error("Void reason must be at least 5 characters");
      return;
    }

    if (!confirm(`CONFIRM VOID: ${invoiceNum}\nAre you sure you want to void this confirmed invoice?`)) return;

    try {
      await api.post(`/staff/accounts/sales-invoices/${invId}/cancel`, {
        reason: reason.trim(),
        company_id: parseInt(selectedCompanyId)
      });
      toast.success(`Invoice ${invoiceNum} voided — all entries reversed`);
      loadInvoices();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Failed to void invoice");
    }
  };

  const handlePostAgain = async (invId: number) => {
    if (!confirm("Post Again: This will re-confirm the voided invoice and recreate all stock and ledger entries. Proceed?")) return;
    try {
      await api.post(`/staff/accounts/sales-invoices/${invId}/confirm`, {
        company_id: parseInt(selectedCompanyId)
      });
      toast.success("Invoice re-confirmed and entries recreated!");
      loadInvoices();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Failed to re-confirm invoice");
    }
  };

  const handleDeleteInvoice = async (invId: number, invoiceNum: string) => {
    if (!confirm(`Delete draft invoice ${invoiceNum}? This action cannot be undone.`)) return;
    try {
      await api.delete(`/staff/accounts/sales-invoices/${invId}`);
      toast.success(`Invoice ${invoiceNum} deleted`);
      loadInvoices();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Failed to delete invoice");
    }
  };

  const handleToggleDispatchTracking = async (invId: number, enable: boolean) => {
    try {
      const res = await api.post(`/staff/accounts/sales-invoices/${invId}/toggle-dispatch-tracking`, { enable });
      if (res.data.success) {
        toast.success(enable ? "Added to Pending Dispatch tracking" : "Removed from Pending Dispatch tracking");
        loadInvoices();
      } else {
        toast.error(res.data.detail || "Failed to update tracking");
      }
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Error updating dispatch tracking");
    }
  };

  // -------------------------------------------------------------
  // PAYMENT RECORDING MODAL LOGIC
  // -------------------------------------------------------------
  const handleOpenPaymentModal = (inv: SalesInvoice) => {
    setViewInvoiceData(inv);
    const balance = inv.balance_due ?? Math.max(0, (inv.net_payable || inv.grand_total || 0) - (inv.amount_received || 0));
    setPayAmount(balance > 0 ? String(balance) : "");
    setPayMode("CASH");
    setPayDate(new Date().toISOString().split("T")[0]);
    setPayRef("");
    setPayNotes("");
    setIsPaymentModalOpen(true);
    loadInvoicePayments(inv.id);
  };

  const handleSubmitPayment = async (invId: number) => {
    const numAmt = parseFloat(payAmount);
    if (!numAmt || numAmt <= 0) {
      toast.error("Please enter a valid payment amount");
      return;
    }

    setSubmittingPayment(true);
    try {
      await api.post(`/staff/accounts/sales-invoices/${invId}/payments`, {
        company_id: parseInt(selectedCompanyId),
        amount: numAmt,
        payment_date: payDate,
        payment_mode: payMode,
        reference_number: payRef.trim() || null,
        notes: payNotes.trim() || null
      });
      toast.success("Payment recorded successfully!");
      setPayAmount("");
      setPayRef("");
      setPayNotes("");
      loadInvoicePayments(invId);
      loadInvoices();
      if (viewInvoiceData) {
        handleViewInvoice(invId);
      }
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Failed to record payment");
    } finally {
      setSubmittingPayment(false);
    }
  };

  // -------------------------------------------------------------
  // PENDING DISPATCH LOGIC
  // -------------------------------------------------------------
  const loadPendingDispatches = async () => {
    if (!selectedCompanyId) return;
    setLoadingPending(true);
    try {
      const res = await api.get(`/staff/accounts/sales-invoices/pending-dispatch?company_id=${selectedCompanyId}`);
      setPendingDispatches(res.data.data || []);
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Failed to load pending dispatches");
    } finally {
      setLoadingPending(false);
    }
  };

  const handleSaveLineTarget = async (invId: number, lineId: number, targetQty: number) => {
    try {
      await api.patch(`/staff/accounts/sales-invoices/${invId}/pending-line-config/${lineId}`, {
        pending_qty: targetQty
      });
      toast.success("Target qty updated");
      loadPendingDispatches();
    } catch (err: any) {
      toast.error("Failed to update target qty");
    }
  };

  const handleSaveExtraItemTarget = async (invId: number, extraId: number, targetQty: number) => {
    try {
      await api.patch(`/staff/accounts/sales-invoices/${invId}/pending-extra-items/${extraId}`, {
        pending_qty: targetQty
      });
      toast.success("Extra item target updated");
      loadPendingDispatches();
    } catch (err: any) {
      toast.error("Failed to update extra item target");
    }
  };

  const handleRecordDispatch = async (inv: PendingDispatchInvoice) => {
    const dispatchDate = dispatchFormDates[inv.id] || new Date().toISOString().split("T")[0];
    const narration = dispatchFormNarrs[inv.id] || "";

    const items: any[] = [];
    inv.lines.forEach((ln) => {
      const key = `${inv.id}-${ln.id}`;
      const qty = dispatchFormQtys[key] !== undefined ? dispatchFormQtys[key] : ln.pending_qty;
      if (qty > 0) items.push({ line_id: ln.id, qty_dispatched: qty });
    });

    const extra_item_dispatches: any[] = [];
    (inv.extra_items || []).forEach((ei) => {
      const key = `${inv.id}-ei-${ei.id}`;
      const qty = dispatchFormQtys[key] !== undefined ? dispatchFormQtys[key] : ei.remaining_qty;
      if (qty > 0) extra_item_dispatches.push({ extra_item_id: ei.id, qty_dispatched: qty });
    });

    if (items.length === 0 && extra_item_dispatches.length === 0) {
      toast.error("Please enter quantity to dispatch for at least one item.");
      return;
    }

    try {
      const res = await api.post(`/staff/accounts/sales-invoices/${inv.id}/record-dispatch`, {
        dispatch_date: dispatchDate,
        narration: narration.trim() || null,
        items,
        extra_item_dispatches
      });
      if (res.data.success) {
        toast.success("Dispatch recorded successfully!");
        loadPendingDispatches();
      } else {
        toast.error(res.data.message || "Dispatch failed");
      }
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Failed to record dispatch");
    }
  };

  // Add Pending Modal
  const handleSearchConfirmedForPending = async (q: string) => {
    setAddPendingSearch(q);
    if (!selectedCompanyId) return;
    try {
      const res = await api.get(
        `/staff/accounts/sales-invoices/search-for-pending?company_id=${selectedCompanyId}&q=${encodeURIComponent(q)}`
      );
      setAddPendingInvoices(res.data.invoices || []);
    } catch (err) {
      console.error(err);
    }
  };

  const handleSelectInvoiceForPending = (inv: any) => {
    setSelectedAddPendingInvoice(inv);
    const qtys: Record<number, number> = {};
    (inv.line_items || []).forEach((ln: any) => {
      qtys[ln.id] = ln.quantity;
    });
    setAddPendingLineQtys(qtys);
    setAddPendingExtraItems([]);
  };

  const handleConfirmAddPending = async () => {
    if (!selectedAddPendingInvoice) return;
    const line_overrides: any[] = [];
    Object.entries(addPendingLineQtys).forEach(([lid, pqty]) => {
      line_overrides.push({ line_id: parseInt(lid), pending_qty: pqty });
    });

    try {
      const res = await api.post(
        `/staff/accounts/sales-invoices/${selectedAddPendingInvoice.id}/toggle-dispatch-tracking`,
        {
          enable: true,
          line_overrides,
          extra_items: addPendingExtraItems
        }
      );
      if (res.data.success) {
        toast.success("Invoice added to Pending Dispatch tracking!");
        setIsAddPendingModalOpen(false);
        loadPendingDispatches();
      }
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Failed to add invoice to pending dispatch");
    }
  };

  // -------------------------------------------------------------
  // SUMMARY TAB LOGIC
  // -------------------------------------------------------------
  const loadSummaryData = async () => {
    if (!selectedCompanyId) return;
    setLoadingSummary(true);
    try {
      const res = await api.get(
        `/staff/accounts/pending-dispatch/summary?invoice_type=sales&company_id=${selectedCompanyId}`
      );
      setItemWiseSummary(res.data.item_wise || []);
      setDayWiseSummary(res.data.day_wise || []);
      setCustomerWiseSummary(res.data.party_wise || []);
    } catch (err: any) {
      console.error("Summary error:", err);
    } finally {
      setLoadingSummary(false);
    }
  };

  // -------------------------------------------------------------
  // QUICK CREATE (STOCK ITEM, HSN, PARTNER)
  // -------------------------------------------------------------
  const handleOpenQuickCreate = (type: "stockitem" | "hsn" | "partner") => {
    setQuickCreateType(type);
    setQcCode("");
    setQcName("");
    setQcCategory("FINISHED_GOODS");
    setQcHsnId("");
    setQcUom("PCS");
    setQcPurchaseRate(0);
    setQcMarkupPct(27);
    setQcSaleRate(0);
    setQcDesc("");
    setQcHsnGstRate(18);
    setQcHsnCess(0);
    setIsQuickCreateOpen(true);
  };

  const handleQcCalcSaleRate = (pRate: number, markup: number) => {
    setQcPurchaseRate(pRate);
    setQcMarkupPct(markup);
    if (pRate > 0) {
      setQcSaleRate(Number((pRate * (1 + markup / 100)).toFixed(2)));
    }
  };

  const handleSubmitQuickCreate = async () => {
    if (!selectedCompanyId) {
      toast.error("Please select a company first");
      return;
    }
    setSubmittingQuickCreate(true);
    try {
      if (quickCreateType === "stockitem") {
        if (!qcCode.trim() || !qcName.trim()) {
          toast.error("Item code and name are required");
          return;
        }
        await api.post("/staff/accounts/stock-items", {
          item_code: qcCode.trim().toUpperCase(),
          item_name: qcName.trim(),
          item_category: qcCategory,
          hsn_id: qcHsnId ? parseInt(qcHsnId) : null,
          unit_of_measure: qcUom || "PCS",
          purchase_rate: Number(qcPurchaseRate || 0),
          selling_rate: Number(qcSaleRate || 0),
          description: qcDesc.trim() || null,
          applicable_companies: [parseInt(selectedCompanyId)]
        });
        toast.success("Stock item created successfully!");
        fetchStockItems(true);
      } else if (quickCreateType === "hsn") {
        if (!qcCode.trim() || !qcDesc.trim()) {
          toast.error("HSN code and description are required");
          return;
        }
        await api.post("/staff/accounts/hsn", {
          hsn_code: qcCode.trim(),
          description: qcDesc.trim(),
          cgst_rate: qcHsnGstRate / 2,
          sgst_rate: qcHsnGstRate / 2,
          igst_rate: qcHsnGstRate,
          cess_rate: Number(qcHsnCess || 0),
          effective_from: new Date().toISOString().split("T")[0]
        });
        toast.success("HSN code created successfully!");
        fetchHsnCodes();
      }
      setIsQuickCreateOpen(false);
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Failed to create master record");
    } finally {
      setSubmittingQuickCreate(false);
    }
  };

  // -------------------------------------------------------------
  // COUPON MANAGER LOGIC
  // -------------------------------------------------------------
  const loadCoupons = async () => {
    setLoadingCoupons(true);
    try {
      const res = await api.get("/staff/accounts/sales-coupons");
      setCouponsList(res.data.coupons || []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoadingCoupons(false);
    }
  };

  const handleCreateCoupon = async () => {
    if (!newCouponCode.trim() || !newCouponPct || newCouponPct <= 0 || newCouponPct > 100) {
      toast.error("Please enter a valid coupon code and discount percentage (1-100%)");
      return;
    }
    try {
      await api.post("/staff/accounts/sales-coupons", {
        coupon_code: newCouponCode.trim().toUpperCase(),
        discount_percentage: Number(newCouponPct),
        valid_from: newCouponFrom || null,
        valid_until: newCouponUntil || null,
        max_uses: newCouponMaxUses ? parseInt(newCouponMaxUses) : null,
        description: newCouponDesc.trim() || null
      });
      toast.success("Coupon created successfully!");
      setNewCouponCode("");
      setNewCouponPct(0);
      setNewCouponFrom("");
      setNewCouponUntil("");
      setNewCouponMaxUses("");
      setNewCouponDesc("");
      loadCoupons();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Failed to create coupon");
    }
  };

  const handleDeleteCoupon = async (cid: number) => {
    if (!confirm("Are you sure you want to delete this coupon?")) return;
    try {
      await api.delete(`/staff/accounts/sales-coupons/${cid}`);
      toast.success("Coupon deleted");
      loadCoupons();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Failed to delete coupon");
    }
  };

  // Formatting helpers
  const formatCurrency = (val: any) => {
    return Number(val || 0).toLocaleString("en-IN", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    });
  };

  const formatDate = (dateStr: string) => {
    if (!dateStr) return "—";
    return new Date(dateStr).toLocaleDateString("en-IN", {
      day: "2-digit",
      month: "short",
      year: "numeric"
    });
  };

  return (
    <div className="p-4 sm:p-6 max-w-7xl mx-auto space-y-6 animate-in fade-in duration-300">
      <Toaster position="top-right" />

      {/* Header Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white p-5 rounded-2xl border border-gray-200/80 shadow-sm">
        <div>
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-emerald-50 text-emerald-600 rounded-xl border border-emerald-100">
              <FileText className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-gray-900 tracking-tight flex items-center gap-2">
                Sales Invoices
              </h1>
              <p className="text-xs text-gray-500 font-medium mt-0.5">
                Manage sales orders, tax invoices, GST breakdowns, pending dispatches & payment receipts
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            onClick={() => loadInvoices()}
            className="px-3.5 py-2 text-xs font-semibold text-gray-700 bg-gray-100 hover:bg-gray-200/80 rounded-xl transition-colors flex items-center gap-1.5"
            title="Refresh Invoices"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            Refresh
          </button>

          <button
            onClick={handleOpenCreateModal}
            disabled={!selectedCompanyId}
            className="px-4 py-2 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-700 hover:to-teal-700 text-white rounded-xl text-xs font-bold shadow-sm shadow-emerald-500/20 transition-all flex items-center gap-1.5 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Plus className="w-4 h-4" />
            Create Invoice
          </button>
        </div>
      </div>

      {/* Top Navigation Tabs */}
      <div className="flex items-center gap-1 border-b border-gray-200 pb-px">
        <button
          onClick={() => setActiveTab("invoices")}
          className={`px-4 py-2.5 text-sm font-bold border-b-2 transition-all flex items-center gap-2 ${
            activeTab === "invoices"
              ? "border-emerald-600 text-emerald-700 bg-emerald-50/50 rounded-t-lg"
              : "border-transparent text-gray-500 hover:text-gray-900"
          }`}
        >
          <FileText className="w-4 h-4" />
          Invoices
          <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-gray-100 text-gray-700">
            {stats.total}
          </span>
        </button>

        <button
          onClick={() => {
            setActiveTab("pending");
            loadPendingDispatches();
          }}
          className={`px-4 py-2.5 text-sm font-bold border-b-2 transition-all flex items-center gap-2 ${
            activeTab === "pending"
              ? "border-purple-600 text-purple-700 bg-purple-50/50 rounded-t-lg"
              : "border-transparent text-gray-500 hover:text-gray-900"
          }`}
        >
          <Truck className="w-4 h-4" />
          Pending Dispatch
        </button>

        <button
          onClick={() => {
            setActiveTab("summary");
            loadSummaryData();
          }}
          className={`px-4 py-2.5 text-sm font-bold border-b-2 transition-all flex items-center gap-2 ${
            activeTab === "summary"
              ? "border-blue-600 text-blue-700 bg-blue-50/50 rounded-t-lg"
              : "border-transparent text-gray-500 hover:text-gray-900"
          }`}
        >
          <Layers className="w-4 h-4" />
          Summary
        </button>
      </div>

      {/* ========================================================================= */}
      {/* TAB 1: INVOICES LIST & FILTERS */}
      {/* ========================================================================= */}
      {activeTab === "invoices" && (
        <div className="space-y-5 animate-in fade-in duration-200">
          {/* Main Filter Section */}
          <div className="bg-white p-4 sm:p-5 rounded-2xl border border-gray-200 shadow-sm space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3.5">
              {/* Company Select */}
              <div className="lg:col-span-2">
                <label className="block text-[11px] font-bold uppercase tracking-wider text-emerald-800 mb-1">
                  Company *
                </label>
                <select
                  value={selectedCompanyId}
                  onChange={(e) => setSelectedCompanyId(e.target.value)}
                  className="w-full px-3 py-2 text-xs font-semibold text-gray-900 bg-emerald-50/50 border border-emerald-300 rounded-xl focus:ring-2 focus:ring-emerald-500 outline-none"
                >
                  <option value="">-- Select Company --</option>
                  {companies.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.company_name}
                    </option>
                  ))}
                </select>
              </div>

              {/* Status Filter */}
              <div>
                <label className="block text-[11px] font-bold uppercase tracking-wider text-gray-500 mb-1">
                  Status
                </label>
                <select
                  value={filterStatus}
                  onChange={(e) => setFilterStatus(e.target.value)}
                  className="w-full px-3 py-2 text-xs text-gray-800 bg-white border border-gray-200 rounded-xl focus:ring-2 focus:ring-emerald-500 outline-none"
                >
                  <option value="">All Status</option>
                  <option value="CONFIRMED">Confirmed</option>
                  <option value="DRAFT">Draft</option>
                  <option value="CANCELLED">Cancelled</option>
                  <option value="VOIDED">Deleted (Voided)</option>
                </select>
              </div>

              {/* Customer Type Filter */}
              <div>
                <label className="block text-[11px] font-bold uppercase tracking-wider text-gray-500 mb-1">
                  Customer Type
                </label>
                <select
                  value={filterCustomerType}
                  onChange={(e) => setFilterCustomerType(e.target.value)}
                  className="w-full px-3 py-2 text-xs text-gray-800 bg-white border border-gray-200 rounded-xl focus:ring-2 focus:ring-emerald-500 outline-none"
                >
                  <option value="">All Types</option>
                  <option value="WALK_IN">Walk-In</option>
                  <option value="REGISTERED">Registered</option>
                </select>
              </div>

              {/* From Date */}
              <div>
                <label className="block text-[11px] font-bold uppercase tracking-wider text-gray-500 mb-1">
                  From Date
                </label>
                <input
                  type="date"
                  value={filterFromDate}
                  onChange={(e) => setFilterFromDate(e.target.value)}
                  className="w-full px-3 py-2 text-xs text-gray-800 bg-white border border-gray-200 rounded-xl focus:ring-2 focus:ring-emerald-500 outline-none"
                />
              </div>

              {/* To Date */}
              <div>
                <label className="block text-[11px] font-bold uppercase tracking-wider text-gray-500 mb-1">
                  To Date
                </label>
                <input
                  type="date"
                  value={filterToDate}
                  onChange={(e) => setFilterToDate(e.target.value)}
                  className="w-full px-3 py-2 text-xs text-gray-800 bg-white border border-gray-200 rounded-xl focus:ring-2 focus:ring-emerald-500 outline-none"
                />
              </div>
            </div>

            {/* Quick Period Buttons */}
            <div className="flex items-center gap-1.5 flex-wrap pt-2 border-t border-gray-100">
              <span className="text-[11px] font-bold text-gray-400 uppercase tracking-wider mr-1">Period:</span>
              {[
                { id: "month", label: "This Month" },
                { id: "quarter", label: "This Quarter" },
                { id: "fy", label: "This FY" },
                { id: "overall", label: "Overall" }
              ].map((p) => (
                <button
                  key={p.id}
                  onClick={() => handleSetPeriod(p.id)}
                  className={`px-3 py-1 text-xs font-semibold rounded-lg transition-colors ${
                    activePeriod === p.id
                      ? "bg-blue-600 text-white shadow-sm"
                      : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                  }`}
                >
                  {p.label}
                </button>
              ))}
            </div>
          </div>

          {/* Quick Filter Status Tabs Bar */}
          <div className="flex items-center gap-2 overflow-x-auto pb-1">
            {[
              { status: "", label: "All", count: stats.total, color: "hover:border-blue-500" },
              { status: "CONFIRMED", label: "Confirmed", count: stats.confirmed, color: "text-emerald-700" },
              { status: "DRAFT", label: "Draft", count: stats.draft, color: "text-blue-700" },
              { status: "CANCELLED", label: "Cancelled", count: stats.cancelled, color: "text-rose-700" },
              { status: "VOIDED", label: "Deleted (Voided)", count: stats.voided, color: "text-purple-700" }
            ].map((st) => (
              <button
                key={st.status}
                onClick={() => setFilterStatus(st.status)}
                className={`px-3.5 py-1.5 text-xs font-bold rounded-full border transition-all flex items-center gap-2 whitespace-nowrap ${
                  filterStatus === st.status
                    ? "bg-slate-900 text-white border-slate-900 shadow-sm"
                    : "bg-white text-gray-700 border-gray-200 hover:bg-gray-50"
                }`}
              >
                {st.label}
                <span
                  className={`px-2 py-0.2 rounded-full text-[10px] font-bold ${
                    filterStatus === st.status ? "bg-white/20 text-white" : "bg-gray-100 text-gray-700"
                  }`}
                >
                  {st.count}
                </span>
              </button>
            ))}
          </div>

          {/* KPI Summary Cards */}
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
            <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm">
              <span className="text-[11px] font-bold uppercase text-gray-400 block">Total</span>
              <h3 className="text-xl font-extrabold text-gray-900 mt-1">{stats.total}</h3>
              <p className="text-[10px] text-gray-500 mt-0.5">Invoices</p>
            </div>

            <div className="bg-white p-4 rounded-xl border border-blue-100 shadow-sm">
              <span className="text-[11px] font-bold uppercase text-blue-500 block">Draft</span>
              <h3 className="text-xl font-extrabold text-blue-600 mt-1">{stats.draft}</h3>
              <p className="text-[10px] text-blue-400 mt-0.5">Unconfirmed</p>
            </div>

            <div className="bg-white p-4 rounded-xl border border-emerald-100 shadow-sm">
              <span className="text-[11px] font-bold uppercase text-emerald-600 block">Confirmed</span>
              <h3 className="text-xl font-extrabold text-emerald-600 mt-1">{stats.confirmed}</h3>
              <p className="text-[10px] text-emerald-500 mt-0.5">Active entries</p>
            </div>

            <div className="bg-white p-4 rounded-xl border border-rose-100 shadow-sm">
              <span className="text-[11px] font-bold uppercase text-rose-500 block">Cancelled</span>
              <h3 className="text-xl font-extrabold text-rose-600 mt-1">{stats.cancelled}</h3>
              <p className="text-[10px] text-rose-400 mt-0.5">Draft cancelled</p>
            </div>

            <div className="bg-white p-4 rounded-xl border border-purple-100 shadow-sm">
              <span className="text-[11px] font-bold uppercase text-purple-600 block">Voided</span>
              <h3 className="text-xl font-extrabold text-purple-600 mt-1">{stats.voided}</h3>
              <p className="text-[10px] text-purple-400 mt-0.5">Reversed entries</p>
            </div>

            <div className="bg-gradient-to-br from-emerald-600 to-teal-700 p-4 rounded-xl text-white shadow-sm">
              <span className="text-[11px] font-bold uppercase text-emerald-200 block">Confirmed Value</span>
              <h3 className="text-lg font-black mt-1 font-mono">₹{formatCurrency(stats.confirmedVal)}</h3>
              <p className="text-[10px] text-emerald-100 mt-0.5">Total Revenue</p>
            </div>
          </div>

          {/* Invoices Table Card */}
          <div className="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden">
            <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between flex-wrap gap-2">
              <div className="flex items-center gap-2">
                <FileText className="w-4 h-4 text-emerald-600" />
                <h3 className="text-sm font-bold text-gray-900">Invoices List</h3>
              </div>
              <span className="text-xs font-semibold text-gray-500">{invoices.length} records found</span>
            </div>

            {loadingInvoices ? (
              <div className="p-12 text-center text-gray-500 space-y-3">
                <RefreshCw className="w-7 h-7 text-emerald-600 animate-spin mx-auto" />
                <p className="text-xs font-medium">Loading sales invoices...</p>
              </div>
            ) : invoices.length === 0 ? (
              <div className="p-12 text-center text-gray-400 space-y-3">
                <FileText className="w-12 h-12 text-gray-300 mx-auto" />
                <h4 className="text-base font-bold text-gray-700">No Sales Invoices Found</h4>
                <p className="text-xs text-gray-500 max-w-sm mx-auto">
                  No invoices matched your filters. Click "Create Invoice" above to generate a new invoice.
                </p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse text-xs">
                  <thead>
                    <tr className="bg-gray-50/80 border-b border-gray-200 text-[11px] font-bold text-gray-500 uppercase tracking-wider">
                      <th className="py-3 px-4">Invoice No.</th>
                      <th className="py-3 px-4">Date</th>
                      <th className="py-3 px-4">Customer</th>
                      <th className="py-3 px-4">Doc Type</th>
                      <th className="py-3 px-4">Company</th>
                      <th className="py-3 px-4 text-right">Net Payable</th>
                      <th className="py-3 px-4 text-center">Payment</th>
                      <th className="py-3 px-4 text-center">Status</th>
                      <th className="py-3 px-4 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100 font-medium text-gray-700">
                    {invoices.map((inv) => {
                      const netAmt = (inv.manual_discount_amount && inv.manual_discount_amount > 0)
                        ? inv.net_payable || 0
                        : inv.grand_total || 0;

                      return (
                        <tr key={inv.id} className="hover:bg-emerald-50/30 transition-colors group">
                          {/* Invoice Number & Coupon */}
                          <td className="py-3.5 px-4 font-mono font-bold text-gray-900 whitespace-nowrap">
                            <span>{inv.invoice_number}</span>
                            {inv.coupon_code && (
                              <span className="ml-1.5 px-1.5 py-0.5 text-[9px] font-bold rounded-md bg-amber-100 text-amber-800 border border-amber-200">
                                {inv.coupon_code}
                              </span>
                            )}
                          </td>

                          {/* Date */}
                          <td className="py-3.5 px-4 whitespace-nowrap text-gray-600">{formatDate(inv.invoice_date)}</td>

                          {/* Customer */}
                          <td className="py-3.5 px-4">
                            <div className="font-bold text-gray-900">{inv.customer_name}</div>
                            {inv.customer_phone && <div className="text-[11px] text-gray-500">{inv.customer_phone}</div>}
                          </td>

                          {/* Doc Type Badge */}
                          <td className="py-3.5 px-4 whitespace-nowrap">
                            {inv.document_type === "estimate" ? (
                              <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-blue-100 text-blue-800 border border-blue-200">
                                Estimate
                              </span>
                            ) : inv.document_type === "credit_note" ? (
                              <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-rose-100 text-rose-800 border border-rose-200 flex items-center gap-1 w-fit">
                                <RotateCcw className="w-2.5 h-2.5" />
                                Credit Note
                              </span>
                            ) : (
                              <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-800 border border-emerald-200">
                                Tax Invoice
                              </span>
                            )}
                          </td>

                          {/* Company */}
                          <td className="py-3.5 px-4 text-[11px]">
                            <div className="font-semibold text-gray-900">{inv.company_name || "—"}</div>
                            {inv.billing_company_name && (
                              <div className="text-[10px] text-gray-400">{inv.billing_company_name}</div>
                            )}
                          </td>

                          {/* Net Payable */}
                          <td className="py-3.5 px-4 text-right font-mono font-bold text-gray-900">
                            ₹{formatCurrency(netAmt)}
                          </td>

                          {/* Payment Status Badge */}
                          <td className="py-3.5 px-4 text-center whitespace-nowrap">
                            <span
                              className={`px-2.5 py-0.5 rounded-full text-[10px] font-extrabold ${
                                inv.payment_status === "PAID"
                                  ? "bg-emerald-100 text-emerald-800"
                                  : inv.payment_status === "PARTIAL"
                                  ? "bg-amber-100 text-amber-800"
                                  : "bg-gray-100 text-gray-700"
                              }`}
                            >
                              {inv.payment_status || "PENDING"}
                            </span>
                          </td>

                          {/* Status Badge */}
                          <td className="py-3.5 px-4 text-center whitespace-nowrap">
                            <span
                              className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold ${
                                inv.status === "CONFIRMED"
                                  ? "bg-emerald-100 text-emerald-800 border border-emerald-200"
                                  : inv.status === "DRAFT"
                                  ? "bg-blue-100 text-blue-800 border border-blue-200"
                                  : inv.status === "VOIDED"
                                  ? "bg-purple-100 text-purple-800 border border-purple-200"
                                  : "bg-rose-100 text-rose-800 border border-rose-200"
                              }`}
                            >
                              {inv.status}
                            </span>
                          </td>

                          {/* Actions */}
                          <td className="py-3.5 px-4 text-right whitespace-nowrap">
                            <div className="flex items-center justify-end gap-1">
                              <button
                                onClick={() => handleViewInvoice(inv.id, inv.company_id)}
                                className="p-1.5 text-gray-600 hover:text-emerald-700 hover:bg-emerald-50 rounded-lg transition-colors"
                                title="View Details"
                              >
                                <Eye className="w-3.5 h-3.5" />
                              </button>

                              <button
                                onClick={() => handleDownloadPdf(inv.id, "estimate", inv.invoice_number)}
                                className="px-1.5 py-0.5 text-[10px] font-bold text-blue-700 bg-blue-50 hover:bg-blue-100 rounded border border-blue-200"
                                title="Download Estimate PDF"
                              >
                                E
                              </button>

                              <button
                                onClick={() => handleDownloadPdf(inv.id, "tax_invoice", inv.invoice_number)}
                                className={`px-1.5 py-0.5 text-[10px] font-bold rounded border ${
                                  inv.status === "DRAFT"
                                    ? "text-purple-700 bg-purple-50 hover:bg-purple-100 border-purple-200"
                                    : "text-emerald-700 bg-emerald-50 hover:bg-emerald-100 border-emerald-200"
                                }`}
                                title={inv.status === "DRAFT" ? "Download Proforma (PI) PDF" : "Download Tax Invoice PDF"}
                              >
                                {inv.status === "DRAFT" ? "PI" : "T"}
                              </button>

                              {inv.status === "DRAFT" && (
                                <>
                                  <button
                                    onClick={() => handleOpenEditModal(inv.id, false)}
                                    className="p-1.5 text-amber-700 hover:bg-amber-50 rounded-lg"
                                    title="Edit Draft"
                                  >
                                    <Edit className="w-3.5 h-3.5" />
                                  </button>
                                  <button
                                    onClick={() => handleOpenConfirm(inv.id, inv.status, netAmt)}
                                    className="p-1.5 text-emerald-700 hover:bg-emerald-50 rounded-lg font-bold"
                                    title="Confirm Invoice"
                                  >
                                    <CheckCircle className="w-3.5 h-3.5" />
                                  </button>
                                  <button
                                    onClick={() => handleCancelInvoice(inv.id)}
                                    className="p-1.5 text-rose-700 hover:bg-rose-50 rounded-lg"
                                    title="Cancel Invoice"
                                  >
                                    <XCircle className="w-3.5 h-3.5" />
                                  </button>
                                  {canDelete && (
                                    <button
                                      onClick={() => handleDeleteInvoice(inv.id, inv.invoice_number)}
                                      className="p-1.5 text-rose-600 hover:bg-rose-50 rounded-lg"
                                      title="Delete Invoice"
                                    >
                                      <Trash2 className="w-3.5 h-3.5" />
                                    </button>
                                  )}
                                </>
                              )}

                              {inv.status === "CONFIRMED" && (
                                <>
                                  <button
                                    onClick={() => handleOpenEditModal(inv.id, true)}
                                    className="p-1.5 text-amber-700 hover:bg-amber-50 rounded-lg"
                                    title="Edit Confirmed Invoice"
                                  >
                                    <Edit className="w-3.5 h-3.5" />
                                  </button>
                                  <button
                                    onClick={() => handleOpenConfirm(inv.id, inv.status, netAmt)}
                                    className="p-1.5 text-emerald-700 hover:bg-emerald-50 rounded-lg"
                                    title="Re-confirm Invoice"
                                  >
                                    <RotateCcw className="w-3.5 h-3.5" />
                                  </button>
                                  <button
                                    onClick={() => handleOpenPaymentModal(inv)}
                                    className="px-2 py-1 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-[10px] font-bold shadow-xs flex items-center gap-0.5"
                                    title="Record Payment"
                                  >
                                    <DollarSign className="w-3 h-3" />
                                    Pay
                                  </button>
                                  <button
                                    onClick={() => handleToggleDispatchTracking(inv.id, !inv.track_physical_dispatch)}
                                    className={`px-2 py-1 rounded-lg text-[10px] font-bold transition-colors flex items-center gap-1 ${
                                      inv.track_physical_dispatch
                                        ? "bg-purple-600 text-white shadow-xs"
                                        : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                                    }`}
                                    title={inv.track_physical_dispatch ? "Disable dispatch tracking" : "Enable dispatch tracking"}
                                  >
                                    <Truck className="w-3 h-3" />
                                    {inv.track_physical_dispatch ? "Tracking" : "Track"}
                                  </button>
                                  {canDelete && (
                                    <button
                                      onClick={() => handleVoidInvoice(inv.id, inv.invoice_number)}
                                      className="px-2 py-1 bg-rose-100 hover:bg-rose-200 text-rose-800 rounded-lg text-[10px] font-bold flex items-center gap-0.5"
                                      title="Void Invoice"
                                    >
                                      <Ban className="w-3 h-3" />
                                      Void
                                    </button>
                                  )}
                                </>
                              )}

                              {inv.status === "VOIDED" && (
                                <button
                                  onClick={() => handlePostAgain(inv.id)}
                                  className="px-2 py-1 bg-emerald-100 hover:bg-emerald-200 text-emerald-800 rounded-lg text-[10px] font-bold flex items-center gap-1"
                                  title="Post Again"
                                >
                                  <RotateCcw className="w-3 h-3" />
                                  Post Again
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
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* TAB 2: PENDING DISPATCH */}
      {/* ========================================================================= */}
      {activeTab === "pending" && (
        <div className="space-y-5 animate-in fade-in duration-200">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white p-4 sm:p-5 rounded-2xl border border-gray-200 shadow-sm">
            <div>
              <h3 className="text-base font-bold text-gray-900 flex items-center gap-2">
                <Truck className="w-5 h-5 text-purple-600" />
                Pending Physical Dispatch
              </h3>
              <p className="text-xs text-gray-500 mt-0.5">
                Confirmed sales invoices with items awaiting physical dispatch to customers
              </p>
            </div>

            <div className="flex items-center gap-2.5 flex-wrap">
              <select
                value={selectedCompanyId}
                onChange={(e) => setSelectedCompanyId(e.target.value)}
                className="px-3 py-2 text-xs font-semibold bg-gray-50 border border-gray-200 rounded-xl outline-none"
              >
                <option value="">-- All Companies --</option>
                {companies.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.company_name}
                  </option>
                ))}
              </select>

              <button
                onClick={() => {
                  setIsAddPendingModalOpen(true);
                  handleSearchConfirmedForPending("");
                }}
                className="px-3.5 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-bold shadow-sm flex items-center gap-1.5"
              >
                <Plus className="w-3.5 h-3.5" />
                Add Pending Invoice
              </button>

              <button
                onClick={loadPendingDispatches}
                className="px-3.5 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-xl text-xs font-bold shadow-sm flex items-center gap-1.5"
              >
                <RefreshCw className="w-3.5 h-3.5" />
                Refresh
              </button>
            </div>
          </div>

          {loadingPending ? (
            <div className="p-12 text-center text-gray-500 space-y-3 bg-white rounded-2xl border border-gray-200">
              <RefreshCw className="w-7 h-7 text-purple-600 animate-spin mx-auto" />
              <p className="text-xs font-medium">Loading pending dispatches...</p>
            </div>
          ) : pendingDispatches.length === 0 ? (
            <div className="p-12 text-center text-gray-400 space-y-3 bg-white rounded-2xl border border-gray-200">
              <CheckCircle className="w-12 h-12 text-emerald-500 mx-auto" />
              <h4 className="text-base font-bold text-gray-800">All Dispatches Completed!</h4>
              <p className="text-xs text-gray-500 max-w-sm mx-auto">
                There are no pending items for dispatch. Click "Add Pending Invoice" above to track an invoice.
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {pendingDispatches.map((inv) => {
                const isOpen = expandedPendingCard === inv.id;
                const dsClass =
                  inv.dispatch_status === "NOT_DISPATCHED"
                    ? "bg-rose-100 text-rose-800 border-rose-200"
                    : inv.dispatch_status === "PARTIALLY_DISPATCHED"
                    ? "bg-amber-100 text-amber-800 border-amber-200"
                    : "bg-emerald-100 text-emerald-800 border-emerald-200";

                return (
                  <div
                    key={inv.id}
                    className="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden transition-all"
                  >
                    {/* Header */}
                    <div
                      onClick={() => setExpandedPendingCard(isOpen ? null : inv.id)}
                      className="p-4 bg-gray-50/70 hover:bg-gray-100/70 transition-colors flex items-center justify-between cursor-pointer flex-wrap gap-2"
                    >
                      <div className="flex items-center gap-3">
                        <span className="font-mono font-bold text-sm text-gray-900">{inv.invoice_number}</span>
                        <span className="text-xs font-semibold text-gray-700">{inv.customer_name}</span>
                        <span className="text-[11px] text-gray-500">{formatDate(inv.invoice_date)}</span>
                      </div>

                      <div className="flex items-center gap-2.5">
                        <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold border ${dsClass}`}>
                          {inv.dispatch_status.replace(/_/g, " ")}
                        </span>
                        <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-amber-50 text-amber-800 border border-amber-200">
                          {inv.total_pending_qty} units · ₹{formatCurrency(inv.total_pending_value)}
                        </span>
                        {inv.extra_items && inv.extra_items.length > 0 && (
                          <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-blue-50 text-blue-700 border border-blue-200">
                            +{inv.extra_items.length} extra
                          </span>
                        )}
                        {isOpen ? <ChevronUp className="w-4 h-4 text-gray-400" /> : <ChevronDown className="w-4 h-4 text-gray-400" />}
                      </div>
                    </div>

                    {/* Card Content */}
                    {isOpen && (
                      <div className="p-5 border-t border-gray-100 space-y-4">
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                          <div>
                            <label className="block text-[11px] font-bold text-gray-500 uppercase tracking-wider mb-1">
                              Dispatch Date *
                            </label>
                            <input
                              type="date"
                              value={dispatchFormDates[inv.id] || new Date().toISOString().split("T")[0]}
                              onChange={(e) =>
                                setDispatchFormDates((prev) => ({ ...prev, [inv.id]: e.target.value }))
                              }
                              className="w-full px-3 py-2 text-xs border border-gray-200 rounded-xl focus:ring-2 focus:ring-purple-500 outline-none"
                            />
                          </div>

                          <div>
                            <label className="block text-[11px] font-bold text-gray-500 uppercase tracking-wider mb-1">
                              Courier / Tracking Narration
                            </label>
                            <input
                              type="text"
                              placeholder="e.g. DTDC AWB #123456"
                              value={dispatchFormNarrs[inv.id] || ""}
                              onChange={(e) =>
                                setDispatchFormNarrs((prev) => ({ ...prev, [inv.id]: e.target.value }))
                              }
                              className="w-full px-3 py-2 text-xs border border-gray-200 rounded-xl focus:ring-2 focus:ring-purple-500 outline-none"
                            />
                          </div>
                        </div>

                        {/* Dispatch Items Table */}
                        <div className="border border-gray-200 rounded-xl overflow-hidden">
                          <table className="w-full text-left border-collapse text-xs">
                            <thead>
                              <tr className="bg-gray-50 text-[11px] font-bold text-gray-500 uppercase border-b border-gray-200">
                                <th className="p-2.5">#</th>
                                <th className="p-2.5">Item</th>
                                <th className="p-2.5">UOM</th>
                                <th className="p-2.5 text-right">Invoiced</th>
                                <th className="p-2.5 text-right">Target</th>
                                <th className="p-2.5 text-right">Dispatched</th>
                                <th className="p-2.5 text-right">Remaining</th>
                                <th className="p-2.5 text-center">Dispatch Now</th>
                              </tr>
                            </thead>
                            <tbody className="divide-y divide-gray-100 font-medium">
                              {inv.lines.map((ln) => {
                                const key = `${inv.id}-${ln.id}`;
                                const nowVal = dispatchFormQtys[key] !== undefined ? dispatchFormQtys[key] : ln.pending_qty;

                                return (
                                  <tr key={ln.id} className="hover:bg-gray-50/50">
                                    <td className="p-2.5 text-gray-400">{ln.line_number}</td>
                                    <td className="p-2.5">
                                      <div className="font-bold text-gray-900">{ln.item_description}</div>
                                      {ln.item_code && <div className="text-[10px] text-gray-400">{ln.item_code}</div>}
                                    </td>
                                    <td className="p-2.5 text-gray-500">{ln.unit_of_measure}</td>
                                    <td className="p-2.5 text-right font-mono">{ln.invoiced_qty}</td>
                                    <td className="p-2.5 text-right">
                                      <input
                                        type="number"
                                        defaultValue={ln.configured_pending_qty}
                                        onBlur={(e) => handleSaveLineTarget(inv.id, ln.id, parseFloat(e.target.value) || 0)}
                                        className="w-16 px-1.5 py-0.5 text-xs text-right border border-amber-200 bg-amber-50/50 rounded"
                                        title="Configure pending target qty"
                                      />
                                    </td>
                                    <td className="p-2.5 text-right text-emerald-700 font-mono">{ln.dispatched_qty}</td>
                                    <td className="p-2.5 text-right font-bold text-amber-700 font-mono">{ln.pending_qty}</td>
                                    <td className="p-2.5 text-center">
                                      <input
                                        type="number"
                                        min={0}
                                        max={ln.pending_qty}
                                        step={0.01}
                                        value={nowVal}
                                        onChange={(e) =>
                                          setDispatchFormQtys((prev) => ({
                                            ...prev,
                                            [key]: parseFloat(e.target.value) || 0
                                          }))
                                        }
                                        className="w-20 px-2 py-1 text-xs text-center border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500"
                                      />
                                    </td>
                                  </tr>
                                );
                              })}

                              {/* Extra Items */}
                              {(inv.extra_items || []).map((ei) => {
                                const key = `${inv.id}-ei-${ei.id}`;
                                const nowVal = dispatchFormQtys[key] !== undefined ? dispatchFormQtys[key] : ei.remaining_qty;

                                return (
                                  <tr key={`ei-${ei.id}`} className="bg-amber-50/40">
                                    <td className="p-2.5 text-amber-600 font-bold">➕</td>
                                    <td className="p-2.5">
                                      <div className="font-bold text-gray-900">{ei.item_description}</div>
                                      <div className="text-[10px] text-amber-800 font-semibold">Extra Free-Issue / Bundle Item</div>
                                    </td>
                                    <td className="p-2.5 text-gray-500">{ei.unit_of_measure}</td>
                                    <td className="p-2.5 text-right text-gray-400">—</td>
                                    <td className="p-2.5 text-right">
                                      <input
                                        type="number"
                                        defaultValue={ei.pending_qty}
                                        onBlur={(e) => handleSaveExtraItemTarget(inv.id, ei.id, parseFloat(e.target.value) || 0)}
                                        className="w-16 px-1.5 py-0.5 text-xs text-right border border-amber-200 bg-amber-50 rounded"
                                      />
                                    </td>
                                    <td className="p-2.5 text-right text-emerald-700 font-mono">{ei.dispatched_qty}</td>
                                    <td className="p-2.5 text-right font-bold text-amber-700 font-mono">{ei.remaining_qty}</td>
                                    <td className="p-2.5 text-center">
                                      <input
                                        type="number"
                                        min={0}
                                        max={ei.remaining_qty}
                                        step={0.01}
                                        value={nowVal}
                                        onChange={(e) =>
                                          setDispatchFormQtys((prev) => ({
                                            ...prev,
                                            [key]: parseFloat(e.target.value) || 0
                                          }))
                                        }
                                        className="w-20 px-2 py-1 text-xs text-center border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500"
                                      />
                                    </td>
                                  </tr>
                                );
                              })}
                            </tbody>
                          </table>
                        </div>

                        <div className="flex justify-end pt-2">
                          <button
                            onClick={() => handleRecordDispatch(inv)}
                            className="px-5 py-2.5 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-700 hover:to-indigo-700 text-white rounded-xl text-xs font-bold shadow-sm flex items-center gap-2"
                          >
                            <Truck className="w-4 h-4" />
                            Record Dispatch
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* ========================================================================= */}
      {/* TAB 3: SUMMARY & BREAKDOWN */}
      {/* ========================================================================= */}
      {activeTab === "summary" && (
        <div className="space-y-5 animate-in fade-in duration-200">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white p-4 sm:p-5 rounded-2xl border border-gray-200 shadow-sm">
            <div>
              <h3 className="text-base font-bold text-gray-900 flex items-center gap-2">
                <Layers className="w-5 h-5 text-blue-600" />
                Pending Dispatch Summary
              </h3>
              <p className="text-xs text-gray-500 mt-0.5">
                Item-wise, day-wise and customer-wise breakdown of active pending dispatches
              </p>
            </div>

            <div className="flex items-center gap-2.5">
              <select
                value={selectedCompanyId}
                onChange={(e) => setSelectedCompanyId(e.target.value)}
                className="px-3 py-2 text-xs font-semibold bg-gray-50 border border-gray-200 rounded-xl outline-none"
              >
                <option value="">-- Select Company --</option>
                {companies.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.company_name}
                  </option>
                ))}
              </select>

              <button
                onClick={loadSummaryData}
                className="px-3.5 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-xs font-bold shadow-sm flex items-center gap-1.5"
              >
                <RefreshCw className="w-3.5 h-3.5" />
                Refresh
              </button>
            </div>
          </div>

          {/* Sub Tabs */}
          <div className="flex items-center gap-2">
            {[
              { id: "item", label: "Item-wise", icon: Package },
              { id: "day", label: "Day-wise", icon: Calendar },
              { id: "customer", label: "Customer-wise", icon: User }
            ].map((sub) => {
              const Icon = sub.icon;
              return (
                <button
                  key={sub.id}
                  onClick={() => setSummarySubTab(sub.id as any)}
                  className={`px-4 py-2 text-xs font-bold rounded-xl border transition-all flex items-center gap-1.5 ${
                    summarySubTab === sub.id
                      ? "bg-slate-900 text-white border-slate-900 shadow-sm"
                      : "bg-white text-gray-700 border-gray-200 hover:bg-gray-50"
                  }`}
                >
                  <Icon className="w-3.5 h-3.5" />
                  {sub.label}
                </button>
              );
            })}
          </div>

          {/* Summary Table Card */}
          <div className="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden">
            {loadingSummary ? (
              <div className="p-12 text-center text-gray-500 space-y-3">
                <RefreshCw className="w-7 h-7 text-blue-600 animate-spin mx-auto" />
                <p className="text-xs font-medium">Loading summary data...</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                {summarySubTab === "item" && (
                  <table className="w-full text-left border-collapse text-xs">
                    <thead>
                      <tr className="bg-gray-50 text-[11px] font-bold text-gray-500 uppercase border-b border-gray-200">
                        <th className="p-3.5">Item Name</th>
                        <th className="p-3.5 text-right">Pending Qty</th>
                        <th className="p-3.5 text-right">Pending Value (₹)</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100 font-medium text-gray-700">
                      {itemWiseSummary.length === 0 ? (
                        <tr>
                          <td colSpan={3} className="p-8 text-center text-gray-400">
                            No pending item summary found.
                          </td>
                        </tr>
                      ) : (
                        itemWiseSummary.map((r, i) => (
                          <tr key={i} className="hover:bg-gray-50">
                            <td className="p-3.5 font-bold text-gray-900">{r.item}</td>
                            <td className="p-3.5 text-right font-mono font-semibold text-amber-700">{r.pending_qty}</td>
                            <td className="p-3.5 text-right font-mono font-bold text-gray-900">
                              ₹{formatCurrency(r.pending_value)}
                            </td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                )}

                {summarySubTab === "day" && (
                  <table className="w-full text-left border-collapse text-xs">
                    <thead>
                      <tr className="bg-gray-50 text-[11px] font-bold text-gray-500 uppercase border-b border-gray-200">
                        <th className="p-3.5">Date</th>
                        <th className="p-3.5 text-center">Invoices Count</th>
                        <th className="p-3.5 text-right">Pending Value (₹)</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100 font-medium text-gray-700">
                      {dayWiseSummary.length === 0 ? (
                        <tr>
                          <td colSpan={3} className="p-8 text-center text-gray-400">
                            No pending day-wise summary found.
                          </td>
                        </tr>
                      ) : (
                        dayWiseSummary.map((r, i) => (
                          <tr key={i} className="hover:bg-gray-50">
                            <td className="p-3.5 font-bold text-gray-900">{r.date}</td>
                            <td className="p-3.5 text-center font-semibold text-blue-700">{r.invoice_count}</td>
                            <td className="p-3.5 text-right font-mono font-bold text-gray-900">
                              ₹{formatCurrency(r.pending_value)}
                            </td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                )}

                {summarySubTab === "customer" && (
                  <table className="w-full text-left border-collapse text-xs">
                    <thead>
                      <tr className="bg-gray-50 text-[11px] font-bold text-gray-500 uppercase border-b border-gray-200">
                        <th className="p-3.5">Customer Name</th>
                        <th className="p-3.5 text-right">Pending Qty</th>
                        <th className="p-3.5 text-right">Pending Value (₹)</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100 font-medium text-gray-700">
                      {customerWiseSummary.length === 0 ? (
                        <tr>
                          <td colSpan={3} className="p-8 text-center text-gray-400">
                            No pending customer summary found.
                          </td>
                        </tr>
                      ) : (
                        customerWiseSummary.map((r, i) => (
                          <tr key={i} className="hover:bg-gray-50">
                            <td className="p-3.5 font-bold text-gray-900">{r.party}</td>
                            <td className="p-3.5 text-right font-mono font-semibold text-amber-700">{r.pending_qty}</td>
                            <td className="p-3.5 text-right font-mono font-bold text-gray-900">
                              ₹{formatCurrency(r.pending_value)}
                            </td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* MODAL 1: CREATE / EDIT SALES INVOICE MODAL (FULL WORKFLOW) */}
      {/* ========================================================================= */}
      {isCreateModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-2 sm:p-4 overflow-y-auto animate-in fade-in duration-200">
          <div className="bg-white w-full max-w-5xl rounded-2xl shadow-2xl border border-gray-200 flex flex-col max-h-[92vh] overflow-hidden my-auto">
            {/* Modal Header */}
            <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between bg-gray-50/80">
              <div className="flex items-center gap-2.5">
                <div className="p-2 bg-emerald-100 text-emerald-700 rounded-xl">
                  <FileText className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-gray-900">
                    {editingInvoiceId ? `Edit Sales Invoice (ID: #${editingInvoiceId})` : "Create Sales Invoice"}
                  </h3>
                  <p className="text-xs text-gray-500">
                    Company-linked GST calculation, HSN live auto-fill, catalog integration & discounts
                  </p>
                </div>
              </div>
              <button
                onClick={() => setIsCreateModalOpen(false)}
                className="p-2 text-gray-400 hover:text-gray-700 rounded-xl hover:bg-gray-100 transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-6 overflow-y-auto space-y-6 flex-1 text-xs">
              {/* Document Type Selector Bar */}
              <div className="p-3.5 bg-slate-50 border border-slate-200 rounded-xl flex items-center justify-between flex-wrap gap-3">
                <div className="flex items-center gap-4">
                  <span className="font-bold text-gray-700 uppercase tracking-wider text-[11px]">Doc Type:</span>

                  <label className="flex items-center gap-1.5 font-semibold text-gray-800 cursor-pointer">
                    <input
                      type="radio"
                      name="docType"
                      value="tax_invoice"
                      checked={docType === "tax_invoice"}
                      onChange={() => setDocType("tax_invoice")}
                      className="text-emerald-600 focus:ring-emerald-500"
                    />
                    <FileText className="w-3.5 h-3.5 text-emerald-600" />
                    Tax Invoice
                  </label>

                  <label className="flex items-center gap-1.5 font-semibold text-gray-800 cursor-pointer">
                    <input
                      type="radio"
                      name="docType"
                      value="estimate"
                      checked={docType === "estimate"}
                      onChange={() => setDocType("estimate")}
                      className="text-blue-600 focus:ring-blue-500"
                    />
                    <FileCheck className="w-3.5 h-3.5 text-blue-600" />
                    Estimate
                  </label>

                  <label className="flex items-center gap-1.5 font-semibold text-rose-700 cursor-pointer">
                    <input
                      type="radio"
                      name="docType"
                      value="credit_note"
                      checked={docType === "credit_note"}
                      onChange={() => setDocType("credit_note")}
                      className="text-rose-600 focus:ring-rose-500"
                    />
                    <RotateCcw className="w-3.5 h-3.5 text-rose-600" />
                    Credit Note (Sales Return)
                  </label>
                </div>

                <span
                  className={`px-3 py-1 rounded-full text-[10px] font-extrabold tracking-wider ${
                    docType === "tax_invoice"
                      ? "bg-emerald-100 text-emerald-800 border border-emerald-300"
                      : docType === "estimate"
                      ? "bg-blue-100 text-blue-800 border border-blue-300"
                      : "bg-rose-100 text-rose-800 border border-rose-300"
                  }`}
                >
                  {docType.replace(/_/g, " ").toUpperCase()}
                </span>
              </div>

              {/* Credit Note Reference field */}
              {docType === "credit_note" && (
                <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl space-y-1">
                  <label className="block text-[11px] font-bold text-rose-800 uppercase">
                    Original Invoice Number (Reference — optional)
                  </label>
                  <input
                    type="text"
                    placeholder="e.g. SI-2026-001"
                    value={creditNoteRef}
                    onChange={(e) => setCreditNoteRef(e.target.value)}
                    className="w-full px-3 py-2 text-xs border border-rose-300 rounded-lg uppercase font-mono font-bold text-rose-900 bg-white"
                  />
                </div>
              )}

              {/* Header Fields */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div>
                  <label className="block font-bold text-gray-700 mb-1">Billing Company (for PDF)</label>
                  <select
                    value={billingCompanyId}
                    onChange={(e) => setBillingCompanyId(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-200 rounded-xl bg-white focus:ring-2 focus:ring-emerald-500 outline-none"
                  >
                    <option value="">-- Same as seller company --</option>
                    {billingCompanies.map((b) => (
                      <option key={b.id} value={b.id}>
                        {b.name}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block font-bold text-gray-700 mb-1">Invoice Date *</label>
                  <input
                    type="date"
                    value={invoiceDate}
                    onChange={(e) => setInvoiceDate(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-200 rounded-xl bg-white focus:ring-2 focus:ring-emerald-500 outline-none"
                    required
                  />
                </div>

                <div>
                  <label className="block font-bold text-gray-700 mb-1">
                    S.O. No. <span className="text-[10px] text-gray-400 font-normal">(Sales Order)</span>
                  </label>
                  <input
                    type="text"
                    placeholder="e.g. SO-2026-001"
                    value={soNumber}
                    onChange={(e) => setSoNumber(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-200 rounded-xl bg-white uppercase font-mono"
                  />
                </div>
              </div>

              {/* Customer Details Box */}
              <div className="p-4 sm:p-5 bg-blue-50/40 border border-blue-200/80 rounded-2xl space-y-4">
                <div className="flex items-center justify-between">
                  <h4 className="font-bold text-blue-900 text-sm flex items-center gap-1.5">
                    <User className="w-4 h-4 text-blue-600" />
                    Customer Details
                  </h4>
                  {selectedPartyBadge && (
                    <div className="flex items-center gap-2 bg-white px-2.5 py-1 rounded-lg border border-blue-200 shadow-2xs">
                      <span className="text-[10px] font-bold text-blue-800">
                        {selectedPartyBadge.name} ({selectedPartyBadge.type})
                      </span>
                      <button
                        onClick={handleClearParty}
                        className="text-rose-600 hover:text-rose-800 text-xs font-bold"
                        title="Clear party"
                      >
                        ✕
                      </button>
                    </div>
                  )}
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                  <div>
                    <label className="block font-bold text-gray-700 mb-1">Customer Type *</label>
                    <select
                      value={customerType}
                      onChange={(e) => {
                        setCustomerType(e.target.value as any);
                        if (e.target.value !== "REGISTERED") handleClearParty();
                      }}
                      className="w-full px-3 py-2 border border-gray-200 rounded-xl bg-white focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="WALK_IN">Walk-In</option>
                      <option value="REGISTERED">Registered Party / Dealer</option>
                    </select>
                  </div>

                  <div className="relative">
                    <label className="block font-bold text-gray-700 mb-1">Customer Name *</label>
                    <input
                      type="text"
                      placeholder={customerType === "REGISTERED" ? "Type to search registered party..." : "Full Customer Name"}
                      value={customerName}
                      onChange={(e) => handlePartySearch(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-200 rounded-xl bg-white focus:ring-2 focus:ring-blue-500"
                      required
                    />

                    {partySearchResults.length > 0 && (
                      <div className="absolute top-full left-0 right-0 z-30 mt-1 bg-white border border-blue-200 rounded-xl shadow-xl max-h-56 overflow-y-auto divide-y divide-gray-100">
                        {partySearchResults.map((p) => (
                          <div
                            key={p.id}
                            onClick={() => handleSelectParty(p)}
                            className="p-2.5 hover:bg-blue-50 cursor-pointer flex items-center justify-between"
                          >
                            <div>
                              <div className="font-bold text-gray-900">{p.name}</div>
                              <div className="text-[10px] text-gray-500 flex items-center gap-1.5 mt-0.5">
                                <span className={`px-1.5 py-0.2 rounded font-bold ${PARTY_TYPE_COLORS[p.type] || "bg-gray-100 text-gray-700"}`}>
                                  {p.type}
                                </span>
                                {p.sub && <span>· {p.sub}</span>}
                                {p.phone && <span>· {p.phone}</span>}
                              </div>
                            </div>
                            <span className="text-[11px] font-mono text-gray-500">{p.phone}</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>

                  <div>
                    <label className="block font-bold text-gray-700 mb-1">Phone Number *</label>
                    <input
                      type="tel"
                      placeholder="10-digit mobile number"
                      value={customerPhone}
                      onChange={(e) => setCustomerPhone(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-200 rounded-xl bg-white"
                      required
                    />
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                  <div>
                    <label className="block font-bold text-gray-700 mb-1">State</label>
                    <select
                      value={customerState}
                      onChange={(e) => setCustomerState(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-200 rounded-xl bg-white"
                    >
                      <option value="">-- Select State --</option>
                      {INDIAN_STATES.map((st) => (
                        <option key={st} value={st}>
                          {st}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="block font-bold text-gray-700 mb-1">GSTIN (if registered)</label>
                    <input
                      type="text"
                      placeholder="15-digit GSTIN"
                      value={customerGstin}
                      onChange={(e) => setCustomerGstin(e.target.value.toUpperCase())}
                      className="w-full px-3 py-2 border border-gray-200 rounded-xl bg-white font-mono"
                    />
                  </div>

                  <div>
                    <label className="block font-bold text-gray-700 mb-1">Email</label>
                    <input
                      type="email"
                      placeholder="Email address"
                      value={customerEmail}
                      onChange={(e) => setCustomerEmail(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-200 rounded-xl bg-white"
                    />
                  </div>
                </div>

                {/* GST Override Toggle Bar */}
                <div className="p-3 bg-white border border-blue-200 rounded-xl flex items-center justify-between flex-wrap gap-2">
                  <div className="flex items-center gap-3">
                    <span className="font-bold text-gray-700 text-[11px] uppercase tracking-wider">GST Type:</span>
                    <label className="flex items-center gap-1 cursor-pointer">
                      <input
                        type="radio"
                        name="gstOverride"
                        value="auto"
                        checked={gstTypeOverride === "auto"}
                        onChange={() => setGstTypeOverride("auto")}
                      />
                      <span>Auto-detect</span>
                    </label>
                    <span className="text-gray-300">|</span>
                    <label className="flex items-center gap-1 cursor-pointer font-bold text-blue-700">
                      <input
                        type="radio"
                        name="gstOverride"
                        value="igst"
                        checked={gstTypeOverride === "igst"}
                        onChange={() => setGstTypeOverride("igst")}
                      />
                      <span>IGST (Inter-state)</span>
                    </label>
                    <span className="text-gray-300">|</span>
                    <label className="flex items-center gap-1 cursor-pointer font-bold text-emerald-700">
                      <input
                        type="radio"
                        name="gstOverride"
                        value="cgst_sgst"
                        checked={gstTypeOverride === "cgst_sgst"}
                        onChange={() => setGstTypeOverride("cgst_sgst")}
                      />
                      <span>CGST+SGST (Intra-state)</span>
                    </label>
                  </div>

                  <span className="text-[11px] font-semibold text-gray-500 italic">
                    {isIgstActive ? "→ IGST (Inter-state calculation)" : "→ CGST + SGST (Intra-state calculation)"}
                  </span>
                </div>

                {/* Addresses */}
                <div className="space-y-3">
                  <div>
                    <label className="block font-bold text-gray-700 mb-1">Billing Address</label>
                    <textarea
                      rows={2}
                      placeholder="Billing / postal address"
                      value={billingAddress}
                      onChange={(e) => setBillingAddress(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-200 rounded-xl bg-white"
                    />
                  </div>

                  <div className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      id="sameShip"
                      checked={shipSameAsBilling}
                      onChange={(e) => setShipSameAsBilling(e.target.checked)}
                      className="rounded text-emerald-600"
                    />
                    <label htmlFor="sameShip" className="font-semibold text-gray-700 cursor-pointer">
                      Ship to same as billing address
                    </label>
                  </div>

                  {!shipSameAsBilling && (
                    <div>
                      <label className="block font-bold text-gray-700 mb-1">Shipping Address</label>
                      <textarea
                        rows={2}
                        placeholder="Shipping address if different from billing"
                        value={shippingAddress}
                        onChange={(e) => setShippingAddress(e.target.value)}
                        className="w-full px-3 py-2 border border-gray-200 rounded-xl bg-white"
                      />
                    </div>
                  )}
                </div>
              </div>

              {/* Line Items Section */}
              <div className="p-4 sm:p-5 bg-gray-50 border border-gray-200 rounded-2xl space-y-4">
                <div className="flex items-center justify-between flex-wrap gap-2">
                  <h4 className="font-bold text-gray-900 text-sm flex items-center gap-1.5">
                    <Package className="w-4 h-4 text-emerald-600" />
                    Line Items
                  </h4>

                  <div className="flex items-center gap-2 flex-wrap">
                    <button
                      type="button"
                      onClick={() => handleOpenQuickCreate("stockitem")}
                      className="px-2.5 py-1.5 bg-white border border-gray-200 hover:bg-gray-100 rounded-lg text-xs font-bold text-gray-700"
                    >
                      + New Stock Item
                    </button>

                    <button
                      type="button"
                      onClick={() => handleOpenQuickCreate("hsn")}
                      className="px-2.5 py-1.5 bg-white border border-gray-200 hover:bg-gray-100 rounded-lg text-xs font-bold text-gray-700"
                    >
                      + New HSN
                    </button>

                    <button
                      type="button"
                      onClick={() => setIsStockSearchOpen(!isStockSearchOpen)}
                      className="px-3 py-1.5 bg-blue-700 hover:bg-blue-800 text-white rounded-lg text-xs font-bold flex items-center gap-1"
                    >
                      <Search className="w-3.5 h-3.5" />
                      Add from Stock
                    </button>

                    <button
                      type="button"
                      onClick={handleAddCustomLine}
                      className="px-3 py-1.5 bg-gray-700 hover:bg-gray-800 text-white rounded-lg text-xs font-bold flex items-center gap-1"
                    >
                      <Plus className="w-3.5 h-3.5" />
                      Custom Item
                    </button>
                  </div>
                </div>

                {/* Stock Search Panel */}
                {isStockSearchOpen && (
                  <div className="p-4 bg-blue-50 border border-blue-200 rounded-xl space-y-3">
                    <div className="flex items-center justify-between gap-2">
                      <div className="relative flex-1">
                        <Search className="w-4 h-4 text-blue-500 absolute left-3 top-2.5" />
                        <input
                          type="text"
                          placeholder="Type stock item name, SKU, specification to search..."
                          value={stockSearchQuery}
                          onChange={(e) => setStockSearchQuery(e.target.value)}
                          className="w-full pl-9 pr-3 py-2 text-xs border border-blue-300 rounded-xl bg-white focus:ring-2 focus:ring-blue-500"
                        />
                      </div>
                      <button
                        onClick={() => fetchStockItems(true)}
                        className="p-2 text-blue-700 hover:bg-blue-100 rounded-xl"
                        title="Refresh stock list"
                      >
                        <RefreshCw className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => setIsStockSearchOpen(false)}
                        className="text-gray-400 hover:text-gray-700 font-bold p-1"
                      >
                        ✕
                      </button>
                    </div>

                    <div className="max-h-60 overflow-y-auto border border-blue-200 rounded-xl bg-white divide-y divide-gray-100">
                      {stockItems
                        .filter((item) => {
                          const q = stockSearchQuery.toLowerCase().trim();
                          if (!q) return true;
                          return (
                            item.item_name.toLowerCase().includes(q) ||
                            (item.item_code || "").toLowerCase().includes(q) ||
                            (item.sku || "").toLowerCase().includes(q) ||
                            (item.specification || "").toLowerCase().includes(q)
                          );
                        })
                        .slice(0, 30)
                        .map((item, idx) => (
                          <div
                            key={idx}
                            onClick={() => handleAddStockItem(item)}
                            className="p-2.5 hover:bg-blue-50/80 cursor-pointer flex items-center justify-between"
                          >
                            <div>
                              <div className="font-bold text-gray-900 flex items-center gap-2">
                                {item.item_name}
                                <span
                                  className={`px-1.5 py-0.2 rounded text-[9px] font-bold ${
                                    item._source === "CATALOG"
                                      ? "bg-purple-100 text-purple-800"
                                      : "bg-emerald-100 text-emerald-800"
                                  }`}
                                >
                                  {item._source}
                                </span>
                              </div>
                              <div className="text-[10px] text-gray-500 mt-0.5">
                                {[
                                  item.item_code || item.sku,
                                  `GST ${item.default_gst_rate || 18}%`,
                                  item.hsn_code ? `HSN ${item.hsn_code}` : "",
                                  item.specification ? item.specification.slice(0, 35) : ""
                                ]
                                  .filter(Boolean)
                                  .join(" · ")}
                              </div>
                            </div>
                            <div className="font-mono font-bold text-blue-700">
                              ₹{formatCurrency(item.selling_rate || item.effective_selling_rate || 0)}
                            </div>
                          </div>
                        ))}
                    </div>
                  </div>
                )}

                {/* Line Items Table */}
                <div className="border border-gray-200 rounded-xl overflow-x-auto bg-white">
                  <table className="w-full text-left border-collapse text-xs">
                    <thead>
                      <tr className="bg-gray-100 text-[11px] font-bold text-gray-500 uppercase border-b border-gray-200">
                        <th className="p-2.5 text-center w-8">#</th>
                        <th className="p-2.5 min-w-[240px]">Description & Specifications</th>
                        <th className="p-2.5 w-32">HSN / SAC</th>
                        <th className="p-2.5 w-20 text-center">Qty</th>
                        <th className="p-2.5 w-24 text-right">Rate (Ex-Tax)</th>
                        <th className="p-2.5 w-16 text-center">Disc %</th>
                        {docType !== "estimate" && <th className="p-2.5 w-16 text-center">GST %</th>}
                        <th className="p-2.5 w-24 text-right">Taxable</th>
                        {docType !== "estimate" && <th className="p-2.5 w-24 text-right">GST Amt</th>}
                        <th className="p-2.5 w-28 text-right">Total</th>
                        <th className="p-2.5 w-10 text-center"></th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">
                      {lineItems.map((line, idx) => {
                        const gross = (line.quantity || 0) * (line.unit_rate || 0);
                        const effDisc = appliedCouponPct > 0 ? appliedCouponPct : line.discount_percent || 0;
                        const disc = gross * (effDisc / 100);
                        const taxable = gross - disc;
                        const gstAmt = docType === "estimate" ? 0 : taxable * ((line.gst_rate || 0) / 100);
                        const lineTotal = taxable + gstAmt;

                        return (
                          <tr key={idx} className="hover:bg-gray-50/50 align-top">
                            <td className="p-2.5 text-center text-gray-400 font-semibold">{idx + 1}</td>

                            <td className="p-2.5 space-y-1.5">
                              <input
                                type="text"
                                placeholder="Item / service description *"
                                value={line.item_description}
                                onChange={(e) => handleUpdateLine(idx, "item_description", e.target.value)}
                                className="w-full px-2 py-1 border border-gray-200 rounded font-semibold text-gray-900"
                                required
                              />

                              <div className="grid grid-cols-2 gap-1.5">
                                <input
                                  type="text"
                                  placeholder="Specification (e.g. 60V, 250W)"
                                  value={line.specification}
                                  onChange={(e) => handleUpdateLine(idx, "specification", e.target.value)}
                                  className="px-1.5 py-0.5 text-[10px] border border-gray-200 rounded bg-gray-50"
                                />
                                <input
                                  type="text"
                                  placeholder="Colour"
                                  value={line.color}
                                  onChange={(e) => handleUpdateLine(idx, "color", e.target.value)}
                                  className="px-1.5 py-0.5 text-[10px] border border-gray-200 rounded bg-gray-50"
                                />
                              </div>

                              <div className="grid grid-cols-3 gap-1.5">
                                <input
                                  type="text"
                                  placeholder="Warranty (e.g. 1 Year)"
                                  value={line.warranty_details}
                                  onChange={(e) => handleUpdateLine(idx, "warranty_details", e.target.value)}
                                  className="px-1.5 py-0.5 text-[10px] border border-emerald-300 rounded bg-emerald-50/40 text-emerald-900"
                                />
                                <input
                                  type="text"
                                  placeholder="Batch No."
                                  value={line.batch_number}
                                  onChange={(e) => handleUpdateLine(idx, "batch_number", e.target.value)}
                                  className="px-1.5 py-0.5 text-[10px] border border-gray-200 rounded bg-gray-50"
                                />
                                <input
                                  type="text"
                                  placeholder="Serial numbers..."
                                  value={line.serial_numbers}
                                  onChange={(e) => handleUpdateLine(idx, "serial_numbers", e.target.value)}
                                  className="px-1.5 py-0.5 text-[10px] border border-blue-200 rounded bg-blue-50/40 text-blue-900 font-mono"
                                />
                              </div>
                            </td>

                            {/* HSN Selection */}
                            <td className="p-2.5">
                              <select
                                value={line.hsn_id ? String(line.hsn_id) : ""}
                                onChange={(e) => {
                                  const h = hsnCodes.find((code) => String(code.id) === e.target.value);
                                  if (h) {
                                    handleUpdateLine(idx, "hsn_id", h.id);
                                    handleUpdateLine(idx, "hsn_code", h.hsn_code);
                                    handleUpdateLine(idx, "gst_rate", h.igst_rate || (h.cgst_rate || 0) * 2 || 18);
                                  } else {
                                    handleUpdateLine(idx, "hsn_id", null);
                                    handleUpdateLine(idx, "hsn_code", "");
                                  }
                                }}
                                className="w-full px-2 py-1 text-xs border border-gray-200 rounded bg-white"
                              >
                                <option value="">Select HSN</option>
                                {hsnCodes.map((h) => (
                                  <option key={h.id} value={h.id}>
                                    {h.hsn_code} - {h.description?.slice(0, 18)}
                                  </option>
                                ))}
                              </select>
                              {line.hsn_code && (
                                <span className="text-[10px] font-mono text-gray-500 block mt-0.5">
                                  HSN: {line.hsn_code}
                                </span>
                              )}
                            </td>

                            {/* Qty */}
                            <td className="p-2.5 text-center">
                              <input
                                type="number"
                                min={0.01}
                                step={0.01}
                                value={line.quantity}
                                onChange={(e) => handleUpdateLine(idx, "quantity", parseFloat(e.target.value) || 0)}
                                className="w-16 px-1.5 py-1 text-xs text-center border border-gray-200 rounded font-semibold"
                              />
                            </td>

                            {/* Rate */}
                            <td className="p-2.5 text-right">
                              <input
                                type="number"
                                min={0}
                                step={0.01}
                                value={line.unit_rate}
                                onChange={(e) => handleUpdateLine(idx, "unit_rate", parseFloat(e.target.value) || 0)}
                                className="w-20 px-1.5 py-1 text-xs text-right border border-gray-200 rounded font-mono font-semibold"
                              />
                            </td>

                            {/* Disc % */}
                            <td className="p-2.5 text-center">
                              <input
                                type="number"
                                min={0}
                                max={100}
                                step={0.1}
                                value={appliedCouponPct > 0 ? appliedCouponPct : line.discount_percent}
                                readOnly={appliedCouponPct > 0}
                                onChange={(e) => handleUpdateLine(idx, "discount_percent", parseFloat(e.target.value) || 0)}
                                className={`w-14 px-1 py-1 text-xs text-center border rounded ${
                                  appliedCouponPct > 0
                                    ? "bg-amber-100 text-amber-900 border-amber-300 font-bold"
                                    : "border-gray-200"
                                }`}
                                title={appliedCouponPct > 0 ? `Locked by coupon ${appliedCouponCode}` : ""}
                              />
                            </td>

                            {/* GST % */}
                            {docType !== "estimate" && (
                              <td className="p-2.5 text-center">
                                <input
                                  type="number"
                                  min={0}
                                  max={28}
                                  step={0.5}
                                  value={line.gst_rate}
                                  onChange={(e) => handleUpdateLine(idx, "gst_rate", parseFloat(e.target.value) || 0)}
                                  className="w-14 px-1 py-1 text-xs text-center border border-gray-200 rounded font-semibold"
                                />
                              </td>
                            )}

                            {/* Taxable */}
                            <td className="p-2.5 text-right font-mono font-bold text-gray-700">
                              ₹{formatCurrency(taxable)}
                            </td>

                            {/* GST Amt */}
                            {docType !== "estimate" && (
                              <td className="p-2.5 text-right font-mono text-gray-600">₹{formatCurrency(gstAmt)}</td>
                            )}

                            {/* Line Total */}
                            <td className="p-2.5 text-right font-mono font-extrabold text-emerald-700">
                              ₹{formatCurrency(lineTotal)}
                            </td>

                            {/* Delete */}
                            <td className="p-2.5 text-center">
                              <button
                                type="button"
                                onClick={() => handleRemoveLine(idx)}
                                className="p-1 text-rose-500 hover:text-rose-700 rounded"
                              >
                                <Trash2 className="w-3.5 h-3.5" />
                              </button>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Additional Courier & Transport Charges */}
              <div className="p-4 bg-sky-50/40 border border-sky-200 rounded-2xl space-y-3">
                <h4 className="font-bold text-sky-900 text-xs uppercase tracking-wider flex items-center gap-1.5">
                  <Truck className="w-4 h-4 text-sky-600" />
                  Additional Charges (Courier & Transport)
                </h4>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  {/* Courier */}
                  <div className="p-3 bg-white border border-sky-100 rounded-xl space-y-2">
                    <span className="font-bold text-gray-800 text-xs">Courier Charges</span>
                    <div className="grid grid-cols-3 gap-2">
                      <input
                        type="number"
                        placeholder="Amount ₹"
                        value={courierAmount || ""}
                        onChange={(e) => setCourierAmount(parseFloat(e.target.value) || 0)}
                        className="px-2.5 py-1.5 text-xs border border-gray-200 rounded-lg font-mono font-semibold"
                      />
                      <select
                        value={courierHsnId ? String(courierHsnId) : ""}
                        onChange={(e) => {
                          const h = hsnCodes.find((c) => String(c.id) === e.target.value);
                          if (h) {
                            setCourierHsnId(h.id);
                            setCourierHsnCode(h.hsn_code);
                            setCourierGstRate(h.igst_rate || (h.cgst_rate || 0) * 2 || 18);
                          } else {
                            setCourierHsnId(null);
                            setCourierHsnCode("");
                          }
                        }}
                        className="px-2 py-1.5 text-xs border border-gray-200 rounded-lg"
                      >
                        <option value="">Courier HSN</option>
                        {hsnCodes.map((h) => (
                          <option key={h.id} value={h.id}>
                            {h.hsn_code} ({h.igst_rate || 18}%)
                          </option>
                        ))}
                      </select>
                      <input
                        type="number"
                        placeholder="GST %"
                        value={courierGstRate || ""}
                        onChange={(e) => setCourierGstRate(parseFloat(e.target.value) || 0)}
                        className="px-2 py-1.5 text-xs border border-gray-200 rounded-lg text-center"
                      />
                    </div>
                  </div>

                  {/* Transport */}
                  <div className="p-3 bg-white border border-sky-100 rounded-xl space-y-2">
                    <span className="font-bold text-gray-800 text-xs">Transport Charges</span>
                    <div className="grid grid-cols-3 gap-2">
                      <input
                        type="number"
                        placeholder="Amount ₹"
                        value={transportAmount || ""}
                        onChange={(e) => setTransportAmount(parseFloat(e.target.value) || 0)}
                        className="px-2.5 py-1.5 text-xs border border-gray-200 rounded-lg font-mono font-semibold"
                      />
                      <select
                        value={transportHsnId ? String(transportHsnId) : ""}
                        onChange={(e) => {
                          const h = hsnCodes.find((c) => String(c.id) === e.target.value);
                          if (h) {
                            setTransportHsnId(h.id);
                            setTransportHsnCode(h.hsn_code);
                            setTransportGstRate(h.igst_rate || (h.cgst_rate || 0) * 2 || 18);
                          } else {
                            setTransportHsnId(null);
                            setTransportHsnCode("");
                          }
                        }}
                        className="px-2 py-1.5 text-xs border border-gray-200 rounded-lg"
                      >
                        <option value="">Transport HSN</option>
                        {hsnCodes.map((h) => (
                          <option key={h.id} value={h.id}>
                            {h.hsn_code} ({h.igst_rate || 18}%)
                          </option>
                        ))}
                      </select>
                      <input
                        type="number"
                        placeholder="GST %"
                        value={transportGstRate || ""}
                        onChange={(e) => setTransportGstRate(parseFloat(e.target.value) || 0)}
                        className="px-2 py-1.5 text-xs border border-gray-200 rounded-lg text-center"
                      />
                    </div>
                  </div>
                </div>
              </div>

              {/* Coupons & Manual Discount */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {/* Coupon Panel */}
                <div className="p-4 bg-amber-50/50 border border-amber-200 rounded-2xl space-y-3">
                  <div className="flex items-center justify-between">
                    <h4 className="font-bold text-amber-900 text-xs uppercase flex items-center gap-1.5">
                      <Ticket className="w-4 h-4 text-amber-600" />
                      Coupons & Promo Codes
                    </h4>
                    <button
                      type="button"
                      onClick={() => {
                        setIsCouponManagerOpen(true);
                        loadCoupons();
                      }}
                      className="text-[11px] font-bold text-amber-700 hover:underline"
                    >
                      Manage Coupons
                    </button>
                  </div>

                  <div className="flex items-center gap-2">
                    <input
                      type="text"
                      placeholder="Enter coupon code"
                      value={couponCodeInput}
                      onChange={(e) => setCouponCodeInput(e.target.value.toUpperCase())}
                      className="flex-1 px-3 py-1.5 text-xs border border-amber-300 rounded-xl bg-white font-mono uppercase"
                    />
                    <button
                      type="button"
                      onClick={handleApplyCoupon}
                      className="px-3.5 py-1.5 bg-amber-600 hover:bg-amber-700 text-white rounded-xl text-xs font-bold"
                    >
                      Apply
                    </button>
                    {appliedCouponCode && (
                      <button
                        type="button"
                        onClick={handleRemoveCoupon}
                        className="px-2.5 py-1.5 text-rose-600 hover:bg-rose-100 rounded-xl text-xs font-bold"
                      >
                        Remove
                      </button>
                    )}
                  </div>

                  {appliedCouponCode && (
                    <div className="text-[11px] font-bold text-emerald-700 bg-emerald-50 px-2.5 py-1 rounded-lg border border-emerald-200">
                      ✔ Coupon "{appliedCouponCode}" active ({appliedCouponPct}% pre-tax discount applied)
                    </div>
                  )}
                </div>

                {/* Manual Discount Panel */}
                <div className="p-4 bg-purple-50/50 border border-purple-200 rounded-2xl space-y-3">
                  <h4 className="font-bold text-purple-900 text-xs uppercase flex items-center gap-1.5">
                    <DollarSign className="w-4 h-4 text-purple-600" />
                    Manual Discount (Post-GST)
                  </h4>

                  <div className="grid grid-cols-2 gap-2">
                    <input
                      type="number"
                      placeholder="Discount Amount ₹"
                      value={manualDiscountAmount || ""}
                      onChange={(e) => setManualDiscountAmount(parseFloat(e.target.value) || 0)}
                      className="px-3 py-1.5 text-xs border border-purple-300 rounded-xl bg-white font-mono"
                    />
                    <input
                      type="text"
                      placeholder="Reason / Note"
                      value={manualDiscountNote}
                      onChange={(e) => setManualDiscountNote(e.target.value)}
                      className="px-3 py-1.5 text-xs border border-purple-300 rounded-xl bg-white"
                    />
                  </div>

                  <div className="flex justify-end">
                    <button
                      type="button"
                      onClick={handleApplyManualDiscount}
                      className="px-3.5 py-1.5 bg-purple-600 hover:bg-purple-700 text-white rounded-xl text-xs font-bold"
                    >
                      Update Discount
                    </button>
                  </div>
                </div>
              </div>

              {/* Remarks / Narration Box & History */}
              <div className="p-4 bg-gray-50 border border-gray-200 rounded-2xl space-y-3">
                <div className="flex items-center justify-between">
                  <h4 className="font-bold text-gray-900 text-xs uppercase">Invoice Remarks / Narration</h4>
                  {editingInvoiceId && (
                    <button
                      type="button"
                      onClick={handleAddNarrationEntry}
                      className="text-[11px] font-bold text-emerald-700 hover:underline"
                    >
                      + Add to Narration History
                    </button>
                  )}
                </div>

                <textarea
                  rows={2}
                  placeholder="Type any invoice narration, payment terms, or delivery notes..."
                  value={invoiceRemarks}
                  onChange={(e) => setInvoiceRemarks(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-200 rounded-xl bg-white"
                />

                {narrations.length > 0 && (
                  <div className="pt-2 border-t border-gray-200 space-y-2">
                    <span className="text-[10px] font-bold uppercase text-gray-400 block">Narration History</span>
                    <div className="space-y-1.5 max-h-32 overflow-y-auto">
                      {narrations.map((n, i) => (
                        <div key={i} className="text-[11px] p-2 bg-white rounded-lg border border-gray-200">
                          <div className="text-gray-900">{n.narration}</div>
                          <div className="text-[10px] text-gray-400 mt-0.5">
                            {n.created_by_name || "Staff"} · {formatDate(n.created_at || "")}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* Invoice Summary Box */}
              <div className="bg-emerald-950 text-white p-5 rounded-2xl space-y-2.5 font-mono shadow-md">
                <h5 className="font-bold text-xs uppercase text-emerald-300 tracking-wider">Invoice Calculation Summary</h5>

                <div className="flex justify-between text-xs text-gray-300">
                  <span>Gross Subtotal:</span>
                  <span>₹{formatCurrency(invoiceCalculations.subtotal)}</span>
                </div>

                {invoiceCalculations.totalDiscount > 0 && (
                  <div className="flex justify-between text-xs text-amber-300">
                    <span>(-) Total Line Item Discount:</span>
                    <span>-₹{formatCurrency(invoiceCalculations.totalDiscount)}</span>
                  </div>
                )}

                <div className="flex justify-between text-xs text-emerald-100 font-bold pt-1 border-t border-emerald-800">
                  <span>Taxable Amount (Pre-GST):</span>
                  <span>₹{formatCurrency(invoiceCalculations.taxableAmount)}</span>
                </div>

                {docType !== "estimate" && (
                  <>
                    {isIgstActive ? (
                      <div className="flex justify-between text-xs text-sky-300">
                        <span>+ Total IGST:</span>
                        <span>₹{formatCurrency(invoiceCalculations.totalIgst)}</span>
                      </div>
                    ) : (
                      <>
                        <div className="flex justify-between text-xs text-sky-300">
                          <span>+ CGST:</span>
                          <span>₹{formatCurrency(invoiceCalculations.totalCgst)}</span>
                        </div>
                        <div className="flex justify-between text-xs text-sky-300">
                          <span>+ SGST:</span>
                          <span>₹{formatCurrency(invoiceCalculations.totalSgst)}</span>
                        </div>
                      </>
                    )}
                  </>
                )}

                {(courierAmount > 0 || transportAmount > 0) && (
                  <div className="flex justify-between text-xs text-cyan-200">
                    <span>+ Additional Courier/Transport Charges:</span>
                    <span>₹{formatCurrency(courierAmount + transportAmount)}</span>
                  </div>
                )}

                {manualDiscountAmount > 0 && (
                  <div className="flex justify-between text-xs text-rose-300">
                    <span>(-) Manual Post-GST Discount:</span>
                    <span>-₹{formatCurrency(manualDiscountAmount)}</span>
                  </div>
                )}

                {Math.abs(invoiceCalculations.roundOff) > 0.001 && (
                  <div className="flex justify-between text-xs text-gray-400">
                    <span>Round Off:</span>
                    <span>₹{formatCurrency(invoiceCalculations.roundOff)}</span>
                  </div>
                )}

                <div className="flex justify-between text-sm sm:text-base font-black text-emerald-300 pt-2 border-t border-emerald-700">
                  <span>Grand Total (Net Payable):</span>
                  <span>₹{formatCurrency(invoiceCalculations.netPayable)}</span>
                </div>
              </div>
            </div>

            {/* Modal Footer */}
            <div className="px-6 py-4 border-t border-gray-200 bg-gray-50 flex items-center justify-between flex-wrap gap-2">
              <div className="flex items-center gap-2">
                {editingInvoiceId && (
                  <>
                    <button
                      type="button"
                      onClick={() => handleDownloadPdf(editingInvoiceId, "estimate")}
                      className="px-3 py-1.5 bg-blue-50 hover:bg-blue-100 text-blue-800 rounded-xl text-xs font-bold border border-blue-200 flex items-center gap-1"
                    >
                      <Download className="w-3.5 h-3.5" />
                      Estimate PDF
                    </button>

                    <button
                      type="button"
                      onClick={() => handleDownloadPdf(editingInvoiceId, "tax_invoice")}
                      className="px-3 py-1.5 bg-emerald-50 hover:bg-emerald-100 text-emerald-800 rounded-xl text-xs font-bold border border-emerald-200 flex items-center gap-1"
                    >
                      <Download className="w-3.5 h-3.5" />
                      {editingInvoiceStatus === "DRAFT" ? "Proforma (PI) PDF" : "Tax Invoice PDF"}
                    </button>
                  </>
                )}
              </div>

              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setIsCreateModalOpen(false)}
                  className="px-4 py-2 border border-gray-200 hover:bg-gray-100 text-gray-700 rounded-xl text-xs font-bold"
                >
                  Cancel
                </button>

                <button
                  type="button"
                  onClick={handleSaveInvoice}
                  className="px-5 py-2 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-700 hover:to-teal-700 text-white rounded-xl text-xs font-bold shadow-sm"
                >
                  {editingInvoiceId ? "Save Changes" : "Save as Draft"}
                </button>

                {editingInvoiceId && editingInvoiceStatus === "DRAFT" && (
                  <button
                    type="button"
                    onClick={() => {
                      setIsCreateModalOpen(false);
                      handleOpenConfirm(editingInvoiceId, "DRAFT", invoiceCalculations.netPayable);
                    }}
                    className="px-4 py-2 bg-emerald-700 hover:bg-emerald-800 text-white rounded-xl text-xs font-bold shadow-sm flex items-center gap-1.5"
                  >
                    <CheckCircle className="w-4 h-4" />
                    Confirm Invoice
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* MODAL 2: VIEW SALES INVOICE DETAILS & PAYMENT FORM */}
      {/* ========================================================================= */}
      {isViewModalOpen && viewInvoiceData && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-2 sm:p-4 overflow-y-auto animate-in fade-in duration-200">
          <div className="bg-white w-full max-w-4xl rounded-2xl shadow-2xl border border-gray-200 flex flex-col max-h-[92vh] overflow-hidden my-auto text-xs">
            {/* Header */}
            <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between bg-gray-50">
              <div>
                <h3 className="text-base font-bold text-gray-900 flex items-center gap-2">
                  <FileText className="w-5 h-5 text-emerald-600" />
                  {viewInvoiceData.invoice_number}
                </h3>
                <p className="text-xs text-gray-500">
                  {viewInvoiceData.customer_name} · {formatDate(viewInvoiceData.invoice_date)}
                </p>
              </div>
              <button
                onClick={() => setIsViewModalOpen(false)}
                className="p-2 text-gray-400 hover:text-gray-700 rounded-xl"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Content */}
            <div className="p-6 overflow-y-auto space-y-5 flex-1">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 p-4 bg-gray-50 rounded-xl border border-gray-200">
                <div className="space-y-1">
                  <div><strong>Invoice No:</strong> {viewInvoiceData.invoice_number}</div>
                  <div><strong>Date:</strong> {formatDate(viewInvoiceData.invoice_date)}</div>
                  {viewInvoiceData.so_number && <div><strong>S.O. No:</strong> {viewInvoiceData.so_number}</div>}
                  <div><strong>Status:</strong> {viewInvoiceData.status}</div>
                  <div><strong>Payment:</strong> {viewInvoiceData.payment_status}</div>
                </div>
                <div className="space-y-1">
                  <div><strong>Customer:</strong> {viewInvoiceData.customer_name}</div>
                  <div><strong>Phone:</strong> {viewInvoiceData.customer_phone || "—"}</div>
                  <div><strong>State:</strong> {viewInvoiceData.customer_state || "—"}</div>
                  <div><strong>GSTIN:</strong> {viewInvoiceData.customer_gstin || "—"}</div>
                </div>
              </div>

              {/* View Mode Toggle */}
              <div className="flex items-center justify-between">
                <h4 className="font-bold text-gray-900 text-sm">Line Items</h4>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setViewGstToggle(false)}
                    className={`px-3 py-1 text-xs font-semibold rounded-lg ${
                      !viewGstToggle ? "bg-blue-600 text-white" : "bg-gray-100 text-gray-700"
                    }`}
                  >
                    Without Tax
                  </button>
                  <button
                    onClick={() => setViewGstToggle(true)}
                    className={`px-3 py-1 text-xs font-semibold rounded-lg ${
                      viewGstToggle ? "bg-emerald-600 text-white" : "bg-gray-100 text-gray-700"
                    }`}
                  >
                    Incl. GST
                  </button>
                </div>
              </div>

              {/* Line Items Table */}
              <div className="border border-gray-200 rounded-xl overflow-hidden">
                <table className="w-full text-left border-collapse text-xs">
                  <thead>
                    <tr className="bg-gray-100 text-[11px] font-bold text-gray-600 uppercase border-b border-gray-200">
                      <th className="p-2.5">#</th>
                      <th className="p-2.5">Item Description</th>
                      {viewGstToggle && <th className="p-2.5 text-center">HSN</th>}
                      <th className="p-2.5 text-center">Qty</th>
                      <th className="p-2.5 text-right">Rate (Ex-Tax)</th>
                      {viewGstToggle && <th className="p-2.5 text-center">GST %</th>}
                      {viewGstToggle && <th className="p-2.5 text-right">GST Amt</th>}
                      <th className="p-2.5 text-right">Total</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100 font-medium">
                    {(viewInvoiceData.line_items || []).map((item, idx) => {
                      const qty = parseFloat(item.quantity || 1);
                      const rate = parseFloat(item.unit_rate || 0);
                      const gross = qty * rate;
                      const disc = gross * ((parseFloat(item.discount_percent) || 0) / 100);
                      const taxable = gross - disc;
                      const gst = taxable * ((parseFloat(item.gst_rate) || 0) / 100);

                      return (
                        <tr key={idx} className="hover:bg-gray-50">
                          <td className="p-2.5 text-gray-400">{idx + 1}</td>
                          <td className="p-2.5 font-bold text-gray-900">
                            {item.item_description}
                            {item.specification && (
                              <span className="block text-[10px] text-gray-500 font-normal">{item.specification}</span>
                            )}
                          </td>
                          {viewGstToggle && <td className="p-2.5 text-center text-gray-500">{item.hsn_code || "—"}</td>}
                          <td className="p-2.5 text-center font-mono">{qty}</td>
                          <td className="p-2.5 text-right font-mono">₹{formatCurrency(rate)}</td>
                          {viewGstToggle && <td className="p-2.5 text-center text-gray-500">{item.gst_rate}%</td>}
                          {viewGstToggle && <td className="p-2.5 text-right font-mono text-gray-600">₹{formatCurrency(gst)}</td>}
                          <td className="p-2.5 text-right font-mono font-bold text-emerald-700">
                            ₹{formatCurrency(viewGstToggle ? taxable + gst : taxable)}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>

              {/* Payment Status & Form */}
              {viewInvoiceData.status !== "DRAFT" && (
                <div className="p-4 bg-slate-50 border border-slate-200 rounded-2xl space-y-4">
                  <div className="flex items-center justify-between flex-wrap gap-2">
                    <div className="flex items-center gap-3">
                      <span className="font-bold text-gray-900">Payment Status:</span>
                      <span className="px-2.5 py-0.5 rounded-full text-[10px] font-extrabold bg-emerald-100 text-emerald-800">
                        {viewInvoiceData.payment_status || "PENDING"}
                      </span>
                      <span className="text-gray-600 font-mono">
                        Received: <strong>₹{formatCurrency(viewInvoiceData.amount_received || 0)}</strong>
                      </span>
                      <span className="text-rose-700 font-mono">
                        Balance Due: <strong>₹{formatCurrency(viewInvoiceData.balance_due || 0)}</strong>
                      </span>
                    </div>

                    <button
                      onClick={() => handleOpenPaymentModal(viewInvoiceData)}
                      className="px-3.5 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-bold flex items-center gap-1"
                    >
                      <Plus className="w-3.5 h-3.5" />
                      Record Payment
                    </button>
                  </div>

                  {/* Payment Records Timeline */}
                  {invoicePayments.length > 0 && (
                    <div className="pt-3 border-t border-gray-200 space-y-2">
                      <span className="font-bold text-gray-600 text-[11px] uppercase tracking-wider block">
                        Payment Transactions
                      </span>
                      <div className="border border-gray-200 rounded-xl overflow-hidden bg-white">
                        <table className="w-full text-left border-collapse text-xs">
                          <thead>
                            <tr className="bg-gray-50 text-[10px] font-bold text-gray-500 uppercase">
                              <th className="p-2">Date</th>
                              <th className="p-2">Mode</th>
                              <th className="p-2 text-right">Amount</th>
                              <th className="p-2">Reference</th>
                              <th className="p-2">Recorded By</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-gray-100">
                            {invoicePayments.map((py) => (
                              <tr key={py.id}>
                                <td className="p-2">{formatDate(py.payment_date)}</td>
                                <td className="p-2 font-bold text-blue-700">{py.payment_mode}</td>
                                <td className="p-2 text-right font-mono font-bold text-emerald-700">
                                  ₹{formatCurrency(py.amount)}
                                </td>
                                <td className="p-2 text-gray-500">{py.reference_number || "—"}</td>
                                <td className="p-2 text-gray-400">{py.created_by || "—"}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Footer */}
            <div className="px-6 py-4 border-t border-gray-200 bg-gray-50 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <button
                  onClick={() => handleDownloadPdf(viewInvoiceData.id, "estimate")}
                  className="px-3 py-1.5 bg-blue-50 text-blue-700 rounded-lg font-bold border border-blue-200 hover:bg-blue-100"
                >
                  View Estimate PDF
                </button>
                <button
                  onClick={() => handleDownloadPdf(viewInvoiceData.id, "tax_invoice")}
                  className="px-3 py-1.5 bg-emerald-50 text-emerald-700 rounded-lg font-bold border border-emerald-200 hover:bg-emerald-100"
                >
                  View Tax Invoice PDF
                </button>
              </div>

              <button
                onClick={() => setIsViewModalOpen(false)}
                className="px-4 py-2 bg-gray-200 hover:bg-gray-300 rounded-xl font-bold"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* MODAL 3: CONFIRM INVOICE MODAL */}
      {/* ========================================================================= */}
      {isConfirmModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4 animate-in fade-in duration-200">
          <div className="bg-white w-full max-w-md rounded-2xl shadow-2xl border border-gray-200 p-6 space-y-4 text-xs">
            <div className="flex items-center gap-2.5 text-emerald-700">
              <ShieldCheck className="w-6 h-6" />
              <h3 className="text-base font-bold text-gray-900">
                {confirmStatus === "CONFIRMED" ? "Re-Confirm Sales Invoice" : "Confirm Sales Invoice"}
              </h3>
            </div>

            {confirmStatus === "CONFIRMED" ? (
              <div className="p-3 bg-amber-50 border border-amber-200 rounded-xl text-amber-900 text-xs">
                <strong>Notice:</strong> This invoice is already CONFIRMED. Re-confirming will reverse previously
                created inventory and ledger entries and generate fresh updated entries.
              </div>
            ) : (
              <p className="text-gray-600">
                Confirming this draft will generate ledger entries, record accounts receivable, and deduct inventory
                quantities.
              </p>
            )}

            <div>
              <label className="block font-bold text-gray-700 mb-1">Advance / Amount Received Now (₹)</label>
              <input
                type="number"
                min={0}
                step={0.01}
                value={confirmAmountReceived}
                onChange={(e) => setConfirmAmountReceived(parseFloat(e.target.value) || 0)}
                className="w-full px-3 py-2 border border-gray-200 rounded-xl bg-white font-mono font-bold"
                placeholder="0.00"
              />
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <button
                onClick={() => setIsConfirmModalOpen(false)}
                className="px-4 py-2 border border-gray-200 rounded-xl font-bold hover:bg-gray-100"
              >
                Cancel
              </button>
              <button
                onClick={handleSubmitConfirm}
                disabled={submittingConfirm}
                className="px-5 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl font-bold shadow-sm flex items-center gap-1.5"
              >
                {submittingConfirm ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <CheckCircle className="w-3.5 h-3.5" />}
                Confirm Now
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* MODAL 4: RECORD PAYMENT MODAL */}
      {/* ========================================================================= */}
      {isPaymentModalOpen && viewInvoiceData && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4 animate-in fade-in duration-200">
          <div className="bg-white w-full max-w-lg rounded-2xl shadow-2xl border border-gray-200 p-6 space-y-4 text-xs">
            <div className="flex items-center justify-between border-b border-gray-100 pb-3">
              <div className="flex items-center gap-2">
                <DollarSign className="w-5 h-5 text-emerald-600" />
                <h3 className="text-base font-bold text-gray-900">Record Payment</h3>
              </div>
              <button onClick={() => setIsPaymentModalOpen(false)} className="text-gray-400 hover:text-gray-700">
                ✕
              </button>
            </div>

            <div className="p-3 bg-emerald-50 rounded-xl border border-emerald-100 flex justify-between font-mono">
              <div>
                <div className="text-[10px] uppercase text-emerald-800">Invoice No:</div>
                <div className="font-bold text-gray-900">{viewInvoiceData.invoice_number}</div>
              </div>
              <div>
                <div className="text-[10px] uppercase text-emerald-800">Balance Due:</div>
                <div className="font-bold text-rose-700">₹{formatCurrency(viewInvoiceData.balance_due || 0)}</div>
              </div>
            </div>

            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-bold text-gray-700 mb-1">Amount (₹) *</label>
                  <input
                    type="number"
                    min={0.01}
                    step={0.01}
                    value={payAmount}
                    onChange={(e) => setPayAmount(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-200 rounded-xl font-mono font-bold"
                    placeholder="₹ 0.00"
                    required
                  />
                </div>

                <div>
                  <label className="block font-bold text-gray-700 mb-1">Payment Mode *</label>
                  <select
                    value={payMode}
                    onChange={(e) => setPayMode(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-200 rounded-xl bg-white"
                  >
                    <option value="CASH">Cash</option>
                    <option value="UPI">UPI</option>
                    <option value="CARD">Card</option>
                    <option value="NEFT">NEFT</option>
                    <option value="RTGS">RTGS</option>
                    <option value="CHEQUE">Cheque</option>
                    <option value="OTHER">Other</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-bold text-gray-700 mb-1">Payment Date *</label>
                  <input
                    type="date"
                    value={payDate}
                    onChange={(e) => setPayDate(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-200 rounded-xl bg-white"
                    required
                  />
                </div>

                <div>
                  <label className="block font-bold text-gray-700 mb-1">Reference / UTR</label>
                  <input
                    type="text"
                    placeholder="Transaction ID / Cheque #"
                    value={payRef}
                    onChange={(e) => setPayRef(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-200 rounded-xl"
                  />
                </div>
              </div>

              <div>
                <label className="block font-bold text-gray-700 mb-1">Notes (Optional)</label>
                <input
                  type="text"
                  placeholder="Additional payment notes"
                  value={payNotes}
                  onChange={(e) => setPayNotes(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-200 rounded-xl"
                />
              </div>
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <button
                onClick={() => setIsPaymentModalOpen(false)}
                className="px-4 py-2 border border-gray-200 rounded-xl font-bold hover:bg-gray-100"
              >
                Cancel
              </button>
              <button
                onClick={() => handleSubmitPayment(viewInvoiceData.id)}
                disabled={submittingPayment}
                className="px-5 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl font-bold shadow-sm flex items-center gap-1.5"
              >
                {submittingPayment ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <DollarSign className="w-3.5 h-3.5" />}
                Save Payment
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* MODAL 5: COUPON MANAGER MODAL */}
      {/* ========================================================================= */}
      {isCouponManagerOpen && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4 animate-in fade-in duration-200">
          <div className="bg-white w-full max-w-2xl rounded-2xl shadow-2xl border border-gray-200 p-6 space-y-5 text-xs">
            <div className="flex items-center justify-between border-b border-gray-100 pb-3">
              <div className="flex items-center gap-2">
                <Ticket className="w-5 h-5 text-amber-600" />
                <h3 className="text-base font-bold text-gray-900">Manage Sales Coupons</h3>
              </div>
              <button onClick={() => setIsCouponManagerOpen(false)} className="text-gray-400 hover:text-gray-700">
                ✕
              </button>
            </div>

            {/* Create Coupon Form */}
            <div className="p-4 bg-amber-50/50 border border-amber-200 rounded-xl space-y-3">
              <span className="font-bold text-amber-900 uppercase text-[11px] block">Create New Coupon</span>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
                <input
                  type="text"
                  placeholder="Code *"
                  value={newCouponCode}
                  onChange={(e) => setNewCouponCode(e.target.value.toUpperCase())}
                  className="px-3 py-1.5 border border-amber-300 rounded-lg uppercase font-mono font-bold bg-white"
                />
                <input
                  type="number"
                  placeholder="Discount % *"
                  min={0.1}
                  max={100}
                  step={0.1}
                  value={newCouponPct || ""}
                  onChange={(e) => setNewCouponPct(parseFloat(e.target.value) || 0)}
                  className="px-3 py-1.5 border border-amber-300 rounded-lg bg-white"
                />
                <input
                  type="date"
                  placeholder="Valid From"
                  value={newCouponFrom}
                  onChange={(e) => setNewCouponFrom(e.target.value)}
                  className="px-2 py-1.5 border border-amber-300 rounded-lg bg-white text-[11px]"
                />
                <input
                  type="date"
                  placeholder="Valid Until"
                  value={newCouponUntil}
                  onChange={(e) => setNewCouponUntil(e.target.value)}
                  className="px-2 py-1.5 border border-amber-300 rounded-lg bg-white text-[11px]"
                />
              </div>

              <div className="flex items-center justify-between gap-2">
                <input
                  type="text"
                  placeholder="Description / Remarks"
                  value={newCouponDesc}
                  onChange={(e) => setNewCouponDesc(e.target.value)}
                  className="flex-1 px-3 py-1.5 border border-amber-300 rounded-lg bg-white"
                />
                <button
                  onClick={handleCreateCoupon}
                  className="px-4 py-1.5 bg-amber-600 hover:bg-amber-700 text-white rounded-lg font-bold"
                >
                  Create Coupon
                </button>
              </div>
            </div>

            {/* Coupons List */}
            <div className="border border-gray-200 rounded-xl overflow-hidden max-h-64 overflow-y-auto">
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="bg-gray-50 text-[10px] font-bold text-gray-500 uppercase border-b border-gray-200">
                    <th className="p-2.5">Code</th>
                    <th className="p-2.5 text-center">Discount</th>
                    <th className="p-2.5">Valid Dates</th>
                    <th className="p-2.5 text-center">Uses</th>
                    <th className="p-2.5 text-center">Active</th>
                    <th className="p-2.5 text-right"></th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100 font-medium">
                  {couponsList.map((c) => (
                    <tr key={c.id} className="hover:bg-gray-50">
                      <td className="p-2.5 font-mono font-bold text-blue-900">{c.coupon_code}</td>
                      <td className="p-2.5 text-center font-bold text-emerald-700">{c.discount_percentage}%</td>
                      <td className="p-2.5 text-gray-500">
                        {c.valid_from ? `${c.valid_from} to ${c.valid_until || "∞"}` : "Always"}
                      </td>
                      <td className="p-2.5 text-center text-gray-600">
                        {c.times_used || 0}
                        {c.max_uses ? `/${c.max_uses}` : ""}
                      </td>
                      <td className="p-2.5 text-center">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${c.is_active ? "bg-emerald-100 text-emerald-800" : "bg-rose-100 text-rose-800"}`}>
                          {c.is_active ? "YES" : "NO"}
                        </span>
                      </td>
                      <td className="p-2.5 text-right">
                        <button
                          onClick={() => handleDeleteCoupon(c.id)}
                          className="p-1 text-rose-600 hover:text-rose-800"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="flex justify-end">
              <button
                onClick={() => setIsCouponManagerOpen(false)}
                className="px-4 py-2 bg-gray-200 hover:bg-gray-300 rounded-xl font-bold"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* MODAL 6: QUICK CREATE MASTER MODAL (STOCK ITEM / HSN / PARTNER) */}
      {/* ========================================================================= */}
      {isQuickCreateOpen && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4 animate-in fade-in duration-200">
          <div className="bg-white w-full max-w-lg rounded-2xl shadow-2xl border border-gray-200 p-6 space-y-4 text-xs">
            <div className="flex items-center justify-between border-b border-gray-100 pb-3">
              <h3 className="text-base font-bold text-gray-900">
                {quickCreateType === "stockitem"
                  ? "Create New Stock Item"
                  : quickCreateType === "hsn"
                  ? "Create New HSN Code"
                  : "Create New Registered Party"}
              </h3>
              <button onClick={() => setIsQuickCreateOpen(false)} className="text-gray-400 hover:text-gray-700">
                ✕
              </button>
            </div>

            {quickCreateType === "stockitem" && (
              <div className="space-y-3">
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block font-bold text-gray-700 mb-1">Item Code *</label>
                    <input
                      type="text"
                      placeholder="e.g. ITM001"
                      value={qcCode}
                      onChange={(e) => setQcCode(e.target.value.toUpperCase())}
                      className="w-full px-3 py-2 border border-gray-200 rounded-xl uppercase font-mono font-bold"
                    />
                  </div>
                  <div>
                    <label className="block font-bold text-gray-700 mb-1">Item Name *</label>
                    <input
                      type="text"
                      placeholder="Full item name"
                      value={qcName}
                      onChange={(e) => setQcName(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-200 rounded-xl"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block font-bold text-gray-700 mb-1">HSN Code</label>
                    <select
                      value={qcHsnId}
                      onChange={(e) => setQcHsnId(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-200 rounded-xl bg-white"
                    >
                      <option value="">Select HSN</option>
                      {hsnCodes.map((h) => (
                        <option key={h.id} value={h.id}>
                          {h.hsn_code} ({h.igst_rate || 18}%)
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="block font-bold text-gray-700 mb-1">UOM</label>
                    <select
                      value={qcUom}
                      onChange={(e) => setQcUom(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-200 rounded-xl bg-white"
                    >
                      <option value="PCS">Pieces (PCS)</option>
                      <option value="NOS">Numbers (NOS)</option>
                      <option value="KG">Kilogram (KG)</option>
                      <option value="SET">Set (SET)</option>
                    </select>
                  </div>
                </div>

                <div className="grid grid-cols-3 gap-3">
                  <div>
                    <label className="block font-bold text-gray-700 mb-1">Purchase Rate</label>
                    <input
                      type="number"
                      step={0.01}
                      value={qcPurchaseRate || ""}
                      onChange={(e) => handleQcCalcSaleRate(parseFloat(e.target.value) || 0, qcMarkupPct)}
                      className="w-full px-3 py-2 border border-gray-200 rounded-xl font-mono"
                    />
                  </div>

                  <div>
                    <label className="block font-bold text-gray-700 mb-1">Markup %</label>
                    <input
                      type="number"
                      step={0.5}
                      value={qcMarkupPct}
                      onChange={(e) => handleQcCalcSaleRate(qcPurchaseRate, parseFloat(e.target.value) || 0)}
                      className="w-full px-3 py-2 border border-gray-200 rounded-xl text-center"
                    />
                  </div>

                  <div>
                    <label className="block font-bold text-gray-700 mb-1">Selling Rate</label>
                    <input
                      type="number"
                      step={0.01}
                      value={qcSaleRate || ""}
                      onChange={(e) => setQcSaleRate(parseFloat(e.target.value) || 0)}
                      className="w-full px-3 py-2 border border-gray-200 rounded-xl font-mono font-bold text-emerald-700"
                    />
                  </div>
                </div>
              </div>
            )}

            {quickCreateType === "hsn" && (
              <div className="space-y-3">
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block font-bold text-gray-700 mb-1">HSN / SAC Code *</label>
                    <input
                      type="text"
                      placeholder="e.g. 8711"
                      value={qcCode}
                      onChange={(e) => setQcCode(e.target.value.trim())}
                      className="w-full px-3 py-2 border border-gray-200 rounded-xl font-mono font-bold"
                    />
                  </div>

                  <div>
                    <label className="block font-bold text-gray-700 mb-1">GST Rate % *</label>
                    <select
                      value={qcHsnGstRate}
                      onChange={(e) => setQcHsnGstRate(parseFloat(e.target.value))}
                      className="w-full px-3 py-2 border border-gray-200 rounded-xl bg-white"
                    >
                      <option value={0}>0%</option>
                      <option value={5}>5%</option>
                      <option value={12}>12%</option>
                      <option value={18}>18%</option>
                      <option value={28}>28%</option>
                    </select>
                  </div>
                </div>

                <div>
                  <label className="block font-bold text-gray-700 mb-1">Description *</label>
                  <textarea
                    rows={2}
                    placeholder="HSN description"
                    value={qcDesc}
                    onChange={(e) => setQcDesc(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-200 rounded-xl bg-white"
                  />
                </div>
              </div>
            )}

            <div className="flex justify-end gap-2 pt-2">
              <button
                onClick={() => setIsQuickCreateOpen(false)}
                className="px-4 py-2 border border-gray-200 rounded-xl font-bold hover:bg-gray-100"
              >
                Cancel
              </button>
              <button
                onClick={handleSubmitQuickCreate}
                disabled={submittingQuickCreate}
                className="px-5 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl font-bold"
              >
                Create Record
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* MODAL 7: ADD PENDING INVOICE MODAL */}
      {/* ========================================================================= */}
      {isAddPendingModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4 animate-in fade-in duration-200">
          <div className="bg-white w-full max-w-2xl rounded-2xl shadow-2xl border border-gray-200 p-6 space-y-4 text-xs">
            <div className="flex items-center justify-between border-b border-gray-100 pb-3">
              <div className="flex items-center gap-2">
                <Truck className="w-5 h-5 text-purple-600" />
                <h3 className="text-base font-bold text-gray-900">Add Invoice to Pending Dispatch</h3>
              </div>
              <button onClick={() => setIsAddPendingModalOpen(false)} className="text-gray-400 hover:text-gray-700">
                ✕
              </button>
            </div>

            <div className="space-y-3">
              <div>
                <label className="block font-bold text-gray-700 mb-1">Search Confirmed Invoice</label>
                <div className="relative">
                  <Search className="w-4 h-4 text-gray-400 absolute left-3 top-2.5" />
                  <input
                    type="text"
                    placeholder="Search invoice number or customer name..."
                    value={addPendingSearch}
                    onChange={(e) => handleSearchConfirmedForPending(e.target.value)}
                    className="w-full pl-9 pr-3 py-2 border border-gray-200 rounded-xl focus:ring-2 focus:ring-purple-500"
                  />
                </div>
              </div>

              {addPendingInvoices.length > 0 && !selectedAddPendingInvoice && (
                <div className="border border-gray-200 rounded-xl max-h-56 overflow-y-auto divide-y divide-gray-100">
                  {addPendingInvoices.map((inv) => (
                    <div
                      key={inv.id}
                      onClick={() => handleSelectInvoiceForPending(inv)}
                      className="p-3 hover:bg-purple-50 cursor-pointer flex items-center justify-between"
                    >
                      <div>
                        <div className="font-bold text-gray-900">{inv.invoice_number}</div>
                        <div className="text-[11px] text-gray-500">{inv.customer_name} · {formatDate(inv.invoice_date)}</div>
                      </div>
                      <div className="text-right">
                        <span className="font-mono font-bold text-emerald-700">₹{formatCurrency(inv.grand_total)}</span>
                        {inv.track_physical_dispatch && (
                          <div className="text-[10px] text-amber-600 font-bold">Already tracking</div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {selectedAddPendingInvoice && (
                <div className="p-4 bg-purple-50 rounded-xl border border-purple-200 space-y-3">
                  <div className="flex items-center justify-between">
                    <div>
                      <h4 className="font-bold text-gray-900 text-sm">{selectedAddPendingInvoice.invoice_number}</h4>
                      <p className="text-gray-500">{selectedAddPendingInvoice.customer_name}</p>
                    </div>
                    <button
                      onClick={() => setSelectedAddPendingInvoice(null)}
                      className="text-xs text-rose-600 font-bold hover:underline"
                    >
                      Change Invoice
                    </button>
                  </div>

                  <div className="border border-purple-200 rounded-xl overflow-hidden bg-white">
                    <table className="w-full text-left border-collapse text-xs">
                      <thead>
                        <tr className="bg-purple-100/60 text-[10px] font-bold text-purple-900 uppercase">
                          <th className="p-2">Item</th>
                          <th className="p-2 text-right">Invoiced Qty</th>
                          <th className="p-2 text-center">Pending to Track</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-100">
                        {(selectedAddPendingInvoice.line_items || []).map((ln: any) => (
                          <tr key={ln.id}>
                            <td className="p-2 font-semibold text-gray-900">{ln.item_description}</td>
                            <td className="p-2 text-right font-mono">{ln.quantity}</td>
                            <td className="p-2 text-center">
                              <input
                                type="number"
                                min={0}
                                max={ln.quantity}
                                step={0.01}
                                value={addPendingLineQtys[ln.id] !== undefined ? addPendingLineQtys[ln.id] : ln.quantity}
                                onChange={(e) =>
                                  setAddPendingLineQtys((prev) => ({
                                    ...prev,
                                    [ln.id]: parseFloat(e.target.value) || 0
                                  }))
                                }
                                className="w-20 px-2 py-0.5 border border-purple-300 rounded text-center font-bold text-purple-900"
                              />
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <button
                onClick={() => setIsAddPendingModalOpen(false)}
                className="px-4 py-2 border border-gray-200 rounded-xl font-bold hover:bg-gray-100"
              >
                Cancel
              </button>
              <button
                onClick={handleConfirmAddPending}
                disabled={!selectedAddPendingInvoice}
                className="px-5 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-xl font-bold disabled:opacity-50"
              >
                Add to Pending Dispatch
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* MODAL 8: PDF VIEWER / DOWNLOAD MODAL */}
      {/* ========================================================================= */}
      {isPdfViewerOpen && pdfBlobUrl && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-xs flex items-center justify-center p-2 sm:p-4 overflow-hidden animate-in fade-in duration-200">
          <div className="bg-white w-full max-w-5xl h-[92vh] rounded-2xl shadow-2xl border border-gray-200 flex flex-col overflow-hidden">
            <div className="px-5 py-3 border-b border-gray-200 bg-gray-50 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <FileText className="w-5 h-5 text-emerald-600" />
                <h3 className="text-sm font-bold text-gray-900">{pdfViewerTitle}</h3>
              </div>
              <div className="flex items-center gap-2">
                <a
                  href={pdfBlobUrl}
                  download={pdfViewerFilename}
                  className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-bold flex items-center gap-1.5 shadow-sm"
                >
                  <Download className="w-3.5 h-3.5" />
                  Download PDF
                </a>
                <button
                  onClick={() => {
                    setIsPdfViewerOpen(false);
                    if (pdfBlobUrl) URL.revokeObjectURL(pdfBlobUrl);
                  }}
                  className="p-1.5 text-gray-400 hover:text-gray-700 rounded-xl"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
            </div>

            <div className="flex-1 bg-gray-100 p-2">
              <iframe src={pdfBlobUrl} className="w-full h-full rounded-xl border border-gray-200 bg-white" />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
