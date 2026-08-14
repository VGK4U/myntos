"use client";

import React, { createContext, useContext, useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { getApiUrl } from "@/lib/api";

interface VendorUser {
  id: number;
  vendor_id: string; // e.g. V-0012
  business_name: string;
  owner_name: string;
  category: string;
  email: string;
  phone: string;
  is_active: boolean;
}

interface VendorAuthContextType {
  token: string | null;
  user: VendorUser | null;
  login: (token: string, user: VendorUser) => void;
  logout: () => void;
  isLoading: boolean;
}

const VendorAuthContext = createContext<VendorAuthContextType | undefined>(undefined);

export function VendorAuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<VendorUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    // Check localStorage for token on initial load
    const storedToken = localStorage.getItem("vendor_token");
    const storedUserStr = localStorage.getItem("vendor_user");
    
    if (storedToken && storedUserStr) {
      try {
        const storedUser = JSON.parse(storedUserStr);
        setToken(storedToken);
        setUser(storedUser);
      } catch (e) {
        console.error("Failed to parse stored vendor user", e);
        localStorage.removeItem("vendor_token");
        localStorage.removeItem("vendor_user");
      }
    }
    
    setIsLoading(false);
  }, []);

  const login = (newToken: string, newUser: VendorUser) => {
    setToken(newToken);
    setUser(newUser);
    localStorage.setItem("vendor_token", newToken);
    localStorage.setItem("vendor_user", JSON.stringify(newUser));
  };

  const logout = () => {
    setToken(null);
    setUser(null);
    localStorage.removeItem("vendor_token");
    localStorage.removeItem("vendor_user");
    router.push("/vendor/login");
  };

  return (
    <VendorAuthContext.Provider value={{ token, user, login, logout, isLoading }}>
      {children}
    </VendorAuthContext.Provider>
  );
}

export function useVendorAuth() {
  const context = useContext(VendorAuthContext);
  if (context === undefined) {
    throw new Error("useVendorAuth must be used within a VendorAuthProvider");
  }
  return context;
}
