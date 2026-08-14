"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMemberAuth } from "@/contexts/MemberAuthContext";

export default function MemberWithdrawPage() {
  const { user } = useMemberAuth();
  const router = useRouter();
  
  const walletBalance = 42500;
  
  const [amount, setAmount] = useState("");
  const [pin, setPin] = useState("");
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleNext = (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    
    const reqAmount = parseInt(amount);
    if (!reqAmount || reqAmount < 500) {
      setError("Minimum withdrawal amount is ₹500");
      return;
    }
    if (reqAmount > walletBalance) {
      setError("Insufficient wallet balance");
      return;
    }
    
    setStep(2);
  };

  const handleConfirm = (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    
    if (pin.length !== 6) {
      setError("Please enter your 6-digit transaction PIN");
      return;
    }
    
    setLoading(true);
    
    // Simulate API Call
    setTimeout(() => {
      setLoading(false);
      setStep(3); // Success Screen
    }, 1500);
  };

  return (
    <div className="p-6 max-w-4xl mx-auto flex flex-col h-[calc(100vh-80px)]">
      <div className="flex justify-between items-end mb-6 shrink-0">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 tracking-tight">Withdraw Funds</h1>
          <p className="text-sm text-gray-500 mt-2">Transfer your E-Wallet balance directly to your registered bank account.</p>
        </div>
        <div>
          <Link href="/member/wallet" className="px-4 py-2 bg-white border border-gray-300 text-gray-700 font-medium rounded-lg shadow-sm hover:bg-gray-50 transition-colors">
            <i className="fas fa-times mr-2"></i> Cancel
          </Link>
        </div>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
        {/* Progress Tracker */}
        <div className="flex border-b border-gray-100 bg-gray-50/50 p-4">
          <div className={`flex-1 text-center text-sm font-bold ${step >= 1 ? 'text-amber-600' : 'text-gray-400'}`}>
            1. Amount Details
          </div>
          <div className="text-gray-300"><i className="fas fa-chevron-right"></i></div>
          <div className={`flex-1 text-center text-sm font-bold ${step >= 2 ? 'text-amber-600' : 'text-gray-400'}`}>
            2. Authorization
          </div>
          <div className="text-gray-300"><i className="fas fa-chevron-right"></i></div>
          <div className={`flex-1 text-center text-sm font-bold ${step === 3 ? 'text-green-600' : 'text-gray-400'}`}>
            3. Confirmation
          </div>
        </div>

        <div className="p-8">
          
          {error && (
            <div className="mb-6 p-4 bg-red-50 border-l-4 border-red-500 text-red-700 rounded-md text-sm font-medium flex items-center">
              <i className="fas fa-exclamation-circle mr-2 text-lg"></i>
              {error}
            </div>
          )}

          {step === 1 && (
            <div className="max-w-md mx-auto">
              <div className="bg-amber-50 rounded-lg p-5 border border-amber-100 mb-6 flex justify-between items-center">
                <div>
                  <p className="text-xs text-amber-800 uppercase tracking-wider font-bold mb-1">Available to Withdraw</p>
                  <h3 className="text-2xl font-bold text-amber-900">₹{walletBalance.toLocaleString('en-IN')}</h3>
                </div>
                <i className="fas fa-wallet text-3xl text-amber-200"></i>
              </div>

              <form onSubmit={handleNext}>
                <div className="mb-6">
                  <label className="block text-sm font-bold text-gray-700 mb-2">Withdrawal Amount (₹)</label>
                  <div className="relative">
                    <span className="absolute left-4 top-1/2 transform -translate-y-1/2 text-xl font-bold text-gray-400">₹</span>
                    <input 
                      type="number" 
                      required
                      value={amount}
                      onChange={(e) => setAmount(e.target.value)}
                      placeholder="0.00"
                      className="w-full pl-10 pr-4 py-4 text-2xl font-bold text-gray-900 border border-gray-300 rounded-xl focus:ring-2 focus:ring-amber-500 outline-none"
                    />
                  </div>
                  <div className="flex justify-between mt-2">
                    <span className="text-xs text-gray-500">Min. ₹500</span>
                    <button type="button" onClick={() => setAmount(walletBalance.toString())} className="text-xs font-bold text-amber-600 hover:underline">Withdraw Max</button>
                  </div>
                </div>

                <div className="mb-8 p-4 border border-gray-200 rounded-lg bg-gray-50">
                  <h4 className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-3">Transfer Destination</h4>
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-full bg-white border border-gray-200 flex items-center justify-center text-blue-600 shadow-sm">
                      <i className="fas fa-university"></i>
                    </div>
                    <div>
                      <p className="text-sm font-bold text-gray-900">HDFC Bank (•••• 4521)</p>
                      <p className="text-xs text-gray-500">{user?.first_name} {user?.last_name}</p>
                    </div>
                  </div>
                </div>

                <button type="submit" className="w-full py-4 bg-gray-900 text-white font-bold rounded-xl shadow-lg hover:bg-gray-800 transition-transform transform hover:-translate-y-0.5">
                  Continue to Authorization
                </button>
              </form>
            </div>
          )}

          {step === 2 && (
            <div className="max-w-md mx-auto text-center">
              <div className="w-16 h-16 bg-blue-50 text-blue-500 rounded-full flex items-center justify-center text-2xl mx-auto mb-4 border border-blue-100">
                <i className="fas fa-shield-alt"></i>
              </div>
              <h2 className="text-xl font-bold text-gray-900 mb-2">Authorize Transfer</h2>
              <p className="text-sm text-gray-500 mb-8">
                You are requesting to withdraw <strong>₹{parseInt(amount).toLocaleString('en-IN')}</strong> to your HDFC Bank account.
              </p>

              <form onSubmit={handleConfirm}>
                <div className="mb-8">
                  <label className="block text-sm font-bold text-gray-700 mb-3">Enter 6-Digit Transaction PIN</label>
                  <input 
                    type="password" 
                    required
                    maxLength={6}
                    value={pin}
                    onChange={(e) => setPin(e.target.value)}
                    placeholder="••••••"
                    className="w-full max-w-xs mx-auto block text-center tracking-[1em] font-mono text-2xl py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-amber-500 outline-none"
                  />
                </div>

                <div className="flex gap-4">
                  <button type="button" onClick={() => setStep(1)} className="flex-1 py-3 bg-white border border-gray-300 text-gray-700 font-bold rounded-xl hover:bg-gray-50 transition-colors">
                    Back
                  </button>
                  <button type="submit" disabled={loading} className="flex-1 py-3 bg-amber-500 text-gray-900 font-bold rounded-xl shadow-lg hover:bg-amber-400 transition-colors disabled:opacity-70">
                    {loading ? <i className="fas fa-spinner fa-spin"></i> : 'Confirm Request'}
                  </button>
                </div>
              </form>
            </div>
          )}

          {step === 3 && (
            <div className="max-w-md mx-auto text-center py-8">
              <div className="w-20 h-20 bg-green-100 text-green-500 rounded-full flex items-center justify-center text-4xl mx-auto mb-6">
                <i className="fas fa-check"></i>
              </div>
              <h2 className="text-2xl font-bold text-gray-900 mb-2">Request Submitted!</h2>
              <p className="text-gray-600 mb-8">
                Your withdrawal request for <strong>₹{parseInt(amount).toLocaleString('en-IN')}</strong> has been submitted successfully and is pending admin clearance.
              </p>
              
              <div className="bg-gray-50 rounded-lg p-4 mb-8 text-left border border-gray-200">
                <div className="flex justify-between mb-2 text-sm">
                  <span className="text-gray-500">Transaction ID</span>
                  <span className="font-mono font-bold text-gray-900">TXN9042</span>
                </div>
                <div className="flex justify-between mb-2 text-sm">
                  <span className="text-gray-500">Expected Processing</span>
                  <span className="font-bold text-gray-900">2-3 Business Days</span>
                </div>
              </div>

              <button onClick={() => router.push('/member/wallet')} className="w-full py-3 bg-gray-900 text-white font-bold rounded-xl hover:bg-gray-800 transition-colors">
                Return to Wallet
              </button>
            </div>
          )}

        </div>
      </div>
    </div>
  );
}
