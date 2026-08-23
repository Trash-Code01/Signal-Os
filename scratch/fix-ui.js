
const fs = require("fs");
const path = "c:\\Code-work\\Signal Os\\apps\\web\\src\\app\\leads\\[id]\\page.tsx";

let content = fs.readFileSync(path, "utf-8");

// Fix invalid tailwind classes
content = content.replace(/font-body-md/g, "text-sm");
content = content.replace(/font-label-md/g, "text-xs font-semibold");
content = content.replace(/px-lg/g, "px-4 sm:px-6 md:px-8");
content = content.replace(/py-md/g, "py-4 md:py-5");
content = content.replace(/p-lg/g, "p-4 sm:p-6 md:p-8");
content = content.replace(/gap-xl/g, "gap-6 lg:gap-10");
content = content.replace(/font-headline-lg/g, "");

// Add SidebarTrigger import
if (!content.includes("SidebarTrigger")) {
  content = content.replace(
    /import Link from "next\/link";/,
    `import Link from "next/link";\nimport { SidebarTrigger } from "@/components/ui/sidebar";`
  );
}

// Add SidebarTrigger into the header
content = content.replace(
  /<div className="flex items-center gap-2 text-on-surface-variant text-sm lowercase tracking-normal">/,
  `<div className="flex items-center gap-2 text-on-surface-variant text-sm lowercase tracking-normal">\n          <SidebarTrigger className="lg:hidden text-outline hover:text-primary transition-colors mr-2 p-1 -ml-2" />`
);

// Add rounded caps to SVG circles for better aesthetics
content = content.replace(/strokeDasharray/g, `strokeLinecap="round" strokeDasharray`);

// Add gentle fade-in animation and better shadow
content = content.replace(
  /className="lead-dossier-page min-h-screen bg-\[#141313\] text-on-surface text-sm flex flex-col"/,
  `className="lead-dossier-page min-h-screen bg-[#141313] text-on-surface text-sm flex flex-col animate-in fade-in duration-500"`
);

// Fix overlapping header by ensuring z-index and bg blur for professional look
content = content.replace(
  /className="bg-surface-dim text-on-surface text-xs font-semibold uppercase tracking-wider flex justify-between items-center w-full px-4 sm:px-6 md:px-8 py-4 md:py-5 sticky top-0 z-40 border-b border-outline-variant\/30"/,
  `className="bg-[#141313]/80 backdrop-blur-md text-on-surface text-xs font-semibold uppercase tracking-wider flex justify-between items-center w-full px-4 sm:px-6 md:px-8 py-4 sticky top-0 z-40 border-b border-outline-variant/30 shadow-sm"`
);

// Add smooth hover lifts to cards
content = content.replace(
  /bg-surface-container-low border border-outline-variant\/40 rounded-lg/g,
  `bg-surface-container-low border border-outline-variant/40 rounded-xl shadow-sm hover:shadow-md hover:-translate-y-0.5 transition-all duration-300`
);

fs.writeFileSync(path, content, "utf-8");
console.log("UI Polish Applied successfully");

