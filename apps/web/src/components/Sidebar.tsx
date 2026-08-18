"use client";

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { FiLayout, FiTarget, FiUsers, FiBriefcase, FiSearch, FiDownload, FiSettings, FiArchive } from 'react-icons/fi';

export function Sidebar() {
  const pathname = usePathname();

  const getLinkClass = (path: string) => {
    const isActive = pathname === path || (path !== '/dashboard' && pathname.startsWith(path));
    if (isActive) {
      return "flex items-center gap-3 px-3 py-2.5 text-sm font-medium rounded-md bg-[#8b5cf6] text-white transition-colors";
    }
    return "flex items-center gap-3 px-3 py-2.5 text-sm font-medium rounded-md hover:bg-zinc-900 text-zinc-300 hover:text-white transition-colors";
  };

  return (
    <aside className="w-64 border-r border-zinc-800 bg-[#09090b] flex flex-col h-screen fixed left-0 top-0">
      <div className="p-6">
        <h1 className="text-xl font-bold tracking-tight text-white">DEVACIA</h1>
        <p className="text-[10px] text-purple-400 font-bold uppercase tracking-widest mt-1">Lead Intelligence OS</p>
      </div>
      
      <nav className="flex-1 px-4 space-y-1 mt-4">
        <Link href="/dashboard" className={getLinkClass('/dashboard')}>
          <FiLayout className="w-4 h-4 opacity-70" />
          Overview
        </Link>
        <Link href="/campaigns" className={getLinkClass('/campaigns')}>
          <FiTarget className="w-4 h-4 opacity-70" />
          Campaigns
        </Link>
        <Link href="/leads" className={getLinkClass('/leads')}>
          <FiUsers className="w-4 h-4 opacity-70" />
          Leads
        </Link>
        <Link href="#" className={getLinkClass('/opportunities')}>
          <FiBriefcase className="w-4 h-4 opacity-70" />
          Opportunities
        </Link>
        <Link href="#" className={`mt-6 ${getLinkClass('/research')}`}>
          <FiSearch className="w-4 h-4 opacity-70" />
          Research
        </Link>
        <Link href="#" className={getLinkClass('/exports')}>
          <FiDownload className="w-4 h-4 opacity-70" />
          Exports
        </Link>
        
        <div className="pt-8 pb-2">
          <p className="px-3 text-[10px] font-bold text-zinc-500 uppercase tracking-wider">Workspace</p>
        </div>
        <Link href="#" className={getLinkClass('/all-campaigns')}>
          <FiArchive className="w-4 h-4 opacity-70" />
          All campaigns
        </Link>
        <Link href="#" className={getLinkClass('/settings')}>
          <FiSettings className="w-4 h-4 opacity-70" />
          Settings
        </Link>
      </nav>

      {/* User Profile Footer */}
      <div className="p-4 border-t border-zinc-800">
        <div className="flex items-center gap-3 p-2 rounded-lg hover:bg-zinc-900 transition-colors cursor-pointer">
          <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-purple-500 to-blue-500 flex items-center justify-center text-xs font-bold text-white shadow-inner">
            N
          </div>
          <div>
            <p className="text-sm font-medium text-white">Laraib - Founder</p>
            <p className="text-xs text-zinc-500">Devacia workspace</p>
          </div>
        </div>
      </div>
    </aside>
  );
}
