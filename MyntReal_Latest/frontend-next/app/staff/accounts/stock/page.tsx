"use client";

import React, { useState, useEffect, useMemo, useCallback } from "react";
import Link from "next/link";
import { useStaffAuth } from "@/contexts/StaffAuthContext";
import api, { getApiUrl } from "@/lib/api";
import {
  Boxes,
  Layers,
  Search,
  Plus,
  Filter,
  ArrowUpDown,
  TrendingUp,
  AlertTriangle,
  CheckCircle2,
  Sliders,
  Edit,
  History,
  Image as ImageIcon,
  Download,
  Upload,
  RefreshCw,
  X,
  ShieldAlert,
  ArrowUpRight,
  ArrowDownRight,
  FileSpreadsheet,
  Building2,
  Trash2,
  DollarSign,
  Info,
  ExternalLink,
  ChevronLeft,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
  Eye,
  Check,
  Percent
} from "lucide-react";

// Types definition
interface StockItem {
  id: number;
  item_code: string;
  item_name: string;
  item_category: string;
  unit_of_measure?: string;
  applicable_companies?: number[];
  description?: string;
  brand?: string;
  model_compat?: string;
  specification?: string;
  size?: string;
  colors?: string[];
  purchase_rate?: number;
  effective_purchase_rate?: number;
  is_average_price?: boolean;
  selling_rate?: number;
  effective_selling_rate?: number;
  is_suggested_price?: boolean;
  reorder_level?: number;
  hsn_id?: number;
  current_stock?: number;
  total_qty_in?: number;
  total_qty_out?: number;
  primary_image?: string;
  has_folder_link?: boolean;
  folder_url?: string;
  images?: Array<{ id?: number; image_url?: string; source_type?: string }>;
  is_active?: boolean;
  marketplace_sku?: string;
  marketplace_linked?: boolean;
  marketplace_available_qty?: number;
  show_in_marketplace?: boolean;
}

interface Company {
  id: number;
  company_name: string;
  is_active?: boolean;
}

interface HsnCode {
  id: number;
  hsn_code: string;
  description: string;
  igst_rate?: number;
  cgst_rate?: number;
  sgst_rate?: number;
  gst_rate?: number;
}

interface StockLedgerEntry {
  id: number;
  company_id: number;
  company_name: string;
  item_id: number;
  item_name: string;
  item_code: string;
  transaction_date: string;
  entry_type: string;
  reference_type: string;
  reference_id: number;
  reference_number?: string;
  quantity_in: number;
  quantity_out: number;
  unit_rate: number;
  total_value: number;
  balance_qty: number;
  balance_value: number;
  narration?: string;
  is_estimate?: boolean;
  created_at?: string;
}

interface MarginConfig {
  id: number;
  from_company_id?: number;
  to_company_id?: number;
  category_slug?: string;
  margin_pct: number;
  is_active: boolean;
}

const CATEGORY_OPTIONS = [
  "PRODUCT",
  "RAW_MATERIAL",
  "CONSUMABLE",
  "SPARE_PART",
  "ACCESSORY",
  "BATTERIES"
];

const UOM_OPTIONS = ["PCS", "KG", "LTR", "MTR", "SET", "BOX", "PACK", "PAIR", "UNIT"];

export default function AccountsStockInHandPage() {
  const { token, user } = useStaffAuth();

  // Active Main Tab: 'stock' | 'ledger' | 'margins'
  const [activeTab, setActiveTab] = useState<"stock" | "ledger" | "margins">("stock");

  // Stock Items State
  const [stockItems, setStockItems] = useState<StockItem[]>([]);
  const [companies, setCompanies] = useState<Company[]>([]);
  const [hsnList, setHsnList] = useState<HsnCode[]>([]);
  const [categories, setCategories] = useState<string[]>(CATEGORY_OPTIONS);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string>("");
  const [summary, setSummary] = useState({
    total_items: 0,
    low_stock_count: 0,
    total_value: 0
  });

  // Pagination & Filtering for Stock
  const [page, setPage] = useState<number>(1);
  const [pageSize, setPageSize] = useState<number>(20);
  const [totalCount, setTotalCount] = useState<number>(0);
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [selectedCompany, setSelectedCompany] = useState<string>("");
  const [selectedCategory, setSelectedCategory] = useState<string>("");
  const [selectedStockLevel, setSelectedStockLevel] = useState<string>("");
  const [selectedSpec, setSelectedSpec] = useState<string>("");
  const [selectedColor, setSelectedColor] = useState<string>("");
  const [sortField, setSortField] = useState<string>("item_name");
  const [sortDirection, setSortDirection] = useState<"asc" | "desc">("asc");

  // Ledger Tab State
  const [ledgerEntries, setLedgerEntries] = useState<StockLedgerEntry[]>([]);
  const [ledgerLoading, setLedgerLoading] = useState<boolean>(false);
  const [ledgerCompany, setLedgerCompany] = useState<string>("");
  const [ledgerType, setLedgerType] = useState<string>("");
  const [ledgerFromDate, setLedgerFromDate] = useState<string>("");
  const [ledgerToDate, setLedgerToDate] = useState<string>("");
  const [ledgerSearch, setLedgerSearch] = useState<string>("");

  // Margin Configs Tab State
  const [marginConfigs, setMarginConfigs] = useState<MarginConfig[]>([]);
  const [marginLoading, setMarginLoading] = useState<boolean>(false);
  const [showAddMarginModal, setShowAddMarginModal] = useState<boolean>(false);
  const [newMarginForm, setNewMarginForm] = useState({
    from_company_id: "",
    to_company_id: "",
    category_slug: "",
    margin_pct: 6.0
  });

  // Modals
  const [showCreateModal, setShowCreateModal] = useState<boolean>(false);
  const [showEditModal, setShowEditModal] = useState<boolean>(false);
  const [showAdjustModal, setShowAdjustModal] = useState<boolean>(false);
  const [showHistoryModal, setShowHistoryModal] = useState<boolean>(false);
  const [showBulkUploadModal, setShowBulkUploadModal] = useState<boolean>(false);
  const [showHsnSubModal, setShowHsnSubModal] = useState<boolean>(false);
  const [lightboxImage, setLightboxImage] = useState<string | null>(null);

  // Form State - Create / Edit Stock Item
  const [formData, setFormData] = useState({
    id: 0,
    item_name: "",
    item_code: "",
    item_category: "PRODUCT",
    unit_of_measure: "PCS",
    applicable_companies: [] as number[],
    description: "",
    brand: "",
    model_compat: "",
    specification: "",
    size: "",
    colors: [] as string[],
    colorInput: "",
    purchase_rate: 0,
    selling_rate: 0,
    markup_pct: 27,
    reorder_level: 10,
    hsn_id: null as number | null,
    hsn_search: "",
    gst_rate_display: "",
    show_in_marketplace: false,
    image_url: "",
    is_active: true,
    // Opening balance fields (for edit)
    opening_qty: "",
    opening_value: "",
    opening_date: new Date().toISOString().split("T")[0],
    // Marketplace link
    marketplace_sku: ""
  });

  // Adjustment Form State
  const [adjForm, setAdjForm] = useState({
    item_id: 0,
    item_code: "",
    item_name: "",
    company_id: "",
    delta_qty: "",
    rate: "",
    reason: ""
  });

  // Item History Modal State
  const [historyItem, setHistoryItem] = useState<{ id: number; code: string; name: string } | null>(null);
  const [historyEntries, setHistoryEntries] = useState<StockLedgerEntry[]>([]);
  const [historyLoading, setHistoryLoading] = useState<boolean>(false);

  // Bulk Upload State
  const [bulkFile, setBulkFile] = useState<File | null>(null);
  const [bulkUploading, setBulkUploading] = useState<boolean>(false);
  const [bulkResult, setBulkResult] = useState<any | null>(null);

  // Quick HSN creation state
  const [newHsn, setNewHsn] = useState({
    hsn_code: "",
    description: "",
    gst_rate: 18,
    cess_rate: 0
  });

  // Currency Formatter (Indian style)
  const formatCurrency = (val: number | undefined | null) => {
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: "INR",
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(val || 0);
  };

  // Fetch Companies & HSN List on Mount
  useEffect(() => {
    if (!token) return;

    const loadMeta = async () => {
      try {
        const [compRes, hsnRes, catRes] = await Promise.allSettled([
          api.get("/staff/accounts/companies"),
          api.get("/staff/accounts/hsn?page_size=100&is_active=true"),
          api.get("/staff/accounts/stock-items/categories")
        ]);

        if (compRes.status === "fulfilled" && compRes.value.data) {
          const compData = compRes.value.data.companies || compRes.value.data || [];
          setCompanies(Array.isArray(compData) ? compData.filter((c: any) => c.is_active !== false) : []);
        }

        if (hsnRes.status === "fulfilled" && hsnRes.value.data) {
          const hsnData = hsnRes.value.data.hsn_codes || hsnRes.value.data.items || [];
          setHsnList(Array.isArray(hsnData) ? hsnData : []);
        }

        if (catRes.status === "fulfilled" && catRes.value.data && catRes.value.data.categories) {
          const uniqueCats = Array.from(new Set([...CATEGORY_OPTIONS, ...catRes.value.data.categories]));
          setCategories(uniqueCats);
        }
      } catch (err) {
        console.error("Failed to load metadata:", err);
      }
    };

    loadMeta();
  }, [token]);

  // Fetch Stock Items
  const fetchStockItems = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setError("");

    try {
      let url = `/staff/accounts/stock-items?include_summary=true&page=${page}&page_size=${pageSize}`;
      if (selectedCompany) url += `&company_id=${encodeURIComponent(selectedCompany)}`;
      if (searchQuery.trim()) url += `&search=${encodeURIComponent(searchQuery.trim())}`;
      if (selectedCategory) url += `&item_category=${encodeURIComponent(selectedCategory)}`;
      if (selectedSpec) url += `&specification=${encodeURIComponent(selectedSpec)}`;
      if (selectedColor) url += `&colors=${encodeURIComponent(selectedColor)}`;
      if (selectedStockLevel) url += `&stock_level=${encodeURIComponent(selectedStockLevel)}`;

      const res = await api.get(url);
      const data = res.data;

      const items = data.stock_items || data.items || [];
      setStockItems(Array.isArray(items) ? items : []);
      setTotalCount(data.total || (Array.isArray(items) ? items.length : 0));

      if (data.summary) {
        setSummary({
          total_items: data.summary.total_items || items.length,
          low_stock_count: data.summary.low_stock_count || 0,
          total_value: Number(data.summary.total_value || 0)
        });
      } else {
        // Fallback computation
        const totalVal = items.reduce(
          (sum: number, it: any) => sum + (Number(it.current_stock || 0) * Number(it.purchase_rate || 0)),
          0
        );
        const lowCount = items.filter(
          (it: any) => Number(it.current_stock || 0) <= Number(it.reorder_level || 10)
        ).length;
        setSummary({
          total_items: items.length,
          low_stock_count: lowCount,
          total_value: totalVal
        });
      }
    } catch (err: any) {
      console.error("Error fetching stock items:", err);
      setError(err.response?.data?.detail || err.message || "Failed to load stock data");
      setStockItems([]);
    } finally {
      setLoading(false);
    }
  }, [token, page, pageSize, selectedCompany, searchQuery, selectedCategory, selectedSpec, selectedColor, selectedStockLevel]);

  useEffect(() => {
    if (activeTab === "stock") {
      fetchStockItems();
    }
  }, [fetchStockItems, activeTab]);

  // Fetch Stock Ledger
  const fetchStockLedger = useCallback(async () => {
    if (!token) return;
    setLedgerLoading(true);
    try {
      let url = `/staff/accounts/stock/ledger?limit=150`;
      if (ledgerCompany) url += `&company_id=${encodeURIComponent(ledgerCompany)}`;
      if (ledgerType) url += `&entry_type=${encodeURIComponent(ledgerType)}`;
      if (ledgerFromDate) url += `&from_date=${encodeURIComponent(ledgerFromDate)}`;
      if (ledgerToDate) url += `&to_date=${encodeURIComponent(ledgerToDate)}`;

      const res = await api.get(url);
      if (res.data?.success && Array.isArray(res.data.data)) {
        setLedgerEntries(res.data.data);
      } else {
        setLedgerEntries([]);
      }
    } catch (err) {
      console.error("Error fetching stock ledger:", err);
      setLedgerEntries([]);
    } finally {
      setLedgerLoading(false);
    }
  }, [token, ledgerCompany, ledgerType, ledgerFromDate, ledgerToDate]);

  useEffect(() => {
    if (activeTab === "ledger") {
      fetchStockLedger();
    }
  }, [fetchStockLedger, activeTab]);

  // Fetch Margin Configurations
  const fetchMarginConfigs = useCallback(async () => {
    if (!token) return;
    setMarginLoading(true);
    try {
      const res = await api.get("/staff/accounts/stock/margin-config");
      if (res.data?.success && Array.isArray(res.data.data)) {
        setMarginConfigs(res.data.data);
      }
    } catch (err) {
      console.error("Error fetching margin configs:", err);
    } finally {
      setMarginLoading(false);
    }
  }, [token]);

  useEffect(() => {
    if (activeTab === "margins") {
      fetchMarginConfigs();
    }
  }, [fetchMarginConfigs, activeTab]);

  // Dynamic Specs & Colors list for filter pills
  const availableSpecs = useMemo(() => {
    const set = new Set<string>();
    stockItems.forEach((i) => {
      if (i.specification) {
        i.specification
          .split(/[,;]/)
          .map((s) => s.trim())
          .filter((s) => s.length > 1 && s.length < 40)
          .forEach((s) => set.add(s));
      }
    });
    return Array.from(set).sort();
  }, [stockItems]);

  const availableColors = useMemo(() => {
    const set = new Set<string>();
    stockItems.forEach((i) => {
      if (Array.isArray(i.colors)) {
        i.colors.forEach((c) => set.add(c));
      }
    });
    return Array.from(set).sort();
  }, [stockItems]);

  // Client-Side Sort Table
  const sortedStockItems = useMemo(() => {
    return [...stockItems].sort((a: any, b: any) => {
      let aVal = a[sortField];
      let bVal = b[sortField];

      if (sortField === "current_stock") {
        aVal = Number(a.current_stock || 0);
        bVal = Number(b.current_stock || 0);
      } else if (sortField === "purchase_rate") {
        aVal = Number(a.effective_purchase_rate || a.purchase_rate || 0);
        bVal = Number(b.effective_purchase_rate || b.purchase_rate || 0);
      } else if (sortField === "selling_rate") {
        aVal = Number(a.effective_selling_rate || a.selling_rate || 0);
        bVal = Number(b.effective_selling_rate || b.selling_rate || 0);
      } else if (sortField === "total_value") {
        aVal = Number(a.current_stock || 0) * Number(a.purchase_rate || 0);
        bVal = Number(b.current_stock || 0) * Number(b.purchase_rate || 0);
      }

      if (typeof aVal === "number" && typeof bVal === "number") {
        return sortDirection === "asc" ? aVal - bVal : bVal - aVal;
      }

      const strA = String(aVal || "").toLowerCase();
      const strB = String(bVal || "").toLowerCase();
      return sortDirection === "asc" ? strA.localeCompare(strB) : strB.localeCompare(strA);
    });
  }, [stockItems, sortField, sortDirection]);

  // Filtered Ledger entries by search
  const filteredLedgerEntries = useMemo(() => {
    if (!ledgerSearch.trim()) return ledgerEntries;
    const q = ledgerSearch.toLowerCase();
    return ledgerEntries.filter(
      (e) =>
        e.item_name?.toLowerCase().includes(q) ||
        e.item_code?.toLowerCase().includes(q) ||
        e.reference_number?.toLowerCase().includes(q) ||
        e.company_name?.toLowerCase().includes(q) ||
        e.narration?.toLowerCase().includes(q)
    );
  }, [ledgerEntries, ledgerSearch]);

  const handleSort = (field: string) => {
    if (sortField === field) {
      setSortDirection(sortDirection === "asc" ? "desc" : "asc");
    } else {
      setSortField(field);
      setSortDirection("asc");
    }
  };

  // Auto-generate Item Code on Category select
  const handleCategoryChange = async (cat: string) => {
    setFormData((prev) => ({ ...prev, item_category: cat }));
    try {
      const res = await api.get(`/staff/accounts/stock-items/generate-code?category=${encodeURIComponent(cat)}`);
      if (res.data?.item_code) {
        setFormData((prev) => ({ ...prev, item_code: res.data.item_code }));
      }
    } catch {
      // ignore
    }
  };

  // Auto-calculate Selling rate on markup change or purchase rate change
  const calcRate = (purchase: number, markup: number) => {
    if (purchase > 0) {
      return Number((purchase * (1 + markup / 100)).toFixed(2));
    }
    return 0;
  };

  const handlePurchaseRateChange = (rate: number) => {
    const selling = calcRate(rate, formData.markup_pct);
    setFormData((prev) => ({
      ...prev,
      purchase_rate: rate,
      selling_rate: selling
    }));
  };

  const handleMarkupPctChange = (pct: number) => {
    const selling = calcRate(formData.purchase_rate, pct);
    setFormData((prev) => ({
      ...prev,
      markup_pct: pct,
      selling_rate: selling
    }));
  };

  // Open Create Modal
  const openCreate = async () => {
    setFormData({
      id: 0,
      item_name: "",
      item_code: "",
      item_category: "PRODUCT",
      unit_of_measure: "PCS",
      applicable_companies: [],
      description: "",
      brand: "",
      model_compat: "",
      specification: "",
      size: "",
      colors: [],
      colorInput: "",
      purchase_rate: 0,
      selling_rate: 0,
      markup_pct: 27,
      reorder_level: 10,
      hsn_id: null,
      hsn_search: "",
      gst_rate_display: "",
      show_in_marketplace: false,
      image_url: "",
      is_active: true,
      opening_qty: "",
      opening_value: "",
      opening_date: new Date().toISOString().split("T")[0],
      marketplace_sku: ""
    });
    setShowCreateModal(true);
    await handleCategoryChange("PRODUCT");
  };

  // Open Edit Modal
  const openEdit = (item: StockItem) => {
    const hsnMatch = hsnList.find((h) => h.id === item.hsn_id);
    const pr = Number(item.purchase_rate || 0);
    const sr = Number(item.selling_rate || 0);
    const computedMarkup = pr > 0 && sr > 0 ? Number((((sr - pr) / pr) * 100).toFixed(1)) : 27;

    setFormData({
      id: item.id,
      item_name: item.item_name || "",
      item_code: item.item_code || "",
      item_category: item.item_category || "PRODUCT",
      unit_of_measure: item.unit_of_measure || "PCS",
      applicable_companies: Array.isArray(item.applicable_companies) ? item.applicable_companies : [],
      description: item.description || "",
      brand: item.brand || "",
      model_compat: item.model_compat || "",
      specification: item.specification || "",
      size: item.size || "",
      colors: Array.isArray(item.colors) ? item.colors : [],
      colorInput: "",
      purchase_rate: pr,
      selling_rate: sr,
      markup_pct: computedMarkup,
      reorder_level: item.reorder_level ?? 10,
      hsn_id: item.hsn_id || null,
      hsn_search: hsnMatch ? `${hsnMatch.hsn_code} - ${hsnMatch.description}` : "",
      gst_rate_display: hsnMatch ? `${hsnMatch.igst_rate || hsnMatch.gst_rate || 18}%` : "",
      show_in_marketplace: item.show_in_marketplace === true,
      image_url: item.folder_url || "",
      is_active: item.is_active !== false,
      opening_qty: "",
      opening_value: "",
      opening_date: new Date().toISOString().split("T")[0],
      marketplace_sku: item.marketplace_sku || ""
    });
    setShowEditModal(true);
  };

  // Save New Stock Item
  const handleCreateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.item_name.trim()) {
      alert("Item Name is required");
      return;
    }

    try {
      const payload = {
        item_name: formData.item_name.trim(),
        item_category: formData.item_category,
        unit_of_measure: formData.unit_of_measure,
        applicable_companies: formData.applicable_companies,
        description: formData.description.trim() || null,
        brand: formData.brand.trim() || null,
        model_compat: formData.model_compat.trim() || null,
        specification: formData.specification.trim() || null,
        size: formData.size.trim() || null,
        colors: formData.colors.length > 0 ? formData.colors : null,
        purchase_rate: Number(formData.purchase_rate) || 0,
        selling_rate: Number(formData.selling_rate) || 0,
        reorder_level: Number(formData.reorder_level) || 0,
        hsn_id: formData.hsn_id || null,
        show_in_marketplace: formData.show_in_marketplace
      };

      const res = await api.post("/staff/accounts/stock-items", payload);
      const createdItem = res.data?.stock_item || res.data;

      // If Google Drive Image URL was provided
      if (createdItem?.id && formData.image_url.trim()) {
        try {
          await api.post(`/staff/accounts/stock-items/${createdItem.id}/image-link`, {
            source_url: formData.image_url.trim()
          });
        } catch {
          // ignore
        }
      }

      setShowCreateModal(false);
      fetchStockItems();
    } catch (err: any) {
      alert(err.response?.data?.detail || err.message || "Failed to create stock item");
    }
  };

  // Save Updated Stock Item
  const handleUpdateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.item_name.trim()) {
      alert("Item Name is required");
      return;
    }

    try {
      const payload = {
        item_name: formData.item_name.trim(),
        item_category: formData.item_category,
        unit_of_measure: formData.unit_of_measure,
        applicable_companies: formData.applicable_companies,
        description: formData.description.trim() || null,
        brand: formData.brand.trim() || null,
        model_compat: formData.model_compat.trim() || null,
        specification: formData.specification.trim() || null,
        size: formData.size.trim() || null,
        colors: formData.colors.length > 0 ? formData.colors : null,
        purchase_rate: Number(formData.purchase_rate) || 0,
        selling_rate: Number(formData.selling_rate) || 0,
        reorder_level: Number(formData.reorder_level) || 0,
        hsn_id: formData.hsn_id || null,
        is_active: formData.is_active,
        show_in_marketplace: formData.show_in_marketplace,
        marketplace_sku: formData.marketplace_sku.trim() || null
      };

      await api.put(`/staff/accounts/stock-items/${formData.id}`, payload);
      setShowEditModal(false);
      fetchStockItems();
    } catch (err: any) {
      alert(err.response?.data?.detail || err.message || "Failed to update stock item");
    }
  };

  // Save Opening Balance in Edit Modal
  const handleSaveOpeningBalance = async () => {
    const qty = parseFloat(formData.opening_qty);
    const val = parseFloat(formData.opening_value);
    if (isNaN(qty) || qty <= 0 || isNaN(val) || val <= 0) {
      alert("Please provide valid opening quantity and total value (> 0)");
      return;
    }

    const companyId = formData.applicable_companies[0];
    if (!companyId) {
      alert("Please ensure this stock item is assigned to at least one company");
      return;
    }

    try {
      await api.post(
        `/staff/accounts/stock-items/${formData.id}/opening-balance?company_id=${companyId}&quantity=${qty}&total_value=${val}&balance_date=${formData.opening_date}`
      );
      alert("Opening balance recorded successfully!");
      setFormData((prev) => ({ ...prev, opening_qty: "", opening_value: "" }));
      fetchStockItems();
    } catch (err: any) {
      alert(err.response?.data?.detail || err.message || "Failed to record opening balance");
    }
  };

  // Open Adjust Stock Modal
  const openAdjust = (item: StockItem) => {
    setAdjForm({
      item_id: item.id,
      item_code: item.item_code,
      item_name: item.item_name,
      company_id: selectedCompany || (item.applicable_companies?.[0]?.toString() || ""),
      delta_qty: "",
      rate: String(item.purchase_rate || ""),
      reason: ""
    });
    setShowAdjustModal(true);
  };

  // Save Stock Adjustment
  const handleAdjustSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const delta = parseFloat(adjForm.delta_qty);
    if (isNaN(delta) || delta === 0) {
      alert("Please enter a non-zero adjustment quantity (e.g. +10 or -5)");
      return;
    }
    if (!adjForm.company_id) {
      alert("Please select a company");
      return;
    }

    try {
      const res = await api.post(`/staff/accounts/stock-items/${adjForm.item_id}/adjust`, {
        company_id: parseInt(adjForm.company_id),
        delta_qty: delta,
        rate: adjForm.rate ? parseFloat(adjForm.rate) : null,
        reason: adjForm.reason.trim() || null
      });

      alert(`Stock adjusted successfully! ${res.data?.message || ""}`);
      setShowAdjustModal(false);
      fetchStockItems();
    } catch (err: any) {
      alert(err.response?.data?.detail || err.message || "Adjustment failed");
    }
  };

  // Open Item History Modal
  const openHistory = async (item: StockItem) => {
    setHistoryItem({ id: item.id, code: item.item_code, name: item.item_name });
    setShowHistoryModal(true);
    setHistoryLoading(true);
    try {
      const res = await api.get(`/staff/accounts/stock/ledger?item_id=${item.id}&limit=100`);
      if (res.data?.success && Array.isArray(res.data.data)) {
        setHistoryEntries(res.data.data);
      } else {
        setHistoryEntries([]);
      }
    } catch {
      setHistoryEntries([]);
    } finally {
      setHistoryLoading(false);
    }
  };

  // Quick Create HSN Code
  const handleCreateHsn = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newHsn.hsn_code.trim() || !newHsn.description.trim()) {
      alert("HSN Code and Description are required");
      return;
    }

    try {
      const payload = {
        hsn_code: newHsn.hsn_code.trim(),
        description: newHsn.description.trim(),
        cgst_rate: newHsn.gst_rate / 2,
        sgst_rate: newHsn.gst_rate / 2,
        igst_rate: newHsn.gst_rate,
        cess_rate: newHsn.cess_rate,
        effective_from: new Date().toISOString().split("T")[0]
      };
      const res = await api.post("/staff/accounts/hsn", payload);
      const created = res.data?.hsn || res.data;

      // Update HSN list and auto-select
      setHsnList((prev) => [created, ...prev]);
      setFormData((prev) => ({
        ...prev,
        hsn_id: created.id,
        hsn_search: `${created.hsn_code} - ${created.description}`,
        gst_rate_display: `${created.igst_rate || newHsn.gst_rate}%`
      }));
      setShowHsnSubModal(false);
      setNewHsn({ hsn_code: "", description: "", gst_rate: 18, cess_rate: 0 });
    } catch (err: any) {
      alert(err.response?.data?.detail || err.message || "Failed to create HSN Code");
    }
  };

  // Bulk Excel Upload
  const handleBulkUpload = async () => {
    if (!bulkFile) {
      alert("Please choose an Excel file (.xlsx or .xls)");
      return;
    }

    const form = new FormData();
    form.append("file", bulkFile);

    setBulkUploading(true);
    setBulkResult(null);

    try {
      const res = await api.post("/staff/accounts/stock-items/bulk-upload", form, {
        headers: { "Content-Type": "multipart/form-data" }
      });
      setBulkResult(res.data);
      fetchStockItems();
    } catch (err: any) {
      alert(err.response?.data?.detail || err.message || "Upload failed");
    } finally {
      setBulkUploading(false);
    }
  };

  // Create Margin Config
  const handleCreateMargin = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.post("/staff/accounts/stock/margin-config", {
        from_company_id: newMarginForm.from_company_id ? parseInt(newMarginForm.from_company_id) : null,
        to_company_id: newMarginForm.to_company_id ? parseInt(newMarginForm.to_company_id) : null,
        category_slug: newMarginForm.category_slug.trim() || null,
        margin_pct: Number(newMarginForm.margin_pct) || 6.0,
        is_active: true
      });
      setShowAddMarginModal(false);
      setNewMarginForm({ from_company_id: "", to_company_id: "", category_slug: "", margin_pct: 6.0 });
      fetchMarginConfigs();
    } catch (err: any) {
      alert(err.response?.data?.detail || err.message || "Failed to create margin configuration");
    }
  };

  // Delete Margin Config
  const handleDeleteMargin = async (id: number) => {
    if (!confirm("Are you sure you want to delete this margin rule?")) return;
    try {
      await api.delete(`/staff/accounts/stock/margin-config/${id}`);
      fetchMarginConfigs();
    } catch (err: any) {
      alert(err.response?.data?.detail || err.message || "Failed to delete");
    }
  };

  // Reset Filters
  const clearFilters = () => {
    setSearchQuery("");
    setSelectedCompany("");
    setSelectedCategory("");
    setSelectedStockLevel("");
    setSelectedSpec("");
    setSelectedColor("");
    setPage(1);
  };

  const totalPages = Math.ceil(totalCount / pageSize) || 1;

  return (
    <div className="min-h-screen bg-slate-50/60 pb-16">
      {/* Enterprise Sticky Top Navigation Bar */}
      <header className="sticky top-0 z-20 border-b border-slate-200 bg-white/95 backdrop-blur-md px-6 py-4 shadow-sm">
        <div className="mx-auto flex max-w-7xl flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-600 to-violet-700 text-white shadow-md shadow-indigo-500/20">
              <Boxes className="h-6 w-6" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-2xl font-bold tracking-tight text-slate-900">
                  Accounts · Stock In Hand & Valuation
                </h1>
                <span className="rounded-full bg-indigo-50 px-2.5 py-0.5 text-xs font-semibold text-indigo-700 border border-indigo-200">
                  SFMS Real-time
                </span>
              </div>
              <p className="text-xs font-medium text-slate-500">
                Multi-company inventory balances, procurement weighted valuations, and audit trail.
              </p>
            </div>
          </div>

          {/* Action Toolbar */}
          <div className="flex flex-wrap items-center gap-2">
            <a
              href={`${getApiUrl()}/api/v1/staff/accounts/stock-items/template`}
              download
              className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs font-semibold text-slate-700 shadow-sm transition hover:bg-slate-50 hover:text-indigo-600"
            >
              <Download className="h-3.5 w-3.5" />
              Template
            </a>

            <button
              onClick={() => setShowBulkUploadModal(true)}
              className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs font-semibold text-slate-700 shadow-sm transition hover:bg-slate-50 hover:text-indigo-600"
            >
              <FileSpreadsheet className="h-3.5 w-3.5" />
              Bulk Upload
            </button>

            <button
              onClick={openCreate}
              className="inline-flex items-center gap-1.5 rounded-lg bg-indigo-600 px-3.5 py-2 text-xs font-semibold text-white shadow-md shadow-indigo-600/20 transition hover:bg-indigo-700"
            >
              <Plus className="h-4 w-4" />
              Add Stock Item
            </button>
          </div>
        </div>

        {/* Tab Navigation Pill Bar */}
        <div className="mx-auto mt-4 flex max-w-7xl items-center gap-2 border-t border-slate-100 pt-3">
          <button
            onClick={() => setActiveTab("stock")}
            className={`inline-flex items-center gap-2 rounded-lg px-3.5 py-1.5 text-xs font-bold transition ${
              activeTab === "stock"
                ? "bg-indigo-600 text-white shadow-sm"
                : "text-slate-600 hover:bg-slate-100"
            }`}
          >
            <Layers className="h-3.5 w-3.5" />
            Stock In Hand & Items Master
          </button>

          <button
            onClick={() => setActiveTab("ledger")}
            className={`inline-flex items-center gap-2 rounded-lg px-3.5 py-1.5 text-xs font-bold transition ${
              activeTab === "ledger"
                ? "bg-indigo-600 text-white shadow-sm"
                : "text-slate-600 hover:bg-slate-100"
            }`}
          >
            <History className="h-3.5 w-3.5" />
            Stock Ledger & Audit Trail
          </button>

          <button
            onClick={() => setActiveTab("margins")}
            className={`inline-flex items-center gap-2 rounded-lg px-3.5 py-1.5 text-xs font-bold transition ${
              activeTab === "margins"
                ? "bg-indigo-600 text-white shadow-sm"
                : "text-slate-600 hover:bg-slate-100"
            }`}
          >
            <Percent className="h-3.5 w-3.5" />
            Inter-Company Margin Rules
          </button>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-6 pt-6">
        {/* DC Protocol Banner */}
        <div
          className={`mb-6 flex items-center justify-between rounded-xl border p-4 shadow-sm transition ${
            selectedCompany
              ? "border-emerald-200 bg-emerald-50/70 text-emerald-900"
              : "border-amber-200 bg-amber-50/80 text-amber-900"
          }`}
        >
          <div className="flex items-center gap-3">
            <div
              className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-lg ${
                selectedCompany ? "bg-emerald-600 text-white" : "bg-amber-500 text-white"
              }`}
            >
              {selectedCompany ? <Check className="h-4 w-4" /> : <AlertTriangle className="h-4 w-4" />}
            </div>
            <div>
              <p className="text-xs font-bold uppercase tracking-wider">
                {selectedCompany
                  ? `Active Scope: ${companies.find((c) => String(c.id) === selectedCompany)?.company_name}`
                  : "DC Protocol Warning · Aggregated Valuation"}
              </p>
              <p className="text-xs text-slate-600">
                {selectedCompany
                  ? "Displaying precise live stock quantities and valuations specifically allocated for this entity."
                  : "Select a specific company from the filter to view isolated company stock holdings. 'All Companies' shows aggregated group inventory."}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <select
              value={selectedCompany}
              onChange={(e) => {
                setSelectedCompany(e.target.value);
                setPage(1);
              }}
              className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 shadow-sm outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20"
            >
              <option value="">All Companies (Aggregated)</option>
              {companies.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.company_name}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Executive KPI Summary Cards */}
        <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-500">
                Total Stock Items
              </span>
              <div className="rounded-lg bg-indigo-50 p-2 text-indigo-600">
                <Boxes className="h-4 w-4" />
              </div>
            </div>
            <p className="mt-3 text-2xl font-black text-slate-900">{summary.total_items}</p>
            <p className="mt-1 text-xs text-slate-500">Registered SKU items in catalog</p>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-500">
                Total Inventory Value
              </span>
              <div className="rounded-lg bg-emerald-50 p-2 text-emerald-600">
                <DollarSign className="h-4 w-4" />
              </div>
            </div>
            <p className="mt-3 text-2xl font-black text-emerald-600">
              {formatCurrency(summary.total_value)}
            </p>
            <p className="mt-1 text-xs text-slate-500">Weighted avg procurement valuation</p>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-500">
                Low Stock Alerts
              </span>
              <div className="rounded-lg bg-rose-50 p-2 text-rose-600">
                <AlertTriangle className="h-4 w-4" />
              </div>
            </div>
            <p className="mt-3 text-2xl font-black text-rose-600">{summary.low_stock_count}</p>
            <p className="mt-1 text-xs text-slate-500">Items below configured reorder level</p>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-500">
                Categories & Outlets
              </span>
              <div className="rounded-lg bg-blue-50 p-2 text-blue-600">
                <Building2 className="h-4 w-4" />
              </div>
            </div>
            <p className="mt-3 text-2xl font-black text-blue-600">
              {categories.length}{" "}
              <span className="text-sm font-semibold text-slate-500">
                / {companies.length} Co.
              </span>
            </p>
            <p className="mt-1 text-xs text-slate-500">Active distribution nodes</p>
          </div>
        </div>

        {/* ================= TAB 1: STOCK ITEMS MASTER & VALUATION ================= */}
        {activeTab === "stock" && (
          <div className="space-y-4">
            {/* Filter Section */}
            <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-6">
                {/* Search */}
                <div className="lg:col-span-2">
                  <label className="mb-1 block text-xs font-semibold text-slate-600">Search</label>
                  <div className="relative">
                    <Search className="absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-400" />
                    <input
                      type="text"
                      value={searchQuery}
                      onChange={(e) => {
                        setSearchQuery(e.target.value);
                        setPage(1);
                      }}
                      placeholder="Item name, code, brand..."
                      className="w-full rounded-lg border border-slate-200 bg-slate-50 py-1.5 pl-8 pr-3 text-xs text-slate-800 outline-none focus:border-indigo-500 focus:bg-white focus:ring-2 focus:ring-indigo-500/20"
                    />
                  </div>
                </div>

                {/* Category */}
                <div>
                  <label className="mb-1 block text-xs font-semibold text-slate-600">Category</label>
                  <select
                    value={selectedCategory}
                    onChange={(e) => {
                      setSelectedCategory(e.target.value);
                      setPage(1);
                    }}
                    className="w-full rounded-lg border border-slate-200 bg-slate-50 px-2.5 py-1.5 text-xs text-slate-800 outline-none focus:border-indigo-500 focus:bg-white"
                  >
                    <option value="">All Categories</option>
                    {categories.map((c) => (
                      <option key={c} value={c}>
                        {c.replace(/_/g, " ")}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Stock Level Filter */}
                <div>
                  <label className="mb-1 block text-xs font-semibold text-slate-600">Stock Level</label>
                  <select
                    value={selectedStockLevel}
                    onChange={(e) => {
                      setSelectedStockLevel(e.target.value);
                      setPage(1);
                    }}
                    className="w-full rounded-lg border border-slate-200 bg-slate-50 px-2.5 py-1.5 text-xs text-slate-800 outline-none focus:border-indigo-500 focus:bg-white"
                  >
                    <option value="">All Levels</option>
                    <option value="in_stock">In Stock (&gt; 0)</option>
                    <option value="out_of_stock">Out of Stock (= 0)</option>
                    <option value="below_reorder">Below Reorder Level</option>
                    <option value="below_zero">Negative Stock (&lt; 0)</option>
                  </select>
                </div>

                {/* Specification */}
                <div>
                  <label className="mb-1 block text-xs font-semibold text-slate-600">Specification</label>
                  <select
                    value={selectedSpec}
                    onChange={(e) => {
                      setSelectedSpec(e.target.value);
                      setPage(1);
                    }}
                    className="w-full rounded-lg border border-slate-200 bg-slate-50 px-2.5 py-1.5 text-xs text-slate-800 outline-none focus:border-indigo-500 focus:bg-white"
                  >
                    <option value="">All Specs</option>
                    {availableSpecs.map((s) => (
                      <option key={s} value={s}>
                        {s}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Clear / Per Page */}
                <div className="flex items-end gap-2">
                  <div className="flex-1">
                    <label className="mb-1 block text-xs font-semibold text-slate-600">Per Page</label>
                    <select
                      value={pageSize}
                      onChange={(e) => {
                        setPageSize(Number(e.target.value));
                        setPage(1);
                      }}
                      className="w-full rounded-lg border border-slate-200 bg-slate-50 px-2.5 py-1.5 text-xs text-slate-800 outline-none focus:border-indigo-500 focus:bg-white"
                    >
                      <option value={20}>20</option>
                      <option value={50}>50</option>
                      <option value={100}>100</option>
                    </select>
                  </div>
                  <button
                    onClick={clearFilters}
                    title="Clear all filters"
                    className="rounded-lg border border-slate-200 p-2 text-slate-500 hover:bg-slate-100 hover:text-slate-800"
                  >
                    <X className="h-4 w-4" />
                  </button>
                </div>
              </div>
            </div>

            {/* Table Card */}
            <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
              <div className="flex items-center justify-between border-b border-slate-100 px-6 py-4">
                <div className="flex items-center gap-2">
                  <span className="font-bold text-slate-800">Stock Items Inventory</span>
                  <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-semibold text-slate-600">
                    {totalCount} Total
                  </span>
                </div>

                {/* Pagination Status */}
                <div className="flex items-center gap-2 text-xs text-slate-500">
                  <span>
                    Page {page} of {totalPages}
                  </span>
                </div>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="border-b border-slate-100 bg-slate-50/70 text-xs font-bold uppercase tracking-wider text-slate-500">
                      <th className="px-4 py-3.5">Image</th>
                      <th
                        className="cursor-pointer px-4 py-3.5 transition hover:text-indigo-600"
                        onClick={() => handleSort("item_code")}
                      >
                        <div className="flex items-center gap-1">
                          Code
                          <ArrowUpDown className="h-3 w-3" />
                        </div>
                      </th>
                      <th
                        className="cursor-pointer px-4 py-3.5 transition hover:text-indigo-600"
                        onClick={() => handleSort("item_name")}
                      >
                        <div className="flex items-center gap-1">
                          Item Name & Specs
                          <ArrowUpDown className="h-3 w-3" />
                        </div>
                      </th>
                      <th className="px-4 py-3.5">Category</th>
                      <th className="px-4 py-3.5">Companies</th>
                      <th className="px-4 py-3.5 text-right text-emerald-700">In</th>
                      <th className="px-4 py-3.5 text-right text-rose-700">Out</th>
                      <th
                        className="cursor-pointer px-4 py-3.5 text-right font-bold text-slate-900 transition hover:text-indigo-600"
                        onClick={() => handleSort("current_stock")}
                      >
                        <div className="flex items-center justify-end gap-1">
                          Balance
                          <ArrowUpDown className="h-3 w-3" />
                        </div>
                      </th>
                      <th className="px-4 py-3.5 text-center">Mkt Qty</th>
                      <th
                        className="cursor-pointer px-4 py-3.5 text-right transition hover:text-indigo-600"
                        onClick={() => handleSort("purchase_rate")}
                      >
                        <div className="flex items-center justify-end gap-1">
                          Avg Purchase
                          <ArrowUpDown className="h-3 w-3" />
                        </div>
                      </th>
                      <th
                        className="cursor-pointer px-4 py-3.5 text-right transition hover:text-indigo-600"
                        onClick={() => handleSort("selling_rate")}
                      >
                        <div className="flex items-center justify-end gap-1">
                          Selling Price
                          <ArrowUpDown className="h-3 w-3" />
                        </div>
                      </th>
                      <th
                        className="cursor-pointer px-4 py-3.5 text-right font-bold text-emerald-800 transition hover:text-indigo-600"
                        onClick={() => handleSort("total_value")}
                      >
                        <div className="flex items-center justify-end gap-1">
                          Valuation
                          <ArrowUpDown className="h-3 w-3" />
                        </div>
                      </th>
                      <th className="px-4 py-3.5 text-center">Status</th>
                      <th className="px-4 py-3.5 text-right">Actions</th>
                    </tr>
                  </thead>

                  <tbody className="divide-y divide-slate-100 text-xs">
                    {loading ? (
                      <tr>
                        <td colSpan={14} className="py-16 text-center text-slate-400">
                          <RefreshCw className="mx-auto h-6 w-6 animate-spin text-indigo-500" />
                          <p className="mt-2 font-medium">Loading Real-time Inventory Data...</p>
                        </td>
                      </tr>
                    ) : sortedStockItems.length === 0 ? (
                      <tr>
                        <td colSpan={14} className="py-16 text-center text-slate-400">
                          <Boxes className="mx-auto h-12 w-12 text-slate-300" />
                          <p className="mt-2 text-sm font-bold text-slate-700">No stock items found</p>
                          <p className="text-xs text-slate-500">
                            Try adjusting your filters or click "Add Stock Item" to get started.
                          </p>
                        </td>
                      </tr>
                    ) : (
                      sortedStockItems.map((item) => {
                        const stock = Number(item.current_stock || 0);
                        const reorder = Number(item.reorder_level || 10);
                        const totalIn = Number(item.total_qty_in || 0);
                        const totalOut = Number(item.total_qty_out || 0);
                        const hasMovement = totalIn > 0 || totalOut > 0;
                        const isLow = hasMovement && stock <= reorder;
                        const isNegative = stock < 0;
                        const avgPurchase = Number(item.effective_purchase_rate || item.purchase_rate || 0);
                        const selling = Number(item.effective_selling_rate || item.selling_rate || 0);
                        const valuation = stock * avgPurchase;

                        const imgUrl = item.primary_image
                          ? item.primary_image.startsWith("/")
                            ? item.primary_image
                            : `/storage/${item.primary_image}`
                          : null;

                        return (
                          <tr
                            key={item.id}
                            className="group transition hover:bg-indigo-50/30"
                          >
                            {/* Thumbnail */}
                            <td className="px-4 py-3">
                              {imgUrl ? (
                                <button
                                  type="button"
                                  onClick={() => setLightboxImage(imgUrl)}
                                  className="h-9 w-9 overflow-hidden rounded-lg border border-slate-200 bg-slate-100 shadow-sm transition hover:scale-105"
                                >
                                  <img
                                    src={imgUrl}
                                    alt={item.item_name}
                                    className="h-full w-full object-cover"
                                  />
                                </button>
                              ) : item.has_folder_link && item.folder_url ? (
                                <a
                                  href={item.folder_url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  title="View on Google Drive"
                                  className="flex h-9 w-9 items-center justify-center rounded-lg border border-blue-200 bg-blue-50 text-blue-600 hover:bg-blue-100"
                                >
                                  <ExternalLink className="h-4 w-4" />
                                </a>
                              ) : (
                                <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-slate-100 text-slate-400">
                                  <ImageIcon className="h-4 w-4" />
                                </div>
                              )}
                            </td>

                            {/* Item Code */}
                            <td className="px-4 py-3 font-mono font-bold text-slate-700">
                              {item.item_code}
                            </td>

                            {/* Item Name & Details */}
                            <td className="px-4 py-3">
                              <p className="font-bold text-slate-900">{item.item_name}</p>
                              <div className="flex flex-wrap items-center gap-1.5 pt-0.5 text-[11px] text-slate-500">
                                {item.brand && (
                                  <span className="rounded bg-slate-100 px-1.5 py-0.5 font-medium text-slate-700">
                                    {item.brand}
                                  </span>
                                )}
                                {item.model_compat && (
                                  <span className="max-w-[140px] truncate" title={item.model_compat}>
                                    {item.model_compat}
                                  </span>
                                )}
                                {item.size && (
                                  <span className="text-slate-400">· Size: {item.size}</span>
                                )}
                              </div>
                              {item.marketplace_linked && item.marketplace_sku && (
                                <div className="mt-1 inline-flex items-center gap-1 rounded bg-emerald-50 px-1.5 py-0.5 text-[10px] font-bold text-emerald-700">
                                  MKT: {item.marketplace_sku}
                                </div>
                              )}
                            </td>

                            {/* Category */}
                            <td className="px-4 py-3">
                              <span className="rounded-md bg-slate-100 px-2 py-0.5 text-[11px] font-semibold text-slate-700">
                                {item.item_category?.replace(/_/g, " ")}
                              </span>
                            </td>

                            {/* Companies */}
                            <td className="px-4 py-3">
                              <div className="flex max-w-[150px] flex-wrap gap-1">
                                {(item.applicable_companies || []).map((cid) => {
                                  const comp = companies.find((c) => c.id === cid);
                                  return (
                                    <span
                                      key={cid}
                                      className="rounded bg-violet-50 px-1.5 py-0.5 text-[10px] font-medium text-violet-700"
                                      title={comp?.company_name}
                                    >
                                      {comp?.company_name ? comp.company_name.slice(0, 12) : `Co #${cid}`}
                                    </span>
                                  );
                                })}
                              </div>
                            </td>

                            {/* Qty In */}
                            <td className="px-4 py-3 text-right font-mono font-semibold text-emerald-700">
                              {totalIn.toLocaleString("en-IN")}
                            </td>

                            {/* Qty Out */}
                            <td className="px-4 py-3 text-right font-mono font-semibold text-rose-700">
                              {totalOut.toLocaleString("en-IN")}
                            </td>

                            {/* Balance Qty */}
                            <td className="px-4 py-3 text-right font-mono text-sm font-bold text-slate-900">
                              {stock.toLocaleString("en-IN")}{" "}
                              <span className="text-[10px] font-normal text-slate-500">
                                {item.unit_of_measure || "PCS"}
                              </span>
                            </td>

                            {/* Marketplace Available Qty */}
                            <td className="px-4 py-3 text-center font-mono">
                              {item.marketplace_available_qty != null ? (
                                <span
                                  className={`rounded px-1.5 py-0.5 text-[11px] font-bold ${
                                    item.marketplace_available_qty > 0
                                      ? "bg-emerald-50 text-emerald-700"
                                      : "bg-rose-50 text-rose-700"
                                  }`}
                                >
                                  {item.marketplace_available_qty}
                                </span>
                              ) : (
                                <span className="text-slate-300">—</span>
                              )}
                            </td>

                            {/* Avg Purchase Rate */}
                            <td className="px-4 py-3 text-right font-mono text-slate-700">
                              {formatCurrency(avgPurchase)}
                              {item.is_average_price && (
                                <span className="ml-1 rounded bg-amber-50 px-1 py-0.2 text-[9px] font-bold text-amber-800">
                                  avg
                                </span>
                              )}
                            </td>

                            {/* Selling Price */}
                            <td className="px-4 py-3 text-right font-mono text-slate-700">
                              {formatCurrency(selling)}
                              {item.is_suggested_price && (
                                <span className="ml-1 rounded bg-indigo-50 px-1 py-0.2 text-[9px] font-bold text-indigo-700">
                                  ~
                                </span>
                              )}
                            </td>

                            {/* Total Valuation */}
                            <td className="px-4 py-3 text-right font-mono font-bold text-emerald-800">
                              {formatCurrency(valuation)}
                            </td>

                            {/* Status Pill */}
                            <td className="px-4 py-3 text-center">
                              {!hasMovement ? (
                                <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-bold text-slate-500">
                                  Unstocked
                                </span>
                              ) : isNegative ? (
                                <span className="rounded-full bg-rose-100 px-2 py-0.5 text-[10px] font-bold text-rose-800">
                                  Negative
                                </span>
                              ) : isLow ? (
                                <span className="rounded-full bg-rose-50 px-2 py-0.5 text-[10px] font-bold text-rose-700 border border-rose-200">
                                  Low Stock
                                </span>
                              ) : (
                                <span className="rounded-full bg-emerald-50 px-2 py-0.5 text-[10px] font-bold text-emerald-700 border border-emerald-200">
                                  In Stock
                                </span>
                              )}
                            </td>

                            {/* Action Buttons */}
                            <td className="px-4 py-3 text-right">
                              <div className="flex items-center justify-end gap-1">
                                <button
                                  onClick={() => openHistory(item)}
                                  title="View Item Stock Ledger History"
                                  className="rounded p-1.5 text-slate-500 transition hover:bg-slate-100 hover:text-indigo-600"
                                >
                                  <History className="h-3.5 w-3.5" />
                                </button>
                                <button
                                  onClick={() => openAdjust(item)}
                                  title="Adjust Stock Quantity (+ / -)"
                                  className="rounded p-1.5 text-slate-500 transition hover:bg-slate-100 hover:text-amber-600"
                                >
                                  <Sliders className="h-3.5 w-3.5" />
                                </button>
                                <button
                                  onClick={() => openEdit(item)}
                                  title="Edit Item Details & Opening Balance"
                                  className="rounded p-1.5 text-slate-500 transition hover:bg-slate-100 hover:text-indigo-600"
                                >
                                  <Edit className="h-3.5 w-3.5" />
                                </button>
                              </div>
                            </td>
                          </tr>
                        );
                      })
                    )}
                  </tbody>
                </table>
              </div>

              {/* Pagination Bar */}
              <div className="flex flex-col items-center justify-between gap-3 border-t border-slate-100 px-6 py-4 sm:flex-row">
                <p className="text-xs text-slate-500">
                  Showing {(page - 1) * pageSize + 1} to{" "}
                  {Math.min(page * pageSize, totalCount)} of {totalCount} stock items
                </p>

                <div className="flex items-center gap-1.5">
                  <button
                    onClick={() => setPage(1)}
                    disabled={page <= 1}
                    className="rounded-lg border border-slate-200 p-1.5 text-slate-600 hover:bg-slate-50 disabled:opacity-40"
                  >
                    <ChevronsLeft className="h-4 w-4" />
                  </button>
                  <button
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                    disabled={page <= 1}
                    className="rounded-lg border border-slate-200 p-1.5 text-slate-600 hover:bg-slate-50 disabled:opacity-40"
                  >
                    <ChevronLeft className="h-4 w-4" />
                  </button>

                  <span className="px-3 text-xs font-bold text-slate-700">
                    {page} / {totalPages}
                  </span>

                  <button
                    onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                    disabled={page >= totalPages}
                    className="rounded-lg border border-slate-200 p-1.5 text-slate-600 hover:bg-slate-50 disabled:opacity-40"
                  >
                    <ChevronRight className="h-4 w-4" />
                  </button>
                  <button
                    onClick={() => setPage(totalPages)}
                    disabled={page >= totalPages}
                    className="rounded-lg border border-slate-200 p-1.5 text-slate-600 hover:bg-slate-50 disabled:opacity-40"
                  >
                    <ChevronsRight className="h-4 w-4" />
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ================= TAB 2: STOCK LEDGER & AUDIT TRAIL ================= */}
        {activeTab === "ledger" && (
          <div className="space-y-4">
            <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 md:grid-cols-5">
                <div>
                  <label className="mb-1 block text-xs font-semibold text-slate-600">Company</label>
                  <select
                    value={ledgerCompany}
                    onChange={(e) => setLedgerCompany(e.target.value)}
                    className="w-full rounded-lg border border-slate-200 bg-slate-50 px-2.5 py-1.5 text-xs text-slate-800 outline-none"
                  >
                    <option value="">All Companies</option>
                    {companies.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.company_name}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="mb-1 block text-xs font-semibold text-slate-600">Entry Type</label>
                  <select
                    value={ledgerType}
                    onChange={(e) => setLedgerType(e.target.value)}
                    className="w-full rounded-lg border border-slate-200 bg-slate-50 px-2.5 py-1.5 text-xs text-slate-800 outline-none"
                  >
                    <option value="">All Types</option>
                    <option value="OPENING">OPENING</option>
                    <option value="PURCHASE">PURCHASE</option>
                    <option value="SALE">SALE</option>
                    <option value="TRANSFER_IN">TRANSFER_IN</option>
                    <option value="TRANSFER_OUT">TRANSFER_OUT</option>
                    <option value="SERVICE_CONSUMPTION">SERVICE_CONSUMPTION</option>
                  </select>
                </div>

                <div>
                  <label className="mb-1 block text-xs font-semibold text-slate-600">From Date</label>
                  <input
                    type="date"
                    value={ledgerFromDate}
                    onChange={(e) => setLedgerFromDate(e.target.value)}
                    className="w-full rounded-lg border border-slate-200 bg-slate-50 px-2.5 py-1.5 text-xs text-slate-800 outline-none"
                  />
                </div>

                <div>
                  <label className="mb-1 block text-xs font-semibold text-slate-600">To Date</label>
                  <input
                    type="date"
                    value={ledgerToDate}
                    onChange={(e) => setLedgerToDate(e.target.value)}
                    className="w-full rounded-lg border border-slate-200 bg-slate-50 px-2.5 py-1.5 text-xs text-slate-800 outline-none"
                  />
                </div>

                <div>
                  <label className="mb-1 block text-xs font-semibold text-slate-600">Search</label>
                  <input
                    type="text"
                    value={ledgerSearch}
                    onChange={(e) => setLedgerSearch(e.target.value)}
                    placeholder="Search ledger..."
                    className="w-full rounded-lg border border-slate-200 bg-slate-50 px-2.5 py-1.5 text-xs text-slate-800 outline-none"
                  />
                </div>
              </div>
            </div>

            <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse text-xs">
                  <thead>
                    <tr className="border-b border-slate-100 bg-slate-50/70 font-bold uppercase tracking-wider text-slate-500">
                      <th className="px-4 py-3">Date</th>
                      <th className="px-4 py-3">Company</th>
                      <th className="px-4 py-3">Item Details</th>
                      <th className="px-4 py-3">Entry Type</th>
                      <th className="px-4 py-3">Reference #</th>
                      <th className="px-4 py-3 text-right text-emerald-700">In</th>
                      <th className="px-4 py-3 text-right text-rose-700">Out</th>
                      <th className="px-4 py-3 text-right">Unit Rate</th>
                      <th className="px-4 py-3 text-right">Balance Qty</th>
                      <th className="px-4 py-3 text-right font-bold text-slate-900">Balance Value</th>
                      <th className="px-4 py-3">Narration</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {ledgerLoading ? (
                      <tr>
                        <td colSpan={11} className="py-16 text-center text-slate-400">
                          <RefreshCw className="mx-auto h-6 w-6 animate-spin text-indigo-500" />
                          <p className="mt-2 font-medium">Loading Stock Ledger...</p>
                        </td>
                      </tr>
                    ) : filteredLedgerEntries.length === 0 ? (
                      <tr>
                        <td colSpan={11} className="py-16 text-center text-slate-400">
                          No ledger movements found.
                        </td>
                      </tr>
                    ) : (
                      filteredLedgerEntries.map((row) => (
                        <tr key={row.id} className="hover:bg-slate-50">
                          <td className="px-4 py-2.5 font-mono text-slate-600">
                            {row.transaction_date || "-"}
                          </td>
                          <td className="px-4 py-2.5 font-semibold text-slate-800">
                            {row.company_name}
                          </td>
                          <td className="px-4 py-2.5">
                            <p className="font-bold text-slate-900">{row.item_name}</p>
                            <p className="font-mono text-[10px] text-slate-400">{row.item_code}</p>
                          </td>
                          <td className="px-4 py-2.5">
                            <span
                              className={`rounded px-2 py-0.5 text-[10px] font-bold ${
                                row.entry_type === "PURCHASE" || row.entry_type === "TRANSFER_IN"
                                  ? "bg-emerald-50 text-emerald-700"
                                  : row.entry_type === "SALE" || row.entry_type === "TRANSFER_OUT"
                                  ? "bg-rose-50 text-rose-700"
                                  : "bg-blue-50 text-blue-700"
                              }`}
                            >
                              {row.entry_type}
                            </span>
                            {row.is_estimate && (
                              <span className="ml-1 rounded bg-amber-50 px-1.5 py-0.5 text-[9px] font-bold text-amber-700">
                                ESTIMATE
                              </span>
                            )}
                          </td>
                          <td className="px-4 py-2.5 font-mono text-slate-700">
                            {row.reference_number || `${row.reference_type} #${row.reference_id}`}
                          </td>
                          <td className="px-4 py-2.5 text-right font-mono text-emerald-700 font-semibold">
                            {row.quantity_in > 0 ? row.quantity_in : "—"}
                          </td>
                          <td className="px-4 py-2.5 text-right font-mono text-rose-700 font-semibold">
                            {row.quantity_out > 0 ? row.quantity_out : "—"}
                          </td>
                          <td className="px-4 py-2.5 text-right font-mono text-slate-600">
                            {formatCurrency(row.unit_rate)}
                          </td>
                          <td className="px-4 py-2.5 text-right font-mono font-bold text-slate-900">
                            {row.balance_qty}
                          </td>
                          <td className="px-4 py-2.5 text-right font-mono font-bold text-emerald-800">
                            {formatCurrency(row.balance_value)}
                          </td>
                          <td className="px-4 py-2.5 text-slate-500 max-w-[200px] truncate" title={row.narration}>
                            {row.narration || "—"}
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* ================= TAB 3: MARGIN RULES ================= */}
        {activeTab === "margins" && (
          <div className="space-y-4">
            <div className="flex items-center justify-between rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
              <div>
                <h3 className="font-bold text-slate-800">Inter-Company Transfer Markup Rules</h3>
                <p className="text-xs text-slate-500">
                  Configure inter-company automated billing margin % applied during stock transfers between subsidiaries.
                </p>
              </div>
              <button
                onClick={() => setShowAddMarginModal(true)}
                className="inline-flex items-center gap-1.5 rounded-lg bg-indigo-600 px-3.5 py-2 text-xs font-semibold text-white shadow-sm hover:bg-indigo-700"
              >
                <Plus className="h-3.5 w-3.5" />
                Add Margin Rule
              </button>
            </div>

            <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="border-b border-slate-100 bg-slate-50/70 font-bold uppercase tracking-wider text-slate-500">
                    <th className="px-4 py-3">From Company</th>
                    <th className="px-4 py-3">To Company</th>
                    <th className="px-4 py-3">Category Scope</th>
                    <th className="px-4 py-3 text-right">Margin Markup %</th>
                    <th className="px-4 py-3 text-center">Status</th>
                    <th className="px-4 py-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {marginLoading ? (
                    <tr>
                      <td colSpan={6} className="py-12 text-center text-slate-400">
                        Loading Margin Rules...
                      </td>
                    </tr>
                  ) : marginConfigs.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="py-12 text-center text-slate-400">
                        No custom margin configs. Default margin is 6.00% across all entities.
                      </td>
                    </tr>
                  ) : (
                    marginConfigs.map((cfg) => {
                      const fromCo = companies.find((c) => c.id === cfg.from_company_id);
                      const toCo = companies.find((c) => c.id === cfg.to_company_id);
                      return (
                        <tr key={cfg.id} className="hover:bg-slate-50">
                          <td className="px-4 py-3 font-semibold text-slate-800">
                            {fromCo ? fromCo.company_name : "All Entities (Global)"}
                          </td>
                          <td className="px-4 py-3 font-semibold text-slate-800">
                            {toCo ? toCo.company_name : "All Entities (Global)"}
                          </td>
                          <td className="px-4 py-3">
                            <span className="rounded bg-slate-100 px-2 py-0.5 font-mono text-[11px] font-semibold text-slate-700">
                              {cfg.category_slug || "ALL CATEGORIES"}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-right font-mono font-bold text-indigo-700 text-sm">
                            {cfg.margin_pct}%
                          </td>
                          <td className="px-4 py-3 text-center">
                            <span
                              className={`rounded px-2 py-0.5 text-[10px] font-bold ${
                                cfg.is_active ? "bg-emerald-50 text-emerald-700" : "bg-slate-100 text-slate-500"
                              }`}
                            >
                              {cfg.is_active ? "Active" : "Inactive"}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-right">
                            <button
                              onClick={() => handleDeleteMargin(cfg.id)}
                              className="rounded p-1.5 text-rose-500 hover:bg-rose-50"
                            >
                              <Trash2 className="h-3.5 w-3.5" />
                            </button>
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </main>

      {/* ================= MODAL: CREATE / ADD STOCK ITEM ================= */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4 backdrop-blur-xs">
          <div className="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-2xl bg-white p-6 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-100 pb-4">
              <div>
                <h2 className="text-lg font-bold text-slate-900">Add Stock Item</h2>
                <p className="text-xs text-slate-500">
                  Register new material or product into SFMS accounts inventory
                </p>
              </div>
              <button
                onClick={() => setShowCreateModal(false)}
                className="rounded-lg p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-700"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <form onSubmit={handleCreateSubmit} className="mt-4 space-y-4 text-xs">
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <div>
                  <label className="mb-1 block font-semibold text-slate-700">Item Name *</label>
                  <input
                    type="text"
                    required
                    value={formData.item_name}
                    onChange={(e) => setFormData({ ...formData, item_name: e.target.value })}
                    placeholder="e.g. EV Battery 48V 60Ah"
                    className="w-full rounded-lg border border-slate-300 p-2 text-xs outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20"
                  />
                </div>

                <div>
                  <label className="mb-1 block font-semibold text-slate-700">
                    Item Code <span className="text-[10px] font-normal text-slate-400">(Auto or Custom)</span>
                  </label>
                  <input
                    type="text"
                    value={formData.item_code}
                    onChange={(e) => setFormData({ ...formData, item_code: e.target.value })}
                    placeholder="Auto-generated..."
                    className="w-full rounded-lg border border-slate-300 bg-slate-50 p-2 font-mono text-xs font-bold text-indigo-700 outline-none"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <div>
                  <label className="mb-1 block font-semibold text-slate-700">Category</label>
                  <select
                    value={formData.item_category}
                    onChange={(e) => handleCategoryChange(e.target.value)}
                    className="w-full rounded-lg border border-slate-300 p-2 text-xs outline-none focus:border-indigo-500"
                  >
                    {categories.map((c) => (
                      <option key={c} value={c}>
                        {c.replace(/_/g, " ")}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="mb-1 block font-semibold text-slate-700">Unit of Measure</label>
                  <select
                    value={formData.unit_of_measure}
                    onChange={(e) => setFormData({ ...formData, unit_of_measure: e.target.value })}
                    className="w-full rounded-lg border border-slate-300 p-2 text-xs outline-none focus:border-indigo-500"
                  >
                    {UOM_OPTIONS.map((u) => (
                      <option key={u} value={u}>
                        {u}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Applicable Companies */}
              <div>
                <label className="mb-1 block font-semibold text-slate-700">
                  Applicable Companies (Multi-Select)
                </label>
                <div className="flex flex-wrap gap-1.5 rounded-lg border border-slate-200 p-2">
                  {companies.map((comp) => {
                    const isSelected = formData.applicable_companies.includes(comp.id);
                    return (
                      <button
                        key={comp.id}
                        type="button"
                        onClick={() => {
                          const updated = isSelected
                            ? formData.applicable_companies.filter((id) => id !== comp.id)
                            : [...formData.applicable_companies, comp.id];
                          setFormData({ ...formData, applicable_companies: updated });
                        }}
                        className={`rounded-full px-2.5 py-1 text-[11px] font-semibold transition ${
                          isSelected
                            ? "bg-indigo-600 text-white"
                            : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                        }`}
                      >
                        {comp.company_name}
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Specs and details */}
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
                <div>
                  <label className="mb-1 block font-semibold text-slate-700">Brand / Maker</label>
                  <input
                    type="text"
                    value={formData.brand}
                    onChange={(e) => setFormData({ ...formData, brand: e.target.value })}
                    placeholder="e.g. Bosch, Exide"
                    className="w-full rounded-lg border border-slate-300 p-2 text-xs outline-none"
                  />
                </div>
                <div>
                  <label className="mb-1 block font-semibold text-slate-700">Model Compatibility</label>
                  <input
                    type="text"
                    value={formData.model_compat}
                    onChange={(e) => setFormData({ ...formData, model_compat: e.target.value })}
                    placeholder="e.g. Activa 6G"
                    className="w-full rounded-lg border border-slate-300 p-2 text-xs outline-none"
                  />
                </div>
                <div>
                  <label className="mb-1 block font-semibold text-slate-700">Size</label>
                  <input
                    type="text"
                    value={formData.size}
                    onChange={(e) => setFormData({ ...formData, size: e.target.value })}
                    placeholder="e.g. Standard, XL"
                    className="w-full rounded-lg border border-slate-300 p-2 text-xs outline-none"
                  />
                </div>
              </div>

              <div>
                <label className="mb-1 block font-semibold text-slate-700">Specification Details</label>
                <textarea
                  rows={2}
                  value={formData.specification}
                  onChange={(e) => setFormData({ ...formData, specification: e.target.value })}
                  placeholder="Technical specs..."
                  className="w-full rounded-lg border border-slate-300 p-2 text-xs outline-none"
                />
              </div>

              {/* Pricing and Markup Calculator */}
              <div className="rounded-xl border border-indigo-100 bg-indigo-50/40 p-4">
                <div className="mb-2 flex items-center gap-2">
                  <DollarSign className="h-4 w-4 text-indigo-600" />
                  <span className="font-bold text-indigo-900">Pricing & Markup Engine</span>
                </div>
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
                  <div>
                    <label className="mb-1 block font-semibold text-slate-700">Purchase Rate (₹)</label>
                    <input
                      type="number"
                      step="0.01"
                      min="0"
                      value={formData.purchase_rate || ""}
                      onChange={(e) => handlePurchaseRateChange(parseFloat(e.target.value) || 0)}
                      placeholder="0.00"
                      className="w-full rounded-lg border border-slate-300 bg-white p-2 font-mono text-xs font-semibold outline-none"
                    />
                  </div>

                  <div>
                    <label className="mb-1 block font-semibold text-slate-700">Markup %</label>
                    <input
                      type="number"
                      step="0.5"
                      min="0"
                      value={formData.markup_pct}
                      onChange={(e) => handleMarkupPctChange(parseFloat(e.target.value) || 0)}
                      className="w-full rounded-lg border border-slate-300 bg-white p-2 font-mono text-xs font-semibold outline-none"
                    />
                  </div>

                  <div>
                    <label className="mb-1 block font-semibold text-slate-700">
                      Selling Rate (₹) <span className="text-[10px] text-slate-400">(Auto-calculated)</span>
                    </label>
                    <input
                      type="number"
                      step="0.01"
                      min="0"
                      value={formData.selling_rate || ""}
                      onChange={(e) => setFormData({ ...formData, selling_rate: parseFloat(e.target.value) || 0 })}
                      className="w-full rounded-lg border border-slate-300 bg-white p-2 font-mono text-xs font-bold text-emerald-700 outline-none"
                    />
                  </div>
                </div>
              </div>

              {/* HSN Code & Reorder Level */}
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
                <div>
                  <label className="mb-1 block font-semibold text-slate-700">Reorder Level (Min Stock)</label>
                  <input
                    type="number"
                    min="0"
                    value={formData.reorder_level}
                    onChange={(e) => setFormData({ ...formData, reorder_level: parseInt(e.target.value) || 0 })}
                    className="w-full rounded-lg border border-slate-300 p-2 text-xs outline-none"
                  />
                </div>

                <div className="sm:col-span-2">
                  <div className="flex items-center justify-between">
                    <label className="mb-1 block font-semibold text-slate-700">HSN Code & GST</label>
                    <button
                      type="button"
                      onClick={() => setShowHsnSubModal(true)}
                      className="text-[11px] font-bold text-indigo-600 hover:underline"
                    >
                      + Create New HSN
                    </button>
                  </div>
                  <select
                    value={formData.hsn_id || ""}
                    onChange={(e) => {
                      const id = e.target.value ? parseInt(e.target.value) : null;
                      const hsnObj = hsnList.find((h) => h.id === id);
                      setFormData({
                        ...formData,
                        hsn_id: id,
                        gst_rate_display: hsnObj ? `${hsnObj.igst_rate || hsnObj.gst_rate || 18}%` : ""
                      });
                    }}
                    className="w-full rounded-lg border border-slate-300 p-2 text-xs outline-none"
                  >
                    <option value="">-- Select HSN Code --</option>
                    {hsnList.map((h) => (
                      <option key={h.id} value={h.id}>
                        {h.hsn_code} - {h.description} ({h.igst_rate || h.gst_rate || 18}% GST)
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Google Drive Image Link */}
              <div>
                <label className="mb-1 block font-semibold text-slate-700">
                  Google Drive Image URL / Folder Link (Optional)
                </label>
                <input
                  type="text"
                  value={formData.image_url}
                  onChange={(e) => setFormData({ ...formData, image_url: e.target.value })}
                  placeholder="https://drive.google.com/..."
                  className="w-full rounded-lg border border-slate-300 p-2 text-xs outline-none"
                />
              </div>

              <div className="flex items-center gap-2 pt-2">
                <input
                  type="checkbox"
                  id="create_show_mkt"
                  checked={formData.show_in_marketplace}
                  onChange={(e) => setFormData({ ...formData, show_in_marketplace: e.target.checked })}
                  className="h-4 w-4 rounded border-slate-300 text-indigo-600"
                />
                <label htmlFor="create_show_mkt" className="font-semibold text-slate-700 cursor-pointer">
                  Show in Marketplace E-Commerce Catalog
                </label>
              </div>

              <div className="flex justify-end gap-2 border-t border-slate-100 pt-4">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="rounded-lg border border-slate-300 px-4 py-2 font-semibold text-slate-700 hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="rounded-lg bg-indigo-600 px-5 py-2 font-semibold text-white shadow hover:bg-indigo-700"
                >
                  Save Stock Item
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ================= MODAL: EDIT STOCK ITEM & OPENING BALANCE ================= */}
      {showEditModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4 backdrop-blur-xs">
          <div className="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-2xl bg-white p-6 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-100 pb-4">
              <div>
                <h2 className="text-lg font-bold text-slate-900">
                  Edit Stock Item · <span className="font-mono text-indigo-600">{formData.item_code}</span>
                </h2>
                <p className="text-xs text-slate-500">Update item master, opening balance, and marketplace linkage</p>
              </div>
              <button
                onClick={() => setShowEditModal(false)}
                className="rounded-lg p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-700"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <form onSubmit={handleUpdateSubmit} className="mt-4 space-y-4 text-xs">
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <div>
                  <label className="mb-1 block font-semibold text-slate-700">Item Name *</label>
                  <input
                    type="text"
                    required
                    value={formData.item_name}
                    onChange={(e) => setFormData({ ...formData, item_name: e.target.value })}
                    className="w-full rounded-lg border border-slate-300 p-2 text-xs outline-none"
                  />
                </div>

                <div>
                  <label className="mb-1 block font-semibold text-slate-700">Category</label>
                  <select
                    value={formData.item_category}
                    onChange={(e) => setFormData({ ...formData, item_category: e.target.value })}
                    className="w-full rounded-lg border border-slate-300 p-2 text-xs outline-none"
                  >
                    {categories.map((c) => (
                      <option key={c} value={c}>
                        {c.replace(/_/g, " ")}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Pricing */}
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
                <div>
                  <label className="mb-1 block font-semibold text-slate-700">Purchase Rate (₹)</label>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    value={formData.purchase_rate || ""}
                    onChange={(e) => handlePurchaseRateChange(parseFloat(e.target.value) || 0)}
                    className="w-full rounded-lg border border-slate-300 p-2 font-mono text-xs outline-none"
                  />
                </div>

                <div>
                  <label className="mb-1 block font-semibold text-slate-700">Markup %</label>
                  <input
                    type="number"
                    step="0.5"
                    value={formData.markup_pct}
                    onChange={(e) => handleMarkupPctChange(parseFloat(e.target.value) || 0)}
                    className="w-full rounded-lg border border-slate-300 p-2 font-mono text-xs outline-none"
                  />
                </div>

                <div>
                  <label className="mb-1 block font-semibold text-slate-700">Selling Rate (₹)</label>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    value={formData.selling_rate || ""}
                    onChange={(e) => setFormData({ ...formData, selling_rate: parseFloat(e.target.value) || 0 })}
                    className="w-full rounded-lg border border-slate-300 p-2 font-mono text-xs font-bold text-emerald-700 outline-none"
                  />
                </div>
              </div>

              {/* Marketplace Link */}
              <div className="rounded-xl border border-emerald-200 bg-emerald-50/50 p-3">
                <label className="mb-1 block font-bold text-emerald-950">Marketplace Link SKU</label>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={formData.marketplace_sku}
                    onChange={(e) => setFormData({ ...formData, marketplace_sku: e.target.value })}
                    placeholder="e.g. EV-BAT-001"
                    className="flex-1 rounded-lg border border-emerald-300 bg-white p-2 font-mono text-xs outline-none"
                  />
                </div>
              </div>

              {/* Record Opening Balance (One-Time) */}
              <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
                <div className="flex items-center gap-2 mb-2">
                  <Boxes className="h-4 w-4 text-slate-600" />
                  <span className="font-bold text-slate-800">Record Initial Opening Balance</span>
                </div>
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
                  <div>
                    <label className="mb-1 block font-medium text-slate-600">Opening Qty</label>
                    <input
                      type="number"
                      step="0.01"
                      value={formData.opening_qty}
                      onChange={(e) => setFormData({ ...formData, opening_qty: e.target.value })}
                      placeholder="e.g. 50"
                      className="w-full rounded-lg border border-slate-300 bg-white p-2 text-xs outline-none"
                    />
                  </div>
                  <div>
                    <label className="mb-1 block font-medium text-slate-600">Total Value (₹)</label>
                    <input
                      type="number"
                      step="0.01"
                      value={formData.opening_value}
                      onChange={(e) => setFormData({ ...formData, opening_value: e.target.value })}
                      placeholder="e.g. 25000"
                      className="w-full rounded-lg border border-slate-300 bg-white p-2 text-xs outline-none"
                    />
                  </div>
                  <div>
                    <label className="mb-1 block font-medium text-slate-600">As of Date</label>
                    <input
                      type="date"
                      value={formData.opening_date}
                      onChange={(e) => setFormData({ ...formData, opening_date: e.target.value })}
                      className="w-full rounded-lg border border-slate-300 bg-white p-2 text-xs outline-none"
                    />
                  </div>
                </div>
                <button
                  type="button"
                  onClick={handleSaveOpeningBalance}
                  className="mt-3 inline-flex items-center gap-1.5 rounded-lg border border-emerald-600 bg-white px-3 py-1.5 text-xs font-semibold text-emerald-700 shadow-sm hover:bg-emerald-50"
                >
                  <Plus className="h-3.5 w-3.5" />
                  Post Opening Balance to Ledger
                </button>
              </div>

              <div className="flex items-center gap-4">
                <label className="flex items-center gap-2 font-semibold text-slate-700 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={formData.is_active}
                    onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                    className="h-4 w-4 rounded border-slate-300 text-indigo-600"
                  />
                  Item is Active
                </label>

                <label className="flex items-center gap-2 font-semibold text-slate-700 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={formData.show_in_marketplace}
                    onChange={(e) => setFormData({ ...formData, show_in_marketplace: e.target.checked })}
                    className="h-4 w-4 rounded border-slate-300 text-indigo-600"
                  />
                  Show in Marketplace
                </label>
              </div>

              <div className="flex justify-end gap-2 border-t border-slate-100 pt-4">
                <button
                  type="button"
                  onClick={() => setShowEditModal(false)}
                  className="rounded-lg border border-slate-300 px-4 py-2 font-semibold text-slate-700 hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="rounded-lg bg-indigo-600 px-5 py-2 font-semibold text-white shadow hover:bg-indigo-700"
                >
                  Update Item Master
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ================= MODAL: STOCK ADJUSTMENT ================= */}
      {showAdjustModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4 backdrop-blur-xs">
          <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div>
                <h3 className="font-bold text-slate-900">Adjust Physical Stock</h3>
                <p className="text-xs text-slate-500">
                  {adjForm.item_code} · {adjForm.item_name}
                </p>
              </div>
              <button
                onClick={() => setShowAdjustModal(false)}
                className="rounded-lg p-1 text-slate-400 hover:bg-slate-100"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <form onSubmit={handleAdjustSubmit} className="mt-4 space-y-3 text-xs">
              <div>
                <label className="mb-1 block font-semibold text-slate-700">Target Company *</label>
                <select
                  required
                  value={adjForm.company_id}
                  onChange={(e) => setAdjForm({ ...adjForm, company_id: e.target.value })}
                  className="w-full rounded-lg border border-slate-300 p-2 text-xs outline-none"
                >
                  <option value="">-- Select Company --</option>
                  {companies.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.company_name}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="mb-1 block font-semibold text-slate-700">
                  Adjustment Delta Quantity (+ or -) *
                </label>
                <input
                  type="number"
                  step="0.01"
                  required
                  value={adjForm.delta_qty}
                  onChange={(e) => setAdjForm({ ...adjForm, delta_qty: e.target.value })}
                  placeholder="e.g. +5 or -3"
                  className="w-full rounded-lg border border-slate-300 p-2 font-mono text-xs font-bold outline-none"
                />
                {adjForm.delta_qty && parseFloat(adjForm.delta_qty) !== 0 && (
                  <p
                    className={`mt-1 font-bold ${
                      parseFloat(adjForm.delta_qty) > 0 ? "text-emerald-600" : "text-rose-600"
                    }`}
                  >
                    {parseFloat(adjForm.delta_qty) > 0
                      ? `▲ Adding +${Math.abs(parseFloat(adjForm.delta_qty))} units to stock`
                      : `▼ Deducting -${Math.abs(parseFloat(adjForm.delta_qty))} units from stock`}
                  </p>
                )}
              </div>

              <div>
                <label className="mb-1 block font-semibold text-slate-700">Unit Valuation Rate (₹)</label>
                <input
                  type="number"
                  step="0.01"
                  value={adjForm.rate}
                  onChange={(e) => setAdjForm({ ...adjForm, rate: e.target.value })}
                  placeholder="Rate per unit"
                  className="w-full rounded-lg border border-slate-300 p-2 font-mono text-xs outline-none"
                />
              </div>

              <div>
                <label className="mb-1 block font-semibold text-slate-700">Reason / Narration</label>
                <input
                  type="text"
                  value={adjForm.reason}
                  onChange={(e) => setAdjForm({ ...adjForm, reason: e.target.value })}
                  placeholder="e.g. Physical audit count reconciliation"
                  className="w-full rounded-lg border border-slate-300 p-2 text-xs outline-none"
                />
              </div>

              <div className="flex justify-end gap-2 border-t border-slate-100 pt-4">
                <button
                  type="button"
                  onClick={() => setShowAdjustModal(false)}
                  className="rounded-lg border border-slate-300 px-4 py-2 font-semibold text-slate-700 hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="rounded-lg bg-emerald-600 px-4 py-2 font-semibold text-white shadow hover:bg-emerald-700"
                >
                  Post Adjustment
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ================= MODAL: ITEM HISTORY DRILLDOWN ================= */}
      {showHistoryModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4 backdrop-blur-xs">
          <div className="max-h-[85vh] w-full max-w-3xl overflow-y-auto rounded-2xl bg-white p-6 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div>
                <h3 className="font-bold text-slate-900">
                  Stock Ledger History · <span className="font-mono text-indigo-600">{historyItem?.code}</span>
                </h3>
                <p className="text-xs text-slate-500">{historyItem?.name}</p>
              </div>
              <button
                onClick={() => setShowHistoryModal(false)}
                className="rounded-lg p-1 text-slate-400 hover:bg-slate-100"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="mt-4 overflow-x-auto">
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="border-b border-slate-100 bg-slate-50 font-bold uppercase tracking-wider text-slate-500">
                    <th className="px-3 py-2">Date</th>
                    <th className="px-3 py-2">Company</th>
                    <th className="px-3 py-2">Type</th>
                    <th className="px-3 py-2 text-right text-emerald-700">In</th>
                    <th className="px-3 py-2 text-right text-rose-700">Out</th>
                    <th className="px-3 py-2 text-right">Balance</th>
                    <th className="px-3 py-2">Ref</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {historyLoading ? (
                    <tr>
                      <td colSpan={7} className="py-8 text-center text-slate-400">
                        Loading transaction history...
                      </td>
                    </tr>
                  ) : historyEntries.length === 0 ? (
                    <tr>
                      <td colSpan={7} className="py-8 text-center text-slate-400">
                        No ledger movements recorded for this item.
                      </td>
                    </tr>
                  ) : (
                    historyEntries.map((e) => (
                      <tr key={e.id} className="hover:bg-slate-50">
                        <td className="px-3 py-2 font-mono text-slate-600">{e.transaction_date}</td>
                        <td className="px-3 py-2 font-semibold text-slate-800">{e.company_name}</td>
                        <td className="px-3 py-2 font-bold">{e.entry_type}</td>
                        <td className="px-3 py-2 text-right font-mono font-semibold text-emerald-700">
                          {e.quantity_in > 0 ? e.quantity_in : "—"}
                        </td>
                        <td className="px-3 py-2 text-right font-mono font-semibold text-rose-700">
                          {e.quantity_out > 0 ? e.quantity_out : "—"}
                        </td>
                        <td className="px-3 py-2 text-right font-mono font-bold text-slate-900">
                          {e.balance_qty}
                        </td>
                        <td className="px-3 py-2 font-mono text-[11px] text-slate-500">
                          {e.reference_number || e.reference_type}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* ================= MODAL: BULK UPLOAD ================= */}
      {showBulkUploadModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4 backdrop-blur-xs">
          <div className="w-full max-w-lg rounded-2xl bg-white p-6 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div>
                <h3 className="font-bold text-slate-900">Bulk Stock Items Upload</h3>
                <p className="text-xs text-slate-500">Import hundreds of stock items via Excel spreadsheet</p>
              </div>
              <button
                onClick={() => setShowBulkUploadModal(false)}
                className="rounded-lg p-1 text-slate-400 hover:bg-slate-100"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="mt-4 space-y-4 text-xs">
              <div className="rounded-xl border-2 border-dashed border-slate-300 p-6 text-center hover:bg-slate-50">
                <FileSpreadsheet className="mx-auto h-10 w-10 text-indigo-500" />
                <p className="mt-2 font-bold text-slate-700">Select Excel File (.xlsx, .xls)</p>
                <input
                  type="file"
                  accept=".xlsx,.xls"
                  onChange={(e) => setBulkFile(e.target.files?.[0] || null)}
                  className="mt-2 text-xs text-slate-500"
                />
                {bulkFile && (
                  <p className="mt-2 font-semibold text-indigo-600">Selected: {bulkFile.name}</p>
                )}
              </div>

              {bulkResult && (
                <div
                  className={`rounded-xl p-3 text-xs ${
                    bulkResult.success ? "bg-emerald-50 text-emerald-800" : "bg-amber-50 text-amber-800"
                  }`}
                >
                  <p className="font-bold">{bulkResult.message || "Upload Processed"}</p>
                  {bulkResult.imported_count != null && (
                    <p>Successfully imported: {bulkResult.imported_count} item(s)</p>
                  )}
                  {bulkResult.errors?.length > 0 && (
                    <div className="mt-2 max-h-32 overflow-y-auto font-mono text-[11px] text-rose-700">
                      {bulkResult.errors.map((err: any, idx: number) => (
                        <p key={idx}>• Row {err.row}: {err.message || JSON.stringify(err)}</p>
                      ))}
                    </div>
                  )}
                </div>
              )}

              <div className="flex justify-end gap-2 border-t border-slate-100 pt-4">
                <button
                  type="button"
                  onClick={() => setShowBulkUploadModal(false)}
                  className="rounded-lg border border-slate-300 px-4 py-2 font-semibold text-slate-700 hover:bg-slate-50"
                >
                  Close
                </button>
                <button
                  type="button"
                  disabled={!bulkFile || bulkUploading}
                  onClick={handleBulkUpload}
                  className="rounded-lg bg-indigo-600 px-5 py-2 font-semibold text-white shadow hover:bg-indigo-700 disabled:opacity-50"
                >
                  {bulkUploading ? "Uploading..." : "Process Upload"}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ================= MODAL: QUICK CREATE HSN ================= */}
      {showHsnSubModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 p-4 backdrop-blur-xs">
          <div className="w-full max-w-sm rounded-2xl bg-white p-5 shadow-2xl">
            <h4 className="font-bold text-slate-900">Create HSN Code</h4>
            <form onSubmit={handleCreateHsn} className="mt-3 space-y-3 text-xs">
              <div>
                <label className="mb-1 block font-semibold text-slate-700">HSN/SAC Code *</label>
                <input
                  type="text"
                  required
                  value={newHsn.hsn_code}
                  onChange={(e) => setNewHsn({ ...newHsn, hsn_code: e.target.value })}
                  placeholder="e.g. 85076000"
                  className="w-full rounded-lg border border-slate-300 p-2 font-mono text-xs outline-none"
                />
              </div>

              <div>
                <label className="mb-1 block font-semibold text-slate-700">Description *</label>
                <input
                  type="text"
                  required
                  value={newHsn.description}
                  onChange={(e) => setNewHsn({ ...newHsn, description: e.target.value })}
                  placeholder="e.g. Lithium-ion accumulators"
                  className="w-full rounded-lg border border-slate-300 p-2 text-xs outline-none"
                />
              </div>

              <div>
                <label className="mb-1 block font-semibold text-slate-700">GST Rate (%)</label>
                <select
                  value={newHsn.gst_rate}
                  onChange={(e) => setNewHsn({ ...newHsn, gst_rate: parseFloat(e.target.value) })}
                  className="w-full rounded-lg border border-slate-300 p-2 text-xs outline-none"
                >
                  <option value={0}>0% GST</option>
                  <option value={5}>5% GST</option>
                  <option value={12}>12% GST</option>
                  <option value={18}>18% GST (Standard)</option>
                  <option value={28}>28% GST</option>
                </select>
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowHsnSubModal(false)}
                  className="rounded-lg border border-slate-300 px-3 py-1.5 font-semibold text-slate-700"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="rounded-lg bg-indigo-600 px-4 py-1.5 font-semibold text-white shadow"
                >
                  Save HSN
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ================= MODAL: ADD MARGIN CONFIG ================= */}
      {showAddMarginModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4 backdrop-blur-xs">
          <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl">
            <h3 className="font-bold text-slate-900">Add Inter-Company Margin Rule</h3>
            <form onSubmit={handleCreateMargin} className="mt-4 space-y-3 text-xs">
              <div>
                <label className="mb-1 block font-semibold text-slate-700">Source Entity (From)</label>
                <select
                  value={newMarginForm.from_company_id}
                  onChange={(e) => setNewMarginForm({ ...newMarginForm, from_company_id: e.target.value })}
                  className="w-full rounded-lg border border-slate-300 p-2 text-xs outline-none"
                >
                  <option value="">All Entities (Global)</option>
                  {companies.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.company_name}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="mb-1 block font-semibold text-slate-700">Destination Entity (To)</label>
                <select
                  value={newMarginForm.to_company_id}
                  onChange={(e) => setNewMarginForm({ ...newMarginForm, to_company_id: e.target.value })}
                  className="w-full rounded-lg border border-slate-300 p-2 text-xs outline-none"
                >
                  <option value="">All Entities (Global)</option>
                  {companies.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.company_name}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="mb-1 block font-semibold text-slate-700">Category Scope (Optional)</label>
                <input
                  type="text"
                  value={newMarginForm.category_slug}
                  onChange={(e) => setNewMarginForm({ ...newMarginForm, category_slug: e.target.value })}
                  placeholder="e.g. BATTERIES or leave blank for all"
                  className="w-full rounded-lg border border-slate-300 p-2 text-xs outline-none"
                />
              </div>

              <div>
                <label className="mb-1 block font-semibold text-slate-700">Inter-Company Margin % *</label>
                <input
                  type="number"
                  step="0.1"
                  required
                  value={newMarginForm.margin_pct}
                  onChange={(e) => setNewMarginForm({ ...newMarginForm, margin_pct: parseFloat(e.target.value) || 0 })}
                  className="w-full rounded-lg border border-slate-300 p-2 font-mono text-xs font-bold outline-none"
                />
              </div>

              <div className="flex justify-end gap-2 border-t border-slate-100 pt-4">
                <button
                  type="button"
                  onClick={() => setShowAddMarginModal(false)}
                  className="rounded-lg border border-slate-300 px-4 py-2 font-semibold text-slate-700 hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="rounded-lg bg-indigo-600 px-4 py-2 font-semibold text-white shadow hover:bg-indigo-700"
                >
                  Save Margin Rule
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ================= LIGHTBOX MODAL ================= */}
      {lightboxImage && (
        <div
          onClick={() => setLightboxImage(null)}
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/90 p-4 cursor-pointer"
        >
          <img
            src={lightboxImage}
            alt="Enlarged"
            className="max-h-[85vh] max-w-[85vw] rounded-xl object-contain shadow-2xl"
          />
        </div>
      )}
    </div>
  );
}
