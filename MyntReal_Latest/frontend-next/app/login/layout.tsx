import { StaffAuthProvider } from "@/contexts/StaffAuthContext";

export default function LoginLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <StaffAuthProvider>
      {children}
    </StaffAuthProvider>
  );
}
