"use client";

import React, { useState, useEffect, useMemo, useCallback } from "react";
import Link from "next/link";
import { useStaffAuth } from "@/contexts/StaffAuthContext";
import api from "@/lib/api";
import toast, { Toaster } from "react-hot-toast";

// UI Components
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Checkbox } from "@/components/ui/checkbox";

// Icons
import {
  Users,
  Building2,
  Truck,
  Handshake,
  UserCheck,
  BookOpen,
  MinusCircle,
  PlusCircle,
  Plus,
  Search,
  RotateCcw,
  Pencil,
  Trash2,
  Folder,
  FolderOpen,
  Coins,
  Receipt,
  IndianRupee,
  MapPin,
  Scale,
  Loader2,
  History,
  X,
  AlertTriangle,
  ArrowUpRight,
  ArrowDownLeft,
  Layers,
  Landmark,
  QrCode,
} from "lucide-react";

// Types & Interfaces
interface Company {
  id: number;
  company_name: string;
  company_code?: string;
  company_type?: string;
  is_active?: boolean;
  address?: string;
  city?: string;
  state?: string;
  pincode?: string;
  gst_number?: string;
  pan_number?: string;
  cin_number?: string;
  phone?: string;
  email?: string;
  website?: string;
  is_marketplace_endpoint?: boolean;
}

interface OpeningBalanceRow {
  company_id: number | null;
  amount: number;
  type: "CREDIT" | "DEBIT";
  date: string | null;
}

interface Vendor {
  id: number;
  vendor_name: string;
  vendor_code: string;
  vendor_type: string;
  is_active?: boolean;
  email?: string;
  gst_number?: string;
  pan_number?: string;
  gst_type?: string;
  trade_name?: string;
  phone?: string;
  contact_person?: string;
  contact_person_1_name?: string;
  contact_person_1_phone?: string;
  contact_person_1_designation?: string;
  contact_person_2_name?: string;
  contact_person_2_phone?: string;
  contact_person_2_designation?: string;
  website_url?: string;
  address?: string;
  pincode?: string;
  city?: string;
  state?: string;
  map_link_1_label?: string;
  map_link_1?: string;
  map_link_2_label?: string;
  map_link_2?: string;
  ship_to_address?: string;
  ship_to_pincode?: string;
  ship_to_city?: string;
  ship_to_state?: string;
  bank_name?: string;
  bank_branch?: string;
  account_number?: string;
  ifsc_code?: string;
  account_holder_name?: string;
  upi_id?: string;
  payment_scanner_path?: string;
  payment_terms?: string;
  credit_limit?: number;
  credit_days?: number;
  terms_conditions?: string;
  applicable_companies?: (number | string)[];
  product_ids?: number[];
  opening_balances?: OpeningBalanceRow[];
}

interface Partner {
  id: number;
  name: string;
  code?: string;
  category: string;
  is_active: boolean;
  gst?: string;
  pan?: string;
  phone?: string;
  email?: string;
  whatsapp_number?: string;
  contact_person?: string;
  contact_person_1_name?: string;
  contact_person_1_phone?: string;
  contact_person_1_designation?: string;
  contact_person_2_name?: string;
  contact_person_2_phone?: string;
  address?: string;
  city?: string;
  state?: string;
  pincode?: string;
  zone?: string;
  bank_name?: string;
  bank_branch?: string;
  account_number?: string;
  ifsc_code?: string;
  payment_terms?: string;
  credit_limit?: number;
  credit_days?: number;
  opening_balance?: number;
  opening_balance_type?: string;
  opening_balance_date?: string;
  opening_balances?: OpeningBalanceRow[];
}

interface StaffMember {
  id: number;
  code: string;
  name: string;
  role: string;
  department: string;
  phone: string;
  status: string;
}

interface LedgerParty {
  party_name: string;
  party_type: string;
  party_id?: string | number;
  display_name?: string;
  total_debit: number;
  total_credit: number;
  balance: number;
}

interface ExpenseMainCat {
  id: number;
  name: string;
  description?: string;
}

interface ExpenseSubCat {
  id: number;
  parent_id: number;
  name: string;
  description?: string;
}

interface CategoryAmountSummary {
  [id: string]: {
    total: number;
    count: number;
  };
}

interface StockProduct {
  id: number;
  item_code: string;
  item_name: string;
}

export default function PartiesMasterPage() {
  const { token, isLoading: authLoading } = useStaffAuth();

  // Active Main Tab
  const [activeTab, setActiveTab] = useState("all");

  // Global Data Store
  const [companies, setCompanies] = useState<Company[]>([]);
  const [vendors, setVendors] = useState<Vendor[]>([]);
  const [partners, setPartners] = useState<Partner[]>([]);
  const [staffList, setStaffList] = useState<StaffMember[]>([]);
  const [ledgerParties, setLedgerParties] = useState<LedgerParty[]>([]);

  // Loading States
  const [loadingData, setLoadingData] = useState(false);
  const [ledgerLoading, setLedgerLoading] = useState(false);

  // Expense & Income Heads
  const [expMain, setExpMain] = useState<ExpenseMainCat[]>([]);
  const [expSub, setExpSub] = useState<ExpenseSubCat[]>([]);
  const [expAmounts, setExpAmounts] = useState<{ main: CategoryAmountSummary; sub: CategoryAmountSummary }>({
    main: {},
    sub: {},
  });
  const [expLoaded, setExpLoaded] = useState(false);
  const [expInnerTab, setExpInnerTab] = useState<"main" | "sub">("main");
  const [expFilterCo, setExpFilterCo] = useState("");
  const [expSort, setExpSort] = useState("name_asc");

  const [incMain, setIncMain] = useState<ExpenseMainCat[]>([]);
  const [incSub, setIncSub] = useState<ExpenseSubCat[]>([]);
  const [incAmounts, setIncAmounts] = useState<{ main: CategoryAmountSummary; sub: CategoryAmountSummary }>({
    main: {},
    sub: {},
  });
  const [incLoaded, setIncLoaded] = useState(false);
  const [incInnerTab, setIncInnerTab] = useState<"main" | "sub">("main");
  const [incFilterCo, setIncFilterCo] = useState("");
  const [incSort, setIncSort] = useState("name_asc");

  // Filters State
  const [allSearch, setAllSearch] = useState("");
  const [allTypeFilter, setAllTypeFilter] = useState("ALL");

  const [coSearch, setCoSearch] = useState("");
  const [coTypeFilter, setCoTypeFilter] = useState("ALL");

  const [vndSearch, setVndSearch] = useState("");
  const [vndTypeFilter, setVndTypeFilter] = useState("ALL");
  const [vndCompanyFilter, setVndCompanyFilter] = useState("ALL");
  const [vndStatusFilter, setVndStatusFilter] = useState("ALL");

  const [prtSearch, setPrtSearch] = useState("");
  const [prtCategoryFilter, setPrtCategoryFilter] = useState("ALL");
  const [prtStatusFilter, setPrtStatusFilter] = useState("ALL");

  const [stfSearch, setStfSearch] = useState("");
  const [stfStatusFilter, setStfStatusFilter] = useState("ALL");

  const [ldgSearch, setLdgSearch] = useState("");
  const [ldgTypeFilter, setLdgTypeFilter] = useState("ALL");
  const [ldgCompanyFilter, setLdgCompanyFilter] = useState("ALL");

  // ----------------------------------------------------
  // Modals & Forms State
  // ----------------------------------------------------
  // Company Modal
  const [isCoModalOpen, setIsCoModalOpen] = useState(false);
  const [coEditId, setCoEditId] = useState<number | null>(null);
  const [coForm, setCoForm] = useState<Partial<Company>>({
    company_type: "SUBSIDIARY",
    is_active: true,
  });
  const [coTransferSummary, setCoTransferSummary] = useState<Array<{ label: string; count: number }>>([]);
  const [coTransferTarget, setCoTransferTarget] = useState("");
  const [showCoTransfer, setShowCoTransfer] = useState(false);
  const [coSaving, setCoSaving] = useState(false);

  // Vendor Modal
  const [isVndModalOpen, setIsVndModalOpen] = useState(false);
  const [vndModalTab, setVndModalTab] = useState("basic");
  const [vndEditId, setVndEditId] = useState<number | null>(null);
  const [vndForm, setVndForm] = useState<Partial<Vendor>>({
    vendor_type: "BOTH",
    is_active: true,
    gst_type: "CGST_SGST",
    payment_terms: "COD",
    credit_limit: 0,
    credit_days: 0,
  });
  const [vndApplicableCos, setVndApplicableCos] = useState<number[]>([]);
  const [vndObRows, setVndObRows] = useState<OpeningBalanceRow[]>([]);
  const [vndSelectedProducts, setVndSelectedProducts] = useState<StockProduct[]>([]);
  const [vndProductSearchResults, setVndProductSearchResults] = useState<StockProduct[]>([]);
  const [vndProductSearchTerm, setVndProductSearchTerm] = useState("");
  const [vndSearchingProducts, setVndSearchingProducts] = useState(false);
  const [vndQrFile, setVndQrFile] = useState<File | null>(null);
  const [vndQrPreview, setVndQrPreview] = useState<string | null>(null);
  const [vndSaving, setVndSaving] = useState(false);
  const [vndHistLoading, setVndHistLoading] = useState(false);

  // Partner Modal
  const [isPrtModalOpen, setIsPrtModalOpen] = useState(false);
  const [prtModalTab, setPrtModalTab] = useState("basic");
  const [prtEditId, setPrtEditId] = useState<number | null>(null);
  const [prtForm, setPrtForm] = useState<Partial<Partner>>({
    category: "DEALER",
    is_active: true,
    payment_terms: "ADVANCE",
    credit_limit: 0,
    credit_days: 0,
  });
  const [prtObRows, setPrtObRows] = useState<OpeningBalanceRow[]>([]);
  const [prtSaving, setPrtSaving] = useState(false);

  // Ledger Add Entry Modal
  const [isLdgModalOpen, setIsLdgModalOpen] = useState(false);
  const [ldgForm, setLdgForm] = useState({
    company_id: "",
    transaction_date: new Date().toISOString().slice(0, 10),
    party_type: "CUSTOMER",
    party_name: "",
    entry_type: "DEBIT",
    amount: "",
    narration: "",
    reference_number: "",
  });
  const [ldgSaving, setLdgSaving] = useState(false);

  // Expense Main & Sub Modals
  const [isExpMainModalOpen, setIsExpMainModalOpen] = useState(false);
  const [expMainEditId, setExpMainEditId] = useState<number | null>(null);
  const [expMainForm, setExpMainForm] = useState({ name: "", description: "" });
  const [expMainSaving, setExpMainSaving] = useState(false);

  const [isExpSubModalOpen, setIsExpSubModalOpen] = useState(false);
  const [expSubEditId, setExpSubEditId] = useState<number | null>(null);
  const [expSubForm, setExpSubForm] = useState({ parent_id: "", name: "", description: "" });
  const [expSubSaving, setExpSubSaving] = useState(false);

  // Income Main & Sub Modals
  const [isIncMainModalOpen, setIsIncMainModalOpen] = useState(false);
  const [incMainEditId, setIncMainEditId] = useState<number | null>(null);
  const [incMainForm, setIncMainForm] = useState({ name: "", description: "" });
  const [incMainSaving, setIncMainSaving] = useState(false);

  const [isIncSubModalOpen, setIsIncSubModalOpen] = useState(false);
  const [incSubEditId, setIncSubEditId] = useState<number | null>(null);
  const [incSubForm, setIncSubForm] = useState({ parent_id: "", name: "", description: "" });
  const [incSubSaving, setIncSubSaving] = useState(false);

  // ----------------------------------------------------
  // Currency Formatter
  // ----------------------------------------------------
  const fmt = (n: number | string | undefined | null) => {
    const v = parseFloat(String(n || 0));
    if (isNaN(v) || v === 0) return "—";
    return "₹" + v.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  };

  const fmtShort = (n: number | string | undefined | null) => {
    const v = parseFloat(String(n || 0));
    if (isNaN(v) || v === 0) return "₹0";
    if (Math.abs(v) >= 100000) return "₹" + (v / 100000).toFixed(2) + "L";
    if (Math.abs(v) >= 1000) return "₹" + (v / 1000).toFixed(1) + "K";
    return "₹" + v.toLocaleString("en-IN", { maximumFractionDigits: 0 });
  };

  // ----------------------------------------------------
  // Data Loaders
  // ----------------------------------------------------
  const loadCompanies = useCallback(async () => {
    try {
      const res = await api.get("/staff/accounts/companies");
      const list = res.data?.companies || [];
      setCompanies(list);
      return list;
    } catch (err: any) {
      console.error("Failed to load companies", err);
      return [];
    }
  }, []);

  const loadVendors = useCallback(async () => {
    try {
      const res = await api.get("/staff/accounts/vendors?include_inactive=true&page_size=500");
      const list = res.data?.vendors || [];
      setVendors(list);
      return list;
    } catch (err: any) {
      console.error("Failed to load vendors", err);
      return [];
    }
  }, []);

  const loadPartners = useCallback(async () => {
    try {
      const res = await api.get("/staff/accounts/official-partners");
      const list = res.data?.partners || [];
      setPartners(list);
      return list;
    } catch (err: any) {
      console.error("Failed to load partners", err);
      return [];
    }
  }, []);

  const loadStaff = useCallback(async () => {
    try {
      const res = await api.get("/staff/accounts/staff-list");
      const list = res.data?.staff || [];
      setStaffList(list);
      return list;
    } catch (err: any) {
      console.error("Failed to load staff list", err);
      return [];
    }
  }, []);

  const loadLedgerData = useCallback(async (companyId?: string) => {
    setLedgerLoading(true);
    try {
      const cid = companyId !== undefined ? companyId : ldgCompanyFilter !== "ALL" ? ldgCompanyFilter : "";
      const params = cid ? `?company_id=${cid}` : "";
      const [rp, rb] = await Promise.all([
        api.get(`/staff/accounts/party-ledger/parties${params}`),
        api.get(`/staff/accounts/party-ledger/balances${params}`),
      ]);
      const pList: any[] = rp.data?.parties || [];
      const bList: any[] = rb.data?.balances || [];

      const balMap: Record<string, any> = {};
      bList.forEach((b) => {
        balMap[`${b.party_name}||${b.party_type}`] = b;
      });

      const merged: LedgerParty[] = pList.map((p) => {
        const key = `${p.party_name}||${p.party_type}`;
        const b = balMap[key] || {};
        return {
          party_name: p.party_name,
          party_type: p.party_type,
          party_id: p.party_id,
          display_name: p.display_name,
          total_debit: parseFloat(b.total_debit) || 0,
          total_credit: parseFloat(b.total_credit) || 0,
          balance: parseFloat(b.balance) || 0,
        };
      });

      setLedgerParties(merged);
    } catch (err) {
      console.error("Failed to load ledger data", err);
      setLedgerParties([]);
    } finally {
      setLedgerLoading(false);
    }
  }, [ldgCompanyFilter]);

  const loadAll = useCallback(async () => {
    setLoadingData(true);
    try {
      await Promise.all([
        loadCompanies(),
        loadVendors(),
        loadPartners(),
        loadStaff(),
        loadLedgerData(),
      ]);
    } finally {
      setLoadingData(false);
    }
  }, [loadCompanies, loadVendors, loadPartners, loadStaff, loadLedgerData]);

  useEffect(() => {
    if (token) {
      loadAll();
    }
  }, [token, loadAll]);

  // Load Expense Categories
  const loadExpenseCategories = useCallback(async (coId?: string) => {
    const cid = coId !== undefined ? coId : expFilterCo;
    const coParam = cid ? `?company_id=${cid}` : "";
    try {
      const [rList, rAmt] = await Promise.all([
        api.get("/expense-categories/list"),
        api.get(`/expense-categories/amounts-summary${coParam}`),
      ]);
      if (rList.data?.success) {
        setExpMain(rList.data.main_categories || []);
        setExpSub(rList.data.sub_categories || []);
      }
      if (rAmt.data?.success) {
        setExpAmounts({
          main: rAmt.data.main || {},
          sub: rAmt.data.sub || {},
        });
      }
      setExpLoaded(true);
    } catch (err) {
      console.error("Failed to load expense categories", err);
    }
  }, [expFilterCo]);

  // Load Income Categories
  const loadIncomeCategories = useCallback(async (coId?: string) => {
    const cid = coId !== undefined ? coId : incFilterCo;
    const coParam = cid ? `?company_id=${cid}` : "";
    try {
      const [rList, rAmt] = await Promise.all([
        api.get("/income-categories/list"),
        api.get(`/income-categories/amounts-summary${coParam}`),
      ]);
      if (rList.data?.success) {
        setIncMain(rList.data.main_categories || []);
        setIncSub(rList.data.sub_categories || []);
      }
      if (rAmt.data?.success) {
        setIncAmounts({
          main: rAmt.data.main || {},
          sub: rAmt.data.sub || {},
        });
      }
      setIncLoaded(true);
    } catch (err) {
      console.error("Failed to load income categories", err);
    }
  }, [incFilterCo]);

  // Lazy tab loader
  useEffect(() => {
    if (activeTab === "expense" && !expLoaded) {
      loadExpenseCategories();
    }
    if (activeTab === "income" && !incLoaded) {
      loadIncomeCategories();
    }
  }, [activeTab, expLoaded, incLoaded, loadExpenseCategories, loadIncomeCategories]);

  // ----------------------------------------------------
  // Combined Parties (for ALL tab)
  // ----------------------------------------------------
  const allCombined = useMemo(() => {
    const list: Array<{
      name: string;
      code: string;
      type: string;
      subType: string;
      contact: string;
      gstOrLocation: string;
      status: string;
    }> = [];

    companies.forEach((c) => {
      list.push({
        name: c.company_name,
        code: c.company_code || "",
        type: "COMPANY",
        subType: c.company_type || "",
        contact: c.phone || c.email || "",
        gstOrLocation: c.gst_number || [c.city, c.state].filter(Boolean).join(", "),
        status: c.is_active === false ? "Inactive" : "Active",
      });
    });

    vendors.forEach((v) => {
      list.push({
        name: v.vendor_name,
        code: v.vendor_code || "",
        type: "VENDOR",
        subType: v.vendor_type || "",
        contact: v.contact_person_1_phone || v.phone || "",
        gstOrLocation: v.gst_number || [v.city, v.state].filter(Boolean).join(", "),
        status: v.is_active === false ? "Inactive" : "Active",
      });
    });

    const catLabels: Record<string, string> = {
      DEALER: "Dealer",
      DISTRIBUTOR: "Distributor",
      SERVICE_CENTER: "Service Center",
      VENDOR: "Vendor",
      REAL_DREAM_PARTNER: "Real Dreams",
    };

    partners.forEach((p) => {
      list.push({
        name: p.name,
        code: p.code || "",
        type: "PARTNER",
        subType: catLabels[p.category] || p.category || "",
        contact: p.phone || p.email || "",
        gstOrLocation: p.gst || [p.city, p.state].filter(Boolean).join(", "),
        status: p.is_active ? "Active" : "Inactive",
      });
    });

    staffList.forEach((s) => {
      list.push({
        name: s.name,
        code: s.code || "",
        type: "STAFF",
        subType: s.role || "",
        contact: s.phone || "",
        gstOrLocation: s.department || "",
        status: (s.status || "Active").charAt(0).toUpperCase() + (s.status || "Active").slice(1),
      });
    });

    const seenNames = new Set(list.map((x) => (x.name || "").toLowerCase()));
    ledgerParties.forEach((lp) => {
      const key = (lp.party_name || "").toLowerCase();
      if (!seenNames.has(key)) {
        seenNames.add(key);
        list.push({
          name: lp.party_name,
          code: String(lp.party_id || ""),
          type: lp.party_type || "EXTERNAL",
          subType: "Ledger",
          contact: "",
          gstOrLocation: "",
          status: "Active",
        });
      }
    });

    return list;
  }, [companies, vendors, partners, staffList, ledgerParties]);

  // ----------------------------------------------------
  // Filtered Lists
  // ----------------------------------------------------
  const filteredAll = useMemo(() => {
    const s = allSearch.trim().toLowerCase();
    return allCombined.filter((p) => {
      const matchSearch =
        !s ||
        p.name.toLowerCase().includes(s) ||
        p.code.toLowerCase().includes(s) ||
        p.contact.toLowerCase().includes(s);
      const matchType = allTypeFilter === "ALL" || p.type === allTypeFilter;
      return matchSearch && matchType;
    });
  }, [allCombined, allSearch, allTypeFilter]);

  const filteredCompanies = useMemo(() => {
    const s = coSearch.trim().toLowerCase();
    return companies.filter((c) => {
      const matchSearch =
        !s ||
        (c.company_name || "").toLowerCase().includes(s) ||
        (c.company_code || "").toLowerCase().includes(s) ||
        (c.gst_number || "").toLowerCase().includes(s);
      const matchType = coTypeFilter === "ALL" || c.company_type === coTypeFilter;
      return matchSearch && matchType;
    });
  }, [companies, coSearch, coTypeFilter]);

  const filteredVendors = useMemo(() => {
    const s = vndSearch.trim().toLowerCase();
    return vendors.filter((v) => {
      const matchSearch =
        !s ||
        (v.vendor_name || "").toLowerCase().includes(s) ||
        (v.vendor_code || "").toLowerCase().includes(s) ||
        (v.gst_number || "").toLowerCase().includes(s);
      const matchType = vndTypeFilter === "ALL" || v.vendor_type === vndTypeFilter;
      const matchCompany =
        vndCompanyFilter === "ALL" ||
        (() => {
          const ac = v.applicable_companies || [];
          return ac.includes("ALL") || ac.includes(parseInt(vndCompanyFilter));
        })();
      const matchStatus =
        vndStatusFilter === "ALL" ||
        (vndStatusFilter === "active" ? v.is_active !== false : v.is_active === false);
      return matchSearch && matchType && matchCompany && matchStatus;
    });
  }, [vendors, vndSearch, vndTypeFilter, vndCompanyFilter, vndStatusFilter]);

  const filteredPartners = useMemo(() => {
    const s = prtSearch.trim().toLowerCase();
    return partners.filter((p) => {
      const matchSearch =
        !s ||
        (p.name || "").toLowerCase().includes(s) ||
        (p.code || "").toLowerCase().includes(s) ||
        (p.phone || "").includes(s);
      const matchCat = prtCategoryFilter === "ALL" || p.category === prtCategoryFilter;
      const matchStatus =
        prtStatusFilter === "ALL" ||
        (prtStatusFilter === "active" ? p.is_active : !p.is_active);
      return matchSearch && matchCat && matchStatus;
    });
  }, [partners, prtSearch, prtCategoryFilter, prtStatusFilter]);

  const filteredStaff = useMemo(() => {
    const s = stfSearch.trim().toLowerCase();
    return staffList.filter((stf) => {
      const matchSearch =
        !s ||
        (stf.name || "").toLowerCase().includes(s) ||
        (stf.code || "").toLowerCase().includes(s) ||
        (stf.phone || "").includes(s);
      const matchStatus =
        stfStatusFilter === "ALL" || (stf.status || "").toLowerCase() === stfStatusFilter.toLowerCase();
      return matchSearch && matchStatus;
    });
  }, [staffList, stfSearch, stfStatusFilter]);

  const filteredLedger = useMemo(() => {
    const s = ldgSearch.trim().toLowerCase();
    return ledgerParties.filter((p) => {
      const matchSearch =
        !s ||
        (p.party_name || "").toLowerCase().includes(s) ||
        (p.display_name || "").toLowerCase().includes(s);
      const matchType = ldgTypeFilter === "ALL" || p.party_type === ldgTypeFilter;
      return matchSearch && matchType;
    });
  }, [ledgerParties, ldgSearch, ldgTypeFilter]);

  // ----------------------------------------------------
  // Stats Calculations
  // ----------------------------------------------------
  const coStats = useMemo(() => {
    const total = companies.length;
    const active = companies.filter((c) => c.is_active !== false).length;
    const inactive = total - active;
    return { total, active, inactive };
  }, [companies]);

  const vndStats = useMemo(() => {
    const total = vendors.length;
    const active = vendors.filter((v) => v.is_active !== false).length;
    const inactive = total - active;
    const both = vendors.filter((v) => v.vendor_type === "BOTH").length;
    return { total, active, inactive, both };
  }, [vendors]);

  const prtStats = useMemo(() => {
    const total = partners.length;
    const active = partners.filter((p) => p.is_active).length;
    const dealer = partners.filter((p) => p.category === "DEALER").length;
    const distributor = partners.filter((p) => p.category === "DISTRIBUTOR").length;
    const svc = partners.filter((p) => p.category === "SERVICE_CENTER").length;
    return { total, active, dealer, distributor, svc };
  }, [partners]);

  const stfStats = useMemo(() => {
    const total = staffList.length;
    const active = staffList.filter((s) => s.status === "active").length;
    const resigned = staffList.filter((s) => s.status === "resigned").length;
    const inactive = staffList.filter((s) => s.status !== "active" && s.status !== "resigned").length;
    return { total, active, resigned, inactive };
  }, [staffList]);

  const ldgStats = useMemo(() => {
    const total = ledgerParties.length;
    const totalDR = ledgerParties.reduce((a, p) => a + p.total_debit, 0);
    const totalCR = ledgerParties.reduce((a, p) => a + p.total_credit, 0);
    const net = totalDR - totalCR;
    return { total, totalDR, totalCR, net };
  }, [ledgerParties]);

  const expStats = useMemo(() => {
    const totalAmt = Object.values(expAmounts.main).reduce((s, v) => s + (v.total || 0), 0);
    const totalEnt = Object.values(expAmounts.main).reduce((s, v) => s + (v.count || 0), 0);
    return {
      main: expMain.length,
      sub: expSub.length,
      totalAmt,
      totalEnt,
    };
  }, [expMain, expSub, expAmounts]);

  const incStats = useMemo(() => {
    const totalAmt = Object.values(incAmounts.main).reduce((s, v) => s + (v.total || 0), 0);
    const totalEnt = Object.values(incAmounts.main).reduce((s, v) => s + (v.count || 0), 0);
    return {
      main: incMain.length,
      sub: incSub.length,
      totalAmt,
      totalEnt,
    };
  }, [incMain, incSub, incAmounts]);

  // Sort helpers for categories
  const sortedExpMain = useMemo(() => {
    const a2n = (id: number) => expAmounts.main[String(id)]?.total || 0;
    const a2c = (id: number) => expAmounts.main[String(id)]?.count || 0;
    const copy = [...expMain];
    if (expSort === "name_asc") copy.sort((a, b) => a.name.localeCompare(b.name));
    else if (expSort === "name_desc") copy.sort((a, b) => b.name.localeCompare(a.name));
    else if (expSort === "amt_desc") copy.sort((a, b) => a2n(b.id) - a2n(a.id));
    else if (expSort === "amt_asc") copy.sort((a, b) => a2n(a.id) - a2n(b.id));
    else if (expSort === "cnt_desc") copy.sort((a, b) => a2c(b.id) - a2c(a.id));
    else if (expSort === "cnt_asc") copy.sort((a, b) => a2c(a.id) - a2c(b.id));
    return copy;
  }, [expMain, expSort, expAmounts]);

  const sortedExpSub = useMemo(() => {
    const a2n = (id: number) => expAmounts.sub[String(id)]?.total || 0;
    const a2c = (id: number) => expAmounts.sub[String(id)]?.count || 0;
    const copy = [...expSub];
    if (expSort === "name_asc") copy.sort((a, b) => a.name.localeCompare(b.name));
    else if (expSort === "name_desc") copy.sort((a, b) => b.name.localeCompare(a.name));
    else if (expSort === "amt_desc") copy.sort((a, b) => a2n(b.id) - a2n(a.id));
    else if (expSort === "amt_asc") copy.sort((a, b) => a2n(a.id) - a2n(b.id));
    else if (expSort === "cnt_desc") copy.sort((a, b) => a2c(b.id) - a2c(a.id));
    else if (expSort === "cnt_asc") copy.sort((a, b) => a2c(a.id) - a2c(b.id));
    return copy;
  }, [expSub, expSort, expAmounts]);

  const sortedIncMain = useMemo(() => {
    const a2n = (id: number) => incAmounts.main[String(id)]?.total || 0;
    const a2c = (id: number) => incAmounts.main[String(id)]?.count || 0;
    const copy = [...incMain];
    if (incSort === "name_asc") copy.sort((a, b) => a.name.localeCompare(b.name));
    else if (incSort === "name_desc") copy.sort((a, b) => b.name.localeCompare(a.name));
    else if (incSort === "amt_desc") copy.sort((a, b) => a2n(b.id) - a2n(a.id));
    else if (incSort === "amt_asc") copy.sort((a, b) => a2n(a.id) - a2n(b.id));
    else if (incSort === "cnt_desc") copy.sort((a, b) => a2c(b.id) - a2c(a.id));
    else if (incSort === "cnt_asc") copy.sort((a, b) => a2c(a.id) - a2c(b.id));
    return copy;
  }, [incMain, incSort, incAmounts]);

  const sortedIncSub = useMemo(() => {
    const a2n = (id: number) => incAmounts.sub[String(id)]?.total || 0;
    const a2c = (id: number) => incAmounts.sub[String(id)]?.count || 0;
    const copy = [...incSub];
    if (incSort === "name_asc") copy.sort((a, b) => a.name.localeCompare(b.name));
    else if (incSort === "name_desc") copy.sort((a, b) => b.name.localeCompare(a.name));
    else if (incSort === "amt_desc") copy.sort((a, b) => a2n(b.id) - a2n(a.id));
    else if (incSort === "amt_asc") copy.sort((a, b) => a2n(a.id) - a2n(b.id));
    else if (incSort === "cnt_desc") copy.sort((a, b) => a2c(b.id) - a2c(a.id));
    else if (incSort === "cnt_asc") copy.sort((a, b) => a2c(a.id) - a2c(b.id));
    return copy;
  }, [incSub, incSort, incAmounts]);

  // ----------------------------------------------------
  // Type Badge Styling Helper
  // ----------------------------------------------------
  const getTypeBadge = (type: string, sub?: string) => {
    const t = type.toUpperCase();
    let bg = "bg-slate-100 text-slate-700 border-slate-200";
    if (t === "COMPANY") bg = "bg-purple-100 text-purple-800 border-purple-200";
    else if (t === "VENDOR") bg = "bg-amber-100 text-amber-800 border-amber-200";
    else if (t === "PARTNER" || t === "DEALER") bg = "bg-blue-100 text-blue-800 border-blue-200";
    else if (t === "STAFF" || t === "EMPLOYEE") bg = "bg-sky-100 text-sky-800 border-sky-200";
    else if (t === "CUSTOMER") bg = "bg-emerald-100 text-emerald-800 border-emerald-200";
    else if (t === "DISTRIBUTOR") bg = "bg-cyan-100 text-cyan-800 border-cyan-200";
    else if (t === "SERVICE_CENTER") bg = "bg-pink-100 text-pink-800 border-pink-200";
    else if (t === "REAL_DREAM_PARTNER") bg = "bg-fuchsia-100 text-fuchsia-800 border-fuchsia-200";

    return (
      <span className="inline-flex items-center gap-1.5">
        <Badge variant="outline" className={`font-semibold text-xs px-2.5 py-0.5 ${bg}`}>
          {t}
        </Badge>
        {sub && <span className="text-xs text-muted-foreground font-medium">({sub})</span>}
      </span>
    );
  };

  // ----------------------------------------------------
  // Company CRUD & Transfer Actions
  // ----------------------------------------------------
  const openCoModal = (co?: Company) => {
    setShowCoTransfer(false);
    setCoTransferSummary([]);
    setCoTransferTarget("");
    if (co) {
      setCoEditId(co.id);
      setCoForm({ ...co, is_active: co.is_active !== false });
    } else {
      setCoEditId(null);
      setCoForm({
        company_type: "SUBSIDIARY",
        is_active: true,
        is_marketplace_endpoint: false,
      });
    }
    setIsCoModalOpen(true);
  };

  const saveCompany = async () => {
    if (!coForm.company_name?.trim()) {
      toast.error("Company Name is required");
      return;
    }
    setCoSaving(true);
    try {
      const isEdit = !!coEditId;
      const payload: any = {
        company_name: coForm.company_name.trim(),
        company_type: coForm.company_type || "SUBSIDIARY",
        is_active: coForm.is_active !== false,
        address: coForm.address?.trim() || null,
        city: coForm.city?.trim() || null,
        state: coForm.state?.trim() || null,
        pincode: coForm.pincode?.trim() || null,
        gst_number: coForm.gst_number?.trim().toUpperCase() || null,
        pan_number: coForm.pan_number?.trim().toUpperCase() || null,
        cin_number: coForm.cin_number?.trim() || null,
        phone: coForm.phone?.trim() || null,
        email: coForm.email?.trim() || null,
        website: coForm.website?.trim() || null,
        is_marketplace_endpoint: !!coForm.is_marketplace_endpoint,
      };
      if (!isEdit && coForm.company_code) {
        payload.company_code = coForm.company_code.trim().toUpperCase();
      }

      if (isEdit) {
        await api.put(`/staff/accounts/companies/${coEditId}`, payload);
        toast.success("Company updated successfully");
      } else {
        await api.post("/staff/accounts/companies", payload);
        toast.success("Company created successfully");
      }
      setIsCoModalOpen(false);
      await loadCompanies();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || err.message || "Failed to save company");
    } finally {
      setCoSaving(false);
    }
  };

  const checkDeleteCompany = async () => {
    if (!coEditId) return;
    try {
      const res = await api.get(`/staff/accounts/companies/${coEditId}/transfer-summary`);
      const summary = res.data?.summary || [];
      if (summary.length > 0) {
        setCoTransferSummary(summary);
        setShowCoTransfer(true);
      } else {
        if (confirm("This company has no linked records. Are you sure you want to delete it?")) {
          await api.delete(`/staff/accounts/companies/${coEditId}`);
          toast.success("Company deleted");
          setIsCoModalOpen(false);
          await loadCompanies();
        }
      }
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Failed to check transfer summary");
    }
  };

  const doTransferAndDelete = async () => {
    if (!coEditId || !coTransferTarget) {
      toast.error("Please select a target company");
      return;
    }
    setCoSaving(true);
    try {
      const res = await api.post(
        `/staff/accounts/companies/${coEditId}/transfer-to/${coTransferTarget}`
      );
      toast.success(res.data?.message || "Data transferred and company deactivated successfully");
      setIsCoModalOpen(false);
      await loadCompanies();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Failed to transfer data");
    } finally {
      setCoSaving(false);
    }
  };

  // ----------------------------------------------------
  // Vendor CRUD & Product Search
  // ----------------------------------------------------
  const openVndModal = async (vnd?: Vendor) => {
    setVndModalTab("basic");
    setVndQrFile(null);
    setVndQrPreview(null);
    setVndProductSearchTerm("");
    setVndProductSearchResults([]);

    if (vnd) {
      setVndEditId(vnd.id);
      setVndForm({
        ...vnd,
        is_active: vnd.is_active !== false,
      });
      setVndQrPreview(vnd.payment_scanner_path || null);

      const cos = Array.isArray(vnd.applicable_companies)
        ? (vnd.applicable_companies.filter((x) => typeof x === "number") as number[])
        : [];
      setVndApplicableCos(cos);

      // Fetch detailed vendor for OB and Products
      try {
        const [vDetail, vProducts] = await Promise.all([
          api.get(`/staff/accounts/vendors/${vnd.id}`),
          api.get(`/staff/accounts/vendors/${vnd.id}/products`),
        ]);
        const fullVnd = vDetail.data?.vendor || {};
        const obList: any[] = fullVnd.opening_balances || [];
        setVndObRows(
          obList
            .map((r) => ({
              company_id: r.company_id || null,
              amount: parseFloat(r.amount ?? r.opening_balance) || 0,
              type: r.type || r.opening_balance_type || "CREDIT",
              date: r.date || r.opening_balance_date || null,
            }))
            .filter((r) => r.amount > 0)
        );

        const prods: any[] = vProducts.data?.products || [];
        setVndSelectedProducts(
          prods.map((p) => ({
            id: p.item_id,
            item_code: p.item_code || `ITEM${p.item_id}`,
            item_name: p.item_name || `Product ${p.item_id}`,
          }))
        );
      } catch (e) {
        console.warn("Could not load vendor sub-details", e);
      }
    } else {
      setVndEditId(null);
      setVndForm({
        vendor_type: "BOTH",
        is_active: true,
        gst_type: "CGST_SGST",
        payment_terms: "COD",
        credit_limit: 0,
        credit_days: 0,
      });
      setVndApplicableCos([]);
      setVndObRows([]);
      setVndSelectedProducts([]);
    }
    setIsVndModalOpen(true);
  };

  const handlePincodeLookup = async (pin: string, isShipping = false) => {
    if (!pin || pin.length !== 6) return;
    try {
      const res = await api.get(`/staff/accounts/pincode/${pin}`);
      if (res.data?.success) {
        if (isShipping) {
          setVndForm((prev) => ({
            ...prev,
            ship_to_city: res.data.city || prev.ship_to_city,
            ship_to_state: res.data.state || prev.ship_to_state,
          }));
        } else {
          setVndForm((prev) => ({
            ...prev,
            city: res.data.city || prev.city,
            state: res.data.state || prev.state,
          }));
        }
        toast.success(`Location detected: ${res.data.city || ""}, ${res.data.state || ""}`);
      }
    } catch {
      // silent
    }
  };

  const searchVndProducts = async (term: string) => {
    setVndProductSearchTerm(term);
    if (!term || term.length < 2) {
      setVndProductSearchResults([]);
      return;
    }
    setVndSearchingProducts(true);
    try {
      const res = await api.get(
        `/staff/accounts/stock-items?search=${encodeURIComponent(term)}&page_size=30`
      );
      setVndProductSearchResults(res.data?.stock_items || []);
    } catch {
      setVndProductSearchResults([]);
    } finally {
      setVndSearchingProducts(false);
    }
  };

  const toggleVndProduct = (prod: StockProduct) => {
    setVndSelectedProducts((prev) => {
      const exists = prev.some((p) => p.id === prod.id);
      if (exists) {
        return prev.filter((p) => p.id !== prod.id);
      } else {
        return [...prev, prod];
      }
    });
  };

  const loadVndPurchaseHistory = async () => {
    if (!vndEditId) return;
    setVndHistLoading(true);
    try {
      const res = await api.get(`/staff/accounts/vendors/${vndEditId}/purchase-history-products`);
      const prods: any[] = res.data?.products || [];
      if (!prods.length) {
        toast("No previous purchase history found for this vendor", { icon: "ℹ️" });
        return;
      }
      let added = 0;
      setVndSelectedProducts((prev) => {
        const copy = [...prev];
        prods.forEach((p) => {
          if (!copy.some((x) => x.id === p.item_id)) {
            copy.push({
              id: p.item_id,
              item_code: p.item_code || `ITEM${p.item_id}`,
              item_name: p.item_name || `Product ${p.item_id}`,
            });
            added++;
          }
        });
        return copy;
      });
      toast.success(`Loaded ${added} product(s) from purchase history`);
    } catch (e: any) {
      toast.error(e.response?.data?.detail || "Failed to load purchase history");
    } finally {
      setVndHistLoading(false);
    }
  };

  const saveVendor = async () => {
    if (!vndForm.vendor_name?.trim()) {
      toast.error("Vendor Name is required");
      return;
    }
    if (!vndEditId && !vndForm.vendor_code?.trim()) {
      toast.error("Vendor Code is required for new vendors");
      return;
    }
    setVndSaving(true);
    try {
      const payload: any = {
        vendor_name: vndForm.vendor_name.trim(),
        vendor_type: vndForm.vendor_type || "BOTH",
        is_active: vndForm.is_active !== false,
        email: vndForm.email?.trim().toLowerCase() || null,
        gst_number: vndForm.gst_number?.trim().toUpperCase() || null,
        pan_number: vndForm.pan_number?.trim().toUpperCase() || null,
        gst_type: vndForm.gst_type || "CGST_SGST",
        trade_name: vndForm.trade_name?.trim() || null,
        contact_person: vndForm.contact_person_1_name?.trim() || null,
        contact_person_1_name: vndForm.contact_person_1_name?.trim() || null,
        contact_person_1_phone: vndForm.contact_person_1_phone?.trim() || null,
        contact_person_1_designation: vndForm.contact_person_1_designation?.trim() || null,
        contact_person_2_name: vndForm.contact_person_2_name?.trim() || null,
        contact_person_2_phone: vndForm.contact_person_2_phone?.trim() || null,
        contact_person_2_designation: vndForm.contact_person_2_designation?.trim() || null,
        website_url: vndForm.website_url?.trim() || null,
        address: vndForm.address?.trim() || null,
        pincode: vndForm.pincode?.trim() || null,
        city: vndForm.city?.trim() || null,
        state: vndForm.state?.trim() || null,
        map_link_1_label: vndForm.map_link_1_label?.trim() || "Office",
        map_link_1: vndForm.map_link_1?.trim() || null,
        map_link_2_label: vndForm.map_link_2_label?.trim() || "Warehouse",
        map_link_2: vndForm.map_link_2?.trim() || null,
        ship_to_address: vndForm.ship_to_address?.trim() || null,
        ship_to_pincode: vndForm.ship_to_pincode?.trim() || null,
        ship_to_city: vndForm.ship_to_city?.trim() || null,
        ship_to_state: vndForm.ship_to_state?.trim() || null,
        bank_name: vndForm.bank_name?.trim() || null,
        bank_branch: vndForm.bank_branch?.trim() || null,
        account_number: vndForm.account_number?.trim() || null,
        ifsc_code: vndForm.ifsc_code?.trim().toUpperCase() || null,
        account_holder_name: vndForm.account_holder_name?.trim() || null,
        upi_id: vndForm.upi_id?.trim() || null,
        payment_terms: vndForm.payment_terms || "COD",
        credit_limit: parseFloat(String(vndForm.credit_limit || 0)) || 0,
        credit_days: parseInt(String(vndForm.credit_days || 0)) || 0,
        terms_conditions: vndForm.terms_conditions?.trim() || null,
        applicable_companies: vndApplicableCos,
        product_ids: vndSelectedProducts.map((p) => p.id),
        opening_balances: vndObRows.filter((r) => r.amount > 0),
      };
      if (!vndEditId && vndForm.vendor_code) {
        payload.vendor_code = vndForm.vendor_code.trim().toUpperCase();
      }

      let savedId = vndEditId;
      if (vndEditId) {
        await api.put(`/staff/accounts/vendors/${vndEditId}`, payload);
        toast.success("Vendor updated successfully");
      } else {
        const res = await api.post("/staff/accounts/vendors", payload);
        savedId = res.data?.vendor?.id || res.data?.id;
        toast.success("Vendor created successfully");
      }

      // Upload QR file if selected
      if (vndQrFile && savedId) {
        const fd = new FormData();
        fd.append("file", vndQrFile);
        await api.post(`/staff/accounts/vendors/${savedId}/scanner`, fd, {
          headers: { "Content-Type": "multipart/form-data" },
        });
      }

      // Sync Products
      if (savedId) {
        await api.post(`/staff/accounts/vendors/${savedId}/products`, {
          product_ids: vndSelectedProducts.map((p) => p.id),
        });
      }

      setIsVndModalOpen(false);
      await loadVendors();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || err.message || "Failed to save vendor");
    } finally {
      setVndSaving(false);
    }
  };

  const deactivateVendor = async () => {
    if (!vndEditId) return;
    if (!confirm("Are you sure you want to deactivate this vendor?")) return;
    try {
      await api.delete(`/staff/accounts/vendors/${vndEditId}`);
      toast.success("Vendor deactivated");
      setIsVndModalOpen(false);
      await loadVendors();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Failed to deactivate vendor");
    }
  };

  // ----------------------------------------------------
  // Partner CRUD
  // ----------------------------------------------------
  const openPrtModal = (prt?: Partner) => {
    setPrtModalTab("basic");
    if (prt) {
      setPrtEditId(prt.id);
      setPrtForm({
        ...prt,
        is_active: prt.is_active !== false,
      });
      if (prt.opening_balance && prt.opening_balance > 0) {
        setPrtObRows([
          {
            company_id: null,
            amount: prt.opening_balance,
            type: (prt.opening_balance_type as any) || "CREDIT",
            date: prt.opening_balance_date || null,
          },
        ]);
      } else {
        setPrtObRows([]);
      }
    } else {
      setPrtEditId(null);
      setPrtForm({
        category: "DEALER",
        is_active: true,
        payment_terms: "ADVANCE",
        credit_limit: 0,
        credit_days: 0,
      });
      setPrtObRows([]);
    }
    setIsPrtModalOpen(true);
  };

  const savePartner = async () => {
    if (!prtForm.name?.trim()) {
      toast.error("Partner Name is required");
      return;
    }
    setPrtSaving(true);
    try {
      const payload: any = {
        partner_name: prtForm.name.trim(),
        partner_code: prtForm.code?.trim().toUpperCase() || undefined,
        category: prtForm.category || "DEALER",
        is_active: prtForm.is_active !== false,
        gst_number: prtForm.gst?.trim().toUpperCase() || null,
        pan_number: prtForm.pan?.trim().toUpperCase() || null,
        phone: prtForm.phone?.trim() || null,
        email: prtForm.email?.trim() || null,
        whatsapp_number: prtForm.whatsapp_number?.trim() || null,
        contact_person: prtForm.contact_person_1_name?.trim() || null,
        contact_person_1_name: prtForm.contact_person_1_name?.trim() || null,
        contact_person_1_phone: prtForm.phone?.trim() || null,
        contact_person_1_designation: prtForm.contact_person_1_designation?.trim() || null,
        contact_person_2_name: prtForm.contact_person_2_name?.trim() || null,
        contact_person_2_phone: prtForm.contact_person_2_phone?.trim() || null,
        address: prtForm.address?.trim() || null,
        city: prtForm.city?.trim() || null,
        state: prtForm.state?.trim() || null,
        pincode: prtForm.pincode?.trim() || null,
        zone: prtForm.zone?.trim() || null,
        bank_name: prtForm.bank_name?.trim() || null,
        bank_branch: prtForm.bank_branch?.trim() || null,
        account_number: prtForm.account_number?.trim() || null,
        ifsc_code: prtForm.ifsc_code?.trim().toUpperCase() || null,
        payment_terms: prtForm.payment_terms || "ADVANCE",
        credit_limit: parseFloat(String(prtForm.credit_limit || 0)) || 0,
        credit_days: parseInt(String(prtForm.credit_days || 0)) || 0,
        opening_balances: prtObRows.filter((r) => r.amount > 0),
      };

      if (prtEditId) {
        await api.put(`/staff/accounts/official-partners/${prtEditId}`, payload);
        toast.success("Partner updated successfully");
      } else {
        await api.post("/staff/accounts/official-partners", payload);
        toast.success("Partner created successfully");
      }
      setIsPrtModalOpen(false);
      await loadPartners();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || err.message || "Failed to save partner");
    } finally {
      setPrtSaving(false);
    }
  };

  const deactivatePartner = async () => {
    if (!prtEditId) return;
    if (!confirm("Are you sure you want to deactivate this partner?")) return;
    try {
      await api.delete(`/staff/accounts/official-partners/${prtEditId}`);
      toast.success("Partner deactivated");
      setIsPrtModalOpen(false);
      await loadPartners();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Failed to deactivate partner");
    }
  };

  // ----------------------------------------------------
  // Ledger Entry Actions
  // ----------------------------------------------------
  const openAddLedgerModal = () => {
    setLdgForm({
      company_id: ldgCompanyFilter !== "ALL" ? ldgCompanyFilter : "",
      transaction_date: new Date().toISOString().slice(0, 10),
      party_type: "CUSTOMER",
      party_name: "",
      entry_type: "DEBIT",
      amount: "",
      narration: "",
      reference_number: "",
    });
    setIsLdgModalOpen(true);
  };

  const saveLedgerEntry = async () => {
    if (!ldgForm.company_id) {
      toast.error("Please select a company");
      return;
    }
    if (!ldgForm.party_name.trim()) {
      toast.error("Party Name is required");
      return;
    }
    const amt = parseFloat(ldgForm.amount);
    if (isNaN(amt) || amt <= 0) {
      toast.error("Please enter a valid amount");
      return;
    }
    setLdgSaving(true);
    try {
      await api.post("/staff/accounts/party-ledger", {
        company_id: parseInt(ldgForm.company_id),
        party_type: ldgForm.party_type,
        party_name: ldgForm.party_name.trim(),
        entry_type: ldgForm.entry_type,
        amount: amt,
        narration: ldgForm.narration.trim() || null,
        reference_number: ldgForm.reference_number.trim() || null,
        transaction_date: ldgForm.transaction_date,
      });
      toast.success("Journal entry posted successfully");
      setIsLdgModalOpen(false);
      await loadLedgerData();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Failed to post entry");
    } finally {
      setLdgSaving(false);
    }
  };

  // ----------------------------------------------------
  // Expense & Income Category Handlers
  // ----------------------------------------------------
  const saveExpMainCat = async () => {
    if (!expMainForm.name.trim()) {
      toast.error("Category name is required");
      return;
    }
    setExpMainSaving(true);
    try {
      const url = expMainEditId
        ? `/expense-categories/main/update/${expMainEditId}`
        : "/expense-categories/main/create";
      const res = await api.post(url, {
        name: expMainForm.name.trim(),
        description: expMainForm.description.trim() || null,
      });
      if (res.data?.success) {
        toast.success(expMainEditId ? "Category updated" : "Category created");
        setIsExpMainModalOpen(false);
        await loadExpenseCategories();
      } else {
        toast.error(res.data?.message || "Failed to save category");
      }
    } catch (e: any) {
      toast.error(e.response?.data?.detail || "Error saving category");
    } finally {
      setExpMainSaving(false);
    }
  };

  const deleteExpMainCat = async (id: number) => {
    if (!confirm("Are you sure you want to delete this expense category?")) return;
    try {
      const res = await api.delete(`/expense-categories/main/${id}`);
      if (res.data?.success) {
        toast.success("Category deleted");
        await loadExpenseCategories();
      } else {
        toast.error(res.data?.message || "Failed to delete");
      }
    } catch (e: any) {
      toast.error(e.response?.data?.detail || "Delete error");
    }
  };

  const saveExpSubCat = async () => {
    if (!expSubForm.parent_id) {
      toast.error("Please select a main category");
      return;
    }
    if (!expSubForm.name.trim()) {
      toast.error("Sub category name is required");
      return;
    }
    setExpSubSaving(true);
    try {
      const url = expSubEditId
        ? `/expense-categories/sub/update/${expSubEditId}`
        : "/expense-categories/sub/create";
      const payload: any = {
        name: expSubForm.name.trim(),
        description: expSubForm.description.trim() || null,
      };
      if (!expSubEditId) {
        payload.parent_id = parseInt(expSubForm.parent_id);
      }
      const res = await api.post(url, payload);
      if (res.data?.success) {
        toast.success(expSubEditId ? "Sub category updated" : "Sub category created");
        setIsExpSubModalOpen(false);
        await loadExpenseCategories();
      } else {
        toast.error(res.data?.message || "Failed to save sub category");
      }
    } catch (e: any) {
      toast.error(e.response?.data?.detail || "Error saving sub category");
    } finally {
      setExpSubSaving(false);
    }
  };

  const deleteExpSubCat = async (id: number) => {
    if (!confirm("Are you sure you want to delete this sub category?")) return;
    try {
      const res = await api.delete(`/expense-categories/sub/${id}`);
      if (res.data?.success) {
        toast.success("Sub category deleted");
        await loadExpenseCategories();
      } else {
        toast.error(res.data?.message || "Failed to delete");
      }
    } catch (e: any) {
      toast.error(e.response?.data?.detail || "Delete error");
    }
  };

  // Income Category Handlers
  const saveIncMainCat = async () => {
    if (!incMainForm.name.trim()) {
      toast.error("Category name is required");
      return;
    }
    setIncMainSaving(true);
    try {
      const url = incMainEditId
        ? `/income-categories/main/update/${incMainEditId}`
        : "/income-categories/main/create";
      const res = await api.post(url, {
        name: incMainForm.name.trim(),
        description: incMainForm.description.trim() || null,
      });
      if (res.data?.success) {
        toast.success(incMainEditId ? "Income category updated" : "Income category created");
        setIsIncMainModalOpen(false);
        await loadIncomeCategories();
      } else {
        toast.error(res.data?.message || "Failed to save category");
      }
    } catch (e: any) {
      toast.error(e.response?.data?.detail || "Error saving category");
    } finally {
      setIncMainSaving(false);
    }
  };

  const deleteIncMainCat = async (id: number) => {
    if (!confirm("Are you sure you want to delete this income category?")) return;
    try {
      const res = await api.delete(`/income-categories/main/${id}`);
      if (res.data?.success) {
        toast.success("Category deleted");
        await loadIncomeCategories();
      } else {
        toast.error(res.data?.message || "Failed to delete");
      }
    } catch (e: any) {
      toast.error(e.response?.data?.detail || "Delete error");
    }
  };

  const saveIncSubCat = async () => {
    if (!incSubForm.parent_id) {
      toast.error("Please select a main category");
      return;
    }
    if (!incSubForm.name.trim()) {
      toast.error("Sub category name is required");
      return;
    }
    setIncSubSaving(true);
    try {
      const url = incSubEditId
        ? `/income-categories/sub/update/${incSubEditId}`
        : "/income-categories/sub/create";
      const payload: any = {
        name: incSubForm.name.trim(),
        description: incSubForm.description.trim() || null,
      };
      if (!incSubEditId) {
        payload.parent_id = parseInt(incSubForm.parent_id);
      }
      const res = await api.post(url, payload);
      if (res.data?.success) {
        toast.success(incSubEditId ? "Sub category updated" : "Sub category created");
        setIsIncSubModalOpen(false);
        await loadIncomeCategories();
      } else {
        toast.error(res.data?.message || "Failed to save sub category");
      }
    } catch (e: any) {
      toast.error(e.response?.data?.detail || "Error saving sub category");
    } finally {
      setIncSubSaving(false);
    }
  };

  const deleteIncSubCat = async (id: number) => {
    if (!confirm("Are you sure you want to delete this sub category?")) return;
    try {
      const res = await api.delete(`/income-categories/sub/${id}`);
      if (res.data?.success) {
        toast.success("Sub category deleted");
        await loadIncomeCategories();
      } else {
        toast.error(res.data?.message || "Failed to delete");
      }
    } catch (e: any) {
      toast.error(e.response?.data?.detail || "Delete error");
    }
  };

  if (authLoading) {
    return (
      <div className="flex h-[70vh] items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-amber-500" />
      </div>
    );
  }

  return (
    <div className="p-4 md:p-6 lg:p-8 max-w-7xl mx-auto space-y-6 animate-in fade-in duration-300">
      <Toaster position="top-right" />

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-gray-900 flex items-center gap-2.5">
            <span className="p-2 rounded-lg bg-amber-100 text-amber-600">
              <Users className="w-6 h-6" />
            </span>
            Parties Master
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            All business entities — associated companies, vendors, partners, staff, ledger parties, and financial heads in one unified hub.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => loadAll()}
            disabled={loadingData}
            className="gap-1.5"
          >
            <RotateCcw className={`w-3.5 h-3.5 ${loadingData ? "animate-spin" : ""}`} />
            Refresh
          </Button>
        </div>
      </div>

      {/* Global Stat Cards Banner */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
        <Card className="border-l-4 border-l-blue-500 shadow-sm">
          <CardContent className="p-3.5 flex items-center gap-3">
            <div className="p-2.5 rounded-lg bg-blue-50 text-blue-600">
              <Layers className="w-5 h-5" />
            </div>
            <div>
              <div className="text-xl font-extrabold text-gray-900">{allCombined.length}</div>
              <div className="text-[11px] font-semibold text-gray-500 uppercase tracking-wider">Total Parties</div>
            </div>
          </CardContent>
        </Card>

        <Card className="border-l-4 border-l-purple-500 shadow-sm">
          <CardContent className="p-3.5 flex items-center gap-3">
            <div className="p-2.5 rounded-lg bg-purple-50 text-purple-600">
              <Building2 className="w-5 h-5" />
            </div>
            <div>
              <div className="text-xl font-extrabold text-gray-900">{companies.length}</div>
              <div className="text-[11px] font-semibold text-gray-500 uppercase tracking-wider">Companies</div>
            </div>
          </CardContent>
        </Card>

        <Card className="border-l-4 border-l-amber-500 shadow-sm">
          <CardContent className="p-3.5 flex items-center gap-3">
            <div className="p-2.5 rounded-lg bg-amber-50 text-amber-600">
              <Truck className="w-5 h-5" />
            </div>
            <div>
              <div className="text-xl font-extrabold text-gray-900">{vendors.length}</div>
              <div className="text-[11px] font-semibold text-gray-500 uppercase tracking-wider">Vendors</div>
            </div>
          </CardContent>
        </Card>

        <Card className="border-l-4 border-l-emerald-500 shadow-sm">
          <CardContent className="p-3.5 flex items-center gap-3">
            <div className="p-2.5 rounded-lg bg-emerald-50 text-emerald-600">
              <Handshake className="w-5 h-5" />
            </div>
            <div>
              <div className="text-xl font-extrabold text-gray-900">{partners.length}</div>
              <div className="text-[11px] font-semibold text-gray-500 uppercase tracking-wider">Partners</div>
            </div>
          </CardContent>
        </Card>

        <Card className="border-l-4 border-l-sky-500 shadow-sm col-span-2 sm:col-span-1">
          <CardContent className="p-3.5 flex items-center gap-3">
            <div className="p-2.5 rounded-lg bg-sky-50 text-sky-600">
              <UserCheck className="w-5 h-5" />
            </div>
            <div>
              <div className="text-xl font-extrabold text-gray-900">{staffList.length}</div>
              <div className="text-[11px] font-semibold text-gray-500 uppercase tracking-wider">Staff Members</div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Main Tabs Navigation */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full space-y-4">
        <div className="border-b overflow-x-auto">
          <TabsList className="h-11 bg-transparent p-0 flex gap-2">
            <TabsTrigger
              value="all"
              className="data-[state=active]:border-amber-500 data-[state=active]:bg-amber-50/50 data-[state=active]:text-amber-700 border-b-2 border-transparent rounded-none px-4 font-semibold text-xs gap-1.5"
            >
              <Layers className="w-4 h-4" /> All ({allCombined.length})
            </TabsTrigger>
            <TabsTrigger
              value="companies"
              className="data-[state=active]:border-purple-500 data-[state=active]:bg-purple-50/50 data-[state=active]:text-purple-700 border-b-2 border-transparent rounded-none px-4 font-semibold text-xs gap-1.5"
            >
              <Building2 className="w-4 h-4" /> Companies ({companies.length})
            </TabsTrigger>
            <TabsTrigger
              value="vendors"
              className="data-[state=active]:border-amber-500 data-[state=active]:bg-amber-50/50 data-[state=active]:text-amber-700 border-b-2 border-transparent rounded-none px-4 font-semibold text-xs gap-1.5"
            >
              <Truck className="w-4 h-4" /> Vendors ({vendors.length})
            </TabsTrigger>
            <TabsTrigger
              value="partners"
              className="data-[state=active]:border-emerald-500 data-[state=active]:bg-emerald-50/50 data-[state=active]:text-emerald-700 border-b-2 border-transparent rounded-none px-4 font-semibold text-xs gap-1.5"
            >
              <Handshake className="w-4 h-4" /> Partners ({partners.length})
            </TabsTrigger>
            <TabsTrigger
              value="staff"
              className="data-[state=active]:border-sky-500 data-[state=active]:bg-sky-50/50 data-[state=active]:text-sky-700 border-b-2 border-transparent rounded-none px-4 font-semibold text-xs gap-1.5"
            >
              <UserCheck className="w-4 h-4" /> Staff ({staffList.length})
            </TabsTrigger>
            <TabsTrigger
              value="ledger"
              className="data-[state=active]:border-blue-500 data-[state=active]:bg-blue-50/50 data-[state=active]:text-blue-700 border-b-2 border-transparent rounded-none px-4 font-semibold text-xs gap-1.5"
            >
              <BookOpen className="w-4 h-4" /> Ledger Balances ({ledgerParties.length})
            </TabsTrigger>
            <TabsTrigger
              value="expense"
              className="data-[state=active]:border-indigo-500 data-[state=active]:bg-indigo-50/50 data-[state=active]:text-indigo-700 border-b-2 border-transparent rounded-none px-4 font-semibold text-xs gap-1.5"
            >
              <MinusCircle className="w-4 h-4 text-rose-500" /> Expense Heads
            </TabsTrigger>
            <TabsTrigger
              value="income"
              className="data-[state=active]:border-emerald-500 data-[state=active]:bg-emerald-50/50 data-[state=active]:text-emerald-700 border-b-2 border-transparent rounded-none px-4 font-semibold text-xs gap-1.5"
            >
              <PlusCircle className="w-4 h-4 text-emerald-500" /> Income Heads
            </TabsTrigger>
          </TabsList>
        </div>

        {/* ---------------------------------------------------- */}
        {/* TAB 1: ALL PARTIES */}
        {/* ---------------------------------------------------- */}
        <TabsContent value="all" className="space-y-4 m-0">
          <Card>
            <CardHeader className="p-4 border-b bg-gray-50/50 flex flex-col md:flex-row md:items-center justify-between gap-3">
              <div className="flex flex-wrap items-center gap-3">
                <div className="relative min-w-[240px]">
                  <Search className="w-4 h-4 absolute left-3 top-3 text-muted-foreground" />
                  <Input
                    placeholder="Search name, code, contact..."
                    value={allSearch}
                    onChange={(e) => setAllSearch(e.target.value)}
                    className="pl-9 bg-white"
                  />
                </div>
                <Select value={allTypeFilter} onValueChange={setAllTypeFilter}>
                  <SelectTrigger className="w-[170px] bg-white">
                    <SelectValue placeholder="All Types" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="ALL">All Types</SelectItem>
                    <SelectItem value="COMPANY">Company</SelectItem>
                    <SelectItem value="VENDOR">Vendor</SelectItem>
                    <SelectItem value="PARTNER">Partner</SelectItem>
                    <SelectItem value="STAFF">Staff</SelectItem>
                    <SelectItem value="CUSTOMER">Customer</SelectItem>
                    <SelectItem value="EMPLOYEE">Employee</SelectItem>
                    <SelectItem value="EXTERNAL">External</SelectItem>
                  </SelectContent>
                </Select>
                {(allSearch || allTypeFilter !== "ALL") && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => {
                      setAllSearch("");
                      setAllTypeFilter("ALL");
                    }}
                    className="text-xs"
                  >
                    <X className="w-3.5 h-3.5 mr-1" /> Reset
                  </Button>
                )}
              </div>
              <span className="text-xs text-muted-foreground font-medium">
                Showing {filteredAll.length} of {allCombined.length} parties
              </span>
            </CardHeader>
            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <table className="w-full text-sm text-left border-collapse">
                  <thead className="bg-gray-50/75 border-b text-xs font-semibold text-gray-500 uppercase">
                    <tr>
                      <th className="px-4 py-3">Party Name</th>
                      <th className="px-4 py-3">Type</th>
                      <th className="px-4 py-3">Code / ID</th>
                      <th className="px-4 py-3">Contact</th>
                      <th className="px-4 py-3">GST / Location</th>
                      <th className="px-4 py-3">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {loadingData ? (
                      <tr>
                        <td colSpan={6} className="text-center py-12">
                          <Loader2 className="w-6 h-6 animate-spin text-amber-500 mx-auto" />
                          <p className="text-xs text-muted-foreground mt-2">Loading parties...</p>
                        </td>
                      </tr>
                    ) : filteredAll.length === 0 ? (
                      <tr>
                        <td colSpan={6} className="text-center py-12 text-muted-foreground">
                          <Search className="w-8 h-8 mx-auto text-gray-300 mb-2" />
                          <p className="font-medium">No parties found</p>
                          <p className="text-xs">Try adjusting your filters or search keyword.</p>
                        </td>
                      </tr>
                    ) : (
                      filteredAll.map((p, idx) => (
                        <tr key={idx} className="hover:bg-amber-50/30 transition-colors">
                          <td className="px-4 py-3 font-semibold text-gray-900">{p.name}</td>
                          <td className="px-4 py-3">{getTypeBadge(p.type, p.subType)}</td>
                          <td className="px-4 py-3 font-mono text-xs text-gray-600">{p.code || "—"}</td>
                          <td className="px-4 py-3 text-xs text-gray-600">{p.contact || "—"}</td>
                          <td className="px-4 py-3 text-xs text-gray-600">{p.gstOrLocation || "—"}</td>
                          <td className="px-4 py-3">
                            <Badge
                              variant="outline"
                              className={
                                p.status === "Active"
                                  ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                                  : p.status === "Resigned"
                                  ? "bg-amber-50 text-amber-700 border-amber-200"
                                  : "bg-rose-50 text-rose-700 border-rose-200"
                              }
                            >
                              {p.status}
                            </Badge>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* ---------------------------------------------------- */}
        {/* TAB 2: COMPANIES */}
        {/* ---------------------------------------------------- */}
        <TabsContent value="companies" className="space-y-4 m-0">
          <div className="grid grid-cols-3 gap-3">
            <Card className="p-3 bg-purple-50/50 border-purple-100 shadow-none">
              <div className="text-xs font-semibold text-purple-700">Total Companies</div>
              <div className="text-2xl font-black text-purple-900 mt-1">{coStats.total}</div>
            </Card>
            <Card className="p-3 bg-emerald-50/50 border-emerald-100 shadow-none">
              <div className="text-xs font-semibold text-emerald-700">Active Companies</div>
              <div className="text-2xl font-black text-emerald-900 mt-1">{coStats.active}</div>
            </Card>
            <Card className="p-3 bg-rose-50/50 border-rose-100 shadow-none">
              <div className="text-xs font-semibold text-rose-700">Inactive Companies</div>
              <div className="text-2xl font-black text-rose-900 mt-1">{coStats.inactive}</div>
            </Card>
          </div>

          <Card>
            <CardHeader className="p-4 border-b bg-gray-50/50 flex flex-col md:flex-row md:items-center justify-between gap-3">
              <div className="flex flex-wrap items-center gap-3">
                <div className="relative min-w-[240px]">
                  <Search className="w-4 h-4 absolute left-3 top-3 text-muted-foreground" />
                  <Input
                    placeholder="Search company name, GST, code..."
                    value={coSearch}
                    onChange={(e) => setCoSearch(e.target.value)}
                    className="pl-9 bg-white"
                  />
                </div>
                <Select value={coTypeFilter} onValueChange={setCoTypeFilter}>
                  <SelectTrigger className="w-[160px] bg-white">
                    <SelectValue placeholder="All Types" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="ALL">All Types</SelectItem>
                    <SelectItem value="MAIN">Main</SelectItem>
                    <SelectItem value="SUBSIDIARY">Subsidiary</SelectItem>
                    <SelectItem value="ASSOCIATE">Associate</SelectItem>
                  </SelectContent>
                </Select>
                {(coSearch || coTypeFilter !== "ALL") && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => {
                      setCoSearch("");
                      setCoTypeFilter("ALL");
                    }}
                    className="text-xs"
                  >
                    <X className="w-3.5 h-3.5 mr-1" /> Reset
                  </Button>
                )}
              </div>
              <Button
                onClick={() => openCoModal()}
                className="bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-700 hover:to-indigo-700 text-white gap-1.5"
              >
                <Plus className="w-4 h-4" /> Add Company
              </Button>
            </CardHeader>
            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <table className="w-full text-sm text-left border-collapse">
                  <thead className="bg-gray-50/75 border-b text-xs font-semibold text-gray-500 uppercase">
                    <tr>
                      <th className="px-4 py-3">ID</th>
                      <th className="px-4 py-3">Company Name</th>
                      <th className="px-4 py-3">Type</th>
                      <th className="px-4 py-3">Code</th>
                      <th className="px-4 py-3">GSTIN</th>
                      <th className="px-4 py-3">Location</th>
                      <th className="px-4 py-3">Status</th>
                      <th className="px-4 py-3 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {filteredCompanies.length === 0 ? (
                      <tr>
                        <td colSpan={8} className="text-center py-12 text-muted-foreground">
                          <Building2 className="w-8 h-8 mx-auto text-gray-300 mb-2" />
                          <p className="font-medium">No companies found</p>
                        </td>
                      </tr>
                    ) : (
                      filteredCompanies.map((c) => (
                        <tr key={c.id} className="hover:bg-purple-50/20 transition-colors">
                          <td className="px-4 py-3 font-mono text-xs text-muted-foreground">#{c.id}</td>
                          <td className="px-4 py-3 font-semibold text-gray-900">
                            {c.company_name}
                            {c.is_marketplace_endpoint && (
                              <Badge variant="secondary" className="ml-2 text-[10px] bg-purple-100 text-purple-700">
                                Mkt Endpoint
                              </Badge>
                            )}
                          </td>
                          <td className="px-4 py-3">
                            <Badge variant="outline" className="bg-purple-50 text-purple-700 border-purple-200">
                              {c.company_type || "SUBSIDIARY"}
                            </Badge>
                          </td>
                          <td className="px-4 py-3 font-mono text-xs">{c.company_code || "—"}</td>
                          <td className="px-4 py-3 font-mono text-xs">{c.gst_number || "—"}</td>
                          <td className="px-4 py-3 text-xs text-gray-600">
                            {[c.city, c.state].filter(Boolean).join(", ") || "—"}
                          </td>
                          <td className="px-4 py-3">
                            <Badge
                              variant="outline"
                              className={
                                c.is_active !== false
                                  ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                                  : "bg-rose-50 text-rose-700 border-rose-200"
                              }
                            >
                              {c.is_active !== false ? "Active" : "Inactive"}
                            </Badge>
                          </td>
                          <td className="px-4 py-3 text-right">
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => openCoModal(c)}
                              className="h-8 gap-1 border-purple-200 text-purple-700 hover:bg-purple-50"
                            >
                              <Pencil className="w-3.5 h-3.5" /> Edit
                            </Button>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* ---------------------------------------------------- */}
        {/* TAB 3: VENDORS */}
        {/* ---------------------------------------------------- */}
        <TabsContent value="vendors" className="space-y-4 m-0">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <Card className="p-3 bg-amber-50/50 border-amber-100 shadow-none">
              <div className="text-xs font-semibold text-amber-700">Total Vendors</div>
              <div className="text-2xl font-black text-amber-900 mt-1">{vndStats.total}</div>
            </Card>
            <Card className="p-3 bg-emerald-50/50 border-emerald-100 shadow-none">
              <div className="text-xs font-semibold text-emerald-700">Active Vendors</div>
              <div className="text-2xl font-black text-emerald-900 mt-1">{vndStats.active}</div>
            </Card>
            <Card className="p-3 bg-rose-50/50 border-rose-100 shadow-none">
              <div className="text-xs font-semibold text-rose-700">Inactive</div>
              <div className="text-2xl font-black text-rose-900 mt-1">{vndStats.inactive}</div>
            </Card>
            <Card className="p-3 bg-blue-50/50 border-blue-100 shadow-none">
              <div className="text-xs font-semibold text-blue-700">Product + Service</div>
              <div className="text-2xl font-black text-blue-900 mt-1">{vndStats.both}</div>
            </Card>
          </div>

          <Card>
            <CardHeader className="p-4 border-b bg-gray-50/50 flex flex-col md:flex-row md:items-center justify-between gap-3">
              <div className="flex flex-wrap items-center gap-3">
                <div className="relative min-w-[220px]">
                  <Search className="w-4 h-4 absolute left-3 top-3 text-muted-foreground" />
                  <Input
                    placeholder="Search vendor name, code, GST..."
                    value={vndSearch}
                    onChange={(e) => setVndSearch(e.target.value)}
                    className="pl-9 bg-white"
                  />
                </div>
                <Select value={vndTypeFilter} onValueChange={setVndTypeFilter}>
                  <SelectTrigger className="w-[140px] bg-white">
                    <SelectValue placeholder="All Types" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="ALL">All Types</SelectItem>
                    <SelectItem value="PRODUCT">Product</SelectItem>
                    <SelectItem value="SERVICE">Service</SelectItem>
                    <SelectItem value="BOTH">Both</SelectItem>
                    <SelectItem value="SOLAR">Solar</SelectItem>
                  </SelectContent>
                </Select>
                <Select value={vndCompanyFilter} onValueChange={setVndCompanyFilter}>
                  <SelectTrigger className="w-[160px] bg-white">
                    <SelectValue placeholder="All Companies" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="ALL">All Companies</SelectItem>
                    {companies.map((c) => (
                      <SelectItem key={c.id} value={String(c.id)}>
                        {c.company_name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Select value={vndStatusFilter} onValueChange={setVndStatusFilter}>
                  <SelectTrigger className="w-[120px] bg-white">
                    <SelectValue placeholder="All Status" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="ALL">All Status</SelectItem>
                    <SelectItem value="active">Active</SelectItem>
                    <SelectItem value="inactive">Inactive</SelectItem>
                  </SelectContent>
                </Select>
                {(vndSearch ||
                  vndTypeFilter !== "ALL" ||
                  vndCompanyFilter !== "ALL" ||
                  vndStatusFilter !== "ALL") && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => {
                      setVndSearch("");
                      setVndTypeFilter("ALL");
                      setVndCompanyFilter("ALL");
                      setVndStatusFilter("ALL");
                    }}
                    className="text-xs"
                  >
                    <X className="w-3.5 h-3.5 mr-1" /> Reset
                  </Button>
                )}
              </div>
              <Button
                onClick={() => openVndModal()}
                className="bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-600 hover:to-orange-600 text-white gap-1.5"
              >
                <Plus className="w-4 h-4" /> Add Vendor
              </Button>
            </CardHeader>
            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <table className="w-full text-sm text-left border-collapse">
                  <thead className="bg-gray-50/75 border-b text-xs font-semibold text-gray-500 uppercase">
                    <tr>
                      <th className="px-4 py-3">Code</th>
                      <th className="px-4 py-3">Vendor Name</th>
                      <th className="px-4 py-3">Type</th>
                      <th className="px-4 py-3">Contact</th>
                      <th className="px-4 py-3">GSTIN</th>
                      <th className="px-4 py-3">Location</th>
                      <th className="px-4 py-3">Applicable Companies</th>
                      <th className="px-4 py-3">Status</th>
                      <th className="px-4 py-3 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {filteredVendors.length === 0 ? (
                      <tr>
                        <td colSpan={9} className="text-center py-12 text-muted-foreground">
                          <Truck className="w-8 h-8 mx-auto text-gray-300 mb-2" />
                          <p className="font-medium">No vendors found</p>
                        </td>
                      </tr>
                    ) : (
                      filteredVendors.map((v) => {
                        const vac = v.applicable_companies || [];
                        const isAll = vac.includes("ALL");
                        const matchedCos = isAll
                          ? ["All Companies"]
                          : companies
                              .filter((c) => (vac as any[]).includes(c.id))
                              .map((c) => c.company_name);

                        return (
                          <tr key={v.id} className="hover:bg-amber-50/20 transition-colors">
                            <td className="px-4 py-3 font-mono font-bold text-xs text-amber-600">
                              {v.vendor_code}
                            </td>
                            <td className="px-4 py-3">
                              <div className="font-semibold text-gray-900">{v.vendor_name}</div>
                              {v.trade_name && (
                                <div className="text-xs text-muted-foreground font-normal">
                                  {v.trade_name}
                                </div>
                              )}
                            </td>
                            <td className="px-4 py-3">
                              <Badge variant="outline" className="bg-amber-50 text-amber-700 border-amber-200">
                                {v.vendor_type}
                              </Badge>
                            </td>
                            <td className="px-4 py-3 text-xs">
                              {v.contact_person_1_phone || v.phone || v.email || "—"}
                            </td>
                            <td className="px-4 py-3 font-mono text-xs">{v.gst_number || "—"}</td>
                            <td className="px-4 py-3 text-xs text-gray-600">
                              {[v.city, v.state].filter(Boolean).join(", ") || "—"}
                            </td>
                            <td className="px-4 py-3">
                              <div className="flex flex-wrap gap-1 max-w-[200px]">
                                {matchedCos.length > 0 ? (
                                  matchedCos.map((cn, i) => (
                                    <Badge
                                      key={i}
                                      variant="secondary"
                                      className="text-[10px] bg-amber-50 text-amber-800 border border-amber-200"
                                    >
                                      {cn}
                                    </Badge>
                                  ))
                                ) : (
                                  <span className="text-xs text-muted-foreground">—</span>
                                )}
                              </div>
                            </td>
                            <td className="px-4 py-3">
                              <Badge
                                variant="outline"
                                className={
                                  v.is_active !== false
                                    ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                                    : "bg-rose-50 text-rose-700 border-rose-200"
                                }
                              >
                                {v.is_active !== false ? "Active" : "Inactive"}
                              </Badge>
                            </td>
                            <td className="px-4 py-3 text-right">
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => openVndModal(v)}
                                className="h-8 gap-1 border-amber-200 text-amber-700 hover:bg-amber-50"
                              >
                                <Pencil className="w-3.5 h-3.5" /> Edit
                              </Button>
                            </td>
                          </tr>
                        );
                      })
                    )}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* ---------------------------------------------------- */}
        {/* TAB 4: PARTNERS */}
        {/* ---------------------------------------------------- */}
        <TabsContent value="partners" className="space-y-4 m-0">
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
            <Card className="p-3 bg-emerald-50/50 border-emerald-100 shadow-none">
              <div className="text-xs font-semibold text-emerald-700">Total Partners</div>
              <div className="text-2xl font-black text-emerald-900 mt-1">{prtStats.total}</div>
            </Card>
            <Card className="p-3 bg-emerald-50/50 border-emerald-100 shadow-none">
              <div className="text-xs font-semibold text-emerald-700">Active</div>
              <div className="text-2xl font-black text-emerald-900 mt-1">{prtStats.active}</div>
            </Card>
            <Card className="p-3 bg-amber-50/50 border-amber-100 shadow-none">
              <div className="text-xs font-semibold text-amber-700">Dealers</div>
              <div className="text-2xl font-black text-amber-900 mt-1">{prtStats.dealer}</div>
            </Card>
            <Card className="p-3 bg-blue-50/50 border-blue-100 shadow-none">
              <div className="text-xs font-semibold text-blue-700">Distributors</div>
              <div className="text-2xl font-black text-blue-900 mt-1">{prtStats.distributor}</div>
            </Card>
            <Card className="p-3 bg-purple-50/50 border-purple-100 shadow-none col-span-2 sm:col-span-1">
              <div className="text-xs font-semibold text-purple-700">Service Centers</div>
              <div className="text-2xl font-black text-purple-900 mt-1">{prtStats.svc}</div>
            </Card>
          </div>

          <Card>
            <CardHeader className="p-4 border-b bg-gray-50/50 flex flex-col md:flex-row md:items-center justify-between gap-3">
              <div className="flex flex-wrap items-center gap-3">
                <div className="relative min-w-[220px]">
                  <Search className="w-4 h-4 absolute left-3 top-3 text-muted-foreground" />
                  <Input
                    placeholder="Search partner name, code, phone..."
                    value={prtSearch}
                    onChange={(e) => setPrtSearch(e.target.value)}
                    className="pl-9 bg-white"
                  />
                </div>
                <Select value={prtCategoryFilter} onValueChange={setPrtCategoryFilter}>
                  <SelectTrigger className="w-[160px] bg-white">
                    <SelectValue placeholder="All Categories" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="ALL">All Categories</SelectItem>
                    <SelectItem value="DEALER">Dealer</SelectItem>
                    <SelectItem value="DISTRIBUTOR">Distributor</SelectItem>
                    <SelectItem value="SERVICE_CENTER">Service Center</SelectItem>
                    <SelectItem value="VENDOR">Vendor</SelectItem>
                    <SelectItem value="REAL_DREAM_PARTNER">Real Dreams</SelectItem>
                  </SelectContent>
                </Select>
                <Select value={prtStatusFilter} onValueChange={setPrtStatusFilter}>
                  <SelectTrigger className="w-[120px] bg-white">
                    <SelectValue placeholder="All Status" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="ALL">All Status</SelectItem>
                    <SelectItem value="active">Active</SelectItem>
                    <SelectItem value="inactive">Inactive</SelectItem>
                  </SelectContent>
                </Select>
                {(prtSearch || prtCategoryFilter !== "ALL" || prtStatusFilter !== "ALL") && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => {
                      setPrtSearch("");
                      setPrtCategoryFilter("ALL");
                      setPrtStatusFilter("ALL");
                    }}
                    className="text-xs"
                  >
                    <X className="w-3.5 h-3.5 mr-1" /> Reset
                  </Button>
                )}
              </div>
              <Button
                onClick={() => openPrtModal()}
                className="bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-700 hover:to-teal-700 text-white gap-1.5"
              >
                <Plus className="w-4 h-4" /> Add Partner
              </Button>
            </CardHeader>
            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <table className="w-full text-sm text-left border-collapse">
                  <thead className="bg-gray-50/75 border-b text-xs font-semibold text-gray-500 uppercase">
                    <tr>
                      <th className="px-4 py-3">Code</th>
                      <th className="px-4 py-3">Partner Name</th>
                      <th className="px-4 py-3">Category</th>
                      <th className="px-4 py-3">Contact</th>
                      <th className="px-4 py-3">GSTIN / PAN</th>
                      <th className="px-4 py-3">Location</th>
                      <th className="px-4 py-3">Status</th>
                      <th className="px-4 py-3 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {filteredPartners.length === 0 ? (
                      <tr>
                        <td colSpan={8} className="text-center py-12 text-muted-foreground">
                          <Handshake className="w-8 h-8 mx-auto text-gray-300 mb-2" />
                          <p className="font-medium">No partners found</p>
                        </td>
                      </tr>
                    ) : (
                      filteredPartners.map((p) => (
                        <tr key={p.id} className="hover:bg-emerald-50/20 transition-colors">
                          <td className="px-4 py-3 font-mono font-bold text-xs text-blue-600">
                            {p.code || "—"}
                          </td>
                          <td className="px-4 py-3 font-semibold text-gray-900">{p.name}</td>
                          <td className="px-4 py-3">{getTypeBadge(p.category)}</td>
                          <td className="px-4 py-3 text-xs text-gray-600">{p.phone || p.email || "—"}</td>
                          <td className="px-4 py-3 font-mono text-xs">
                            {[p.gst, p.pan].filter(Boolean).join(" / ") || "—"}
                          </td>
                          <td className="px-4 py-3 text-xs text-gray-600">
                            {[p.city, p.state].filter(Boolean).join(", ") || "—"}
                          </td>
                          <td className="px-4 py-3">
                            <Badge
                              variant="outline"
                              className={
                                p.is_active
                                  ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                                  : "bg-rose-50 text-rose-700 border-rose-200"
                              }
                            >
                              {p.is_active ? "Active" : "Inactive"}
                            </Badge>
                          </td>
                          <td className="px-4 py-3 text-right">
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => openPrtModal(p)}
                              className="h-8 gap-1 border-emerald-200 text-emerald-700 hover:bg-emerald-50"
                            >
                              <Pencil className="w-3.5 h-3.5" /> Edit
                            </Button>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* ---------------------------------------------------- */}
        {/* TAB 5: STAFF */}
        {/* ---------------------------------------------------- */}
        <TabsContent value="staff" className="space-y-4 m-0">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <Card className="p-3 bg-sky-50/50 border-sky-100 shadow-none">
              <div className="text-xs font-semibold text-sky-700">Total Staff</div>
              <div className="text-2xl font-black text-sky-900 mt-1">{stfStats.total}</div>
            </Card>
            <Card className="p-3 bg-emerald-50/50 border-emerald-100 shadow-none">
              <div className="text-xs font-semibold text-emerald-700">Active Staff</div>
              <div className="text-2xl font-black text-emerald-900 mt-1">{stfStats.active}</div>
            </Card>
            <Card className="p-3 bg-amber-50/50 border-amber-100 shadow-none">
              <div className="text-xs font-semibold text-amber-700">Resigned</div>
              <div className="text-2xl font-black text-amber-900 mt-1">{stfStats.resigned}</div>
            </Card>
            <Card className="p-3 bg-rose-50/50 border-rose-100 shadow-none">
              <div className="text-xs font-semibold text-rose-700">Inactive</div>
              <div className="text-2xl font-black text-rose-900 mt-1">{stfStats.inactive}</div>
            </Card>
          </div>

          <Card>
            <CardHeader className="p-4 border-b bg-gray-50/50 flex flex-col md:flex-row md:items-center justify-between gap-3">
              <div className="flex flex-wrap items-center gap-3">
                <div className="relative min-w-[240px]">
                  <Search className="w-4 h-4 absolute left-3 top-3 text-muted-foreground" />
                  <Input
                    placeholder="Search staff name, code, phone..."
                    value={stfSearch}
                    onChange={(e) => setStfSearch(e.target.value)}
                    className="pl-9 bg-white"
                  />
                </div>
                <Select value={stfStatusFilter} onValueChange={setStfStatusFilter}>
                  <SelectTrigger className="w-[140px] bg-white">
                    <SelectValue placeholder="All Status" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="ALL">All Status</SelectItem>
                    <SelectItem value="active">Active</SelectItem>
                    <SelectItem value="inactive">Inactive</SelectItem>
                    <SelectItem value="resigned">Resigned</SelectItem>
                    <SelectItem value="terminated">Terminated</SelectItem>
                  </SelectContent>
                </Select>
                {(stfSearch || stfStatusFilter !== "ALL") && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => {
                      setStfSearch("");
                      setStfStatusFilter("ALL");
                    }}
                    className="text-xs"
                  >
                    <X className="w-3.5 h-3.5 mr-1" /> Reset
                  </Button>
                )}
              </div>
              <span className="text-xs text-muted-foreground font-medium">
                {filteredStaff.length} of {staffList.length} staff members
              </span>
            </CardHeader>
            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <table className="w-full text-sm text-left border-collapse">
                  <thead className="bg-gray-50/75 border-b text-xs font-semibold text-gray-500 uppercase">
                    <tr>
                      <th className="px-4 py-3">Code</th>
                      <th className="px-4 py-3">Full Name</th>
                      <th className="px-4 py-3">Role</th>
                      <th className="px-4 py-3">Department</th>
                      <th className="px-4 py-3">Phone</th>
                      <th className="px-4 py-3">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {filteredStaff.length === 0 ? (
                      <tr>
                        <td colSpan={6} className="text-center py-12 text-muted-foreground">
                          <UserCheck className="w-8 h-8 mx-auto text-gray-300 mb-2" />
                          <p className="font-medium">No staff members found</p>
                        </td>
                      </tr>
                    ) : (
                      filteredStaff.map((s) => (
                        <tr key={s.id} className="hover:bg-sky-50/20 transition-colors">
                          <td className="px-4 py-3 font-mono font-bold text-xs text-sky-700">
                            {s.code || `EMP${s.id}`}
                          </td>
                          <td className="px-4 py-3 font-semibold text-gray-900">{s.name}</td>
                          <td className="px-4 py-3 text-xs">{s.role || "—"}</td>
                          <td className="px-4 py-3 text-xs">{s.department || "—"}</td>
                          <td className="px-4 py-3 text-xs">{s.phone || "—"}</td>
                          <td className="px-4 py-3">
                            <Badge
                              variant="outline"
                              className={
                                s.status === "active"
                                  ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                                  : s.status === "resigned"
                                  ? "bg-amber-50 text-amber-700 border-amber-200"
                                  : "bg-rose-50 text-rose-700 border-rose-200"
                              }
                            >
                              {(s.status || "—").charAt(0).toUpperCase() + (s.status || "").slice(1)}
                            </Badge>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* ---------------------------------------------------- */}
        {/* TAB 6: LEDGER BALANCES */}
        {/* ---------------------------------------------------- */}
        <TabsContent value="ledger" className="space-y-4 m-0">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <Card className="p-3 bg-blue-50/50 border-blue-100 shadow-none">
              <div className="text-xs font-semibold text-blue-700">Total Parties</div>
              <div className="text-2xl font-black text-blue-900 mt-1">{ldgStats.total}</div>
            </Card>
            <Card className="p-3 bg-rose-50/50 border-rose-100 shadow-none">
              <div className="text-xs font-semibold text-rose-700 flex items-center gap-1">
                <ArrowUpRight className="w-3.5 h-3.5 text-rose-500" /> Total Debit (DR)
              </div>
              <div className="text-2xl font-black text-rose-600 mt-1">{fmtShort(ldgStats.totalDR)}</div>
            </Card>
            <Card className="p-3 bg-emerald-50/50 border-emerald-100 shadow-none">
              <div className="text-xs font-semibold text-emerald-700 flex items-center gap-1">
                <ArrowDownLeft className="w-3.5 h-3.5 text-emerald-500" /> Total Credit (CR)
              </div>
              <div className="text-2xl font-black text-emerald-600 mt-1">{fmtShort(ldgStats.totalCR)}</div>
            </Card>
            <Card className="p-3 bg-amber-50/50 border-amber-100 shadow-none">
              <div className="text-xs font-semibold text-amber-700 flex items-center gap-1">
                <Scale className="w-3.5 h-3.5 text-amber-500" /> Net Balance
              </div>
              <div className="text-2xl font-black text-amber-900 mt-1">{fmtShort(Math.abs(ldgStats.net))}</div>
            </Card>
          </div>

          <Card>
            <CardHeader className="p-4 border-b bg-gray-50/50 flex flex-col md:flex-row md:items-center justify-between gap-3">
              <div className="flex flex-wrap items-center gap-3">
                <div className="relative min-w-[220px]">
                  <Search className="w-4 h-4 absolute left-3 top-3 text-muted-foreground" />
                  <Input
                    placeholder="Search party name..."
                    value={ldgSearch}
                    onChange={(e) => setLdgSearch(e.target.value)}
                    className="pl-9 bg-white"
                  />
                </div>
                <Select value={ldgTypeFilter} onValueChange={setLdgTypeFilter}>
                  <SelectTrigger className="w-[140px] bg-white">
                    <SelectValue placeholder="All Types" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="ALL">All Types</SelectItem>
                    <SelectItem value="COMPANY">Company</SelectItem>
                    <SelectItem value="CUSTOMER">Customer</SelectItem>
                    <SelectItem value="VENDOR">Vendor</SelectItem>
                    <SelectItem value="EMPLOYEE">Employee</SelectItem>
                    <SelectItem value="EXTERNAL">External</SelectItem>
                  </SelectContent>
                </Select>
                <Select
                  value={ldgCompanyFilter}
                  onValueChange={(val) => {
                    setLdgCompanyFilter(val);
                    loadLedgerData(val !== "ALL" ? val : "");
                  }}
                >
                  <SelectTrigger className="w-[160px] bg-white">
                    <SelectValue placeholder="All Companies" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="ALL">All Companies</SelectItem>
                    {companies.map((c) => (
                      <SelectItem key={c.id} value={String(c.id)}>
                        {c.company_name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                {(ldgSearch || ldgTypeFilter !== "ALL" || ldgCompanyFilter !== "ALL") && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => {
                      setLdgSearch("");
                      setLdgTypeFilter("ALL");
                      setLdgCompanyFilter("ALL");
                      loadLedgerData("");
                    }}
                    className="text-xs"
                  >
                    <X className="w-3.5 h-3.5 mr-1" /> Reset
                  </Button>
                )}
              </div>
              <Button
                onClick={openAddLedgerModal}
                className="bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white gap-1.5"
              >
                <Plus className="w-4 h-4" /> Add Journal Entry
              </Button>
            </CardHeader>
            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <table className="w-full text-sm text-left border-collapse">
                  <thead className="bg-gray-50/75 border-b text-xs font-semibold text-gray-500 uppercase">
                    <tr>
                      <th className="px-4 py-3">Party Name</th>
                      <th className="px-4 py-3">Type</th>
                      <th className="px-4 py-3">Party ID</th>
                      <th className="px-4 py-3 text-right">Total DR (₹)</th>
                      <th className="px-4 py-3 text-right">Total CR (₹)</th>
                      <th className="px-4 py-3 text-right">Net Balance</th>
                      <th className="px-4 py-3 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {ledgerLoading ? (
                      <tr>
                        <td colSpan={7} className="text-center py-12">
                          <Loader2 className="w-6 h-6 animate-spin text-blue-500 mx-auto" />
                          <p className="text-xs text-muted-foreground mt-2">Computing ledger balances...</p>
                        </td>
                      </tr>
                    ) : filteredLedger.length === 0 ? (
                      <tr>
                        <td colSpan={7} className="text-center py-12 text-muted-foreground">
                          <BookOpen className="w-8 h-8 mx-auto text-gray-300 mb-2" />
                          <p className="font-medium">No ledger parties found</p>
                        </td>
                      </tr>
                    ) : (
                      filteredLedger.map((lp, idx) => {
                        const net = lp.balance;
                        const netCls =
                          net > 0
                            ? "text-emerald-700 bg-emerald-50 border-emerald-200"
                            : net < 0
                            ? "text-rose-700 bg-rose-50 border-rose-200"
                            : "text-gray-600 bg-gray-50 border-gray-200";

                        return (
                          <tr key={idx} className="hover:bg-blue-50/20 transition-colors">
                            <td className="px-4 py-3 font-semibold text-gray-900">{lp.party_name}</td>
                            <td className="px-4 py-3">{getTypeBadge(lp.party_type)}</td>
                            <td className="px-4 py-3 font-mono text-xs text-muted-foreground">
                              {lp.party_id || "—"}
                            </td>
                            <td className="px-4 py-3 text-right font-mono font-medium text-rose-600">
                              {fmt(lp.total_debit)}
                            </td>
                            <td className="px-4 py-3 text-right font-mono font-medium text-emerald-600">
                              {fmt(lp.total_credit)}
                            </td>
                            <td className="px-4 py-3 text-right">
                              <Badge variant="outline" className={`font-mono font-bold ${netCls}`}>
                                {fmt(Math.abs(net))} {net < 0 ? "CR" : net > 0 ? "DR" : ""}
                              </Badge>
                            </td>
                            <td className="px-4 py-3 text-right">
                              <Link
                                href={`/staff/accounts/party-ledger?party_name=${encodeURIComponent(
                                  lp.party_name
                                )}&party_type=${encodeURIComponent(lp.party_type || "")}`}
                              >
                                <Button
                                  variant="outline"
                                  size="sm"
                                  className="h-8 gap-1 border-blue-200 text-blue-700 hover:bg-blue-50"
                                >
                                  <BookOpen className="w-3.5 h-3.5" /> View Ledger
                                </Button>
                              </Link>
                            </td>
                          </tr>
                        );
                      })
                    )}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* ---------------------------------------------------- */}
        {/* TAB 7: EXPENSE HEADS */}
        {/* ---------------------------------------------------- */}
        <TabsContent value="expense" className="space-y-4 m-0">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <Card className="p-3 bg-indigo-50/50 border-indigo-100 shadow-none">
              <div className="text-xs font-semibold text-indigo-700">Main Categories</div>
              <div className="text-2xl font-black text-indigo-900 mt-1">{expStats.main}</div>
            </Card>
            <Card className="p-3 bg-blue-50/50 border-blue-100 shadow-none">
              <div className="text-xs font-semibold text-blue-700">Sub Categories</div>
              <div className="text-2xl font-black text-blue-900 mt-1">{expStats.sub}</div>
            </Card>
            <Card className="p-3 bg-rose-50/50 border-rose-100 shadow-none">
              <div className="text-xs font-semibold text-rose-700 flex items-center gap-1">
                <IndianRupee className="w-3.5 h-3.5" /> Total Expenses
              </div>
              <div className="text-2xl font-black text-rose-600 mt-1">{fmt(expStats.totalAmt)}</div>
            </Card>
            <Card className="p-3 bg-amber-50/50 border-amber-100 shadow-none">
              <div className="text-xs font-semibold text-amber-700 flex items-center gap-1">
                <Receipt className="w-3.5 h-3.5" /> Total Entries
              </div>
              <div className="text-2xl font-black text-amber-900 mt-1">{expStats.totalEnt}</div>
            </Card>
          </div>

          <div className="flex flex-wrap items-center justify-between gap-3 bg-white p-3 rounded-lg border shadow-sm">
            <div className="flex items-center gap-2">
              <Button
                size="sm"
                variant={expInnerTab === "main" ? "default" : "outline"}
                onClick={() => setExpInnerTab("main")}
                className={expInnerTab === "main" ? "bg-indigo-600 hover:bg-indigo-700" : ""}
              >
                <Folder className="w-4 h-4 mr-1.5" /> Main Categories ({expMain.length})
              </Button>
              <Button
                size="sm"
                variant={expInnerTab === "sub" ? "default" : "outline"}
                onClick={() => setExpInnerTab("sub")}
                className={expInnerTab === "sub" ? "bg-emerald-600 hover:bg-emerald-700 text-white" : ""}
              >
                <FolderOpen className="w-4 h-4 mr-1.5" /> Sub Categories ({expSub.length})
              </Button>
            </div>

            <div className="flex items-center gap-2">
              <Select
                value={expFilterCo}
                onValueChange={(val) => {
                  setExpFilterCo(val);
                  loadExpenseCategories(val);
                }}
              >
                <SelectTrigger className="w-[150px] h-9">
                  <SelectValue placeholder="All Companies" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">All Companies</SelectItem>
                  {companies.map((c) => (
                    <SelectItem key={c.id} value={String(c.id)}>
                      {c.company_name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>

              <Select value={expSort} onValueChange={setExpSort}>
                <SelectTrigger className="w-[170px] h-9">
                  <SelectValue placeholder="Sort..." />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="name_asc">Name A → Z</SelectItem>
                  <SelectItem value="name_desc">Name Z → A</SelectItem>
                  <SelectItem value="amt_desc">Amount ↓ High</SelectItem>
                  <SelectItem value="amt_asc">Amount ↑ Low</SelectItem>
                  <SelectItem value="cnt_desc">Entries ↓ High</SelectItem>
                  <SelectItem value="cnt_asc">Entries ↑ Low</SelectItem>
                </SelectContent>
              </Select>

              {expInnerTab === "main" ? (
                <Button
                  size="sm"
                  onClick={() => {
                    setExpMainEditId(null);
                    setExpMainForm({ name: "", description: "" });
                    setIsExpMainModalOpen(true);
                  }}
                  className="bg-indigo-600 hover:bg-indigo-700 h-9 gap-1"
                >
                  <Plus className="w-4 h-4" /> Add Main Category
                </Button>
              ) : (
                <Button
                  size="sm"
                  onClick={() => {
                    setExpSubEditId(null);
                    setExpSubForm({ parent_id: "", name: "", description: "" });
                    setIsExpSubModalOpen(true);
                  }}
                  className="bg-emerald-600 hover:bg-emerald-700 text-white h-9 gap-1"
                >
                  <Plus className="w-4 h-4" /> Add Sub Category
                </Button>
              )}
            </div>
          </div>

          {expInnerTab === "main" ? (
            <Card>
              <CardContent className="p-0">
                <div className="overflow-x-auto">
                  <table className="w-full text-sm text-left border-collapse">
                    <thead className="bg-gray-50/75 border-b text-xs font-semibold text-gray-500 uppercase">
                      <tr>
                        <th className="px-4 py-3">#ID</th>
                        <th className="px-4 py-3">Category Name</th>
                        <th className="px-4 py-3">Description</th>
                        <th className="px-4 py-3">Sub Categories</th>
                        <th className="px-4 py-3 text-right">Total Amount (₹)</th>
                        <th className="px-4 py-3 text-right">Entries</th>
                        <th className="px-4 py-3 text-right">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">
                      {sortedExpMain.length === 0 ? (
                        <tr>
                          <td colSpan={7} className="text-center py-12 text-muted-foreground">
                            <Folder className="w-8 h-8 mx-auto text-gray-300 mb-2" />
                            <p className="font-medium">No expense main categories found</p>
                          </td>
                        </tr>
                      ) : (
                        sortedExpMain.map((cat) => {
                          const subs = expSub.filter((s) => s.parent_id === cat.id);
                          const amt = expAmounts.main[String(cat.id)] || { total: 0, count: 0 };
                          return (
                            <tr key={cat.id} className="hover:bg-indigo-50/20 transition-colors">
                              <td className="px-4 py-3 font-mono text-xs text-muted-foreground">
                                #{cat.id}
                              </td>
                              <td className="px-4 py-3">
                                <div className="font-bold text-gray-900">{cat.name}</div>
                                {subs.length > 0 && (
                                  <div className="flex flex-wrap gap-1 mt-1">
                                    {subs.map((s) => (
                                      <Badge
                                        key={s.id}
                                        variant="secondary"
                                        className="text-[10px] bg-indigo-50 text-indigo-700"
                                      >
                                        {s.name}
                                      </Badge>
                                    ))}
                                  </div>
                                )}
                              </td>
                              <td className="px-4 py-3 text-xs text-gray-600">{cat.description || "—"}</td>
                              <td className="px-4 py-3">
                                <Badge variant="outline" className="bg-sky-50 text-sky-700">
                                  {subs.length} sub-categories
                                </Badge>
                              </td>
                              <td className="px-4 py-3 text-right font-mono font-semibold text-rose-600">
                                {fmt(amt.total)}
                              </td>
                              <td className="px-4 py-3 text-right font-semibold text-gray-700">
                                {amt.count || 0}
                              </td>
                              <td className="px-4 py-3 text-right">
                                <div className="flex items-center justify-end gap-1.5">
                                  <Button
                                    variant="outline"
                                    size="sm"
                                    onClick={() => {
                                      setExpMainEditId(cat.id);
                                      setExpMainForm({
                                        name: cat.name,
                                        description: cat.description || "",
                                      });
                                      setIsExpMainModalOpen(true);
                                    }}
                                    className="h-7 text-xs gap-1 border-indigo-200 text-indigo-700"
                                  >
                                    <Pencil className="w-3 h-3" /> Edit
                                  </Button>
                                  <Button
                                    variant="ghost"
                                    size="sm"
                                    onClick={() => deleteExpMainCat(cat.id)}
                                    className="h-7 text-xs text-rose-600 hover:bg-rose-50"
                                  >
                                    <Trash2 className="w-3.5 h-3.5" />
                                  </Button>
                                </div>
                              </td>
                            </tr>
                          );
                        })
                      )}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>
          ) : (
            <Card>
              <CardContent className="p-0">
                <div className="overflow-x-auto">
                  <table className="w-full text-sm text-left border-collapse">
                    <thead className="bg-gray-50/75 border-b text-xs font-semibold text-gray-500 uppercase">
                      <tr>
                        <th className="px-4 py-3">#ID</th>
                        <th className="px-4 py-3">Sub Category Name</th>
                        <th className="px-4 py-3">Main Category</th>
                        <th className="px-4 py-3">Description</th>
                        <th className="px-4 py-3 text-right">Total Amount (₹)</th>
                        <th className="px-4 py-3 text-right">Entries</th>
                        <th className="px-4 py-3 text-right">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">
                      {sortedExpSub.length === 0 ? (
                        <tr>
                          <td colSpan={7} className="text-center py-12 text-muted-foreground">
                            <FolderOpen className="w-8 h-8 mx-auto text-gray-300 mb-2" />
                            <p className="font-medium">No expense sub categories found</p>
                          </td>
                        </tr>
                      ) : (
                        sortedExpSub.map((sub) => {
                          const par = expMain.find((m) => m.id === sub.parent_id);
                          const amt = expAmounts.sub[String(sub.id)] || { total: 0, count: 0 };
                          return (
                            <tr key={sub.id} className="hover:bg-emerald-50/20 transition-colors">
                              <td className="px-4 py-3 font-mono text-xs text-muted-foreground">
                                #{sub.id}
                              </td>
                              <td className="px-4 py-3 font-bold text-gray-900">{sub.name}</td>
                              <td className="px-4 py-3">
                                <Badge variant="outline" className="bg-indigo-50 text-indigo-700">
                                  {par?.name || `Main #${sub.parent_id}`}
                                </Badge>
                              </td>
                              <td className="px-4 py-3 text-xs text-gray-600">{sub.description || "—"}</td>
                              <td className="px-4 py-3 text-right font-mono font-semibold text-rose-600">
                                {fmt(amt.total)}
                              </td>
                              <td className="px-4 py-3 text-right font-semibold text-gray-700">
                                {amt.count || 0}
                              </td>
                              <td className="px-4 py-3 text-right">
                                <div className="flex items-center justify-end gap-1.5">
                                  <Button
                                    variant="outline"
                                    size="sm"
                                    onClick={() => {
                                      setExpSubEditId(sub.id);
                                      setExpSubForm({
                                        parent_id: String(sub.parent_id),
                                        name: sub.name,
                                        description: sub.description || "",
                                      });
                                      setIsExpSubModalOpen(true);
                                    }}
                                    className="h-7 text-xs gap-1 border-emerald-200 text-emerald-700"
                                  >
                                    <Pencil className="w-3 h-3" /> Edit
                                  </Button>
                                  <Button
                                    variant="ghost"
                                    size="sm"
                                    onClick={() => deleteExpSubCat(sub.id)}
                                    className="h-7 text-xs text-rose-600 hover:bg-rose-50"
                                  >
                                    <Trash2 className="w-3.5 h-3.5" />
                                  </Button>
                                </div>
                              </td>
                            </tr>
                          );
                        })
                      )}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* ---------------------------------------------------- */}
        {/* TAB 8: INCOME HEADS */}
        {/* ---------------------------------------------------- */}
        <TabsContent value="income" className="space-y-4 m-0">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <Card className="p-3 bg-amber-50/50 border-amber-100 shadow-none">
              <div className="text-xs font-semibold text-amber-700">Main Categories</div>
              <div className="text-2xl font-black text-amber-900 mt-1">{incStats.main}</div>
            </Card>
            <Card className="p-3 bg-emerald-50/50 border-emerald-100 shadow-none">
              <div className="text-xs font-semibold text-emerald-700">Sub Categories</div>
              <div className="text-2xl font-black text-emerald-900 mt-1">{incStats.sub}</div>
            </Card>
            <Card className="p-3 bg-blue-50/50 border-blue-100 shadow-none">
              <div className="text-xs font-semibold text-blue-700 flex items-center gap-1">
                <IndianRupee className="w-3.5 h-3.5" /> Total Income
              </div>
              <div className="text-2xl font-black text-blue-600 mt-1">{fmt(incStats.totalAmt)}</div>
            </Card>
            <Card className="p-3 bg-purple-50/50 border-purple-100 shadow-none">
              <div className="text-xs font-semibold text-purple-700 flex items-center gap-1">
                <Receipt className="w-3.5 h-3.5" /> Total Entries
              </div>
              <div className="text-2xl font-black text-purple-900 mt-1">{incStats.totalEnt}</div>
            </Card>
          </div>

          <div className="flex flex-wrap items-center justify-between gap-3 bg-white p-3 rounded-lg border shadow-sm">
            <div className="flex items-center gap-2">
              <Button
                size="sm"
                variant={incInnerTab === "main" ? "default" : "outline"}
                onClick={() => setIncInnerTab("main")}
                className={incInnerTab === "main" ? "bg-amber-500 hover:bg-amber-600 text-white" : ""}
              >
                <Coins className="w-4 h-4 mr-1.5" /> Main Categories ({incMain.length})
              </Button>
              <Button
                size="sm"
                variant={incInnerTab === "sub" ? "default" : "outline"}
                onClick={() => setIncInnerTab("sub")}
                className={incInnerTab === "sub" ? "bg-emerald-600 hover:bg-emerald-700 text-white" : ""}
              >
                <FolderOpen className="w-4 h-4 mr-1.5" /> Sub Categories ({incSub.length})
              </Button>
            </div>

            <div className="flex items-center gap-2">
              <Select
                value={incFilterCo}
                onValueChange={(val) => {
                  setIncFilterCo(val);
                  loadIncomeCategories(val);
                }}
              >
                <SelectTrigger className="w-[150px] h-9">
                  <SelectValue placeholder="All Companies" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">All Companies</SelectItem>
                  {companies.map((c) => (
                    <SelectItem key={c.id} value={String(c.id)}>
                      {c.company_name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>

              <Select value={incSort} onValueChange={setIncSort}>
                <SelectTrigger className="w-[170px] h-9">
                  <SelectValue placeholder="Sort..." />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="name_asc">Name A → Z</SelectItem>
                  <SelectItem value="name_desc">Name Z → A</SelectItem>
                  <SelectItem value="amt_desc">Amount ↓ High</SelectItem>
                  <SelectItem value="amt_asc">Amount ↑ Low</SelectItem>
                  <SelectItem value="cnt_desc">Entries ↓ High</SelectItem>
                  <SelectItem value="cnt_asc">Entries ↑ Low</SelectItem>
                </SelectContent>
              </Select>

              {incInnerTab === "main" ? (
                <Button
                  size="sm"
                  onClick={() => {
                    setIncMainEditId(null);
                    setIncMainForm({ name: "", description: "" });
                    setIsIncMainModalOpen(true);
                  }}
                  className="bg-amber-500 hover:bg-amber-600 text-white h-9 gap-1"
                >
                  <Plus className="w-4 h-4" /> Add Main Category
                </Button>
              ) : (
                <Button
                  size="sm"
                  onClick={() => {
                    setIncSubEditId(null);
                    setIncSubForm({ parent_id: "", name: "", description: "" });
                    setIsIncSubModalOpen(true);
                  }}
                  className="bg-emerald-600 hover:bg-emerald-700 text-white h-9 gap-1"
                >
                  <Plus className="w-4 h-4" /> Add Sub Category
                </Button>
              )}
            </div>
          </div>

          {incInnerTab === "main" ? (
            <Card>
              <CardContent className="p-0">
                <div className="overflow-x-auto">
                  <table className="w-full text-sm text-left border-collapse">
                    <thead className="bg-gray-50/75 border-b text-xs font-semibold text-gray-500 uppercase">
                      <tr>
                        <th className="px-4 py-3">#ID</th>
                        <th className="px-4 py-3">Category Name</th>
                        <th className="px-4 py-3">Description</th>
                        <th className="px-4 py-3">Sub Categories</th>
                        <th className="px-4 py-3 text-right">Total Amount (₹)</th>
                        <th className="px-4 py-3 text-right">Entries</th>
                        <th className="px-4 py-3 text-right">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">
                      {sortedIncMain.length === 0 ? (
                        <tr>
                          <td colSpan={7} className="text-center py-12 text-muted-foreground">
                            <Coins className="w-8 h-8 mx-auto text-gray-300 mb-2" />
                            <p className="font-medium">No income main categories found</p>
                          </td>
                        </tr>
                      ) : (
                        sortedIncMain.map((cat) => {
                          const subs = incSub.filter((s) => s.parent_id === cat.id);
                          const amt = incAmounts.main[String(cat.id)] || { total: 0, count: 0 };
                          return (
                            <tr key={cat.id} className="hover:bg-amber-50/20 transition-colors">
                              <td className="px-4 py-3 font-mono text-xs text-muted-foreground">
                                #{cat.id}
                              </td>
                              <td className="px-4 py-3">
                                <div className="font-bold text-gray-900">{cat.name}</div>
                                {subs.length > 0 && (
                                  <div className="flex flex-wrap gap-1 mt-1">
                                    {subs.map((s) => (
                                      <Badge
                                        key={s.id}
                                        variant="secondary"
                                        className="text-[10px] bg-amber-50 text-amber-800"
                                      >
                                        {s.name}
                                      </Badge>
                                    ))}
                                  </div>
                                )}
                              </td>
                              <td className="px-4 py-3 text-xs text-gray-600">{cat.description || "—"}</td>
                              <td className="px-4 py-3">
                                <Badge variant="outline" className="bg-emerald-50 text-emerald-700">
                                  {subs.length} sub-categories
                                </Badge>
                              </td>
                              <td className="px-4 py-3 text-right font-mono font-semibold text-emerald-600">
                                {fmt(amt.total)}
                              </td>
                              <td className="px-4 py-3 text-right font-semibold text-gray-700">
                                {amt.count || 0}
                              </td>
                              <td className="px-4 py-3 text-right">
                                <div className="flex items-center justify-end gap-1.5">
                                  <Button
                                    variant="outline"
                                    size="sm"
                                    onClick={() => {
                                      setIncMainEditId(cat.id);
                                      setIncMainForm({
                                        name: cat.name,
                                        description: cat.description || "",
                                      });
                                      setIsIncMainModalOpen(true);
                                    }}
                                    className="h-7 text-xs gap-1 border-amber-200 text-amber-700"
                                  >
                                    <Pencil className="w-3 h-3" /> Edit
                                  </Button>
                                  <Button
                                    variant="ghost"
                                    size="sm"
                                    onClick={() => deleteIncMainCat(cat.id)}
                                    className="h-7 text-xs text-rose-600 hover:bg-rose-50"
                                  >
                                    <Trash2 className="w-3.5 h-3.5" />
                                  </Button>
                                </div>
                              </td>
                            </tr>
                          );
                        })
                      )}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>
          ) : (
            <Card>
              <CardContent className="p-0">
                <div className="overflow-x-auto">
                  <table className="w-full text-sm text-left border-collapse">
                    <thead className="bg-gray-50/75 border-b text-xs font-semibold text-gray-500 uppercase">
                      <tr>
                        <th className="px-4 py-3">#ID</th>
                        <th className="px-4 py-3">Sub Category Name</th>
                        <th className="px-4 py-3">Main Category</th>
                        <th className="px-4 py-3">Description</th>
                        <th className="px-4 py-3 text-right">Total Amount (₹)</th>
                        <th className="px-4 py-3 text-right">Entries</th>
                        <th className="px-4 py-3 text-right">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">
                      {sortedIncSub.length === 0 ? (
                        <tr>
                          <td colSpan={7} className="text-center py-12 text-muted-foreground">
                            <FolderOpen className="w-8 h-8 mx-auto text-gray-300 mb-2" />
                            <p className="font-medium">No income sub categories found</p>
                          </td>
                        </tr>
                      ) : (
                        sortedIncSub.map((sub) => {
                          const par = incMain.find((m) => m.id === sub.parent_id);
                          const amt = incAmounts.sub[String(sub.id)] || { total: 0, count: 0 };
                          return (
                            <tr key={sub.id} className="hover:bg-emerald-50/20 transition-colors">
                              <td className="px-4 py-3 font-mono text-xs text-muted-foreground">
                                #{sub.id}
                              </td>
                              <td className="px-4 py-3 font-bold text-gray-900">{sub.name}</td>
                              <td className="px-4 py-3">
                                <Badge variant="outline" className="bg-amber-50 text-amber-800">
                                  {par?.name || `Main #${sub.parent_id}`}
                                </Badge>
                              </td>
                              <td className="px-4 py-3 text-xs text-gray-600">{sub.description || "—"}</td>
                              <td className="px-4 py-3 text-right font-mono font-semibold text-emerald-600">
                                {fmt(amt.total)}
                              </td>
                              <td className="px-4 py-3 text-right font-semibold text-gray-700">
                                {amt.count || 0}
                              </td>
                              <td className="px-4 py-3 text-right">
                                <div className="flex items-center justify-end gap-1.5">
                                  <Button
                                    variant="outline"
                                    size="sm"
                                    onClick={() => {
                                      setIncSubEditId(sub.id);
                                      setIncSubForm({
                                        parent_id: String(sub.parent_id),
                                        name: sub.name,
                                        description: sub.description || "",
                                      });
                                      setIsIncSubModalOpen(true);
                                    }}
                                    className="h-7 text-xs gap-1 border-emerald-200 text-emerald-700"
                                  >
                                    <Pencil className="w-3 h-3" /> Edit
                                  </Button>
                                  <Button
                                    variant="ghost"
                                    size="sm"
                                    onClick={() => deleteIncSubCat(sub.id)}
                                    className="h-7 text-xs text-rose-600 hover:bg-rose-50"
                                  >
                                    <Trash2 className="w-3.5 h-3.5" />
                                  </Button>
                                </div>
                              </td>
                            </tr>
                          );
                        })
                      )}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>
      </Tabs>

      {/* ==================================================== */}
      {/* MODAL 1: COMPANY (Add / Edit / Transfer-Delete) */}
      {/* ==================================================== */}
      <Dialog open={isCoModalOpen} onOpenChange={setIsCoModalOpen}>
        <DialogContent className="max-w-xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-lg">
              <Building2 className="w-5 h-5 text-purple-600" />
              {coEditId ? "Edit Associated Company" : "Add New Company"}
            </DialogTitle>
          </DialogHeader>

          {showCoTransfer ? (
            <div className="space-y-4 py-2">
              <div className="p-4 bg-rose-50 border border-rose-200 rounded-lg flex items-start gap-3">
                <AlertTriangle className="w-5 h-5 text-rose-600 shrink-0 mt-0.5" />
                <div>
                  <h4 className="text-sm font-bold text-rose-800">
                    This company has associated financial &amp; operational data
                  </h4>
                  <p className="text-xs text-rose-700 mt-1">
                    Before deleting this company, transfer all its records to another active company.
                  </p>
                </div>
              </div>

              <div className="border rounded-lg overflow-hidden bg-gray-50">
                <div className="bg-gray-100 px-3 py-2 border-b text-xs font-semibold text-gray-600 uppercase">
                  Data Records to be Reassigned
                </div>
                <div className="divide-y divide-gray-200 p-2">
                  {coTransferSummary.map((item, idx) => (
                    <div key={idx} className="flex justify-between items-center py-2 px-2 text-xs">
                      <span className="font-medium text-gray-700">{item.label}</span>
                      <Badge variant="secondary" className="bg-blue-100 text-blue-800 font-bold">
                        {item.count.toLocaleString()}
                      </Badge>
                    </div>
                  ))}
                </div>
              </div>

              <div className="space-y-1.5">
                <Label className="text-xs font-semibold">Select Target Company *</Label>
                <Select value={coTransferTarget} onValueChange={setCoTransferTarget}>
                  <SelectTrigger>
                    <SelectValue placeholder="— Select Destination Company —" />
                  </SelectTrigger>
                  <SelectContent>
                    {companies
                      .filter((c) => c.id !== coEditId && c.is_active !== false)
                      .map((c) => (
                        <SelectItem key={c.id} value={String(c.id)}>
                          {c.company_name}
                        </SelectItem>
                      ))}
                  </SelectContent>
                </Select>
              </div>

              <DialogFooter className="flex justify-between items-center pt-3 border-t">
                <Button variant="outline" size="sm" onClick={() => setShowCoTransfer(false)}>
                  Back
                </Button>
                <Button
                  variant="destructive"
                  size="sm"
                  onClick={doTransferAndDelete}
                  disabled={coSaving || !coTransferTarget}
                  className="gap-1.5 bg-rose-600 hover:bg-rose-700"
                >
                  {coSaving && <Loader2 className="w-4 h-4 animate-spin" />}
                  Transfer &amp; Delete
                </Button>
              </DialogFooter>
            </div>
          ) : (
            <div className="space-y-4 py-2">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <Label className="text-xs font-semibold">
                    Company Name <span className="text-rose-500">*</span>
                  </Label>
                  <Input
                    placeholder="Full Legal Company Name"
                    value={coForm.company_name || ""}
                    onChange={(e) => setCoForm({ ...coForm, company_name: e.target.value })}
                  />
                </div>
                <div className="space-y-1.5">
                  <Label className="text-xs font-semibold">Short Code</Label>
                  <Input
                    placeholder="e.g. MRL"
                    value={coForm.company_code || ""}
                    disabled={!!coEditId}
                    onChange={(e) =>
                      setCoForm({ ...coForm, company_code: e.target.value.toUpperCase() })
                    }
                    className={coEditId ? "bg-gray-100 font-mono" : "font-mono"}
                  />
                  {coEditId && (
                    <span className="text-[10px] text-muted-foreground">Code is immutable after creation</span>
                  )}
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <Label className="text-xs font-semibold">Company Type</Label>
                  <Select
                    value={coForm.company_type || "SUBSIDIARY"}
                    onValueChange={(val) => setCoForm({ ...coForm, company_type: val })}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="MAIN">Main Company</SelectItem>
                      <SelectItem value="SUBSIDIARY">Subsidiary</SelectItem>
                      <SelectItem value="ASSOCIATE">Associate</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-1.5">
                  <Label className="text-xs font-semibold">Status</Label>
                  <Select
                    value={coForm.is_active !== false ? "true" : "false"}
                    onValueChange={(val) => setCoForm({ ...coForm, is_active: val === "true" })}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="true">Active</SelectItem>
                      <SelectItem value="false">Inactive</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div className="space-y-1.5">
                <Label className="text-xs font-semibold">Registered Address</Label>
                <Textarea
                  rows={2}
                  placeholder="Street, locality, building..."
                  value={coForm.address || ""}
                  onChange={(e) => setCoForm({ ...coForm, address: e.target.value })}
                />
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div className="space-y-1.5">
                  <Label className="text-xs font-semibold">City</Label>
                  <Input
                    value={coForm.city || ""}
                    onChange={(e) => setCoForm({ ...coForm, city: e.target.value })}
                  />
                </div>
                <div className="space-y-1.5">
                  <Label className="text-xs font-semibold">State</Label>
                  <Input
                    value={coForm.state || ""}
                    onChange={(e) => setCoForm({ ...coForm, state: e.target.value })}
                  />
                </div>
                <div className="space-y-1.5">
                  <Label className="text-xs font-semibold">Pincode</Label>
                  <Input
                    maxLength={10}
                    value={coForm.pincode || ""}
                    onChange={(e) => setCoForm({ ...coForm, pincode: e.target.value })}
                  />
                </div>
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div className="space-y-1.5">
                  <Label className="text-xs font-semibold">GSTIN</Label>
                  <Input
                    maxLength={15}
                    placeholder="15-digit GSTIN"
                    value={coForm.gst_number || ""}
                    onChange={(e) =>
                      setCoForm({ ...coForm, gst_number: e.target.value.toUpperCase() })
                    }
                    className="font-mono text-xs uppercase"
                  />
                </div>
                <div className="space-y-1.5">
                  <Label className="text-xs font-semibold">PAN</Label>
                  <Input
                    maxLength={10}
                    placeholder="PAN Number"
                    value={coForm.pan_number || ""}
                    onChange={(e) =>
                      setCoForm({ ...coForm, pan_number: e.target.value.toUpperCase() })
                    }
                    className="font-mono text-xs uppercase"
                  />
                </div>
                <div className="space-y-1.5">
                  <Label className="text-xs font-semibold">CIN</Label>
                  <Input
                    maxLength={25}
                    placeholder="CIN Number"
                    value={coForm.cin_number || ""}
                    onChange={(e) => setCoForm({ ...coForm, cin_number: e.target.value })}
                    className="font-mono text-xs"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <Label className="text-xs font-semibold">Official Phone</Label>
                  <Input
                    placeholder="+91..."
                    value={coForm.phone || ""}
                    onChange={(e) => setCoForm({ ...coForm, phone: e.target.value })}
                  />
                </div>
                <div className="space-y-1.5">
                  <Label className="text-xs font-semibold">Official Email</Label>
                  <Input
                    placeholder="accounts@company.com"
                    value={coForm.email || ""}
                    onChange={(e) => setCoForm({ ...coForm, email: e.target.value })}
                  />
                </div>
              </div>

              <div className="flex items-center space-x-2 pt-2">
                <Checkbox
                  id="co_marketplace"
                  checked={!!coForm.is_marketplace_endpoint}
                  onCheckedChange={(checked) =>
                    setCoForm({ ...coForm, is_marketplace_endpoint: !!checked })
                  }
                />
                <label
                  htmlFor="co_marketplace"
                  className="text-xs font-semibold text-gray-800 cursor-pointer"
                >
                  Designate as Marketplace Endpoint{" "}
                  <span className="text-purple-600 font-normal">
                    (sells marketplace products directly to customers)
                  </span>
                </label>
              </div>

              <DialogFooter className="flex justify-between items-center pt-3 border-t">
                {coEditId ? (
                  <Button
                    type="button"
                    variant="destructive"
                    size="sm"
                    onClick={checkDeleteCompany}
                    className="gap-1 bg-rose-600 hover:bg-rose-700"
                  >
                    <Trash2 className="w-3.5 h-3.5" /> Delete
                  </Button>
                ) : (
                  <div />
                )}
                <div className="flex gap-2">
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => setIsCoModalOpen(false)}
                  >
                    Cancel
                  </Button>
                  <Button
                    type="button"
                    size="sm"
                    onClick={saveCompany}
                    disabled={coSaving}
                    className="bg-purple-600 hover:bg-purple-700 text-white gap-1.5"
                  >
                    {coSaving && <Loader2 className="w-4 h-4 animate-spin" />}
                    Save Company
                  </Button>
                </div>
              </DialogFooter>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* ==================================================== */}
      {/* MODAL 2: VENDOR (Add / Edit / Multi-Tabs) */}
      {/* ==================================================== */}
      <Dialog open={isVndModalOpen} onOpenChange={setIsVndModalOpen}>
        <DialogContent className="max-w-3xl max-h-[92vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-lg">
              <Truck className="w-5 h-5 text-amber-600" />
              {vndEditId ? "Edit Vendor Master" : "Add Vendor Master"}
            </DialogTitle>
          </DialogHeader>

          <Tabs value={vndModalTab} onValueChange={setVndModalTab} className="w-full mt-2">
            <TabsList className="grid grid-cols-5 w-full bg-gray-100">
              <TabsTrigger value="basic" className="text-xs font-semibold">
                Basic Info
              </TabsTrigger>
              <TabsTrigger value="contacts" className="text-xs font-semibold">
                Contacts
              </TabsTrigger>
              <TabsTrigger value="address" className="text-xs font-semibold">
                Address
              </TabsTrigger>
              <TabsTrigger value="bank" className="text-xs font-semibold">
                Bank &amp; Terms
              </TabsTrigger>
              <TabsTrigger value="products" className="text-xs font-semibold">
                Products ({vndSelectedProducts.length})
              </TabsTrigger>
            </TabsList>

            {/* TAB: Basic Info */}
            <TabsContent value="basic" className="space-y-3.5 pt-3">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <Label className="text-xs font-semibold">
                    Vendor Legal Name <span className="text-rose-500">*</span>
                  </Label>
                  <Input
                    placeholder="Full registered entity name"
                    value={vndForm.vendor_name || ""}
                    onChange={(e) => setVndForm({ ...vndForm, vendor_name: e.target.value })}
                  />
                </div>
                <div className="space-y-1.5">
                  <Label className="text-xs font-semibold">
                    Vendor Code <span className="text-rose-500">*</span>
                  </Label>
                  <Input
                    placeholder="e.g. VND001"
                    value={vndForm.vendor_code || ""}
                    disabled={!!vndEditId}
                    onChange={(e) =>
                      setVndForm({ ...vndForm, vendor_code: e.target.value.toUpperCase() })
                    }
                    className="font-mono uppercase"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                <div className="space-y-1.5">
                  <Label className="text-xs font-semibold">Vendor Type</Label>
                  <Select
                    value={vndForm.vendor_type || "BOTH"}
                    onValueChange={(val) => setVndForm({ ...vndForm, vendor_type: val })}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="BOTH">Both (Product &amp; Service)</SelectItem>
                      <SelectItem value="PRODUCT">Product Only</SelectItem>
                      <SelectItem value="SERVICE">Service Only</SelectItem>
                      <SelectItem value="SOLAR">Solar Supplier</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-1.5">
                  <Label className="text-xs font-semibold">Trade Name (Brand)</Label>
                  <Input
                    placeholder="DBA / Brand name"
                    value={vndForm.trade_name || ""}
                    onChange={(e) => setVndForm({ ...vndForm, trade_name: e.target.value })}
                  />
                </div>
                <div className="space-y-1.5">
                  <Label className="text-xs font-semibold">Status</Label>
                  <Select
                    value={vndForm.is_active !== false ? "true" : "false"}
                    onValueChange={(val) => setVndForm({ ...vndForm, is_active: val === "true" })}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="true">Active</SelectItem>
                      <SelectItem value="false">Inactive</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <Label className="text-xs font-semibold">GSTIN</Label>
                  <Input
                    maxLength={15}
                    placeholder="15-character GSTIN"
                    value={vndForm.gst_number || ""}
                    onChange={(e) =>
                      setVndForm({ ...vndForm, gst_number: e.target.value.toUpperCase() })
                    }
                    className="font-mono uppercase"
                  />
                </div>
                <div className="space-y-1.5">
                  <Label className="text-xs font-semibold">PAN Number</Label>
                  <Input
                    maxLength={10}
                    placeholder="10-character PAN"
                    value={vndForm.pan_number || ""}
                    onChange={(e) =>
                      setVndForm({ ...vndForm, pan_number: e.target.value.toUpperCase() })
                    }
                    className="font-mono uppercase"
                  />
                </div>
              </div>

              {/* GST Treatment Radio Cards */}
              <div className="space-y-1.5">
                <Label className="text-xs font-semibold">GST Treatment (Tax Split)</Label>
                <div className="grid grid-cols-2 gap-3">
                  <div
                    onClick={() => setVndForm({ ...vndForm, gst_type: "CGST_SGST" })}
                    className={`p-3 rounded-lg border-2 cursor-pointer transition-all ${
                      vndForm.gst_type === "CGST_SGST"
                        ? "border-blue-500 bg-blue-50/50"
                        : "border-gray-200 hover:border-gray-300"
                    }`}
                  >
                    <div className="font-bold text-xs text-blue-700">CGST + SGST</div>
                    <div className="text-[11px] text-gray-500 mt-0.5">Intra-State supply within same state</div>
                  </div>
                  <div
                    onClick={() => setVndForm({ ...vndForm, gst_type: "IGST" })}
                    className={`p-3 rounded-lg border-2 cursor-pointer transition-all ${
                      vndForm.gst_type === "IGST"
                        ? "border-amber-500 bg-amber-50/50"
                        : "border-gray-200 hover:border-gray-300"
                    }`}
                  >
                    <div className="font-bold text-xs text-amber-700">IGST</div>
                    <div className="text-[11px] text-gray-500 mt-0.5">Inter-State supply / Import</div>
                  </div>
                </div>
              </div>

              {/* Applicable Companies Multi-Badge */}
              <div className="space-y-2 pt-2 border-t">
                <Label className="text-xs font-semibold flex items-center gap-1.5">
                  <Building2 className="w-3.5 h-3.5 text-amber-600" /> Applicable Companies
                </Label>
                <div className="flex flex-wrap gap-2 items-center">
                  <Select
                    value=""
                    onValueChange={(val) => {
                      if (!val) return;
                      const cid = parseInt(val);
                      if (!vndApplicableCos.includes(cid)) {
                        setVndApplicableCos([...vndApplicableCos, cid]);
                      }
                    }}
                  >
                    <SelectTrigger className="w-[200px] h-8 text-xs">
                      <SelectValue placeholder="+ Add Company Access" />
                    </SelectTrigger>
                    <SelectContent>
                      {companies.map((c) => (
                        <SelectItem key={c.id} value={String(c.id)}>
                          {c.company_name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>

                  {vndApplicableCos.map((cid) => {
                    const co = companies.find((c) => c.id === cid);
                    return (
                      <Badge
                        key={cid}
                        className="bg-amber-100 text-amber-800 border-amber-200 flex items-center gap-1 py-1"
                      >
                        {co?.company_name || `Company #${cid}`}
                        <button
                          type="button"
                          onClick={() => setVndApplicableCos(vndApplicableCos.filter((x) => x !== cid))}
                          className="hover:text-rose-600 rounded-full"
                        >
                          <X className="w-3 h-3" />
                        </button>
                      </Badge>
                    );
                  })}
                </div>
              </div>

              {/* Opening Balance Widget */}
              <div className="space-y-2 pt-2 border-t">
                <div className="flex items-center justify-between">
                  <Label className="text-xs font-semibold flex items-center gap-1.5">
                    <Scale className="w-3.5 h-3.5 text-amber-600" /> Opening Balances (Per Company)
                  </Label>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() =>
                      setVndObRows([
                        ...vndObRows,
                        {
                          company_id: vndApplicableCos[0] || null,
                          amount: 0,
                          type: "CREDIT",
                          date: new Date().toISOString().slice(0, 10),
                        },
                      ])
                    }
                    className="h-7 text-xs gap-1 border-dashed"
                  >
                    <Plus className="w-3 h-3" /> Add Balance Row
                  </Button>
                </div>

                {vndObRows.length === 0 ? (
                  <div className="text-xs text-muted-foreground italic bg-gray-50 p-2.5 rounded border">
                    No opening balance rows set. Click Add Balance Row above if required.
                  </div>
                ) : (
                  <div className="space-y-2">
                    {vndObRows.map((row, idx) => (
                      <div
                        key={idx}
                        className="grid grid-cols-12 gap-2 items-center bg-gray-50 p-2 rounded-lg border text-xs"
                      >
                        <div className="col-span-4">
                          <Select
                            value={row.company_id ? String(row.company_id) : ""}
                            onValueChange={(val) => {
                              const copy = [...vndObRows];
                              copy[idx].company_id = val ? parseInt(val) : null;
                              setVndObRows(copy);
                            }}
                          >
                            <SelectTrigger className="h-8 text-xs bg-white">
                              <SelectValue placeholder="All Companies" />
                            </SelectTrigger>
                            <SelectContent>
                              {companies.map((c) => (
                                <SelectItem key={c.id} value={String(c.id)}>
                                  {c.company_name}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </div>
                        <div className="col-span-3">
                          <Input
                            type="number"
                            step="0.01"
                            placeholder="Amount (₹)"
                            value={row.amount || ""}
                            onChange={(e) => {
                              const copy = [...vndObRows];
                              copy[idx].amount = parseFloat(e.target.value) || 0;
                              setVndObRows(copy);
                            }}
                            className="h-8 text-xs bg-white"
                          />
                        </div>
                        <div className="col-span-2">
                          <Select
                            value={row.type}
                            onValueChange={(val: any) => {
                              const copy = [...vndObRows];
                              copy[idx].type = val;
                              setVndObRows(copy);
                            }}
                          >
                            <SelectTrigger className="h-8 text-xs bg-white">
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="CREDIT">CR (Payable)</SelectItem>
                              <SelectItem value="DEBIT">DR (Receivable)</SelectItem>
                            </SelectContent>
                          </Select>
                        </div>
                        <div className="col-span-2">
                          <Input
                            type="date"
                            value={row.date || ""}
                            onChange={(e) => {
                              const copy = [...vndObRows];
                              copy[idx].date = e.target.value || null;
                              setVndObRows(copy);
                            }}
                            className="h-8 text-xs bg-white"
                          />
                        </div>
                        <div className="col-span-1 text-right">
                          <Button
                            type="button"
                            variant="ghost"
                            size="sm"
                            onClick={() => setVndObRows(vndObRows.filter((_, i) => i !== idx))}
                            className="h-8 w-8 p-0 text-rose-500 hover:bg-rose-50"
                          >
                            <X className="w-4 h-4" />
                          </Button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </TabsContent>

            {/* TAB: Contacts */}
            <TabsContent value="contacts" className="space-y-4 pt-3">
              <div className="p-3 bg-gray-50 rounded-lg border space-y-3">
                <div className="text-xs font-bold text-gray-800 flex items-center gap-1.5">
                  <UserCheck className="w-3.5 h-3.5 text-amber-600" /> Primary Contact Person
                </div>
                <div className="grid grid-cols-3 gap-3">
                  <div className="space-y-1">
                    <Label className="text-[11px]">Full Name</Label>
                    <Input
                      placeholder="Contact name"
                      value={vndForm.contact_person_1_name || ""}
                      onChange={(e) => setVndForm({ ...vndForm, contact_person_1_name: e.target.value })}
                      className="bg-white"
                    />
                  </div>
                  <div className="space-y-1">
                    <Label className="text-[11px]">Phone / Mobile</Label>
                    <Input
                      placeholder="+91..."
                      value={vndForm.contact_person_1_phone || ""}
                      onChange={(e) => setVndForm({ ...vndForm, contact_person_1_phone: e.target.value })}
                      className="bg-white"
                    />
                  </div>
                  <div className="space-y-1">
                    <Label className="text-[11px]">Designation</Label>
                    <Input
                      placeholder="e.g. Sales Manager"
                      value={vndForm.contact_person_1_designation || ""}
                      onChange={(e) =>
                        setVndForm({ ...vndForm, contact_person_1_designation: e.target.value })
                      }
                      className="bg-white"
                    />
                  </div>
                </div>
              </div>

              <div className="p-3 bg-gray-50 rounded-lg border space-y-3">
                <div className="text-xs font-bold text-gray-800 flex items-center gap-1.5">
                  <Users className="w-3.5 h-3.5 text-amber-600" /> Secondary Contact Person
                </div>
                <div className="grid grid-cols-3 gap-3">
                  <div className="space-y-1">
                    <Label className="text-[11px]">Full Name</Label>
                    <Input
                      placeholder="Contact name"
                      value={vndForm.contact_person_2_name || ""}
                      onChange={(e) => setVndForm({ ...vndForm, contact_person_2_name: e.target.value })}
                      className="bg-white"
                    />
                  </div>
                  <div className="space-y-1">
                    <Label className="text-[11px]">Phone / Mobile</Label>
                    <Input
                      placeholder="+91..."
                      value={vndForm.contact_person_2_phone || ""}
                      onChange={(e) => setVndForm({ ...vndForm, contact_person_2_phone: e.target.value })}
                      className="bg-white"
                    />
                  </div>
                  <div className="space-y-1">
                    <Label className="text-[11px]">Designation</Label>
                    <Input
                      placeholder="e.g. Accounts Manager"
                      value={vndForm.contact_person_2_designation || ""}
                      onChange={(e) =>
                        setVndForm({ ...vndForm, contact_person_2_designation: e.target.value })
                      }
                      className="bg-white"
                    />
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <Label className="text-xs font-semibold">Vendor Email</Label>
                  <Input
                    type="email"
                    placeholder="sales@vendor.com"
                    value={vndForm.email || ""}
                    onChange={(e) => setVndForm({ ...vndForm, email: e.target.value })}
                  />
                </div>
                <div className="space-y-1.5">
                  <Label className="text-xs font-semibold">Website URL</Label>
                  <Input
                    placeholder="https://www.vendor.com"
                    value={vndForm.website_url || ""}
                    onChange={(e) => setVndForm({ ...vndForm, website_url: e.target.value })}
                  />
                </div>
              </div>
            </TabsContent>

            {/* TAB: Address */}
            <TabsContent value="address" className="space-y-4 pt-3">
              <div className="p-3 bg-gray-50 rounded-lg border space-y-3">
                <div className="text-xs font-bold text-gray-800 flex items-center gap-1.5">
                  <MapPin className="w-3.5 h-3.5 text-amber-600" /> Primary / Billing Address
                </div>
                <Textarea
                  rows={2}
                  placeholder="Street address, building, premises..."
                  value={vndForm.address || ""}
                  onChange={(e) => setVndForm({ ...vndForm, address: e.target.value })}
                  className="bg-white"
                />
                <div className="grid grid-cols-3 gap-3">
                  <div className="space-y-1">
                    <Label className="text-[11px]">Pincode (Auto-lookup)</Label>
                    <Input
                      maxLength={6}
                      placeholder="6-digit PIN"
                      value={vndForm.pincode || ""}
                      onChange={(e) => {
                        const val = e.target.value;
                        setVndForm({ ...vndForm, pincode: val });
                        if (val.length === 6) handlePincodeLookup(val, false);
                      }}
                      className="bg-white font-mono"
                    />
                  </div>
                  <div className="space-y-1">
                    <Label className="text-[11px]">City</Label>
                    <Input
                      placeholder="City"
                      value={vndForm.city || ""}
                      onChange={(e) => setVndForm({ ...vndForm, city: e.target.value })}
                      className="bg-white"
                    />
                  </div>
                  <div className="space-y-1">
                    <Label className="text-[11px]">State</Label>
                    <Input
                      placeholder="State"
                      value={vndForm.state || ""}
                      onChange={(e) => setVndForm({ ...vndForm, state: e.target.value })}
                      className="bg-white"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3 pt-2">
                  <div className="space-y-1">
                    <Label className="text-[11px]">Google Map Link 1</Label>
                    <Input
                      placeholder="Map URL (e.g. Office)"
                      value={vndForm.map_link_1 || ""}
                      onChange={(e) => setVndForm({ ...vndForm, map_link_1: e.target.value })}
                      className="bg-white text-xs"
                    />
                  </div>
                  <div className="space-y-1">
                    <Label className="text-[11px]">Google Map Link 2</Label>
                    <Input
                      placeholder="Map URL (e.g. Factory / Yard)"
                      value={vndForm.map_link_2 || ""}
                      onChange={(e) => setVndForm({ ...vndForm, map_link_2: e.target.value })}
                      className="bg-white text-xs"
                    />
                  </div>
                </div>
              </div>

              <div className="p-3 bg-gray-50 rounded-lg border space-y-3">
                <div className="text-xs font-bold text-gray-800 flex items-center gap-1.5">
                  <Truck className="w-3.5 h-3.5 text-amber-600" /> Shipping / Dispatch Address (If Different)
                </div>
                <Textarea
                  rows={2}
                  placeholder="Dispatch address..."
                  value={vndForm.ship_to_address || ""}
                  onChange={(e) => setVndForm({ ...vndForm, ship_to_address: e.target.value })}
                  className="bg-white"
                />
                <div className="grid grid-cols-3 gap-3">
                  <div className="space-y-1">
                    <Label className="text-[11px]">Pincode</Label>
                    <Input
                      maxLength={6}
                      placeholder="6-digit PIN"
                      value={vndForm.ship_to_pincode || ""}
                      onChange={(e) => {
                        const val = e.target.value;
                        setVndForm({ ...vndForm, ship_to_pincode: val });
                        if (val.length === 6) handlePincodeLookup(val, true);
                      }}
                      className="bg-white font-mono"
                    />
                  </div>
                  <div className="space-y-1">
                    <Label className="text-[11px]">City</Label>
                    <Input
                      placeholder="City"
                      value={vndForm.ship_to_city || ""}
                      onChange={(e) => setVndForm({ ...vndForm, ship_to_city: e.target.value })}
                      className="bg-white"
                    />
                  </div>
                  <div className="space-y-1">
                    <Label className="text-[11px]">State</Label>
                    <Input
                      placeholder="State"
                      value={vndForm.ship_to_state || ""}
                      onChange={(e) => setVndForm({ ...vndForm, ship_to_state: e.target.value })}
                      className="bg-white"
                    />
                  </div>
                </div>
              </div>
            </TabsContent>

            {/* TAB: Bank & Terms */}
            <TabsContent value="bank" className="space-y-4 pt-3">
              <div className="p-3 bg-gray-50 rounded-lg border space-y-3">
                <div className="text-xs font-bold text-gray-800 flex items-center gap-1.5">
                  <Landmark className="w-3.5 h-3.5 text-amber-600" /> Bank Account Details
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1">
                    <Label className="text-[11px]">Bank Name</Label>
                    <Input
                      placeholder="e.g. HDFC Bank"
                      value={vndForm.bank_name || ""}
                      onChange={(e) => setVndForm({ ...vndForm, bank_name: e.target.value })}
                      className="bg-white"
                    />
                  </div>
                  <div className="space-y-1">
                    <Label className="text-[11px]">Branch</Label>
                    <Input
                      placeholder="Branch name"
                      value={vndForm.bank_branch || ""}
                      onChange={(e) => setVndForm({ ...vndForm, bank_branch: e.target.value })}
                      className="bg-white"
                    />
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1">
                    <Label className="text-[11px]">Account Number</Label>
                    <Input
                      placeholder="Account number"
                      value={vndForm.account_number || ""}
                      onChange={(e) => setVndForm({ ...vndForm, account_number: e.target.value })}
                      className="bg-white font-mono"
                    />
                  </div>
                  <div className="space-y-1">
                    <Label className="text-[11px]">IFSC Code</Label>
                    <Input
                      maxLength={11}
                      placeholder="11-digit IFSC"
                      value={vndForm.ifsc_code || ""}
                      onChange={(e) =>
                        setVndForm({ ...vndForm, ifsc_code: e.target.value.toUpperCase() })
                      }
                      className="bg-white font-mono uppercase"
                    />
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1">
                    <Label className="text-[11px]">Account Holder Name</Label>
                    <Input
                      placeholder="Name as per bank passbook"
                      value={vndForm.account_holder_name || ""}
                      onChange={(e) =>
                        setVndForm({ ...vndForm, account_holder_name: e.target.value })
                      }
                      className="bg-white"
                    />
                  </div>
                  <div className="space-y-1">
                    <Label className="text-[11px]">UPI ID</Label>
                    <Input
                      placeholder="e.g. vendor@okhdfcbank"
                      value={vndForm.upi_id || ""}
                      onChange={(e) => setVndForm({ ...vndForm, upi_id: e.target.value })}
                      className="bg-white font-mono"
                    />
                  </div>
                </div>
              </div>

              {/* QR Upload */}
              <div className="p-3 bg-gray-50 rounded-lg border space-y-2">
                <div className="text-xs font-bold text-gray-800 flex items-center gap-1.5">
                  <QrCode className="w-3.5 h-3.5 text-amber-600" /> Payment QR Code Scanner
                </div>
                <Input
                  type="file"
                  accept="image/*"
                  onChange={(e) => {
                    const f = e.target.files?.[0];
                    if (f) {
                      setVndQrFile(f);
                      setVndQrPreview(URL.createObjectURL(f));
                    }
                  }}
                  className="bg-white"
                />
                {vndQrPreview && (
                  <div className="pt-2 flex items-center gap-3">
                    <img
                      src={vndQrPreview}
                      alt="Vendor QR"
                      className="w-24 h-24 object-contain rounded border bg-white shadow-sm"
                    />
                    <span className="text-xs text-muted-foreground">Current / Uploaded QR file preview</span>
                  </div>
                )}
              </div>

              {/* Terms */}
              <div className="grid grid-cols-3 gap-3">
                <div className="space-y-1.5">
                  <Label className="text-xs font-semibold">Payment Terms</Label>
                  <Select
                    value={vndForm.payment_terms || "COD"}
                    onValueChange={(val) => setVndForm({ ...vndForm, payment_terms: val })}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="COD">Cash on Delivery</SelectItem>
                      <SelectItem value="ADVANCE">100% Advance</SelectItem>
                      <SelectItem value="CREDIT_15">15 Days Credit</SelectItem>
                      <SelectItem value="CREDIT_30">30 Days Credit</SelectItem>
                      <SelectItem value="CREDIT_45">45 Days Credit</SelectItem>
                      <SelectItem value="CREDIT_60">60 Days Credit</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-1.5">
                  <Label className="text-xs font-semibold">Credit Limit (₹)</Label>
                  <Input
                    type="number"
                    min="0"
                    value={vndForm.credit_limit || 0}
                    onChange={(e) => setVndForm({ ...vndForm, credit_limit: parseFloat(e.target.value) || 0 })}
                  />
                </div>
                <div className="space-y-1.5">
                  <Label className="text-xs font-semibold">Credit Days</Label>
                  <Input
                    type="number"
                    min="0"
                    max="365"
                    value={vndForm.credit_days || 0}
                    onChange={(e) => setVndForm({ ...vndForm, credit_days: parseInt(e.target.value) || 0 })}
                  />
                </div>
              </div>

              <div className="space-y-1.5">
                <Label className="text-xs font-semibold">Custom Terms &amp; Conditions</Label>
                <Textarea
                  rows={2}
                  placeholder="Special discounts, delivery SLAs, warranty terms..."
                  value={vndForm.terms_conditions || ""}
                  onChange={(e) => setVndForm({ ...vndForm, terms_conditions: e.target.value })}
                />
              </div>
            </TabsContent>

            {/* TAB: Products */}
            <TabsContent value="products" className="space-y-3.5 pt-3">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                <p className="text-xs text-muted-foreground">
                  Map the stock items and products supplied by this vendor.
                </p>
                {vndEditId && (
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={loadVndPurchaseHistory}
                    disabled={vndHistLoading}
                    className="h-8 gap-1.5 text-xs text-amber-700 border-amber-300 hover:bg-amber-50"
                  >
                    {vndHistLoading ? (
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    ) : (
                      <History className="w-3.5 h-3.5" />
                    )}
                    Load from Purchase History
                  </Button>
                )}
              </div>

              {/* Search products bar */}
              <div className="relative">
                <Search className="w-4 h-4 absolute left-3 top-3 text-muted-foreground" />
                <Input
                  placeholder="Search products by code or name..."
                  value={vndProductSearchTerm}
                  onChange={(e) => searchVndProducts(e.target.value)}
                  className="pl-9"
                />
              </div>

              {/* Selected items box */}
              {vndSelectedProducts.length > 0 && (
                <div className="p-2.5 bg-emerald-50/50 border border-emerald-200 rounded-lg space-y-1.5">
                  <div className="text-xs font-bold text-emerald-800 flex items-center justify-between">
                    <span>Selected Products ({vndSelectedProducts.length})</span>
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={() => setVndSelectedProducts([])}
                      className="h-6 text-[10px] text-emerald-700 hover:bg-emerald-100"
                    >
                      Clear All
                    </Button>
                  </div>
                  <div className="flex flex-wrap gap-1.5 max-h-28 overflow-y-auto p-1">
                    {vndSelectedProducts.map((p) => (
                      <Badge
                        key={p.id}
                        variant="secondary"
                        className="bg-white border text-gray-800 flex items-center gap-1 text-xs py-1"
                      >
                        <span className="font-mono text-amber-700 font-bold">{p.item_code}</span> — {p.item_name}
                        <button
                          type="button"
                          onClick={() => toggleVndProduct(p)}
                          className="hover:text-rose-500"
                        >
                          <X className="w-3 h-3" />
                        </button>
                      </Badge>
                    ))}
                  </div>
                </div>
              )}

              {/* Search Results List */}
              <div className="border rounded-lg max-h-48 overflow-y-auto divide-y bg-white">
                {vndSearchingProducts ? (
                  <div className="p-4 text-center text-xs text-muted-foreground">
                    <Loader2 className="w-4 h-4 animate-spin mx-auto mb-1 text-amber-500" />
                    Searching stock catalog...
                  </div>
                ) : vndProductSearchResults.length === 0 ? (
                  <div className="p-4 text-center text-xs text-muted-foreground">
                    {vndProductSearchTerm.length >= 2
                      ? "No stock items matched your query"
                      : "Type at least 2 characters to search inventory catalog"}
                  </div>
                ) : (
                  vndProductSearchResults.map((prod) => {
                    const isSelected = vndSelectedProducts.some((p) => p.id === prod.id);
                    return (
                      <div
                        key={prod.id}
                        onClick={() => toggleVndProduct(prod)}
                        className={`p-2.5 flex items-center justify-between text-xs cursor-pointer hover:bg-amber-50/50 transition-colors ${
                          isSelected ? "bg-amber-50/80 font-semibold" : ""
                        }`}
                      >
                        <div className="flex items-center gap-2">
                          <Checkbox checked={isSelected} />
                          <span className="font-mono text-amber-700 font-bold">{prod.item_code}</span>
                          <span className="text-gray-800">{prod.item_name}</span>
                        </div>
                        {isSelected && <Badge variant="outline" className="text-[10px] bg-emerald-100 text-emerald-800">Added</Badge>}
                      </div>
                    );
                  })
                )}
              </div>
            </TabsContent>
          </Tabs>

          <DialogFooter className="flex justify-between items-center pt-3 border-t">
            {vndEditId ? (
              <Button
                type="button"
                variant="destructive"
                size="sm"
                onClick={deactivateVendor}
                className="gap-1 bg-rose-600 hover:bg-rose-700"
              >
                <Trash2 className="w-3.5 h-3.5" /> Deactivate
              </Button>
            ) : (
              <div />
            )}
            <div className="flex gap-2">
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => setIsVndModalOpen(false)}
              >
                Cancel
              </Button>
              <Button
                type="button"
                size="sm"
                onClick={saveVendor}
                disabled={vndSaving}
                className="bg-amber-500 hover:bg-amber-600 text-white gap-1.5"
              >
                {vndSaving && <Loader2 className="w-4 h-4 animate-spin" />}
                Save Vendor
              </Button>
            </div>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* ==================================================== */}
      {/* MODAL 3: PARTNER (Add / Edit / Multi-Tabs) */}
      {/* ==================================================== */}
      <Dialog open={isPrtModalOpen} onOpenChange={setIsPrtModalOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-lg">
              <Handshake className="w-5 h-5 text-emerald-600" />
              {prtEditId ? "Edit Official Partner" : "Add Official Partner"}
            </DialogTitle>
          </DialogHeader>

          <Tabs value={prtModalTab} onValueChange={setPrtModalTab} className="w-full mt-2">
            <TabsList className="grid grid-cols-4 w-full bg-gray-100">
              <TabsTrigger value="basic" className="text-xs font-semibold">
                Basic Info
              </TabsTrigger>
              <TabsTrigger value="contacts" className="text-xs font-semibold">
                Contacts
              </TabsTrigger>
              <TabsTrigger value="address" className="text-xs font-semibold">
                Address
              </TabsTrigger>
              <TabsTrigger value="bank" className="text-xs font-semibold">
                Bank &amp; Credit
              </TabsTrigger>
            </TabsList>

            <TabsContent value="basic" className="space-y-3.5 pt-3">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <Label className="text-xs font-semibold">
                    Partner Name <span className="text-rose-500">*</span>
                  </Label>
                  <Input
                    placeholder="Full partner name"
                    value={prtForm.name || ""}
                    onChange={(e) => setPrtForm({ ...prtForm, name: e.target.value })}
                  />
                </div>
                <div className="space-y-1.5">
                  <Label className="text-xs font-semibold">Partner Code</Label>
                  <Input
                    placeholder="Auto-generated if empty"
                    value={prtForm.code || ""}
                    onChange={(e) =>
                      setPrtForm({ ...prtForm, code: e.target.value.toUpperCase() })
                    }
                    className="font-mono uppercase"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <Label className="text-xs font-semibold">
                    Category <span className="text-rose-500">*</span>
                  </Label>
                  <Select
                    value={prtForm.category || "DEALER"}
                    onValueChange={(val) => setPrtForm({ ...prtForm, category: val })}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="DEALER">Dealer</SelectItem>
                      <SelectItem value="DISTRIBUTOR">Distributor</SelectItem>
                      <SelectItem value="SERVICE_CENTER">Service Center</SelectItem>
                      <SelectItem value="VENDOR">Vendor</SelectItem>
                      <SelectItem value="REAL_DREAM_PARTNER">Real Dreams Partner</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-1.5">
                  <Label className="text-xs font-semibold">Status</Label>
                  <Select
                    value={prtForm.is_active ? "true" : "false"}
                    onValueChange={(val) => setPrtForm({ ...prtForm, is_active: val === "true" })}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="true">Active</SelectItem>
                      <SelectItem value="false">Inactive</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <Label className="text-xs font-semibold">GSTIN</Label>
                  <Input
                    maxLength={15}
                    placeholder="15-character GSTIN"
                    value={prtForm.gst || ""}
                    onChange={(e) =>
                      setPrtForm({ ...prtForm, gst: e.target.value.toUpperCase() })
                    }
                    className="font-mono uppercase"
                  />
                </div>
                <div className="space-y-1.5">
                  <Label className="text-xs font-semibold">PAN Number</Label>
                  <Input
                    maxLength={10}
                    placeholder="10-character PAN"
                    value={prtForm.pan || ""}
                    onChange={(e) =>
                      setPrtForm({ ...prtForm, pan: e.target.value.toUpperCase() })
                    }
                    className="font-mono uppercase"
                  />
                </div>
              </div>

              {/* Opening Balance Widget */}
              <div className="space-y-2 pt-2 border-t">
                <div className="flex items-center justify-between">
                  <Label className="text-xs font-semibold flex items-center gap-1.5">
                    <Scale className="w-3.5 h-3.5 text-emerald-600" /> Opening Balances
                  </Label>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() =>
                      setPrtObRows([
                        ...prtObRows,
                        {
                          company_id: null,
                          amount: 0,
                          type: "CREDIT",
                          date: new Date().toISOString().slice(0, 10),
                        },
                      ])
                    }
                    className="h-7 text-xs gap-1 border-dashed"
                  >
                    <Plus className="w-3 h-3" /> Add Balance Row
                  </Button>
                </div>

                {prtObRows.length === 0 ? (
                  <div className="text-xs text-muted-foreground italic bg-gray-50 p-2.5 rounded border">
                    No opening balance specified.
                  </div>
                ) : (
                  <div className="space-y-2">
                    {prtObRows.map((row, idx) => (
                      <div
                        key={idx}
                        className="grid grid-cols-12 gap-2 items-center bg-gray-50 p-2 rounded-lg border text-xs"
                      >
                        <div className="col-span-4">
                          <Select
                            value={row.company_id ? String(row.company_id) : ""}
                            onValueChange={(val) => {
                              const copy = [...prtObRows];
                              copy[idx].company_id = val ? parseInt(val) : null;
                              setPrtObRows(copy);
                            }}
                          >
                            <SelectTrigger className="h-8 text-xs bg-white">
                              <SelectValue placeholder="All Companies" />
                            </SelectTrigger>
                            <SelectContent>
                              {companies.map((c) => (
                                <SelectItem key={c.id} value={String(c.id)}>
                                  {c.company_name}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </div>
                        <div className="col-span-3">
                          <Input
                            type="number"
                            step="0.01"
                            placeholder="Amount (₹)"
                            value={row.amount || ""}
                            onChange={(e) => {
                              const copy = [...prtObRows];
                              copy[idx].amount = parseFloat(e.target.value) || 0;
                              setPrtObRows(copy);
                            }}
                            className="h-8 text-xs bg-white"
                          />
                        </div>
                        <div className="col-span-2">
                          <Select
                            value={row.type}
                            onValueChange={(val: any) => {
                              const copy = [...prtObRows];
                              copy[idx].type = val;
                              setPrtObRows(copy);
                            }}
                          >
                            <SelectTrigger className="h-8 text-xs bg-white">
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="CREDIT">CR</SelectItem>
                              <SelectItem value="DEBIT">DR</SelectItem>
                            </SelectContent>
                          </Select>
                        </div>
                        <div className="col-span-2">
                          <Input
                            type="date"
                            value={row.date || ""}
                            onChange={(e) => {
                              const copy = [...prtObRows];
                              copy[idx].date = e.target.value || null;
                              setPrtObRows(copy);
                            }}
                            className="h-8 text-xs bg-white"
                          />
                        </div>
                        <div className="col-span-1 text-right">
                          <Button
                            type="button"
                            variant="ghost"
                            size="sm"
                            onClick={() => setPrtObRows(prtObRows.filter((_, i) => i !== idx))}
                            className="h-8 w-8 p-0 text-rose-500 hover:bg-rose-50"
                          >
                            <X className="w-4 h-4" />
                          </Button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </TabsContent>

            <TabsContent value="contacts" className="space-y-4 pt-3">
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <Label className="text-xs font-semibold">Primary Contact Name</Label>
                  <Input
                    value={prtForm.contact_person_1_name || ""}
                    onChange={(e) => setPrtForm({ ...prtForm, contact_person_1_name: e.target.value })}
                  />
                </div>
                <div className="space-y-1.5">
                  <Label className="text-xs font-semibold">Phone / WhatsApp</Label>
                  <Input
                    placeholder="10-digit mobile"
                    value={prtForm.phone || ""}
                    onChange={(e) => setPrtForm({ ...prtForm, phone: e.target.value })}
                  />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <Label className="text-xs font-semibold">Email Address</Label>
                  <Input
                    type="email"
                    value={prtForm.email || ""}
                    onChange={(e) => setPrtForm({ ...prtForm, email: e.target.value })}
                  />
                </div>
                <div className="space-y-1.5">
                  <Label className="text-xs font-semibold">Designation</Label>
                  <Input
                    placeholder="e.g. Director / Owner"
                    value={prtForm.contact_person_1_designation || ""}
                    onChange={(e) =>
                      setPrtForm({ ...prtForm, contact_person_1_designation: e.target.value })
                    }
                  />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3 pt-2 border-t">
                <div className="space-y-1.5">
                  <Label className="text-xs font-semibold">Contact Person 2</Label>
                  <Input
                    value={prtForm.contact_person_2_name || ""}
                    onChange={(e) => setPrtForm({ ...prtForm, contact_person_2_name: e.target.value })}
                  />
                </div>
                <div className="space-y-1.5">
                  <Label className="text-xs font-semibold">Contact 2 Phone</Label>
                  <Input
                    value={prtForm.contact_person_2_phone || ""}
                    onChange={(e) => setPrtForm({ ...prtForm, contact_person_2_phone: e.target.value })}
                  />
                </div>
              </div>
            </TabsContent>

            <TabsContent value="address" className="space-y-3.5 pt-3">
              <div className="space-y-1.5">
                <Label className="text-xs font-semibold">Physical Address</Label>
                <Textarea
                  rows={2}
                  value={prtForm.address || ""}
                  onChange={(e) => setPrtForm({ ...prtForm, address: e.target.value })}
                />
              </div>
              <div className="grid grid-cols-3 gap-3">
                <div className="space-y-1.5">
                  <Label className="text-xs font-semibold">City</Label>
                  <Input
                    value={prtForm.city || ""}
                    onChange={(e) => setPrtForm({ ...prtForm, city: e.target.value })}
                  />
                </div>
                <div className="space-y-1.5">
                  <Label className="text-xs font-semibold">State</Label>
                  <Input
                    value={prtForm.state || ""}
                    onChange={(e) => setPrtForm({ ...prtForm, state: e.target.value })}
                  />
                </div>
                <div className="space-y-1.5">
                  <Label className="text-xs font-semibold">Pincode</Label>
                  <Input
                    maxLength={10}
                    value={prtForm.pincode || ""}
                    onChange={(e) => setPrtForm({ ...prtForm, pincode: e.target.value })}
                  />
                </div>
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs font-semibold">Zone / Region</Label>
                <Input
                  placeholder="e.g. South Zone, Telangana & AP"
                  value={prtForm.zone || ""}
                  onChange={(e) => setPrtForm({ ...prtForm, zone: e.target.value })}
                />
              </div>
            </TabsContent>

            <TabsContent value="bank" className="space-y-3.5 pt-3">
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <Label className="text-xs font-semibold">Bank Name</Label>
                  <Input
                    value={prtForm.bank_name || ""}
                    onChange={(e) => setPrtForm({ ...prtForm, bank_name: e.target.value })}
                  />
                </div>
                <div className="space-y-1.5">
                  <Label className="text-xs font-semibold">Branch</Label>
                  <Input
                    value={prtForm.bank_branch || ""}
                    onChange={(e) => setPrtForm({ ...prtForm, bank_branch: e.target.value })}
                  />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <Label className="text-xs font-semibold">Account Number</Label>
                  <Input
                    value={prtForm.account_number || ""}
                    onChange={(e) => setPrtForm({ ...prtForm, account_number: e.target.value })}
                    className="font-mono"
                  />
                </div>
                <div className="space-y-1.5">
                  <Label className="text-xs font-semibold">IFSC Code</Label>
                  <Input
                    maxLength={11}
                    value={prtForm.ifsc_code || ""}
                    onChange={(e) =>
                      setPrtForm({ ...prtForm, ifsc_code: e.target.value.toUpperCase() })
                    }
                    className="font-mono uppercase"
                  />
                </div>
              </div>
              <div className="grid grid-cols-3 gap-3 pt-2 border-t">
                <div className="space-y-1.5">
                  <Label className="text-xs font-semibold">Payment Terms</Label>
                  <Select
                    value={prtForm.payment_terms || "ADVANCE"}
                    onValueChange={(val) => setPrtForm({ ...prtForm, payment_terms: val })}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="ADVANCE">Advance</SelectItem>
                      <SelectItem value="COD">Cash on Delivery</SelectItem>
                      <SelectItem value="CREDIT_15">15 Days</SelectItem>
                      <SelectItem value="CREDIT_30">30 Days</SelectItem>
                      <SelectItem value="CREDIT_45">45 Days</SelectItem>
                      <SelectItem value="CREDIT_60">60 Days</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-1.5">
                  <Label className="text-xs font-semibold">Credit Limit (₹)</Label>
                  <Input
                    type="number"
                    min="0"
                    value={prtForm.credit_limit || 0}
                    onChange={(e) =>
                      setPrtForm({ ...prtForm, credit_limit: parseFloat(e.target.value) || 0 })
                    }
                  />
                </div>
                <div className="space-y-1.5">
                  <Label className="text-xs font-semibold">Credit Days</Label>
                  <Input
                    type="number"
                    min="0"
                    max="365"
                    value={prtForm.credit_days || 0}
                    onChange={(e) =>
                      setPrtForm({ ...prtForm, credit_days: parseInt(e.target.value) || 0 })
                    }
                  />
                </div>
              </div>
            </TabsContent>
          </Tabs>

          <DialogFooter className="flex justify-between items-center pt-3 border-t">
            {prtEditId ? (
              <Button
                type="button"
                variant="destructive"
                size="sm"
                onClick={deactivatePartner}
                className="gap-1 bg-rose-600 hover:bg-rose-700"
              >
                <Trash2 className="w-3.5 h-3.5" /> Deactivate
              </Button>
            ) : (
              <div />
            )}
            <div className="flex gap-2">
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => setIsPrtModalOpen(false)}
              >
                Cancel
              </Button>
              <Button
                type="button"
                size="sm"
                onClick={savePartner}
                disabled={prtSaving}
                className="bg-emerald-600 hover:bg-emerald-700 text-white gap-1.5"
              >
                {prtSaving && <Loader2 className="w-4 h-4 animate-spin" />}
                Save Partner
              </Button>
            </div>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* ==================================================== */}
      {/* MODAL 4: ADD JOURNAL ENTRY (Party Ledger) */}
      {/* ==================================================== */}
      <Dialog open={isLdgModalOpen} onOpenChange={setIsLdgModalOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-lg">
              <BookOpen className="w-5 h-5 text-blue-600" />
              Add Party Journal Entry
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-3.5 py-2">
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label className="text-xs font-semibold">
                  Company <span className="text-rose-500">*</span>
                </Label>
                <Select
                  value={ldgForm.company_id}
                  onValueChange={(val) => setLdgForm({ ...ldgForm, company_id: val })}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select Company" />
                  </SelectTrigger>
                  <SelectContent>
                    {companies.map((c) => (
                      <SelectItem key={c.id} value={String(c.id)}>
                        {c.company_name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs font-semibold">
                  Date <span className="text-rose-500">*</span>
                </Label>
                <Input
                  type="date"
                  value={ldgForm.transaction_date}
                  onChange={(e) => setLdgForm({ ...ldgForm, transaction_date: e.target.value })}
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label className="text-xs font-semibold">
                  Party Type <span className="text-rose-500">*</span>
                </Label>
                <Select
                  value={ldgForm.party_type}
                  onValueChange={(val) => setLdgForm({ ...ldgForm, party_type: val })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="CUSTOMER">Customer</SelectItem>
                    <SelectItem value="VENDOR">Vendor</SelectItem>
                    <SelectItem value="EMPLOYEE">Employee</SelectItem>
                    <SelectItem value="COMPANY">Company</SelectItem>
                    <SelectItem value="EXTERNAL">External</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs font-semibold">
                  Party Name <span className="text-rose-500">*</span>
                </Label>
                <Input
                  placeholder="Full Party Name"
                  value={ldgForm.party_name}
                  onChange={(e) => setLdgForm({ ...ldgForm, party_name: e.target.value })}
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label className="text-xs font-semibold">
                  Entry Type <span className="text-rose-500">*</span>
                </Label>
                <Select
                  value={ldgForm.entry_type}
                  onValueChange={(val) => setLdgForm({ ...ldgForm, entry_type: val })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="DEBIT">Debit (DR)</SelectItem>
                    <SelectItem value="CREDIT">Credit (CR)</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs font-semibold">
                  Amount (₹) <span className="text-rose-500">*</span>
                </Label>
                <Input
                  type="number"
                  step="0.01"
                  min="0.01"
                  placeholder="0.00"
                  value={ldgForm.amount}
                  onChange={(e) => setLdgForm({ ...ldgForm, amount: e.target.value })}
                />
              </div>
            </div>

            <div className="space-y-1.5">
              <Label className="text-xs font-semibold">Narration / Remarks</Label>
              <Textarea
                rows={2}
                placeholder="Brief explanation of journal entry"
                value={ldgForm.narration}
                onChange={(e) => setLdgForm({ ...ldgForm, narration: e.target.value })}
              />
            </div>

            <div className="space-y-1.5">
              <Label className="text-xs font-semibold">Reference Number</Label>
              <Input
                placeholder="Invoice, receipt, or JV reference"
                value={ldgForm.reference_number}
                onChange={(e) => setLdgForm({ ...ldgForm, reference_number: e.target.value })}
              />
            </div>
          </div>
          <DialogFooter className="flex justify-end gap-2 pt-3 border-t">
            <Button variant="outline" size="sm" onClick={() => setIsLdgModalOpen(false)}>
              Cancel
            </Button>
            <Button
              size="sm"
              onClick={saveLedgerEntry}
              disabled={ldgSaving}
              className="bg-blue-600 hover:bg-blue-700 text-white gap-1.5"
            >
              {ldgSaving && <Loader2 className="w-4 h-4 animate-spin" />}
              Post Journal Entry
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* ==================================================== */}
      {/* MODAL 5: EXPENSE MAIN CATEGORY */}
      {/* ==================================================== */}
      <Dialog open={isExpMainModalOpen} onOpenChange={setIsExpMainModalOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-lg">
              <Folder className="w-5 h-5 text-indigo-600" />
              {expMainEditId ? "Edit Expense Category" : "Add Expense Category"}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-3.5 py-2">
            <div className="space-y-1.5">
              <Label className="text-xs font-semibold">
                Category Name <span className="text-rose-500">*</span>
              </Label>
              <Input
                placeholder="e.g. Office Operations"
                value={expMainForm.name}
                onChange={(e) => setExpMainForm({ ...expMainForm, name: e.target.value })}
              />
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs font-semibold">Description</Label>
              <Textarea
                rows={3}
                placeholder="Brief summary of what expenses fall under this category"
                value={expMainForm.description}
                onChange={(e) => setExpMainForm({ ...expMainForm, description: e.target.value })}
              />
            </div>
          </div>
          <DialogFooter className="flex justify-end gap-2 pt-3 border-t">
            <Button variant="outline" size="sm" onClick={() => setIsExpMainModalOpen(false)}>
              Cancel
            </Button>
            <Button
              size="sm"
              onClick={saveExpMainCat}
              disabled={expMainSaving}
              className="bg-indigo-600 hover:bg-indigo-700 text-white gap-1.5"
            >
              {expMainSaving && <Loader2 className="w-4 h-4 animate-spin" />}
              Save Category
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* ==================================================== */}
      {/* MODAL 6: EXPENSE SUB CATEGORY */}
      {/* ==================================================== */}
      <Dialog open={isExpSubModalOpen} onOpenChange={setIsExpSubModalOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-lg">
              <FolderOpen className="w-5 h-5 text-emerald-600" />
              {expSubEditId ? "Edit Expense Sub Category" : "Add Expense Sub Category"}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-3.5 py-2">
            <div className="space-y-1.5">
              <Label className="text-xs font-semibold">
                Parent Main Category <span className="text-rose-500">*</span>
              </Label>
              <Select
                value={expSubForm.parent_id}
                onValueChange={(val) => setExpSubForm({ ...expSubForm, parent_id: val })}
              >
                <SelectTrigger>
                  <SelectValue placeholder="-- Select Main Category --" />
                </SelectTrigger>
                <SelectContent>
                  {expMain.map((m) => (
                    <SelectItem key={m.id} value={String(m.id)}>
                      {m.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs font-semibold">
                Sub Category Name <span className="text-rose-500">*</span>
              </Label>
              <Input
                placeholder="e.g. Stationery &amp; Printing"
                value={expSubForm.name}
                onChange={(e) => setExpSubForm({ ...expSubForm, name: e.target.value })}
              />
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs font-semibold">Description</Label>
              <Textarea
                rows={2}
                placeholder="Sub category details"
                value={expSubForm.description}
                onChange={(e) => setExpSubForm({ ...expSubForm, description: e.target.value })}
              />
            </div>
          </div>
          <DialogFooter className="flex justify-end gap-2 pt-3 border-t">
            <Button variant="outline" size="sm" onClick={() => setIsExpSubModalOpen(false)}>
              Cancel
            </Button>
            <Button
              size="sm"
              onClick={saveExpSubCat}
              disabled={expSubSaving}
              className="bg-emerald-600 hover:bg-emerald-700 text-white gap-1.5"
            >
              {expSubSaving && <Loader2 className="w-4 h-4 animate-spin" />}
              Save Sub Category
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* ==================================================== */}
      {/* MODAL 7: INCOME MAIN CATEGORY */}
      {/* ==================================================== */}
      <Dialog open={isIncMainModalOpen} onOpenChange={setIsIncMainModalOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-lg">
              <Coins className="w-5 h-5 text-amber-500" />
              {incMainEditId ? "Edit Income Category" : "Add Income Category"}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-3.5 py-2">
            <div className="space-y-1.5">
              <Label className="text-xs font-semibold">
                Category Name <span className="text-rose-500">*</span>
              </Label>
              <Input
                placeholder="e.g. Sales Revenue"
                value={incMainForm.name}
                onChange={(e) => setIncMainForm({ ...incMainForm, name: e.target.value })}
              />
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs font-semibold">Description</Label>
              <Textarea
                rows={3}
                placeholder="Income head description"
                value={incMainForm.description}
                onChange={(e) => setIncMainForm({ ...incMainForm, description: e.target.value })}
              />
            </div>
          </div>
          <DialogFooter className="flex justify-end gap-2 pt-3 border-t">
            <Button variant="outline" size="sm" onClick={() => setIsIncMainModalOpen(false)}>
              Cancel
            </Button>
            <Button
              size="sm"
              onClick={saveIncMainCat}
              disabled={incMainSaving}
              className="bg-amber-500 hover:bg-amber-600 text-white gap-1.5"
            >
              {incMainSaving && <Loader2 className="w-4 h-4 animate-spin" />}
              Save Income Category
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* ==================================================== */}
      {/* MODAL 8: INCOME SUB CATEGORY */}
      {/* ==================================================== */}
      <Dialog open={isIncSubModalOpen} onOpenChange={setIsIncSubModalOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-lg">
              <FolderOpen className="w-5 h-5 text-emerald-600" />
              {incSubEditId ? "Edit Income Sub Category" : "Add Income Sub Category"}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-3.5 py-2">
            <div className="space-y-1.5">
              <Label className="text-xs font-semibold">
                Parent Main Category <span className="text-rose-500">*</span>
              </Label>
              <Select
                value={incSubForm.parent_id}
                onValueChange={(val) => setIncSubForm({ ...incSubForm, parent_id: val })}
              >
                <SelectTrigger>
                  <SelectValue placeholder="-- Select Main Category --" />
                </SelectTrigger>
                <SelectContent>
                  {incMain.map((m) => (
                    <SelectItem key={m.id} value={String(m.id)}>
                      {m.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs font-semibold">
                Sub Category Name <span className="text-rose-500">*</span>
              </Label>
              <Input
                placeholder="e.g. EV Vehicle Sales"
                value={incSubForm.name}
                onChange={(e) => setIncSubForm({ ...incSubForm, name: e.target.value })}
              />
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs font-semibold">Description</Label>
              <Textarea
                rows={2}
                placeholder="Sub category details"
                value={incSubForm.description}
                onChange={(e) => setIncSubForm({ ...incSubForm, description: e.target.value })}
              />
            </div>
          </div>
          <DialogFooter className="flex justify-end gap-2 pt-3 border-t">
            <Button variant="outline" size="sm" onClick={() => setIsIncSubModalOpen(false)}>
              Cancel
            </Button>
            <Button
              size="sm"
              onClick={saveIncSubCat}
              disabled={incSubSaving}
              className="bg-emerald-600 hover:bg-emerald-700 text-white gap-1.5"
            >
              {incSubSaving && <Loader2 className="w-4 h-4 animate-spin" />}
              Save Sub Category
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
