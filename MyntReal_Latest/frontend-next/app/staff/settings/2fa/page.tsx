"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useStaffAuth } from "@/contexts/StaffAuthContext";
import api from "@/lib/api";

export default function Staff2FASettingsPage() {
  const { user, isLoading } = useStaffAuth();
  
  const [loading, setLoading] = useState(false);
  const [alertInfo, setAlertInfo] = useState<{ message: string; type: 'success' | 'error' | 'warning' } | null>(null);

  // Setup state
  const [is2faEnabled, setIs2faEnabled] = useState(false);
  const [setupStep, setSetupStep] = useState<"disabled" | "setup" | "enabled">("disabled");
  const [secretKey, setSecretKey] = useState("");
  const [provisioningUri, setProvisioningUri] = useState("");
  const [verificationCode, setVerificationCode] = useState("");
  const [passwordForDisable, setPasswordForDisable] = useState("");
  
  const [backupCodes, setBackupCodes] = useState<string[]>([]);
  
  useEffect(() => {
    if (user && !isLoading) {
      const enabled = user.is_2fa_enabled || user.totp_enabled || false;
      setIs2faEnabled(enabled);
      setSetupStep(enabled ? "enabled" : "disabled");
    }
  }, [user, isLoading]);

  const showAlert = (message: string, type: 'success' | 'error' | 'warning') => {
    setAlertInfo({ message, type });
    setTimeout(() => setAlertInfo(null), 5000);
  };

  const handleEnableSetup = async () => {
    setLoading(true);
    setAlertInfo(null);
    try {
      const res = await api.post('/staff/auth/setup-2fa');
      if (res.data.success) {
        setSecretKey(res.data.secret);
        setProvisioningUri(res.data.provisioning_uri);
        setSetupStep("setup");
      }
    } catch (err: any) {
      console.error(err);
      showAlert(err.response?.data?.detail || "Failed to setup 2FA", "error");
    } finally {
      setLoading(false);
    }
  };

  const handleVerify2FA = async () => {
    if (verificationCode.length !== 6 || !/^\d+$/.test(verificationCode)) {
      showAlert('Please enter a valid 6-digit code', 'error');
      return;
    }

    setLoading(true);
    setAlertInfo(null);
    try {
      const res = await api.post('/staff/auth/verify-2fa', { totp_code: verificationCode });
      if (res.data.success) {
        setIs2faEnabled(true);
        setSetupStep("enabled");
        showAlert('Two-factor authentication has been enabled!', 'success');
      }
    } catch (err: any) {
      console.error(err);
      showAlert(err.response?.data?.detail || "Invalid verification code", "error");
    } finally {
      setLoading(false);
    }
  };

  const handleDisable2FA = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!passwordForDisable) {
      showAlert('Password is required to disable 2FA', 'error');
      return;
    }
    
    if (!confirm('Are you sure you want to disable two-factor authentication? This will make your account less secure.')) {
      return;
    }

    setLoading(true);
    setAlertInfo(null);
    try {
      const res = await api.post('/staff/auth/disable-2fa', { password: passwordForDisable });
      if (res.data.success) {
        setIs2faEnabled(false);
        setSetupStep("disabled");
        setPasswordForDisable("");
        showAlert('Two-factor authentication has been disabled.', 'warning');
      }
    } catch (err: any) {
      console.error(err);
      showAlert(err.response?.data?.detail || "Failed to disable 2FA", "error");
    } finally {
      setLoading(false);
    }
  };

  const generateBackupCodes = () => {
    const codes = [];
    for (let i = 0; i < 8; i++) {
      codes.push(
        Math.random().toString(36).substring(2, 6).toUpperCase() + '-' +
        Math.random().toString(36).substring(2, 6).toUpperCase()
      );
    }
    setBackupCodes(codes);
  };

  const copyBackupCodes = () => {
    navigator.clipboard.writeText(backupCodes.join('\n'));
    showAlert('Backup codes copied to clipboard!', 'success');
  };

  if (isLoading) {
    return <div className="p-6">Loading settings...</div>;
  }

  return (
    <div className="p-6 max-w-7xl mx-auto flex flex-col md:flex-row gap-8">
      {/* Settings Sidebar Nav */}
      <div className="w-full md:w-64 shrink-0 space-y-2">
        <h2 className="text-sm font-bold text-gray-500 uppercase tracking-wider mb-4 px-3">Settings Menu</h2>
        
        <Link href="/staff/settings/profile" className="w-full text-left px-4 py-3 rounded-lg font-medium transition-colors flex items-center text-gray-600 hover:bg-gray-100">
          <i className="fas fa-user-circle text-lg w-6 text-gray-400 mr-2"></i>
          Profile & Preferences
        </Link>
        
        <Link href="/staff/settings/security" className="w-full text-left px-4 py-3 rounded-lg font-medium transition-colors flex items-center text-gray-600 hover:bg-gray-100">
          <i className="fas fa-lock text-lg w-6 text-gray-400 mr-2"></i>
          Security
        </Link>
        
        <Link href="/staff/settings/2fa" className="w-full text-left px-4 py-3 rounded-lg font-medium transition-colors flex items-center bg-indigo-50 text-indigo-700">
          <i className="fas fa-shield-alt text-lg w-6 text-indigo-600 mr-2"></i>
          Two-Factor Auth
        </Link>
        
        <Link href="/staff/settings/audit-logs" className="w-full text-left px-4 py-3 rounded-lg font-medium transition-colors flex items-center text-gray-600 hover:bg-gray-100">
          <i className="fas fa-history text-lg w-6 text-gray-400 mr-2"></i>
          Audit & Activity Logs
        </Link>
      </div>

      {/* Main Content */}
      <div className="flex-1 space-y-6 max-w-3xl">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 tracking-tight">Two-Factor Authentication (2FA)</h1>
          <p className="text-sm text-gray-500 mt-2">Add an extra layer of security to your account.</p>
        </div>

        {alertInfo && (
          <div className={`p-4 rounded-lg flex items-start border ${
            alertInfo.type === 'success' ? 'bg-green-50 border-green-200 text-green-700' :
            alertInfo.type === 'error' ? 'bg-red-50 border-red-200 text-red-700' :
            'bg-yellow-50 border-yellow-200 text-yellow-700'
          }`}>
            <i className={`fas mt-0.5 mr-2 ${
              alertInfo.type === 'success' ? 'fa-check-circle' :
              alertInfo.type === 'error' ? 'fa-exclamation-circle' : 'fa-exclamation-triangle'
            }`}></i>
            {alertInfo.message}
          </div>
        )}

        <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
          <div className="p-6 border-b border-gray-100 flex justify-between items-center bg-gray-50/50">
            <div>
              <h2 className="text-lg font-bold text-gray-900">2FA Status</h2>
            </div>
            <div>
              <span className={`inline-block px-3 py-1 text-xs font-bold rounded-full border ${is2faEnabled ? 'bg-green-50 text-green-700 border-green-200' : 'bg-red-50 text-red-700 border-red-200'}`}>
                {is2faEnabled ? 'ENABLED' : 'DISABLED'}
              </span>
            </div>
          </div>
          
          <div className="p-6">
            <p className="text-gray-600 text-sm mb-6">Two-factor authentication adds an extra layer of security to your account by requiring a verification code in addition to your password.</p>

            {setupStep === "disabled" && (
              <div className="bg-gray-50 rounded-xl p-8 text-center border border-gray-200">
                <i className="fas fa-qrcode text-6xl text-gray-300 mb-4"></i>
                <p className="text-gray-500 mb-6 font-medium">Enable 2FA to configure your authenticator app</p>
                <button 
                  onClick={handleEnableSetup} 
                  disabled={loading}
                  className="px-6 py-2.5 bg-indigo-600 text-white font-medium rounded-lg shadow-sm hover:bg-indigo-700 transition-colors disabled:opacity-70 flex items-center justify-center mx-auto"
                >
                  <i className="fas fa-shield-alt mr-2"></i> Enable Two-Factor Authentication
                </button>
              </div>
            )}

            {setupStep === "setup" && (
              <div className="space-y-6">
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                  <h4 className="font-bold text-blue-800 text-sm mb-2 flex items-center"><i className="fas fa-info-circle mr-2"></i>Setup Instructions</h4>
                  <ol className="text-sm text-blue-900 list-decimal pl-5 space-y-1">
                    <li>Download an authenticator app (Google Authenticator, Authy, etc.)</li>
                    <li>Scan the QR code below or enter the secret key manually</li>
                    <li>Enter the 6-digit code from your app to verify</li>
                  </ol>
                </div>

                <div className="bg-gray-50 p-6 rounded-xl border border-gray-200 flex flex-col items-center justify-center">
                  {provisioningUri ? (
                    <div className="bg-white p-3 rounded-lg border border-gray-200 mb-4 shadow-sm">
                       <img src={`https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=${encodeURIComponent(provisioningUri)}`} alt="QR Code" className="w-48 h-48" />
                    </div>
                  ) : (
                    <div className="w-48 h-48 bg-gray-200 rounded flex items-center justify-center mb-4">Loading QR...</div>
                  )}
                  <p className="text-sm text-gray-600 mb-1 font-medium">Secret Key:</p>
                  <code className="bg-white px-4 py-2 rounded border border-gray-200 font-mono font-bold text-gray-800 tracking-wider">
                    {secretKey}
                  </code>
                </div>

                <div className="max-w-xs mx-auto">
                  <label className="block text-sm font-medium text-gray-700 mb-1 text-center">Enter 6-digit Verification Code</label>
                  <input 
                    type="text" 
                    maxLength={6}
                    value={verificationCode}
                    onChange={(e) => setVerificationCode(e.target.value)}
                    placeholder="000000" 
                    className="w-full border border-gray-300 rounded-lg p-3 text-center text-xl tracking-widest font-mono focus:ring-2 focus:ring-indigo-500 outline-none mb-4" 
                  />
                  <button 
                    onClick={handleVerify2FA}
                    disabled={loading || verificationCode.length !== 6}
                    className="w-full py-2.5 bg-indigo-600 text-white font-medium rounded-lg shadow-sm hover:bg-indigo-700 transition-colors disabled:opacity-70 flex items-center justify-center"
                  >
                    {loading ? "Verifying..." : <><i className="fas fa-check mr-2"></i> Verify and Enable</>}
                  </button>
                </div>
              </div>
            )}

            {setupStep === "enabled" && (
              <div className="space-y-6">
                <div className="bg-green-50 border border-green-200 rounded-lg p-4 flex items-start">
                  <i className="fas fa-check-circle text-green-600 mt-0.5 mr-3 text-lg"></i>
                  <div>
                    <h4 className="font-bold text-green-800 text-sm">Two-factor authentication is enabled</h4>
                    <p className="text-sm text-green-700 mt-1">Your account is secured with 2FA. You will need to enter a code from your authenticator app when you log in.</p>
                  </div>
                </div>

                <form onSubmit={handleDisable2FA} className="bg-red-50 border border-red-100 p-5 rounded-xl mt-6">
                  <h4 className="font-bold text-red-800 text-sm mb-3 flex items-center"><i className="fas fa-exclamation-triangle mr-2"></i>Disable 2FA</h4>
                  <p className="text-sm text-red-700 mb-4">Disabling two-factor authentication will make your account less secure. Please enter your password to confirm.</p>
                  
                  <div className="flex gap-3">
                    <input 
                      type="password" 
                      required
                      value={passwordForDisable}
                      onChange={(e) => setPasswordForDisable(e.target.value)}
                      placeholder="Enter your password" 
                      className="flex-1 border border-red-200 rounded-lg p-2.5 text-sm focus:ring-2 focus:ring-red-500 outline-none" 
                    />
                    <button 
                      type="submit"
                      disabled={loading || !passwordForDisable}
                      className="px-4 py-2.5 bg-red-600 text-white font-medium rounded-lg shadow-sm hover:bg-red-700 transition-colors disabled:opacity-70 whitespace-nowrap"
                    >
                      <i className="fas fa-times mr-2"></i> Disable 2FA
                    </button>
                  </div>
                </form>
              </div>
            )}
          </div>
        </div>

        {/* Backup Codes Section */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden mt-6 opacity-80 hover:opacity-100 transition-opacity">
          <div className="p-6 border-b border-gray-100 bg-gray-50/50">
            <h2 className="text-lg font-bold text-gray-900 flex items-center"><i className="fas fa-key mr-2 text-gray-400"></i>Backup Codes</h2>
          </div>
          <div className="p-6">
            <p className="text-gray-600 text-sm mb-4">Backup codes can be used to access your account if you lose access to your authenticator app or device.</p>
            
            <button 
              onClick={generateBackupCodes} 
              disabled={!is2faEnabled}
              className="px-4 py-2 border border-gray-300 text-gray-700 font-medium rounded-lg hover:bg-gray-50 transition-colors text-sm disabled:opacity-50 disabled:cursor-not-allowed flex items-center"
            >
              <i className="fas fa-download mr-2"></i> Generate Backup Codes
            </button>
            
            {backupCodes.length > 0 && (
              <div className="mt-6 border border-gray-200 rounded-xl overflow-hidden">
                <div className="bg-yellow-50 border-b border-yellow-200 p-4 flex items-start">
                  <i className="fas fa-exclamation-triangle text-yellow-600 mt-0.5 mr-3"></i>
                  <div>
                    <h4 className="font-bold text-yellow-800 text-sm">Save these codes in a secure location!</h4>
                    <p className="text-sm text-yellow-700 mt-1">Each code can only be used once. If you lose them, you might be locked out of your account.</p>
                  </div>
                </div>
                
                <div className="p-6 bg-gray-50">
                  <div className="grid grid-cols-2 gap-4 mb-4">
                    {backupCodes.map((code, idx) => (
                      <div key={idx} className="bg-white border border-gray-200 p-2 rounded text-center font-mono font-bold tracking-wider text-gray-800">
                        {code}
                      </div>
                    ))}
                  </div>
                  <button 
                    onClick={copyBackupCodes}
                    className="w-full py-2 bg-white border border-gray-300 text-gray-700 font-medium rounded-lg hover:bg-gray-50 transition-colors text-sm flex items-center justify-center"
                  >
                    <i className="fas fa-copy mr-2"></i> Copy All Codes
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
