"use client";

import React, { useState } from "react";
import { useVendorAuth } from "@/contexts/VendorAuthContext";
import api from "@/lib/api";
import { Scanner } from '@yudiel/react-qr-scanner';
import { Camera, Keyboard, CheckCircle, XCircle, Loader2 } from "lucide-react";

interface ScanResult {
  memberId: string;
  memberName: string;
  tier: string;
  couponCode: string;
  discountPercentage: number;
  maxDiscount: number;
  validity: string;
}

export default function VendorScanPage() {
  const { } = useVendorAuth();
  
  const [scanMode, setScanMode] = useState<'camera' | 'manual'>('camera');
  const [manualCode, setManualCode] = useState("");
  const [scanResult, setScanResult] = useState<ScanResult | null>(null);
  const [loading, setLoading] = useState(false);

  const [billAmount, setBillAmount] = useState("");

  const handleSimulateScan = async (code: string) => {
    if (!code) return;
    setLoading(true);
    try {
      const res = await api.get(`/vendor/me/verify-member?code=${code}`);
      if (res.data && res.data.success) {
        setScanResult(res.data.data);
      } else {
        alert("Invalid or inactive member.");
      }
    } catch (err: any) {
      console.error(err);
      alert(err.response?.data?.detail || "Failed to verify member code.");
    } finally {
      setLoading(false);
    }
  };

  const handleManualSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!manualCode) return;
    handleSimulateScan(manualCode);
  };

  const resetScan = () => {
    setScanResult(null);
    setManualCode("");
    setBillAmount("");
  };

  const handleProcessTransaction = async () => {
    if (!scanResult) return;
    const amount = parseFloat(billAmount);
    if (!amount || amount <= 0) {
      alert("Please enter a valid bill amount before processing.");
      return;
    }
    
    setLoading(true);
    try {
      const res = await api.post(`/vendor/me/process-scan`, {
        memberId: scanResult.memberId,
        amount: amount
      });
      if (res.data && res.data.success) {
        alert(`Transaction Processed! TXN: ${res.data.txn_number}. Discount Applied: ₹${res.data.discount_amount}`);
        resetScan();
      }
    } catch (err: any) {
      console.error(err);
      alert(err.response?.data?.detail || "Failed to process transaction.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-6 max-w-4xl mx-auto flex flex-col min-h-[calc(100vh-80px)]">
      <div className="flex justify-between items-end mb-6 shrink-0">
        <div>
          <h1 className="text-3xl font-bold text-slate-900 tracking-tight">Scan Coupon</h1>
          <p className="text-sm text-slate-500 mt-2">Scan a VGK Member&apos;s QR Code or manually enter their code to apply discounts.</p>
        </div>
      </div>

      <div className="flex-1 flex flex-col items-center justify-center py-8">
        
        {!scanResult ? (
          <div className="w-full max-w-md bg-white rounded-3xl shadow-xl border border-slate-200 overflow-hidden transition-all">
            
            <div className="flex border-b border-slate-100">
              <button 
                onClick={() => setScanMode('camera')}
                className={`flex-1 py-4 text-sm font-bold transition-all flex items-center justify-center gap-2 ${scanMode === 'camera' ? 'bg-sky-50 text-sky-600 border-b-2 border-sky-500' : 'text-slate-500 hover:bg-slate-50'}`}
              >
                <Camera className="w-4 h-4" /> Use Camera
              </button>
              <button 
                onClick={() => setScanMode('manual')}
                className={`flex-1 py-4 text-sm font-bold transition-all flex items-center justify-center gap-2 ${scanMode === 'manual' ? 'bg-sky-50 text-sky-600 border-b-2 border-sky-500' : 'text-slate-500 hover:bg-slate-50'}`}
              >
                <Keyboard className="w-4 h-4" /> Enter Code
              </button>
            </div>

            <div className="p-8">
              {scanMode === 'camera' ? (
                <div className="flex flex-col items-center animate-in fade-in zoom-in-95 duration-200">
                  <div className="w-64 h-64 rounded-3xl overflow-hidden relative border-4 border-dashed border-sky-300 shadow-inner bg-slate-50 flex items-center justify-center">
                    <Scanner
                      onScan={(result) => {
                        if (result && result.length > 0) {
                          handleSimulateScan(result[0].rawValue);
                        }
                      }}
                    />
                  </div>
                  <p className="text-center text-sm text-slate-500 mt-6 font-medium">
                    Position the member&apos;s QR code within the frame to scan automatically.
                  </p>
                  <button 
                    onClick={() => handleSimulateScan('VGK00214')}
                    className="mt-6 px-6 py-2.5 bg-slate-100 text-slate-600 font-bold rounded-xl text-sm hover:bg-slate-200 transition-all hover:shadow-sm"
                  >
                    (Dev) Simulate Scan
                  </button>
                </div>
              ) : (
                <form onSubmit={handleManualSubmit} className="flex flex-col animate-in fade-in slide-in-from-right-4 duration-200">
                  <label className="text-sm font-bold text-slate-700 mb-2">Coupon / Member Code</label>
                  <input 
                    type="text" 
                    value={manualCode}
                    onChange={(e) => setManualCode(e.target.value.toUpperCase())}
                    placeholder="e.g. CPN-VGK-001"
                    className="w-full px-4 py-4 border-2 border-slate-200 rounded-xl font-mono text-xl text-center tracking-widest focus:ring-4 focus:ring-sky-500/20 focus:border-sky-500 outline-none uppercase transition-all bg-slate-50 focus:bg-white"
                  />
                  <button 
                    type="submit"
                    disabled={!manualCode || loading}
                    className="mt-6 w-full py-3.5 bg-sky-600 text-white font-bold rounded-xl shadow-lg shadow-sky-600/20 hover:bg-sky-700 disabled:opacity-50 transition-all flex items-center justify-center gap-2 active:scale-[0.98]"
                  >
                    {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : "Verify Code"}
                  </button>
                </form>
              )}
            </div>
          </div>
        ) : (
          <div className="w-full max-w-lg bg-white rounded-3xl shadow-xl border border-slate-200 overflow-hidden animate-in zoom-in-95 duration-300">
            <div className="bg-emerald-500 text-white p-8 text-center relative overflow-hidden">
              <div className="absolute top-0 right-0 w-32 h-32 bg-white/10 rounded-full blur-2xl -mr-10 -mt-10"></div>
              <div className="w-20 h-20 bg-white rounded-full flex items-center justify-center mx-auto mb-4 shadow-xl">
                <CheckCircle className="w-12 h-12 text-emerald-500" />
              </div>
              <h2 className="text-3xl font-black tracking-tight">Valid Member</h2>
              <p className="text-emerald-50 font-medium mt-1">Code verified successfully</p>
            </div>

            <div className="p-8">
              <div className="flex items-center gap-5 mb-8 p-5 bg-slate-50 rounded-2xl border border-slate-100 shadow-inner">
                <div className="w-14 h-14 bg-slate-200 rounded-full flex items-center justify-center font-bold text-slate-600 text-2xl shrink-0">
                  {scanResult.memberName.charAt(0)}
                </div>
                <div className="flex-1 min-w-0">
                  <h3 className="font-bold text-slate-900 text-xl truncate">{scanResult.memberName}</h3>
                  <div className="flex items-center gap-3 mt-1">
                    <span className="font-mono text-sm font-semibold text-slate-500">{scanResult.memberId}</span>
                    <span className="bg-slate-900 text-white text-xs font-bold px-2.5 py-1 rounded-md uppercase tracking-wider">{scanResult.tier}</span>
                  </div>
                </div>
              </div>

              <div className="border-t-2 border-dashed border-slate-200 pt-8 mb-8">
                <h4 className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-5">Applicable Discount</h4>
                
                <div className="space-y-4">
                  <div className="flex justify-between items-center">
                    <span className="text-slate-600 font-medium">Coupon Code</span>
                    <span className="font-mono font-bold text-slate-900 bg-slate-100 px-3 py-1 rounded-lg">{scanResult.couponCode}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-slate-600 font-medium">Discount Value</span>
                    <span className="text-3xl font-black text-emerald-600">{scanResult.discountPercentage}% OFF</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-slate-600 font-medium">Maximum Cap</span>
                    <span className="font-bold text-slate-900 text-lg">₹{scanResult.maxDiscount.toLocaleString()}</span>
                  </div>
                </div>
              </div>

              <div className="mb-8">
                <label className="text-sm font-bold text-slate-700 mb-3 block">Total Bill Amount (₹)</label>
                <div className="relative">
                  <span className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 font-bold text-lg">₹</span>
                  <input 
                    type="number" 
                    value={billAmount}
                    onChange={(e) => setBillAmount(e.target.value)}
                    placeholder="0.00"
                    className="w-full pl-10 pr-4 py-4 border-2 border-slate-200 rounded-2xl font-black text-2xl focus:ring-4 focus:ring-sky-500/20 focus:border-sky-500 outline-none transition-all"
                  />
                </div>
              </div>

              <div className="flex gap-4">
                <button 
                  onClick={resetScan}
                  className="flex-1 py-4 bg-white border-2 border-slate-200 text-slate-700 font-bold rounded-2xl hover:bg-slate-50 transition-all hover:border-slate-300"
                >
                  Cancel
                </button>
                <button 
                  onClick={handleProcessTransaction}
                  disabled={loading}
                  className="flex-[2] py-4 bg-sky-600 text-white font-bold rounded-2xl shadow-lg shadow-sky-600/20 hover:bg-sky-700 transition-all flex items-center justify-center gap-2 active:scale-[0.98] disabled:opacity-70"
                >
                  {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : "Process Transaction"}
                </button>
              </div>
            </div>
          </div>
        )}

      </div>
    </div>
  );
}
