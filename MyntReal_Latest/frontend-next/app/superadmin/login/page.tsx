"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { useSuperAdminAuth } from "@/contexts/SuperAdminAuthContext";
import api from "@/lib/api";
import { Shield, User, Lock, Key, AlertTriangle, Loader2 } from "lucide-react";

export default function SuperAdminLoginPage() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [securityKey, setSecurityKey] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  
  const { login } = useSuperAdminAuth();
  const router = useRouter();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      if (username && password && securityKey) {
        const res = await api.post("/staff/auth/login", {
          employee_id: username,
          password: password,
          totp_code: securityKey
        });

        if (res.data && res.data.success) {
          const accessToken = res.data.access_token;
          
          const profileRes = await api.get("/staff/auth/me", {
            headers: { Authorization: `Bearer ${accessToken}` }
          });
          
          if (profileRes.data.success) {
            const roleName = profileRes.data.employee?.role_name?.toLowerCase() || '';
            const isAdmin = roleName.includes('admin') || roleName.includes('leadership') || roleName.includes('director');
            
            if (isAdmin) {
              const adminUser = {
                id: profileRes.data.employee.id,
                username: profileRes.data.employee.emp_code,
                role: profileRes.data.employee.role_name,
                permissions: ["all"],
              };
              login(accessToken, adminUser);
              router.push("/superadmin/dashboard");
            } else {
              setError("Access Denied: Insufficient Clearance Level.");
            }
          } else {
             setError("Failed to fetch profile details.");
          }
        } else {
          setError(res.data.message || "Invalid credentials.");
        }
      } else {
        setError("All fields including Hardware Security Key are required.");
      }
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || err.response?.data?.message || "Authorization failed. Access Denied.";
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#0B0F19] flex flex-col justify-center py-12 sm:px-6 lg:px-8 relative overflow-hidden">
      <div className="absolute inset-0 opacity-5 mix-blend-overlay" style={{ backgroundImage: "radial-gradient(#e11d48 1px, transparent 1px)", backgroundSize: "32px 32px" }}></div>
      <div className="absolute top-[-20%] left-[-10%] w-[50%] h-[50%] rounded-full bg-rose-600 opacity-10 blur-[120px]"></div>

      <div className="sm:mx-auto sm:w-full sm:max-w-md relative z-10 flex flex-col items-center">
        <div className="w-20 h-20 bg-gradient-to-br from-rose-600 to-rose-900 rounded-2xl flex items-center justify-center shadow-[0_0_40px_rgba(225,29,72,0.3)] text-white border border-rose-500/50 mb-6">
          <Shield className="h-10 w-10" />
        </div>
        <h2 className="text-center text-3xl font-extrabold text-white tracking-tight">
          System Core
        </h2>
        <p className="mt-2 text-center text-sm font-semibold text-rose-500 tracking-widest uppercase">
          Restricted Access Terminal
        </p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md relative z-10">
        <div className="bg-[#111827]/80 backdrop-blur-xl py-8 px-4 shadow-2xl sm:rounded-2xl sm:px-10 border border-slate-800">
          
          <div className="mb-8 p-4 bg-rose-500/10 border-l-4 border-rose-600 text-rose-200 rounded-r-md flex items-start">
            <AlertTriangle className="h-5 w-5 text-rose-500 mr-3 shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-semibold tracking-wide">Level 5 Access Required</p>
              <p className="text-xs text-rose-400 mt-1">Unauthorized access attempts are logged and reported.</p>
            </div>
          </div>

          <form className="space-y-6" onSubmit={handleLogin}>
            {error && (
              <div className="p-3 bg-rose-500/10 border border-rose-500/30 rounded-md">
                <p className="text-sm text-rose-400 font-medium text-center">{error}</p>
              </div>
            )}

            <div className="space-y-2">
              <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider block">Admin Identifier</label>
              <div className="relative">
                <User className="absolute left-3 top-3 h-5 w-5 text-slate-500" />
                <input
                  type="text"
                  required
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-700 rounded-md py-2.5 pl-10 pr-3 text-white placeholder-slate-600 focus:outline-none focus:ring-1 focus:ring-rose-500 focus:border-rose-500 transition-colors font-mono sm:text-sm"
                  placeholder="SYS_ADMIN_ID"
                />
              </div>
            </div>

            <div className="space-y-2">
              <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider block">Passcode</label>
              <div className="relative">
                <Lock className="absolute left-3 top-3 h-5 w-5 text-slate-500" />
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-700 rounded-md py-2.5 pl-10 pr-3 text-white placeholder-slate-600 focus:outline-none focus:ring-1 focus:ring-rose-500 focus:border-rose-500 transition-colors font-mono tracking-widest sm:text-sm"
                  placeholder="••••••••"
                />
              </div>
            </div>

            <div className="space-y-2">
              <div className="flex justify-between items-center">
                <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider block">Hardware Security Key</label>
                <span className="text-[10px] font-bold text-rose-500 animate-pulse uppercase">Required</span>
              </div>
              <div className="relative">
                <Key className="absolute left-3 top-3 h-5 w-5 text-slate-500" />
                <input
                  type="password"
                  required
                  value={securityKey}
                  onChange={(e) => setSecurityKey(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-700 rounded-md py-2.5 pl-10 pr-3 text-white placeholder-slate-600 focus:outline-none focus:ring-1 focus:ring-rose-500 focus:border-rose-500 transition-colors font-mono sm:text-sm"
                  placeholder="Enter 2FA / Security Key"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full flex items-center justify-center py-3 px-4 border border-rose-500/50 rounded-md shadow-[0_0_20px_rgba(225,29,72,0.25)] text-sm font-bold text-white bg-rose-600 hover:bg-rose-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-[#111827] focus:ring-rose-500 disabled:opacity-50 transition-all uppercase tracking-widest mt-8"
            >
              {loading ? (
                <>
                  <Loader2 className="animate-spin mr-2 h-5 w-5" />
                  Authenticating...
                </>
              ) : (
                "Initiate Override"
              )}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
