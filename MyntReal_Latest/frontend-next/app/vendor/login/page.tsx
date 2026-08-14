"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { useVendorAuth } from "@/contexts/VendorAuthContext";

export default function VendorLoginPage() {
  const [vendorId, setVendorId] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  
  const { login } = useVendorAuth();
  const router = useRouter();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      if (vendorId && password) {
        // Mock successful login
        const mockToken = "mock_vendor_jwt_token";
        const mockUser = {
          id: 501,
          vendor_id: "V-9942",
          business_name: "Super Electronics Ltd",
          owner_name: "Ramesh Kumar",
          category: "Electronics",
          email: "contact@superelectronics.com",
          phone: "+91 9876500000",
          is_active: true,
        };
        
        setTimeout(() => {
          login(mockToken, mockUser);
          router.push("/vendor/dashboard");
        }, 800);
      } else {
        setError("Please enter Vendor ID and password.");
        setLoading(false);
      }
    } catch (err) {
      setError("An unexpected error occurred.");
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-900 flex flex-col justify-center py-12 sm:px-6 lg:px-8 relative overflow-hidden">
      
      {/* Background decoration */}
      <div className="absolute top-[-20%] left-[-10%] w-[50%] h-[50%] rounded-full bg-sky-500 opacity-20 blur-[120px]"></div>
      <div className="absolute bottom-[-20%] right-[-10%] w-[50%] h-[50%] rounded-full bg-blue-600 opacity-20 blur-[120px]"></div>

      <div className="sm:mx-auto sm:w-full sm:max-w-md relative z-10">
        <div className="flex justify-center mb-6">
          <div className="w-16 h-16 bg-gradient-to-tr from-sky-400 to-blue-600 rounded-2xl flex items-center justify-center font-bold text-4xl shadow-xl text-white border border-white/20">
            <i className="fas fa-store"></i>
          </div>
        </div>
        <h2 className="text-center text-3xl font-extrabold text-white tracking-tight">
          Vendor Partner Login
        </h2>
        <p className="mt-2 text-center text-sm text-slate-400">
          Access the VGK Vendor network to scan coupons and track sales
        </p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md relative z-10">
        <div className="bg-white/10 backdrop-blur-xl py-8 px-4 shadow-2xl sm:rounded-2xl sm:px-10 border border-white/10">
          <form className="space-y-6" onSubmit={handleLogin}>
            
            {error && (
              <div className="bg-red-500/20 border border-red-500/50 p-4 rounded-lg">
                <div className="flex items-center">
                  <i className="fas fa-exclamation-circle text-red-400 mr-3 text-lg"></i>
                  <p className="text-sm text-red-200 font-medium">{error}</p>
                </div>
              </div>
            )}

            <div>
              <label className="block text-sm font-medium text-slate-300">
                Vendor ID (e.g., V-1234)
              </label>
              <div className="mt-1 relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <i className="fas fa-id-badge text-slate-400"></i>
                </div>
                <input
                  type="text"
                  required
                  value={vendorId}
                  onChange={(e) => setVendorId(e.target.value)}
                  className="appearance-none block w-full pl-10 pr-3 py-3 border border-slate-600 rounded-xl shadow-sm placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-sky-500 focus:border-transparent sm:text-sm bg-slate-800/50 text-white transition-colors"
                  placeholder="V-0000"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-300">
                Password
              </label>
              <div className="mt-1 relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <i className="fas fa-lock text-slate-400"></i>
                </div>
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="appearance-none block w-full pl-10 pr-3 py-3 border border-slate-600 rounded-xl shadow-sm placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-sky-500 focus:border-transparent sm:text-sm bg-slate-800/50 text-white transition-colors"
                  placeholder="••••••••"
                />
              </div>
            </div>

            <div className="flex items-center justify-between">
              <div className="flex items-center">
                <input
                  id="remember-me"
                  type="checkbox"
                  className="h-4 w-4 text-sky-500 focus:ring-sky-500 border-slate-600 rounded bg-slate-800 cursor-pointer"
                />
                <label htmlFor="remember-me" className="ml-2 block text-sm text-slate-300 cursor-pointer">
                  Remember device
                </label>
              </div>
              <div className="text-sm">
                <a href="#" className="font-medium text-sky-400 hover:text-sky-300">
                  Forgot password?
                </a>
              </div>
            </div>

            <div>
              <button
                type="submit"
                disabled={loading}
                className="w-full flex justify-center py-3.5 px-4 border border-transparent rounded-xl shadow-lg text-sm font-bold text-white bg-gradient-to-r from-sky-500 to-blue-600 hover:from-sky-400 hover:to-blue-500 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-slate-900 focus:ring-sky-500 disabled:opacity-70 transition-all transform hover:-translate-y-0.5 active:translate-y-0"
              >
                {loading ? (
                  <span className="flex items-center">
                    <i className="fas fa-circle-notch fa-spin mr-2"></i> Verifying...
                  </span>
                ) : (
                  "Secure Vendor Login"
                )}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
