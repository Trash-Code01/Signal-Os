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
      <head>
        <link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap" rel="stylesheet" />
        <style>{`
          .material-symbols-outlined {
            font-variation-settings: 'FILL' 0, 'wght' 300, 'GRAD' 0, 'opsz' 24;
          }
        `}</style>
      </head>
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
