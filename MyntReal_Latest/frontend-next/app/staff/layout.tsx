import Sidebar from "@/components/layout/Sidebar";
import Header from "@/components/layout/Header";
import AuthGuard from "@/components/layout/AuthGuard";

export default function StaffLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <AuthGuard>
      <Sidebar />
      <Header />
      
      {/* Main Content Wrapper */}
      <main className="ml-[260px] pt-22 p-6 transition-all duration-300">
        {children}
      </main>
    </AuthGuard>
  );
}
