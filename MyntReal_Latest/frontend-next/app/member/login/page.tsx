"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { useMemberAuth } from "@/contexts/MemberAuthContext";
import api from "@/lib/api";
import Link from "next/link";

export default function MemberLoginPage() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const { login } = useMemberAuth();
  const router = useRouter();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      if (username && password) {
        const response = await api.post("/auth/login", {
          user_id: username,
          password: password,
        });

        if (response.data && response.data.access_token) {
          const { access_token, user } = response.data;
          
          // Map backend fields to frontend context expectations
          const memberUser = {
            id: user.id,
            mnr_id: user.id, // backend returns id as the mnr_id
            name: user.name,
            email: user.email,
            wallet_balance: user.wallet_balance || 0,
            kyc_status: user.kyc_status,
            coupon_status: user.coupon_status,
            account_status: user.account_status || 'Active',
            is_active: user.account_status === 'Active'
          };

          login(access_token, memberUser);
          router.push("/member/dashboard");
        }
      } else {
        setError("Please enter your VGK ID and password.");
        setLoading(false);
      }
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || "Invalid credentials or network error.";
      setError(errorMessage);
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col justify-center py-12 sm:px-6 lg:px-8 relative overflow-hidden">
      
      {/* Background decoration */}
      <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] rounded-full bg-amber-400 opacity-20 blur-[100px]"></div>
      <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] rounded-full bg-yellow-600 opacity-20 blur-[100px]"></div>

      <div className="sm:mx-auto sm:w-full sm:max-w-md relative z-10">
        <div className="flex justify-center mb-6">
          <div className="w-16 h-16 bg-gradient-to-tr from-yellow-400 to-amber-600 rounded-2xl flex items-center justify-center font-bold text-4xl shadow-xl text-white">
            V
          </div>
        </div>
        <h2 className="text-center text-3xl font-extrabold text-gray-900 tracking-tight">
          VGK Network Portal
        </h2>
        <p className="mt-2 text-center text-sm text-gray-600">
          Sign in to access your member benefits and earnings
        </p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md relative z-10">
        <div className="bg-white py-8 px-4 shadow-xl sm:rounded-xl sm:px-10 border border-gray-100">
          <form className="space-y-6" onSubmit={handleLogin}>
            
            {error && (
              <div className="bg-red-50 border-l-4 border-red-500 p-4 rounded-md">
                <div className="flex">
                  <div className="flex-shrink-0">
                    <i className="fas fa-exclamation-circle text-red-500"></i>
                  </div>
                  <div className="ml-3">
                    <p className="text-sm text-red-700 font-medium">{error}</p>
                  </div>
                </div>
              </div>
            )}

            <div>
              <label className="block text-sm font-medium text-gray-700">
                VGK Member ID / Phone Number
              </label>
              <div className="mt-1 relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <i className="fas fa-user text-gray-400"></i>
                </div>
                <input
                  type="text"
                  required
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  className="appearance-none block w-full pl-10 pr-3 py-3 border border-gray-300 rounded-lg shadow-sm placeholder-gray-400 focus:outline-none focus:ring-amber-500 focus:border-amber-500 sm:text-sm bg-gray-50 focus:bg-white transition-colors"
                  placeholder="e.g. MNR182364369"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700">
                Password
              </label>
              <div className="mt-1 relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <i className="fas fa-lock text-gray-400"></i>
                </div>
                <input
                  type={showPassword ? "text" : "password"}
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="appearance-none block w-full pl-10 pr-10 py-3 border border-gray-300 rounded-lg shadow-sm placeholder-gray-400 focus:outline-none focus:ring-amber-500 focus:border-amber-500 sm:text-sm bg-gray-50 focus:bg-white transition-colors"
                  placeholder="••••••••"
                />
                <div className="absolute inset-y-0 right-0 pr-3 flex items-center">
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="text-gray-400 hover:text-gray-500 focus:outline-none focus:text-amber-500 transition-colors"
                  >
                    <i className={`fas ${showPassword ? 'fa-eye-slash' : 'fa-eye'}`}></i>
                  </button>
                </div>
              </div>
            </div>

            <div className="flex items-center justify-between">
              <div className="flex items-center">
                <input
                  id="remember-me"
                  name="remember-me"
                  type="checkbox"
                  className="h-4 w-4 text-amber-600 focus:ring-amber-500 border-gray-300 rounded cursor-pointer"
                />
                <label htmlFor="remember-me" className="ml-2 block text-sm text-gray-900 cursor-pointer">
                  Remember me
                </label>
              </div>

              <div className="text-sm">
                <a href="#" className="font-medium text-amber-600 hover:text-amber-500">
                  Forgot password?
                </a>
              </div>
            </div>

            <div>
              <button
                type="submit"
                disabled={loading}
                className="w-full flex justify-center py-3 px-4 border border-transparent rounded-lg shadow-md text-sm font-bold text-white bg-gradient-to-r from-yellow-500 to-amber-600 hover:from-yellow-600 hover:to-amber-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-amber-500 disabled:opacity-70 transition-all transform hover:-translate-y-0.5 active:translate-y-0"
              >
                {loading ? (
                  <span className="flex items-center">
                    <i className="fas fa-circle-notch fa-spin mr-2"></i> Authenticating...
                  </span>
                ) : (
                  "Secure Sign In"
                )}
              </button>
            </div>
          </form>

          <div className="mt-6">
            <div className="relative">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-gray-200" />
              </div>
              <div className="relative flex justify-center text-sm">
                <span className="px-2 bg-white text-gray-500">
                  Not a member yet?
                </span>
              </div>
            </div>

            <div className="mt-6">
              <Link
                href="/member/signup"
                className="w-full flex justify-center py-2.5 px-4 border-2 border-gray-200 rounded-lg shadow-sm text-sm font-bold text-gray-700 bg-white hover:bg-gray-50 hover:border-gray-300 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-amber-500 transition-colors"
              >
                Join the VGK Network
              </Link>
            </div>
          </div>
        </div>
        
        {/* Security Badges */}
        <div className="mt-8 flex justify-center space-x-6 opacity-60">
          <div className="flex items-center text-gray-500 text-xs font-medium">
            <i className="fas fa-shield-alt mr-1.5 text-lg"></i> 256-bit Secure
          </div>
          <div className="flex items-center text-gray-500 text-xs font-medium">
            <i className="fas fa-lock mr-1.5 text-lg"></i> Encrypted Login
          </div>
        </div>
      </div>
    </div>
  );
}
