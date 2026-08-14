"use client";

import React, { createContext, useContext, useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { getApiUrl } from "@/lib/api";

interface SuperAdminUser {
  id: number;
  username: string;
  role: string; // 'SUPER_ADMIN', 'FINANCE_DIRECTOR'
  permissions: string[];
}

interface SuperAdminAuthContextType {
  token: string | null;
  user: SuperAdminUser | null;
  login: (token: string, user: SuperAdminUser) => void;
  logout: () => void;
  isLoading: boolean;
}

const SuperAdminAuthContext = createContext<SuperAdminAuthContextType | undefined>(undefined);

export function SuperAdminAuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<SuperAdminUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    // Check localStorage for token on initial load
    const storedToken = localStorage.getItem("superadmin_token");
    const storedUserStr = localStorage.getItem("superadmin_user");
    
    if (storedToken && storedUserStr) {
      try {
        const storedUser = JSON.parse(storedUserStr);
        setToken(storedToken);
        setUser(storedUser);
      } catch (e) {
        console.error("Failed to parse stored superadmin user", e);
        localStorage.removeItem("superadmin_token");
        localStorage.removeItem("superadmin_user");
      }
    }
    
    setIsLoading(false);
  }, []);

  const login = (newToken: string, newUser: SuperAdminUser) => {
    setToken(newToken);
    setUser(newUser);
    localStorage.setItem("superadmin_token", newToken);
    localStorage.setItem("superadmin_user", JSON.stringify(newUser));
  };

  const logout = () => {
    setToken(null);
    setUser(null);
    localStorage.removeItem("superadmin_token");
    localStorage.removeItem("superadmin_user");
    router.push("/superadmin/login");
  };

  return (
    <SuperAdminAuthContext.Provider value={{ token, user, login, logout, isLoading }}>
      {children}
    </SuperAdminAuthContext.Provider>
  );
}

export function useSuperAdminAuth() {
  const context = useContext(SuperAdminAuthContext);
  if (context === undefined) {
    throw new Error("useSuperAdminAuth must be used within a SuperAdminAuthProvider");
  }
  return context;
}
