"use client";

import React, { useState } from "react";
import { useVendorAuth } from "@/contexts/VendorAuthContext";
import api from "@/lib/api";
import { Scanner } from '@yudiel/react-qr-scanner';

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
    <div className="p-6 max-w-4xl mx-auto flex flex-col h-[calc(100vh-80px)]">
      <div className="flex justify-between items-end mb-6 shrink-0">
        <div>
          <h1 className="text-3xl font-bold text-slate-900 tracking-tight">Scan Coupon</h1>
          <p className="text-sm text-slate-500 mt-2">Scan a VGK Member&apos;s QR Code or manually enter their code to apply discounts.</p>
        </div>
      </div>

      <div className="flex-1 flex flex-col items-center justify-center">
        
        {!scanResult ? (
          <div className="w-full max-w-md bg-white rounded-2xl shadow-xl border border-slate-200 overflow-hidden">
            
            <div className="flex border-b border-slate-100">
              <button 
                onClick={() => setScanMode('camera')}
                className={`flex-1 py-4 text-sm font-bold transition-colors ${scanMode === 'camera' ? 'bg-slate-50 text-sky-600 border-b-2 border-sky-500' : 'text-slate-500 hover:bg-slate-50'}`}
              >
                <i className="fas fa-camera mr-2"></i> Use Camera
              </button>
              <button 
                onClick={() => setScanMode('manual')}
                className={`flex-1 py-4 text-sm font-bold transition-colors ${scanMode === 'manual' ? 'bg-slate-50 text-sky-600 border-b-2 border-sky-500' : 'text-slate-500 hover:bg-slate-50'}`}
              >
                <i className="fas fa-keyboard mr-2"></i> Enter Code
              </button>
            </div>

            <div className="p-8">
              {scanMode === 'camera' ? (
                <div className="flex flex-col items-center">
                  <div className="w-64 h-64 rounded-2xl overflow-hidden relative border-4 border-dashed border-sky-300">
                    <Scanner
                      onScan={(result) => {
                        if (result && result.length > 0) {
                          handleSimulateScan(result[0].rawValue);
                        }
                      }}
                      components={{
                        audio: false,
                        onOff: true,
                        finder: false,
                      }}
                    />
                  </div>
                  <p className="text-center text-sm text-slate-500 mt-6">
                    Position the member&apos;s QR code within the frame to scan automatically.
                  </p>
                  <button 
                    onClick={() => handleSimulateScan('VGK00214')}
                    className="mt-6 px-6 py-2 bg-slate-100 text-slate-600 font-bold rounded-lg text-sm hover:bg-slate-200 transition-colors"
                  >
                    (Dev) Simulate Scan
                  </button>
                </div>
              ) : (
                <form onSubmit={handleManualSubmit} className="flex flex-col">
                  <label className="text-sm font-bold text-slate-700 mb-2">Coupon / Member Code</label>
                  <input 
                    type="text" 
                    value={manualCode}
                    onChange={(e) => setManualCode(e.target.value.toUpperCase())}
                    placeholder="e.g. CPN-VGK-001"
                    className="w-full px-4 py-3 border border-slate-300 rounded-xl font-mono text-lg text-center tracking-widest focus:ring-2 focus:ring-sky-500 focus:border-transparent outline-none uppercase"
                  />
                  <button 
                    type="submit"
                    disabled={!manualCode || loading}
                    className="mt-6 w-full py-3 bg-sky-600 text-white font-bold rounded-xl shadow-md hover:bg-sky-700 disabled:opacity-50 transition-colors"
                  >
                    {loading ? <i className="fas fa-circle-notch fa-spin"></i> : "Verify Code"}
                  </button>
                </form>
              )}
            </div>
          </div>
        ) : (
          <div className="w-full max-w-lg bg-white rounded-2xl shadow-xl border border-slate-200 overflow-hidden animate-fade-in-up">
            <div className="bg-green-500 text-white p-6 text-center">
              <div className="w-16 h-16 bg-white rounded-full flex items-center justify-center text-3xl text-green-500 mx-auto mb-3 shadow-lg">
                <i className="fas fa-check"></i>
              </div>
              <h2 className="text-2xl font-bold">Valid VGK Member</h2>
              <p className="text-green-100 text-sm">Code verified successfully</p>
            </div>

            <div className="p-6">
              <div className="flex items-center gap-4 mb-6 p-4 bg-slate-50 rounded-xl border border-slate-100">
                <div className="w-12 h-12 bg-slate-200 rounded-full flex items-center justify-center font-bold text-slate-600 text-xl">
                  {scanResult.memberName.charAt(0)}
                </div>
                <div>
                  <h3 className="font-bold text-slate-900 text-lg">{scanResult.memberName}</h3>
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-xs font-bold text-slate-500">{scanResult.memberId}</span>
                    <span className="bg-slate-800 text-white text-[10px] font-bold px-2 py-0.5 rounded uppercase">{scanResult.tier}</span>
                  </div>
                </div>
              </div>

              <div className="border-t border-dashed border-slate-200 pt-6 mb-6">
                <h4 className="text-sm font-bold text-slate-500 uppercase tracking-wider mb-4">Applicable Discount</h4>
                
                <div className="flex justify-between items-center mb-2">
                  <span className="text-slate-600 font-medium">Coupon Code</span>
                  <span className="font-mono font-bold text-slate-900">{scanResult.couponCode}</span>
                </div>
                <div className="flex justify-between items-center mb-2">
                  <span className="text-slate-600 font-medium">Discount Value</span>
                  <span className="text-2xl font-black text-green-600">{scanResult.discountPercentage}% OFF</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-slate-600 font-medium">Maximum Cap</span>
                  <span className="font-bold text-slate-900">₹{scanResult.maxDiscount.toLocaleString()}</span>
                </div>
              </div>

              <div className="mb-6">
                <label className="text-sm font-bold text-slate-700 mb-2 block">Bill Amount (₹)</label>
                <input 
                  type="number" 
                  value={billAmount}
                  onChange={(e) => setBillAmount(e.target.value)}
                  placeholder="Enter total bill amount"
                  className="w-full px-4 py-3 border border-slate-300 rounded-xl font-bold text-lg focus:ring-2 focus:ring-sky-500 focus:border-transparent outline-none"
                />
              </div>

              <div className="flex gap-3">
                <button 
                  onClick={resetScan}
                  className="flex-1 py-3 bg-white border border-slate-300 text-slate-700 font-bold rounded-xl hover:bg-slate-50 transition-colors"
                >
                  Cancel
                </button>
                <button 
                  onClick={handleProcessTransaction}
                  className="flex-[2] py-3 bg-sky-600 text-white font-bold rounded-xl shadow-md hover:bg-sky-700 transition-colors"
                >
                  Process Transaction
                </button>
              </div>
            </div>
          </div>
        )}

      </div>
    </div>
  );
}
