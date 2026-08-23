
const fs = require("fs");
const files = [
  "c:\\Code-work\\Signal Os\\apps\\web\\src\\app\\leads\\page.tsx",
  "c:\\Code-work\\Signal Os\\apps\\web\\src\\app\\campaigns\\page.tsx",
  "c:\\Code-work\\Signal Os\\apps\\web\\src\\app\\dashboard\\page.tsx",
  "c:\\Code-work\\Signal Os\\apps\\web\\src\\app\\campaigns\\new\\page.tsx",
  "c:\\Code-work\\Signal Os\\apps\\web\\src\\app\\leads\\[id]\\page.tsx"
];

for (const file of files) {
  if (fs.existsSync(file)) {
    let content = fs.readFileSync(file, "utf8");
    const newContent = content.replace(/(\?|)/g, "•").replace(/â€¢/g, "•");
    if (content !== newContent) {
      fs.writeFileSync(file, newContent, "utf8");
      console.log("Fixed encoding in", file);
    }
  }
}

