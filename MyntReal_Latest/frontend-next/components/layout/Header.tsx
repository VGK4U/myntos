"use client";

import { useStaffAuth } from "@/contexts/StaffAuthContext";

export default function Header() {
  const { logout, user } = useStaffAuth();
  
  // Use real user info from context, fallback if loading
  let userName = "Staff Member";
  let userEmail = "staff@vgk4u.com";
  let userInitial = "S";
  
  if (user) {
    userName = user.full_name || user.emp_code || "Staff Member";
    userEmail = user.email || user.role_name || "staff@vgk4u.com";
    userInitial = userName.charAt(0).toUpperCase();
  }

  return (
    <header className="fixed top-0 right-0 left-0 h-22 bg-white/90 backdrop-blur-md z-30 border-b border-gray-200 shadow-sm flex items-center justify-between px-6 pl-[280px]">
      <div className="flex items-center gap-4">
        <h1 className="text-xl font-bold text-gray-900">Staff Portal</h1>
      </div>
      
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-4 border-r border-gray-200 pr-4">
          <div className="text-right">
            <p className="text-sm font-bold text-gray-900">{userName}</p>
            <p className="text-xs text-gray-500">{userEmail}</p>
          </div>
          <div className="w-10 h-10 rounded-full bg-brand-warning/20 flex items-center justify-center text-brand-warning border border-brand-warning/30 font-bold">
            {userInitial}
          </div>
        </div>
        
        <button 
          onClick={logout}
          className="text-gray-500 hover:text-rose-600 transition-colors p-2 rounded-lg hover:bg-rose-50"
          title="Sign Out"
        >
          <i className="fas fa-sign-out-alt text-lg"></i>
        </button>
      </div>
    </header>
  );
}
