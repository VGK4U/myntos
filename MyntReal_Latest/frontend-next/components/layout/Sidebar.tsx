"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { MENU_MASTER, SidebarSection, SidebarSubSection, SidebarItem } from "@/lib/navigation";
import { useStaffAuth } from "@/contexts/StaffAuthContext";

export default function Sidebar() {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [openSections, setOpenSections] = useState<string[]>([]);
  const pathname = usePathname();
  const { user } = useStaffAuth();

  // Find and open the active section on mount and pathname change
  useEffect(() => {
    let activeSubsectionCode = "";
    MENU_MASTER.forEach((section) => {
      section.subSections?.forEach((sub) => {
        if (sub.items.some((item) => item.route === pathname)) {
          activeSubsectionCode = sub.sub_section_code;
        }
      });
    });

    if (activeSubsectionCode) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setOpenSections((prev) => {
        if (!prev.includes(activeSubsectionCode)) {
          return [...prev, activeSubsectionCode];
        }
        return prev;
      });
    }
  }, [pathname]);

  const toggleSection = (code: string) => {
    setOpenSections((prev) =>
      prev.includes(code) ? prev.filter((c) => c !== code) : [...prev, code]
    );
  };

  const renderItem = (item: SidebarItem) => {
    const isActive = pathname === item.route;
    
    return (
      <Link
        key={item.menu_code}
        href={item.route}
        className={`flex items-center gap-3 px-3 py-2 rounded-lg transition-all duration-200 text-sm ${
          isActive
            ? "bg-brand-warning/10 text-brand-warning font-semibold border-l-2 border-brand-warning"
            : "text-gray-600 hover:text-brand-warning hover:bg-gray-50 border-l-2 border-transparent"
        }`}
        title={isCollapsed ? item.label : undefined}
      >
        <div className="w-5 flex items-center justify-center flex-shrink-0">
          {item.icon ? (
            <i className={`${item.icon} ${isActive ? "text-brand-warning" : ""}`}></i>
          ) : (
            <div className={`w-1.5 h-1.5 rounded-full ${isActive ? "bg-brand-warning" : "bg-gray-300"}`}></div>
          )}
        </div>
        {!isCollapsed && <span className="truncate">{item.label}</span>}
      </Link>
    );
  };

  const renderSubSection = (sub: SidebarSubSection) => {
    const isOpen = openSections.includes(sub.sub_section_code);
    const hasActiveItem = sub.items.some((item) => item.route === pathname);

    return (
      <div key={sub.sub_section_code} className="mb-1">
        <button
          onClick={() => toggleSection(sub.sub_section_code)}
          className={`w-full flex items-center justify-between px-3 py-2 text-sm rounded-lg transition-colors ${
            hasActiveItem ? "text-gray-900 font-semibold bg-gray-50" : "text-gray-700 hover:bg-gray-50"
          }`}
          title={isCollapsed ? sub.sub_section_label : undefined}
        >
          <div className="flex items-center gap-3 overflow-hidden">
             <div className="w-5 flex items-center justify-center flex-shrink-0 text-gray-400">
               <i className="fas fa-folder text-xs"></i>
             </div>
            {!isCollapsed && <span className="truncate">{sub.sub_section_label}</span>}
          </div>
          {!isCollapsed && (
            <i
              className={`fas fa-chevron-down text-[10px] transition-transform duration-200 ${
                isOpen ? "rotate-180 text-brand-warning" : "text-gray-400"
              }`}
            ></i>
          )}
        </button>
        
        {/* Sub-items */}
        {!isCollapsed && isOpen && (
          <div className="mt-1 pl-4 space-y-1 relative before:absolute before:left-5 before:top-0 before:bottom-0 before:w-px before:bg-gray-200">
            {sub.items.map(renderItem)}
          </div>
        )}
      </div>
    );
  };

  const renderSection = (section: SidebarSection) => {
    return (
      <div key={section.section_code} className="mb-6">
        {!isCollapsed && (
          <h3 className="px-4 text-xs font-bold text-gray-400 uppercase tracking-wider mb-2">
            {section.section_label}
          </h3>
        )}
        
        <div className="space-y-1">
          {section.items?.map(renderItem)}
          {section.subSections?.map(renderSubSection)}
        </div>
      </div>
    );
  };

  return (
    <aside
      className={`fixed top-0 left-0 h-screen transition-all duration-300 z-40 border-r border-gray-200 bg-white flex flex-col shadow-sm ${
        isCollapsed ? "w-[70px]" : "w-[260px]"
      }`}
    >
      <div className="h-22 flex items-center justify-between px-4 border-b border-gray-200 flex-shrink-0 bg-white">
        {!isCollapsed && (
          <Link href="/dashboard" className="font-bold text-xl text-brand-warning flex items-center gap-2 truncate">
            <span>MyntReal</span>
          </Link>
        )}
        <button
          onClick={() => setIsCollapsed(!isCollapsed)}
          className={`p-2 text-gray-400 hover:text-gray-700 rounded-lg hover:bg-gray-100 ${isCollapsed ? "mx-auto" : ""}`}
        >
          <i className="fas fa-bars"></i>
        </button>
      </div>

      <div className="flex-1 overflow-y-auto overflow-x-hidden p-3 custom-scrollbar bg-white">
        {MENU_MASTER.map(renderSection)}
      </div>
      
      {/* Footer / Profile collapsed hint */}
      <div className="p-4 border-t border-gray-200 flex-shrink-0 bg-gray-50">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-brand-warning/20 text-brand-warning flex items-center justify-center font-bold flex-shrink-0">
             {user?.name?.charAt(0) || "U"}
          </div>
          {!isCollapsed && (
            <div className="flex-1 min-w-0">
              <p className="text-sm font-bold text-gray-900 truncate">{user?.name || "Mynt Staff"}</p>
              <p className="text-xs text-gray-500 truncate">{user?.role?.role_name || "MNR"}</p>
            </div>
          )}
        </div>
      </div>
      
      <style dangerouslySetInnerHTML={{__html: `
        .custom-scrollbar::-webkit-scrollbar {
          width: 4px;
        }
        .custom-scrollbar::-webkit-scrollbar-track {
          background: transparent;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb {
          background: rgba(156, 163, 175, 0.3);
          border-radius: 4px;
        }
        .custom-scrollbar:hover::-webkit-scrollbar-thumb {
          background: rgba(156, 163, 175, 0.6);
        }
      `}} />
    </aside>
  );
}
