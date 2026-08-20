"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useMemberAuth } from "@/contexts/MemberAuthContext";
import api from "@/lib/api";

export default function MemberWithdrawPage() {
  const { user } = useMemberAuth();
  const [walletBalance, setWalletBalance] = useState(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!user || !user.id) return;
    
    // Fetch latest balance
    api.get(`/vgk/auth/me`)
      .then(res => {
        if (res.data && res.data.success) {
           setWalletBalance(res.data.dashboard?.wallet_balance || user.wallet_balance || 0);
        }
      })
      .catch(err => console.error("Failed to fetch balance", err))
      .finally(() => setLoading(false));

  }, [user]);

  if (loading) {
    return (
      <div className="min-h-[80vh] flex items-center justify-center">
        <i className="fas fa-circle-notch fa-spin text-4xl text-amber-500"></i>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-3xl mx-auto min-h-screen">
      <div className="mb-6">
        <Link href="/member/wallet" className="text-slate-500 hover:text-slate-900 flex items-center gap-2 font-medium">
          <i className="fas fa-arrow-left"></i> Back to Ledger
        </Link>
      </div>

      <div className="bg-white rounded-3xl p-8 border border-slate-200 shadow-sm relative overflow-hidden">
        <div className="absolute top-0 right-0 w-64 h-64 bg-emerald-50 rounded-full blur-3xl opacity-50 -mr-10 -mt-10 pointer-events-none"></div>
        
        <div className="text-center mb-8 relative z-10">
          <div className="w-20 h-20 bg-emerald-100 text-emerald-600 rounded-full flex items-center justify-center text-3xl mx-auto mb-4 shadow-inner">
            <i className="fas fa-robot"></i>
          </div>
          <h1 className="text-3xl font-black text-slate-900 mb-2">Automated Payouts</h1>
          <p className="text-slate-500 text-lg">Manual withdrawals are no longer required.</p>
        </div>

        <div className="bg-slate-50 border border-slate-200 rounded-2xl p-6 mb-8 relative z-10">
          <div className="flex justify-between items-center mb-2">
            <span className="text-slate-500 font-medium">Current Withdrawable Balance</span>
            <span className="text-2xl font-black text-slate-900">₹{walletBalance.toLocaleString()}</span>
          </div>
        </div>

        <div className="space-y-4 relative z-10">
          <div className="flex gap-4 p-4 rounded-xl bg-blue-50 border border-blue-100">
            <i className="fas fa-info-circle text-blue-500 text-xl mt-1"></i>
            <div>
              <h3 className="font-bold text-blue-900 mb-1">Daily Processing at 7:00 AM</h3>
              <p className="text-blue-800 text-sm">
                The system automatically generates withdrawal requests daily at 7:00 AM (Monday to Saturday) for all members with an eligible balance in their withdrawable wallet.
              </p>
            </div>
          </div>
          
          <div className="flex gap-4 p-4 rounded-xl bg-amber-50 border border-amber-100">
            <i className="fas fa-university text-amber-500 text-xl mt-1"></i>
            <div>
              <h3 className="font-bold text-amber-900 mb-1">Bank Account Verification</h3>
              <p className="text-amber-800 text-sm">
                Please ensure your bank details and KYC are fully verified in your profile settings to ensure automated transfers do not bounce.
              </p>
            </div>
          </div>
        </div>

        <div className="mt-8 text-center relative z-10">
          <Link href="/member/settings" className="inline-flex items-center gap-2 px-6 py-3 bg-slate-900 text-white font-bold rounded-xl hover:bg-slate-800 transition-colors">
            <i className="fas fa-user-check"></i> Verify Bank Details
          </Link>
        </div>
      </div>
    </div>
  );
}
