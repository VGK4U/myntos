"use client";

import React, { createContext, useContext, useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { getApiUrl } from "@/lib/api";

interface MemberUser {
  id: number;
  vgk_id: string; // e.g. VGK00123
  first_name: string;
  last_name: string;
  email: string;
  phone: string;
  tier: string; // BRONZE, SILVER, GOLD, PLATINUM
  is_active: boolean;
  kyc_status: string; // PENDING, VERIFIED, REJECTED
}

interface MemberAuthContextType {
  token: string | null;
  user: MemberUser | null;
  login: (token: string, user: MemberUser) => void;
  logout: () => void;
  isLoading: boolean;
}

const MemberAuthContext = createContext<MemberAuthContextType | undefined>(undefined);

export function MemberAuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<MemberUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    // Check localStorage for token on initial load
    const storedToken = localStorage.getItem("member_token");
    const storedUserStr = localStorage.getItem("member_user");
    
    if (storedToken && storedUserStr) {
      try {
        const storedUser = JSON.parse(storedUserStr);
        setToken(storedToken);
        setUser(storedUser);
      } catch (e) {
        console.error("Failed to parse stored member user", e);
        localStorage.removeItem("member_token");
        localStorage.removeItem("member_user");
      }
    }
    
    setIsLoading(false);
  }, []);

  const login = (newToken: string, newUser: MemberUser) => {
    setToken(newToken);
    setUser(newUser);
    localStorage.setItem("member_token", newToken);
    localStorage.setItem("member_user", JSON.stringify(newUser));
  };

  const logout = () => {
    setToken(null);
    setUser(null);
    localStorage.removeItem("member_token");
    localStorage.removeItem("member_user");
    router.push("/member/login");
  };

  return (
    <MemberAuthContext.Provider value={{ token, user, login, logout, isLoading }}>
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
