"use client";

import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import api from '@/lib/api';

// Defined based on backend StaffProfileResponse
export interface Employee {
  id: number;
  emp_code: string;
  full_name: string;
  email: string | null;
  role_id: number;
  role_name: string;
  department_name: string | null;
  is_active: boolean;
  requires_password_change?: boolean;
}

interface AuthContextType {
  isAuthenticated: boolean;
  isLoading: boolean;
  token: string | null;
  user: Employee | null;
  logout: () => void;
  login: (token: string, userData: Employee) => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function StaffAuthProvider({ children }: { children: ReactNode }) {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<Employee | null>(null);
  
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    let isMounted = true;
    
    const initializeAuth = async () => {
      // 1. Extract token from localStorage or cookies
      let storedToken = localStorage.getItem('staff_token');
      
      if (!storedToken || storedToken === 'null' || storedToken === 'undefined') {
        const cookieMatch = document.cookie
          .split(';')
          .map(c => c.trim())
          .find(c => c.startsWith('staff_token='));
          
        if (cookieMatch) {
          storedToken = cookieMatch.split('=')[1];
          if (storedToken) {
            try { storedToken = decodeURIComponent(storedToken); } catch(e) {}
          }
        }
      }

      // 2. Validate token structure
      if (storedToken) {
        let cleanToken = storedToken.trim();
        while (cleanToken.toLowerCase().startsWith('bearer ')) {
          cleanToken = cleanToken.slice(7).trim();
        }
        cleanToken = cleanToken.replace(/^["']|["']$/g, '').trim();

        if (cleanToken.split('.').length === 3) {
          // Token is structurally valid, try to fetch user profile
          if (isMounted) {
            setToken(cleanToken);
            // Ensure local storage is synced so axios interceptor can use it immediately
            if (localStorage.getItem('staff_token') !== cleanToken) {
              localStorage.setItem('staff_token', cleanToken);
            }
          }
          
          try {
            const response = await api.get('/staff/auth/me');
            if (response.data.success && isMounted) {
              setUser(response.data.employee);
              setIsAuthenticated(true);
            }
          } catch (error) {
            console.error('Failed to validate session:', error);
            // On 401, axios interceptor handles removal, but we clear state here
            if (isMounted) {
              setToken(null);
              setUser(null);
              setIsAuthenticated(false);
            }
          }
        } else {
          // Corrupted token
          localStorage.removeItem('staff_token');
          if (isMounted) {
            setToken(null);
            setUser(null);
            setIsAuthenticated(false);
          }
        }
      } else {
        if (isMounted) {
          setIsAuthenticated(false);
        }
      }
      
      if (isMounted) {
        setIsLoading(false);
      }
    };

    initializeAuth();
    
    return () => {
      isMounted = false;
    };
  }, [pathname]);

  const login = (newToken: string, userData: Employee) => {
    localStorage.setItem('staff_token', newToken);
    setToken(newToken);
    setUser(userData);
    setIsAuthenticated(true);
    router.push('/staff/dashboard');
  };

  const logout = () => {
    localStorage.removeItem('staff_token');
    document.cookie = 'staff_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
    setToken(null);
    setUser(null);
    setIsAuthenticated(false);
    router.push('/login');
  };

  return (
    <AuthContext.Provider value={{ isAuthenticated, isLoading, token, user, logout, login }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useStaffAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useStaffAuth must be used within a StaffAuthProvider');
  }
  return context;
}
