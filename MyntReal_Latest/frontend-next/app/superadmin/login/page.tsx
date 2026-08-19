"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { useSuperAdminAuth } from "@/contexts/SuperAdminAuthContext";
import api from "@/lib/api";

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
          
          // Verify user role explicitly for superadmin access
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
      
      {/* Background decoration */}
      <div className="absolute inset-0 bg-[url('https://www.transparenttextures.com/patterns/cubes.png')] opacity-5 mix-blend-overlay"></div>
      <div className="absolute top-[-20%] left-[-10%] w-[50%] h-[50%] rounded-full bg-red-600 opacity-10 blur-[120px]"></div>

      <div className="sm:mx-auto sm:w-full sm:max-w-md relative z-10">
        <div className="flex justify-center mb-6">
          <div className="w-20 h-20 bg-gradient-to-br from-red-600 to-rose-900 rounded-2xl flex items-center justify-center font-bold text-4xl shadow-[0_0_30px_rgba(225,29,72,0.4)] text-white border border-red-500/50">
            <i className="fas fa-shield-alt"></i>
          </div>
        </div>
        <h2 className="text-center text-3xl font-black text-white tracking-widest uppercase">
          System Core
        </h2>
        <p className="mt-2 text-center text-xs font-bold text-red-500 tracking-widest uppercase">
          Restricted Access Terminal
        </p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md relative z-10">
        <div className="bg-[#111827] py-8 px-4 shadow-2xl sm:rounded-2xl sm:px-10 border border-[#1F2937]">
          
          <div className="mb-6 p-4 bg-red-900/20 border-l-4 border-red-600 text-red-400 rounded-r text-xs font-bold uppercase tracking-wider flex items-center">
            <i className="fas fa-exclamation-triangle mr-3 text-lg"></i>
            <div>
              <p>Warning: Level 5 Access Required</p>
              <p className="text-[9px] text-red-500/70 mt-1">Unauthorized access attempts are logged and reported.</p>
            </div>
          </div>

          <form className="space-y-6" onSubmit={handleLogin}>
            
            {error && (
              <div className="bg-red-500/10 border border-red-500/30 p-3 rounded text-center">
                <p className="text-sm text-red-400 font-bold">{error}</p>
              </div>
            )}

            <div>
              <label className="block text-xs font-bold text-gray-400 uppercase tracking-wider mb-2">
                Admin Identifier
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <i className="fas fa-user-astronaut text-gray-500"></i>
                </div>
                <input
                  type="text"
                  required
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  className="appearance-none block w-full pl-10 pr-3 py-3 border border-gray-700 rounded bg-gray-900 text-white placeholder-gray-600 focus:outline-none focus:border-red-500 focus:ring-1 focus:ring-red-500 font-mono text-sm transition-colors"
                  placeholder="SYS_ADMIN_ID"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-bold text-gray-400 uppercase tracking-wider mb-2">
                Passcode
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <i className="fas fa-lock text-gray-500"></i>
                </div>
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="appearance-none block w-full pl-10 pr-3 py-3 border border-gray-700 rounded bg-gray-900 text-white placeholder-gray-600 focus:outline-none focus:border-red-500 focus:ring-1 focus:ring-red-500 font-mono tracking-[0.5em] text-sm transition-colors"
                  placeholder="••••••••"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-bold text-gray-400 uppercase tracking-wider mb-2 flex justify-between">
                <span>Hardware Security Key</span>
                <span className="text-[10px] text-red-500 animate-pulse">Required</span>
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <i className="fas fa-key text-gray-500"></i>
                </div>
                <input
                  type="password"
                  required
                  value={securityKey}
                  onChange={(e) => setSecurityKey(e.target.value)}
                  className="appearance-none block w-full pl-10 pr-3 py-3 border border-gray-700 rounded bg-gray-900 text-white placeholder-gray-600 focus:outline-none focus:border-red-500 focus:ring-1 focus:ring-red-500 font-mono text-sm transition-colors"
                  placeholder="Enter 2FA / Security Key"
                />
              </div>
            </div>

            <div className="pt-2">
              <button
                type="submit"
                disabled={loading}
                className="w-full flex justify-center py-4 px-4 border border-red-500/50 rounded shadow-[0_0_15px_rgba(225,29,72,0.2)] text-sm font-bold text-white bg-red-600 hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-gray-900 focus:ring-red-500 disabled:opacity-50 transition-all uppercase tracking-widest"
              >
                {loading ? (
                  <span className="flex items-center">
                    <i className="fas fa-circle-notch fa-spin mr-3"></i> Authenticating...
                  </span>
                ) : (
                  "Initiate Override"
                )}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
