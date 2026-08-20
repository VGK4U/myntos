"use client";

import React, { createContext, useContext, useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import api from "@/lib/api";

interface SuperAdminUser {
  id: number;
  username: string;
  role: string;
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
    const initializeAuth = async () => {
      const storedToken = localStorage.getItem("superadmin_token");
      const storedUserStr = localStorage.getItem("superadmin_user");
      
      if (storedToken && storedUserStr) {
        setToken(storedToken);
        try {
          setUser(JSON.parse(storedUserStr));
        } catch {
          console.error("Failed to parse superadmin user");
        }
        
        // Optionally fetch fresh admin details
        try {
          const res = await api.get("/staff/auth/me", {
            headers: { Authorization: `Bearer ${storedToken}` }
          });
          if (res.data.success) {
            const adminUser = {
              id: res.data.employee.id,
              username: res.data.employee.emp_code,
              role: res.data.employee.role_name,
              permissions: ['all'] // This could be populated from backend
            };
            setUser(adminUser);
            localStorage.setItem("superadmin_user", JSON.stringify(adminUser));
          }
        } catch (err) {
          console.error("SuperAdmin session invalid", err);
          // Don't auto-logout here, let interceptor handle if 401
        }
      }
      setIsLoading(false);
    };

    initializeAuth();
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
