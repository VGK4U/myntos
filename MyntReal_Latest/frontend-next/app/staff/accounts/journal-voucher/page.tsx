"use client";

import { useState, useEffect } from "react";
import { useStaffAuth } from "@/contexts/StaffAuthContext";
import { getApiUrl } from "@/lib/api";
import Link from "next/link";

interface JournalEntryLine {
  id: string;
  accountId: string;
  accountName: string;
  type: "DEBIT" | "CREDIT";
  amount: number | "";
  narration: string;
}

export default function JournalVoucherPage() {
  const { token } = useStaffAuth();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  
  // Voucher Meta
  const [voucherDate, setVoucherDate] = useState(new Date().toISOString().split('T')[0]);
  const [reference, setReference] = useState("");
  const [description, setDescription] = useState("");

  // Voucher Lines
  const [lines, setLines] = useState<JournalEntryLine[]>([
    { id: "1", accountId: "", accountName: "", type: "DEBIT", amount: "", narration: "" },
    { id: "2", accountId: "", accountName: "", type: "CREDIT", amount: "", narration: "" }
  ]);

  // Mocked accounts for UI, usually fetched from Chart of Accounts API
  const accountOptions = [
    { id: "1001", name: "Cash in Hand" },
    { id: "1002", name: "HDFC Bank Account" },
    { id: "4001", name: "Sales Revenue" },
    { id: "5001", name: "Office Expenses" },
    { id: "5002", name: "Marketing Expenses" },
    { id: "2001", name: "Accounts Payable" },
  ];

  const addLine = () => {
    setLines([...lines, { 
      id: Date.now().toString(), 
      accountId: "", 
      accountName: "", 
      type: "DEBIT", 
      amount: "", 
      narration: "" 
    }]);
  };

  const removeLine = (id: string) => {
    if (lines.length <= 2) return; // Minimum 2 lines required
    setLines(lines.filter(l => l.id !== id));
  };

  const updateLine = (id: string, field: keyof JournalEntryLine, value: any) => {
    setLines(lines.map(l => {
      if (l.id === id) {
        const updated = { ...l, [field]: value };
        if (field === "accountId") {
          updated.accountName = accountOptions.find(a => a.id === value)?.name || "";
        }
        return updated;
      }
      return l;
    }));
  };

  const totalDebit = lines.filter(l => l.type === "DEBIT").reduce((sum, l) => sum + (Number(l.amount) || 0), 0);
  const totalCredit = lines.filter(l => l.type === "CREDIT").reduce((sum, l) => sum + (Number(l.amount) || 0), 0);
  const isBalanced = totalDebit === totalCredit && totalDebit > 0;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setSuccess("");

    if (!isBalanced) {
      setError("Voucher is not balanced. Total Debit must equal Total Credit.");
      return;
    }

    const invalidLines = lines.some(l => !l.accountId || !l.amount);
    if (invalidLines) {
      setError("Please select an account and enter an amount for all lines.");
      return;
    }

    setLoading(true);
    try {
      // API call to actual FastAPI backend
      const res = await fetch(`${getApiUrl()}/api/v1/staff/accounts/journal-voucher`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          date: voucherDate,
          reference,
          description,
          entries: lines.map(l => ({
            account_id: l.accountId,
            type: l.type,
            amount: Number(l.amount),
            narration: l.narration
          }))
        })
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Failed to submit journal voucher");
      
      setSuccess(`Journal Voucher ${data.voucher_no || 'submitted'} successfully!`);
      // Reset form
      setReference("");
      setDescription("");
      setLines([
        { id: Date.now().toString(), accountId: "", accountName: "", type: "DEBIT", amount: "", narration: "" },
        { id: (Date.now() + 1).toString(), accountId: "", accountName: "", type: "CREDIT", amount: "", narration: "" }
      ]);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50/50 pb-12">
      {/* Enterprise Header */}
      <div className="bg-white border-b border-gray-200 px-8 py-6 sticky top-0 z-10 shadow-sm">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 max-w-screen-xl mx-auto">
          <div className="flex items-center gap-4">
            <Link href="/staff/accounts/general-ledger" className="w-10 h-10 bg-gray-50 border border-gray-200 rounded-lg flex items-center justify-center text-gray-500 hover:text-indigo-600 hover:bg-indigo-50 transition-colors">
              <i className="fas fa-arrow-left"></i>
            </Link>
            <div>
              <h1 className="text-2xl font-bold text-gray-900 tracking-tight flex items-center gap-2">
                <i className="fas fa-file-invoice-dollar text-indigo-600 text-xl hidden sm:inline-block"></i>
                Journal Voucher
              </h1>
              <p className="text-sm text-gray-500 font-medium mt-0.5">Create manual accounting entries and transfers</p>
            </div>
          </div>
          <div className="flex gap-3">
            <button className="px-4 py-2 bg-white border border-gray-300 text-gray-700 font-medium rounded-lg hover:bg-gray-50 transition-all flex items-center gap-2 text-sm shadow-sm">
              <i className="fas fa-print"></i> Print Draft
            </button>
            <button onClick={handleSubmit} disabled={loading || !isBalanced} className="px-6 py-2 bg-indigo-600 text-white font-medium rounded-lg hover:bg-indigo-700 disabled:opacity-50 transition-all flex items-center gap-2 text-sm shadow-sm">
              {loading ? <i className="fas fa-spinner fa-spin"></i> : <i className="fas fa-save"></i>}
              Post Voucher
            </button>
          </div>
        </div>
      </div>

      <div className="p-8 max-w-screen-xl mx-auto">
        {error && (
          <div className="mb-6 bg-red-50 border border-red-200 rounded-xl p-4 flex items-start gap-3 shadow-sm animate-in fade-in slide-in-from-top-2">
            <i className="fas fa-exclamation-circle text-red-500 mt-0.5"></i>
            <div>
              <h3 className="text-sm font-bold text-red-800">Validation Error</h3>
              <p className="text-sm text-red-600 mt-1">{error}</p>
            </div>
          </div>
        )}

        {success && (
          <div className="mb-6 bg-green-50 border border-green-200 rounded-xl p-4 flex items-start gap-3 shadow-sm animate-in fade-in slide-in-from-top-2">
            <i className="fas fa-check-circle text-green-500 mt-0.5"></i>
            <div>
              <h3 className="text-sm font-bold text-green-800">Success</h3>
              <p className="text-sm text-green-600 mt-1">{success}</p>
            </div>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Section 1: Meta Information */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
            <div className="p-4 border-b border-gray-100 bg-gray-50/50">
              <h2 className="text-sm font-bold text-gray-700 uppercase tracking-wider flex items-center gap-2">
                <i className="fas fa-info-circle text-indigo-400"></i> Voucher Details
              </h2>
            </div>
            <div className="p-6 grid grid-cols-1 md:grid-cols-3 gap-6">
              <div>
                <label className="block text-xs font-bold text-gray-600 uppercase mb-2">Voucher Date <span className="text-red-500">*</span></label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    <i className="far fa-calendar-alt text-gray-400"></i>
                  </div>
                  <input
                    type="date"
                    required
                    value={voucherDate}
                    onChange={(e) => setVoucherDate(e.target.value)}
                    className="block w-full pl-10 pr-3 py-2.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-colors bg-gray-50 hover:bg-white focus:bg-white"
                  />
                </div>
              </div>
              
              <div>
                <label className="block text-xs font-bold text-gray-600 uppercase mb-2">Reference No.</label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    <i className="fas fa-hashtag text-gray-400"></i>
                  </div>
                  <input
                    type="text"
                    value={reference}
                    onChange={(e) => setReference(e.target.value)}
                    placeholder="e.g. INV-2026-08-01"
                    className="block w-full pl-10 pr-3 py-2.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-colors bg-gray-50 hover:bg-white focus:bg-white"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-bold text-gray-600 uppercase mb-2">Description / Memo <span className="text-red-500">*</span></label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    <i className="fas fa-align-left text-gray-400"></i>
                  </div>
                  <input
                    type="text"
                    required
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    placeholder="Brief description of this entry"
                    className="block w-full pl-10 pr-3 py-2.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-colors bg-gray-50 hover:bg-white focus:bg-white"
                  />
                </div>
              </div>
            </div>
          </div>

          {/* Section 2: Line Items */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
            <div className="p-4 border-b border-gray-100 bg-gray-50/50 flex justify-between items-center">
              <h2 className="text-sm font-bold text-gray-700 uppercase tracking-wider flex items-center gap-2">
                <i className="fas fa-list text-indigo-400"></i> Ledger Entries
              </h2>
              <button type="button" onClick={addLine} className="text-xs font-bold text-indigo-600 bg-indigo-50 px-3 py-1.5 rounded-md hover:bg-indigo-100 transition-colors flex items-center gap-1">
                <i className="fas fa-plus"></i> Add Row
              </button>
            </div>
            
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead className="bg-white border-b border-gray-200">
                  <tr>
                    <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider w-16 text-center">Dr/Cr</th>
                    <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider w-1/3">Account Head <span className="text-red-500">*</span></th>
                    <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Amount (₹) <span className="text-red-500">*</span></th>
                    <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Narration / Remarks</th>
                    <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider w-12 text-center"></th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100 bg-gray-50/30">
                  {lines.map((line, index) => (
                    <tr key={line.id} className="group hover:bg-white transition-colors">
                      <td className="p-4">
                        <select
                          value={line.type}
                          onChange={(e) => updateLine(line.id, "type", e.target.value)}
                          className={`w-full p-2 text-sm font-bold border-gray-300 rounded-lg focus:ring-indigo-500 focus:border-indigo-500 text-center
                            ${line.type === 'DEBIT' ? 'bg-red-50 text-red-700' : 'bg-green-50 text-green-700'}`}
                        >
                          <option value="DEBIT">Dr</option>
                          <option value="CREDIT">Cr</option>
                        </select>
                      </td>
                      <td className="p-4">
                        <div className="relative">
                          <select
                            value={line.accountId}
                            onChange={(e) => updateLine(line.id, "accountId", e.target.value)}
                            className="w-full p-2 text-sm border-gray-300 rounded-lg focus:ring-indigo-500 focus:border-indigo-500 bg-white shadow-sm"
                            required
                          >
                            <option value="">Search Account...</option>
                            {accountOptions.map(acc => (
                              <option key={acc.id} value={acc.id}>{acc.name}</option>
                            ))}
                          </select>
                        </div>
                      </td>
                      <td className="p-4">
                        <div className="relative">
                          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                            <span className="text-gray-500 font-medium text-sm">₹</span>
                          </div>
                          <input
                            type="number"
                            min="1"
                            step="0.01"
                            required
                            value={line.amount}
                            onChange={(e) => updateLine(line.id, "amount", e.target.value)}
                            placeholder="0.00"
                            className="w-full pl-8 pr-3 py-2 text-sm font-bold border-gray-300 rounded-lg focus:ring-indigo-500 focus:border-indigo-500 text-right shadow-sm bg-white"
                          />
                        </div>
                      </td>
                      <td className="p-4">
                        <input
                          type="text"
                          value={line.narration}
                          onChange={(e) => updateLine(line.id, "narration", e.target.value)}
                          placeholder="Optional line remarks..."
                          className="w-full p-2 text-sm border-gray-300 rounded-lg focus:ring-indigo-500 focus:border-indigo-500 shadow-sm bg-white"
                        />
                      </td>
                      <td className="p-4 text-center">
                        <button 
                          type="button" 
                          onClick={() => removeLine(line.id)}
                          disabled={lines.length <= 2}
                          className="w-8 h-8 rounded text-gray-400 hover:text-red-500 hover:bg-red-50 disabled:opacity-30 disabled:hover:bg-transparent disabled:hover:text-gray-400 transition-colors"
                        >
                          <i className="fas fa-trash-alt"></i>
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
                <tfoot className="bg-white border-t border-gray-200">
                  <tr>
                    <td colSpan={2} className="p-4 text-right font-bold text-gray-700 uppercase tracking-wider text-sm">
                      Total
                    </td>
                    <td className="p-4">
                      <div className="flex flex-col gap-2">
                        <div className="flex justify-between items-center px-3 py-1.5 bg-red-50 rounded text-red-700 font-bold text-sm border border-red-100">
                          <span className="text-xs uppercase">Debit (Dr)</span>
                          <span>₹ {totalDebit.toLocaleString('en-IN', {minimumFractionDigits: 2})}</span>
                        </div>
                        <div className="flex justify-between items-center px-3 py-1.5 bg-green-50 rounded text-green-700 font-bold text-sm border border-green-100">
                          <span className="text-xs uppercase">Credit (Cr)</span>
                          <span>₹ {totalCredit.toLocaleString('en-IN', {minimumFractionDigits: 2})}</span>
                        </div>
                      </div>
                    </td>
                    <td colSpan={2} className="p-4 align-middle">
                      {totalDebit === 0 && totalCredit === 0 ? (
                        <div className="text-xs text-gray-400 italic">Enter amounts to calculate balance</div>
                      ) : isBalanced ? (
                        <div className="flex items-center gap-2 text-green-600 font-bold text-sm bg-green-50 px-4 py-2 rounded-lg border border-green-200">
                          <i className="fas fa-balance-scale"></i> Voucher is Balanced
                        </div>
                      ) : (
                        <div className="flex items-center gap-2 text-red-600 font-bold text-sm bg-red-50 px-4 py-2 rounded-lg border border-red-200">
                          <i className="fas fa-exclamation-triangle"></i> Difference: ₹ {Math.abs(totalDebit - totalCredit).toLocaleString('en-IN', {minimumFractionDigits: 2})}
                        </div>
                      )}
                    </td>
                  </tr>
                </tfoot>
              </table>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
}
