"use client";

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { 
  PieChart, 
  Magnet, 
  Activity, 
  PlusCircle, 
  Megaphone, 
  Settings, 
  LogOut, 
  Search,
  Trash2,
  ChevronLeft,
  ChevronRight
} from 'lucide-react';
import {
  Sidebar as ShadcnSidebar,
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuItem,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarTrigger,
  SidebarRail,
  useSidebar
} from "@/components/ui/sidebar";

export function Sidebar() {
  const pathname = usePathname() || '';
  const { state } = useSidebar();

  const isActive = (path: string) => {
    return pathname === path || (path !== '/dashboard' && pathname.startsWith(path));
  };

  const getLinkClass = (path: string, exact: boolean = false) => {
    const active = exact ? pathname === path : isActive(path);
    return `flex items-center gap-3 px-3 py-2 group-data-[collapsible=icon]:justify-center group-data-[collapsible=icon]:px-0 text-sm rounded-md transition-all duration-200 ${
      active 
        ? 'bg-white/10 text-white font-medium shadow-sm' 
        : 'text-zinc-400 hover:bg-white/5 hover:text-white'
    }`;
  };

  return (
    <ShadcnSidebar collapsible="icon" className="border-r border-white/5 bg-[#09090b] text-zinc-300 hidden md:flex">
      <SidebarHeader className="p-5 group-data-[collapsible=icon]:p-2 group-data-[collapsible=icon]:pt-5 group-data-[collapsible=icon]:items-center">
        <div className="flex items-center justify-between w-full group-data-[collapsible=icon]:justify-center">
          <div className="flex items-center gap-3 overflow-hidden group-data-[collapsible=icon]:hidden">
            <div className="flex shrink-0 h-8 w-8 items-center justify-center rounded-md bg-white text-black font-bold text-lg">
              D
            </div>
            <span className="font-semibold text-white tracking-tight">Devacia Admin</span>
          </div>
          <SidebarTrigger className="h-6 w-6 shrink-0 text-zinc-500 hover:text-white hover:bg-white/10 rounded-md p-0 flex items-center justify-center transition-colors">
            {state === "collapsed" ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
          </SidebarTrigger>
        </div>
        
        <div className="mt-6 relative group-data-[collapsible=icon]:hidden">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500" />
          <input 
            type="text" 
            placeholder="Search" 
            className="w-full bg-white/5 border border-white/10 rounded-md py-1.5 pl-9 pr-3 text-sm text-white placeholder:text-zinc-500 outline-none focus:border-white/20 transition-colors"
          />
        </div>
      </SidebarHeader>
      
      <SidebarContent className="px-3">
        <SidebarGroup>
          <SidebarGroupLabel className="text-[10px] font-semibold text-zinc-500 uppercase tracking-wider mb-2 px-3 group-data-[collapsible=icon]:hidden">
            Main
          </SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu className="space-y-0.5">
              <SidebarMenuItem>
                <Link href="/dashboard" className={getLinkClass('/dashboard', true)}>
                  <PieChart className="w-4 h-4 shrink-0" strokeWidth={2} />
                  <span className="group-data-[collapsible=icon]:hidden">Analytics</span>
                </Link>
              </SidebarMenuItem>
              <SidebarMenuItem>
                <Link href="/leads" className={getLinkClass('/leads')}>
                  <Magnet className="w-4 h-4 shrink-0" strokeWidth={2} />
                  <span className="group-data-[collapsible=icon]:hidden">Leads</span>
                </Link>
              </SidebarMenuItem>
              <SidebarMenuItem>
                <Link href="/jobs" className={getLinkClass('/jobs')}>
                  <Activity className="w-4 h-4 shrink-0" strokeWidth={2} />
                  <span className="group-data-[collapsible=icon]:hidden">Job Monitor</span>
                </Link>
              </SidebarMenuItem>
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        <SidebarGroup className="mt-4">
          <SidebarGroupLabel className="text-[10px] font-semibold text-zinc-500 uppercase tracking-wider mb-2 px-3 group-data-[collapsible=icon]:hidden">
            Campaigns
          </SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu className="space-y-0.5">
              <SidebarMenuItem>
                <Link href="/campaigns" className={getLinkClass('/campaigns', true)}>
                  <Megaphone className="w-4 h-4 shrink-0" strokeWidth={2} />
                  <span className="group-data-[collapsible=icon]:hidden">All Campaigns</span>
                </Link>
              </SidebarMenuItem>
              <SidebarMenuItem>
                <Link href="/campaigns/new" className={getLinkClass('/campaigns/new', true)}>
                  <PlusCircle className="w-4 h-4 shrink-0" strokeWidth={2} />
                  <span className="group-data-[collapsible=icon]:hidden">New Campaign</span>
                </Link>
              </SidebarMenuItem>
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        <SidebarGroup className="mt-4">
          <SidebarGroupLabel className="text-[10px] font-semibold text-zinc-500 uppercase tracking-wider mb-2 px-3 group-data-[collapsible=icon]:hidden">
            System
          </SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu className="space-y-0.5">
              <SidebarMenuItem>
                <Link href="/settings" className={getLinkClass('/settings')}>
                  <Settings className="w-4 h-4 shrink-0" strokeWidth={2} />
                  <span className="group-data-[collapsible=icon]:hidden">Settings</span>
                </Link>
              </SidebarMenuItem>
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        <SidebarGroup className="mt-4">
          <SidebarGroupLabel className="text-[10px] font-semibold text-zinc-500 uppercase tracking-wider mb-2 px-3 group-data-[collapsible=icon]:hidden">
            Data
          </SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu className="space-y-0.5">
              <SidebarMenuItem>
                <Link href="/trash" className={getLinkClass('/trash')}>
                  <Trash2 className="w-4 h-4 shrink-0" strokeWidth={2} />
                  <span className="group-data-[collapsible=icon]:hidden">Trash Bin</span>
                </Link>
              </SidebarMenuItem>
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>

      <SidebarFooter className="p-5 mt-auto border-t border-white/5 group-data-[collapsible=icon]:p-2 group-data-[collapsible=icon]:pb-5">
        <button onClick={async () => {
          await fetch('/api/auth/logout', { method: 'POST' });
          window.location.href = '/login';
        }} className="flex items-center gap-3 px-3 py-2 w-full group-data-[collapsible=icon]:px-1.5 group-data-[collapsible=icon]:justify-center text-sm text-zinc-400 hover:text-white transition-colors mb-4">
          <LogOut className="w-4 h-4 shrink-0" strokeWidth={2} />
          <span className="group-data-[collapsible=icon]:hidden">Log Out</span>
        </button>
        <div className="flex items-center gap-3 p-2 rounded-xl bg-white/5 border border-white/10 hover:bg-white/10 transition-colors cursor-pointer group-data-[collapsible=icon]:bg-transparent group-data-[collapsible=icon]:border-transparent group-data-[collapsible=icon]:p-0">
          <div className="w-8 h-8 flex-shrink-0 rounded-lg bg-zinc-800 flex items-center justify-center text-sm font-semibold text-white shadow-sm border border-white/10">
            L
          </div>
          <div className="flex flex-col overflow-hidden group-data-[collapsible=icon]:hidden">
            <span className="text-sm font-medium text-white truncate leading-tight">laraib</span>
            <span className="text-xs text-zinc-500 truncate mt-0.5">Administrator</span>
          </div>
        </div>
      </SidebarFooter>
      <SidebarRail />
    </ShadcnSidebar>
  );
}
