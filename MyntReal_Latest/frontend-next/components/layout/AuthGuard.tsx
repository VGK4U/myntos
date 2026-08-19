"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useStaffAuth } from "@/contexts/StaffAuthContext";

export default function AuthGuard({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useStaffAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push("/login");
    }
  }, [isLoading, isAuthenticated, router]);

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="flex flex-col items-center">
          <i className="fas fa-circle-notch fa-spin text-4xl text-gray-400 mb-4"></i>
          <p className="text-gray-500 font-medium">Verifying session...</p>
        </div>
      </div>
    );
  }

  // If not authenticated, we return null to prevent flashing the protected content
  // before the useEffect redirect kicks in
  if (!isAuthenticated) {
    return null;
  }

  return <>{children}</>;
}
