"use client";

import React, { createContext, useContext, useState, useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";
import api from "@/lib/api";

interface MemberUser {
  id: string | number;
  mnr_id: string; // e.g. MNR182364369
  name: string;
  email: string;
  wallet_balance: number;
  kyc_status: string; // pending, verified, rejected
  coupon_status: string | null;
  account_status: string;
  is_active: boolean;
  [key: string]: any;
}

interface MemberAuthContextType {
  token: string | null;
  user: MemberUser | null;
  login: (token: string, user: MemberUser) => void;
  logout: () => void;
  isLoading: boolean;
  refreshUser: () => Promise<void>;
}

const MemberAuthContext = createContext<MemberAuthContextType | undefined>(undefined);

export function MemberAuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<MemberUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();
  const pathname = usePathname();

  const fetchUser = async (authToken: string) => {
    try {
      // Use the hybrid auth endpoint to prioritize MNR roles
      const response = await api.get('/auth/me-hybrid?role=mnr', {
        headers: { Authorization: `Bearer ${authToken}` }
      });
      if (response.data && response.data.success && response.data.data) {
        setUser(response.data.data as MemberUser);
        localStorage.setItem("member_user", JSON.stringify(response.data.data));
      }
    } catch (err) {
      console.error("Failed to fetch member user profile", err);
      // Let the interceptor handle 401s
    }
  };

  useEffect(() => {
    const initializeAuth = async () => {
      const storedToken = localStorage.getItem("member_token");
      const storedUserStr = localStorage.getItem("member_user");
      
      if (storedToken) {
        setToken(storedToken);
        if (storedUserStr) {
          try {
            setUser(JSON.parse(storedUserStr));
          } catch {
            console.error("Failed to parse stored member user");
          }
        }
        
        // Fetch fresh data in the background
        await fetchUser(storedToken);
      } else {
        // Redirect to login if trying to access a protected route
        if (pathname && !pathname.endsWith('/login') && pathname.startsWith('/member')) {
           router.push('/member/login');
        }
      }
      setIsLoading(false);
    };

    initializeAuth();
  }, [pathname, router]);

  const login = (newToken: string, newUser: MemberUser) => {
    setToken(newToken);
    setUser(newUser);
    localStorage.setItem("member_token", newToken);
    localStorage.setItem("member_user", JSON.stringify(newUser));
  };

  const logout = async () => {
    try {
      if (token) {
        await api.post('/logout', {}, {
           headers: { Authorization: `Bearer ${token}` }
        });
      }
    } catch {
      // ignore logout errors
    } finally {
      setToken(null);
      setUser(null);
      localStorage.removeItem("member_token");
      localStorage.removeItem("member_user");
      router.push("/member/login");
    }
  };

  const refreshUser = async () => {
    if (token) {
      await fetchUser(token);
    }
  };

  return (
    <MemberAuthContext.Provider value={{ token, user, login, logout, isLoading, refreshUser }}>
      {children}
    </MemberAuthContext.Provider>
  );
}

export function useMemberAuth() {
  const context = useContext(MemberAuthContext);
  if (context === undefined) {
    throw new Error("useMemberAuth must be used within a MemberAuthProvider");
  }
  return context;
}
