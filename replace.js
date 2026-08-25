const fs = require('fs');
const path = require('path');

function walk(dir) {
    let results = [];
    const list = fs.readdirSync(dir);
    list.forEach(file => {
        file = path.join(dir, file);
        const stat = fs.statSync(file);
        if (stat && stat.isDirectory()) {
            results = results.concat(walk(file));
        } else {
            if (file.endsWith('.ts') || file.endsWith('.tsx')) results.push(file);
        }
    });
    return results;
}

const files = walk('apps/web/src');
files.forEach(f => {
    let content = fs.readFileSync(f, 'utf8');
    const old = content;
    content = content.replace(/'https:\/\/devacia-api\.onrender\.com'/g, "(process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000')");
    
    if (content !== old) {
        fs.writeFileSync(f, content, 'utf8');
        console.log('Reverted: ' + f);
    }
});
