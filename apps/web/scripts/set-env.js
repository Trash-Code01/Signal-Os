const fs = require('fs');
const path = require('path');
const { spawn } = require('child_process');

const targetEnv = process.argv[2] || 'staging'; // 'staging' or 'production'
const webRoot = path.resolve(__dirname, '..');
const sourceFile = path.join(webRoot, `.env.${targetEnv}`);
const targetFile = path.join(webRoot, '.env.local');

if (!fs.existsSync(sourceFile)) {
  console.error(`[Error] Environment file not found: ${sourceFile}`);
  process.exit(1);
}

fs.copyFileSync(sourceFile, targetFile);
console.log(`\n========================================`);
if (targetEnv === 'staging') {
  console.log(`>>> ACTIVATING STAGING DEVELOPMENT MODE <<<`);
  console.log(`- Backend: http://localhost:8000 (Local / Staging)`);
  console.log(`- Frontend: http://localhost:3001`);
  console.log(`- Mode: Safe sandbox (isolated from Render production)`);
} else {
  console.log(`>>> ACTIVATING PRODUCTION MODE <<<`);
  console.log(`- Backend: https://devacia-backend.onrender.com`);
  console.log(`- Frontend: http://localhost:3001`);
  console.log(`- Mode: Live production database`);
}
console.log(`========================================\n`);

// Run next dev on port 3001
const isWin = process.platform === 'win32';
const nextCmd = isWin ? 'npx.cmd' : 'npx';
const child = spawn(nextCmd, ['next', 'dev', '-p', '3001'], {
  cwd: webRoot,
  stdio: 'inherit',
  shell: true,
});

child.on('exit', (code) => {
  process.exit(code || 0);
});
