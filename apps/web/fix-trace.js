const fs = require('fs');
const path = require('path');

const target = path.join(__dirname, '.next', 'next-server.js.nft.json');
const fallback = path.join(__dirname, '.next', 'next-minimal-server.js.nft.json');

if (!fs.existsSync(target)) {
  console.log(`[Vercel Fix] ${target} is missing. Creating it to prevent Vercel ENOENT crash...`);
  if (fs.existsSync(fallback)) {
    fs.copyFileSync(fallback, target);
    console.log(`[Vercel Fix] Copied from ${fallback}`);
  } else {
    fs.writeFileSync(target, JSON.stringify({ version: 1, files: [] }));
    console.log(`[Vercel Fix] Created empty trace file`);
  }
} else {
  console.log(`[Vercel Fix] ${target} already exists. No action needed.`);
}
