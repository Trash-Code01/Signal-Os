
const fs = require("fs");
const path = "c:\\Code-work\\Signal Os\\apps\\web\\src\\app\\leads\\page.tsx";

let content = fs.readFileSync(path, "utf-8");

// Add SidebarTrigger import
if (!content.includes("SidebarTrigger")) {
  content = content.replace(
    /import \{ useDebounce \} from "use-debounce";/,
    `import { useDebounce } from "use-debounce";\nimport { SidebarTrigger } from "@/components/ui/sidebar";`
  );
}

// Add SidebarTrigger into the header next to "Leads"
content = content.replace(
  /<h1 className="text-xl font-bold text-white">Leads<\/h1>/,
  `<div className="flex items-center gap-2"><SidebarTrigger className="lg:hidden text-zinc-400 hover:text-white" /><h1 className="text-xl font-bold text-white">Leads</h1></div>`
);

fs.writeFileSync(path, content, "utf-8");
console.log("Main Leads UI Polish Applied successfully");

