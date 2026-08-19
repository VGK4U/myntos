"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useMemberAuth } from "@/contexts/MemberAuthContext";
import api from "@/lib/api";

export default function MemberWalletPage() {
  const { user } = useMemberAuth();

  const [activeTab, setActiveTab] = useState("all");

  const [walletBalance, setWalletBalance] = useState(0);
  const [pendingClearance, setPendingClearance] = useState(0);
  const [transactions, setTransactions] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!user || !user.mnr_id) return;

    const fetchData = async () => {
      setLoading(true);
      try {
        const res = await api.get(`/user/${user.mnr_id}/comprehensive`);
        if (res.data && res.data.success) {
          setWalletBalance(res.data.dashboard?.wallet_balance || 0);
          setPendingClearance(res.data.dashboard?.pending_withdrawals || 0);
        }

        const finRes = await api.get(`/user/${user.mnr_id}/financial-summary`);
        if (finRes.data && finRes.data.success) {
          const txs = finRes.data.recent_transactions || [];
          setTransactions(
            txs.map((tx: any) => ({
              id: tx.id || Math.random().toString(),
              date: tx.date || tx.created_at || new Date().toISOString(),
              desc: tx.description || tx.transaction_type || 'Transaction',
              amount: tx.amount || 0,
              type: (tx.amount || 0) > 0 ? 'CREDIT' : 'DEBIT',
              status: tx.status || 'CLEARED'
            }))
          );
        }
      } catch (err) {
        console.error("Failed to fetch wallet data", err);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [user]);

  const filteredTx = activeTab === "all" ? transactions : transactions.filter(t => t.type.toLowerCase() === activeTab);

  return (
    <div className="p-6 max-w-7xl mx-auto flex flex-col h-[calc(100vh-80px)]">
      <div className="flex justify-between items-end mb-6 shrink-0">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 tracking-tight">My Wallet</h1>
          <p className="text-sm text-gray-500 mt-2">Manage your E-Wallet funds, view statements, and request withdrawals.</p>
        </div>
        <div className="flex space-x-3">
          <Link href="/member/wallet/withdraw" className="px-5 py-2.5 bg-gradient-to-r from-amber-500 to-amber-600 text-white font-bold rounded-lg shadow-md hover:from-amber-600 hover:to-amber-700 transition-colors">
            <i className="fas fa-money-bill-wave mr-2"></i> Request Withdrawal
          </Link>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8 shrink-0">
        <div className="bg-gradient-to-br from-gray-900 to-gray-800 p-6 rounded-2xl shadow-lg text-white relative overflow-hidden">
          <i className="fas fa-wallet absolute right-[-20px] bottom-[-20px] text-8xl opacity-10"></i>
          <p className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-2">Available Balance</p>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl text-amber-500 font-medium">₹</span>
            <h2 className="text-4xl font-bold tracking-tight">{walletBalance.toLocaleString('en-IN')}</h2>
          </div>
          <p className="text-sm text-gray-400 mt-4">
            <i className="fas fa-check-circle text-green-400 mr-1"></i> Ready for withdrawal
          </p>
        </div>

        <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-100 relative overflow-hidden">
          <p className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-2">Pending Clearance</p>
          <div className="flex items-baseline gap-2">
            <span className="text-xl text-gray-500 font-medium">₹</span>
            <h2 className="text-3xl font-bold text-gray-900">{pendingClearance.toLocaleString('en-IN')}</h2>
          </div>
          <p className="text-sm text-amber-600 font-medium mt-4">
            <i className="fas fa-clock mr-1"></i> Awaiting admin approval
          </p>
        </div>
        
        <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-100 flex flex-col justify-center">
          <div className="flex items-center gap-4">
            <div className="w-14 h-14 rounded-full bg-blue-50 text-blue-600 flex items-center justify-center text-2xl shrink-0">
              <i className="fas fa-university"></i>
            </div>
            <div>
              <p className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-1">Linked Bank</p>
              <p className="font-bold text-gray-900">HDFC Bank</p>
              <p className="text-sm text-gray-500">•••• 4521</p>
            </div>
          </div>
          <Link href="/member/settings" className="mt-4 text-sm font-bold text-amber-600 hover:text-amber-700">
            Change Account &rarr;
          </Link>
        </div>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-gray-100 flex-1 overflow-hidden flex flex-col min-h-0">
        <div className="p-4 border-b border-gray-200 bg-gray-50 flex justify-between items-center">
          <div className="flex space-x-1 bg-gray-200/50 p-1 rounded-lg">
            <button 
              onClick={() => setActiveTab("all")}
              className={`px-4 py-1.5 text-sm font-medium rounded-md transition-colors ${activeTab === 'all' ? 'bg-white shadow text-gray-900' : 'text-gray-500 hover:text-gray-700'}`}
            >
              All
            </button>
            <button 
              onClick={() => setActiveTab("credit")}
              className={`px-4 py-1.5 text-sm font-medium rounded-md transition-colors ${activeTab === 'credit' ? 'bg-white shadow text-green-700' : 'text-gray-500 hover:text-gray-700'}`}
            >
              Credits (+IN)
            </button>
            <button 
              onClick={() => setActiveTab("debit")}
              className={`px-4 py-1.5 text-sm font-medium rounded-md transition-colors ${activeTab === 'debit' ? 'bg-white shadow text-red-700' : 'text-gray-500 hover:text-gray-700'}`}
            >
              Debits (-OUT)
            </button>
          </div>
          
          <button className="text-gray-500 hover:text-gray-700">
            <i className="fas fa-filter text-lg"></i>
          </button>
        </div>

        <div className="flex-1 overflow-y-auto">
          <table className="w-full text-left">
            <thead className="bg-white sticky top-0 z-10">
              <tr className="border-b border-gray-200">
                <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Transaction ID / Date</th>
                <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Description</th>
                <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider text-right">Amount</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {filteredTx.map((tx, idx) => (
                <tr key={idx} className="hover:bg-gray-50 transition-colors group">
                  <td className="p-4">
                    <p className="font-mono text-xs text-gray-500">{tx.id}</p>
                    <p className="text-sm font-medium text-gray-900 mt-0.5">{new Date(tx.date).toLocaleDateString()}</p>
                  </td>
                  <td className="p-4">
                    <div className="flex items-center">
                      <div className={`w-8 h-8 rounded-full flex items-center justify-center mr-3 shrink-0 ${
                        tx.type === 'CREDIT' ? 'bg-green-100 text-green-600' : 'bg-red-100 text-red-600'
                      }`}>
                        <i className={`fas ${tx.type === 'CREDIT' ? 'fa-arrow-down' : 'fa-arrow-up'}`}></i>
                      </div>
                      <div>
                        <p className="text-sm font-medium text-gray-900">{tx.desc}</p>
                        <span className="text-[10px] font-bold text-gray-500 uppercase">{tx.status}</span>
                      </div>
                    </div>
                  </td>
                  <td className="p-4 text-right">
                    <span className={`text-lg font-bold ${tx.type === 'CREDIT' ? 'text-green-600' : 'text-gray-900'}`}>
                      {tx.type === 'CREDIT' ? '+' : ''}₹{Math.abs(tx.amount).toLocaleString('en-IN')}
                    </span>
                  </td>
                </tr>
              ))}
              
              {filteredTx.length === 0 && (
                <tr>
                  <td colSpan={3} className="p-12 text-center text-gray-500">
                    <i className="fas fa-receipt text-4xl mb-3 text-gray-300"></i>
                    <p>No transactions found for this filter.</p>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
