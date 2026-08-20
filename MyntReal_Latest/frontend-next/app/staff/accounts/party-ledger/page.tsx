"use client";

import React, { useState, useEffect, useMemo, useCallback } from "react";
import Link from "next/link";
import {
  BookOpen,
  PlusCircle,
  Upload,
  Layers,
  Landmark,
  ListFilter,
  Users,
  Building2,
  Search,
  RotateCcw,
  RefreshCw,
  Eye,
  Edit,
  Trash2,
  CheckCircle2,
  AlertTriangle,
  ArrowRight,
  ArrowLeft,
  X,
  ExternalLink,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  Coins,
  Receipt,
  FileSpreadsheet,
  Printer,
  FileText,
  Tag,
  Calendar,
  Check,
  Filter,
  Wallet
} from "lucide-react";
import toast, { Toaster } from "react-hot-toast";

import api from "@/lib/api";
import { useStaffAuth } from "@/contexts/StaffAuthContext";

// ── Types & Interfaces ──────────────────────────────────────────────

interface Company {
  id: number | string;
  company_name?: string;
  name?: string;
}

interface PartyOption {
  type: string;
  id: number;
  name: string;
  displayName?: string;
  badge?: string;
  badgeColor?: string;
  badgeBg?: string;
}

interface LedgerEntry {
  id: number;
  company_id?: number;
  transaction_date: string;
  party_id?: number;
  party_name?: string;
  party_type?: string;
  entry_type: "DEBIT" | "CREDIT";
  debit_amount?: number;
  credit_amount?: number;
  running_balance?: number;
  balance?: number;
  voucher_type?: string | null;
  reference_type?: string | null;
  reference_id?: number | string | null;
  reference_number?: string | null;
  particulars?: string | null;
  narration?: string | null;
  main_category_name?: string | null;
  sub_category_name?: string | null;
  category?: string | null;
  source_status?: string | null;
  account_name?: string;
  account_type?: string;
  date?: string;
}

interface PartyLedgerResponse {
  success: boolean;
  message?: string;
  entries: LedgerEntry[];
  total: number;
  opening_balance?: number;
  opening_balance_date?: string;
  total_debit?: number;
  total_credit?: number;
  closing_balance?: number;
}

interface GLHead {
  account_type: string;
  account_name: string;
  company_id?: number;
  total_debit: number;
  total_credit: number;
  balance: number;
  last_date?: string | null;
}

interface PartyWiseRow {
  party_id?: number;
  company_id?: number;
  party_name: string;
  party_type: string;
  entry_count: number;
  total_debit: number;
  total_credit: number;
  net_balance: number;
  last_date?: string | null;
}

interface TallyPreviewItem {
  date: string;
  ref: string;
  vtype: string;
  part: string;
  debit: number;
  credit: number;
}

interface TallyImportResult {
  success: boolean;
  message: string;
  imported: number;
  skipped_duplicates: number;
  closing_balance: number;
  date_range_in_file?: string;
  name_deviation?: boolean;
  party_name_in_file?: string;
  file_closing_balance?: number | null;
  balance_verified?: boolean;
  balance_diff?: number;
  new_particulars?: string[];
}

// ── Constants & Helpers ─────────────────────────────────────────────

const PARTY_TYPE_META: Record<string, { badge: string; badgeColor: string; badgeBg: string }> = {
  VENDOR:   { badge: "Vendor",    badgeColor: "text-blue-700",   badgeBg: "bg-blue-50 border-blue-200" },
  EMPLOYEE: { badge: "Staff",     badgeColor: "text-amber-700",  badgeBg: "bg-amber-50 border-amber-200" },
  CUSTOMER: { badge: "Customer",  badgeColor: "text-cyan-700",   badgeBg: "bg-cyan-50 border-cyan-200" },
  EXTERNAL: { badge: "External",  badgeColor: "text-purple-700", badgeBg: "bg-purple-50 border-purple-200" },
  USER:     { badge: "User",      badgeColor: "text-emerald-700",badgeBg: "bg-emerald-50 border-emerald-200" },
  PARTNER:  { badge: "Partner",   badgeColor: "text-pink-700",   badgeBg: "bg-pink-50 border-pink-200" },
  ALL:      { badge: "Party",     badgeColor: "text-gray-700",   badgeBg: "bg-gray-100 border-gray-200" },
};

const fmt = (n: number | string | null | undefined): string => {
  if (n === null || n === undefined || n === "") return "₹0.00";
  const num = Number(n);
  if (isNaN(num)) return "₹0.00";
  return "₹" + num.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
};

const fmtBal = (val: number | string | null | undefined) => {
  const n = parseFloat(String(val || 0));
  if (!n) return { text: "Nil", isDr: false, isCr: false, num: 0 };
  const abs = Math.abs(n);
  const isDr = n > 0;
  const isCr = n < 0;
  return {
    text: "₹" + abs.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 }),
    label: isDr ? "Dr" : isCr ? "Cr" : "",
    isDr,
    isCr,
    num: n
  };
};

const fmtDate = (raw?: string | null) => {
  if (!raw) return "—";
  try {
    const clean = raw.includes("T") ? raw.split("T")[0] : raw;
    const [y, m, d] = clean.split("-");
    if (y && m && d) {
      const dt = new Date(+y, +m - 1, +d);
      return dt.toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" });
    }
    return raw;
  } catch {
    return raw;
  }
};

const getCategoryChip = (e: LedgerEntry) => {
  const refType = (e.reference_type || "").toUpperCase();
  const vt = (e.voucher_type || "").toUpperCase();

  if (e.main_category_name) {
    return { label: e.main_category_name, cls: "bg-sky-50 text-sky-800 border-sky-200" };
  }
  if (e.category) {
    return { label: e.category, cls: "bg-sky-50 text-sky-800 border-sky-200" };
  }
  const catMap: Record<string, { label: string; cls: string }> = {
    SALES_INVOICE:    { label: "Sale", cls: "bg-emerald-50 text-emerald-800 border-emerald-200" },
    PURCHASE_INVOICE: { label: "Purchase", cls: "bg-amber-50 text-amber-800 border-amber-200" },
    VENDOR_TXN:       { label: "Purchase", cls: "bg-amber-50 text-amber-800 border-amber-200" },
    INCOME:           { label: "Income", cls: "bg-emerald-50 text-emerald-800 border-emerald-200" },
    EXPENSE:          { label: "Expense", cls: "bg-red-50 text-red-800 border-red-200" },
    OPENING_BALANCE:  { label: "Opening", cls: "bg-gray-100 text-gray-800 border-gray-200" },
    DEBIT_NOTE:       { label: "Debit Note", cls: "bg-pink-50 text-pink-800 border-pink-200" },
    CREDIT_NOTE:      { label: "Credit Note", cls: "bg-purple-50 text-purple-800 border-purple-200" },
    ADVANCE:          { label: "Advance", cls: "bg-blue-50 text-blue-800 border-blue-200" },
    REFUND:           { label: "Refund", cls: "bg-gray-100 text-gray-800 border-gray-200" },
  };

  if (catMap[refType]) return catMap[refType];

  if (["JOURNAL", "MANUAL", "TALLY_IMPORT"].includes(refType)) {
    if (vt.includes("PAYMENT")) return { label: "Payment", cls: "bg-blue-50 text-blue-800 border-blue-200" };
    if (vt.includes("RECEIPT")) return { label: "Receipt", cls: "bg-emerald-50 text-emerald-800 border-emerald-200" };
    if (vt.includes("PURCH"))   return { label: "Purchase", cls: "bg-amber-50 text-amber-800 border-amber-200" };
    if (vt.includes("SALE"))    return { label: "Sale", cls: "bg-emerald-50 text-emerald-800 border-emerald-200" };
    if (vt.includes("CONTRA"))  return { label: "Contra", cls: "bg-gray-100 text-gray-800 border-gray-200" };
    return { label: "Journal", cls: "bg-gray-100 text-gray-800 border-gray-200" };
  }

  if (vt === "PAYMENT") return { label: "Payment", cls: "bg-blue-50 text-blue-800 border-blue-200" };
  if (vt === "RECEIPT") return { label: "Receipt", cls: "bg-emerald-50 text-emerald-800 border-emerald-200" };

  return { label: refType.replace(/_/g, " ") || "—", cls: "bg-gray-100 text-gray-800 border-gray-200" };
};

const getSourceBadge = (ss?: string | null) => {
  const s = (ss || "").toUpperCase();
  if (s === "MANUAL") return <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-amber-100 text-amber-800 border border-amber-200">Manual</span>;
  if (s === "TALLY_IMPORT") return <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-purple-100 text-purple-800 border border-purple-200">Tally</span>;
  if (s === "OPENING_BALANCE") return <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-blue-100 text-blue-800 border border-blue-200">Opening Bal</span>;
  if (s === "CONFIRMED") return <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-100 text-emerald-800 border border-emerald-200">Confirmed</span>;
  if (s === "CANCELLED") return <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-red-100 text-red-800 border border-red-200">Cancelled</span>;
  if (s) return <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-gray-100 text-gray-700 border border-gray-200">{s.replace(/_/g, " ")}</span>;
  return <span className="text-gray-400">—</span>;
};

// ── Main Component ──────────────────────────────────────────────────

export default function PartyLedgerPage() {
  const { user } = useStaffAuth();

  // Active Tab: 'party' | 'acct' | 'cash' | 'pwise' | 'awise' | 'cwise' | 'deleted'
  const [activeTab, setActiveTab] = useState<string>("party");

  // Companies
  const [companies, setCompanies] = useState<Company[]>([]);

  // ── Tab 1: Party Ledger States ─────────────────────────────────────
  const [filterCompany, setFilterCompany] = useState<string>("");
  const [filterPartyType, setFilterPartyType] = useState<string>("");
  const [filterPartyInput, setFilterPartyInput] = useState<string>("");
  const [selectedPartyData, setSelectedPartyData] = useState<PartyOption | null>(null);
  const [filterFromDate, setFilterFromDate] = useState<string>("");
  const [filterToDate, setFilterToDate] = useState<string>("");
  const [filterRefNumber, setFilterRefNumber] = useState<string>("");
  const [filterParticulars, setFilterParticulars] = useState<string>("");
  const [filterRefType, setFilterRefType] = useState<string>("");
  const [plStatusChecks, setPlStatusChecks] = useState<string[]>([]);
  const [statusMenuOpen, setStatusMenuOpen] = useState(false);
  const [partyComboOpen, setPartyComboOpen] = useState(false);

  const [allParties, setAllParties] = useState<PartyOption[]>([]);
  const [plLoading, setPlLoading] = useState(false);
  const [plEntries, setPlEntries] = useState<LedgerEntry[]>([]);
  const [plTotal, setPlTotal] = useState(0);
  const [plOpeningBal, setPlOpeningBal] = useState<number>(0);
  const [plOpeningDate, setPlOpeningDate] = useState<string>("");
  const [plTotalDebit, setPlTotalDebit] = useState<number>(0);
  const [plTotalCredit, setPlTotalCredit] = useState<number>(0);
  const [plClosingBal, setPlClosingBal] = useState<number>(0);
  const [plCurrentPage, setPlCurrentPage] = useState<number>(1);
  const pageSize = 50;

  // ── Tab 2: Account Ledger States ──────────────────────────────────
  const [alFilterCompany, setAlFilterCompany] = useState<string>("");
  const [alFilterType, setAlFilterType] = useState<string>("");
  const [alFilterAccount, setAlFilterAccount] = useState<string>("");
  const [alFromDate, setAlFromDate] = useState<string>("");
  const [alToDate, setAlToDate] = useState<string>("");
  const [alRefNumber, setAlRefNumber] = useState<string>("");
  const [alHeadsList, setAlHeadsList] = useState<GLHead[]>([]);
  const [alEntries, setAlEntries] = useState<LedgerEntry[]>([]);
  const [alLoading, setAlLoading] = useState(false);
  const [alTotal, setAlTotal] = useState(0);
  const [alTotalDebit, setAlTotalDebit] = useState(0);
  const [alTotalCredit, setAlTotalCredit] = useState(0);
  const [alNetBal, setAlNetBal] = useState(0);
  const [alCurrentPage, setAlCurrentPage] = useState(1);

  // ── Tab 3: Cash Ledger States ─────────────────────────────────────
  const [cashFilterCompany, setCashFilterCompany] = useState<string>("");
  const [cashFilterAccount, setCashFilterAccount] = useState<string>("");
  const [cashFromDate, setCashFromDate] = useState<string>("");
  const [cashToDate, setCashToDate] = useState<string>("");
  const [cashRefNumber, setCashRefNumber] = useState<string>("");
  const [cashHeadsList, setCashHeadsList] = useState<GLHead[]>([]);
  const [cashEntries, setCashEntries] = useState<LedgerEntry[]>([]);
  const [cashLoading, setCashLoading] = useState(false);
  const [cashTotal, setCashTotal] = useState(0);
  const [cashTotalDebit, setCashTotalDebit] = useState(0);
  const [cashTotalCredit, setCashTotalCredit] = useState(0);
  const [cashNetBal, setCashNetBal] = useState(0);
  const [cashCurrentPage, setCashCurrentPage] = useState(1);

  // ── Tab 4: Party-wise Consolidated States ─────────────────────────
  const [pwiseCompany, setPwiseCompany] = useState<string>("");
  const [pwisePartyType, setPwisePartyType] = useState<string>("");
  const [pwisePartySearch, setPwisePartySearch] = useState<string>("");
  const [pwiseFromDate, setPwiseFromDate] = useState<string>("");
  const [pwiseToDate, setPwiseToDate] = useState<string>("");
  const [pwiseData, setPwiseData] = useState<PartyWiseRow[]>([]);
  const [pwiseLoading, setPwiseLoading] = useState(false);

  // ── Tab 5: Bank Account-wise Consolidated States ──────────────────
  const [awiseCompany, setAwiseCompany] = useState<string>("");
  const [awiseFromDate, setAwiseFromDate] = useState<string>("");
  const [awiseToDate, setAwiseToDate] = useState<string>("");
  const [awiseData, setAwiseData] = useState<GLHead[]>([]);
  const [awiseLoading, setAwiseLoading] = useState(false);

  // ── Tab 6: Cash-wise Consolidated States ──────────────────────────
  const [cwiseCompany, setCwiseCompany] = useState<string>("");
  const [cwiseFromDate, setCwiseFromDate] = useState<string>("");
  const [cwiseToDate, setCwiseToDate] = useState<string>("");
  const [cwiseData, setCwiseData] = useState<GLHead[]>([]);
  const [cwiseLoading, setCwiseLoading] = useState(false);

  // ── Tab 7: Deleted Entries States ─────────────────────────────────
  const [delCompany, setDelCompany] = useState<string>("");
  const [delFromDate, setDelFromDate] = useState<string>("");
  const [delToDate, setDelToDate] = useState<string>("");
  const [delParticulars, setDelParticulars] = useState<string>("");
  const [delRefNumber, setDelRefNumber] = useState<string>("");
  const [delEntries, setDelEntries] = useState<LedgerEntry[]>([]);
  const [delLoading, setDelLoading] = useState(false);
  const [delTotal, setDelTotal] = useState(0);
  const [delCurrentPage, setDelCurrentPage] = useState(1);

  // ── Modals & Dialog States ─────────────────────────────────────────

  // 1. New Entry Modal
  const [newEntryModalOpen, setNewEntryModalOpen] = useState(false);
  const [entryDate, setEntryDate] = useState<string>(new Date().toISOString().split("T")[0]);
  const [entryRef, setEntryRef] = useState("");
  const [entryPartyVal, setEntryPartyVal] = useState("");
  const [entryVoucherType, setEntryVoucherType] = useState("");
  const [entryCategory, setEntryCategory] = useState("");
  const [entryParticulars, setEntryParticulars] = useState("");
  const [entryType, setEntryType] = useState<"DEBIT" | "CREDIT">("DEBIT");
  const [entryAmount, setEntryAmount] = useState<string>("");
  const [entryNarration, setEntryNarration] = useState("");
  const [savingEntry, setSavingEntry] = useState(false);

  // 2. Tally Import Modal
  const [tallyModalOpen, setTallyModalOpen] = useState(false);
  const [tallyStep, setTallyStep] = useState<1 | 2>(1);
  const [tallyPartyType, setTallyPartyType] = useState<string>("VENDOR");
  const [tallyPartyInput, setTallyPartyInput] = useState<string>("");
  const [tallyComboOpen, setTallyComboOpen] = useState(false);
  const [tallySelectedParty, setTallySelectedParty] = useState<PartyOption | null>(null);
  const [tallyFile, setTallyFile] = useState<File | null>(null);
  const [tallyPreview, setTallyPreview] = useState<TallyPreviewItem[]>([]);
  const [tallyPdfDetectedParty, setTallyPdfDetectedParty] = useState<string | null>(null);
  const [importingTally, setImportingTally] = useState(false);
  const [tallyImportResult, setTallyImportResult] = useState<TallyImportResult | null>(null);
  const [renamingParty, setRenamingParty] = useState(false);
  const [renameResultMsg, setRenameResultMsg] = useState<{ text: string; isError: boolean } | null>(null);

  // 3. Edit Entry Modal
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [editEntryId, setEditEntryId] = useState<number | null>(null);
  const [editDate, setEditDate] = useState("");
  const [editType, setEditType] = useState<"DEBIT" | "CREDIT">("DEBIT");
  const [editAmount, setEditAmount] = useState<string>("");
  const [editRef, setEditRef] = useState("");
  const [editVchType, setEditVchType] = useState("");
  const [editParticulars, setEditParticulars] = useState("");
  const [editNarration, setEditNarration] = useState("");
  const [savingEdit, setSavingEdit] = useState(false);

  // 4. View Source Document Modal
  const [viewDocModalOpen, setViewDocModalOpen] = useState(false);
  const [viewDocLoading, setViewDocLoading] = useState(false);
  const [viewDocTitle, setViewDocTitle] = useState("");
  const [viewDocData, setViewDocData] = useState<any>(null);
  const [viewDocRefType, setViewDocRefType] = useState<string>("");
  const [viewDocCurrentEntry, setViewDocCurrentEntry] = useState<LedgerEntry | null>(null);

  // 5. Fix / Rename Party Modal
  const [fixPartyModalOpen, setFixPartyModalOpen] = useState(false);
  const [fixPartyData, setFixPartyData] = useState<{
    partyName: string;
    partyType: string;
    partyId: number;
    companyId: number;
  } | null>(null);
  const [fpNewName, setFpNewName] = useState("");
  const [fpNewType, setFpNewType] = useState("");
  const [savingFixParty, setSavingFixParty] = useState(false);

  // ── Initial Data Fetching ─────────────────────────────────────────

  const loadCompanies = async () => {
    try {
      const res = await api.get("/staff/accounts/companies");
      if (res.data.success && res.data.companies) {
        setCompanies(res.data.companies);
      }
    } catch (e) {
      console.error("Failed to load companies", e);
    }
  };

  const loadParties = useCallback(async (coId?: string, pType?: string) => {
    try {
      let url = "/staff/accounts/party-ledger/parties";
      const params = new URLSearchParams();
      if (coId) params.append("company_id", coId);
      if (pType) params.append("party_type", pType);
      if (params.toString()) url += `?${params.toString()}`;

      const res = await api.get(url);
      const pd = res.data;
      if (pd.parties) {
        const seen = new Set<string>();
        const seenByName = new Map<string, number>();
        const partiesList: PartyOption[] = [];

        pd.parties.forEach((p: any) => {
          const type = p.party_type;
          const id = parseInt(p.party_id) || 0;
          const name = p.party_name || "";
          const displayName = p.display_name || name;
          const key = `${type}:${id}`;
          if (seen.has(key)) return;
          seen.add(key);

          const nk = name.toLowerCase().trim();
          if (seenByName.has(nk)) {
            const idx = seenByName.get(nk)!;
            if (partiesList[idx].type !== "ALL") {
              partiesList[idx].type = "ALL";
              partiesList[idx].id = 0;
              Object.assign(partiesList[idx], PARTY_TYPE_META["ALL"]);
            }
            return;
          }

          const m = PARTY_TYPE_META[type] || { badge: type, badgeColor: "text-gray-700", badgeBg: "bg-gray-100 border-gray-200" };
          seenByName.set(nk, partiesList.length);
          partiesList.push({ type, id, name, displayName, ...m });
        });

        const typeOrder: Record<string, number> = { VENDOR: 0, CUSTOMER: 1, EMPLOYEE: 2, EXTERNAL: 3, USER: 4 };
        partiesList.sort((a, b) => (typeOrder[a.type] ?? 9) - (typeOrder[b.type] ?? 9) || a.name.localeCompare(b.name));
        setAllParties(partiesList);
      }
    } catch (e) {
      console.error("Failed to load parties", e);
    }
  }, []);

  useEffect(() => {
    loadCompanies();
    loadParties();
  }, [loadParties]);

  // ── Tab 1: Party Ledger Loader ────────────────────────────────────

  const loadLedger = useCallback(async (page = 1) => {
    setPlLoading(true);
    setPlCurrentPage(page);

    const isUnified = !filterPartyType || selectedPartyData?.type === "ALL" || selectedPartyData?.type === null;
    const pType = isUnified ? "" : (selectedPartyData?.type || filterPartyType || "");
    const pId = isUnified ? 0 : (selectedPartyData?.id ?? 0);
    const pName = selectedPartyData?.name || filterPartyInput.trim();

    try {
      const params = new URLSearchParams({
        page: String(page),
        page_size: String(pageSize),
      });

      if (filterCompany) params.append("company_id", filterCompany);
      if (pType) params.append("party_type", pType);
      if (pId) params.append("party_id", String(pId));
      if (pName) params.append("party_name", pName);
      if (filterFromDate) params.append("date_from", filterFromDate);
      if (filterToDate) params.append("date_to", filterToDate);
      if (filterRefNumber.trim()) params.append("reference_number", filterRefNumber.trim());
      if (filterParticulars.trim()) params.append("particulars", filterParticulars.trim());
      if (filterRefType) params.append("reference_type", filterRefType);
      if (plStatusChecks.length) params.append("source_status", plStatusChecks.join(","));

      const res = await api.get(`/staff/accounts/party-ledger?${params.toString()}`);
      const data: PartyLedgerResponse = res.data;

      if (data.success) {
        setPlOpeningBal(data.opening_balance || 0);
        setPlOpeningDate(data.opening_balance_date || "");
        setPlTotalDebit(data.total_debit || 0);
        setPlTotalCredit(data.total_credit || 0);
        setPlClosingBal(data.closing_balance || 0);
        setPlTotal(data.total || (data.entries ? data.entries.length : 0));

        const rawEntries = data.entries || [];
        // Recompute running_balance client-side in date+id ASC order from opening_balance
        const obRaw = parseFloat(String(data.opening_balance || 0));
        const ascE = [...rawEntries].sort((a, b) => {
          const d = new Date(a.transaction_date).getTime() - new Date(b.transaction_date).getTime();
          return d !== 0 ? d : a.id - b.id;
        });

        let rb = obRaw;
        const rbMap: Record<number, number> = {};
        for (const e of ascE) {
          rb += parseFloat(String(e.debit_amount || 0)) - parseFloat(String(e.credit_amount || 0));
          rbMap[e.id] = rb;
        }

        const computedEntries = rawEntries.map((e) => ({
          ...e,
          running_balance: rbMap[e.id] !== undefined ? rbMap[e.id] : e.running_balance,
        }));

        setPlEntries(computedEntries);
      } else {
        toast.error(data.message || "Failed to load party ledger");
        setPlEntries([]);
      }
    } catch (e: any) {
      toast.error(e.response?.data?.message || "Failed to load party ledger");
      setPlEntries([]);
    } finally {
      setPlLoading(false);
    }
  }, [
    filterCompany,
    filterPartyType,
    filterPartyInput,
    selectedPartyData,
    filterFromDate,
    filterToDate,
    filterRefNumber,
    filterParticulars,
    filterRefType,
    plStatusChecks,
  ]);

  // Initial load
  useEffect(() => {
    loadLedger(1);
  }, []);

  // ── Tab 2: Account Ledger Loader ──────────────────────────────────

  const loadAlAccounts = useCallback(async () => {
    try {
      const params = new URLSearchParams();
      if (alFilterCompany) params.append("company_id", alFilterCompany);
      if (alFilterType) params.append("account_type", alFilterType);

      const res = await api.get(`/staff/accounts/general-ledger/heads?${params.toString()}`);
      if (res.data.success && res.data.heads) {
        setAlHeadsList(res.data.heads);
      }
    } catch (e) {
      console.error(e);
    }
  }, [alFilterCompany, alFilterType]);

  const loadAccountLedger = useCallback(async (page = 1) => {
    setAlLoading(true);
    setAlCurrentPage(page);
    try {
      const params = new URLSearchParams({
        page: String(page),
        page_size: String(pageSize),
      });
      if (alFilterCompany) params.append("company_id", alFilterCompany);
      if (alFilterType) params.append("account_type", alFilterType);
      if (alFilterAccount) params.append("account_name", alFilterAccount);
      if (alFromDate) params.append("date_from", alFromDate);
      if (alToDate) params.append("date_to", alToDate);
      if (alRefNumber.trim()) params.append("reference_number", alRefNumber.trim());

      const res = await api.get(`/staff/accounts/general-ledger/entries?${params.toString()}`);
      const data = res.data;
      if (data.success) {
        const entries = data.entries || [];
        setAlEntries(entries);
        setAlTotal(data.total || entries.length);
        const totals = data.totals || {};
        setAlTotalDebit(totals.total_debit || 0);
        setAlTotalCredit(totals.total_credit || 0);
        setAlNetBal(totals.net_balance ?? (totals.total_debit || 0) - (totals.total_credit || 0));
      } else {
        toast.error(data.message || "Failed to load account ledger");
      }
    } catch (e: any) {
      toast.error(e.response?.data?.message || "Failed to load account statement");
    } finally {
      setAlLoading(false);
    }
  }, [alFilterCompany, alFilterType, alFilterAccount, alFromDate, alToDate, alRefNumber]);

  // ── Tab 3: Cash Ledger Loader ─────────────────────────────────────

  const loadCashAccounts = useCallback(async () => {
    try {
      const params = new URLSearchParams({ account_type: "CASH" });
      if (cashFilterCompany) params.append("company_id", cashFilterCompany);
      const res = await api.get(`/staff/accounts/general-ledger/heads?${params.toString()}`);
      if (res.data.success && res.data.heads) {
        setCashHeadsList(res.data.heads);
      }
    } catch (e) {
      console.error(e);
    }
  }, [cashFilterCompany]);

  const loadCashLedger = useCallback(async (page = 1) => {
    setCashLoading(true);
    setCashCurrentPage(page);
    try {
      const params = new URLSearchParams({
        page: String(page),
        page_size: String(pageSize),
        account_type: "CASH",
      });
      if (cashFilterCompany) params.append("company_id", cashFilterCompany);
      if (cashFilterAccount) params.append("account_name", cashFilterAccount);
      if (cashFromDate) params.append("date_from", cashFromDate);
      if (cashToDate) params.append("date_to", cashToDate);
      if (cashRefNumber.trim()) params.append("reference_number", cashRefNumber.trim());

      const res = await api.get(`/staff/accounts/general-ledger/entries?${params.toString()}`);
      const data = res.data;
      if (data.success) {
        const entries = data.entries || [];
        setCashEntries(entries);
        setCashTotal(data.total || entries.length);
        const totals = data.totals || {};
        setCashTotalDebit(totals.total_debit || 0);
        setCashTotalCredit(totals.total_credit || 0);
        setCashNetBal(totals.net_balance ?? (totals.total_debit || 0) - (totals.total_credit || 0));
      } else {
        toast.error(data.message || "Failed to load cash ledger");
      }
    } catch (e: any) {
      toast.error(e.response?.data?.message || "Failed to load cash statement");
    } finally {
      setCashLoading(false);
    }
  }, [cashFilterCompany, cashFilterAccount, cashFromDate, cashToDate, cashRefNumber]);

  // ── Tab 4: Party-Wise Consolidated Loader ─────────────────────────

  const loadPartyWise = useCallback(async () => {
    setPwiseLoading(true);
    try {
      const params = new URLSearchParams();
      if (pwiseCompany) params.append("company_id", pwiseCompany);
      if (pwisePartyType) params.append("party_type", pwisePartyType);
      if (pwiseFromDate) params.append("date_from", pwiseFromDate);
      if (pwiseToDate) params.append("date_to", pwiseToDate);

      const res = await api.get(`/staff/accounts/party-ledger/summary?${params.toString()}`);
      if (res.data.success && res.data.parties) {
        setPwiseData(res.data.parties);
      } else {
        setPwiseData([]);
      }
    } catch (e: any) {
      toast.error(e.response?.data?.message || "Failed to load party summary");
      setPwiseData([]);
    } finally {
      setPwiseLoading(false);
    }
  }, [pwiseCompany, pwisePartyType, pwiseFromDate, pwiseToDate]);

  // Filtered party-wise rows client-side search
  const filteredPwiseRows = useMemo(() => {
    if (!pwiseData.length) return [];
    const nq = pwisePartySearch.trim().toLowerCase();
    const tq = pwisePartyType.trim();
    return pwiseData.filter((r) => {
      const nm = !nq || (r.party_name || "").toLowerCase().includes(nq);
      const tm = !tq || r.party_type === tq;
      return nm && tm;
    });
  }, [pwiseData, pwisePartySearch, pwisePartyType]);

  // ── Tab 5: Bank Account-wise Consolidated Loader ──────────────────

  const loadAccountWise = useCallback(async () => {
    setAwiseLoading(true);
    try {
      const params = new URLSearchParams({ account_type: "BANK" });
      if (awiseCompany) params.append("company_id", awiseCompany);
      const res = await api.get(`/staff/accounts/general-ledger/heads?${params.toString()}`);
      if (res.data.success && res.data.heads) {
        setAwiseData(res.data.heads);
      } else {
        setAwiseData([]);
      }
    } catch (e: any) {
      toast.error(e.response?.data?.message || "Failed to load bank accounts");
      setAwiseData([]);
    } finally {
      setAwiseLoading(false);
    }
  }, [awiseCompany]);

  // ── Tab 6: Cash-wise Consolidated Loader ──────────────────────────

  const loadCashWise = useCallback(async () => {
    setCwiseLoading(true);
    try {
      const params = new URLSearchParams({ account_type: "CASH" });
      if (cwiseCompany) params.append("company_id", cwiseCompany);
      const res = await api.get(`/staff/accounts/general-ledger/heads?${params.toString()}`);
      if (res.data.success && res.data.heads) {
        setCwiseData(res.data.heads);
      } else {
        setCwiseData([]);
      }
    } catch (e: any) {
      toast.error(e.response?.data?.message || "Failed to load cash summary");
      setCwiseData([]);
    } finally {
      setCwiseLoading(false);
    }
  }, [cwiseCompany]);

  // ── Tab 7: Deleted Entries Loader ─────────────────────────────────

  const loadDeletedLedger = useCallback(async (page = 1) => {
    setDelLoading(true);
    setDelCurrentPage(page);
    try {
      const params = new URLSearchParams({
        page: String(page),
        page_size: "30",
        source_status: "CANCELLED",
      });
      if (delCompany) params.append("company_id", delCompany);
      if (delFromDate) params.append("date_from", delFromDate);
      if (delToDate) params.append("date_to", delToDate);
      if (delParticulars.trim()) params.append("particulars", delParticulars.trim());
      if (delRefNumber.trim()) params.append("reference_number", delRefNumber.trim());

      const res = await api.get(`/staff/accounts/party-ledger?${params.toString()}`);
      if (res.data.success) {
        setDelEntries(res.data.entries || []);
        setDelTotal(res.data.total || 0);
      } else {
        setDelEntries([]);
      }
    } catch (e: any) {
      toast.error(e.response?.data?.message || "Failed to load deleted entries");
      setDelEntries([]);
    } finally {
      setDelLoading(false);
    }
  }, [delCompany, delFromDate, delToDate, delParticulars, delRefNumber]);

  // Handle Tab Switch
  const switchTab = (tab: string) => {
    setActiveTab(tab);
    if (tab === "party") {
      loadLedger(1);
    } else if (tab === "acct") {
      loadAlAccounts();
    } else if (tab === "cash") {
      loadCashAccounts();
      loadCashLedger(1);
    } else if (tab === "pwise") {
      loadPartyWise();
    } else if (tab === "awise") {
      loadAccountWise();
    } else if (tab === "cwise") {
      loadCashWise();
    } else if (tab === "deleted") {
      loadDeletedLedger(1);
    }
  };

  // ── Period helper ─────────────────────────────────────────────────
  const setPeriodRange = (period: "month" | "quarter" | "fy" | "overall" | "custom") => {
    const today = new Date();
    const pad = (n: number) => String(n).padStart(2, "0");
    const fmtD = (d: Date) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;

    if (period === "month") {
      const start = new Date(today.getFullYear(), today.getMonth(), 1);
      const end = new Date(today.getFullYear(), today.getMonth() + 1, 0);
      setFilterFromDate(fmtD(start));
      setFilterToDate(fmtD(end > today ? today : end));
    } else if (period === "quarter") {
      const qMonth = Math.floor(today.getMonth() / 3) * 3;
      const start = new Date(today.getFullYear(), qMonth, 1);
      const end = new Date(today.getFullYear(), qMonth + 3, 0);
      setFilterFromDate(fmtD(start));
      setFilterToDate(fmtD(end > today ? today : end));
    } else if (period === "fy") {
      const m = today.getMonth();
      const y = m >= 3 ? today.getFullYear() : today.getFullYear() - 1;
      const start = new Date(y, 3, 1);
      setFilterFromDate(fmtD(start));
      setFilterToDate(fmtD(today));
    } else if (period === "overall") {
      setFilterFromDate("");
      setFilterToDate(fmtD(today));
    }
  };

  // Reset tab filters
  const resetTabFilters = (tab: string) => {
    if (tab === "party") {
      setFilterCompany("");
      setFilterPartyType("");
      setFilterPartyInput("");
      setSelectedPartyData(null);
      setFilterFromDate("");
      setFilterToDate("");
      setFilterRefNumber("");
      setFilterParticulars("");
      setFilterRefType("");
      setPlStatusChecks([]);
      loadParties();
    } else if (tab === "acct") {
      setAlFilterCompany("");
      setAlFilterType("");
      setAlFilterAccount("");
      setAlFromDate("");
      setAlToDate("");
      setAlRefNumber("");
      setAlEntries([]);
    } else if (tab === "cash") {
      setCashFilterCompany("");
      setCashFilterAccount("");
      setCashFromDate("");
      setCashToDate("");
      setCashRefNumber("");
      setCashEntries([]);
    } else if (tab === "pwise") {
      setPwiseCompany("");
      setPwisePartyType("");
      setPwisePartySearch("");
      setPwiseFromDate("");
      setPwiseToDate("");
      setPwiseData([]);
    } else if (tab === "awise") {
      setAwiseCompany("");
      setAwiseFromDate("");
      setAwiseToDate("");
      setAwiseData([]);
    } else if (tab === "cwise") {
      setCwiseCompany("");
      setCwiseFromDate("");
      setCwiseToDate("");
      setCwiseData([]);
    } else if (tab === "deleted") {
      setDelCompany("");
      setDelFromDate("");
      setDelToDate("");
      setDelParticulars("");
      setDelRefNumber("");
      setDelEntries([]);
    }
  };

  // ── Drill Down Handlers ───────────────────────────────────────────
  const drillDownParty = (partyName: string, partyType?: string) => {
    setSelectedPartyData({
      name: partyName,
      type: partyType || "ALL",
      id: 0,
      badge: partyType || "Party",
      badgeBg: "bg-gray-100",
      badgeColor: "text-gray-800",
    });
    setFilterPartyInput(partyName);
    if (partyType) setFilterPartyType(partyType);
    switchTab("party");
  };

  const drillDownAccount = (accountName: string, accountType: string) => {
    if (accountType === "CASH") {
      setCashFilterAccount(accountName);
      switchTab("cash");
    } else {
      setAlFilterAccount(accountName);
      setAlFilterType(accountType || "BANK");
      switchTab("acct");
    }
  };

  // ── Manual Entry Handlers ─────────────────────────────────────────
  const handleOpenNewEntry = () => {
    if (!filterCompany) {
      toast.error("Please select a specific company first");
      return;
    }
    setEntryDate(new Date().toISOString().split("T")[0]);
    setEntryRef("");
    setEntryVoucherType("");
    setEntryCategory("");
    setEntryParticulars("");
    setEntryType("DEBIT");
    setEntryAmount("");
    setEntryNarration("");

    if (selectedPartyData) {
      setEntryPartyVal(`${selectedPartyData.type}:${selectedPartyData.id}:${selectedPartyData.name}`);
    } else {
      setEntryPartyVal("");
    }
    setNewEntryModalOpen(true);
  };

  const handleSaveManualEntry = async () => {
    if (!entryPartyVal) {
      toast.error("Please select a party");
      return;
    }
    if (!entryDate) {
      toast.error("Please enter transaction date");
      return;
    }
    const amt = parseFloat(entryAmount);
    if (!amt || amt <= 0) {
      toast.error("Please enter a valid positive amount");
      return;
    }
    if (!filterCompany) {
      toast.error("Company is required");
      return;
    }

    const [pType, pIdStr, ...rest] = entryPartyVal.split(":");
    const pName = rest.join(":");
    const pId = parseInt(pIdStr) || 0;

    setSavingEntry(true);
    try {
      const res = await api.post("/staff/accounts/party-ledger", {
        party_type: pType,
        party_id: pId,
        party_name: pName,
        company_id: parseInt(filterCompany),
        transaction_date: entryDate,
        entry_type: entryType,
        amount: amt,
        reference_number: entryRef.trim() || undefined,
        narration: entryNarration.trim() || undefined,
        voucher_type: entryVoucherType || undefined,
        particulars: entryParticulars.trim() || undefined,
        category: entryCategory.trim() || undefined,
      });

      if (res.data.success) {
        toast.success("Ledger entry created successfully!");
        setNewEntryModalOpen(false);
        loadLedger(plCurrentPage);
      } else {
        toast.error(res.data.message || "Failed to save entry");
      }
    } catch (e: any) {
      toast.error(e.response?.data?.message || "Failed to create entry");
    } finally {
      setSavingEntry(false);
    }
  };

  // ── Edit Entry Handlers ───────────────────────────────────────────
  const handleOpenEdit = (e: LedgerEntry) => {
    setEditEntryId(e.id);
    setEditDate(e.transaction_date);
    setEditType(e.entry_type || (e.debit_amount ? "DEBIT" : "CREDIT"));
    const amt = (e.debit_amount || 0) > 0 ? e.debit_amount : e.credit_amount || 0;
    setEditAmount(String(amt));
    setEditRef(e.reference_number || "");
    setEditVchType(e.voucher_type || "");
    setEditParticulars(e.particulars || "");
    setEditNarration(e.narration || "");
    setEditModalOpen(true);
  };

  const handleSaveEdit = async () => {
    if (!editEntryId) return;
    const amt = parseFloat(editAmount);
    if (!amt || amt <= 0) {
      toast.error("Amount must be greater than 0");
      return;
    }

    setSavingEdit(true);
    try {
      const res = await api.patch(`/staff/accounts/party-ledger/${editEntryId}`, {
        transaction_date: editDate,
        entry_type: editType,
        amount: amt,
        reference_number: editRef.trim() || undefined,
        voucher_type: editVchType.trim() || undefined,
        particulars: editParticulars.trim() || undefined,
        narration: editNarration.trim() || undefined,
      });

      if (res.data.success) {
        toast.success("Entry updated successfully!");
        setEditModalOpen(false);
        loadLedger(plCurrentPage);
      } else {
        toast.error(res.data.message || "Update failed");
      }
    } catch (e: any) {
      toast.error(e.response?.data?.message || "Failed to update entry");
    } finally {
      setSavingEdit(false);
    }
  };

  // ── Delete Entry Handler ──────────────────────────────────────────
  const handleDeleteEntry = async (id: number) => {
    if (!confirm("Are you sure you want to delete this ledger entry? Running balances will be automatically recalculated.")) return;

    try {
      const res = await api.delete(`/staff/accounts/party-ledger/${id}`);
      if (res.data.success) {
        toast.success("Entry deleted and balances recomputed.");
        loadLedger(plCurrentPage);
      } else {
        toast.error(res.data.message || "Delete failed");
      }
    } catch (e: any) {
      toast.error(e.response?.data?.message || "Delete request failed");
    }
  };

  // ── View Source Document Handler ──────────────────────────────────
  const handleViewSourceDoc = async (entry: LedgerEntry) => {
    setViewDocCurrentEntry(entry);
    setViewDocModalOpen(true);
    setViewDocLoading(true);
    setViewDocData(null);

    const refType = (entry.reference_type || "").toUpperCase();
    const refId = entry.reference_id;
    setViewDocRefType(refType);

    try {
      if (refType === "SALES_INVOICE" && refId) {
        setViewDocTitle("Sales Invoice Document");
        const cid = filterCompany || entry.company_id || "";
        const res = await api.get(`/staff/accounts/sales-invoices/${refId}?company_id=${cid}`);
        setViewDocData(res.data.invoice || res.data);
      } else if (refType === "VENDOR_TXN" && refId) {
        setViewDocTitle("Purchase / Vendor Transaction");
        const res = await api.get(`/staff/accounts/vendor-transactions/${refId}`);
        setViewDocData(res.data.transaction || res.data);
      } else if (refType === "INCOME" && refId) {
        setViewDocTitle("Income Entry Record");
        const res = await api.get(`/staff/accounts/income-entries/${refId}`);
        setViewDocData(res.data.entry || res.data);
      } else if (refType === "EXPENSE" && refId) {
        setViewDocTitle("Expense Entry Record");
        const res = await api.get(`/staff/accounts/expense-entries/${refId}`);
        setViewDocData(res.data.entry || res.data);
      } else {
        setViewDocTitle("Ledger Entry Details");
        setViewDocData(entry);
      }
    } catch (e: any) {
      toast.error("Failed to load source document details");
    } finally {
      setViewDocLoading(false);
    }
  };

  // ── Tally Modal & File Upload Handlers ─────────────────────────────
  const handleOpenTallyModal = () => {
    if (!filterCompany) {
      toast.error("Please select a specific company first");
      return;
    }
    setTallyStep(1);
    setTallyFile(null);
    setTallyPreview([]);
    setTallyPdfDetectedParty(null);
    setTallyImportResult(null);
    setRenameResultMsg(null);

    if (selectedPartyData) {
      setTallyPartyInput(selectedPartyData.name);
      setTallyPartyType(selectedPartyData.type || "VENDOR");
      setTallySelectedParty(selectedPartyData);
    } else {
      setTallyPartyInput("");
      setTallyPartyType("VENDOR");
      setTallySelectedParty(null);
    }
    setTallyModalOpen(true);
  };

  const handleProcessTallyFile = (file: File) => {
    setTallyFile(file);
    setTallyPdfDetectedParty(null);

    const reader = new FileReader();
    reader.onload = (e) => {
      const content = String(e.target?.result || "");
      const fname = file.name.toLowerCase();
      const entries: TallyPreviewItem[] = [];

      if (fname.endsWith(".xml") || content.includes("<ENVELOPE>") || content.includes("<VOUCHER")) {
        try {
          const parser = new DOMParser();
          const xml = parser.parseFromString(content, "text/xml");
          xml.querySelectorAll("VOUCHER").forEach((v) => {
            const date = v.querySelector("DATE")?.textContent?.trim() || "";
            const vno = v.querySelector("VOUCHERNUMBER")?.textContent?.trim() || "";
            const vtype = v.querySelector("VOUCHERTYPENAME")?.textContent?.trim() || "";
            v.querySelectorAll("ALLLEDGERENTRIES\\.LIST, LEDGERENTRIES\\.LIST").forEach((le) => {
              const amt = parseFloat(le.querySelector("AMOUNT")?.textContent || "0");
              const lname = le.querySelector("LEDGERNAME")?.textContent?.trim() || "";
              if (amt !== 0) {
                entries.push({
                  date,
                  ref: vno,
                  vtype,
                  part: lname,
                  debit: amt < 0 ? Math.abs(amt) : 0,
                  credit: amt > 0 ? amt : 0,
                });
              }
            });
          });
        } catch {}
      } else if (fname.endsWith(".csv")) {
        const lines = content.split("\n").filter((l) => l.trim());
        if (lines.length > 1) {
          const hdrs = lines[0].split(",").map((h) => h.trim().replace(/"/g, "").toLowerCase());
          for (let i = 1; i < lines.length && i < 10; i++) {
            const cols = lines[i].split(",").map((c) => c.trim().replace(/"/g, ""));
            const row: Record<string, string> = {};
            hdrs.forEach((h, j) => (row[h] = cols[j] || ""));
            const d = parseFloat(row["debit"] || "0") || 0;
            const c = parseFloat(row["credit"] || "0") || 0;
            entries.push({
              date: row["date"] || "",
              ref: row["reference"] || row["vch no"] || "",
              vtype: row["vch type"] || row["type"] || "",
              part: row["particulars"] || "",
              debit: d,
              credit: c,
            });
          }
        }
      } else {
        // Text / PDF
        const lines = content.split("\n");
        let hdrIdx = -1;
        for (let i = 0; i < lines.length; i++) {
          if (lines[i].includes("Date") && lines[i].includes("Particulars")) {
            hdrIdx = i;
            break;
          }
        }
        if (hdrIdx > 0) {
          let prevLine = "";
          for (let i = 0; i < hdrIdx; i++) {
            const ls = lines[i].trim();
            if (!ls) continue;
            if (ls.includes("Ledger Account") && prevLine) {
              setTallyPdfDetectedParty(prevLine);
              break;
            }
            prevLine = ls;
          }
        }
      }
      setTallyPreview(entries.slice(0, 5));
    };
    reader.readAsText(file);
  };

  const handleImportTally = async () => {
    const typedName = tallyPartyInput.trim();
    if (!tallyFile || !typedName || !filterCompany) {
      toast.error("Party name, company, and ledger file are required");
      return;
    }

    const matchedParty = allParties.find((p) => p.name.toLowerCase() === typedName.toLowerCase());
    const finalParty = matchedParty || {
      type: tallyPartyType || "EXTERNAL",
      id: 0,
      name: typedName,
    };

    setImportingTally(true);
    const formData = new FormData();
    formData.append("file", tallyFile);
    formData.append("company_id", filterCompany);
    formData.append("party_type", finalParty.type);
    formData.append("party_id", String(finalParty.id));
    formData.append("party_name", finalParty.name);

    try {
      const res = await api.post("/staff/accounts/party-ledger/tally-import", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      const data = res.data;
      if (data.success) {
        setTallyImportResult(data);
        setTallyStep(2);
        toast.success(data.message || "Tally ledger imported successfully!");
      } else {
        toast.error(data.message || "Import failed");
      }
    } catch (e: any) {
      toast.error(e.response?.data?.message || "Import request failed");
    } finally {
      setImportingTally(false);
    }
  };

  const handleRenameImportedParty = async (newName: string, oldName: string, partyType: string) => {
    setRenamingParty(true);
    setRenameResultMsg(null);
    try {
      const res = await api.patch("/staff/accounts/party-ledger/rename-party", {
        company_id: parseInt(filterCompany),
        party_id: tallySelectedParty?.id || 0,
        party_type: partyType,
        old_party_name: oldName,
        new_party_name: newName,
      });

      if (res.data.success) {
        setRenameResultMsg({
          text: `Successfully renamed ${res.data.updated} entries to "${newName}".`,
          isError: false,
        });
        setTallyPartyInput(newName);
        if (selectedPartyData) {
          setSelectedPartyData({ ...selectedPartyData, name: newName });
        }
      } else {
        setRenameResultMsg({ text: res.data.message || "Rename failed", isError: true });
      }
    } catch (e: any) {
      setRenameResultMsg({ text: e.response?.data?.message || "Rename failed", isError: true });
    } finally {
      setRenamingParty(false);
    }
  };

  // ── Fix Party Modal Handlers ──────────────────────────────────────
  const handleOpenFixParty = (r: PartyWiseRow) => {
    setFixPartyData({
      partyName: r.party_name,
      partyType: r.party_type,
      partyId: r.party_id || 0,
      companyId: r.company_id || parseInt(pwiseCompany) || 0,
    });
    setFpNewName(r.party_name);
    setFpNewType(r.party_type);
    setFixPartyModalOpen(true);
  };

  const handleSaveFixParty = async () => {
    if (!fixPartyData || !fpNewName.trim()) {
      toast.error("Party name is required");
      return;
    }

    setSavingFixParty(true);
    try {
      const payload: any = {
        company_id: fixPartyData.companyId,
        party_id: fixPartyData.partyId,
        party_type: fixPartyData.partyType,
        old_party_name: fixPartyData.partyName,
        new_party_name: fpNewName.trim(),
      };
      if (fpNewType !== fixPartyData.partyType) {
        payload.new_party_type = fpNewType;
      }

      const res = await api.patch("/staff/accounts/party-ledger/rename-party", payload);
      if (res.data.success) {
        toast.success(`Updated ${res.data.updated} entries for ${fpNewName}`);
        setFixPartyModalOpen(false);
        loadPartyWise();
      } else {
        toast.error(res.data.message || "Update failed");
      }
    } catch (e: any) {
      toast.error(e.response?.data?.message || "Failed to update party");
    } finally {
      setSavingFixParty(false);
    }
  };

  // ── Export & Print Handlers ───────────────────────────────────────

  const printPartyStatement = () => {
    const compName = companies.find((c) => String(c.id) === String(filterCompany))?.company_name || "All Companies";
    const partyName = selectedPartyData?.name || filterPartyInput || "All Parties";
    const dateRange = filterFromDate || filterToDate ? `${fmtDate(filterFromDate)} – ${fmtDate(filterToDate)}` : "All Dates";

    const obFmt = fmt(Math.abs(plOpeningBal));
    const obSign = plOpeningBal < 0 ? "Cr" : plOpeningBal > 0 ? "Dr" : "";

    let rowsHtml = `
      <tr style="background:#f8fafc; font-weight:bold;">
        <td>—</td>
        <td>${filterFromDate ? "As of " + fmtDate(filterFromDate) : "Opening"}</td>
        <td colspan="4">Opening Balance Brought Forward</td>
        <td style="text-align:right;">${plOpeningBal < 0 ? obFmt : "—"}</td>
        <td style="text-align:right;">${plOpeningBal > 0 ? obFmt : "—"}</td>
        <td style="text-align:right;">${obFmt} ${obSign}</td>
      </tr>
    `;

    plEntries.forEach((e, idx) => {
      const dr = (e.debit_amount || 0) > 0 ? fmt(e.debit_amount) : "—";
      const cr = (e.credit_amount || 0) > 0 ? fmt(e.credit_amount) : "—";
      const bal = fmtBal(e.running_balance);
      rowsHtml += `
        <tr>
          <td>${idx + 1}</td>
          <td>${fmtDate(e.transaction_date)}</td>
          <td>${e.reference_number || "—"}</td>
          <td>${e.voucher_type || "—"}</td>
          <td>${e.particulars || "—"}</td>
          <td>${e.narration || "—"}</td>
          <td style="text-align:right; color:#dc2626;">${dr}</td>
          <td style="text-align:right; color:#059669;">${cr}</td>
          <td style="text-align:right; font-weight:600;">${bal.text} ${bal.label}</td>
        </tr>
      `;
    });

    const grandBal = fmtBal(plClosingBal);
    rowsHtml += `
      <tr style="background:#f5f3ff; font-weight:bold; border-top:2px solid #6366f1;">
        <td colspan="6" style="padding:10px;">Grand Total</td>
        <td style="text-align:right; color:#dc2626; padding:10px;">${fmt(plTotalDebit)}</td>
        <td style="text-align:right; color:#059669; padding:10px;">${fmt(plTotalCredit)}</td>
        <td style="text-align:right; padding:10px;">${grandBal.text} ${grandBal.label}</td>
      </tr>
    `;

    const printWin = window.open("", "_blank");
    if (!printWin) {
      toast.error("Please allow popups to print statement");
      return;
    }

    printWin.document.write(`
      <!DOCTYPE html>
      <html>
      <head>
        <title>Party Ledger — ${partyName}</title>
        <style>
          body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; padding: 24px; color: #1f2937; }
          .header { display: flex; justify-content: space-between; border-bottom: 2px solid #e5e7eb; padding-bottom: 16px; margin-bottom: 20px; }
          .title { font-size: 22px; font-weight: 800; color: #4338ca; }
          .meta { font-size: 12px; color: #6b7280; margin-top: 4px; }
          .summary-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 20px; }
          .sum-card { background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 8px; padding: 12px; text-align: center; }
          .sum-val { font-size: 16px; font-weight: 700; }
          .sum-lbl { font-size: 11px; color: #6b7280; margin-top: 2px; }
          table { width: 100%; border-collapse: collapse; font-size: 11px; }
          th { background: #f3f4f6; text-align: left; padding: 8px 10px; border-bottom: 2px solid #e5e7eb; font-weight: 600; color: #4b5563; }
          td { padding: 7px 10px; border-bottom: 1px solid #f3f4f6; }
          @media print { body { padding: 0; } @page { margin: 15mm; size: landscape; } }
        </style>
      </head>
      <body>
        <div class="header">
          <div>
            <div class="title">${compName} — Party Ledger Statement</div>
            <div class="meta">Party: <strong>${partyName}</strong> &nbsp;|&nbsp; Period: <strong>${dateRange}</strong></div>
          </div>
          <div style="text-align:right; font-size:11px; color:#9ca3af;">
            Generated on ${new Date().toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" })}
          </div>
        </div>

        <div class="summary-grid">
          <div class="sum-card"><div class="sum-val" style="color:#6366f1;">${fmt(plOpeningBal)}</div><div class="sum-lbl">Opening Balance</div></div>
          <div class="sum-card"><div class="sum-val" style="color:#dc2626;">${fmt(plTotalDebit)}</div><div class="sum-lbl">Total Debit</div></div>
          <div class="sum-card"><div class="sum-val" style="color:#059669;">${fmt(plTotalCredit)}</div><div class="sum-lbl">Total Credit</div></div>
          <div class="sum-card"><div class="sum-val" style="color:#1d4ed8;">${fmt(plClosingBal)}</div><div class="sum-lbl">Closing Balance</div></div>
        </div>

        <table>
          <thead>
            <tr>
              <th>#</th><th>Date</th><th>Vch No.</th><th>Type</th><th>Particulars</th><th>Narration</th>
              <th style="text-align:right;">Debit (₹)</th><th style="text-align:right;">Credit (₹)</th><th style="text-align:right;">Balance (₹)</th>
            </tr>
          </thead>
          <tbody>${rowsHtml}</tbody>
        </table>
        <script>window.onload = () => { window.print(); };</script>
      </body>
      </html>
    `);
    printWin.document.close();
  };

  const exportConsolidatedCsv = (tab: "pwise" | "awise" | "cwise") => {
    let filename = "summary";
    let rows: string[][] = [];

    if (tab === "pwise") {
      filename = "party-wise-summary";
      rows.push(["#", "Party Name", "Party Type", "Entries", "Total Debit", "Total Credit", "Net Balance", "Last Transaction"]);
      filteredPwiseRows.forEach((r, idx) => {
        rows.push([
          String(idx + 1),
          r.party_name || "",
          r.party_type || "",
          String(r.entry_count),
          String(r.total_debit || 0),
          String(r.total_credit || 0),
          String(r.net_balance || 0),
          r.last_date || "",
        ]);
      });
    } else if (tab === "awise") {
      filename = "bank-account-wise-summary";
      rows.push(["#", "Bank Account Name", "Type", "Total Debit (In)", "Total Credit (Out)", "Balance", "Last Transaction"]);
      awiseData.forEach((r, idx) => {
        rows.push([
          String(idx + 1),
          r.account_name || "",
          r.account_type || "BANK",
          String(r.total_debit || 0),
          String(r.total_credit || 0),
          String(r.balance || 0),
          r.last_date || "",
        ]);
      });
    } else if (tab === "cwise") {
      filename = "cash-wise-summary";
      rows.push(["#", "Cash Account Name", "Type", "Total Cash In", "Total Cash Out", "Balance", "Last Transaction"]);
      cwiseData.forEach((r, idx) => {
        rows.push([
          String(idx + 1),
          r.account_name || "",
          "CASH",
          String(r.total_debit || 0),
          String(r.total_credit || 0),
          String(r.balance || 0),
          r.last_date || "",
        ]);
      });
    }

    if (!rows.length) return;
    const csvContent = "data:text/csv;charset=utf-8," + rows.map((e) => e.map((val) => `"${val.replace(/"/g, '""')}"`).join(",")).join("\n");
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `${filename}-${new Date().toISOString().split("T")[0]}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  // ── Render ────────────────────────────────────────────────────────

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-[1600px] mx-auto space-y-6 animate-in fade-in duration-300">
      <Toaster position="top-right" />

      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white p-5 rounded-2xl border border-gray-100 shadow-sm">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2.5 tracking-tight">
            <div className="p-2 bg-indigo-50 text-indigo-600 rounded-xl">
              <BookOpen className="w-6 h-6" />
            </div>
            Party Ledger & Statements
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            Track consolidated transaction histories, balances, Tally imports, and bank statements for vendors, customers, and staff.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          {filterCompany && (
            <>
              <button
                onClick={handleOpenTallyModal}
                className="inline-flex items-center gap-2 px-3.5 py-2 bg-amber-500 hover:bg-amber-600 text-white font-semibold text-xs rounded-xl shadow-sm hover:shadow transition-all"
              >
                <Upload className="w-4 h-4" />
                Upload Tally Ledger
              </button>
              <button
                onClick={handleOpenNewEntry}
                className="inline-flex items-center gap-2 px-3.5 py-2 bg-emerald-600 hover:bg-emerald-700 text-white font-semibold text-xs rounded-xl shadow-sm hover:shadow transition-all"
              >
                <PlusCircle className="w-4 h-4" />
                New Entry
              </button>
            </>
          )}
        </div>
      </div>

      {/* Page Tabs */}
      <div className="flex items-center gap-1.5 overflow-x-auto border-b border-gray-200 pb-1 scrollbar-none">
        {[
          { id: "party", label: "Party Ledger", icon: <BookOpen className="w-4 h-4" /> },
          { id: "acct", label: "Account Ledger", icon: <Landmark className="w-4 h-4" /> },
          { id: "cash", label: "Cash Ledger", icon: <Wallet className="w-4 h-4" /> },
          { id: "pwise", label: "Party-wise", icon: <Users className="w-4 h-4" /> },
          { id: "awise", label: "Account-wise (Bank)", icon: <Layers className="w-4 h-4" /> },
          { id: "cwise", label: "Cash-wise", icon: <Coins className="w-4 h-4" /> },
          { id: "deleted", label: "Deleted Entries", icon: <Trash2 className="w-4 h-4 text-red-500" /> },
        ].map((t) => {
          const isActive = activeTab === t.id;
          return (
            <button
              key={t.id}
              onClick={() => switchTab(t.id)}
              className={`inline-flex items-center gap-2 px-4 py-2.5 text-xs font-semibold rounded-t-xl transition-all whitespace-nowrap border-b-2 ${
                isActive
                  ? "border-indigo-600 text-indigo-600 bg-indigo-50/50"
                  : "border-transparent text-gray-500 hover:text-gray-900 hover:bg-gray-50"
              }`}
            >
              {t.icon}
              {t.label}
            </button>
          );
        })}
      </div>

      {/* ─────────────────────────────────────────────────────────── */}
      {/* TAB 1: PARTY LEDGER                                         */}
      {/* ─────────────────────────────────────────────────────────── */}
      {activeTab === "party" && (
        <div className="space-y-6">
          {/* Filters Card */}
          <div className="bg-white rounded-2xl border border-gray-200/80 shadow-sm p-5 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-gray-100">
              <div className="flex items-center gap-2 text-xs font-bold text-gray-700 uppercase tracking-wider">
                <Filter className="w-4 h-4 text-indigo-500" />
                Search & Filters
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => resetTabFilters("party")}
                  className="inline-flex items-center gap-1.5 px-2.5 py-1 text-xs text-gray-500 hover:text-gray-800 bg-gray-50 hover:bg-gray-100 rounded-lg transition-all"
                >
                  <RotateCcw className="w-3.5 h-3.5" />
                  Reset
                </button>
                <button
                  onClick={() => loadLedger(1)}
                  className="inline-flex items-center gap-1.5 px-4 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-xs rounded-lg shadow-sm transition-all"
                >
                  <Search className="w-3.5 h-3.5" />
                  Load Ledger
                </button>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6 gap-3.5">
              {/* Company */}
              <div className="space-y-1">
                <label className="text-[11px] font-bold text-gray-600 uppercase tracking-wider">Company</label>
                <select
                  value={filterCompany}
                  onChange={(e) => {
                    setFilterCompany(e.target.value);
                    loadParties(e.target.value, filterPartyType);
                  }}
                  className="w-full h-9 px-3 text-xs bg-white border border-gray-200 rounded-xl focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all"
                >
                  <option value="">All Companies</option>
                  {companies.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.company_name || c.name}
                    </option>
                  ))}
                </select>
              </div>

              {/* Party Type */}
              <div className="space-y-1">
                <label className="text-[11px] font-bold text-gray-600 uppercase tracking-wider">Party Type</label>
                <select
                  value={filterPartyType}
                  onChange={(e) => {
                    setFilterPartyType(e.target.value);
                    loadParties(filterCompany, e.target.value);
                  }}
                  className="w-full h-9 px-3 text-xs bg-white border border-gray-200 rounded-xl focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all"
                >
                  <option value="">All Types</option>
                  <option value="VENDOR">Vendor / Supplier</option>
                  <option value="PARTNER">Partner</option>
                  <option value="CUSTOMER">Customer</option>
                  <option value="EMPLOYEE">Staff / Employee</option>
                  <option value="EXTERNAL">External Party</option>
                </select>
              </div>

              {/* Party Name Combobox */}
              <div className="space-y-1 relative xl:col-span-2">
                <label className="text-[11px] font-bold text-gray-600 uppercase tracking-wider">Party Name</label>
                <div className="relative">
                  <input
                    type="text"
                    value={filterPartyInput}
                    placeholder="Search or type party name..."
                    autoComplete="off"
                    onChange={(e) => {
                      setFilterPartyInput(e.target.value);
                      setPartyComboOpen(true);
                    }}
                    onFocus={() => setPartyComboOpen(true)}
                    onKeyDown={(e) => {
                      if (e.key === "Escape") setPartyComboOpen(false);
                      if (e.key === "Enter") {
                        const match = allParties.find((p) => p.name.toLowerCase() === filterPartyInput.trim().toLowerCase());
                        if (match) setSelectedPartyData(match);
                        else setSelectedPartyData({ type: "EXTERNAL", id: 0, name: filterPartyInput.trim() });
                        setPartyComboOpen(false);
                        loadLedger(1);
                      }
                    }}
                    className="w-full h-9 px-3 text-xs bg-white border border-gray-200 rounded-xl focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all"
                  />
                  {filterPartyInput && (
                    <button
                      type="button"
                      onClick={() => {
                        setFilterPartyInput("");
                        setSelectedPartyData(null);
                      }}
                      className="absolute right-2.5 top-2.5 text-gray-400 hover:text-gray-600"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  )}
                </div>

                {partyComboOpen && (
                  <div className="absolute top-full left-0 right-0 z-50 mt-1 bg-white border border-gray-200 rounded-xl shadow-xl max-h-56 overflow-y-auto divide-y divide-gray-50">
                    {allParties
                      .filter((p) => !filterPartyInput || p.name.toLowerCase().includes(filterPartyInput.toLowerCase()))
                      .slice(0, 20)
                      .map((p, idx) => (
                        <div
                          key={idx}
                          onMouseDown={(e) => {
                            e.preventDefault();
                            setSelectedPartyData(p);
                            setFilterPartyInput(p.name);
                            setPartyComboOpen(false);
                          }}
                          className="p-2.5 hover:bg-indigo-50 cursor-pointer flex items-center justify-between text-xs transition-colors"
                        >
                          <span className="font-medium text-gray-800">{p.name}</span>
                          <span className={`px-2 py-0.5 rounded text-[10px] font-semibold border ${p.badgeBg || "bg-gray-100"} ${p.badgeColor || "text-gray-700"}`}>
                            {p.badge || p.type}
                          </span>
                        </div>
                      ))}
                    {filterPartyInput.trim() && (
                      <div
                        onMouseDown={(e) => {
                          e.preventDefault();
                          setSelectedPartyData({ type: "EXTERNAL", id: 0, name: filterPartyInput.trim() });
                          setPartyComboOpen(false);
                        }}
                        className="p-2.5 bg-amber-50/50 hover:bg-amber-100/60 text-amber-900 cursor-pointer flex items-center gap-2 text-xs font-semibold"
                      >
                        <span className="px-1.5 py-0.5 bg-amber-200 rounded text-[9px]">Custom</span>
                        Use &quot;{filterPartyInput.trim()}&quot;
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* Reference Type */}
              <div className="space-y-1">
                <label className="text-[11px] font-bold text-gray-600 uppercase tracking-wider">Ref Type</label>
                <select
                  value={filterRefType}
                  onChange={(e) => setFilterRefType(e.target.value)}
                  className="w-full h-9 px-3 text-xs bg-white border border-gray-200 rounded-xl focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all"
                >
                  <option value="">All Types</option>
                  <option value="INCOME">Income (Receipts)</option>
                  <option value="SALES_INVOICE">Sales Invoice</option>
                  <option value="PURCHASE_INVOICE">Purchase Invoice</option>
                  <option value="VENDOR_TXN">Vendor Transaction</option>
                  <option value="EXPENSE">Expense</option>
                  <option value="FUND_TRANSFER">Fund Transfer</option>
                  <option value="OPENING">Opening Balance</option>
                  <option value="JOURNAL">Journal Voucher</option>
                </select>
              </div>

              {/* Voucher Status Multi-select */}
              <div className="space-y-1 relative">
                <label className="text-[11px] font-bold text-gray-600 uppercase tracking-wider">Voucher Status</label>
                <button
                  type="button"
                  onClick={() => setStatusMenuOpen(!statusMenuOpen)}
                  className="w-full h-9 px-3 text-xs bg-white border border-gray-200 rounded-xl flex items-center justify-between text-gray-700 text-left focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500"
                >
                  <span className="truncate">
                    {!plStatusChecks.length
                      ? "All Statuses"
                      : plStatusChecks.length === 1
                      ? plStatusChecks[0]
                      : `${plStatusChecks.length} Selected`}
                  </span>
                  <ChevronDown className="w-3.5 h-3.5 text-gray-400 ml-1" />
                </button>

                {statusMenuOpen && (
                  <div className="absolute top-full left-0 right-0 z-50 mt-1 bg-white border border-gray-200 rounded-xl shadow-xl p-2 space-y-1">
                    {[
                      { val: "CONFIRMED", label: "Confirmed" },
                      { val: "MANUAL", label: "Manual Entry" },
                      { val: "TALLY_IMPORT", label: "Tally Import" },
                      { val: "OPENING_BALANCE", label: "Opening Balance" },
                      { val: "CANCELLED", label: "Cancelled" },
                    ].map((s) => (
                      <label
                        key={s.val}
                        className="flex items-center gap-2 p-1.5 hover:bg-gray-50 rounded-lg cursor-pointer text-xs text-gray-700"
                      >
                        <input
                          type="checkbox"
                          checked={plStatusChecks.includes(s.val)}
                          onChange={(e) => {
                            if (e.target.checked) setPlStatusChecks([...plStatusChecks, s.val]);
                            else setPlStatusChecks(plStatusChecks.filter((x) => x !== s.val));
                          }}
                          className="rounded text-indigo-600 focus:ring-indigo-500 h-3.5 w-3.5"
                        />
                        {s.label}
                      </label>
                    ))}
                  </div>
                )}
              </div>

              {/* Ref # Search */}
              <div className="space-y-1">
                <label className="text-[11px] font-bold text-gray-600 uppercase tracking-wider">Ref # / Invoice #</label>
                <input
                  type="text"
                  value={filterRefNumber}
                  onChange={(e) => setFilterRefNumber(e.target.value)}
                  placeholder="e.g. INV-2026-001"
                  className="w-full h-9 px-3 text-xs bg-white border border-gray-200 rounded-xl focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500"
                />
              </div>

              {/* Particulars / SKU Search */}
              <div className="space-y-1">
                <label className="text-[11px] font-bold text-gray-600 uppercase tracking-wider">Particulars / SKU</label>
                <input
                  type="text"
                  value={filterParticulars}
                  onChange={(e) => setFilterParticulars(e.target.value)}
                  placeholder="e.g. Battery, Union Bank..."
                  className="w-full h-9 px-3 text-xs bg-white border border-gray-200 rounded-xl focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500"
                />
              </div>

              {/* From Date */}
              <div className="space-y-1">
                <label className="text-[11px] font-bold text-gray-600 uppercase tracking-wider">From Date</label>
                <input
                  type="date"
                  value={filterFromDate}
                  onChange={(e) => setFilterFromDate(e.target.value)}
                  className="w-full h-9 px-2.5 text-xs bg-white border border-gray-200 rounded-xl focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500"
                />
              </div>

              {/* To Date */}
              <div className="space-y-1">
                <label className="text-[11px] font-bold text-gray-600 uppercase tracking-wider">To Date</label>
                <input
                  type="date"
                  value={filterToDate}
                  onChange={(e) => setFilterToDate(e.target.value)}
                  className="w-full h-9 px-2.5 text-xs bg-white border border-gray-200 rounded-xl focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500"
                />
              </div>

              {/* Quick Period Buttons */}
              <div className="xl:col-span-2 space-y-1">
                <label className="text-[11px] font-bold text-gray-600 uppercase tracking-wider">Quick Period</label>
                <div className="flex items-center gap-1 flex-wrap">
                  {(["month", "quarter", "fy", "overall"] as const).map((p) => (
                    <button
                      key={p}
                      type="button"
                      onClick={() => setPeriodRange(p)}
                      className="px-2.5 py-1.5 text-[11px] font-medium bg-gray-50 hover:bg-indigo-50 hover:text-indigo-600 text-gray-600 border border-gray-200 rounded-lg transition-all"
                    >
                      {p === "month" ? "This Month" : p === "quarter" ? "Quarter" : p === "fy" ? "FY" : "All Time"}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* Party Banner Bar */}
          <div className="bg-gradient-to-r from-indigo-50 via-blue-50 to-purple-50 border border-indigo-100/80 rounded-2xl p-4 flex flex-wrap items-center justify-between gap-4 shadow-sm">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-indigo-600 text-white flex items-center justify-center font-bold text-base shadow-sm">
                {(selectedPartyData?.name || filterPartyInput || "A").charAt(0).toUpperCase()}
              </div>
              <div>
                <h3 className="text-base font-bold text-gray-900 flex items-center gap-2">
                  {selectedPartyData?.name || filterPartyInput || "All Parties Statement"}
                  {selectedPartyData?.badge && (
                    <span className={`px-2 py-0.5 text-[10px] font-bold rounded-full border ${selectedPartyData.badgeBg} ${selectedPartyData.badgeColor}`}>
                      {selectedPartyData.badge}
                    </span>
                  )}
                </h3>
                <p className="text-xs text-gray-500">
                  {filterCompany ? companies.find((c) => String(c.id) === String(filterCompany))?.company_name : "All Companies"} ·{" "}
                  {filterFromDate || filterToDate ? `${fmtDate(filterFromDate)} to ${fmtDate(filterToDate)}` : "All Time"}
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={printPartyStatement}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-white hover:bg-gray-50 text-indigo-700 font-semibold text-xs rounded-xl border border-indigo-200 shadow-sm transition-all"
              >
                <Printer className="w-3.5 h-3.5" />
                Print Statement / PDF
              </button>
            </div>
          </div>

          {/* KPI Summary Row */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="bg-white p-4 rounded-2xl border border-gray-200/70 shadow-sm text-center space-y-1">
              <div className="text-[11px] font-bold text-indigo-600 uppercase tracking-wider">Opening Balance</div>
              <div className="text-xl font-bold font-mono text-indigo-900">{fmt(plOpeningBal)}</div>
              <div className="text-[10px] text-gray-400">
                {plOpeningDate ? `As on ${fmtDate(plOpeningDate)}` : "Start of Period"}
              </div>
            </div>

            <div className="bg-white p-4 rounded-2xl border border-gray-200/70 shadow-sm text-center space-y-1">
              <div className="text-[11px] font-bold text-red-600 uppercase tracking-wider">Total Debit (Dr)</div>
              <div className="text-xl font-bold font-mono text-red-700">{fmt(plTotalDebit)}</div>
              <div className="text-[10px] text-gray-400">Outflows / Receivables</div>
            </div>

            <div className="bg-white p-4 rounded-2xl border border-gray-200/70 shadow-sm text-center space-y-1">
              <div className="text-[11px] font-bold text-emerald-600 uppercase tracking-wider">Total Credit (Cr)</div>
              <div className="text-xl font-bold font-mono text-emerald-700">{fmt(plTotalCredit)}</div>
              <div className="text-[10px] text-gray-400">Inflows / Payables</div>
            </div>

            <div className="bg-white p-4 rounded-2xl border border-gray-200/70 shadow-sm text-center space-y-1">
              <div className="text-[11px] font-bold text-blue-600 uppercase tracking-wider">Closing Balance</div>
              <div className="text-xl font-bold font-mono text-blue-900">{fmt(plClosingBal)}</div>
              <div className="text-[10px] text-gray-400">
                {plClosingBal > 0 ? "Dr (Payable)" : plClosingBal < 0 ? "Cr (Advance / Receivable)" : "Settled"}
              </div>
            </div>
          </div>

          {/* Ledger Table Card */}
          <div className="bg-white rounded-2xl border border-gray-200/80 shadow-sm overflow-hidden">
            <div className="p-4 border-b border-gray-100 flex items-center justify-between bg-gray-50/50">
              <div className="flex items-center gap-2">
                <ListFilter className="w-4 h-4 text-gray-500" />
                <span className="text-xs font-bold text-gray-700 uppercase tracking-wider">Ledger Entries</span>
                <span className="px-2 py-0.5 text-[10px] font-semibold bg-gray-200 text-gray-700 rounded-full">
                  {plTotal} records
                </span>
              </div>
            </div>

            {plLoading ? (
              <div className="p-16 text-center text-gray-500 space-y-3">
                <RefreshCw className="w-8 h-8 animate-spin text-indigo-600 mx-auto" />
                <p className="text-xs font-medium">Loading ledger records...</p>
              </div>
            ) : plEntries.length === 0 ? (
              <div className="p-16 text-center text-gray-400 space-y-2">
                <BookOpen className="w-12 h-12 text-gray-300 mx-auto" />
                <h4 className="text-sm font-semibold text-gray-700">No Entries Found</h4>
                <p className="text-xs text-gray-400">No ledger transactions match the current filters.</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse text-xs">
                  <thead>
                    <tr className="bg-gray-50/90 text-gray-600 font-semibold border-b border-gray-200 text-[11px] uppercase tracking-wider">
                      <th className="py-3 px-3 w-10">#</th>
                      <th className="py-3 px-3 whitespace-nowrap">Date</th>
                      <th className="py-3 px-3">Party Name</th>
                      <th className="py-3 px-3">Vch No.</th>
                      <th className="py-3 px-3">Vch Type</th>
                      <th className="py-3 px-3">Category</th>
                      <th className="py-3 px-3">Sub-Category</th>
                      <th className="py-3 px-3 min-w-[140px]">Particulars</th>
                      <th className="py-3 px-3 min-w-[140px]">Description</th>
                      <th className="py-3 px-3 text-right">Debit (₹)</th>
                      <th className="py-3 px-3 text-right">Credit (₹)</th>
                      <th className="py-3 px-3 text-right whitespace-nowrap">Balance</th>
                      <th className="py-3 px-3 text-center">Source</th>
                      <th className="py-3 px-3 text-center">Actions</th>
                    </tr>
                  </thead>

                  <tbody className="divide-y divide-gray-100">
                    {/* Opening Balance Pinned Row */}
                    <tr className="bg-indigo-50/30 font-semibold text-gray-800 border-b border-indigo-100">
                      <td className="py-2.5 px-3 text-gray-400">—</td>
                      <td className="py-2.5 px-3 whitespace-nowrap text-indigo-900">
                        {filterFromDate ? `As of ${fmtDate(filterFromDate)}` : "Opening"}
                      </td>
                      <td colSpan={4} className="py-2.5 px-3 text-indigo-900">
                        Opening Balance Brought Forward
                      </td>
                      <td className="py-2.5 px-3 text-gray-400">—</td>
                      <td className="py-2.5 px-3 text-gray-400">—</td>
                      <td className="py-2.5 px-3 text-gray-400">—</td>
                      <td className="py-2.5 px-3 text-right text-red-600">
                        {plOpeningBal < 0 ? fmt(Math.abs(plOpeningBal)) : "—"}
                      </td>
                      <td className="py-2.5 px-3 text-right text-emerald-600">
                        {plOpeningBal > 0 ? fmt(Math.abs(plOpeningBal)) : "—"}
                      </td>
                      <td className="py-2.5 px-3 text-right text-indigo-900 whitespace-nowrap">
                        {fmtBal(plOpeningBal).text} {fmtBal(plOpeningBal).label}
                      </td>
                      <td className="py-2.5 px-3 text-center text-gray-400">—</td>
                      <td className="py-2.5 px-3 text-center text-gray-400">—</td>
                    </tr>

                    {/* Data Rows */}
                    {plEntries.map((e, idx) => {
                      const debit = e.debit_amount || 0;
                      const credit = e.credit_amount || 0;
                      const bal = fmtBal(e.running_balance);
                      const cat = getCategoryChip(e);
                      const isCancelled = (e.source_status || "").toUpperCase() === "CANCELLED";
                      const rowNum = (plCurrentPage - 1) * pageSize + idx + 1;

                      return (
                        <tr
                          key={e.id}
                          className={`hover:bg-gray-50/80 transition-colors ${
                            isCancelled ? "opacity-60 line-through bg-red-50/20" : ""
                          }`}
                        >
                          <td className="py-2.5 px-3 text-gray-400">{rowNum}</td>
                          <td className="py-2.5 px-3 whitespace-nowrap font-medium text-gray-800">
                            {fmtDate(e.transaction_date)}
                          </td>
                          <td className="py-2.5 px-3">
                            {e.party_name ? (
                              <button
                                onClick={() => drillDownParty(e.party_name!, e.party_type)}
                                className="text-indigo-600 font-semibold hover:underline text-left"
                              >
                                {e.party_name}
                              </button>
                            ) : (
                              <span className="text-gray-400">—</span>
                            )}
                          </td>
                          <td className="py-2.5 px-3 font-mono text-[11px] text-gray-700">
                            {e.reference_number || "—"}
                          </td>
                          <td className="py-2.5 px-3">
                            {e.voucher_type ? (
                              <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-blue-50 text-blue-700 border border-blue-100">
                                {e.voucher_type}
                              </span>
                            ) : (
                              <span className="text-gray-400">—</span>
                            )}
                          </td>
                          <td className="py-2.5 px-3">
                            <span className={`px-2 py-0.5 rounded text-[10px] font-semibold border ${cat.cls}`}>
                              {cat.label}
                            </span>
                          </td>
                          <td className="py-2.5 px-3 text-gray-600">
                            {e.sub_category_name ? (
                              <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-purple-50 text-purple-700 border border-purple-100">
                                {e.sub_category_name}
                              </span>
                            ) : (
                              <span className="text-gray-400">—</span>
                            )}
                          </td>
                          <td className="py-2.5 px-3 text-gray-700 max-w-[160px] truncate" title={e.particulars || ""}>
                            {e.particulars || "—"}
                          </td>
                          <td className="py-2.5 px-3 text-gray-500 max-w-[180px] truncate" title={e.narration || ""}>
                            {e.narration || "—"}
                          </td>
                          <td className="py-2.5 px-3 text-right font-semibold text-red-600">
                            {debit > 0 ? fmt(debit) : "—"}
                          </td>
                          <td className="py-2.5 px-3 text-right font-semibold text-emerald-600">
                            {credit > 0 ? fmt(credit) : "—"}
                          </td>
                          <td className="py-2.5 px-3 text-right font-bold text-gray-900 whitespace-nowrap">
                            {bal.text} <span className="text-[10px] text-gray-500">{bal.label}</span>
                          </td>
                          <td className="py-2.5 px-3 text-center">{getSourceBadge(e.source_status)}</td>
                          <td className="py-2.5 px-3 text-center whitespace-nowrap">
                            <div className="inline-flex items-center gap-1">
                              {["SALES_INVOICE", "VENDOR_TXN", "INCOME", "EXPENSE"].includes((e.reference_type || "").toUpperCase()) && (
                                <button
                                  onClick={() => handleViewSourceDoc(e)}
                                  className="p-1 text-indigo-600 hover:bg-indigo-50 rounded"
                                  title="View Source Document"
                                >
                                  <Eye className="w-3.5 h-3.5" />
                                </button>
                              )}
                              <button
                                onClick={() => handleOpenEdit(e)}
                                className="p-1 text-gray-600 hover:bg-gray-100 rounded"
                                title="Edit Entry"
                              >
                                <Edit className="w-3.5 h-3.5" />
                              </button>
                              <button
                                onClick={() => handleDeleteEntry(e.id)}
                                className="p-1 text-red-600 hover:bg-red-50 rounded"
                                title="Delete Entry"
                              >
                                <Trash2 className="w-3.5 h-3.5" />
                              </button>
                            </div>
                          </td>
                        </tr>
                      );
                    })}

                    {/* Grand Total Row */}
                    <tr className="bg-indigo-50/60 font-bold text-gray-900 border-t-2 border-indigo-200">
                      <td className="py-3 px-3 text-gray-400">—</td>
                      <td colSpan={8} className="py-3 px-3 text-indigo-900 font-bold uppercase tracking-wider text-xs">
                        Grand Total
                      </td>
                      <td className="py-3 px-3 text-right text-red-700 font-mono text-sm">{fmt(plTotalDebit)}</td>
                      <td className="py-3 px-3 text-right text-emerald-700 font-mono text-sm">{fmt(plTotalCredit)}</td>
                      <td className="py-3 px-3 text-right text-indigo-900 font-mono text-sm whitespace-nowrap">
                        {fmtBal(plClosingBal).text} <span className="text-[10px]">{fmtBal(plClosingBal).label}</span>
                      </td>
                      <td className="py-3 px-3 text-center text-gray-400">—</td>
                      <td className="py-3 px-3 text-center text-gray-400">—</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            )}

            {/* Pagination */}
            {plTotal > pageSize && (
              <div className="p-4 border-t border-gray-100 flex items-center justify-between bg-gray-50/50">
                <div className="text-xs text-gray-500">
                  Showing {(plCurrentPage - 1) * pageSize + 1} to {Math.min(plCurrentPage * pageSize, plTotal)} of {plTotal} entries
                </div>
                <div className="flex items-center gap-1">
                  <button
                    disabled={plCurrentPage === 1}
                    onClick={() => loadLedger(plCurrentPage - 1)}
                    className="p-1.5 text-xs bg-white border border-gray-200 rounded-lg hover:bg-gray-50 disabled:opacity-40"
                  >
                    <ChevronLeft className="w-4 h-4" />
                  </button>
                  <span className="px-3 text-xs font-semibold text-gray-700">
                    Page {plCurrentPage} of {Math.ceil(plTotal / pageSize)}
                  </span>
                  <button
                    disabled={plCurrentPage >= Math.ceil(plTotal / pageSize)}
                    onClick={() => loadLedger(plCurrentPage + 1)}
                    className="p-1.5 text-xs bg-white border border-gray-200 rounded-lg hover:bg-gray-50 disabled:opacity-40"
                  >
                    <ChevronRight className="w-4 h-4" />
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ─────────────────────────────────────────────────────────── */}
      {/* TAB 2: ACCOUNT LEDGER                                       */}
      {/* ─────────────────────────────────────────────────────────── */}
      {activeTab === "acct" && (
        <div className="space-y-6">
          <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-5 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-gray-100">
              <div className="text-xs font-bold text-gray-700 uppercase tracking-wider flex items-center gap-2">
                <Filter className="w-4 h-4 text-indigo-500" />
                Account Statement Filter
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => resetTabFilters("acct")}
                  className="px-3 py-1.5 text-xs text-gray-600 bg-gray-100 hover:bg-gray-200 rounded-lg"
                >
                  Reset
                </button>
                <button
                  onClick={() => loadAccountLedger(1)}
                  className="px-4 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold rounded-lg shadow-sm"
                >
                  Load Statement
                </button>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
              <div>
                <label className="text-[11px] font-bold text-gray-600 uppercase">Company</label>
                <select
                  value={alFilterCompany}
                  onChange={(e) => {
                    setAlFilterCompany(e.target.value);
                    loadAlAccounts();
                  }}
                  className="w-full h-9 px-3 text-xs bg-white border border-gray-200 rounded-xl"
                >
                  <option value="">All Companies</option>
                  {companies.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.company_name || c.name}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="text-[11px] font-bold text-gray-600 uppercase">Account Type</label>
                <select
                  value={alFilterType}
                  onChange={(e) => {
                    setAlFilterType(e.target.value);
                    loadAlAccounts();
                  }}
                  className="w-full h-9 px-3 text-xs bg-white border border-gray-200 rounded-xl"
                >
                  <option value="">All Types</option>
                  <option value="BANK">Bank</option>
                  <option value="CASH">Cash</option>
                  <option value="UPI">UPI / Digital</option>
                  <option value="INCOME">Income Head</option>
                  <option value="EXPENSE">Expense Head</option>
                  <option value="PARTY">Party Account</option>
                </select>
              </div>

              <div className="lg:col-span-2">
                <label className="text-[11px] font-bold text-gray-600 uppercase">Account Name</label>
                <input
                  type="text"
                  list="alAccountList"
                  value={alFilterAccount}
                  onChange={(e) => setAlFilterAccount(e.target.value)}
                  placeholder="Type or select account..."
                  className="w-full h-9 px-3 text-xs bg-white border border-gray-200 rounded-xl"
                />
                <datalist id="alAccountList">
                  {alHeadsList.map((h, i) => (
                    <option key={i} value={h.account_name} label={`${h.account_name} (${h.account_type}) - ₹${h.balance}`} />
                  ))}
                </datalist>
              </div>

              <div>
                <label className="text-[11px] font-bold text-gray-600 uppercase">From Date</label>
                <input
                  type="date"
                  value={alFromDate}
                  onChange={(e) => setAlFromDate(e.target.value)}
                  className="w-full h-9 px-2.5 text-xs bg-white border border-gray-200 rounded-xl"
                />
              </div>

              <div>
                <label className="text-[11px] font-bold text-gray-600 uppercase">To Date</label>
                <input
                  type="date"
                  value={alToDate}
                  onChange={(e) => setAlToDate(e.target.value)}
                  className="w-full h-9 px-2.5 text-xs bg-white border border-gray-200 rounded-xl"
                />
              </div>
            </div>
          </div>

          {/* Account KPI Summary */}
          {alEntries.length > 0 && (
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="bg-white p-4 rounded-2xl border border-gray-200 text-center">
                <div className="text-[11px] font-bold text-emerald-600 uppercase">Total In (Debit)</div>
                <div className="text-xl font-bold font-mono text-emerald-700">{fmt(alTotalDebit)}</div>
              </div>
              <div className="bg-white p-4 rounded-2xl border border-gray-200 text-center">
                <div className="text-[11px] font-bold text-red-600 uppercase">Total Out (Credit)</div>
                <div className="text-xl font-bold font-mono text-red-700">{fmt(alTotalCredit)}</div>
              </div>
              <div className="bg-white p-4 rounded-2xl border border-gray-200 text-center">
                <div className="text-[11px] font-bold text-blue-600 uppercase">Net Balance</div>
                <div className="text-xl font-bold font-mono text-blue-900">{fmt(alNetBal)}</div>
              </div>
              <div className="bg-white p-4 rounded-2xl border border-gray-200 text-center">
                <div className="text-[11px] font-bold text-purple-600 uppercase">Transactions</div>
                <div className="text-xl font-bold font-mono text-purple-900">{alTotal}</div>
              </div>
            </div>
          )}

          {/* Table */}
          <div className="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden">
            {alLoading ? (
              <div className="p-16 text-center text-gray-500">
                <RefreshCw className="w-8 h-8 animate-spin text-indigo-600 mx-auto mb-2" />
                <p className="text-xs">Loading account statements...</p>
              </div>
            ) : alEntries.length === 0 ? (
              <div className="p-16 text-center text-gray-400">
                <Landmark className="w-12 h-12 text-gray-300 mx-auto mb-2" />
                <p className="text-sm font-semibold text-gray-700">Select an Account to View Statement</p>
                <p className="text-xs text-gray-400">Choose account type/name and click Load Statement.</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse text-xs">
                  <thead>
                    <tr className="bg-gray-50 text-gray-600 font-semibold border-b text-[11px] uppercase">
                      <th className="py-3 px-3">#</th>
                      <th className="py-3 px-3">Date</th>
                      <th className="py-3 px-3">Account</th>
                      <th className="py-3 px-3">Type</th>
                      <th className="py-3 px-3">Vch No.</th>
                      <th className="py-3 px-3">Particulars</th>
                      <th className="py-3 px-3">Narration</th>
                      <th className="py-3 px-3 text-right">Debit (In)</th>
                      <th className="py-3 px-3 text-right">Credit (Out)</th>
                      <th className="py-3 px-3 text-right">Balance</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {alEntries.map((e, idx) => (
                      <tr key={e.id} className="hover:bg-gray-50">
                        <td className="py-2.5 px-3 text-gray-400">{(alCurrentPage - 1) * pageSize + idx + 1}</td>
                        <td className="py-2.5 px-3 whitespace-nowrap">{fmtDate(e.transaction_date || e.date)}</td>
                        <td className="py-2.5 px-3 font-semibold text-gray-900">{e.account_name}</td>
                        <td className="py-2.5 px-3">
                          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-50 text-blue-700">
                            {e.account_type}
                          </span>
                        </td>
                        <td className="py-2.5 px-3 font-mono text-[11px]">{e.reference_number || "—"}</td>
                        <td className="py-2.5 px-3 max-w-[150px] truncate">{e.particulars || "—"}</td>
                        <td className="py-2.5 px-3 text-gray-500 max-w-[160px] truncate">{e.narration || "—"}</td>
                        <td className="py-2.5 px-3 text-right font-semibold text-emerald-600">
                          {e.debit_amount ? fmt(e.debit_amount) : "—"}
                        </td>
                        <td className="py-2.5 px-3 text-right font-semibold text-red-600">
                          {e.credit_amount ? fmt(e.credit_amount) : "—"}
                        </td>
                        <td className="py-2.5 px-3 text-right font-bold text-gray-900">{fmt(e.running_balance || e.balance)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ─────────────────────────────────────────────────────────── */}
      {/* TAB 3: CASH LEDGER                                          */}
      {/* ─────────────────────────────────────────────────────────── */}
      {activeTab === "cash" && (
        <div className="space-y-6">
          <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-5 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-gray-100">
              <div className="text-xs font-bold text-gray-700 uppercase tracking-wider flex items-center gap-2">
                <Wallet className="w-4 h-4 text-emerald-500" />
                Cash Account Filter
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => resetTabFilters("cash")}
                  className="px-3 py-1.5 text-xs text-gray-600 bg-gray-100 hover:bg-gray-200 rounded-lg"
                >
                  Reset
                </button>
                <button
                  onClick={() => loadCashLedger(1)}
                  className="px-4 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold rounded-lg shadow-sm"
                >
                  Load Cash Statement
                </button>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3">
              <div>
                <label className="text-[11px] font-bold text-gray-600 uppercase">Company</label>
                <select
                  value={cashFilterCompany}
                  onChange={(e) => {
                    setCashFilterCompany(e.target.value);
                    loadCashAccounts();
                  }}
                  className="w-full h-9 px-3 text-xs bg-white border border-gray-200 rounded-xl"
                >
                  <option value="">All Companies</option>
                  {companies.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.company_name || c.name}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="text-[11px] font-bold text-gray-600 uppercase">Cash Account</label>
                <input
                  type="text"
                  list="cashAccountList"
                  value={cashFilterAccount}
                  onChange={(e) => setCashFilterAccount(e.target.value)}
                  placeholder="Select cash account..."
                  className="w-full h-9 px-3 text-xs bg-white border border-gray-200 rounded-xl"
                />
                <datalist id="cashAccountList">
                  {cashHeadsList.map((h, i) => (
                    <option key={i} value={h.account_name} label={`${h.account_name} — Bal: ₹${h.balance}`} />
                  ))}
                </datalist>
              </div>

              <div>
                <label className="text-[11px] font-bold text-gray-600 uppercase">From Date</label>
                <input
                  type="date"
                  value={cashFromDate}
                  onChange={(e) => setCashFromDate(e.target.value)}
                  className="w-full h-9 px-2.5 text-xs bg-white border border-gray-200 rounded-xl"
                />
              </div>

              <div>
                <label className="text-[11px] font-bold text-gray-600 uppercase">To Date</label>
                <input
                  type="date"
                  value={cashToDate}
                  onChange={(e) => setCashToDate(e.target.value)}
                  className="w-full h-9 px-2.5 text-xs bg-white border border-gray-200 rounded-xl"
                />
              </div>
            </div>
          </div>

          {/* Cash Summary */}
          {cashEntries.length > 0 && (
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="bg-white p-4 rounded-2xl border border-gray-200 text-center">
                <div className="text-[11px] font-bold text-emerald-600 uppercase">Cash In (Dr)</div>
                <div className="text-xl font-bold font-mono text-emerald-700">{fmt(cashTotalDebit)}</div>
              </div>
              <div className="bg-white p-4 rounded-2xl border border-gray-200 text-center">
                <div className="text-[11px] font-bold text-red-600 uppercase">Cash Out (Cr)</div>
                <div className="text-xl font-bold font-mono text-red-700">{fmt(cashTotalCredit)}</div>
              </div>
              <div className="bg-white p-4 rounded-2xl border border-gray-200 text-center">
                <div className="text-[11px] font-bold text-blue-600 uppercase">Net Balance</div>
                <div className="text-xl font-bold font-mono text-blue-900">{fmt(cashNetBal)}</div>
              </div>
              <div className="bg-white p-4 rounded-2xl border border-gray-200 text-center">
                <div className="text-[11px] font-bold text-purple-600 uppercase">Transactions</div>
                <div className="text-xl font-bold font-mono text-purple-900">{cashTotal}</div>
              </div>
            </div>
          )}

          {/* Cash Table */}
          <div className="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden">
            {cashLoading ? (
              <div className="p-16 text-center text-gray-500">
                <RefreshCw className="w-8 h-8 animate-spin text-emerald-600 mx-auto mb-2" />
                <p className="text-xs">Loading cash ledger...</p>
              </div>
            ) : cashEntries.length === 0 ? (
              <div className="p-16 text-center text-gray-400">
                <Wallet className="w-12 h-12 text-gray-300 mx-auto mb-2" />
                <p className="text-sm font-semibold text-gray-700">No Cash Entries Found</p>
                <p className="text-xs text-gray-400">Select a cash account and click Load Cash Statement.</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse text-xs">
                  <thead>
                    <tr className="bg-gray-50 text-gray-600 font-semibold border-b text-[11px] uppercase">
                      <th className="py-3 px-3">#</th>
                      <th className="py-3 px-3">Date</th>
                      <th className="py-3 px-3">Account</th>
                      <th className="py-3 px-3">Vch No.</th>
                      <th className="py-3 px-3">Particulars</th>
                      <th className="py-3 px-3">Narration</th>
                      <th className="py-3 px-3 text-right">Cash In (Dr)</th>
                      <th className="py-3 px-3 text-right">Cash Out (Cr)</th>
                      <th className="py-3 px-3 text-right">Balance</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {cashEntries.map((e, idx) => (
                      <tr key={e.id} className="hover:bg-gray-50">
                        <td className="py-2.5 px-3 text-gray-400">{(cashCurrentPage - 1) * pageSize + idx + 1}</td>
                        <td className="py-2.5 px-3 whitespace-nowrap">{fmtDate(e.transaction_date)}</td>
                        <td className="py-2.5 px-3 font-semibold text-gray-900">{e.account_name}</td>
                        <td className="py-2.5 px-3 font-mono text-[11px]">{e.reference_number || "—"}</td>
                        <td className="py-2.5 px-3 max-w-[150px] truncate">{e.particulars || "—"}</td>
                        <td className="py-2.5 px-3 text-gray-500 max-w-[160px] truncate">{e.narration || "—"}</td>
                        <td className="py-2.5 px-3 text-right font-semibold text-emerald-600">
                          {e.debit_amount ? fmt(e.debit_amount) : "—"}
                        </td>
                        <td className="py-2.5 px-3 text-right font-semibold text-red-600">
                          {e.credit_amount ? fmt(e.credit_amount) : "—"}
                        </td>
                        <td className="py-2.5 px-3 text-right font-bold text-gray-900">{fmt(e.running_balance)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ─────────────────────────────────────────────────────────── */}
      {/* TAB 4: PARTY-WISE CONSOLIDATED                              */}
      {/* ─────────────────────────────────────────────────────────── */}
      {activeTab === "pwise" && (
        <div className="space-y-6">
          <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-5 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-gray-100">
              <div className="text-xs font-bold text-gray-700 uppercase tracking-wider flex items-center gap-2">
                <Users className="w-4 h-4 text-indigo-500" />
                Party-wise Consolidated Filter
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => resetTabFilters("pwise")}
                  className="px-3 py-1.5 text-xs text-gray-600 bg-gray-100 hover:bg-gray-200 rounded-lg"
                >
                  Reset
                </button>
                <button
                  onClick={loadPartyWise}
                  className="px-4 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold rounded-lg shadow-sm"
                >
                  Load Summary
                </button>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3">
              <div>
                <label className="text-[11px] font-bold text-gray-600 uppercase">Company</label>
                <select
                  value={pwiseCompany}
                  onChange={(e) => setPwiseCompany(e.target.value)}
                  className="w-full h-9 px-3 text-xs bg-white border border-gray-200 rounded-xl"
                >
                  <option value="">All Companies</option>
                  {companies.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.company_name || c.name}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="text-[11px] font-bold text-gray-600 uppercase">Party Type</label>
                <select
                  value={pwisePartyType}
                  onChange={(e) => setPwisePartyType(e.target.value)}
                  className="w-full h-9 px-3 text-xs bg-white border border-gray-200 rounded-xl"
                >
                  <option value="">All Types</option>
                  <option value="VENDOR">Vendor</option>
                  <option value="CUSTOMER">Customer</option>
                  <option value="EMPLOYEE">Staff</option>
                  <option value="EXTERNAL">External</option>
                </select>
              </div>

              <div className="relative">
                <label className="text-[11px] font-bold text-gray-600 uppercase">Live Party Search</label>
                <input
                  type="text"
                  value={pwisePartySearch}
                  onChange={(e) => setPwisePartySearch(e.target.value)}
                  placeholder="Filter table rows..."
                  className="w-full h-9 px-3 text-xs bg-white border border-gray-200 rounded-xl"
                />
              </div>

              <div>
                <label className="text-[11px] font-bold text-gray-600 uppercase">Date Range</label>
                <div className="flex gap-2">
                  <input
                    type="date"
                    value={pwiseFromDate}
                    onChange={(e) => setPwiseFromDate(e.target.value)}
                    className="w-1/2 h-9 px-2 text-xs bg-white border border-gray-200 rounded-xl"
                  />
                  <input
                    type="date"
                    value={pwiseToDate}
                    onChange={(e) => setPwiseToDate(e.target.value)}
                    className="w-1/2 h-9 px-2 text-xs bg-white border border-gray-200 rounded-xl"
                  />
                </div>
              </div>
            </div>
          </div>

          {/* Party Wise Actions Bar */}
          <div className="flex items-center justify-between">
            <span className="text-xs text-gray-500 font-medium">Click any row to drill down into party ledger detail</span>
            <button
              onClick={() => exportConsolidatedCsv("pwise")}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white font-semibold text-xs rounded-xl shadow-sm"
            >
              <FileSpreadsheet className="w-3.5 h-3.5" />
              Export CSV
            </button>
          </div>

          {/* Table */}
          <div className="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden">
            {pwiseLoading ? (
              <div className="p-16 text-center text-gray-500">
                <RefreshCw className="w-8 h-8 animate-spin text-indigo-600 mx-auto mb-2" />
                <p className="text-xs">Loading consolidated party balances...</p>
              </div>
            ) : filteredPwiseRows.length === 0 ? (
              <div className="p-16 text-center text-gray-400">
                <Users className="w-12 h-12 text-gray-300 mx-auto mb-2" />
                <p className="text-sm font-semibold text-gray-700">No Parties Found</p>
                <p className="text-xs text-gray-400">Click Load Summary to fetch consolidated balances.</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse text-xs">
                  <thead>
                    <tr className="bg-gray-50 text-gray-600 font-semibold border-b text-[11px] uppercase">
                      <th className="py-3 px-3">#</th>
                      <th className="py-3 px-3">Party Name</th>
                      <th className="py-3 px-3">Type</th>
                      <th className="py-3 px-3 text-center">Entries</th>
                      <th className="py-3 px-3 text-right">Total Debit</th>
                      <th className="py-3 px-3 text-right">Total Credit</th>
                      <th className="py-3 px-3 text-right">Net Balance</th>
                      <th className="py-3 px-3">Last Transaction</th>
                      <th className="py-3 px-3 text-center">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {filteredPwiseRows.map((r, idx) => {
                      const bal = fmtBal(r.net_balance);
                      return (
                        <tr
                          key={idx}
                          onClick={() => drillDownParty(r.party_name, r.party_type)}
                          className="hover:bg-indigo-50/40 cursor-pointer transition-colors"
                        >
                          <td className="py-2.5 px-3 text-gray-400">{idx + 1}</td>
                          <td className="py-2.5 px-3 font-semibold text-indigo-900">{r.party_name}</td>
                          <td className="py-2.5 px-3">
                            <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-gray-100 text-gray-700">
                              {r.party_type}
                            </span>
                          </td>
                          <td className="py-2.5 px-3 text-center font-mono font-semibold">{r.entry_count}</td>
                          <td className="py-2.5 px-3 text-right font-semibold text-red-600">{fmt(r.total_debit)}</td>
                          <td className="py-2.5 px-3 text-right font-semibold text-emerald-600">{fmt(r.total_credit)}</td>
                          <td className="py-2.5 px-3 text-right font-bold text-gray-900">
                            {bal.text} <span className="text-[10px] text-gray-500">{bal.label}</span>
                          </td>
                          <td className="py-2.5 px-3 text-gray-500">{fmtDate(r.last_date)}</td>
                          <td className="py-2.5 px-3 text-center" onClick={(e) => e.stopPropagation()}>
                            <div className="inline-flex items-center gap-1.5">
                              <button
                                onClick={() => drillDownParty(r.party_name, r.party_type)}
                                className="px-2 py-1 bg-indigo-50 hover:bg-indigo-100 text-indigo-700 rounded text-[11px] font-semibold"
                              >
                                View
                              </button>
                              <button
                                onClick={() => handleOpenFixParty(r)}
                                className="p-1 text-amber-600 hover:bg-amber-50 rounded"
                                title="Fix / Rename Party"
                              >
                                <Edit className="w-3.5 h-3.5" />
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
          </div>
        </div>
      )}

      {/* ─────────────────────────────────────────────────────────── */}
      {/* TAB 5: BANK ACCOUNT-WISE CONSOLIDATED                       */}
      {/* ─────────────────────────────────────────────────────────── */}
      {activeTab === "awise" && (
        <div className="space-y-6">
          <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-5 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-gray-100">
              <div className="text-xs font-bold text-gray-700 uppercase tracking-wider flex items-center gap-2">
                <Landmark className="w-4 h-4 text-indigo-500" />
                Bank Account-wise Summary
              </div>
              <button
                onClick={loadAccountWise}
                className="px-4 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold rounded-lg shadow-sm"
              >
                Load Summary
              </button>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div>
                <label className="text-[11px] font-bold text-gray-600 uppercase">Company</label>
                <select
                  value={awiseCompany}
                  onChange={(e) => setAwiseCompany(e.target.value)}
                  className="w-full h-9 px-3 text-xs bg-white border border-gray-200 rounded-xl"
                >
                  <option value="">All Companies</option>
                  {companies.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.company_name || c.name}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          </div>

          <div className="flex items-center justify-between">
            <span className="text-xs text-gray-500 font-medium">Click any row to drill down into account statement</span>
            <button
              onClick={() => exportConsolidatedCsv("awise")}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white font-semibold text-xs rounded-xl shadow-sm"
            >
              <FileSpreadsheet className="w-3.5 h-3.5" />
              Export CSV
            </button>
          </div>

          <div className="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden">
            {awiseLoading ? (
              <div className="p-16 text-center text-gray-500">
                <RefreshCw className="w-8 h-8 animate-spin text-indigo-600 mx-auto mb-2" />
                <p className="text-xs">Loading bank accounts...</p>
              </div>
            ) : awiseData.length === 0 ? (
              <div className="p-16 text-center text-gray-400">
                <Landmark className="w-12 h-12 text-gray-300 mx-auto mb-2" />
                <p className="text-sm font-semibold text-gray-700">No Bank Accounts Found</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse text-xs">
                  <thead>
                    <tr className="bg-gray-50 text-gray-600 font-semibold border-b text-[11px] uppercase">
                      <th className="py-3 px-3">#</th>
                      <th className="py-3 px-3">Bank Account Name</th>
                      <th className="py-3 px-3">Type</th>
                      <th className="py-3 px-3 text-right">Total Debit (In)</th>
                      <th className="py-3 px-3 text-right">Total Credit (Out)</th>
                      <th className="py-3 px-3 text-right">Balance</th>
                      <th className="py-3 px-3">Last Transaction</th>
                      <th className="py-3 px-3 text-center">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {awiseData.map((r, idx) => (
                      <tr
                        key={idx}
                        onClick={() => drillDownAccount(r.account_name, r.account_type)}
                        className="hover:bg-indigo-50/40 cursor-pointer transition-colors"
                      >
                        <td className="py-2.5 px-3 text-gray-400">{idx + 1}</td>
                        <td className="py-2.5 px-3 font-semibold text-indigo-900">{r.account_name}</td>
                        <td className="py-2.5 px-3">
                          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-50 text-blue-700">
                            {r.account_type}
                          </span>
                        </td>
                        <td className="py-2.5 px-3 text-right font-semibold text-emerald-600">{fmt(r.total_debit)}</td>
                        <td className="py-2.5 px-3 text-right font-semibold text-red-600">{fmt(r.total_credit)}</td>
                        <td className="py-2.5 px-3 text-right font-bold text-gray-900">{fmt(r.balance)}</td>
                        <td className="py-2.5 px-3 text-gray-500">{fmtDate(r.last_date)}</td>
                        <td className="py-2.5 px-3 text-center">
                          <button className="px-2.5 py-1 bg-indigo-50 hover:bg-indigo-100 text-indigo-700 font-semibold rounded text-[11px]">
                            View
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ─────────────────────────────────────────────────────────── */}
      {/* TAB 6: CASH-WISE CONSOLIDATED                               */}
      {/* ─────────────────────────────────────────────────────────── */}
      {activeTab === "cwise" && (
        <div className="space-y-6">
          <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-5 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-gray-100">
              <div className="text-xs font-bold text-gray-700 uppercase tracking-wider flex items-center gap-2">
                <Coins className="w-4 h-4 text-emerald-500" />
                Cash-wise Summary
              </div>
              <button
                onClick={loadCashWise}
                className="px-4 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold rounded-lg shadow-sm"
              >
                Load Summary
              </button>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div>
                <label className="text-[11px] font-bold text-gray-600 uppercase">Company</label>
                <select
                  value={cwiseCompany}
                  onChange={(e) => setCwiseCompany(e.target.value)}
                  className="w-full h-9 px-3 text-xs bg-white border border-gray-200 rounded-xl"
                >
                  <option value="">All Companies</option>
                  {companies.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.company_name || c.name}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          </div>

          <div className="flex items-center justify-between">
            <span className="text-xs text-gray-500 font-medium">Click any row to drill down into cash statement</span>
            <button
              onClick={() => exportConsolidatedCsv("cwise")}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white font-semibold text-xs rounded-xl shadow-sm"
            >
              <FileSpreadsheet className="w-3.5 h-3.5" />
              Export CSV
            </button>
          </div>

          <div className="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden">
            {cwiseLoading ? (
              <div className="p-16 text-center text-gray-500">
                <RefreshCw className="w-8 h-8 animate-spin text-emerald-600 mx-auto mb-2" />
                <p className="text-xs">Loading cash accounts...</p>
              </div>
            ) : cwiseData.length === 0 ? (
              <div className="p-16 text-center text-gray-400">
                <Coins className="w-12 h-12 text-gray-300 mx-auto mb-2" />
                <p className="text-sm font-semibold text-gray-700">No Cash Accounts Found</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse text-xs">
                  <thead>
                    <tr className="bg-gray-50 text-gray-600 font-semibold border-b text-[11px] uppercase">
                      <th className="py-3 px-3">#</th>
                      <th className="py-3 px-3">Cash Account Name</th>
                      <th className="py-3 px-3">Type</th>
                      <th className="py-3 px-3 text-right">Total In (Dr)</th>
                      <th className="py-3 px-3 text-right">Total Out (Cr)</th>
                      <th className="py-3 px-3 text-right">Balance</th>
                      <th className="py-3 px-3">Last Transaction</th>
                      <th className="py-3 px-3 text-center">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {cwiseData.map((r, idx) => (
                      <tr
                        key={idx}
                        onClick={() => drillDownAccount(r.account_name, "CASH")}
                        className="hover:bg-emerald-50/40 cursor-pointer transition-colors"
                      >
                        <td className="py-2.5 px-3 text-gray-400">{idx + 1}</td>
                        <td className="py-2.5 px-3 font-semibold text-emerald-950">{r.account_name}</td>
                        <td className="py-2.5 px-3">
                          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-50 text-emerald-700">
                            CASH
                          </span>
                        </td>
                        <td className="py-2.5 px-3 text-right font-semibold text-emerald-600">{fmt(r.total_debit)}</td>
                        <td className="py-2.5 px-3 text-right font-semibold text-red-600">{fmt(r.total_credit)}</td>
                        <td className="py-2.5 px-3 text-right font-bold text-gray-900">{fmt(r.balance)}</td>
                        <td className="py-2.5 px-3 text-gray-500">{fmtDate(r.last_date)}</td>
                        <td className="py-2.5 px-3 text-center">
                          <button className="px-2.5 py-1 bg-emerald-50 hover:bg-emerald-100 text-emerald-700 font-semibold rounded text-[11px]">
                            View
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ─────────────────────────────────────────────────────────── */}
      {/* TAB 7: DELETED ENTRIES                                      */}
      {/* ─────────────────────────────────────────────────────────── */}
      {activeTab === "deleted" && (
        <div className="space-y-6">
          <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-5 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-gray-100">
              <div className="text-xs font-bold text-red-700 uppercase tracking-wider flex items-center gap-2">
                <Trash2 className="w-4 h-4 text-red-500" />
                Deleted & Cancelled Entries Filter
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => resetTabFilters("deleted")}
                  className="px-3 py-1.5 text-xs text-gray-600 bg-gray-100 hover:bg-gray-200 rounded-lg"
                >
                  Reset
                </button>
                <button
                  onClick={() => loadDeletedLedger(1)}
                  className="px-4 py-1.5 bg-red-600 hover:bg-red-700 text-white text-xs font-semibold rounded-lg shadow-sm"
                >
                  Search Deleted
                </button>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3">
              <div>
                <label className="text-[11px] font-bold text-gray-600 uppercase">Company</label>
                <select
                  value={delCompany}
                  onChange={(e) => setDelCompany(e.target.value)}
                  className="w-full h-9 px-3 text-xs bg-white border border-gray-200 rounded-xl"
                >
                  <option value="">All Companies</option>
                  {companies.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.company_name || c.name}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="text-[11px] font-bold text-gray-600 uppercase">Search Particulars</label>
                <input
                  type="text"
                  value={delParticulars}
                  onChange={(e) => setDelParticulars(e.target.value)}
                  placeholder="Search..."
                  className="w-full h-9 px-3 text-xs bg-white border border-gray-200 rounded-xl"
                />
              </div>

              <div>
                <label className="text-[11px] font-bold text-gray-600 uppercase">From Date</label>
                <input
                  type="date"
                  value={delFromDate}
                  onChange={(e) => setDelFromDate(e.target.value)}
                  className="w-full h-9 px-2.5 text-xs bg-white border border-gray-200 rounded-xl"
                />
              </div>

              <div>
                <label className="text-[11px] font-bold text-gray-600 uppercase">To Date</label>
                <input
                  type="date"
                  value={delToDate}
                  onChange={(e) => setDelToDate(e.target.value)}
                  className="w-full h-9 px-2.5 text-xs bg-white border border-gray-200 rounded-xl"
                />
              </div>
            </div>
          </div>

          <div className="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden">
            {delLoading ? (
              <div className="p-16 text-center text-gray-500">
                <RefreshCw className="w-8 h-8 animate-spin text-red-600 mx-auto mb-2" />
                <p className="text-xs">Loading deleted ledger entries...</p>
              </div>
            ) : delEntries.length === 0 ? (
              <div className="p-16 text-center text-gray-400">
                <Trash2 className="w-12 h-12 text-gray-300 mx-auto mb-2" />
                <p className="text-sm font-semibold text-gray-700">No Deleted Entries Found</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse text-xs">
                  <thead>
                    <tr className="bg-red-50/50 text-red-900 font-semibold border-b text-[11px] uppercase">
                      <th className="py-3 px-3">Date</th>
                      <th className="py-3 px-3">Party</th>
                      <th className="py-3 px-3">Ref Type</th>
                      <th className="py-3 px-3">Ref / Voucher #</th>
                      <th className="py-3 px-3">Particulars</th>
                      <th className="py-3 px-3 text-right">Debit (₹)</th>
                      <th className="py-3 px-3 text-right">Credit (₹)</th>
                      <th className="py-3 px-3 text-center">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100 opacity-75">
                    {delEntries.map((e) => (
                      <tr key={e.id} className="hover:bg-red-50/30 line-through">
                        <td className="py-2.5 px-3 whitespace-nowrap">{fmtDate(e.transaction_date)}</td>
                        <td className="py-2.5 px-3 font-semibold">{e.party_name || "—"}</td>
                        <td className="py-2.5 px-3">
                          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-red-100 text-red-800">
                            {e.reference_type}
                          </span>
                        </td>
                        <td className="py-2.5 px-3 font-mono text-[11px] text-indigo-600">{e.reference_number || "—"}</td>
                        <td className="py-2.5 px-3 max-w-[200px] truncate">{e.particulars || "—"}</td>
                        <td className="py-2.5 px-3 text-right text-red-600 font-semibold">{fmt(e.debit_amount)}</td>
                        <td className="py-2.5 px-3 text-right text-emerald-600 font-semibold">{fmt(e.credit_amount)}</td>
                        <td className="py-2.5 px-3 text-center">
                          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-red-100 text-red-800">
                            CANCELLED
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ─────────────────────────────────────────────────────────── */}
      {/* MODAL 1: NEW MANUAL ENTRY                                   */}
      {/* ─────────────────────────────────────────────────────────── */}
      {newEntryModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full shadow-2xl border border-gray-100 overflow-hidden animate-in zoom-in-95 duration-200">
            <div className="p-4 sm:p-5 border-b border-gray-100 flex items-center justify-between bg-gray-50/50">
              <h3 className="font-bold text-gray-900 text-sm flex items-center gap-2">
                <PlusCircle className="w-4 h-4 text-emerald-600" />
                New Ledger Entry
              </h3>
              <button onClick={() => setNewEntryModalOpen(false)} className="text-gray-400 hover:text-gray-600">
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="p-5 space-y-4 text-xs">
              <div className="p-3 bg-indigo-50/70 border border-indigo-100 rounded-xl text-indigo-900 flex items-start gap-2">
                <Tag className="w-4 h-4 text-indigo-600 mt-0.5 shrink-0" />
                <div>Creating manual ledger entry for company: <strong>{companies.find((c) => String(c.id) === String(filterCompany))?.company_name}</strong></div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="font-semibold text-gray-700 block mb-1">Transaction Date *</label>
                  <input
                    type="date"
                    value={entryDate}
                    onChange={(e) => setEntryDate(e.target.value)}
                    className="w-full h-9 px-3 border border-gray-200 rounded-xl"
                  />
                </div>
                <div>
                  <label className="font-semibold text-gray-700 block mb-1">Reference No.</label>
                  <input
                    type="text"
                    value={entryRef}
                    onChange={(e) => setEntryRef(e.target.value)}
                    placeholder="Invoice / Receipt #"
                    className="w-full h-9 px-3 border border-gray-200 rounded-xl"
                  />
                </div>
              </div>

              <div>
                <label className="font-semibold text-gray-700 block mb-1">Party *</label>
                <select
                  value={entryPartyVal}
                  onChange={(e) => setEntryPartyVal(e.target.value)}
                  className="w-full h-9 px-3 border border-gray-200 rounded-xl"
                >
                  <option value="">-- Choose Party --</option>
                  {allParties.map((p, i) => (
                    <option key={i} value={`${p.type}:${p.id}:${p.name}`}>
                      [{p.badge || p.type}] {p.name}
                    </option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="font-semibold text-gray-700 block mb-1">Voucher Type</label>
                  <select
                    value={entryVoucherType}
                    onChange={(e) => setEntryVoucherType(e.target.value)}
                    className="w-full h-9 px-3 border border-gray-200 rounded-xl"
                  >
                    <option value="">— Select Type —</option>
                    <option value="Receipt">Receipt</option>
                    <option value="Sales">Sales</option>
                    <option value="Purchase">Purchase</option>
                    <option value="Payment">Payment</option>
                    <option value="Journal">Journal</option>
                    <option value="Credit Note">Credit Note</option>
                    <option value="Debit Note">Debit Note</option>
                    <option value="Contra">Contra</option>
                  </select>
                </div>
                <div>
                  <label className="font-semibold text-gray-700 block mb-1">Category</label>
                  <input
                    type="text"
                    list="entryCategorySuggestions"
                    value={entryCategory}
                    onChange={(e) => setEntryCategory(e.target.value)}
                    placeholder="e.g. Salary, Rent, Travel..."
                    className="w-full h-9 px-3 border border-gray-200 rounded-xl"
                  />
                  <datalist id="entryCategorySuggestions">
                    <option value="Salary" />
                    <option value="Rent" />
                    <option value="Travel" />
                    <option value="Office Expense" />
                    <option value="Utilities" />
                    <option value="Professional Fee" />
                    <option value="Marketing" />
                    <option value="Advance" />
                    <option value="Loan" />
                    <option value="Purchase" />
                    <option value="Sales" />
                  </datalist>
                </div>
              </div>

              <div>
                <label className="font-semibold text-gray-700 block mb-1">Particulars (Account)</label>
                <input
                  type="text"
                  value={entryParticulars}
                  onChange={(e) => setEntryParticulars(e.target.value)}
                  placeholder="e.g. Union Bank 0001"
                  className="w-full h-9 px-3 border border-gray-200 rounded-xl"
                />
              </div>

              <div>
                <label className="font-semibold text-gray-700 block mb-1">Entry Type *</label>
                <div className="grid grid-cols-2 gap-2">
                  <button
                    type="button"
                    onClick={() => setEntryType("DEBIT")}
                    className={`py-2 px-3 rounded-xl font-bold transition-all ${
                      entryType === "DEBIT"
                        ? "bg-red-600 text-white shadow-sm"
                        : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                    }`}
                  >
                    Dr DEBIT (Payable / Owed)
                  </button>
                  <button
                    type="button"
                    onClick={() => setEntryType("CREDIT")}
                    className={`py-2 px-3 rounded-xl font-bold transition-all ${
                      entryType === "CREDIT"
                        ? "bg-emerald-600 text-white shadow-sm"
                        : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                    }`}
                  >
                    Cr CREDIT (Paid / Received)
                  </button>
                </div>
              </div>

              <div>
                <label className="font-semibold text-gray-700 block mb-1">Amount (₹) *</label>
                <input
                  type="number"
                  min="0.01"
                  step="0.01"
                  value={entryAmount}
                  onChange={(e) => setEntryAmount(e.target.value)}
                  placeholder="0.00"
                  className="w-full h-9 px-3 border border-gray-200 rounded-xl font-mono text-sm"
                />
              </div>

              <div>
                <label className="font-semibold text-gray-700 block mb-1">Narration / Description</label>
                <textarea
                  rows={2}
                  value={entryNarration}
                  onChange={(e) => setEntryNarration(e.target.value)}
                  placeholder="Note / transaction description..."
                  className="w-full p-2.5 border border-gray-200 rounded-xl resize-none"
                />
              </div>
            </div>

            <div className="p-4 bg-gray-50 border-t border-gray-100 flex items-center justify-end gap-2">
              <button
                onClick={() => setNewEntryModalOpen(false)}
                className="px-4 py-2 text-xs font-semibold text-gray-600 hover:bg-gray-200 rounded-xl"
              >
                Cancel
              </button>
              <button
                disabled={savingEntry}
                onClick={handleSaveManualEntry}
                className="px-5 py-2 bg-emerald-600 hover:bg-emerald-700 text-white font-semibold text-xs rounded-xl shadow-sm disabled:opacity-50 inline-flex items-center gap-1.5"
              >
                {savingEntry ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <CheckCircle2 className="w-3.5 h-3.5" />}
                Save Entry
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ─────────────────────────────────────────────────────────── */}
      {/* MODAL 2: TALLY LEDGER IMPORT (2 STEPS)                      */}
      {/* ─────────────────────────────────────────────────────────── */}
      {tallyModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-2xl w-full shadow-2xl border border-gray-100 overflow-hidden animate-in zoom-in-95 duration-200">
            <div className="p-4 sm:p-5 border-b border-gray-100 flex items-center justify-between bg-amber-50/50">
              <h3 className="font-bold text-gray-900 text-sm flex items-center gap-2">
                <Upload className="w-4 h-4 text-amber-600" />
                Upload Tally Ledger Statement
              </h3>
              <button onClick={() => setTallyModalOpen(false)} className="text-gray-400 hover:text-gray-600">
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="p-6 space-y-4 text-xs max-h-[80vh] overflow-y-auto">
              {tallyStep === 1 ? (
                <>
                  <div className="p-3 bg-blue-50 border border-blue-100 rounded-xl text-blue-900 flex items-start gap-2">
                    <Receipt className="w-4 h-4 text-blue-600 mt-0.5 shrink-0" />
                    <div>
                      <strong>Supported formats:</strong> Tally PDF (.pdf), Tally XML (.xml), CSV, or plain text export (.txt). Duplicate entries are automatically skipped.
                    </div>
                  </div>

                  <div className="grid grid-cols-3 gap-3">
                    <div>
                      <label className="font-semibold text-gray-700 block mb-1">Party Type *</label>
                      <select
                        value={tallyPartyType}
                        onChange={(e) => setTallyPartyType(e.target.value)}
                        className="w-full h-9 px-3 border border-gray-200 rounded-xl"
                      >
                        <option value="VENDOR">Vendor / Supplier</option>
                        <option value="CUSTOMER">Customer / Partner</option>
                        <option value="EMPLOYEE">Staff / Employee</option>
                        <option value="EXTERNAL">External Party</option>
                      </select>
                    </div>

                    <div className="col-span-2 relative">
                      <label className="font-semibold text-gray-700 block mb-1">Party Name *</label>
                      <input
                        type="text"
                        value={tallyPartyInput}
                        onChange={(e) => {
                          setTallyPartyInput(e.target.value);
                          setTallyComboOpen(true);
                        }}
                        onFocus={() => setTallyComboOpen(true)}
                        placeholder="Search existing or type new party..."
                        className="w-full h-9 px-3 border border-gray-200 rounded-xl"
                      />
                      {tallyComboOpen && (
                        <div className="absolute top-full left-0 right-0 z-50 mt-1 bg-white border border-gray-200 rounded-xl shadow-xl max-h-48 overflow-y-auto divide-y divide-gray-50">
                          {allParties
                            .filter((p) => !tallyPartyInput || p.name.toLowerCase().includes(tallyPartyInput.toLowerCase()))
                            .slice(0, 15)
                            .map((p, idx) => (
                              <div
                                key={idx}
                                onMouseDown={(e) => {
                                  e.preventDefault();
                                  setTallyPartyInput(p.name);
                                  setTallySelectedParty(p);
                                  setTallyComboOpen(false);
                                }}
                                className="p-2 hover:bg-amber-50 cursor-pointer flex items-center justify-between text-xs"
                              >
                                <span className="font-medium text-gray-800">{p.name}</span>
                                <span className="text-[10px] text-gray-500 font-semibold">{p.type}</span>
                              </div>
                            ))}
                        </div>
                      )}
                    </div>
                  </div>

                  {tallyPdfDetectedParty && (
                    <div className="p-2.5 bg-amber-50 border border-amber-200 rounded-xl flex items-center justify-between">
                      <div className="text-xs text-amber-900">
                        Party name detected in file: <strong>{tallyPdfDetectedParty}</strong>
                      </div>
                      <button
                        type="button"
                        onClick={() => setTallyPartyInput(tallyPdfDetectedParty)}
                        className="px-2.5 py-1 bg-amber-500 text-white rounded-lg text-xs font-semibold hover:bg-amber-600"
                      >
                        Use This Name
                      </button>
                    </div>
                  )}

                  {/* Drag & drop upload area */}
                  <div
                    onClick={() => document.getElementById("tallyFileInput")?.click()}
                    onDragOver={(e) => e.preventDefault()}
                    onDrop={(e) => {
                      e.preventDefault();
                      if (e.dataTransfer.files?.[0]) handleProcessTallyFile(e.dataTransfer.files[0]);
                    }}
                    className={`border-2 border-dashed rounded-2xl p-8 text-center cursor-pointer transition-all ${
                      tallyFile ? "bg-emerald-50 border-emerald-300" : "hover:bg-gray-50 border-gray-300"
                    }`}
                  >
                    <input
                      id="tallyFileInput"
                      type="file"
                      accept=".xml,.csv,.txt,.pdf"
                      className="hidden"
                      onChange={(e) => {
                        if (e.target.files?.[0]) handleProcessTallyFile(e.target.files[0]);
                      }}
                    />
                    {tallyFile ? (
                      <div className="space-y-1 text-emerald-800">
                        <CheckCircle2 className="w-10 h-10 text-emerald-600 mx-auto" />
                        <h4 className="font-bold text-sm">{tallyFile.name}</h4>
                        <p className="text-xs text-emerald-600">{(tallyFile.size / 1024).toFixed(1)} KB — Ready to import</p>
                      </div>
                    ) : (
                      <div className="space-y-1 text-gray-500">
                        <Upload className="w-10 h-10 text-gray-400 mx-auto" />
                        <h4 className="font-bold text-sm text-gray-800">Drag & Drop or Click to Select File</h4>
                        <p className="text-xs text-gray-400">Supports PDF, XML, CSV, TXT (up to 10MB)</p>
                      </div>
                    )}
                  </div>

                  {/* Preview Table */}
                  {tallyPreview.length > 0 && (
                    <div className="space-y-2">
                      <div className="text-xs font-bold text-gray-700">Preview (First 5 Rows)</div>
                      <div className="border border-gray-200 rounded-xl overflow-x-auto max-h-36">
                        <table className="w-full text-left text-[11px]">
                          <thead className="bg-gray-50 text-gray-600 font-semibold border-b">
                            <tr>
                              <th className="p-2">Date</th>
                              <th className="p-2">Vch No.</th>
                              <th className="p-2">Type</th>
                              <th className="p-2">Particulars</th>
                              <th className="p-2 text-right">Debit</th>
                              <th className="p-2 text-right">Credit</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-gray-100">
                            {tallyPreview.map((r, i) => (
                              <tr key={i}>
                                <td className="p-2 whitespace-nowrap">{r.date}</td>
                                <td className="p-2 font-mono">{r.ref || "—"}</td>
                                <td className="p-2">{r.vtype || "—"}</td>
                                <td className="p-2 max-w-[120px] truncate">{r.part || "—"}</td>
                                <td className="p-2 text-right text-red-600">{r.debit ? fmt(r.debit) : "—"}</td>
                                <td className="p-2 text-right text-emerald-600">{r.credit ? fmt(r.credit) : "—"}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}
                </>
              ) : (
                /* Step 2: Results & Verification */
                <div className="space-y-4">
                  <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-xl text-emerald-950 space-y-1">
                    <h4 className="font-bold text-sm flex items-center gap-2">
                      <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                      {tallyImportResult?.message}
                    </h4>
                    {tallyImportResult?.date_range_in_file && (
                      <p className="text-xs text-emerald-700">Period: {tallyImportResult.date_range_in_file}</p>
                    )}
                  </div>

                  <div className="grid grid-cols-3 gap-3">
                    <div className="p-3 bg-gray-50 border border-gray-200 rounded-xl text-center">
                      <div className="text-lg font-bold font-mono text-emerald-600">{tallyImportResult?.imported || 0}</div>
                      <div className="text-[10px] text-gray-500 uppercase font-semibold">Entries Imported</div>
                    </div>
                    <div className="p-3 bg-gray-50 border border-gray-200 rounded-xl text-center">
                      <div className="text-lg font-bold font-mono text-amber-600">{tallyImportResult?.skipped_duplicates || 0}</div>
                      <div className="text-[10px] text-gray-500 uppercase font-semibold">Duplicates Skipped</div>
                    </div>
                    <div className="p-3 bg-gray-50 border border-gray-200 rounded-xl text-center">
                      <div className="text-lg font-bold font-mono text-blue-600">{fmt(tallyImportResult?.closing_balance)}</div>
                      <div className="text-[10px] text-gray-500 uppercase font-semibold">Closing Balance</div>
                    </div>
                  </div>

                  {/* Party name deviation */}
                  {tallyImportResult?.name_deviation && tallyImportResult?.party_name_in_file && (
                    <div className="p-4 bg-amber-50 border border-amber-200 rounded-xl space-y-3">
                      <div className="font-bold text-amber-900 flex items-center gap-2 text-xs">
                        <AlertTriangle className="w-4 h-4 text-amber-600" />
                        Party Name Deviation Found in File
                      </div>
                      <div className="flex items-center gap-3 text-xs">
                        <div className="flex-1 p-2 bg-amber-100/70 rounded-lg">
                          <span className="text-[10px] font-bold text-amber-800 block">Name in File</span>
                          <strong>{tallyImportResult.party_name_in_file}</strong>
                        </div>
                        <div className="text-gray-400 font-bold">≠</div>
                        <div className="flex-1 p-2 bg-emerald-100/70 rounded-lg">
                          <span className="text-[10px] font-bold text-emerald-800 block">Selected in System</span>
                          <strong>{tallyPartyInput}</strong>
                        </div>
                      </div>

                      <div className="flex items-center gap-2 pt-2">
                        <button
                          disabled={renamingParty}
                          onClick={() =>
                            handleRenameImportedParty(
                              tallyImportResult.party_name_in_file!,
                              tallyPartyInput,
                              tallyPartyType
                            )
                          }
                          className="px-3 py-1.5 bg-amber-600 hover:bg-amber-700 text-white font-semibold rounded-lg text-xs"
                        >
                          {renamingParty ? "Renaming..." : `Rename to "${tallyImportResult.party_name_in_file}"`}
                        </button>
                      </div>

                      {renameResultMsg && (
                        <div
                          className={`p-2.5 rounded-lg text-xs font-medium ${
                            renameResultMsg.isError ? "bg-red-100 text-red-800" : "bg-emerald-100 text-emerald-800"
                          }`}
                        >
                          {renameResultMsg.text}
                        </div>
                      )}
                    </div>
                  )}

                  {/* Balance Verification */}
                  {tallyImportResult?.file_closing_balance !== null && tallyImportResult?.file_closing_balance !== undefined && (
                    <div className="p-3 bg-gray-50 border border-gray-200 rounded-xl space-y-1">
                      <div className="font-bold text-gray-700 text-xs">Balance Verification</div>
                      <div className="flex items-center gap-3 text-xs">
                        <div>File Balance: <strong>{fmt(tallyImportResult.file_closing_balance)}</strong></div>
                        <div>→</div>
                        <div>System Balance: <strong>{fmt(tallyImportResult.closing_balance)}</strong></div>
                        <div>
                          {tallyImportResult.balance_verified ? (
                            <span className="text-emerald-600 font-bold">✓ Match</span>
                          ) : (
                            <span className="text-amber-600 font-bold">⚠ Diff: {fmt(tallyImportResult.balance_diff)}</span>
                          )}
                        </div>
                      </div>
                    </div>
                  )}

                  {/* New Particulars Found */}
                  {tallyImportResult?.new_particulars && tallyImportResult.new_particulars.length > 0 && (
                    <div className="space-y-1.5">
                      <div className="font-bold text-gray-700 text-xs">New Particulars / Accounts Found in File:</div>
                      <div className="flex flex-wrap gap-1.5">
                        {tallyImportResult.new_particulars.map((p, i) => (
                          <span key={i} className="px-2 py-0.5 bg-indigo-50 border border-indigo-200 text-indigo-800 rounded-full text-[11px]">
                            {p}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>

            <div className="p-4 bg-gray-50 border-t border-gray-100 flex items-center justify-end gap-2">
              <button
                onClick={() => setTallyModalOpen(false)}
                className="px-4 py-2 text-xs font-semibold text-gray-600 hover:bg-gray-200 rounded-xl"
              >
                Close
              </button>
              {tallyStep === 1 ? (
                <button
                  disabled={!tallyFile || !tallyPartyInput.trim() || importingTally}
                  onClick={handleImportTally}
                  className="px-5 py-2 bg-amber-500 hover:bg-amber-600 text-white font-semibold text-xs rounded-xl shadow-sm disabled:opacity-50 inline-flex items-center gap-1.5"
                >
                  {importingTally ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Upload className="w-3.5 h-3.5" />}
                  Import Entries
                </button>
              ) : (
                <button
                  onClick={() => {
                    setTallyModalOpen(false);
                    loadLedger(1);
                  }}
                  className="px-5 py-2 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-xs rounded-xl shadow-sm"
                >
                  Reload Ledger
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ─────────────────────────────────────────────────────────── */}
      {/* MODAL 3: EDIT LEDGER ENTRY                                  */}
      {/* ─────────────────────────────────────────────────────────── */}
      {editModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-md w-full shadow-2xl border border-gray-100 overflow-hidden animate-in zoom-in-95 duration-200">
            <div className="p-4 sm:p-5 border-b border-gray-100 flex items-center justify-between bg-gray-50">
              <h3 className="font-bold text-gray-900 text-sm flex items-center gap-2">
                <Edit className="w-4 h-4 text-indigo-600" />
                Edit Ledger Entry #{editEntryId}
              </h3>
              <button onClick={() => setEditModalOpen(false)} className="text-gray-400 hover:text-gray-600">
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="p-5 space-y-3.5 text-xs">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="font-semibold text-gray-700 block mb-1">Date *</label>
                  <input
                    type="date"
                    value={editDate}
                    onChange={(e) => setEditDate(e.target.value)}
                    className="w-full h-9 px-3 border border-gray-200 rounded-xl"
                  />
                </div>
                <div>
                  <label className="font-semibold text-gray-700 block mb-1">Entry Type *</label>
                  <div className="flex gap-1">
                    <button
                      type="button"
                      onClick={() => setEditType("DEBIT")}
                      className={`flex-1 py-2 text-xs font-bold rounded-lg ${
                        editType === "DEBIT" ? "bg-red-600 text-white" : "bg-gray-100 text-gray-600"
                      }`}
                    >
                      Dr Debit
                    </button>
                    <button
                      type="button"
                      onClick={() => setEditType("CREDIT")}
                      className={`flex-1 py-2 text-xs font-bold rounded-lg ${
                        editType === "CREDIT" ? "bg-emerald-600 text-white" : "bg-gray-100 text-gray-600"
                      }`}
                    >
                      Cr Credit
                    </button>
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="font-semibold text-gray-700 block mb-1">Amount (₹) *</label>
                  <input
                    type="number"
                    min="0.01"
                    step="0.01"
                    value={editAmount}
                    onChange={(e) => setEditAmount(e.target.value)}
                    className="w-full h-9 px-3 border border-gray-200 rounded-xl font-mono"
                  />
                </div>
                <div>
                  <label className="font-semibold text-gray-700 block mb-1">Vch No.</label>
                  <input
                    type="text"
                    value={editRef}
                    onChange={(e) => setEditRef(e.target.value)}
                    className="w-full h-9 px-3 border border-gray-200 rounded-xl"
                  />
                </div>
              </div>

              <div>
                <label className="font-semibold text-gray-700 block mb-1">Vch Type</label>
                <input
                  type="text"
                  value={editVchType}
                  onChange={(e) => setEditVchType(e.target.value)}
                  placeholder="Receipt, Payment, Sales..."
                  className="w-full h-9 px-3 border border-gray-200 rounded-xl"
                />
              </div>

              <div>
                <label className="font-semibold text-gray-700 block mb-1">Particulars</label>
                <input
                  type="text"
                  value={editParticulars}
                  onChange={(e) => setEditParticulars(e.target.value)}
                  className="w-full h-9 px-3 border border-gray-200 rounded-xl"
                />
              </div>

              <div>
                <label className="font-semibold text-gray-700 block mb-1">Description / Narration</label>
                <textarea
                  rows={2}
                  value={editNarration}
                  onChange={(e) => setEditNarration(e.target.value)}
                  className="w-full p-2.5 border border-gray-200 rounded-xl resize-none"
                />
              </div>
            </div>

            <div className="p-4 bg-gray-50 border-t border-gray-100 flex items-center justify-end gap-2">
              <button
                onClick={() => setEditModalOpen(false)}
                className="px-4 py-2 text-xs font-semibold text-gray-600 hover:bg-gray-200 rounded-xl"
              >
                Cancel
              </button>
              <button
                disabled={savingEdit}
                onClick={handleSaveEdit}
                className="px-5 py-2 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-xs rounded-xl shadow-sm disabled:opacity-50 inline-flex items-center gap-1.5"
              >
                {savingEdit ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Check className="w-3.5 h-3.5" />}
                Save Changes
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ─────────────────────────────────────────────────────────── */}
      {/* MODAL 4: VIEW SOURCE DOCUMENT                               */}
      {/* ─────────────────────────────────────────────────────────── */}
      {viewDocModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-2xl w-full shadow-2xl border border-gray-100 overflow-hidden animate-in zoom-in-95 duration-200">
            <div className="p-4 sm:p-5 border-b border-gray-100 flex items-center justify-between bg-indigo-50/50">
              <h3 className="font-bold text-gray-900 text-sm flex items-center gap-2">
                <FileText className="w-4 h-4 text-indigo-600" />
                {viewDocTitle}
              </h3>
              <button onClick={() => setViewDocModalOpen(false)} className="text-gray-400 hover:text-gray-600">
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="p-6 space-y-4 text-xs max-h-[75vh] overflow-y-auto">
              {viewDocLoading ? (
                <div className="p-12 text-center text-gray-500">
                  <RefreshCw className="w-8 h-8 animate-spin text-indigo-600 mx-auto mb-2" />
                  <p className="text-xs">Loading document record...</p>
                </div>
              ) : viewDocData ? (
                <div className="space-y-4">
                  {/* Sales Invoice view */}
                  {viewDocRefType === "SALES_INVOICE" && (
                    <div className="space-y-4">
                      <div className="p-4 bg-gradient-to-r from-blue-50 to-indigo-50 rounded-xl flex justify-between items-start border border-blue-100">
                        <div>
                          <div className="text-base font-extrabold text-blue-900">{viewDocData.invoice_number}</div>
                          <div className="text-[11px] text-gray-500 mt-0.5">
                            {viewDocData.document_type?.replace(/_/g, " ").toUpperCase() || "TAX INVOICE"}
                          </div>
                          {viewDocData.so_number && (
                            <div className="text-[11px] text-gray-500">SO: {viewDocData.so_number}</div>
                          )}
                        </div>
                        <div className="text-right">
                          <span className="px-2.5 py-1 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-800">
                            {viewDocData.payment_status || "CONFIRMED"}
                          </span>
                          <div className="text-[11px] text-gray-500 mt-1">Date: {fmtDate(viewDocData.invoice_date)}</div>
                        </div>
                      </div>

                      <div className="p-3 bg-gray-50 rounded-xl space-y-1">
                        <div className="font-bold text-gray-900 text-xs">Customer: {viewDocData.customer_name}</div>
                        {viewDocData.customer_phone && <div>Phone: {viewDocData.customer_phone}</div>}
                        {viewDocData.customer_gstin && <div>GSTIN: {viewDocData.customer_gstin}</div>}
                      </div>

                      {/* Line Items */}
                      {viewDocData.line_items && (
                        <div className="border border-gray-200 rounded-xl overflow-hidden">
                          <table className="w-full text-left text-[11px]">
                            <thead className="bg-gray-50 text-gray-600 font-semibold border-b">
                              <tr>
                                <th className="p-2">Item</th>
                                <th className="p-2 text-right">Qty</th>
                                <th className="p-2 text-right">Rate</th>
                                <th className="p-2 text-right">Total</th>
                              </tr>
                            </thead>
                            <tbody className="divide-y divide-gray-100">
                              {viewDocData.line_items.map((li: any, i: number) => (
                                <tr key={i}>
                                  <td className="p-2">{li.item_description || li.item_code}</td>
                                  <td className="p-2 text-right">{li.quantity}</td>
                                  <td className="p-2 text-right">{fmt(li.unit_rate)}</td>
                                  <td className="p-2 text-right font-semibold">{fmt(li.total_amount || li.line_total)}</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      )}

                      <div className="p-3 bg-gray-50 rounded-xl space-y-1.5 text-right font-mono text-xs">
                        <div className="flex justify-between text-gray-600"><span>Subtotal:</span><span>{fmt(viewDocData.subtotal)}</span></div>
                        {viewDocData.total_discount > 0 && <div className="flex justify-between text-red-600"><span>Discount:</span><span>− {fmt(viewDocData.total_discount)}</span></div>}
                        <div className="flex justify-between text-gray-600"><span>Taxable:</span><span>{fmt(viewDocData.taxable_amount)}</span></div>
                        <div className="flex justify-between text-gray-600"><span>Tax:</span><span>{fmt(viewDocData.total_tax)}</span></div>
                        <div className="flex justify-between text-blue-900 font-extrabold text-sm pt-1 border-t border-gray-200"><span>Grand Total:</span><span>{fmt(viewDocData.grand_total)}</span></div>
                      </div>
                    </div>
                  )}

                  {/* Vendor transaction view */}
                  {viewDocRefType === "VENDOR_TXN" && (
                    <div className="space-y-4">
                      <div className="p-4 bg-gradient-to-r from-amber-50 to-orange-50 rounded-xl flex justify-between items-start border border-amber-100">
                        <div>
                          <div className="text-base font-extrabold text-amber-900">{viewDocData.transaction_number}</div>
                          <div className="text-[11px] text-gray-500 mt-0.5">{viewDocData.transaction_type}</div>
                        </div>
                        <div className="text-right">
                          <span className="px-2.5 py-1 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-800">
                            {viewDocData.payment_status}
                          </span>
                          <div className="text-[11px] text-gray-500 mt-1">Date: {fmtDate(viewDocData.transaction_date)}</div>
                        </div>
                      </div>

                      <div className="p-3 bg-gray-50 rounded-xl space-y-1">
                        <div className="font-bold text-gray-900 text-xs">Vendor: {viewDocData.vendor_name}</div>
                        {viewDocData.vendor_gstin && <div>GSTIN: {viewDocData.vendor_gstin}</div>}
                        {viewDocData.vendor_invoice_no && <div>Invoice #: {viewDocData.vendor_invoice_no}</div>}
                      </div>

                      <div className="p-3 bg-gray-50 rounded-xl space-y-1.5 text-right font-mono text-xs">
                        <div className="flex justify-between text-gray-600"><span>Taxable Amount:</span><span>{fmt(viewDocData.taxable_amount)}</span></div>
                        <div className="flex justify-between text-amber-900 font-extrabold text-sm pt-1 border-t border-gray-200"><span>Grand Total:</span><span>{fmt(viewDocData.grand_total)}</span></div>
                      </div>
                    </div>
                  )}

                  {/* Income/Expense or generic */}
                  {!["SALES_INVOICE", "VENDOR_TXN"].includes(viewDocRefType) && (
                    <div className="p-4 bg-gray-50 rounded-xl space-y-2">
                      <div className="flex justify-between py-1 border-b border-gray-200">
                        <span className="text-gray-500">Reference:</span>
                        <strong>{viewDocData.reference_number || viewDocData.entry_number || "—"}</strong>
                      </div>
                      <div className="flex justify-between py-1 border-b border-gray-200">
                        <span className="text-gray-500">Party / Payee:</span>
                        <strong>{viewDocData.party_name || viewDocData.payer_name || viewDocData.vendor_name || "—"}</strong>
                      </div>
                      <div className="flex justify-between py-1 border-b border-gray-200">
                        <span className="text-gray-500">Date:</span>
                        <strong>{fmtDate(viewDocData.transaction_date || viewDocData.income_date || viewDocData.expense_date)}</strong>
                      </div>
                      <div className="flex justify-between py-1 border-b border-gray-200">
                        <span className="text-gray-500">Amount:</span>
                        <strong className="text-emerald-700 text-sm font-mono">{fmt(viewDocData.amount || viewDocData.net_amount)}</strong>
                      </div>
                      {viewDocData.narration && (
                        <div className="pt-2 text-gray-600">
                          <span className="text-gray-500 block text-[10px] uppercase font-bold">Narration</span>
                          {viewDocData.narration}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ) : (
                <p className="text-center text-gray-500">No document details available.</p>
              )}
            </div>

            <div className="p-4 bg-gray-50 border-t border-gray-100 flex items-center justify-end">
              <button
                onClick={() => setViewDocModalOpen(false)}
                className="px-4 py-2 text-xs font-semibold text-gray-600 hover:bg-gray-200 rounded-xl"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ─────────────────────────────────────────────────────────── */}
      {/* MODAL 5: FIX / RENAME PARTY                                 */}
      {/* ─────────────────────────────────────────────────────────── */}
      {fixPartyModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-md w-full shadow-2xl border border-gray-100 overflow-hidden animate-in zoom-in-95 duration-200">
            <div className="p-4 sm:p-5 border-b border-gray-100 flex items-center justify-between bg-amber-50">
              <h3 className="font-bold text-amber-950 text-sm flex items-center gap-2">
                <Edit className="w-4 h-4 text-amber-600" />
                Fix / Rename Party Master
              </h3>
              <button onClick={() => setFixPartyModalOpen(false)} className="text-gray-400 hover:text-gray-600">
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="p-5 space-y-3.5 text-xs">
              <div className="p-3 bg-gray-50 rounded-xl space-y-1 border border-gray-200">
                <span className="text-[10px] uppercase font-bold text-gray-500 block">Current Registered Name</span>
                <strong className="text-gray-900 text-sm">{fixPartyData?.partyName}</strong>
                <span className="text-gray-500 text-xs block">Type: {fixPartyData?.partyType}</span>
              </div>

              <div>
                <label className="font-semibold text-gray-700 block mb-1">New Party Name *</label>
                <input
                  type="text"
                  value={fpNewName}
                  onChange={(e) => setFpNewName(e.target.value)}
                  className="w-full h-9 px-3 border border-gray-200 rounded-xl font-medium"
                />
              </div>

              <div>
                <label className="font-semibold text-gray-700 block mb-1">New Party Type</label>
                <select
                  value={fpNewType}
                  onChange={(e) => setFpNewType(e.target.value)}
                  className="w-full h-9 px-3 border border-gray-200 rounded-xl"
                >
                  <option value="VENDOR">Vendor / Supplier</option>
                  <option value="CUSTOMER">Customer / Partner</option>
                  <option value="EMPLOYEE">Staff / Employee</option>
                  <option value="EXTERNAL">External Party</option>
                </select>
              </div>
            </div>

            <div className="p-4 bg-gray-50 border-t border-gray-100 flex items-center justify-end gap-2">
              <button
                onClick={() => setFixPartyModalOpen(false)}
                className="px-4 py-2 text-xs font-semibold text-gray-600 hover:bg-gray-200 rounded-xl"
              >
                Cancel
              </button>
              <button
                disabled={savingFixParty}
                onClick={handleSaveFixParty}
                className="px-5 py-2 bg-amber-600 hover:bg-amber-700 text-white font-semibold text-xs rounded-xl shadow-sm disabled:opacity-50 inline-flex items-center gap-1.5"
              >
                {savingFixParty ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Check className="w-3.5 h-3.5" />}
                Save Changes
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

