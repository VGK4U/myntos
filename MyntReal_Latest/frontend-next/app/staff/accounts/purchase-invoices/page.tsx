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
  AlertCircle,
  HelpCircle,
  X,
  ExternalLink,
  ChevronUp,
  Upload,
  Undo2,
  Warehouse,
  History,
  Info,
  Check,
  ArrowRight,
  FileSpreadsheet
} from "lucide-react";

// --- Types & Interfaces ---
interface Company {
  id: number;
  company_name?: string;
  name?: string;
  state?: string;
  gstin?: string;
  [key: string]: any;
}

interface Segment {
  id: number;
  segment_name: string;
  company_id?: number;
}

interface Vendor {
  id: number;
  vendor_name: string;
  vendor_code?: string;
  gst_number?: string;
  gst_type?: string;
  state?: string;
  city?: string;
  phone?: string;
  email?: string;
  display_label?: string;
  [key: string]: any;
}

interface StockItem {
  id: number | string;
  item_name: string;
  item_code?: string;
  sku?: string;
  purchase_rate?: number;
  cost_price?: number;
  selling_rate?: number;
  hsn_code?: string;
  hsn_id?: number;
  unit_of_measure?: string;
  uom?: string;
  brand?: string;
  model_compat?: string;
  specification?: string;
  hsn?: any;
  [key: string]: any;
}

interface HsnCode {
  id: number;
  hsn_code: string;
  description?: string;
  cgst_rate?: number;
  sgst_rate?: number;
  igst_rate?: number;
  cess_rate?: number;
  effective_from?: string;
  effective_to?: string;
  is_active?: boolean;
}

interface PurchaseLineItem {
  id?: number;
  line_number?: number;
  stock_item_id?: number | null;
  item_description?: string;
  item_code?: string;
  hsn_code?: string;
  hsn_id?: number | null;
  quantity: number;
  rate: number;
  amount: number;
  gst_rate: number;
  cgst_rate?: number;
  sgst_rate?: number;
  igst_rate?: number;
  cgst_amount?: number;
  sgst_amount?: number;
  igst_amount?: number;
  tax_amount?: number;
  total_amount?: number;
  serial_numbers?: string;
  unit_of_measure?: string;
}

interface PurchaseUpload {
  id: number;
  upload_number: string;
  voucher_number?: string;
  company_id: number;
  company_name?: string;
  vendor_id?: number;
  vendor_name?: string;
  segment_id?: number | null;
  vendor_invoice_no?: string;
  vendor_invoice_date?: string;
  uploaded_at?: string;
  status: "UPLOADED" | "EXTRACTING" | "EXTRACTED" | "REVIEWED" | "CONFIRMED" | "PROCESSED" | "REJECTED" | "VOIDED" | "CANCELLED";
  document_type?: string;
  is_credit_purchase?: boolean;
  credit_days?: number;
  due_date?: string;
  taxable_amount?: number;
  total_tax?: number;
  grand_total?: number;
  round_off?: number;
  is_igst?: boolean;
  courier_amount?: number;
  courier_hsn_code?: string;
  courier_hsn_id?: number;
  courier_gst_rate?: number;
  courier_cgst_amount?: number;
  courier_sgst_amount?: number;
  courier_igst_amount?: number;
  courier_is_inclusive?: boolean;
  transport_amount?: number;
  transport_hsn_code?: string;
  transport_hsn_id?: number;
  transport_gst_rate?: number;
  transport_cgst_amount?: number;
  transport_sgst_amount?: number;
  transport_igst_amount?: number;
  transport_is_inclusive?: boolean;
  review_notes?: string;
  file_path?: string;
  original_filename?: string;
  track_physical_receipt?: boolean;
  void_reason?: string;
  voided_by_name?: string;
  voided_by_id?: number;
  voided_at?: string;
  line_items?: PurchaseLineItem[];
  extracted_data?: any;
}

interface NarrationLog {
  id?: number;
  narration: string;
  created_by_name?: string;
  created_at?: string;
}

interface PendingReceiptLine {
  id: number;
  line_number: number;
  item_description: string;
  item_code?: string;
  unit_of_measure: string;
  hsn_code?: string;
  unit_rate: number;
  ordered_qty: number;
  configured_pending_qty: number;
  received_qty: number;
  pending_qty: number;
}

interface PendingReceiptExtraItem {
  id: number;
  item_description: string;
  item_code?: string;
  unit_of_measure: string;
  pending_qty: number;
  received_qty: number;
  remaining_qty: number;
  notes?: string;
}

interface PendingReceiptInvoice {
  id: number;
  upload_number: string;
  vendor_name: string;
  vendor_invoice_no?: string;
  vendor_invoice_date?: string;
  total_pending_qty: number;
  total_pending_value: number;
  lines: PendingReceiptLine[];
  extra_items?: PendingReceiptExtraItem[];
}

export default function PurchaseInvoicesPage() {
  const { user, token } = useStaffAuth();

  // Navigation Tabs
  const [activeTab, setActiveTab] = useState<"invoices" | "pending" | "summary">("invoices");

  // Master Data
  const [companies, setCompanies] = useState<Company[]>([]);
  const [vendors, setVendors] = useState<Vendor[]>([]);
  const [stockItems, setStockItems] = useState<StockItem[]>([]);
  const [hsnCodes, setHsnCodes] = useState<HsnCode[]>([]);
  const [segments, setSegments] = useState<Segment[]>([]);

  // Filter States
  const [selectedCompanyId, setSelectedCompanyId] = useState<string>("");
  const [filterStatus, setFilterStatus] = useState<string>("");
  const [filterVendorId, setFilterVendorId] = useState<string>("");
  const [filterVendorSearch, setFilterVendorSearch] = useState<string>("");
  const [filterFromDate, setFilterFromDate] = useState<string>("");
  const [filterToDate, setFilterToDate] = useState<string>("");
  const [activePeriod, setActivePeriod] = useState<string>("month");

  // Pagination & List State
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [pageSize, setPageSize] = useState<number>(50);
  const [totalRecords, setTotalRecords] = useState<number>(0);
  const [totalPages, setTotalPages] = useState<number>(1);
  const [invoices, setInvoices] = useState<PurchaseUpload[]>([]);
  const [loadingInvoices, setLoadingInvoices] = useState<boolean>(false);
  const [stats, setStats] = useState({
    uploaded: 0,
    pending_review: 0,
    confirmed: 0,
    rejected: 0,
    voided: 0,
    total_confirmed_value: 0
  });

  // Selected invoice for View / Review / Confirm / Reject
  const [selectedInvoice, setSelectedInvoice] = useState<PurchaseUpload | null>(null);

  // Modals
  const [isUploadModalOpen, setIsUploadModalOpen] = useState<boolean>(false);
  const [isReviewModalOpen, setIsReviewModalOpen] = useState<boolean>(false);
  const [isViewModalOpen, setIsViewModalOpen] = useState<boolean>(false);
  const [isManualModalOpen, setIsManualModalOpen] = useState<boolean>(false);
  const [isRejectModalOpen, setIsRejectModalOpen] = useState<boolean>(false);
  const [isAddPendingModalOpen, setIsAddPendingModalOpen] = useState<boolean>(false);
  const [isPdfModalOpen, setIsPdfModalOpen] = useState<boolean>(false);

  // Quick Create Modals
  const [isQcVendorOpen, setIsQcVendorOpen] = useState<boolean>(false);
  const [isQcStockOpen, setIsQcStockOpen] = useState<boolean>(false);
  const [isQcHsnOpen, setIsQcHsnOpen] = useState<boolean>(false);

  // PDF Viewer State
  const [pdfBlobUrl, setPdfBlobUrl] = useState<string | null>(null);
  const [pdfFilename, setPdfFilename] = useState<string>("");
  const [pdfTitle, setPdfTitle] = useState<string>("");

  // Role Permissions
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

  // -------------------------------------------------------------
  // INITIALIZATION & MASTER DATA
  // -------------------------------------------------------------
  useEffect(() => {
    const savedCompany = typeof window !== "undefined" ? localStorage.getItem("sfms_selected_company") : null;
    if (savedCompany) setSelectedCompanyId(savedCompany);

    handleSetPeriod("month");
    fetchCompanies();
    fetchVendors();
    fetchStockItems();
    fetchHsnCodes();
  }, [token]);

  useEffect(() => {
    if (selectedCompanyId) {
      localStorage.setItem("sfms_selected_company", selectedCompanyId);
      fetchSegments(selectedCompanyId);
      setCurrentPage(1);
      loadInvoices(1);
      if (activeTab === "pending") loadPendingReceipt();
      if (activeTab === "summary") loadPurchaseSummary();
    } else {
      setInvoices([]);
    }
  }, [selectedCompanyId, filterStatus, filterVendorId, filterFromDate, filterToDate]);

  const fetchCompanies = async () => {
    try {
      const res = await api.get("/staff/accounts/companies");
      const list = res.data.companies || res.data || [];
      setCompanies(list);
      if (!selectedCompanyId && list.length > 0) {
        const saved = localStorage.getItem("sfms_selected_company");
        const match = list.find((c: any) => String(c.id) === String(saved));
        setSelectedCompanyId(match ? String(match.id) : String(list[0].id));
      }
    } catch (err) {
      console.error("Error fetching companies:", err);
    }
  };

  const fetchVendors = async () => {
    try {
      const res = await api.get("/staff/accounts/vendors?page_size=500&is_active=true");
      const list = (res.data.vendors || []).map((v: any) => ({
        ...v,
        display_label: v.vendor_code ? `${v.vendor_code} - ${v.vendor_name}` : v.vendor_name
      }));
      setVendors(list);
    } catch (err) {
      console.error("Error fetching vendors:", err);
    }
  };

  const fetchStockItems = async () => {
    try {
      const res = await api.get("/staff/accounts/stock-items?page_size=2000&is_active=true&include_summary=false");
      const list = res.data.stock_items || res.data.items || [];
      setStockItems(list);
    } catch (err) {
      console.error("Error fetching stock items:", err);
    }
  };

  const fetchHsnCodes = async () => {
    try {
      const res = await api.get("/staff/accounts/hsn?page_size=200&is_active=true");
      setHsnCodes(res.data.hsn_codes || []);
    } catch (err) {
      console.error("Error fetching HSN codes:", err);
    }
  };

  const fetchSegments = async (companyId: string) => {
    try {
      const res = await api.get(`/staff/accounts/segments?company_id=${companyId}`);
      setSegments(res.data.segments || []);
    } catch (err) {
      console.error("Error fetching segments:", err);
    }
  };

  // Period Date Range Helper
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
  // INVOICES LIST LOADER
  // -------------------------------------------------------------
  const loadInvoices = async (pageToLoad = currentPage) => {
    setLoadingInvoices(true);
    try {
      const params = new URLSearchParams();
      if (selectedCompanyId) params.append("company_id", selectedCompanyId);
      if (filterStatus) params.append("status", filterStatus);
      if (filterVendorId) params.append("vendor_id", filterVendorId);
      if (filterFromDate) params.append("from_date", filterFromDate);
      if (filterToDate) params.append("to_date", filterToDate);
      params.append("page", String(pageToLoad));
      params.append("page_size", String(pageSize));

      const res = await api.get(`/staff/accounts/purchase-uploads?${params.toString()}`);
      const data = res.data;
      setInvoices(data.uploads || []);
      setTotalRecords(data.total || 0);
      setTotalPages(Math.ceil((data.total || 0) / (data.page_size || pageSize)) || 1);
      setCurrentPage(data.page || pageToLoad);

      if (data.stats) {
        setStats({
          uploaded: data.stats.uploaded ?? 0,
          pending_review: data.stats.pending_review ?? 0,
          confirmed: data.stats.confirmed ?? 0,
          rejected: data.stats.rejected ?? 0,
          voided: data.stats.voided ?? 0,
          total_confirmed_value: data.stats.total_confirmed_value ?? 0
        });
      }
    } catch (err: any) {
      console.error("Error loading purchase invoices:", err);
      toast.error(err.response?.data?.detail || "Failed to load purchase invoices");
    } finally {
      setLoadingInvoices(false);
    }
  };

  const handlePageChange = (newPage: number) => {
    if (newPage < 1 || newPage > totalPages) return;
    setCurrentPage(newPage);
    loadInvoices(newPage);
  };

  // -------------------------------------------------------------
  // UPLOAD INVOICE FORM STATE & SUBMISSION
  // -------------------------------------------------------------
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploadCompanyId, setUploadCompanyId] = useState<string>("");
  const [uploadSegmentId, setUploadSegmentId] = useState<string>("");
  const [uploadVendorId, setUploadVendorId] = useState<string>("");
  const [uploadVendorSearch, setUploadVendorSearch] = useState<string>("");
  const [uploadInvoiceNo, setUploadInvoiceNo] = useState<string>("");
  const [uploadInvoiceDate, setUploadInvoiceDate] = useState<string>("");
  const [uploadCreditPurchase, setUploadCreditPurchase] = useState<boolean>(false);
  const [uploadCreditDays, setUploadCreditDays] = useState<number>(30);
  const [uploadDueDate, setUploadDueDate] = useState<string>("");
  const [uploading, setUploading] = useState<boolean>(false);

  const handleOpenUploadModal = () => {
    setUploadFile(null);
    setUploadCompanyId(selectedCompanyId || (companies[0]?.id ? String(companies[0].id) : ""));
    setUploadSegmentId("");
    setUploadVendorId("");
    setUploadVendorSearch("");
    setUploadInvoiceNo("");
    setUploadInvoiceDate("");
    setUploadCreditPurchase(false);
    setUploadCreditDays(30);
    setUploadDueDate("");
    setIsUploadModalOpen(true);
  };

  const handleUploadSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!uploadCompanyId) {
      toast.error("Please select a company");
      return;
    }
    if (!uploadFile) {
      toast.error("Please select an invoice file to upload");
      return;
    }

    setUploading(true);
    try {
      const formData = new FormData();
      formData.append("file", uploadFile);
      formData.append("company_id", uploadCompanyId);
      if (uploadVendorId) formData.append("vendor_id", uploadVendorId);
      if (uploadSegmentId) formData.append("segment_id", uploadSegmentId);
      if (uploadInvoiceNo) formData.append("vendor_invoice_no", uploadInvoiceNo);
      if (uploadInvoiceDate) formData.append("vendor_invoice_date", uploadInvoiceDate);
      formData.append("is_credit_purchase", String(uploadCreditPurchase));
      if (uploadCreditPurchase) {
        formData.append("credit_days", String(uploadCreditDays));
        if (uploadDueDate) formData.append("due_date", uploadDueDate);
      }

      const res = await api.post("/staff/accounts/purchase-uploads", formData, {
        headers: { "Content-Type": "multipart/form-data" }
      });

      toast.success("Invoice uploaded successfully!");
      setIsUploadModalOpen(false);
      loadInvoices();

      if (res.data.upload?.id) {
        handleOpenReviewModal(res.data.upload.id);
      }
    } catch (err: any) {
      console.error("Upload error:", err);
      toast.error(err.response?.data?.detail || err.response?.data?.message || "Failed to upload invoice");
    } finally {
      setUploading(false);
    }
  };

  // -------------------------------------------------------------
  // REVIEW & CONFIRM MODAL STATE & ACTIONS
  // -------------------------------------------------------------
  const [reviewId, setReviewId] = useState<number | null>(null);
  const [reviewUploadNumber, setReviewUploadNumber] = useState<string>("");
  const [reviewCompanyId, setReviewCompanyId] = useState<number | null>(null);
  const [reviewCompanyName, setReviewCompanyName] = useState<string>("");
  const [reviewVendorId, setReviewVendorId] = useState<string>("");
  const [reviewVendorSearch, setReviewVendorSearch] = useState<string>("");
  const [reviewInvoiceNo, setReviewInvoiceNo] = useState<string>("");
  const [reviewInvoiceDate, setReviewInvoiceDate] = useState<string>("");
  const [reviewDueDate, setReviewDueDate] = useState<string>("");
  const [reviewNotes, setReviewNotes] = useState<string>("");
  const [reviewIsIgst, setReviewIsIgst] = useState<boolean>(false);
  const [reviewLineItems, setReviewLineItems] = useState<PurchaseLineItem[]>([]);
  const [reviewCourierAmount, setReviewCourierAmount] = useState<number>(0);
  const [reviewCourierHsnCode, setReviewCourierHsnCode] = useState<string>("");
  const [reviewCourierHsnId, setReviewCourierHsnId] = useState<number | null>(null);
  const [reviewCourierGstRate, setReviewCourierGstRate] = useState<number>(0);
  const [reviewCourierInclusive, setReviewCourierInclusive] = useState<boolean>(true);
  const [reviewTransportAmount, setReviewTransportAmount] = useState<number>(0);
  const [reviewTransportHsnCode, setReviewTransportHsnCode] = useState<string>("");
  const [reviewTransportHsnId, setReviewTransportHsnId] = useState<number | null>(null);
  const [reviewTransportGstRate, setReviewTransportGstRate] = useState<number>(0);
  const [reviewTransportInclusive, setReviewTransportInclusive] = useState<boolean>(true);
  const [reviewRoundOff, setReviewRoundOff] = useState<number>(0);
  const [reviewMatchingStatus, setReviewMatchingStatus] = useState<any>(null);
  const [reviewNarrations, setReviewNarrations] = useState<NarrationLog[]>([]);
  const [savingReview, setSavingReview] = useState<boolean>(false);
  const [confirmingReview, setConfirmingReview] = useState<boolean>(false);

  const handleOpenReviewModal = async (id: number) => {
    try {
      const res = await api.get(`/staff/accounts/purchase-uploads/${id}`);
      const inv: PurchaseUpload = res.data.upload;
      setSelectedInvoice(inv);
      setReviewId(inv.id);
      setReviewUploadNumber(inv.upload_number);
      setReviewCompanyId(inv.company_id);
      setReviewCompanyName(inv.company_name || companies.find(c => c.id === inv.company_id)?.company_name || "Company");
      setReviewVendorId(inv.vendor_id ? String(inv.vendor_id) : "");

      const vendorMatch = vendors.find(v => v.id === inv.vendor_id);
      setReviewVendorSearch(vendorMatch ? vendorMatch.display_label || vendorMatch.vendor_name : "");

      const isIgstVal = (vendorMatch?.gst_type === "IGST" || inv.is_igst) ? true : false;
      setReviewIsIgst(isIgstVal);

      setReviewInvoiceNo(inv.vendor_invoice_no || "");
      setReviewInvoiceDate(inv.vendor_invoice_date ? inv.vendor_invoice_date.split("T")[0] : "");
      setReviewDueDate(inv.due_date ? inv.due_date.split("T")[0] : "");
      setReviewNotes(inv.review_notes || "");

      setReviewCourierAmount(inv.courier_amount || 0);
      setReviewCourierHsnCode(inv.courier_hsn_code || "");
      setReviewCourierHsnId(inv.courier_hsn_id || null);
      setReviewCourierGstRate(inv.courier_gst_rate || 0);
      setReviewCourierInclusive(inv.courier_is_inclusive !== false);

      setReviewTransportAmount(inv.transport_amount || 0);
      setReviewTransportHsnCode(inv.transport_hsn_code || "");
      setReviewTransportHsnId(inv.transport_hsn_id || null);
      setReviewTransportGstRate(inv.transport_gst_rate || 0);
      setReviewTransportInclusive(inv.transport_is_inclusive !== false);

      setReviewRoundOff(inv.round_off || 0);
      setReviewMatchingStatus(inv.extracted_data?.matching_status || null);

      const mappedLines: PurchaseLineItem[] = (inv.line_items || []).map((li, idx) => ({
        id: li.id,
        line_number: li.line_number || idx + 1,
        stock_item_id: li.stock_item_id || null,
        item_description: li.item_description || "",
        item_code: li.item_code || "",
        hsn_code: li.hsn_code || "",
        hsn_id: li.hsn_id || null,
        quantity: li.quantity || 1,
        rate: li.rate || 0,
        amount: li.amount || (li.quantity || 1) * (li.rate || 0),
        gst_rate: li.gst_rate || 0,
        cgst_rate: (li.gst_rate || 0) / 2,
        sgst_rate: (li.gst_rate || 0) / 2,
        igst_rate: li.gst_rate || 0,
        tax_amount: li.tax_amount || ((li.amount || (li.quantity || 1) * (li.rate || 0)) * (li.gst_rate || 0)) / 100,
        total_amount: li.total_amount || 0,
        serial_numbers: Array.isArray(li.serial_numbers) ? li.serial_numbers.join(", ") : (li.serial_numbers || "")
      }));

      if (mappedLines.length === 0) {
        mappedLines.push({
          line_number: 1,
          stock_item_id: null,
          item_description: "",
          hsn_code: "",
          hsn_id: null,
          quantity: 1,
          rate: 0,
          amount: 0,
          gst_rate: 0,
          tax_amount: 0,
          total_amount: 0,
          serial_numbers: ""
        });
      }
      setReviewLineItems(mappedLines);

      fetchNarrations(inv.id);
      setIsReviewModalOpen(true);
    } catch (err: any) {
      console.error("Error loading invoice for review:", err);
      toast.error(err.response?.data?.detail || "Failed to load invoice details");
    }
  };

  const fetchNarrations = async (invoiceId: number) => {
    try {
      const res = await api.get(`/staff/accounts/invoice-narration-log?invoice_type=PURCHASE&invoice_id=${invoiceId}`);
      if (res.data.success) {
        setReviewNarrations(res.data.entries || []);
      }
    } catch (err) {
      console.warn("Failed to load narrations:", err);
    }
  };

  const handleAddNarration = async (context: "review" | "view" | "manual", invId: number | null, text: string) => {
    if (!invId) {
      toast.error("Please save the invoice first before logging a narration");
      return;
    }
    if (!text.trim()) {
      toast.error("Please enter narration text");
      return;
    }
    try {
      const res = await api.post("/staff/accounts/invoice-narration-log", {
        invoice_type: "PURCHASE",
        invoice_id: invId,
        company_id: selectedCompanyId ? parseInt(selectedCompanyId) : reviewCompanyId,
        narration: text.trim()
      });
      if (res.data.success) {
        toast.success("Narration entry added");
        fetchNarrations(invId);
      }
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Failed to add narration entry");
    }
  };

  // Review Line Item Operations
  const handleReviewLineChange = (index: number, field: keyof PurchaseLineItem, value: any) => {
    setReviewLineItems(prev => {
      const updated = [...prev];
      const row = { ...updated[index], [field]: value };

      if (field === "quantity" || field === "rate" || field === "gst_rate") {
        const qty = parseFloat(String(row.quantity)) || 0;
        const rate = parseFloat(String(row.rate)) || 0;
        const gstRate = parseFloat(String(row.gst_rate)) || 0;
        const amount = qty * rate;
        const taxAmount = amount * (gstRate / 100);
        row.amount = parseFloat(amount.toFixed(2));
        row.tax_amount = parseFloat(taxAmount.toFixed(2));
        row.total_amount = parseFloat((amount + taxAmount).toFixed(2));
      }
      updated[index] = row;
      return updated;
    });
  };

  const handleAddReviewLine = () => {
    setReviewLineItems(prev => [
      ...prev,
      {
        line_number: prev.length + 1,
        stock_item_id: null,
        item_description: "",
        hsn_code: "",
        hsn_id: null,
        quantity: 1,
        rate: 0,
        amount: 0,
        gst_rate: 0,
        tax_amount: 0,
        total_amount: 0,
        serial_numbers: ""
      }
    ]);
  };

  const handleRemoveReviewLine = (index: number) => {
    if (reviewLineItems.length <= 1) return;
    setReviewLineItems(prev => prev.filter((_, i) => i !== index));
  };

  // Review Modal Calculated Totals
  const reviewCalculations = useMemo(() => {
    let taxable = 0;
    let totalTax = 0;

    reviewLineItems.forEach(li => {
      taxable += Number(li.amount || 0);
      totalTax += Number(li.tax_amount || 0);
    });

    const courierGst = (reviewCourierAmount * reviewCourierGstRate) / 100;
    const transportGst = (reviewTransportAmount * reviewTransportGstRate) / 100;

    const rawGrandTotal = taxable + totalTax + reviewCourierAmount + courierGst + reviewTransportAmount + transportGst + reviewRoundOff;

    return {
      taxable,
      totalTax,
      cgst: reviewIsIgst ? 0 : totalTax / 2,
      sgst: reviewIsIgst ? 0 : totalTax / 2,
      igst: reviewIsIgst ? totalTax : 0,
      courierGst,
      transportGst,
      grandTotal: rawGrandTotal
    };
  }, [
    reviewLineItems,
    reviewCourierAmount,
    reviewCourierGstRate,
    reviewTransportAmount,
    reviewTransportGstRate,
    reviewRoundOff,
    reviewIsIgst
  ]);

  const handleAutoCalcRoundOff = () => {
    const withoutRound = reviewCalculations.taxable + reviewCalculations.totalTax + reviewCourierAmount + reviewCalculations.courierGst + reviewTransportAmount + reviewCalculations.transportGst;
    const rounded = Math.round(withoutRound);
    const diff = rounded - withoutRound;
    setReviewRoundOff(parseFloat(diff.toFixed(2)));
  };

  // Save Review (Draft)
  const handleSaveReview = async () => {
    if (!reviewId) return;
    if (!reviewInvoiceNo.trim() || !reviewInvoiceDate) {
      toast.error("Invoice number and date are required");
      return;
    }

    setSavingReview(true);
    try {
      const payload = {
        vendor_id: reviewVendorId ? parseInt(reviewVendorId) : null,
        vendor_invoice_no: reviewInvoiceNo.trim(),
        vendor_invoice_date: reviewInvoiceDate,
        due_date: reviewDueDate || null,
        review_notes: reviewNotes,
        round_off: reviewRoundOff,
        courier_amount: reviewCourierAmount,
        courier_hsn_code: reviewCourierHsnCode || null,
        courier_hsn_id: reviewCourierHsnId,
        courier_is_inclusive: reviewCourierInclusive,
        courier_gst_rate: reviewCourierGstRate,
        courier_cgst_amount: reviewIsIgst ? 0 : reviewCalculations.courierGst / 2,
        courier_sgst_amount: reviewIsIgst ? 0 : reviewCalculations.courierGst / 2,
        courier_igst_amount: reviewIsIgst ? reviewCalculations.courierGst : 0,
        transport_amount: reviewTransportAmount,
        transport_hsn_code: reviewTransportHsnCode || null,
        transport_hsn_id: reviewTransportHsnId,
        transport_is_inclusive: reviewTransportInclusive,
        transport_gst_rate: reviewTransportGstRate,
        transport_cgst_amount: reviewIsIgst ? 0 : reviewCalculations.transportGst / 2,
        transport_sgst_amount: reviewIsIgst ? 0 : reviewCalculations.transportGst / 2,
        transport_igst_amount: reviewIsIgst ? reviewCalculations.transportGst : 0,
        line_items: reviewLineItems.map((li, idx) => ({
          line_number: idx + 1,
          stock_item_id: li.stock_item_id || null,
          item_description: li.item_description,
          hsn_code: li.hsn_code || "",
          hsn_id: li.hsn_id || null,
          quantity: li.quantity,
          rate: li.rate,
          amount: li.amount,
          gst_rate: li.gst_rate,
          tax_amount: li.tax_amount,
          total_amount: li.total_amount,
          serial_numbers: li.serial_numbers || ""
        }))
      };

      await api.put(`/staff/accounts/purchase-uploads/${reviewId}`, payload);
      toast.success("Invoice changes saved successfully");
      setIsReviewModalOpen(false);
      loadInvoices();
    } catch (err: any) {
      console.error("Save review error:", err);
      toast.error(err.response?.data?.detail || "Failed to save invoice changes");
    } finally {
      setSavingReview(false);
    }
  };

  // Confirm Invoice
  const handleConfirmInvoice = async () => {
    if (!reviewId) return;
    if (!reviewVendorId) {
      toast.error("Please select or create a vendor before confirmation");
      return;
    }
    if (!reviewInvoiceNo.trim() || !reviewInvoiceDate) {
      toast.error("Invoice number and date are required");
      return;
    }
    if (reviewLineItems.length === 0) {
      toast.error("Please add at least one line item");
      return;
    }

    setConfirmingReview(true);
    try {
      const dupCheck = await api.post("/staff/accounts/purchase-uploads/check-duplicate", {
        company_id: reviewCompanyId,
        vendor_id: parseInt(reviewVendorId),
        vendor_invoice_no: reviewInvoiceNo.trim(),
        vendor_invoice_date: reviewInvoiceDate,
        exclude_upload_id: reviewId
      });
      if (dupCheck.data.is_duplicate) {
        toast.error(`Duplicate invoice detected: "${reviewInvoiceNo}" is already confirmed.`);
        setConfirmingReview(false);
        return;
      }

      const payload = {
        vendor_id: parseInt(reviewVendorId),
        vendor_invoice_no: reviewInvoiceNo.trim(),
        vendor_invoice_date: reviewInvoiceDate,
        due_date: reviewDueDate || null,
        review_notes: reviewNotes,
        round_off: reviewRoundOff,
        courier_amount: reviewCourierAmount,
        courier_hsn_code: reviewCourierHsnCode || null,
        courier_hsn_id: reviewCourierHsnId,
        courier_is_inclusive: reviewCourierInclusive,
        courier_gst_rate: reviewCourierGstRate,
        courier_cgst_amount: reviewIsIgst ? 0 : reviewCalculations.courierGst / 2,
        courier_sgst_amount: reviewIsIgst ? 0 : reviewCalculations.courierGst / 2,
        courier_igst_amount: reviewIsIgst ? reviewCalculations.courierGst : 0,
        transport_amount: reviewTransportAmount,
        transport_hsn_code: reviewTransportHsnCode || null,
        transport_hsn_id: reviewTransportHsnId,
        transport_is_inclusive: reviewTransportInclusive,
        transport_gst_rate: reviewTransportGstRate,
        transport_cgst_amount: reviewIsIgst ? 0 : reviewCalculations.transportGst / 2,
        transport_sgst_amount: reviewIsIgst ? 0 : reviewCalculations.transportGst / 2,
        transport_igst_amount: reviewIsIgst ? reviewCalculations.transportGst : 0,
        line_items: reviewLineItems.map((li, idx) => ({
          line_number: idx + 1,
          stock_item_id: li.stock_item_id || null,
          item_description: li.item_description,
          hsn_code: li.hsn_code || "",
          hsn_id: li.hsn_id || null,
          quantity: li.quantity,
          rate: li.rate,
          amount: li.amount,
          gst_rate: li.gst_rate,
          tax_amount: li.tax_amount,
          total_amount: li.total_amount,
          serial_numbers: li.serial_numbers || ""
        }))
      };

      await api.put(`/staff/accounts/purchase-uploads/${reviewId}`, payload);
      await api.post(`/staff/accounts/purchase-uploads/${reviewId}/confirm`);
      toast.success("Purchase Invoice confirmed! Stock Ledger, AP, and Party Ledger updated.");
      setIsReviewModalOpen(false);
      loadInvoices();
    } catch (err: any) {
      console.error("Confirm error:", err);
      toast.error(err.response?.data?.detail || err.response?.data?.message || "Failed to confirm invoice");
    } finally {
      setConfirmingReview(false);
    }
  };

  // Re-confirm Invoice
  const handleReconfirmInvoice = async (id: number) => {
    if (!confirm("Re-confirming will reverse the previous stock ledger, AP, and party ledger entries and recreate fresh ones based on current data. Proceed?")) return;
    try {
      await api.post(`/staff/accounts/purchase-uploads/${id}/confirm`, {});
      toast.success("Invoice re-confirmed successfully!");
      loadInvoices();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Failed to re-confirm invoice");
    }
  };

  // Void Invoice
  const handleVoidInvoice = async (id: number, uploadNumber: string) => {
    const reason = prompt(`Void invoice ${uploadNumber}?\n\nThis will PERMANENTLY REVERSE all stock, ledger, and AP entries.\nEnter void reason (required):`);
    if (!reason || reason.trim().length < 5) {
      if (reason !== null) toast.error("Void reason must be at least 5 characters");
      return;
    }

    try {
      const res = await api.post(`/staff/accounts/purchase-uploads/${id}/void`, { reason: reason.trim() });
      if (res.data.success) {
        toast.success(`Invoice ${uploadNumber} voided successfully`);
        loadInvoices();
      }
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Failed to void invoice");
    }
  };

  // Post Again
  const handlePostAgain = async (id: number) => {
    if (!confirm("Post Again: This will re-confirm the voided invoice and recreate all stock and ledger entries. Proceed?")) return;
    try {
      const res = await api.post(`/staff/accounts/purchase-uploads/${id}/confirm`, {});
      if (res.data.success) {
        toast.success("Invoice re-confirmed and entries recreated!");
        loadInvoices();
      }
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Failed to post invoice again");
    }
  };

  // Toggle Physical Receipt Tracking
  const handleToggleReceiptTracking = async (id: number, enable: boolean) => {
    try {
      const res = await api.post(`/staff/accounts/purchase-invoices/${id}/toggle-receipt-tracking`, { enable });
      if (res.data.success) {
        toast.success(enable ? "Invoice added to Pending Receipt tracking" : "Invoice removed from Pending Receipt tracking");
        loadInvoices();
      }
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Failed to update tracking");
    }
  };

  // Delete Invoice
  const handleDeleteInvoice = async (id: number, uploadNumber: string) => {
    if (!confirm(`Are you sure you want to delete invoice ${uploadNumber}? This action cannot be undone.`)) return;
    try {
      await api.delete(`/staff/accounts/purchase-uploads/${id}`);
      toast.success(`Invoice ${uploadNumber} deleted`);
      loadInvoices();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Failed to delete invoice");
    }
  };

  // Download Purchase PDF
  const handleDownloadPdf = async (uploadId: number, companyId?: number) => {
    const cid = companyId || selectedCompanyId;
    try {
      const res = await api.get(`/staff/accounts/purchase-uploads/${uploadId}/pdf?company_id=${cid}`, {
        responseType: "blob"
      });
      const blob = new Blob([res.data], { type: "application/pdf" });
      const url = URL.createObjectURL(blob);
      const filename = `purchase-${uploadId}.pdf`;
      setPdfBlobUrl(url);
      setPdfFilename(filename);
      setPdfTitle(`Purchase Document - #${uploadId}`);
      setIsPdfModalOpen(true);
    } catch (err: any) {
      toast.error("Failed to generate PDF");
    }
  };

  // -------------------------------------------------------------
  // VIEW INVOICE MODAL
  // -------------------------------------------------------------
  const [viewInvoiceData, setViewInvoiceData] = useState<PurchaseUpload | null>(null);
  const [viewNarrations, setViewNarrations] = useState<NarrationLog[]>([]);

  const handleOpenViewModal = async (id: number) => {
    try {
      const res = await api.get(`/staff/accounts/purchase-uploads/${id}`);
      const inv = res.data.upload;
      setViewInvoiceData(inv);
      setIsViewModalOpen(true);

      const narrRes = await api.get(`/staff/accounts/invoice-narration-log?invoice_type=PURCHASE&invoice_id=${id}`);
      if (narrRes.data.success) {
        setViewNarrations(narrRes.data.entries || []);
      }
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Failed to load invoice details");
    }
  };

  // -------------------------------------------------------------
  // MANUAL ENTRY MODAL STATE & ACTIONS
  // -------------------------------------------------------------
  const [manualDocType, setManualDocType] = useState<"invoice" | "purchase_return">("invoice");
  const [manualReturnRef, setManualReturnRef] = useState<string>("");
  const [manualCompanyId, setManualCompanyId] = useState<string>("");
  const [manualSegmentId, setManualSegmentId] = useState<string>("");
  const [manualVendorId, setManualVendorId] = useState<string>("");
  const [manualVendorSearch, setManualVendorSearch] = useState<string>("");
  const [manualInvoiceNo, setManualInvoiceNo] = useState<string>("");
  const [manualInvoiceDate, setManualInvoiceDate] = useState<string>(new Date().toISOString().split("T")[0]);
  const [manualDueDate, setManualDueDate] = useState<string>("");
  const [manualCreditPurchase, setManualCreditPurchase] = useState<boolean>(false);
  const [manualCreditDays, setManualCreditDays] = useState<number>(30);
  const [manualNotes, setManualNotes] = useState<string>("");
  const [manualGstType, setManualGstType] = useState<"CGST_SGST" | "IGST">("CGST_SGST");
  const [manualLineItems, setManualLineItems] = useState<PurchaseLineItem[]>([
    {
      line_number: 1,
      stock_item_id: null,
      item_description: "",
      hsn_code: "",
      hsn_id: null,
      quantity: 1,
      rate: 0,
      amount: 0,
      gst_rate: 0,
      cgst_rate: 0,
      sgst_rate: 0,
      igst_rate: 0,
      cgst_amount: 0,
      sgst_amount: 0,
      igst_amount: 0,
      tax_amount: 0,
      total_amount: 0,
      serial_numbers: ""
    }
  ]);
  const [manualRounding, setManualRounding] = useState<number>(0);
  const [savingManual, setSavingManual] = useState<boolean>(false);

  const handleOpenManualModal = () => {
    setManualDocType("invoice");
    setManualReturnRef("");
    setManualCompanyId(selectedCompanyId || (companies[0]?.id ? String(companies[0].id) : ""));
    setManualSegmentId("");
    setManualVendorId("");
    setManualVendorSearch("");
    setManualInvoiceNo("");
    setManualInvoiceDate(new Date().toISOString().split("T")[0]);
    setManualDueDate("");
    setManualCreditPurchase(false);
    setManualCreditDays(30);
    setManualNotes("");
    setManualGstType("CGST_SGST");
    setManualRounding(0);
    setManualLineItems([
      {
        line_number: 1,
        stock_item_id: null,
        item_description: "",
        hsn_code: "",
        hsn_id: null,
        quantity: 1,
        rate: 0,
        amount: 0,
        gst_rate: 0,
        cgst_rate: 0,
        sgst_rate: 0,
        igst_rate: 0,
        cgst_amount: 0,
        sgst_amount: 0,
        igst_amount: 0,
        tax_amount: 0,
        total_amount: 0,
        serial_numbers: ""
      }
    ]);
    setIsManualModalOpen(true);
  };

  const handleManualLineChange = (index: number, field: keyof PurchaseLineItem, value: any) => {
    setManualLineItems(prev => {
      const updated = [...prev];
      const row = { ...updated[index], [field]: value };

      if (field === "quantity" || field === "rate" || field === "gst_rate") {
        const qty = parseFloat(String(row.quantity)) || 0;
        const rate = parseFloat(String(row.rate)) || 0;
        const gstRate = parseFloat(String(row.gst_rate)) || 0;
        const amount = qty * rate;
        const isIgst = manualGstType === "IGST";
        const taxAmount = amount * (gstRate / 100);

        row.amount = parseFloat(amount.toFixed(2));
        row.gst_rate = gstRate;
        row.cgst_rate = isIgst ? 0 : gstRate / 2;
        row.sgst_rate = isIgst ? 0 : gstRate / 2;
        row.igst_rate = isIgst ? gstRate : 0;
        row.cgst_amount = isIgst ? 0 : parseFloat((taxAmount / 2).toFixed(2));
        row.sgst_amount = isIgst ? 0 : parseFloat((taxAmount / 2).toFixed(2));
        row.igst_amount = isIgst ? parseFloat(taxAmount.toFixed(2)) : 0;
        row.tax_amount = parseFloat(taxAmount.toFixed(2));
        row.total_amount = parseFloat((amount + taxAmount).toFixed(2));
      }
      updated[index] = row;
      return updated;
    });
  };

  const handleAddManualLine = () => {
    setManualLineItems(prev => [
      ...prev,
      {
        line_number: prev.length + 1,
        stock_item_id: null,
        item_description: "",
        hsn_code: "",
        hsn_id: null,
        quantity: 1,
        rate: 0,
        amount: 0,
        gst_rate: 0,
        cgst_rate: 0,
        sgst_rate: 0,
        igst_rate: 0,
        cgst_amount: 0,
        sgst_amount: 0,
        igst_amount: 0,
        tax_amount: 0,
        total_amount: 0,
        serial_numbers: ""
      }
    ]);
  };

  const handleRemoveManualLine = (index: number) => {
    if (manualLineItems.length <= 1) return;
    setManualLineItems(prev => prev.filter((_, i) => i !== index));
  };

  // Manual Entry Computed Summaries
  const manualCalculations = useMemo(() => {
    let taxable = 0;
    let totalCgst = 0;
    let totalSgst = 0;
    let totalIgst = 0;

    const hsnMap: Record<string, { taxable: number; cgstRate: number; cgstAmt: number; sgstRate: number; sgstAmt: number; totalTax: number }> = {};

    manualLineItems.forEach(li => {
      const amt = Number(li.amount || 0);
      const isIgst = manualGstType === "IGST";
      const gstRate = Number(li.gst_rate || 0);
      const taxAmt = amt * (gstRate / 100);

      taxable += amt;
      if (isIgst) {
        totalIgst += taxAmt;
      } else {
        totalCgst += taxAmt / 2;
        totalSgst += taxAmt / 2;
      }

      if (li.hsn_code) {
        if (!hsnMap[li.hsn_code]) {
          hsnMap[li.hsn_code] = {
            taxable: 0,
            cgstRate: isIgst ? 0 : gstRate / 2,
            cgstAmt: 0,
            sgstRate: isIgst ? 0 : gstRate / 2,
            sgstAmt: 0,
            totalTax: 0
          };
        }
        hsnMap[li.hsn_code].taxable += amt;
        hsnMap[li.hsn_code].cgstAmt += isIgst ? 0 : taxAmt / 2;
        hsnMap[li.hsn_code].sgstAmt += isIgst ? 0 : taxAmt / 2;
        hsnMap[li.hsn_code].totalTax += taxAmt;
      }
    });

    const totalTax = manualGstType === "IGST" ? totalIgst : totalCgst + totalSgst;
    const subTotal = taxable + totalTax;
    const grandTotal = Math.round(subTotal + manualRounding);

    return {
      taxable,
      totalCgst,
      totalSgst,
      totalIgst,
      totalTax,
      subTotal,
      grandTotal,
      hsnSummary: Object.entries(hsnMap).map(([code, data]) => ({ hsn_code: code, ...data }))
    };
  }, [manualLineItems, manualGstType, manualRounding]);

  // Convert Number to Indian Rupees in Words
  const convertToIndianWords = (amount: number) => {
    if (!amount || amount === 0) return "Zero Rupees Only";
    const ones = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen", "Seventeen", "Eighteen", "Nineteen"];
    const tens = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"];

    const convertLessThanHundred = (n: number) => {
      if (n < 20) return ones[n];
      return tens[Math.floor(n / 10)] + (n % 10 ? " " + ones[n % 10] : "");
    };

    const convertLessThanThousand = (n: number) => {
      if (n < 100) return convertLessThanHundred(n);
      return ones[Math.floor(n / 100)] + " Hundred" + (n % 100 ? " " + convertLessThanHundred(n % 100) : "");
    };

    const isNegative = amount < 0;
    let num = Math.abs(Math.round(amount));
    let words = "";

    if (num >= 10000000) {
      words += convertLessThanThousand(Math.floor(num / 10000000)) + " Crore ";
      num %= 10000000;
    }
    if (num >= 100000) {
      words += convertLessThanHundred(Math.floor(num / 100000)) + " Lakh ";
      num %= 100000;
    }
    if (num >= 1000) {
      words += convertLessThanHundred(Math.floor(num / 1000)) + " Thousand ";
      num %= 1000;
    }
    if (num > 0) {
      words += convertLessThanThousand(num);
    }
    return (isNegative ? "Minus " : "") + "Rupees " + words.trim() + " Only";
  };

  // Submit Manual Invoice
  const handleSaveManualInvoice = async (confirmAfterSave: boolean) => {
    if (!manualCompanyId) {
      toast.error("Please select a company");
      return;
    }
    if (!manualVendorId) {
      toast.error("Please select a vendor");
      return;
    }
    if (!manualInvoiceNo.trim()) {
      toast.error("Please enter invoice number");
      return;
    }
    if (!manualInvoiceDate) {
      toast.error("Please select invoice date");
      return;
    }
    const validLines = manualLineItems.filter(l => l.stock_item_id || l.item_description);
    if (validLines.length === 0) {
      toast.error("Please add at least one line item");
      return;
    }

    setSavingManual(true);
    try {
      const payload = {
        company_id: parseInt(manualCompanyId),
        vendor_id: parseInt(manualVendorId),
        segment_id: manualSegmentId ? parseInt(manualSegmentId) : null,
        vendor_invoice_no: manualInvoiceNo.trim(),
        vendor_invoice_date: manualInvoiceDate,
        due_date: manualDueDate || null,
        is_credit_purchase: manualCreditPurchase,
        credit_days: manualCreditPurchase ? manualCreditDays : 0,
        review_notes: manualNotes,
        is_manual_entry: true,
        is_igst: manualGstType === "IGST",
        document_type: manualDocType,
        return_reference: manualDocType === "purchase_return" ? manualReturnRef.trim() || null : null,
        line_items: validLines.map((li, idx) => ({
          stock_item_id: li.stock_item_id ? Number(li.stock_item_id) : null,
          hsn_code: li.hsn_code || "",
          hsn_id: li.hsn_id ? Number(li.hsn_id) : null,
          quantity: li.quantity,
          rate: li.rate,
          amount: li.amount,
          gst_rate: li.gst_rate,
          cgst_rate: manualGstType === "IGST" ? 0 : li.gst_rate / 2,
          sgst_rate: manualGstType === "IGST" ? 0 : li.gst_rate / 2,
          igst_rate: manualGstType === "IGST" ? li.gst_rate : 0,
          cgst_amount: manualGstType === "IGST" ? 0 : li.tax_amount! / 2,
          sgst_amount: manualGstType === "IGST" ? 0 : li.tax_amount! / 2,
          igst_amount: manualGstType === "IGST" ? li.tax_amount : 0,
          tax_amount: li.tax_amount,
          total_amount: li.total_amount,
          serial_numbers: li.serial_numbers || ""
        }))
      };

      const res = await api.post("/staff/accounts/purchase-uploads/manual", payload);
      const uploadId = res.data.upload?.id;

      if (confirmAfterSave && uploadId) {
        await api.post(`/staff/accounts/purchase-uploads/${uploadId}/confirm`);
        toast.success("Invoice created and confirmed! Stock Ledger, AP, and Party Ledger updated.");
      } else {
        toast.success("Invoice saved as draft successfully");
      }

      setIsManualModalOpen(false);
      loadInvoices();
    } catch (err: any) {
      console.error("Manual invoice save error:", err);
      toast.error(err.response?.data?.detail || err.response?.data?.message || "Failed to save invoice");
    } finally {
      setSavingManual(false);
    }
  };

  // -------------------------------------------------------------
  // REJECT MODAL
  // -------------------------------------------------------------
  const [rejectReason, setRejectReason] = useState<string>("");
  const [rejecting, setRejecting] = useState<boolean>(false);

  const handleOpenRejectModal = (inv: PurchaseUpload) => {
    setSelectedInvoice(inv);
    setRejectReason("");
    setIsRejectModalOpen(true);
  };

  const handleConfirmReject = async () => {
    if (!selectedInvoice) return;
    if (!rejectReason.trim()) {
      toast.error("Please enter a rejection reason");
      return;
    }

    setRejecting(true);
    try {
      await api.post(`/staff/accounts/purchase-uploads/${selectedInvoice.id}/reject`, {
        rejection_reason: rejectReason.trim()
      });
      toast.success("Purchase Invoice rejected");
      setIsRejectModalOpen(false);
      loadInvoices();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Failed to reject invoice");
    } finally {
      setRejecting(false);
    }
  };

  // -------------------------------------------------------------
  // PENDING RECEIPT TAB STATE & ACTIONS
  // -------------------------------------------------------------
  const [pendingInvoices, setPendingInvoices] = useState<PendingReceiptInvoice[]>([]);
  const [loadingPending, setLoadingPending] = useState<boolean>(false);
  const [expandedPendingIndex, setExpandedPendingIndex] = useState<number | null>(null);
  const [receiveQtys, setReceiveQtys] = useState<Record<string, number>>({});

  const loadPendingReceipt = async () => {
    if (!selectedCompanyId) return;
    setLoadingPending(true);
    try {
      const res = await api.get(`/staff/accounts/purchase-invoices/pending-receipt?company_id=${selectedCompanyId}`);
      setPendingInvoices(res.data.data || []);
    } catch (err: any) {
      console.error("Error loading pending receipt:", err);
      toast.error("Failed to load pending receipts");
    } finally {
      setLoadingPending(false);
    }
  };

  const handleSavePurLineTarget = async (invId: number, lineId: number, newTargetQty: number) => {
    try {
      const res = await api.patch(`/staff/accounts/purchase-invoices/${invId}/pending-line-config/${lineId}`, {
        pending_qty: newTargetQty
      });
      if (res.data.success) {
        toast.success("Target qty updated");
        loadPendingReceipt();
      }
    } catch (err: any) {
      toast.error("Failed to update target qty");
    }
  };

  const handleSavePurEiTarget = async (invId: number, eiId: number, newTargetQty: number) => {
    try {
      const res = await api.patch(`/staff/accounts/purchase-invoices/${invId}/pending-extra-items/${eiId}`, {
        pending_qty: newTargetQty
      });
      if (res.data.success) {
        toast.success("Extra item target qty updated");
        loadPendingReceipt();
      }
    } catch (err: any) {
      toast.error("Failed to update extra item target qty");
    }
  };

  const handleCreateIntakeBatch = async (inv: PendingReceiptInvoice, invIndex: number) => {
    const regularItems: { line_id: number; qty_to_receive: number }[] = [];
    const extraItems: { extra_item_id: number; qty: number }[] = [];

    inv.lines.forEach(line => {
      const key = `line-${invIndex}-${line.id}`;
      const qty = receiveQtys[key] !== undefined ? receiveQtys[key] : line.pending_qty;
      if (qty > 0) regularItems.push({ line_id: line.id, qty_to_receive: qty });
    });

    (inv.extra_items || []).forEach(ei => {
      const key = `ei-${invIndex}-${ei.id}`;
      const qty = receiveQtys[key] !== undefined ? receiveQtys[key] : ei.remaining_qty;
      if (qty > 0) extraItems.push({ extra_item_id: ei.id, qty });
    });

    if (regularItems.length === 0 && extraItems.length === 0) {
      toast.error("Please enter quantity to receive for at least one item");
      return;
    }

    try {
      for (const er of extraItems) {
        await api.patch(`/staff/accounts/purchase-invoices/${inv.id}/pending-extra-items/${er.extra_item_id}`, {
          received_qty: er.qty
        });
      }

      if (regularItems.length > 0) {
        const res = await api.post(`/staff/accounts/purchase-invoices/${inv.id}/create-intake-batch`, {
          items: regularItems
        });
        if (res.data.success) {
          toast.success(`Intake Batch created: ${res.data.batch_number}`);
        }
      } else {
        toast.success("Extra items receipt recorded");
      }
      loadPendingReceipt();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Failed to create intake batch");
    }
  };

  // -------------------------------------------------------------
  // ADD PENDING INVOICE MODAL
  // -------------------------------------------------------------
  const [addPendingSearch, setAddPendingSearch] = useState<string>("");
  const [addPendingResults, setAddPendingResults] = useState<any[]>([]);
  const [selectedAddPendingInv, setSelectedAddPendingInv] = useState<any | null>(null);
  const [addPendingLineOverrides, setAddPendingLineOverrides] = useState<Record<number, number>>({});
  const [addPendingExtraItems, setAddPendingExtraItems] = useState<{ item_id: number | null; item_description: string; item_code: string; uom: string; pending_qty: number }[]>([]);
  const [searchingAddPending, setSearchingAddPending] = useState<boolean>(false);

  const handleOpenAddPendingModal = () => {
    setAddPendingSearch("");
    setAddPendingResults([]);
    setSelectedAddPendingInv(null);
    setAddPendingLineOverrides({});
    setAddPendingExtraItems([]);
    setIsAddPendingModalOpen(true);
    searchPendingInvoices("");
  };

  const searchPendingInvoices = async (q: string) => {
    if (!selectedCompanyId) return;
    setSearchingAddPending(true);
    try {
      const res = await api.get(`/staff/accounts/purchase-invoices/search-for-pending?company_id=${selectedCompanyId}&q=${encodeURIComponent(q)}`);
      setAddPendingResults(res.data.invoices || []);
    } catch (err) {
      console.error("Error searching pending invoices:", err);
    } finally {
      setSearchingAddPending(false);
    }
  };

  const handleSelectAddPendingInvoice = (inv: any) => {
    setSelectedAddPendingInv(inv);
    const overrides: Record<number, number> = {};
    (inv.line_items || []).forEach((li: any) => {
      overrides[li.id] = li.quantity;
    });
    setAddPendingLineOverrides(overrides);
  };

  const handleConfirmAddPending = async () => {
    if (!selectedAddPendingInv) return;
    try {
      const line_overrides = Object.entries(addPendingLineOverrides).map(([id, qty]) => ({
        line_id: parseInt(id),
        pending_qty: qty
      }));

      await api.post(`/staff/accounts/purchase-invoices/${selectedAddPendingInv.id}/toggle-receipt-tracking`, {
        enable: true,
        line_overrides,
        extra_items: addPendingExtraItems
      });
      toast.success("Invoice added to Pending Receipt list");
      setIsAddPendingModalOpen(false);
      loadPendingReceipt();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Failed to add to pending receipts");
    }
  };

  // -------------------------------------------------------------
  // SUMMARY TAB STATE & LOADER
  // -------------------------------------------------------------
  const [summarySubTab, setSummarySubTab] = useState<"item" | "day" | "vendor">("item");
  const [itemWiseSummary, setItemWiseSummary] = useState<any[]>([]);
  const [dayWiseSummary, setDayWiseSummary] = useState<any[]>([]);
  const [vendorWiseSummary, setVendorWiseSummary] = useState<any[]>([]);
  const [loadingSummary, setLoadingSummary] = useState<boolean>(false);

  const loadPurchaseSummary = async () => {
    if (!selectedCompanyId) return;
    setLoadingSummary(true);
    try {
      const res = await api.get(`/staff/accounts/pending-dispatch/summary?invoice_type=purchase&company_id=${selectedCompanyId}`);
      setItemWiseSummary(res.data.item_wise || []);
      setDayWiseSummary(res.data.day_wise || []);
      setVendorWiseSummary(res.data.party_wise || []);
    } catch (err) {
      console.error("Error loading purchase summary:", err);
    } finally {
      setLoadingSummary(false);
    }
  };

  // -------------------------------------------------------------
  // QUICK CREATE MODAL STATES & ACTIONS (Vendor / Stock Item / HSN)
  // -------------------------------------------------------------
  const [qcVendorName, setQcVendorName] = useState<string>("");
  const [qcVendorCode, setQcVendorCode] = useState<string>("");
  const [qcVendorType, setQcVendorType] = useState<string>("BOTH");
  const [qcVendorEmail, setQcVendorEmail] = useState<string>("");
  const [qcVendorGst, setQcVendorGst] = useState<string>("");
  const [qcVendorPan, setQcVendorPan] = useState<string>("");
  const [qcVendorPhone, setQcVendorPhone] = useState<string>("");
  const [qcVendorContactName, setQcVendorContactName] = useState<string>("");
  const [qcVendorAddress, setQcVendorAddress] = useState<string>("");
  const [qcVendorPincode, setQcVendorPincode] = useState<string>("");
  const [qcVendorCity, setQcVendorCity] = useState<string>("");
  const [qcVendorState, setQcVendorState] = useState<string>("");
  const [qcVendorApplicableCompanies, setQcVendorApplicableCompanies] = useState<number[]>([]);
  const [savingQcVendor, setSavingQcVendor] = useState<boolean>(false);

  const handleOpenQcVendor = () => {
    setQcVendorName("");
    setQcVendorCode("");
    setQcVendorType("BOTH");
    setQcVendorEmail("");
    setQcVendorGst("");
    setQcVendorPan("");
    setQcVendorPhone("");
    setQcVendorContactName("");
    setQcVendorAddress("");
    setQcVendorPincode("");
    setQcVendorCity("");
    setQcVendorState("");
    setQcVendorApplicableCompanies(selectedCompanyId ? [parseInt(selectedCompanyId)] : []);
    setIsQcVendorOpen(true);
  };

  const handlePincodeLookup = async (pincode: string) => {
    if (!pincode || pincode.length !== 6) return;
    try {
      const res = await api.get(`/staff/accounts/pincode-lookup/${pincode}`);
      if (res.data.success && res.data.city && res.data.state) {
        setQcVendorCity(res.data.city);
        setQcVendorState(res.data.state);
        toast.success(`Found: ${res.data.city}, ${res.data.state}`);
      }
    } catch (err) {
      console.warn("Pincode lookup failed:", err);
    }
  };

  const handleSaveQcVendor = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!qcVendorName.trim() || !qcVendorCode.trim()) {
      toast.error("Vendor name and code are required");
      return;
    }
    if (qcVendorApplicableCompanies.length === 0) {
      toast.error("Please select at least one applicable company");
      return;
    }

    setSavingQcVendor(true);
    try {
      const payload = {
        vendor_name: qcVendorName.trim(),
        vendor_code: qcVendorCode.trim().toUpperCase(),
        vendor_type: qcVendorType,
        email: qcVendorEmail.trim() || null,
        gst_number: qcVendorGst.trim().toUpperCase() || null,
        pan_number: qcVendorPan.trim().toUpperCase() || null,
        contact_person: qcVendorContactName.trim() || null,
        phone: qcVendorPhone.trim() || null,
        address: qcVendorAddress.trim() || null,
        pincode: qcVendorPincode.trim() || null,
        city: qcVendorCity.trim() || null,
        state: qcVendorState.trim() || null,
        applicable_companies: qcVendorApplicableCompanies
      };

      const res = await api.post("/staff/accounts/vendors", payload);
      toast.success("Vendor created successfully!");
      setIsQcVendorOpen(false);
      fetchVendors();

      if (res.data.vendor?.id) {
        const v = res.data.vendor;
        const label = v.vendor_code ? `${v.vendor_code} - ${v.vendor_name}` : v.vendor_name;
        if (isUploadModalOpen) {
          setUploadVendorId(String(v.id));
          setUploadVendorSearch(label);
        }
        if (isReviewModalOpen) {
          setReviewVendorId(String(v.id));
          setReviewVendorSearch(label);
        }
        if (isManualModalOpen) {
          setManualVendorId(String(v.id));
          setManualVendorSearch(label);
        }
      }
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Failed to create vendor");
    } finally {
      setSavingQcVendor(false);
    }
  };

  // Quick Create Stock Item
  const [qcStockName, setQcStockName] = useState<string>("");
  const [qcStockCode, setQcStockCode] = useState<string>("");
  const [qcStockCategory, setQcStockCategory] = useState<string>("PRODUCT");
  const [qcStockUom, setQcStockUom] = useState<string>("PCS");
  const [qcStockHsnId, setQcStockHsnId] = useState<string>("");
  const [qcStockPurchaseRate, setQcStockPurchaseRate] = useState<number>(0);
  const [qcStockSellingRate, setQcStockSellingRate] = useState<number>(0);
  const [qcStockMarkupPct, setQcStockMarkupPct] = useState<number>(27);
  const [qcStockApplicableCompanies, setQcStockApplicableCompanies] = useState<number[]>([]);
  const [savingQcStock, setSavingQcStock] = useState<boolean>(false);

  const handleOpenQcStock = async () => {
    setQcStockName("");
    setQcStockCategory("PRODUCT");
    setQcStockUom("PCS");
    setQcStockHsnId("");
    setQcStockPurchaseRate(0);
    setQcStockSellingRate(0);
    setQcStockMarkupPct(27);
    setQcStockApplicableCompanies(selectedCompanyId ? [parseInt(selectedCompanyId)] : []);
    setIsQcStockOpen(true);
    generateStockCode("PRODUCT");
  };

  const generateStockCode = async (category: string) => {
    try {
      const res = await api.get(`/staff/accounts/stock-items/generate-code?category=${encodeURIComponent(category)}`);
      if (res.data.item_code) setQcStockCode(res.data.item_code);
    } catch (err) {
      setQcStockCode(`ITEM_${Date.now().toString(36).toUpperCase().slice(-8)}`);
    }
  };

  const handleSaveQcStock = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!qcStockName.trim() || !qcStockCode.trim()) {
      toast.error("Stock item name and code are required");
      return;
    }
    if (qcStockApplicableCompanies.length === 0) {
      toast.error("Please select at least one applicable company");
      return;
    }

    setSavingQcStock(true);
    try {
      const payload = {
        item_name: qcStockName.trim(),
        item_code: qcStockCode.trim().toUpperCase(),
        item_category: qcStockCategory,
        unit_of_measure: qcStockUom,
        hsn_id: qcStockHsnId ? parseInt(qcStockHsnId) : null,
        purchase_rate: qcStockPurchaseRate,
        selling_rate: qcStockSellingRate,
        applicable_companies: qcStockApplicableCompanies
      };

      await api.post("/staff/accounts/stock-items", payload);
      toast.success("Stock item created successfully!");
      setIsQcStockOpen(false);
      fetchStockItems();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Failed to create stock item");
    } finally {
      setSavingQcStock(false);
    }
  };

  // Quick Create HSN
  const [qcHsnCodeVal, setQcHsnCodeVal] = useState<string>("");
  const [qcHsnDesc, setQcHsnDesc] = useState<string>("");
  const [qcHsnGstRate, setQcHsnGstRate] = useState<number>(18);
  const [qcHsnEffectiveFrom, setQcHsnEffectiveFrom] = useState<string>(new Date().toISOString().split("T")[0]);
  const [savingQcHsn, setSavingQcHsn] = useState<boolean>(false);

  const handleOpenQcHsn = () => {
    setQcHsnCodeVal("");
    setQcHsnDesc("");
    setQcHsnGstRate(18);
    setQcHsnEffectiveFrom(new Date().toISOString().split("T")[0]);
    setIsQcHsnOpen(true);
  };

  const handleSaveQcHsn = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!qcHsnCodeVal.trim() || !qcHsnDesc.trim()) {
      toast.error("HSN code and description are required");
      return;
    }

    setSavingQcHsn(true);
    try {
      const payload = {
        hsn_code: qcHsnCodeVal.trim().toUpperCase(),
        description: qcHsnDesc.trim(),
        cgst_rate: qcHsnGstRate / 2,
        sgst_rate: qcHsnGstRate / 2,
        igst_rate: qcHsnGstRate,
        cess_rate: 0,
        effective_from: qcHsnEffectiveFrom
      };

      await api.post("/staff/accounts/hsn", payload);
      toast.success("HSN code created successfully!");
      setIsQcHsnOpen(false);
      fetchHsnCodes();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Failed to create HSN code");
    } finally {
      setSavingQcHsn(false);
    }
  };

  // Currency Formatter
  const formatCurrency = (val: number) => {
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: "INR",
      minimumFractionDigits: 2
    }).format(val || 0);
  };

  return (
    <div className="p-4 sm:p-6 max-w-[1600px] mx-auto space-y-6 animate-in fade-in duration-300">
      <Toaster position="top-right" />

      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white p-6 rounded-2xl shadow-sm border border-gray-100">
        <div>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center font-bold">
              <FileText className="w-5 h-5" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-gray-900 tracking-tight">Purchase Invoices</h1>
              <p className="text-sm text-gray-500 mt-0.5">
                Upload, review, calculate GST, and confirm vendor purchase invoices
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3 flex-wrap">
          <button
            onClick={handleOpenManualModal}
            className="inline-flex items-center gap-2 px-4 py-2.5 bg-white border border-gray-200 hover:border-emerald-500 hover:bg-emerald-50/30 text-gray-700 font-semibold rounded-xl text-sm transition-all shadow-sm"
          >
            <Edit className="w-4 h-4 text-emerald-600" />
            Manual Entry
          </button>
          <button
            onClick={handleOpenUploadModal}
            className="inline-flex items-center gap-2 px-5 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white font-semibold rounded-xl text-sm transition-all shadow-md shadow-emerald-200"
          >
            <Upload className="w-4 h-4" />
            Upload Invoice
          </button>
        </div>
      </div>

      {/* Navigation Tabs Bar */}
      <div className="flex border-b border-gray-200 bg-white px-6 rounded-t-xl gap-6">
        <button
          onClick={() => {
            setActiveTab("invoices");
            loadInvoices(1);
          }}
          className={`py-4 font-semibold text-sm border-b-2 flex items-center gap-2 transition-all ${
            activeTab === "invoices"
              ? "border-emerald-600 text-emerald-600"
              : "border-transparent text-gray-500 hover:text-gray-900"
          }`}
        >
          <FileText className="w-4 h-4" />
          Invoices
        </button>
        <button
          onClick={() => {
            setActiveTab("pending");
            loadPendingReceipt();
          }}
          className={`py-4 font-semibold text-sm border-b-2 flex items-center gap-2 transition-all ${
            activeTab === "pending"
              ? "border-emerald-600 text-emerald-600"
              : "border-transparent text-gray-500 hover:text-gray-900"
          }`}
        >
          <Clock className="w-4 h-4 text-amber-500" />
          Pending Receipt
        </button>
        <button
          onClick={() => {
            setActiveTab("summary");
            loadPurchaseSummary();
          }}
          className={`py-4 font-semibold text-sm border-b-2 flex items-center gap-2 transition-all ${
            activeTab === "summary"
              ? "border-emerald-600 text-emerald-600"
              : "border-transparent text-gray-500 hover:text-gray-900"
          }`}
        >
          <Layers className="w-4 h-4 text-blue-500" />
          Summary
        </button>
      </div>

      {/* TAB 1: INVOICES */}
      {activeTab === "invoices" && (
        <div className="space-y-6">
          {/* Filters Bar */}
          <div className="bg-white p-5 rounded-2xl shadow-sm border border-gray-100 space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              {/* Company Select */}
              <div>
                <label className="block text-xs font-bold text-gray-700 uppercase tracking-wider mb-1.5 flex items-center gap-1.5">
                  <Building className="w-3.5 h-3.5 text-emerald-600" />
                  Company
                </label>
                <select
                  value={selectedCompanyId}
                  onChange={e => setSelectedCompanyId(e.target.value)}
                  className="w-full px-3.5 py-2.5 bg-gray-50 border border-gray-200 rounded-xl text-sm font-medium text-gray-900 focus:bg-white focus:border-emerald-500 focus:ring-2 focus:ring-emerald-100 transition-all"
                >
                  <option value="">-- All Companies --</option>
                  {companies.map(c => (
                    <option key={c.id} value={c.id}>
                      {c.company_name || c.name}
                    </option>
                  ))}
                </select>
              </div>

              {/* Status Select */}
              <div>
                <label className="block text-xs font-bold text-gray-700 uppercase tracking-wider mb-1.5">
                  Status
                </label>
                <select
                  value={filterStatus}
                  onChange={e => setFilterStatus(e.target.value)}
                  className="w-full px-3.5 py-2.5 bg-gray-50 border border-gray-200 rounded-xl text-sm font-medium text-gray-900 focus:bg-white focus:border-emerald-500 focus:ring-2 focus:ring-emerald-100 transition-all"
                >
                  <option value="">All Statuses</option>
                  <option value="UPLOADED">Uploaded</option>
                  <option value="EXTRACTING">Extracting</option>
                  <option value="EXTRACTED">Extracted (Pending Review)</option>
                  <option value="REVIEWED">Reviewed</option>
                  <option value="CONFIRMED">Confirmed</option>
                  <option value="PROCESSED">Processed</option>
                  <option value="REJECTED">Rejected</option>
                  <option value="VOIDED">Deleted (Voided)</option>
                </select>
              </div>

              {/* Vendor Search Input */}
              <div>
                <label className="block text-xs font-bold text-gray-700 uppercase tracking-wider mb-1.5 flex items-center justify-between">
                  <span>Vendor</span>
                  {filterVendorId && (
                    <button
                      onClick={() => {
                        setFilterVendorId("");
                        setFilterVendorSearch("");
                      }}
                      className="text-xs text-red-500 hover:underline"
                    >
                      Clear
                    </button>
                  )}
                </label>
                <div className="relative">
                  <input
                    type="text"
                    placeholder="Search vendors..."
                    value={filterVendorSearch}
                    onChange={e => {
                      setFilterVendorSearch(e.target.value);
                      if (!e.target.value) setFilterVendorId("");
                    }}
                    className="w-full pl-9 pr-3.5 py-2.5 bg-gray-50 border border-gray-200 rounded-xl text-sm font-medium text-gray-900 focus:bg-white focus:border-emerald-500 focus:ring-2 focus:ring-emerald-100 transition-all"
                  />
                  <Search className="w-4 h-4 text-gray-400 absolute left-3 top-3" />
                  {filterVendorSearch && !filterVendorId && (
                    <div className="absolute left-0 right-0 top-full mt-1 bg-white rounded-xl shadow-xl border border-gray-200 max-h-52 overflow-y-auto z-50 divide-y divide-gray-100">
                      {vendors
                        .filter(v =>
                          (v.display_label || v.vendor_name || "").toLowerCase().includes(filterVendorSearch.toLowerCase())
                        )
                        .slice(0, 10)
                        .map(v => (
                          <div
                            key={v.id}
                            onClick={() => {
                              setFilterVendorId(String(v.id));
                              setFilterVendorSearch(v.display_label || v.vendor_name);
                            }}
                            className="p-2.5 hover:bg-emerald-50 cursor-pointer text-xs font-medium text-gray-800"
                          >
                            {v.display_label || v.vendor_name}
                          </div>
                        ))}
                    </div>
                  )}
                </div>
              </div>

              {/* Date Pickers */}
              <div>
                <label className="block text-xs font-bold text-gray-700 uppercase tracking-wider mb-1.5 flex items-center gap-1.5">
                  <Calendar className="w-3.5 h-3.5 text-gray-500" />
                  Date Range
                </label>
                <div className="grid grid-cols-2 gap-2">
                  <input
                    type="date"
                    value={filterFromDate}
                    onChange={e => {
                      setFilterFromDate(e.target.value);
                      setActivePeriod("custom");
                    }}
                    className="w-full px-2.5 py-2 bg-gray-50 border border-gray-200 rounded-xl text-xs font-medium text-gray-900"
                  />
                  <input
                    type="date"
                    value={filterToDate}
                    onChange={e => {
                      setFilterToDate(e.target.value);
                      setActivePeriod("custom");
                    }}
                    className="w-full px-2.5 py-2 bg-gray-50 border border-gray-200 rounded-xl text-xs font-medium text-gray-900"
                  />
                </div>
              </div>
            </div>

            {/* Quick Period Buttons */}
            <div className="flex items-center gap-2 pt-2 border-t border-gray-100 flex-wrap">
              <span className="text-xs font-semibold text-gray-400 mr-2">Quick Periods:</span>
              {[
                { label: "This Month", key: "month" },
                { label: "This Quarter", key: "quarter" },
                { label: "This FY", key: "fy" },
                { label: "Overall", key: "overall" }
              ].map(p => (
                <button
                  key={p.key}
                  onClick={() => handleSetPeriod(p.key)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                    activePeriod === p.key
                      ? "bg-emerald-600 text-white shadow-sm"
                      : "bg-gray-100 hover:bg-gray-200 text-gray-600"
                  }`}
                >
                  {p.label}
                </button>
              ))}
              <button
                onClick={() => loadInvoices(1)}
                className="ml-auto inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-bold text-gray-600 bg-gray-100 hover:bg-gray-200 rounded-lg transition-all"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${loadingInvoices ? "animate-spin" : ""}`} />
                Refresh
              </button>
            </div>
          </div>

          {/* KPI Summary Cards */}
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
            <div className="bg-white p-4 rounded-2xl shadow-sm border border-gray-100 flex flex-col justify-between">
              <span className="text-xs font-bold text-gray-400 uppercase tracking-wider">Uploaded</span>
              <div className="text-2xl font-extrabold text-blue-600 mt-2">{stats.uploaded}</div>
            </div>
            <div className="bg-white p-4 rounded-2xl shadow-sm border border-gray-100 flex flex-col justify-between">
              <span className="text-xs font-bold text-gray-400 uppercase tracking-wider">Pending Review</span>
              <div className="text-2xl font-extrabold text-amber-500 mt-2">{stats.pending_review}</div>
            </div>
            <div className="bg-white p-4 rounded-2xl shadow-sm border border-gray-100 flex flex-col justify-between">
              <span className="text-xs font-bold text-gray-400 uppercase tracking-wider">Confirmed</span>
              <div className="text-2xl font-extrabold text-emerald-600 mt-2">{stats.confirmed}</div>
            </div>
            <div className="bg-white p-4 rounded-2xl shadow-sm border border-gray-100 flex flex-col justify-between">
              <span className="text-xs font-bold text-gray-400 uppercase tracking-wider">Rejected</span>
              <div className="text-2xl font-extrabold text-red-500 mt-2">{stats.rejected}</div>
            </div>
            <div className="bg-white p-4 rounded-2xl shadow-sm border border-gray-100 border-l-4 border-l-purple-500 flex flex-col justify-between">
              <span className="text-xs font-bold text-purple-600 uppercase tracking-wider">Voided</span>
              <div className="text-2xl font-extrabold text-purple-700 mt-2">{stats.voided}</div>
            </div>
            <div className="bg-white p-4 rounded-2xl shadow-sm border border-gray-100 flex flex-col justify-between">
              <span className="text-xs font-bold text-gray-400 uppercase tracking-wider">Total Confirmed Value</span>
              <div className="text-lg sm:text-xl font-black font-mono text-emerald-700 mt-2 truncate">
                {formatCurrency(stats.total_confirmed_value)}
              </div>
            </div>
          </div>

          {/* Invoices Table Card */}
          <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
            <div className="p-4 sm:p-5 border-b border-gray-100 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="font-bold text-gray-900">Purchase Invoices</span>
                <span className="text-xs text-gray-400 bg-gray-100 px-2 py-0.5 rounded-full font-semibold">
                  {totalRecords} records
                </span>
              </div>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="bg-gray-50/75 border-b border-gray-100 text-xs font-bold text-gray-500 uppercase tracking-wider">
                    <th className="py-3.5 px-4">Upload #</th>
                    <th className="py-3.5 px-4">Upload Date</th>
                    <th className="py-3.5 px-4">Invoice Date</th>
                    <th className="py-3.5 px-4">Company</th>
                    <th className="py-3.5 px-4">Vendor</th>
                    <th className="py-3.5 px-4">Invoice No</th>
                    <th className="py-3.5 px-4 text-right">Taxable</th>
                    <th className="py-3.5 px-4 text-right">GST</th>
                    <th className="py-3.5 px-4 text-right">Total</th>
                    <th className="py-3.5 px-4 text-center">Status</th>
                    <th className="py-3.5 px-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100 text-sm">
                  {loadingInvoices ? (
                    <tr>
                      <td colSpan={11} className="py-12 text-center text-gray-400">
                        <RefreshCw className="w-6 h-6 animate-spin mx-auto text-emerald-600 mb-2" />
                        Loading purchase invoices...
                      </td>
                    </tr>
                  ) : invoices.length === 0 ? (
                    <tr>
                      <td colSpan={11} className="py-12 text-center text-gray-400">
                        <FileText className="w-10 h-10 mx-auto text-gray-300 mb-2" />
                        <p className="font-semibold text-gray-600">No purchase invoices found</p>
                        <p className="text-xs text-gray-400 mt-1">Upload an invoice or create a manual entry to get started</p>
                      </td>
                    </tr>
                  ) : (
                    invoices.map(inv => {
                      const isDebitNote = inv.document_type === "purchase_return";
                      return (
                        <tr key={inv.id} className="hover:bg-gray-50/80 transition-colors">
                          <td className="py-3 px-4 font-semibold text-gray-900">
                            <div>{inv.voucher_number || inv.upload_number}</div>
                            {inv.voucher_number && (
                              <div className="text-xs text-gray-400">{inv.upload_number}</div>
                            )}
                          </td>
                          <td className="py-3 px-4 text-xs text-gray-500">
                            {inv.uploaded_at ? new Date(inv.uploaded_at).toLocaleDateString("en-IN") : "-"}
                          </td>
                          <td className="py-3 px-4 text-xs text-gray-500">
                            {inv.vendor_invoice_date ? new Date(inv.vendor_invoice_date).toLocaleDateString("en-IN") : "-"}
                          </td>
                          <td className="py-3 px-4 text-xs text-gray-700 font-medium">{inv.company_name || "-"}</td>
                          <td className="py-3 px-4 text-xs font-semibold text-gray-900">{inv.vendor_name || "-"}</td>
                          <td className="py-3 px-4 text-xs font-mono text-gray-700">{inv.vendor_invoice_no || "-"}</td>
                          <td className="py-3 px-4 text-xs font-mono text-right text-gray-700">
                            {formatCurrency(inv.taxable_amount || 0)}
                          </td>
                          <td className="py-3 px-4 text-xs font-mono text-right text-gray-700">
                            {formatCurrency(inv.total_tax || 0)}
                          </td>
                          <td className="py-3 px-4 text-xs font-mono text-right font-bold text-emerald-700">
                            {formatCurrency(inv.grand_total || 0)}
                          </td>
                          <td className="py-3 px-4 text-center">
                            <span
                              className={`inline-block px-2.5 py-1 rounded-full text-xs font-bold ${
                                inv.status === "CONFIRMED"
                                  ? "bg-emerald-100 text-emerald-800"
                                  : inv.status === "EXTRACTED" || inv.status === "REVIEWED"
                                  ? "bg-amber-100 text-amber-800"
                                  : inv.status === "VOIDED"
                                  ? "bg-purple-100 text-purple-800"
                                  : inv.status === "REJECTED"
                                  ? "bg-red-100 text-red-800"
                                  : "bg-blue-100 text-blue-800"
                              }`}
                            >
                              {inv.status}
                            </span>
                            {isDebitNote && (
                              <div className="mt-1">
                                <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-amber-100 text-amber-700">
                                  Debit Note
                                </span>
                              </div>
                            )}
                            {inv.status === "VOIDED" && inv.voided_by_name && (
                              <div className="text-[10px] text-purple-600 mt-0.5">
                                by {inv.voided_by_name}
                              </div>
                            )}
                          </td>
                          <td className="py-3 px-4 text-right">
                            <div className="flex items-center justify-end gap-1.5">
                              {/* View button */}
                              <button
                                onClick={() => handleOpenViewModal(inv.id)}
                                title="View Details"
                                className="p-1.5 text-gray-500 hover:text-gray-900 bg-gray-100 hover:bg-gray-200 rounded-lg transition-all"
                              >
                                <Eye className="w-4 h-4" />
                              </button>

                              {/* Voided -> Post Again */}
                              {inv.status === "VOIDED" && (
                                <button
                                  onClick={() => handlePostAgain(inv.id)}
                                  title="Post Again (Recreate stock and ledger entries)"
                                  className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-bold text-emerald-700 bg-emerald-100 hover:bg-emerald-200 rounded-lg transition-all"
                                >
                                  <RotateCcw className="w-3.5 h-3.5" />
                                  Post Again
                                </button>
                              )}

                              {/* Editable statuses -> Edit button */}
                              {["UPLOADED", "EXTRACTED", "REVIEWED", "REJECTED", "CONFIRMED"].includes(inv.status) && (
                                <button
                                  onClick={() => handleOpenReviewModal(inv.id)}
                                  title="Edit / Review Invoice"
                                  className="p-1.5 text-blue-600 hover:text-blue-800 bg-blue-50 hover:bg-blue-100 rounded-lg transition-all"
                                >
                                  <Edit className="w-4 h-4" />
                                </button>
                              )}

                              {/* Pending Review -> Reject button */}
                              {["EXTRACTED", "REVIEWED"].includes(inv.status) && (
                                <button
                                  onClick={() => handleOpenRejectModal(inv)}
                                  title="Reject Invoice"
                                  className="p-1.5 text-red-600 hover:text-red-800 bg-red-50 hover:bg-red-100 rounded-lg transition-all"
                                >
                                  <X className="w-4 h-4" />
                                </button>
                              )}

                              {/* Confirmed actions */}
                              {inv.status === "CONFIRMED" && (
                                <>
                                  <button
                                    onClick={() => handleReconfirmInvoice(inv.id)}
                                    title="Re-confirm Invoice (re-runs entries)"
                                    className="p-1.5 text-emerald-600 hover:text-emerald-800 bg-emerald-50 hover:bg-emerald-100 rounded-lg transition-all"
                                  >
                                    <RotateCcw className="w-4 h-4" />
                                  </button>

                                  <button
                                    onClick={() => handleToggleReceiptTracking(inv.id, !inv.track_physical_receipt)}
                                    title={inv.track_physical_receipt ? "Disable physical receipt tracking" : "Enable physical receipt tracking"}
                                    className={`px-2 py-1 text-[11px] font-bold rounded-lg transition-all flex items-center gap-1 ${
                                      inv.track_physical_receipt
                                        ? "bg-purple-100 text-purple-700"
                                        : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                                    }`}
                                  >
                                    <Warehouse className="w-3.5 h-3.5" />
                                    {inv.track_physical_receipt ? "Tracking" : "Track"}
                                  </button>

                                  {canDelete && (
                                    <button
                                      onClick={() => handleVoidInvoice(inv.id, inv.upload_number)}
                                      title="Void Invoice (reverses stock, AP, ledger entries)"
                                      className="px-2 py-1 text-[11px] font-bold text-red-700 bg-red-100 hover:bg-red-200 rounded-lg transition-all"
                                    >
                                      <Ban className="w-3.5 h-3.5" />
                                      Void
                                    </button>
                                  )}
                                </>
                              )}

                              {/* PDF download */}
                              {inv.status !== "CANCELLED" && (
                                <button
                                  onClick={() => handleDownloadPdf(inv.id, inv.company_id)}
                                  title="Download PDF"
                                  className="p-1.5 text-indigo-600 hover:text-indigo-800 bg-indigo-50 hover:bg-indigo-100 rounded-lg transition-all"
                                >
                                  <Download className="w-4 h-4" />
                                </button>
                              )}

                              {/* Non-confirmed delete */}
                              {!["CONFIRMED", "PROCESSED", "VOIDED"].includes(inv.status) && canDelete && (
                                <button
                                  onClick={() => handleDeleteInvoice(inv.id, inv.upload_number)}
                                  title="Delete Invoice"
                                  className="p-1.5 text-red-600 hover:text-red-800 bg-red-50 hover:bg-red-100 rounded-lg transition-all"
                                >
                                  <Trash2 className="w-4 h-4" />
                                </button>
                              )}
                            </div>
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>

            {/* Pagination footer */}
            {totalPages > 1 && (
              <div className="p-4 border-t border-gray-100 flex items-center justify-between flex-wrap gap-4 text-xs font-semibold text-gray-500">
                <div>
                  Page {currentPage} of {totalPages}
                </div>
                <div className="flex items-center gap-1.5">
                  <button
                    disabled={currentPage <= 1}
                    onClick={() => handlePageChange(currentPage - 1)}
                    className="px-3 py-1.5 bg-gray-100 hover:bg-gray-200 disabled:opacity-40 rounded-lg transition-all"
                  >
                    Previous
                  </button>
                  {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                    const pageNum = i + 1;
                    return (
                      <button
                        key={pageNum}
                        onClick={() => handlePageChange(pageNum)}
                        className={`px-3 py-1.5 rounded-lg transition-all ${
                          currentPage === pageNum
                            ? "bg-emerald-600 text-white"
                            : "bg-gray-100 hover:bg-gray-200 text-gray-700"
                        }`}
                      >
                        {pageNum}
                      </button>
                    );
                  })}
                  <button
                    disabled={currentPage >= totalPages}
                    onClick={() => handlePageChange(currentPage + 1)}
                    className="px-3 py-1.5 bg-gray-100 hover:bg-gray-200 disabled:opacity-40 rounded-lg transition-all"
                  >
                    Next
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB 2: PENDING RECEIPT */}
      {activeTab === "pending" && (
        <div className="space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white p-5 rounded-2xl shadow-sm border border-gray-100">
            <div>
              <h3 className="text-base font-bold text-gray-900 flex items-center gap-2">
                <Clock className="w-5 h-5 text-amber-500" />
                Pending Receipt Tracking
              </h3>
              <p className="text-xs text-gray-500 mt-0.5">
                Confirmed purchase invoices with items not yet fully received into stock
              </p>
            </div>
            <div className="flex items-center gap-3">
              <button
                onClick={handleOpenAddPendingModal}
                className="inline-flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold rounded-xl transition-all shadow-sm"
              >
                <Plus className="w-4 h-4" />
                Add Pending Invoice
              </button>
              <button
                onClick={loadPendingReceipt}
                className="inline-flex items-center gap-2 px-3.5 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 text-xs font-bold rounded-xl transition-all"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${loadingPending ? "animate-spin" : ""}`} />
                Refresh
              </button>
            </div>
          </div>

          {loadingPending ? (
            <div className="bg-white p-12 rounded-2xl text-center text-gray-400">
              <RefreshCw className="w-6 h-6 animate-spin mx-auto text-emerald-600 mb-2" />
              Loading pending receipts...
            </div>
          ) : pendingInvoices.length === 0 ? (
            <div className="bg-white p-12 rounded-2xl text-center text-gray-400 border border-gray-100">
              <CheckCircle className="w-12 h-12 text-emerald-500 mx-auto mb-2" />
              <h4 className="text-base font-bold text-gray-800">All Items Received!</h4>
              <p className="text-xs text-gray-400 mt-1">No pending stock receipts found for the selected company.</p>
            </div>
          ) : (
            <div className="space-y-4">
              {pendingInvoices.map((inv, invIdx) => {
                const isExpanded = expandedPendingIndex === invIdx;
                const extraItems = inv.extra_items || [];
                return (
                  <div
                    key={inv.id}
                    className="bg-white rounded-2xl shadow-sm border border-gray-200 overflow-hidden transition-all"
                  >
                    {/* Header */}
                    <div
                      onClick={() => setExpandedPendingIndex(isExpanded ? null : invIdx)}
                      className="p-4 sm:p-5 flex items-center justify-between cursor-pointer hover:bg-gray-50/80 transition-colors"
                    >
                      <div className="flex items-center gap-4 flex-wrap">
                        <span className="font-bold text-gray-900 text-sm sm:text-base">{inv.upload_number}</span>
                        <span className="text-xs font-semibold text-gray-600 bg-gray-100 px-2.5 py-1 rounded-lg">
                          {inv.vendor_name}
                        </span>
                        {inv.vendor_invoice_no && (
                          <span className="text-xs text-gray-400">
                            Inv: {inv.vendor_invoice_no} {inv.vendor_invoice_date && `· ${inv.vendor_invoice_date}`}
                          </span>
                        )}
                      </div>

                      <div className="flex items-center gap-3">
                        <span className="px-3 py-1 rounded-full text-xs font-bold bg-amber-100 text-amber-800">
                          {inv.total_pending_qty} units pending · {formatCurrency(inv.total_pending_value)}
                        </span>
                        {extraItems.length > 0 && (
                          <span className="px-2 py-0.5 rounded text-[11px] font-bold bg-orange-100 text-orange-700">
                            +{extraItems.length} extra
                          </span>
                        )}
                        <ChevronDown
                          className={`w-5 h-5 text-gray-400 transition-transform ${isExpanded ? "rotate-180" : ""}`}
                        />
                      </div>
                    </div>

                    {/* Body */}
                    {isExpanded && (
                      <div className="p-4 sm:p-6 border-t border-gray-100 bg-gray-50/50 space-y-4">
                        <div className="overflow-x-auto bg-white rounded-xl border border-gray-200">
                          <table className="w-full text-left text-xs border-collapse">
                            <thead>
                              <tr className="bg-gray-50 border-b border-gray-200 font-bold text-gray-600 uppercase">
                                <th className="p-3">#</th>
                                <th className="p-3">Item</th>
                                <th className="p-3">HSN</th>
                                <th className="p-3">UOM</th>
                                <th className="p-3 text-right">Unit Cost</th>
                                <th className="p-3 text-right">Ordered</th>
                                <th className="p-3 text-right text-amber-600">Target</th>
                                <th className="p-3 text-right">Received</th>
                                <th className="p-3 text-right text-amber-600">Remaining</th>
                                <th className="p-3 text-center">Receive Now</th>
                              </tr>
                            </thead>
                            <tbody className="divide-y divide-gray-100">
                              {inv.lines
                                .filter(l => l.pending_qty > 0)
                                .map(l => {
                                  const key = `line-${invIdx}-${l.id}`;
                                  const curVal = receiveQtys[key] !== undefined ? receiveQtys[key] : l.pending_qty;
                                  return (
                                    <tr key={l.id} className="hover:bg-gray-50">
                                      <td className="p-3 text-gray-400">{l.line_number}</td>
                                      <td className="p-3 font-semibold text-gray-900">
                                        <div>{l.item_description}</div>
                                        {l.item_code && <div className="text-[11px] text-gray-400">{l.item_code}</div>}
                                      </td>
                                      <td className="p-3 text-gray-500">{l.hsn_code || "—"}</td>
                                      <td className="p-3 text-gray-500">{l.unit_of_measure}</td>
                                      <td className="p-3 text-right font-mono font-medium">{formatCurrency(l.unit_rate)}</td>
                                      <td className="p-3 text-right font-semibold">{l.ordered_qty}</td>
                                      <td className="p-3 text-right">
                                        <input
                                          type="number"
                                          defaultValue={l.configured_pending_qty}
                                          onBlur={e => handleSavePurLineTarget(inv.id, l.id, parseFloat(e.target.value) || 0)}
                                          className="w-16 px-1.5 py-1 text-right bg-amber-50 border border-amber-200 rounded font-semibold text-amber-900 text-xs"
                                        />
                                      </td>
                                      <td className="p-3 text-right text-emerald-600 font-bold">{l.received_qty}</td>
                                      <td className="p-3 text-right font-bold text-amber-600">{l.pending_qty}</td>
                                      <td className="p-3 text-center">
                                        <input
                                          type="number"
                                          value={curVal}
                                          min={0}
                                          max={l.pending_qty}
                                          onChange={e =>
                                            setReceiveQtys(prev => ({
                                              ...prev,
                                              [key]: parseFloat(e.target.value) || 0
                                            }))
                                          }
                                          className="w-20 px-2 py-1 text-center border border-gray-300 rounded font-bold text-xs bg-white"
                                        />
                                      </td>
                                    </tr>
                                  );
                                })}

                              {/* Extra Items */}
                              {extraItems
                                .filter(ei => ei.remaining_qty > 0)
                                .map(ei => {
                                  const key = `ei-${invIdx}-${ei.id}`;
                                  const curVal = receiveQtys[key] !== undefined ? receiveQtys[key] : ei.remaining_qty;
                                  return (
                                    <tr key={ei.id} className="bg-amber-50/40 hover:bg-amber-50/80">
                                      <td className="p-3">
                                        <span className="px-1.5 py-0.5 rounded bg-amber-500 text-white font-black text-[10px]">
                                          +
                                        </span>
                                      </td>
                                      <td className="p-3 font-semibold text-gray-900">
                                        <div>{ei.item_description}</div>
                                        <div className="text-[11px] text-gray-400">{ei.item_code}</div>
                                      </td>
                                      <td className="p-3 text-gray-400">—</td>
                                      <td className="p-3 text-gray-500">{ei.unit_of_measure}</td>
                                      <td className="p-3 text-right text-gray-400">—</td>
                                      <td className="p-3 text-right text-gray-400">—</td>
                                      <td className="p-3 text-right">
                                        <input
                                          type="number"
                                          defaultValue={ei.pending_qty}
                                          onBlur={e => handleSavePurEiTarget(inv.id, ei.id, parseFloat(e.target.value) || 0)}
                                          className="w-16 px-1.5 py-1 text-right bg-amber-50 border border-amber-200 rounded font-semibold text-amber-900 text-xs"
                                        />
                                      </td>
                                      <td className="p-3 text-right text-emerald-600 font-bold">{ei.received_qty}</td>
                                      <td className="p-3 text-right font-bold text-amber-600">{ei.remaining_qty}</td>
                                      <td className="p-3 text-center">
                                        <input
                                          type="number"
                                          value={curVal}
                                          min={0}
                                          max={ei.remaining_qty}
                                          onChange={e =>
                                            setReceiveQtys(prev => ({
                                              ...prev,
                                              [key]: parseFloat(e.target.value) || 0
                                            }))
                                          }
                                          className="w-20 px-2 py-1 text-center border border-gray-300 rounded font-bold text-xs bg-white"
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
                            onClick={() => handleCreateIntakeBatch(inv, invIdx)}
                            className="inline-flex items-center gap-2 px-4 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs rounded-xl transition-all shadow-sm"
                          >
                            <Warehouse className="w-4 h-4" />
                            Create Intake Batch
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

      {/* TAB 3: SUMMARY */}
      {activeTab === "summary" && (
        <div className="space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white p-5 rounded-2xl shadow-sm border border-gray-100">
            <div>
              <h3 className="text-base font-bold text-gray-900 flex items-center gap-2">
                <Layers className="w-5 h-5 text-blue-500" />
                Pending Breakdown Summary
              </h3>
              <p className="text-xs text-gray-500 mt-0.5">Item-wise, day-wise, and vendor-wise breakdown of pending stock receipts</p>
            </div>
            <button
              onClick={loadPurchaseSummary}
              className="inline-flex items-center gap-2 px-3.5 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 text-xs font-bold rounded-xl transition-all"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loadingSummary ? "animate-spin" : ""}`} />
              Refresh
            </button>
          </div>

          {/* Sub-tabs */}
          <div className="flex items-center gap-2">
            <button
              onClick={() => setSummarySubTab("item")}
              className={`px-4 py-2 rounded-xl text-xs font-bold transition-all ${
                summarySubTab === "item"
                  ? "bg-slate-900 text-white shadow-sm"
                  : "bg-white text-gray-600 hover:bg-gray-100 border border-gray-200"
              }`}
            >
              <Package className="w-3.5 h-3.5 inline mr-1.5" />
              Item-wise
            </button>
            <button
              onClick={() => setSummarySubTab("day")}
              className={`px-4 py-2 rounded-xl text-xs font-bold transition-all ${
                summarySubTab === "day"
                  ? "bg-slate-900 text-white shadow-sm"
                  : "bg-white text-gray-600 hover:bg-gray-100 border border-gray-200"
              }`}
            >
              <Calendar className="w-3.5 h-3.5 inline mr-1.5" />
              Day-wise
            </button>
            <button
              onClick={() => setSummarySubTab("vendor")}
              className={`px-4 py-2 rounded-xl text-xs font-bold transition-all ${
                summarySubTab === "vendor"
                  ? "bg-slate-900 text-white shadow-sm"
                  : "bg-white text-gray-600 hover:bg-gray-100 border border-gray-200"
              }`}
            >
              <Truck className="w-3.5 h-3.5 inline mr-1.5" />
              Vendor-wise
            </button>
          </div>

          {/* Content */}
          <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
            {loadingSummary ? (
              <div className="p-12 text-center text-gray-400">
                <RefreshCw className="w-6 h-6 animate-spin mx-auto text-emerald-600 mb-2" />
                Loading summary data...
              </div>
            ) : summarySubTab === "item" ? (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs border-collapse">
                  <thead>
                    <tr className="bg-gray-50 border-b border-gray-200 font-bold text-gray-600 uppercase">
                      <th className="p-3.5">Item</th>
                      <th className="p-3.5 text-right">Pending Qty</th>
                      <th className="p-3.5 text-right">Pending Value</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {itemWiseSummary.length === 0 ? (
                      <tr><td colSpan={3} className="p-8 text-center text-gray-400">No pending item records</td></tr>
                    ) : (
                      itemWiseSummary.map((r, i) => (
                        <tr key={i} className="hover:bg-gray-50">
                          <td className="p-3.5 font-semibold text-gray-900">{r.item}</td>
                          <td className="p-3.5 text-right font-bold text-amber-600">{r.pending_qty}</td>
                          <td className="p-3.5 text-right font-mono font-bold text-emerald-700">{formatCurrency(r.pending_value)}</td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            ) : summarySubTab === "day" ? (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs border-collapse">
                  <thead>
                    <tr className="bg-gray-50 border-b border-gray-200 font-bold text-gray-600 uppercase">
                      <th className="p-3.5">Invoice Date</th>
                      <th className="p-3.5 text-right">Invoices</th>
                      <th className="p-3.5 text-right">Pending Value</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {dayWiseSummary.length === 0 ? (
                      <tr><td colSpan={3} className="p-8 text-center text-gray-400">No pending day records</td></tr>
                    ) : (
                      dayWiseSummary.map((r, i) => (
                        <tr key={i} className="hover:bg-gray-50">
                          <td className="p-3.5 font-semibold text-gray-900">{r.date}</td>
                          <td className="p-3.5 text-right font-bold text-gray-700">{r.invoice_count}</td>
                          <td className="p-3.5 text-right font-mono font-bold text-emerald-700">{formatCurrency(r.pending_value)}</td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs border-collapse">
                  <thead>
                    <tr className="bg-gray-50 border-b border-gray-200 font-bold text-gray-600 uppercase">
                      <th className="p-3.5">Vendor</th>
                      <th className="p-3.5 text-right">Pending Qty</th>
                      <th className="p-3.5 text-right">Pending Value</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {vendorWiseSummary.length === 0 ? (
                      <tr><td colSpan={3} className="p-8 text-center text-gray-400">No pending vendor records</td></tr>
                    ) : (
                      vendorWiseSummary.map((r, i) => (
                        <tr key={i} className="hover:bg-gray-50">
                          <td className="p-3.5 font-semibold text-gray-900">{r.party}</td>
                          <td className="p-3.5 text-right font-bold text-amber-600">{r.pending_qty}</td>
                          <td className="p-3.5 text-right font-mono font-bold text-emerald-700">{formatCurrency(r.pending_value)}</td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ------------------------------------------------------------- */}
      {/* MODAL 1: UPLOAD PURCHASE INVOICE */}
      {/* ------------------------------------------------------------- */}
      {isUploadModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4 overflow-y-auto">
          <div className="bg-white rounded-2xl shadow-2xl border border-gray-100 max-w-2xl w-full max-h-[90vh] overflow-y-auto animate-in zoom-in-95 duration-200">
            <div className="p-5 border-b border-gray-100 flex items-center justify-between sticky top-0 bg-white z-10">
              <h3 className="font-bold text-lg text-gray-900 flex items-center gap-2">
                <Upload className="w-5 h-5 text-emerald-600" />
                Upload Purchase Invoice
              </h3>
              <button
                onClick={() => setIsUploadModalOpen(false)}
                className="text-gray-400 hover:text-gray-600 p-1.5 rounded-lg hover:bg-gray-100 transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleUploadSubmit} className="p-6 space-y-4">
              <div className="p-3.5 bg-emerald-50 text-emerald-800 text-xs rounded-xl flex items-start gap-2.5">
                <Info className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                <span>
                  Upload vendor invoice in PDF, Image (JPG/PNG), Excel or CSV format. Details will be extracted automatically.
                </span>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-bold text-gray-700 mb-1">Company *</label>
                  <select
                    value={uploadCompanyId}
                    onChange={e => {
                      setUploadCompanyId(e.target.value);
                      fetchSegments(e.target.value);
                    }}
                    required
                    className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-xl text-sm font-medium"
                  >
                    <option value="">Select Company</option>
                    {companies.map(c => (
                      <option key={c.id} value={c.id}>
                        {c.company_name || c.name}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-bold text-gray-700 mb-1">Segment</label>
                  <select
                    value={uploadSegmentId}
                    onChange={e => setUploadSegmentId(e.target.value)}
                    className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-xl text-sm font-medium"
                  >
                    <option value="">Select Segment (Optional)</option>
                    {segments.map(s => (
                      <option key={s.id} value={s.id}>
                        {s.segment_name}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div>
                <div className="flex items-center justify-between mb-1">
                  <label className="text-xs font-bold text-gray-700">Vendor (Optional - will be extracted)</label>
                  <button
                    type="button"
                    onClick={handleOpenQcVendor}
                    className="text-xs text-emerald-600 font-bold hover:underline"
                  >
                    + New Vendor
                  </button>
                </div>
                <div className="relative">
                  <input
                    type="text"
                    placeholder="Search vendor or leave blank for AI extraction..."
                    value={uploadVendorSearch}
                    onChange={e => {
                      setUploadVendorSearch(e.target.value);
                      if (!e.target.value) setUploadVendorId("");
                    }}
                    className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-xl text-sm font-medium"
                  />
                  {uploadVendorSearch && !uploadVendorId && (
                    <div className="absolute left-0 right-0 top-full mt-1 bg-white rounded-xl shadow-xl border border-gray-200 max-h-40 overflow-y-auto z-50 divide-y divide-gray-100">
                      {vendors
                        .filter(v =>
                          (v.display_label || v.vendor_name || "").toLowerCase().includes(uploadVendorSearch.toLowerCase())
                        )
                        .slice(0, 8)
                        .map(v => (
                          <div
                            key={v.id}
                            onClick={() => {
                              setUploadVendorId(String(v.id));
                              setUploadVendorSearch(v.display_label || v.vendor_name);
                            }}
                            className="p-2 hover:bg-emerald-50 cursor-pointer text-xs font-medium text-gray-800"
                          >
                            {v.display_label || v.vendor_name}
                          </div>
                        ))}
                    </div>
                  )}
                </div>
              </div>

              {/* Drag & Drop File Zone */}
              <div>
                <label className="block text-xs font-bold text-gray-700 mb-1">Invoice File *</label>
                <div
                  onDragOver={e => e.preventDefault()}
                  onDrop={e => {
                    e.preventDefault();
                    if (e.dataTransfer.files?.[0]) setUploadFile(e.dataTransfer.files[0]);
                  }}
                  onClick={() => document.getElementById("uploadFileInput")?.click()}
                  className="border-2 border-dashed border-gray-300 hover:border-emerald-500 hover:bg-emerald-50/20 p-8 rounded-2xl text-center cursor-pointer transition-all"
                >
                  <input
                    id="uploadFileInput"
                    type="file"
                    accept=".pdf,.jpg,.jpeg,.png,.xlsx,.xls,.csv"
                    onChange={e => {
                      if (e.target.files?.[0]) setUploadFile(e.target.files[0]);
                    }}
                    className="hidden"
                  />
                  {uploadFile ? (
                    <div className="flex items-center justify-center gap-3">
                      <FileText className="w-8 h-8 text-emerald-600" />
                      <div className="text-left">
                        <div className="font-bold text-sm text-gray-900">{uploadFile.name}</div>
                        <div className="text-xs text-gray-400">{(uploadFile.size / 1024 / 1024).toFixed(2)} MB</div>
                      </div>
                      <button
                        type="button"
                        onClick={e => {
                          e.stopPropagation();
                          setUploadFile(null);
                        }}
                        className="p-1 text-red-500 hover:bg-red-50 rounded-lg ml-2"
                      >
                        <X className="w-4 h-4" />
                      </button>
                    </div>
                  ) : (
                    <>
                      <Upload className="w-8 h-8 text-gray-400 mx-auto mb-2" />
                      <p className="text-sm font-bold text-gray-700">Drag & Drop Invoice File here</p>
                      <p className="text-xs text-gray-400 mt-1">or click to browse files (PDF, JPG, PNG, XLSX, CSV, max 10MB)</p>
                    </>
                  )}
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-bold text-gray-700 mb-1">Vendor Invoice No (Optional)</label>
                  <input
                    type="text"
                    placeholder="Enter if known"
                    value={uploadInvoiceNo}
                    onChange={e => setUploadInvoiceNo(e.target.value)}
                    className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-xl text-sm font-medium"
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold text-gray-700 mb-1">Invoice Date (Optional)</label>
                  <input
                    type="date"
                    value={uploadInvoiceDate}
                    onChange={e => setUploadInvoiceDate(e.target.value)}
                    className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-xl text-sm font-medium"
                  />
                </div>
              </div>

              <div className="space-y-3 pt-2">
                <label className="flex items-center gap-2 cursor-pointer text-xs font-bold text-gray-700">
                  <input
                    type="checkbox"
                    checked={uploadCreditPurchase}
                    onChange={e => setUploadCreditPurchase(e.target.checked)}
                    className="w-4 h-4 rounded text-emerald-600"
                  />
                  Credit Purchase
                </label>

                {uploadCreditPurchase && (
                  <div className="grid grid-cols-2 gap-4 p-3 bg-gray-50 rounded-xl border border-gray-200">
                    <div>
                      <label className="block text-xs font-bold text-gray-600 mb-1">Credit Days</label>
                      <input
                        type="number"
                        min={0}
                        value={uploadCreditDays}
                        onChange={e => setUploadCreditDays(parseInt(e.target.value) || 0)}
                        className="w-full px-3 py-1.5 bg-white border border-gray-300 rounded-lg text-xs font-medium"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-bold text-gray-600 mb-1">Due Date</label>
                      <input
                        type="date"
                        value={uploadDueDate}
                        onChange={e => setUploadDueDate(e.target.value)}
                        className="w-full px-3 py-1.5 bg-white border border-gray-300 rounded-lg text-xs font-medium"
                      />
                    </div>
                  </div>
                )}
              </div>

              <div className="flex justify-end gap-3 pt-4 border-t border-gray-100">
                <button
                  type="button"
                  onClick={() => setIsUploadModalOpen(false)}
                  className="px-4 py-2 text-sm font-semibold text-gray-600 bg-gray-100 hover:bg-gray-200 rounded-xl transition-all"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={uploading}
                  className="px-5 py-2 text-sm font-bold text-white bg-emerald-600 hover:bg-emerald-700 rounded-xl transition-all shadow-md shadow-emerald-200 flex items-center gap-2"
                >
                  {uploading && <RefreshCw className="w-4 h-4 animate-spin" />}
                  Upload & Extract
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ------------------------------------------------------------- */}
      {/* MODAL 2: REVIEW & CONFIRM INVOICE */}
      {/* ------------------------------------------------------------- */}
      {isReviewModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4 overflow-y-auto">
          <div className="bg-white rounded-2xl shadow-2xl border border-gray-100 max-w-6xl w-full max-h-[92vh] overflow-y-auto animate-in zoom-in-95 duration-200">
            <div className="p-5 border-b border-gray-100 flex items-center justify-between sticky top-0 bg-white z-10">
              <div>
                <h3 className="font-bold text-lg text-gray-900 flex items-center gap-2">
                  <Edit className="w-5 h-5 text-blue-600" />
                  Review & Edit Invoice — {reviewUploadNumber}
                </h3>
                <p className="text-xs text-gray-500 mt-0.5">{reviewCompanyName}</p>
              </div>
              <button
                onClick={() => setIsReviewModalOpen(false)}
                className="text-gray-400 hover:text-gray-600 p-1.5 rounded-lg hover:bg-gray-100 transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6 space-y-6">
              {reviewMatchingStatus && !reviewMatchingStatus.all_resolved && (
                <div className="p-4 bg-amber-50 border border-amber-200 rounded-2xl text-xs text-amber-900 flex items-start gap-3">
                  <AlertCircle className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
                  <div className="space-y-1">
                    <div className="font-bold text-sm text-amber-900">Some items need attention before confirmation</div>
                    <div className="text-amber-700">
                      {reviewMatchingStatus.unresolved_count || 0} unresolved items (Vendor, Stock Items or HSN). Please map or create them before confirming.
                    </div>
                  </div>
                </div>
              )}

              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                <div className="sm:col-span-2">
                  <div className="flex items-center justify-between mb-1">
                    <label className="text-xs font-bold text-gray-700">Vendor *</label>
                    <button
                      type="button"
                      onClick={handleOpenQcVendor}
                      className="text-xs text-emerald-600 font-bold hover:underline"
                    >
                      + New Vendor
                    </button>
                  </div>
                  <div className="relative">
                    <input
                      type="text"
                      placeholder="Search vendor..."
                      value={reviewVendorSearch}
                      onChange={e => {
                        setReviewVendorSearch(e.target.value);
                        if (!e.target.value) setReviewVendorId("");
                      }}
                      className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-xl text-sm font-medium"
                    />
                    {reviewVendorSearch && !reviewVendorId && (
                      <div className="absolute left-0 right-0 top-full mt-1 bg-white rounded-xl shadow-xl border border-gray-200 max-h-40 overflow-y-auto z-50 divide-y divide-gray-100">
                        {vendors
                          .filter(v =>
                            (v.display_label || v.vendor_name || "").toLowerCase().includes(reviewVendorSearch.toLowerCase())
                          )
                          .slice(0, 8)
                          .map(v => (
                            <div
                              key={v.id}
                              onClick={() => {
                                setReviewVendorId(String(v.id));
                                setReviewVendorSearch(v.display_label || v.vendor_name);
                                if (v.gst_type === "IGST") setReviewIsIgst(true);
                              }}
                              className="p-2 hover:bg-emerald-50 cursor-pointer text-xs font-medium text-gray-800"
                            >
                              {v.display_label || v.vendor_name}
                            </div>
                          ))}
                      </div>
                    )}
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-bold text-gray-700 mb-1">Vendor Invoice No *</label>
                  <input
                    type="text"
                    value={reviewInvoiceNo}
                    onChange={e => setReviewInvoiceNo(e.target.value)}
                    required
                    className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-xl text-sm font-medium"
                  />
                </div>

                <div>
                  <label className="block text-xs font-bold text-gray-700 mb-1">Invoice Date *</label>
                  <input
                    type="date"
                    value={reviewInvoiceDate}
                    onChange={e => setReviewInvoiceDate(e.target.value)}
                    required
                    className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-xl text-sm font-medium"
                  />
                </div>
              </div>

              <div>
                <div className="flex items-center justify-between mb-2">
                  <h4 className="text-sm font-bold text-gray-900">Line Items</h4>
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={() => setReviewIsIgst(!reviewIsIgst)}
                      className={`px-3 py-1 text-xs font-bold rounded-lg transition-all ${
                        reviewIsIgst ? "bg-purple-100 text-purple-700" : "bg-gray-100 text-gray-700"
                      }`}
                    >
                      {reviewIsIgst ? "IGST (Inter-State)" : "CGST + SGST (Intra-State)"}
                    </button>
                    <button
                      type="button"
                      onClick={handleOpenQcStock}
                      className="px-2.5 py-1 bg-white border border-gray-200 text-gray-700 hover:bg-gray-50 text-xs font-bold rounded-lg"
                    >
                      + Stock Item
                    </button>
                    <button
                      type="button"
                      onClick={handleOpenQcHsn}
                      className="px-2.5 py-1 bg-white border border-gray-200 text-gray-700 hover:bg-gray-50 text-xs font-bold rounded-lg"
                    >
                      + HSN
                    </button>
                  </div>
                </div>

                <div className="overflow-x-auto bg-white rounded-xl border border-gray-200">
                  <table className="w-full text-left text-xs border-collapse">
                    <thead>
                      <tr className="bg-gray-50 border-b border-gray-200 font-bold text-gray-600 uppercase">
                        <th className="p-2.5 w-64">Stock Item</th>
                        <th className="p-2.5 w-24">HSN</th>
                        <th className="p-2.5 w-20 text-right">Qty</th>
                        <th className="p-2.5 w-24 text-right">Rate</th>
                        <th className="p-2.5 w-24 text-right">Amount</th>
                        <th className="p-2.5 w-20 text-center">GST %</th>
                        <th className="p-2.5 w-24 text-right">Tax</th>
                        <th className="p-2.5 w-24 text-right">Total</th>
                        <th className="p-2.5 w-24">Serial / S/N</th>
                        <th className="p-2.5 w-10"></th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">
                      {reviewLineItems.map((li, idx) => (
                        <tr key={idx} className="hover:bg-gray-50/60">
                          <td className="p-2">
                            <input
                              type="text"
                              placeholder="Search stock item..."
                              value={li.item_description}
                              onChange={e => handleReviewLineChange(idx, "item_description", e.target.value)}
                              className="w-full px-2 py-1.5 bg-gray-50 border border-gray-200 rounded-lg text-xs font-medium"
                            />
                          </td>
                          <td className="p-2">
                            <input
                              type="text"
                              value={li.hsn_code || ""}
                              onChange={e => handleReviewLineChange(idx, "hsn_code", e.target.value)}
                              className="w-full px-2 py-1.5 bg-gray-50 border border-gray-200 rounded-lg text-xs font-mono"
                            />
                          </td>
                          <td className="p-2 text-right">
                            <input
                              type="number"
                              min={0.001}
                              step={0.001}
                              value={li.quantity}
                              onChange={e => handleReviewLineChange(idx, "quantity", parseFloat(e.target.value) || 0)}
                              className="w-full px-2 py-1.5 bg-gray-50 border border-gray-200 rounded-lg text-xs text-right font-semibold"
                            />
                          </td>
                          <td className="p-2 text-right">
                            <input
                              type="number"
                              step={0.01}
                              value={li.rate}
                              onChange={e => handleReviewLineChange(idx, "rate", parseFloat(e.target.value) || 0)}
                              className="w-full px-2 py-1.5 bg-gray-50 border border-gray-200 rounded-lg text-xs text-right font-mono"
                            />
                          </td>
                          <td className="p-2 text-right font-mono font-medium">{formatCurrency(li.amount)}</td>
                          <td className="p-2 text-center">
                            <input
                              type="number"
                              value={li.gst_rate}
                              onChange={e => handleReviewLineChange(idx, "gst_rate", parseFloat(e.target.value) || 0)}
                              className="w-full px-1.5 py-1.5 bg-gray-50 border border-gray-200 rounded-lg text-xs text-center font-bold"
                            />
                          </td>
                          <td className="p-2 text-right font-mono text-gray-600">{formatCurrency(li.tax_amount || 0)}</td>
                          <td className="p-2 text-right font-mono font-bold text-emerald-700">{formatCurrency(li.total_amount || 0)}</td>
                          <td className="p-2">
                            <input
                              type="text"
                              placeholder="S/N"
                              value={li.serial_numbers || ""}
                              onChange={e => handleReviewLineChange(idx, "serial_numbers", e.target.value)}
                              className="w-full px-2 py-1.5 bg-gray-50 border border-gray-200 rounded-lg text-xs font-mono"
                            />
                          </td>
                          <td className="p-2 text-center">
                            <button
                              type="button"
                              onClick={() => handleRemoveReviewLine(idx)}
                              className="p-1 text-red-500 hover:bg-red-50 rounded"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                <div className="mt-2">
                  <button
                    type="button"
                    onClick={handleAddReviewLine}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-emerald-50 text-emerald-700 hover:bg-emerald-100 font-bold text-xs rounded-lg transition-all"
                  >
                    <Plus className="w-3.5 h-3.5" />
                    Add Line Item
                  </button>
                </div>
              </div>

              {/* Additional Charges */}
              <div className="p-4 bg-sky-50/50 border border-sky-200 rounded-2xl space-y-3">
                <h5 className="text-xs font-bold text-sky-900 uppercase tracking-wider flex items-center gap-1.5">
                  <Truck className="w-4 h-4 text-sky-600" />
                  Additional Freight & Charges (Optional)
                </h5>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className="p-3 bg-white rounded-xl border border-sky-100 space-y-2">
                    <div className="text-xs font-bold text-sky-900">Courier Charges</div>
                    <div className="grid grid-cols-3 gap-2">
                      <div>
                        <label className="text-[10px] text-gray-500 font-bold">Amount (₹)</label>
                        <input
                          type="number"
                          value={reviewCourierAmount || ""}
                          onChange={e => setReviewCourierAmount(parseFloat(e.target.value) || 0)}
                          placeholder="0.00"
                          className="w-full px-2 py-1 bg-gray-50 border border-gray-200 rounded text-xs"
                        />
                      </div>
                      <div>
                        <label className="text-[10px] text-gray-500 font-bold">HSN</label>
                        <input
                          type="text"
                          value={reviewCourierHsnCode}
                          onChange={e => setReviewCourierHsnCode(e.target.value)}
                          placeholder="996812"
                          className="w-full px-2 py-1 bg-gray-50 border border-gray-200 rounded text-xs"
                        />
                      </div>
                      <div>
                        <label className="text-[10px] text-gray-500 font-bold">GST %</label>
                        <input
                          type="number"
                          value={reviewCourierGstRate || ""}
                          onChange={e => setReviewCourierGstRate(parseFloat(e.target.value) || 0)}
                          placeholder="18"
                          className="w-full px-2 py-1 bg-gray-50 border border-gray-200 rounded text-xs"
                        />
                      </div>
                    </div>
                  </div>

                  <div className="p-3 bg-white rounded-xl border border-sky-100 space-y-2">
                    <div className="text-xs font-bold text-sky-900">Transport Charges</div>
                    <div className="grid grid-cols-3 gap-2">
                      <div>
                        <label className="text-[10px] text-gray-500 font-bold">Amount (₹)</label>
                        <input
                          type="number"
                          value={reviewTransportAmount || ""}
                          onChange={e => setReviewTransportAmount(parseFloat(e.target.value) || 0)}
                          placeholder="0.00"
                          className="w-full px-2 py-1 bg-gray-50 border border-gray-200 rounded text-xs"
                        />
                      </div>
                      <div>
                        <label className="text-[10px] text-gray-500 font-bold">HSN</label>
                        <input
                          type="text"
                          value={reviewTransportHsnCode}
                          onChange={e => setReviewTransportHsnCode(e.target.value)}
                          placeholder="996601"
                          className="w-full px-2 py-1 bg-gray-50 border border-gray-200 rounded text-xs"
                        />
                      </div>
                      <div>
                        <label className="text-[10px] text-gray-500 font-bold">GST %</label>
                        <input
                          type="number"
                          value={reviewTransportGstRate || ""}
                          onChange={e => setReviewTransportGstRate(parseFloat(e.target.value) || 0)}
                          placeholder="5"
                          className="w-full px-2 py-1 bg-gray-50 border border-gray-200 rounded text-xs"
                        />
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* GST Summary & Totals */}
              <div className="p-4 bg-emerald-50/50 border border-emerald-200 rounded-2xl space-y-2">
                <h5 className="text-xs font-bold text-emerald-900 uppercase tracking-wider">GST Summary</h5>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                  <div>
                    <span className="text-gray-500">Taxable Amount:</span>
                    <div className="font-bold text-sm font-mono text-gray-900">
                      {formatCurrency(reviewCalculations.taxable)}
                    </div>
                  </div>
                  {reviewIsIgst ? (
                    <div>
                      <span className="text-gray-500">IGST:</span>
                      <div className="font-bold text-sm font-mono text-purple-700">
                        {formatCurrency(reviewCalculations.igst)}
                      </div>
                    </div>
                  ) : (
                    <>
                      <div>
                        <span className="text-gray-500">CGST:</span>
                        <div className="font-bold text-sm font-mono text-gray-800">
                          {formatCurrency(reviewCalculations.cgst)}
                        </div>
                      </div>
                      <div>
                        <span className="text-gray-500">SGST:</span>
                        <div className="font-bold text-sm font-mono text-gray-800">
                          {formatCurrency(reviewCalculations.sgst)}
                        </div>
                      </div>
                    </>
                  )}
                  <div>
                    <span className="text-gray-500">Total Tax:</span>
                    <div className="font-bold text-sm font-mono text-gray-900">
                      {formatCurrency(reviewCalculations.totalTax)}
                    </div>
                  </div>
                </div>

                <div className="pt-2 border-t border-emerald-200 flex items-center justify-between flex-wrap gap-4">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold text-gray-700">Round Off:</span>
                    <input
                      type="number"
                      step={0.01}
                      value={reviewRoundOff}
                      onChange={e => setReviewRoundOff(parseFloat(e.target.value) || 0)}
                      className="w-20 px-2 py-1 bg-white border border-gray-300 rounded text-xs text-right font-bold"
                    />
                    <button
                      type="button"
                      onClick={handleAutoCalcRoundOff}
                      className="px-2 py-1 bg-gray-200 hover:bg-gray-300 text-gray-700 text-[10px] font-bold rounded"
                    >
                      Auto
                    </button>
                  </div>

                  <div className="text-right">
                    <span className="text-xs text-gray-500 font-bold uppercase">Grand Total:</span>
                    <div className="text-2xl font-black font-mono text-emerald-800">
                      {formatCurrency(reviewCalculations.grandTotal)}
                    </div>
                  </div>
                </div>
              </div>

              {/* Narration & History */}
              <div className="space-y-2">
                <label className="block text-xs font-bold text-gray-700">Narration</label>
                <textarea
                  value={reviewNotes}
                  onChange={e => setReviewNotes(e.target.value)}
                  placeholder="Add a narration note for this invoice..."
                  className="w-full p-3 bg-gray-50 border border-gray-200 rounded-xl text-sm font-medium"
                  rows={2}
                />
                <div className="flex justify-end">
                  <button
                    type="button"
                    onClick={() => handleAddNarration("review", reviewId, reviewNotes)}
                    className="px-3 py-1 text-xs font-bold bg-slate-900 text-white rounded-lg hover:bg-slate-800"
                  >
                    + Log Narration Entry
                  </button>
                </div>

                {reviewNarrations.length > 0 && (
                  <div className="p-3 bg-gray-50 rounded-xl border border-gray-200 max-h-36 overflow-y-auto space-y-2">
                    <div className="text-[11px] font-bold text-gray-500 uppercase">Narration History</div>
                    {reviewNarrations.map((n, i) => (
                      <div key={i} className="text-xs text-gray-700 border-b border-gray-200 pb-1.5 last:border-none">
                        <div>{n.narration}</div>
                        <div className="text-[10px] text-gray-400 mt-0.5">
                          {n.created_by_name} · {n.created_at ? new Date(n.created_at).toLocaleString("en-IN") : ""}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Footer */}
              <div className="flex justify-end gap-3 pt-4 border-t border-gray-100">
                <button
                  type="button"
                  onClick={() => setIsReviewModalOpen(false)}
                  className="px-4 py-2 text-sm font-semibold text-gray-600 bg-gray-100 hover:bg-gray-200 rounded-xl transition-all"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleSaveReview}
                  disabled={savingReview}
                  className="px-4 py-2 text-sm font-bold text-blue-600 bg-blue-50 hover:bg-blue-100 rounded-xl transition-all"
                >
                  {savingReview ? "Saving..." : "Save Draft Changes"}
                </button>
                <button
                  type="button"
                  onClick={handleConfirmInvoice}
                  disabled={confirmingReview}
                  className="px-5 py-2 text-sm font-bold text-white bg-emerald-600 hover:bg-emerald-700 rounded-xl transition-all shadow-md shadow-emerald-200 flex items-center gap-2"
                >
                  {confirmingReview ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Check className="w-4 h-4" />}
                  Confirm & Process
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ------------------------------------------------------------- */}
      {/* MODAL 3: VIEW INVOICE */}
      {/* ------------------------------------------------------------- */}
      {isViewModalOpen && viewInvoiceData && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4 overflow-y-auto">
          <div className="bg-white rounded-2xl shadow-2xl border border-gray-100 max-w-4xl w-full max-h-[90vh] overflow-y-auto animate-in zoom-in-95 duration-200">
            <div className="p-5 border-b border-gray-100 flex items-center justify-between sticky top-0 bg-white z-10">
              <div>
                <h3 className="font-bold text-lg text-gray-900 flex items-center gap-2">
                  <Eye className="w-5 h-5 text-indigo-600" />
                  View Invoice — {viewInvoiceData.upload_number}
                </h3>
                <span className="text-xs text-gray-400">{viewInvoiceData.company_name}</span>
              </div>
              <button
                onClick={() => setIsViewModalOpen(false)}
                className="text-gray-400 hover:text-gray-600 p-1.5 rounded-lg hover:bg-gray-100 transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6 space-y-6">
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 p-4 bg-gray-50 rounded-2xl border border-gray-100 text-xs">
                <div>
                  <span className="text-gray-400 font-bold uppercase">Vendor</span>
                  <div className="font-bold text-gray-900 mt-0.5">{viewInvoiceData.vendor_name || "—"}</div>
                </div>
                <div>
                  <span className="text-gray-400 font-bold uppercase">Invoice No</span>
                  <div className="font-bold font-mono text-gray-900 mt-0.5">{viewInvoiceData.vendor_invoice_no || "—"}</div>
                </div>
                <div>
                  <span className="text-gray-400 font-bold uppercase">Invoice Date</span>
                  <div className="font-bold text-gray-900 mt-0.5">
                    {viewInvoiceData.vendor_invoice_date ? new Date(viewInvoiceData.vendor_invoice_date).toLocaleDateString("en-IN") : "—"}
                  </div>
                </div>
                <div>
                  <span className="text-gray-400 font-bold uppercase">Status</span>
                  <div className="mt-0.5">
                    <span className="px-2 py-0.5 rounded-full font-bold bg-emerald-100 text-emerald-800">
                      {viewInvoiceData.status}
                    </span>
                  </div>
                </div>
              </div>

              {viewInvoiceData.file_path && (
                <div className="p-3 bg-blue-50/60 border border-blue-200 rounded-xl flex items-center justify-between">
                  <div className="flex items-center gap-2 text-xs font-semibold text-blue-900">
                    <FileText className="w-4 h-4 text-blue-600" />
                    <span>Uploaded File: {viewInvoiceData.original_filename || "Original Invoice"}</span>
                  </div>
                  <a
                    href={`/storage/${viewInvoiceData.file_path}`}
                    target="_blank"
                    rel="noreferrer"
                    className="text-xs font-bold text-blue-600 hover:underline flex items-center gap-1"
                  >
                    Download File <ExternalLink className="w-3.5 h-3.5" />
                  </a>
                </div>
              )}

              <div>
                <h4 className="text-xs font-bold text-gray-700 uppercase tracking-wider mb-2">Line Items</h4>
                <div className="overflow-x-auto bg-white rounded-xl border border-gray-200">
                  <table className="w-full text-left text-xs border-collapse">
                    <thead>
                      <tr className="bg-gray-50 border-b border-gray-200 font-bold text-gray-600 uppercase">
                        <th className="p-3">Item</th>
                        <th className="p-3">HSN</th>
                        <th className="p-3 text-right">Qty</th>
                        <th className="p-3 text-right">Rate</th>
                        <th className="p-3 text-right">Amount</th>
                        <th className="p-3 text-center">GST</th>
                        <th className="p-3 text-right">Tax</th>
                        <th className="p-3 text-right">Total</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">
                      {(viewInvoiceData.line_items || []).map((li, idx) => (
                        <tr key={idx} className="hover:bg-gray-50">
                          <td className="p-3 font-semibold text-gray-900">{li.item_description}</td>
                          <td className="p-3 text-gray-500">{li.hsn_code || "—"}</td>
                          <td className="p-3 text-right font-semibold">{li.quantity}</td>
                          <td className="p-3 text-right font-mono">{formatCurrency(li.rate)}</td>
                          <td className="p-3 text-right font-mono">{formatCurrency(li.amount)}</td>
                          <td className="p-3 text-center font-bold">{li.gst_rate}%</td>
                          <td className="p-3 text-right font-mono text-gray-600">{formatCurrency(li.tax_amount || 0)}</td>
                          <td className="p-3 text-right font-mono font-bold text-emerald-700">{formatCurrency(li.total_amount || 0)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              <div className="p-4 bg-emerald-50/50 rounded-2xl border border-emerald-200 space-y-2">
                <div className="flex items-center justify-between text-xs text-gray-600">
                  <span>Taxable Amount:</span>
                  <span className="font-mono font-bold">{formatCurrency(viewInvoiceData.taxable_amount || 0)}</span>
                </div>
                <div className="flex items-center justify-between text-xs text-gray-600">
                  <span>Total Tax:</span>
                  <span className="font-mono font-bold">{formatCurrency(viewInvoiceData.total_tax || 0)}</span>
                </div>
                {Number(viewInvoiceData.courier_amount || 0) > 0 && (
                  <div className="flex items-center justify-between text-xs text-gray-600">
                    <span>Courier Charges:</span>
                    <span className="font-mono font-bold">{formatCurrency(viewInvoiceData.courier_amount || 0)}</span>
                  </div>
                )}
                {Number(viewInvoiceData.transport_amount || 0) > 0 && (
                  <div className="flex items-center justify-between text-xs text-gray-600">
                    <span>Transport Charges:</span>
                    <span className="font-mono font-bold">{formatCurrency(viewInvoiceData.transport_amount || 0)}</span>
                  </div>
                )}
                <div className="pt-2 border-t border-emerald-200 flex items-center justify-between text-sm font-black text-emerald-900">
                  <span>Grand Total:</span>
                  <span className="font-mono text-xl">{formatCurrency(viewInvoiceData.grand_total || 0)}</span>
                </div>
              </div>

              {viewNarrations.length > 0 && (
                <div className="space-y-2">
                  <h5 className="text-xs font-bold text-gray-700 uppercase">Narration History</h5>
                  <div className="p-3 bg-gray-50 rounded-xl border border-gray-200 max-h-36 overflow-y-auto space-y-2">
                    {viewNarrations.map((n, i) => (
                      <div key={i} className="text-xs text-gray-700 border-b border-gray-200 pb-1.5 last:border-none">
                        <div>{n.narration}</div>
                        <div className="text-[10px] text-gray-400 mt-0.5">
                          {n.created_by_name} · {n.created_at ? new Date(n.created_at).toLocaleString("en-IN") : ""}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <div className="flex justify-between items-center pt-4 border-t border-gray-100">
                <button
                  onClick={() => handleDownloadPdf(viewInvoiceData.id, viewInvoiceData.company_id)}
                  className="px-4 py-2 bg-indigo-50 hover:bg-indigo-100 text-indigo-700 font-bold text-xs rounded-xl transition-all flex items-center gap-1.5"
                >
                  <Download className="w-4 h-4" />
                  Download PDF
                </button>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => {
                      setIsViewModalOpen(false);
                      handleOpenReviewModal(viewInvoiceData.id);
                    }}
                    className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs rounded-xl transition-all"
                  >
                    Edit Invoice
                  </button>
                  <button
                    onClick={() => setIsViewModalOpen(false)}
                    className="px-4 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 font-bold text-xs rounded-xl transition-all"
                  >
                    Close
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ------------------------------------------------------------- */}
      {/* MODAL 4: MANUAL INVOICE ENTRY */}
      {/* ------------------------------------------------------------- */}
      {isManualModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4 overflow-y-auto">
          <div className="bg-white rounded-2xl shadow-2xl border border-gray-100 max-w-6xl w-full max-h-[92vh] overflow-y-auto animate-in zoom-in-95 duration-200">
            <div className="p-5 border-b border-gray-100 flex items-center justify-between sticky top-0 bg-white z-10">
              <h3 className="font-bold text-lg text-gray-900 flex items-center gap-2">
                <Edit className="w-5 h-5 text-emerald-600" />
                Create Manual Purchase Invoice
              </h3>
              <button
                onClick={() => setIsManualModalOpen(false)}
                className="text-gray-400 hover:text-gray-600 p-1.5 rounded-lg hover:bg-gray-100 transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6 space-y-6">
              <div className="p-3 bg-gray-50 border border-gray-200 rounded-xl flex items-center gap-6 flex-wrap">
                <span className="text-xs font-bold text-gray-700">Document Type:</span>
                <label className="flex items-center gap-2 text-xs font-bold text-gray-700 cursor-pointer">
                  <input
                    type="radio"
                    name="manualDocType"
                    value="invoice"
                    checked={manualDocType === "invoice"}
                    onChange={() => setManualDocType("invoice")}
                    className="text-emerald-600"
                  />
                  Purchase Invoice
                </label>
                <label className="flex items-center gap-2 text-xs font-bold text-amber-700 cursor-pointer">
                  <input
                    type="radio"
                    name="manualDocType"
                    value="purchase_return"
                    checked={manualDocType === "purchase_return"}
                    onChange={() => setManualDocType("purchase_return")}
                    className="text-amber-600"
                  />
                  Purchase Return (Debit Note)
                </label>
              </div>

              {manualDocType === "purchase_return" && (
                <div className="p-3 bg-amber-50 border border-amber-200 rounded-xl">
                  <label className="block text-xs font-bold text-amber-800 mb-1">
                    Original Invoice / PO Reference
                  </label>
                  <input
                    type="text"
                    placeholder="e.g. PUR-2026-001"
                    value={manualReturnRef}
                    onChange={e => setManualReturnRef(e.target.value)}
                    className="w-full px-3 py-1.5 bg-white border border-amber-300 rounded-lg text-xs font-medium"
                  />
                </div>
              )}

              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                <div>
                  <label className="block text-xs font-bold text-gray-700 mb-1">Company *</label>
                  <select
                    value={manualCompanyId}
                    onChange={e => {
                      setManualCompanyId(e.target.value);
                      fetchSegments(e.target.value);
                    }}
                    required
                    className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-xl text-sm font-medium"
                  >
                    <option value="">Select Company</option>
                    {companies.map(c => (
                      <option key={c.id} value={c.id}>
                        {c.company_name || c.name}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-bold text-gray-700 mb-1">Segment</label>
                  <select
                    value={manualSegmentId}
                    onChange={e => setManualSegmentId(e.target.value)}
                    className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-xl text-sm font-medium"
                  >
                    <option value="">Select Segment (Optional)</option>
                    {segments.map(s => (
                      <option key={s.id} value={s.id}>
                        {s.segment_name}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="sm:col-span-2">
                  <div className="flex items-center justify-between mb-1">
                    <label className="text-xs font-bold text-gray-700">Vendor *</label>
                    <button
                      type="button"
                      onClick={handleOpenQcVendor}
                      className="text-xs text-emerald-600 font-bold hover:underline"
                    >
                      + New Vendor
                    </button>
                  </div>
                  <div className="relative">
                    <input
                      type="text"
                      placeholder="Search vendor..."
                      value={manualVendorSearch}
                      onChange={e => {
                        setManualVendorSearch(e.target.value);
                        if (!e.target.value) setManualVendorId("");
                      }}
                      className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-xl text-sm font-medium"
                    />
                    {manualVendorSearch && !manualVendorId && (
                      <div className="absolute left-0 right-0 top-full mt-1 bg-white rounded-xl shadow-xl border border-gray-200 max-h-40 overflow-y-auto z-50 divide-y divide-gray-100">
                        {vendors
                          .filter(v =>
                            (v.display_label || v.vendor_name || "").toLowerCase().includes(manualVendorSearch.toLowerCase())
                          )
                          .slice(0, 8)
                          .map(v => (
                            <div
                              key={v.id}
                              onClick={() => {
                                setManualVendorId(String(v.id));
                                setManualVendorSearch(v.display_label || v.vendor_name);
                                if (v.gst_type === "IGST") setManualGstType("IGST");
                              }}
                              className="p-2 hover:bg-emerald-50 cursor-pointer text-xs font-medium text-gray-800"
                            >
                              {v.display_label || v.vendor_name}
                            </div>
                          ))}
                      </div>
                    )}
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div>
                  <label className="block text-xs font-bold text-gray-700 mb-1">Vendor Invoice No *</label>
                  <input
                    type="text"
                    value={manualInvoiceNo}
                    onChange={e => setManualInvoiceNo(e.target.value)}
                    required
                    placeholder="e.g. INV-1002"
                    className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-xl text-sm font-medium"
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold text-gray-700 mb-1">Invoice Date *</label>
                  <input
                    type="date"
                    value={manualInvoiceDate}
                    onChange={e => setManualInvoiceDate(e.target.value)}
                    required
                    className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-xl text-sm font-medium"
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold text-gray-700 mb-1">Due Date</label>
                  <input
                    type="date"
                    value={manualDueDate}
                    onChange={e => setManualDueDate(e.target.value)}
                    className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-xl text-sm font-medium"
                  />
                </div>
              </div>

              <div>
                <div className="flex items-center justify-between mb-2">
                  <h4 className="text-sm font-bold text-gray-900">Line Items</h4>
                  <div className="flex items-center gap-2">
                    <div className="flex items-center bg-gray-100 p-0.5 rounded-lg border border-gray-200">
                      <button
                        type="button"
                        onClick={() => setManualGstType("CGST_SGST")}
                        className={`px-2.5 py-1 text-xs font-bold rounded-md transition-all ${
                          manualGstType === "CGST_SGST" ? "bg-purple-600 text-white shadow-sm" : "text-gray-600"
                        }`}
                      >
                        CGST + SGST
                      </button>
                      <button
                        type="button"
                        onClick={() => setManualGstType("IGST")}
                        className={`px-2.5 py-1 text-xs font-bold rounded-md transition-all ${
                          manualGstType === "IGST" ? "bg-purple-600 text-white shadow-sm" : "text-gray-600"
                        }`}
                      >
                        IGST
                      </button>
                    </div>
                    <button
                      type="button"
                      onClick={handleOpenQcStock}
                      className="px-2.5 py-1 bg-white border border-gray-200 text-gray-700 hover:bg-gray-50 text-xs font-bold rounded-lg"
                    >
                      + Stock Item
                    </button>
                  </div>
                </div>

                <div className="overflow-x-auto bg-white rounded-xl border border-gray-200">
                  <table className="w-full text-left text-xs border-collapse">
                    <thead>
                      <tr className="bg-gray-50 border-b border-gray-200 font-bold text-gray-600 uppercase">
                        <th className="p-2.5 w-60">Stock Item</th>
                        <th className="p-2.5 w-24">HSN</th>
                        <th className="p-2.5 w-16 text-right">Qty</th>
                        <th className="p-2.5 w-24 text-right">Rate</th>
                        <th className="p-2.5 w-24 text-right">Amount</th>
                        <th className="p-2.5 w-16 text-center">GST %</th>
                        {manualGstType === "IGST" ? (
                          <th className="p-2.5 w-24 text-right">IGST</th>
                        ) : (
                          <>
                            <th className="p-2.5 w-20 text-right">CGST</th>
                            <th className="p-2.5 w-20 text-right">SGST</th>
                          </>
                        )}
                        <th className="p-2.5 w-24 text-right">Total</th>
                        <th className="p-2.5 w-20">S/N</th>
                        <th className="p-2.5 w-10"></th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">
                      {manualLineItems.map((li, idx) => (
                        <tr key={idx} className="hover:bg-gray-50/60">
                          <td className="p-2">
                            <input
                              type="text"
                              placeholder="Search item..."
                              value={li.item_description}
                              onChange={e => handleManualLineChange(idx, "item_description", e.target.value)}
                              className="w-full px-2 py-1 bg-gray-50 border border-gray-200 rounded-lg text-xs font-medium"
                            />
                          </td>
                          <td className="p-2">
                            <input
                              type="text"
                              value={li.hsn_code || ""}
                              onChange={e => handleManualLineChange(idx, "hsn_code", e.target.value)}
                              className="w-full px-2 py-1 bg-gray-50 border border-gray-200 rounded-lg text-xs font-mono"
                            />
                          </td>
                          <td className="p-2 text-right">
                            <input
                              type="number"
                              min={0.001}
                              step={0.001}
                              value={li.quantity}
                              onChange={e => handleManualLineChange(idx, "quantity", parseFloat(e.target.value) || 0)}
                              className="w-full px-1.5 py-1 bg-gray-50 border border-gray-200 rounded-lg text-xs text-right font-semibold"
                            />
                          </td>
                          <td className="p-2 text-right">
                            <input
                              type="number"
                              step={0.01}
                              value={li.rate}
                              onChange={e => handleManualLineChange(idx, "rate", parseFloat(e.target.value) || 0)}
                              className="w-full px-1.5 py-1 bg-gray-50 border border-gray-200 rounded-lg text-xs text-right font-mono"
                            />
                          </td>
                          <td className="p-2 text-right font-mono font-medium">{formatCurrency(li.amount)}</td>
                          <td className="p-2 text-center">
                            <input
                              type="number"
                              value={li.gst_rate}
                              onChange={e => handleManualLineChange(idx, "gst_rate", parseFloat(e.target.value) || 0)}
                              className="w-full px-1 py-1 bg-gray-50 border border-gray-200 rounded-lg text-xs text-center font-bold"
                            />
                          </td>
                          {manualGstType === "IGST" ? (
                            <td className="p-2 text-right font-mono text-purple-700">{formatCurrency(li.tax_amount || 0)}</td>
                          ) : (
                            <>
                              <td className="p-2 text-right font-mono text-gray-600">{formatCurrency((li.tax_amount || 0) / 2)}</td>
                              <td className="p-2 text-right font-mono text-gray-600">{formatCurrency((li.tax_amount || 0) / 2)}</td>
                            </>
                          )}
                          <td className="p-2 text-right font-mono font-bold text-emerald-700">{formatCurrency(li.total_amount || 0)}</td>
                          <td className="p-2">
                            <input
                              type="text"
                              placeholder="S/N"
                              value={li.serial_numbers || ""}
                              onChange={e => handleManualLineChange(idx, "serial_numbers", e.target.value)}
                              className="w-full px-1.5 py-1 bg-gray-50 border border-gray-200 rounded-lg text-xs font-mono"
                            />
                          </td>
                          <td className="p-2 text-center">
                            <button
                              type="button"
                              onClick={() => handleRemoveManualLine(idx)}
                              className="p-1 text-red-500 hover:bg-red-50 rounded"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                <div className="mt-2">
                  <button
                    type="button"
                    onClick={handleAddManualLine}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-emerald-50 text-emerald-700 hover:bg-emerald-100 font-bold text-xs rounded-lg transition-all"
                  >
                    <Plus className="w-3.5 h-3.5" />
                    Add Line
                  </button>
                </div>
              </div>

              {manualCalculations.hsnSummary.length > 0 && (
                <div className="p-4 bg-gray-50 border border-gray-200 rounded-2xl space-y-2">
                  <h5 className="text-xs font-bold text-gray-700 uppercase tracking-wider">HSN / SAC Summary</h5>
                  <div className="overflow-x-auto bg-white rounded-xl border border-gray-200">
                    <table className="w-full text-left text-xs border-collapse">
                      <thead>
                        <tr className="bg-gray-50 border-b border-gray-200 font-bold text-gray-600">
                          <th className="p-2.5">HSN Code</th>
                          <th className="p-2.5 text-right">Taxable Value</th>
                          <th className="p-2.5 text-center">CGST %</th>
                          <th className="p-2.5 text-right">CGST Amt</th>
                          <th className="p-2.5 text-center">SGST %</th>
                          <th className="p-2.5 text-right">SGST Amt</th>
                          <th className="p-2.5 text-right">Total Tax</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-100">
                        {manualCalculations.hsnSummary.map((h, i) => (
                          <tr key={i}>
                            <td className="p-2.5 font-bold text-gray-800">{h.hsn_code}</td>
                            <td className="p-2.5 text-right font-mono">{formatCurrency(h.taxable)}</td>
                            <td className="p-2.5 text-center">{h.cgstRate}%</td>
                            <td className="p-2.5 text-right font-mono">{formatCurrency(h.cgstAmt)}</td>
                            <td className="p-2.5 text-center">{h.sgstRate}%</td>
                            <td className="p-2.5 text-right font-mono">{formatCurrency(h.sgstAmt)}</td>
                            <td className="p-2.5 text-right font-mono font-bold text-emerald-700">{formatCurrency(h.totalTax)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              <div className="p-4 bg-emerald-50/50 border border-emerald-200 rounded-2xl space-y-3">
                <h5 className="text-xs font-bold text-emerald-900 uppercase tracking-wider">GST Summary</h5>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                  <div>
                    <span className="text-gray-500">Taxable Amount:</span>
                    <div className="font-bold text-sm font-mono text-gray-900">{formatCurrency(manualCalculations.taxable)}</div>
                  </div>
                  {manualGstType === "IGST" ? (
                    <div>
                      <span className="text-gray-500">IGST:</span>
                      <div className="font-bold text-sm font-mono text-purple-700">{formatCurrency(manualCalculations.totalIgst)}</div>
                    </div>
                  ) : (
                    <>
                      <div>
                        <span className="text-gray-500">CGST:</span>
                        <div className="font-bold text-sm font-mono text-gray-800">{formatCurrency(manualCalculations.totalCgst)}</div>
                      </div>
                      <div>
                        <span className="text-gray-500">SGST:</span>
                        <div className="font-bold text-sm font-mono text-gray-800">{formatCurrency(manualCalculations.totalSgst)}</div>
                      </div>
                    </>
                  )}
                  <div>
                    <span className="text-gray-500">Total Tax:</span>
                    <div className="font-bold text-sm font-mono text-gray-900">{formatCurrency(manualCalculations.totalTax)}</div>
                  </div>
                </div>

                <div className="pt-2 border-t border-emerald-200 flex items-center justify-between flex-wrap gap-4">
                  <div className="flex items-center gap-2 text-xs">
                    <span className="font-bold text-gray-700">Rounding (+/-):</span>
                    <input
                      type="number"
                      step={0.01}
                      value={manualRounding}
                      onChange={e => setManualRounding(parseFloat(e.target.value) || 0)}
                      className="w-20 px-2 py-1 bg-white border border-gray-300 rounded text-xs text-right font-bold"
                    />
                  </div>

                  <div className="text-right">
                    <span className="text-xs text-gray-500 font-bold uppercase">Grand Total:</span>
                    <div className="text-2xl font-black font-mono text-emerald-800">
                      {formatCurrency(manualCalculations.grandTotal)}
                    </div>
                  </div>
                </div>

                <div className="p-2.5 bg-amber-50 border border-amber-200 rounded-xl text-xs">
                  <span className="font-bold text-amber-900">Amount in Words: </span>
                  <span className="text-amber-800 italic">{convertToIndianWords(manualCalculations.grandTotal)}</span>
                </div>
              </div>

              <div className="space-y-3">
                <label className="flex items-center gap-2 cursor-pointer text-xs font-bold text-gray-700">
                  <input
                    type="checkbox"
                    checked={manualCreditPurchase}
                    onChange={e => setManualCreditPurchase(e.target.checked)}
                    className="w-4 h-4 rounded text-emerald-600"
                  />
                  Credit Purchase
                </label>

                {manualCreditPurchase && (
                  <div className="p-3 bg-gray-50 rounded-xl border border-gray-200 w-48">
                    <label className="block text-xs font-bold text-gray-600 mb-1">Credit Days</label>
                    <input
                      type="number"
                      min={0}
                      value={manualCreditDays}
                      onChange={e => setManualCreditDays(parseInt(e.target.value) || 0)}
                      className="w-full px-3 py-1.5 bg-white border border-gray-300 rounded-lg text-xs font-medium"
                    />
                  </div>
                )}

                <div>
                  <label className="block text-xs font-bold text-gray-700 mb-1">Narration</label>
                  <textarea
                    value={manualNotes}
                    onChange={e => setManualNotes(e.target.value)}
                    placeholder="Add a narration note..."
                    rows={2}
                    className="w-full p-3 bg-gray-50 border border-gray-200 rounded-xl text-sm font-medium"
                  />
                </div>
              </div>

              <div className="flex justify-end gap-3 pt-4 border-t border-gray-100">
                <button
                  type="button"
                  onClick={() => setIsManualModalOpen(false)}
                  className="px-4 py-2 text-sm font-semibold text-gray-600 bg-gray-100 hover:bg-gray-200 rounded-xl transition-all"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={() => handleSaveManualInvoice(false)}
                  disabled={savingManual}
                  className="px-4 py-2 text-sm font-bold text-emerald-700 bg-emerald-50 hover:bg-emerald-100 rounded-xl transition-all"
                >
                  Save as Draft
                </button>
                <button
                  type="button"
                  onClick={() => handleSaveManualInvoice(true)}
                  disabled={savingManual}
                  className="px-5 py-2 text-sm font-bold text-white bg-emerald-600 hover:bg-emerald-700 rounded-xl transition-all shadow-md shadow-emerald-200 flex items-center gap-2"
                >
                  {savingManual ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Check className="w-4 h-4" />}
                  Save & Confirm
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ------------------------------------------------------------- */}
      {/* MODAL 5: REJECT INVOICE */}
      {/* ------------------------------------------------------------- */}
      {isRejectModalOpen && selectedInvoice && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4 overflow-y-auto">
          <div className="bg-white rounded-2xl shadow-2xl border border-gray-100 max-w-md w-full animate-in zoom-in-95 duration-200">
            <div className="p-5 border-b border-gray-100 flex items-center justify-between">
              <h3 className="font-bold text-base text-gray-900 flex items-center gap-2 text-red-600">
                <XCircle className="w-5 h-5" />
                Reject Purchase Invoice
              </h3>
              <button
                onClick={() => setIsRejectModalOpen(false)}
                className="text-gray-400 hover:text-gray-600 p-1.5 rounded-lg hover:bg-gray-100"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6 space-y-4">
              <p className="text-xs text-gray-600">
                Are you sure you want to reject this purchase invoice?
              </p>
              <div className="p-3 bg-red-50 border border-red-200 rounded-xl text-xs space-y-1 text-red-900">
                <div><strong>Upload #:</strong> {selectedInvoice.upload_number}</div>
                <div><strong>Vendor:</strong> {selectedInvoice.vendor_name || "—"}</div>
                <div><strong>Amount:</strong> {formatCurrency(selectedInvoice.grand_total || 0)}</div>
              </div>

              <div>
                <label className="block text-xs font-bold text-gray-700 mb-1">Rejection Reason *</label>
                <textarea
                  value={rejectReason}
                  onChange={e => setRejectReason(e.target.value)}
                  placeholder="Please provide a clear reason for rejection..."
                  rows={3}
                  className="w-full p-2.5 bg-gray-50 border border-gray-200 rounded-xl text-xs font-medium"
                />
              </div>

              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setIsRejectModalOpen(false)}
                  className="px-4 py-2 text-xs font-semibold text-gray-600 bg-gray-100 hover:bg-gray-200 rounded-xl"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleConfirmReject}
                  disabled={rejecting}
                  className="px-4 py-2 text-xs font-bold text-white bg-red-600 hover:bg-red-700 rounded-xl flex items-center gap-1.5"
                >
                  {rejecting && <RefreshCw className="w-3.5 h-3.5 animate-spin" />}
                  Reject Invoice
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ------------------------------------------------------------- */}
      {/* MODAL 6: ADD PENDING INVOICE MODAL */}
      {/* ------------------------------------------------------------- */}
      {isAddPendingModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4 overflow-y-auto">
          <div className="bg-white rounded-2xl shadow-2xl border border-gray-100 max-w-2xl w-full max-h-[90vh] overflow-y-auto animate-in zoom-in-95 duration-200">
            <div className="p-5 border-b border-gray-100 flex items-center justify-between sticky top-0 bg-white z-10">
              <h3 className="font-bold text-base text-gray-900 flex items-center gap-2">
                <Plus className="w-5 h-5 text-emerald-600" />
                Add Invoice to Pending Receipt
              </h3>
              <button
                onClick={() => setIsAddPendingModalOpen(false)}
                className="text-gray-400 hover:text-gray-600 p-1.5 rounded-lg hover:bg-gray-100"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6 space-y-4">
              <div>
                <label className="block text-xs font-bold text-gray-700 uppercase tracking-wider mb-1">
                  Search Confirmed Invoices
                </label>
                <div className="relative">
                  <input
                    type="text"
                    placeholder="Type vendor invoice number or vendor name..."
                    value={addPendingSearch}
                    onChange={e => {
                      setAddPendingSearch(e.target.value);
                      searchPendingInvoices(e.target.value);
                    }}
                    className="w-full pl-9 pr-3 py-2 bg-gray-50 border border-gray-200 rounded-xl text-sm font-medium"
                  />
                  <Search className="w-4 h-4 text-gray-400 absolute left-3 top-3" />
                </div>

                {addPendingResults.length > 0 && !selectedAddPendingInv && (
                  <div className="mt-2 bg-white rounded-xl shadow-lg border border-gray-200 max-h-48 overflow-y-auto divide-y divide-gray-100">
                    {addPendingResults.map(inv => (
                      <div
                        key={inv.id}
                        onClick={() => handleSelectAddPendingInvoice(inv)}
                        className="p-3 hover:bg-emerald-50 cursor-pointer flex items-center justify-between text-xs"
                      >
                        <div>
                          <div className="font-bold text-gray-900">{inv.upload_number}</div>
                          <div className="text-gray-500">{inv.vendor_name} · {inv.vendor_invoice_no}</div>
                        </div>
                        <div className="text-right font-mono font-bold text-emerald-700">
                          {formatCurrency(inv.grand_total || inv.total_amount || 0)}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {selectedAddPendingInv && (
                <div className="space-y-4 p-4 bg-gray-50 rounded-2xl border border-gray-200">
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="font-bold text-gray-900 text-sm">{selectedAddPendingInv.upload_number}</div>
                      <div className="text-xs text-gray-500">{selectedAddPendingInv.vendor_name}</div>
                    </div>
                    <div className="text-right font-mono font-bold text-emerald-700 text-sm">
                      {formatCurrency(selectedAddPendingInv.grand_total || selectedAddPendingInv.total_amount || 0)}
                    </div>
                  </div>

                  <div className="overflow-x-auto bg-white rounded-xl border border-gray-200">
                    <table className="w-full text-left text-xs border-collapse">
                      <thead>
                        <tr className="bg-gray-50 border-b border-gray-200 font-bold text-gray-600">
                          <th className="p-2.5">Item</th>
                          <th className="p-2.5 text-right">Ordered</th>
                          <th className="p-2.5 text-right text-amber-600">Pending Qty</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-100">
                        {(selectedAddPendingInv.line_items || []).map((li: any) => (
                          <tr key={li.id}>
                            <td className="p-2.5 font-medium text-gray-900">{li.item_description}</td>
                            <td className="p-2.5 text-right font-semibold">{li.quantity}</td>
                            <td className="p-2.5 text-right">
                              <input
                                type="number"
                                min={0}
                                max={li.quantity}
                                value={addPendingLineOverrides[li.id] ?? li.quantity}
                                onChange={e =>
                                  setAddPendingLineOverrides({
                                    ...addPendingLineOverrides,
                                    [li.id]: parseFloat(e.target.value) || 0
                                  })
                                }
                                className="w-16 px-1.5 py-1 text-right bg-amber-50 border border-amber-200 rounded font-bold text-xs"
                              />
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setIsAddPendingModalOpen(false)}
                  className="px-4 py-2 text-xs font-semibold text-gray-600 bg-gray-100 hover:bg-gray-200 rounded-xl"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  disabled={!selectedAddPendingInv}
                  onClick={handleConfirmAddPending}
                  className="px-5 py-2 text-xs font-bold text-white bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 rounded-xl shadow-sm"
                >
                  Add to Pending Receipt
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ------------------------------------------------------------- */}
      {/* MODAL 7: QUICK CREATE VENDOR */}
      {/* ------------------------------------------------------------- */}
      {isQcVendorOpen && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4 overflow-y-auto">
          <div className="bg-white rounded-2xl shadow-2xl border border-gray-100 max-w-xl w-full max-h-[90vh] overflow-y-auto animate-in zoom-in-95 duration-200">
            <div className="p-5 border-b border-gray-100 flex items-center justify-between sticky top-0 bg-white z-10">
              <h3 className="font-bold text-base text-gray-900 flex items-center gap-2">
                <User className="w-5 h-5 text-emerald-600" />
                Add Vendor
              </h3>
              <button
                onClick={() => setIsQcVendorOpen(false)}
                className="text-gray-400 hover:text-gray-600 p-1.5 rounded-lg hover:bg-gray-100"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleSaveQcVendor} className="p-6 space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-bold text-gray-700 mb-1">Vendor Name *</label>
                  <input
                    type="text"
                    required
                    value={qcVendorName}
                    onChange={e => setQcVendorName(e.target.value)}
                    placeholder="Enter vendor name"
                    className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-xl text-xs font-medium"
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold text-gray-700 mb-1">Vendor Code *</label>
                  <input
                    type="text"
                    required
                    value={qcVendorCode}
                    onChange={e => setQcVendorCode(e.target.value.toUpperCase())}
                    placeholder="e.g. VND001"
                    className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-xl text-xs font-medium"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-bold text-gray-700 mb-1">GST Number</label>
                  <input
                    type="text"
                    maxLength={15}
                    value={qcVendorGst}
                    onChange={e => setQcVendorGst(e.target.value.toUpperCase())}
                    placeholder="15-char GSTIN"
                    className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-xl text-xs font-mono"
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold text-gray-700 mb-1">Phone</label>
                  <input
                    type="text"
                    value={qcVendorPhone}
                    onChange={e => setQcVendorPhone(e.target.value)}
                    placeholder="Contact number"
                    className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-xl text-xs font-medium"
                  />
                </div>
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="block text-xs font-bold text-gray-700 mb-1">Pincode</label>
                  <input
                    type="text"
                    maxLength={6}
                    value={qcVendorPincode}
                    onChange={e => {
                      setQcVendorPincode(e.target.value);
                      if (e.target.value.length === 6) handlePincodeLookup(e.target.value);
                    }}
                    placeholder="6-digit PIN"
                    className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-xl text-xs font-medium"
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold text-gray-700 mb-1">City</label>
                  <input
                    type="text"
                    value={qcVendorCity}
                    onChange={e => setQcVendorCity(e.target.value)}
                    placeholder="City"
                    className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-xl text-xs font-medium"
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold text-gray-700 mb-1">State</label>
                  <input
                    type="text"
                    value={qcVendorState}
                    onChange={e => setQcVendorState(e.target.value)}
                    placeholder="State"
                    className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-xl text-xs font-medium"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-bold text-gray-700 mb-1">Applicable Companies *</label>
                <div className="flex flex-wrap gap-2 pt-1">
                  {companies.map(c => {
                    const isSelected = qcVendorApplicableCompanies.includes(c.id);
                    return (
                      <button
                        key={c.id}
                        type="button"
                        onClick={() =>
                          setQcVendorApplicableCompanies(prev =>
                            isSelected ? prev.filter(id => id !== c.id) : [...prev, c.id]
                          )
                        }
                        className={`px-3 py-1 rounded-lg text-xs font-bold transition-all ${
                          isSelected
                            ? "bg-emerald-100 text-emerald-800 border border-emerald-300"
                            : "bg-gray-100 text-gray-600 hover:bg-gray-200 border border-transparent"
                        }`}
                      >
                        {c.company_name || c.name}
                      </button>
                    );
                  })}
                </div>
              </div>

              <div className="flex justify-end gap-3 pt-4 border-t border-gray-100">
                <button
                  type="button"
                  onClick={() => setIsQcVendorOpen(false)}
                  className="px-4 py-2 text-xs font-semibold text-gray-600 bg-gray-100 hover:bg-gray-200 rounded-xl"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={savingQcVendor}
                  className="px-5 py-2 text-xs font-bold text-white bg-emerald-600 hover:bg-emerald-700 rounded-xl shadow-sm"
                >
                  {savingQcVendor ? "Saving..." : "Save Vendor"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ------------------------------------------------------------- */}
      {/* MODAL 8: QUICK CREATE STOCK ITEM */}
      {/* ------------------------------------------------------------- */}
      {isQcStockOpen && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4 overflow-y-auto">
          <div className="bg-white rounded-2xl shadow-2xl border border-gray-100 max-w-lg w-full max-h-[90vh] overflow-y-auto animate-in zoom-in-95 duration-200">
            <div className="p-5 border-b border-gray-100 flex items-center justify-between sticky top-0 bg-white z-10">
              <h3 className="font-bold text-base text-gray-900 flex items-center gap-2">
                <Package className="w-5 h-5 text-emerald-600" />
                Add Stock Item
              </h3>
              <button
                onClick={() => setIsQcStockOpen(false)}
                className="text-gray-400 hover:text-gray-600 p-1.5 rounded-lg hover:bg-gray-100"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleSaveQcStock} className="p-6 space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-bold text-gray-700 mb-1">Item Name *</label>
                  <input
                    type="text"
                    required
                    value={qcStockName}
                    onChange={e => setQcStockName(e.target.value)}
                    placeholder="Enter item name"
                    className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-xl text-xs font-medium"
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold text-gray-700 mb-1">Item Code</label>
                  <input
                    type="text"
                    required
                    value={qcStockCode}
                    onChange={e => setQcStockCode(e.target.value.toUpperCase())}
                    className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-xl text-xs font-mono font-bold text-purple-700"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-bold text-gray-700 mb-1">Category</label>
                  <select
                    value={qcStockCategory}
                    onChange={e => {
                      setQcStockCategory(e.target.value);
                      generateStockCode(e.target.value);
                    }}
                    className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-xl text-xs font-medium"
                  >
                    <option value="PRODUCT">Product</option>
                    <option value="RAW_MATERIAL">Raw Material</option>
                    <option value="CONSUMABLE">Consumable</option>
                    <option value="SPARE_PART">Spare Part</option>
                    <option value="ACCESSORY">Accessory</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-bold text-gray-700 mb-1">Unit of Measure</label>
                  <select
                    value={qcStockUom}
                    onChange={e => setQcStockUom(e.target.value)}
                    className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-xl text-xs font-medium"
                  >
                    <option value="PCS">Pieces (PCS)</option>
                    <option value="NOS">Numbers (NOS)</option>
                    <option value="KG">Kilograms (KG)</option>
                    <option value="LTR">Liters (LTR)</option>
                    <option value="MTR">Meters (MTR)</option>
                    <option value="SET">Set (SET)</option>
                    <option value="BOX">Box (BOX)</option>
                    <option value="PACK">Pack (PACK)</option>
                    <option value="PAIR">Pair (PAIR)</option>
                    <option value="UNIT">Unit (UNIT)</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-bold text-gray-700 mb-1">HSN Code</label>
                  <select
                    value={qcStockHsnId}
                    onChange={e => setQcStockHsnId(e.target.value)}
                    className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-xl text-xs font-medium"
                  >
                    <option value="">Select HSN</option>
                    {hsnCodes.map(h => (
                      <option key={h.id} value={h.id}>
                        {h.hsn_code} - {h.description || ""} ({h.igst_rate || (h.cgst_rate || 0) * 2}%)
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-bold text-gray-700 mb-1">Purchase Rate (₹)</label>
                  <input
                    type="number"
                    step={0.01}
                    value={qcStockPurchaseRate || ""}
                    onChange={e => {
                      const pr = parseFloat(e.target.value) || 0;
                      setQcStockPurchaseRate(pr);
                      setQcStockSellingRate(parseFloat((pr * (1 + qcStockMarkupPct / 100)).toFixed(2)));
                    }}
                    placeholder="0.00"
                    className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-xl text-xs font-medium"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-bold text-gray-700 mb-1">Applicable Companies *</label>
                <div className="flex flex-wrap gap-2 pt-1">
                  {companies.map(c => {
                    const isSelected = qcStockApplicableCompanies.includes(c.id);
                    return (
                      <button
                        key={c.id}
                        type="button"
                        onClick={() =>
                          setQcStockApplicableCompanies(prev =>
                            isSelected ? prev.filter(id => id !== c.id) : [...prev, c.id]
                          )
                        }
                        className={`px-3 py-1 rounded-lg text-xs font-bold transition-all ${
                          isSelected
                            ? "bg-emerald-100 text-emerald-800 border border-emerald-300"
                            : "bg-gray-100 text-gray-600 hover:bg-gray-200 border border-transparent"
                        }`}
                      >
                        {c.company_name || c.name}
                      </button>
                    );
                  })}
                </div>
              </div>

              <div className="flex justify-end gap-3 pt-4 border-t border-gray-100">
                <button
                  type="button"
                  onClick={() => setIsQcStockOpen(false)}
                  className="px-4 py-2 text-xs font-semibold text-gray-600 bg-gray-100 hover:bg-gray-200 rounded-xl"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={savingQcStock}
                  className="px-5 py-2 text-xs font-bold text-white bg-emerald-600 hover:bg-emerald-700 rounded-xl shadow-sm"
                >
                  {savingQcStock ? "Saving..." : "Save Stock Item"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ------------------------------------------------------------- */}
      {/* MODAL 9: QUICK CREATE HSN */}
      {/* ------------------------------------------------------------- */}
      {isQcHsnOpen && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4 overflow-y-auto">
          <div className="bg-white rounded-2xl shadow-2xl border border-gray-100 max-w-md w-full animate-in zoom-in-95 duration-200">
            <div className="p-5 border-b border-gray-100 flex items-center justify-between">
              <h3 className="font-bold text-base text-gray-900 flex items-center gap-2">
                <Barcode className="w-5 h-5 text-emerald-600" />
                Add HSN / SAC Code
              </h3>
              <button
                onClick={() => setIsQcHsnOpen(false)}
                className="text-gray-400 hover:text-gray-600 p-1.5 rounded-lg hover:bg-gray-100"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleSaveQcHsn} className="p-6 space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-bold text-gray-700 mb-1">HSN/SAC Code *</label>
                  <input
                    type="text"
                    required
                    maxLength={10}
                    value={qcHsnCodeVal}
                    onChange={e => setQcHsnCodeVal(e.target.value.toUpperCase())}
                    placeholder="e.g. 8503"
                    className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-xl text-xs font-mono font-bold"
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold text-gray-700 mb-1">GST Rate (%) *</label>
                  <select
                    value={qcHsnGstRate}
                    onChange={e => setQcHsnGstRate(parseFloat(e.target.value) || 0)}
                    className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-xl text-xs font-bold"
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
                <label className="block text-xs font-bold text-gray-700 mb-1">Description *</label>
                <input
                  type="text"
                  required
                  value={qcHsnDesc}
                  onChange={e => setQcHsnDesc(e.target.value)}
                  placeholder="Description of goods/services"
                  className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-xl text-xs font-medium"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-gray-700 mb-1">Effective From *</label>
                <input
                  type="date"
                  required
                  value={qcHsnEffectiveFrom}
                  onChange={e => setQcHsnEffectiveFrom(e.target.value)}
                  className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-xl text-xs font-medium"
                />
              </div>

              <div className="flex justify-end gap-3 pt-4 border-t border-gray-100">
                <button
                  type="button"
                  onClick={() => setIsQcHsnOpen(false)}
                  className="px-4 py-2 text-xs font-semibold text-gray-600 bg-gray-100 hover:bg-gray-200 rounded-xl"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={savingQcHsn}
                  className="px-5 py-2 text-xs font-bold text-white bg-emerald-600 hover:bg-emerald-700 rounded-xl shadow-sm"
                >
                  {savingQcHsn ? "Saving..." : "Save HSN"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ------------------------------------------------------------- */}
      {/* MODAL 10: PDF VIEWER MODAL */}
      {/* ------------------------------------------------------------- */}
      {isPdfModalOpen && pdfBlobUrl && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4 overflow-y-auto">
          <div className="bg-white rounded-2xl shadow-2xl border border-gray-100 max-w-5xl w-full h-[90vh] flex flex-col overflow-hidden animate-in zoom-in-95 duration-200">
            <div className="p-4 border-b border-gray-100 flex items-center justify-between bg-white z-10">
              <h3 className="font-bold text-sm text-gray-900 flex items-center gap-2">
                <FileText className="w-4 h-4 text-emerald-600" />
                {pdfTitle || pdfFilename}
              </h3>
              <div className="flex items-center gap-2">
                <a
                  href={pdfBlobUrl}
                  download={pdfFilename}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-indigo-50 text-indigo-700 hover:bg-indigo-100 text-xs font-bold rounded-lg transition-all"
                >
                  <Download className="w-3.5 h-3.5" />
                  Download
                </a>
                <button
                  onClick={() => {
                    setIsPdfModalOpen(false);
                    if (pdfBlobUrl) URL.revokeObjectURL(pdfBlobUrl);
                  }}
                  className="text-gray-400 hover:text-gray-600 p-1.5 rounded-lg hover:bg-gray-100 transition-colors"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
            </div>

            <div className="flex-1 bg-gray-100">
              <iframe src={pdfBlobUrl} className="w-full h-full border-none" title="PDF Viewer" />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
