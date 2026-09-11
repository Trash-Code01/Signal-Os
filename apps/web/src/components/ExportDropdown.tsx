"use client";

import React, { useState, useRef, useEffect } from "react";
import { Download, FileSpreadsheet, FileText, Code2, ChevronDown, Check, Loader2 } from "lucide-react";

export type ExportFormat = "xlsx" | "csv" | "json";
export type ExportScope = "selected" | "all";

interface ExportDropdownProps {
  totalCount: number;
  selectedCount: number;
  onExport: (format: ExportFormat, scope: ExportScope) => Promise<void> | void;
  entityName?: string; // e.g. "Leads" or "Campaigns"
  variant?: "header" | "floating" | "compact";
  className?: string;
}

export default function ExportDropdown({
  totalCount,
  selectedCount,
  onExport,
  entityName = "items",
  variant = "header",
  className = "",
}: ExportDropdownProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [scope, setScope] = useState<ExportScope>(selectedCount > 0 ? "selected" : "all");
  const [isExporting, setIsExporting] = useState(false);
  const [exportSuccess, setExportSuccess] = useState<string | null>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Sync scope when selection changes
  useEffect(() => {
    if (selectedCount > 0 && scope !== "selected") {
      setScope("selected");
    } else if (selectedCount === 0 && scope === "selected") {
      setScope("all");
    }
  }, [selectedCount]);

  // Click outside listener
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [isOpen]);

  const handleSelectFormat = async (format: ExportFormat) => {
    try {
      setIsExporting(true);
      await onExport(format, scope);
      setExportSuccess(format.toUpperCase());
      setTimeout(() => {
        setExportSuccess(null);
        setIsOpen(false);
      }, 1000);
    } catch (err) {
      console.error("Export failed:", err);
    } finally {
      setIsExporting(false);
    }
  };

  const countToExport = scope === "selected" ? selectedCount : totalCount;

  // Trigger button styling based on variant
  let triggerButtonClass = "";
  if (variant === "header") {
    triggerButtonClass =
      "flex items-center gap-2 bg-[#18181b] hover:bg-zinc-800 text-zinc-200 hover:text-white border border-zinc-700/80 px-3.5 py-2 rounded-lg text-xs font-semibold transition-all shadow-sm";
  } else if (variant === "floating") {
    triggerButtonClass =
      "flex items-center gap-2 text-purple-300 hover:text-white bg-purple-950/60 hover:bg-purple-900/80 border border-purple-500/40 px-3.5 py-1.5 rounded-full text-xs font-semibold transition-all";
  } else {
    triggerButtonClass =
      "p-2 text-zinc-400 hover:text-white rounded-lg hover:bg-zinc-800 transition";
  }

  return (
    <div className={`relative inline-block text-left ${className}`} ref={dropdownRef}>
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        disabled={isExporting}
        className={triggerButtonClass}
        title="Export data to Excel, CSV, or JSON"
      >
        {isExporting ? (
          <Loader2 className="w-3.5 h-3.5 animate-spin text-purple-400" />
        ) : (
          <Download className="w-3.5 h-3.5 text-purple-400" />
        )}
        <span>
          {variant === "floating"
            ? `Export (${selectedCount})`
            : selectedCount > 0
            ? `Export (${selectedCount})`
            : "Export"}
        </span>
        <ChevronDown className="w-3 h-3 text-zinc-400" />
      </button>

      {isOpen && (
        <div className="absolute right-0 mt-2 w-64 origin-top-right rounded-xl bg-[#121214] border border-zinc-800 shadow-2xl p-2 z-50 animate-in fade-in zoom-in-95 duration-150">
          {/* Scope selection if items are selected */}
          {selectedCount > 0 ? (
            <div className="mb-2 p-1.5 bg-[#09090b] rounded-lg border border-zinc-800/80">
              <div className="text-[10px] uppercase tracking-wider font-semibold text-zinc-500 px-2 pt-1 pb-1">
                Export Scope
              </div>
              <div className="grid grid-cols-2 gap-1 text-xs">
                <button
                  type="button"
                  onClick={() => setScope("selected")}
                  className={`px-2 py-1.5 rounded-md font-medium transition text-left flex items-center justify-between ${
                    scope === "selected"
                      ? "bg-purple-600/30 text-purple-300 border border-purple-500/40"
                      : "text-zinc-400 hover:bg-zinc-800 hover:text-white"
                  }`}
                >
                  <span>Selected</span>
                  <span className="text-[10px] bg-zinc-800 px-1.5 py-0.5 rounded text-zinc-300">
                    {selectedCount}
                  </span>
                </button>
                <button
                  type="button"
                  onClick={() => setScope("all")}
                  className={`px-2 py-1.5 rounded-md font-medium transition text-left flex items-center justify-between ${
                    scope === "all"
                      ? "bg-purple-600/30 text-purple-300 border border-purple-500/40"
                      : "text-zinc-400 hover:bg-zinc-800 hover:text-white"
                  }`}
                >
                  <span>All</span>
                  <span className="text-[10px] bg-zinc-800 px-1.5 py-0.5 rounded text-zinc-300">
                    {totalCount}
                  </span>
                </button>
              </div>
            </div>
          ) : (
            <div className="px-3 py-1.5 mb-1 border-b border-zinc-800/60 flex items-center justify-between text-xs text-zinc-400">
              <span>Exporting all</span>
              <span className="font-semibold text-white">
                {totalCount} {entityName.toLowerCase()}
              </span>
            </div>
          )}

          {/* Format Options */}
          <div className="space-y-1">
            <button
              type="button"
              disabled={isExporting}
              onClick={() => handleSelectFormat("xlsx")}
              className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-left text-xs text-zinc-200 hover:text-white hover:bg-zinc-800/80 transition group"
            >
              <div className="w-7 h-7 rounded-md bg-emerald-500/10 text-emerald-400 flex items-center justify-center shrink-0 group-hover:bg-emerald-500/20 group-hover:scale-105 transition">
                <FileSpreadsheet className="w-4 h-4" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="font-semibold flex items-center gap-1.5">
                  Excel Spreadsheet
                  <span className="text-[10px] text-emerald-400 font-mono font-normal">.xlsx</span>
                </div>
                <div className="text-[10px] text-zinc-500 truncate">
                  Formatted sheets & auto column widths
                </div>
              </div>
              {exportSuccess === "XLSX" && (
                <Check className="w-4 h-4 text-emerald-400 animate-in zoom-in" />
              )}
            </button>

            <button
              type="button"
              disabled={isExporting}
              onClick={() => handleSelectFormat("csv")}
              className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-left text-xs text-zinc-200 hover:text-white hover:bg-zinc-800/80 transition group"
            >
              <div className="w-7 h-7 rounded-md bg-blue-500/10 text-blue-400 flex items-center justify-center shrink-0 group-hover:bg-blue-500/20 group-hover:scale-105 transition">
                <FileText className="w-4 h-4" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="font-semibold flex items-center gap-1.5">
                  CSV Document
                  <span className="text-[10px] text-blue-400 font-mono font-normal">.csv</span>
                </div>
                <div className="text-[10px] text-zinc-500 truncate">
                  UTF-8 BOM for Excel & Google Sheets
                </div>
              </div>
              {exportSuccess === "CSV" && (
                <Check className="w-4 h-4 text-blue-400 animate-in zoom-in" />
              )}
            </button>

            <button
              type="button"
              disabled={isExporting}
              onClick={() => handleSelectFormat("json")}
              className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-left text-xs text-zinc-200 hover:text-white hover:bg-zinc-800/80 transition group"
            >
              <div className="w-7 h-7 rounded-md bg-purple-500/10 text-purple-400 flex items-center justify-center shrink-0 group-hover:bg-purple-500/20 group-hover:scale-105 transition">
                <Code2 className="w-4 h-4" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="font-semibold flex items-center gap-1.5">
                  JSON Raw Data
                  <span className="text-[10px] text-purple-400 font-mono font-normal">.json</span>
                </div>
                <div className="text-[10px] text-zinc-500 truncate">
                  Complete structured records
                </div>
              </div>
              {exportSuccess === "JSON" && (
                <Check className="w-4 h-4 text-purple-400 animate-in zoom-in" />
              )}
            </button>
          </div>

          {/* Footer note */}
          <div className="mt-2 pt-2 border-t border-zinc-800/60 px-2 py-1 text-[10px] text-zinc-500 text-center">
            Ready to export {countToExport} {entityName.toLowerCase()}
          </div>
        </div>
      )}
    </div>
  );
}
