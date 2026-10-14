import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Devacia Lead Intelligence",
  description: "Contact intelligence, website research, and personalised outreach.",
};

import { SidebarProvider } from "@/components/ui/sidebar";
import { TooltipProvider } from "@/components/ui/tooltip";
import { SessionProvider } from "@/components/SessionProvider";
import { AppShell } from "@/components/AppShell";

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark h-full antialiased" suppressHydrationWarning>
      <body className="min-h-full flex bg-[#09090b] font-sans text-white" suppressHydrationWarning>
        <TooltipProvider>
          <SidebarProvider>
            <SessionProvider><AppShell>{children}</AppShell></SessionProvider>
          </SidebarProvider>
        </TooltipProvider>
      </body>
    </html>
  );
}
