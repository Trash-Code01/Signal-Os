const { test, afterEach, mock } = require('node:test');
const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const { resolve, dirname } = require('node:path');
const { createRequire } = require('node:module');
const { runInThisContext } = require('node:vm');
const ts = require('typescript');
const { NextRequest } = require('next/server');

// Execute the actual route handlers with mocked upstream HTTP, without a build
// or new test dependencies. Local TypeScript/alias imports share one cache.
const modules = new Map();
function load(relative) {
  const file = resolve(__dirname, '../src', relative);
  if (modules.has(file)) return modules.get(file).exports;
  const module = { exports: {} };
  modules.set(file, module);
  const code = ts.transpileModule(readFileSync(file, 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  }).outputText;
  const nativeRequire = createRequire(file);
  const localRequire = (name) => {
    if (name.startsWith('@/')) return load(`${name.slice(2)}.ts`);
    if (name.startsWith('.')) return load(resolve(dirname(file), `${name}.ts`));
    return nativeRequire(name);
  };
  runInThisContext(`(function(require, module, exports) { ${code}\n})`, { filename: file })(localRequire, module, module.exports);
  return module.exports;
}

const originalEnvironment = { ...process.env };
process.env.NODE_ENV = 'production';
const google = load('app/api/auth/google/route.ts');
const login = load('app/api/auth/login/route.ts');
const { authRequest } = load('lib/authRequest.ts');
afterEach(() => {
  mock.restoreAll();
  for (const key of ['API_URL', 'NEXT_PUBLIC_API_URL', 'NODE_ENV']) {
    if (originalEnvironment[key] === undefined) delete process.env[key];
    else process.env[key] = originalEnvironment[key];
  }
});

function request(path, body = {}, origin = 'https://app.example', cookie = '') {
  return new NextRequest(`https://app.example/api/auth/${path}`, {
    method: 'POST',
    headers: { host: 'app.example', origin, 'x-forwarded-proto': 'https', cookie, 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
}

test('Google config uses the runtime backend ID and issues a secure nonce', async () => {
  process.env.API_URL = 'https://runtime-api.example/';
  process.env.NEXT_PUBLIC_API_URL = 'https://old-build-api.example';
  const upstream = mock.method(globalThis, 'fetch', async (url) => {
    assert.equal(url, 'https://runtime-api.example/api/auth/config');
    return Response.json({ client_id: 'backend-client' });
  });
  const result = await google.GET();
  const data = await result.json();
  assert.equal(result.status, 200);
  assert.equal(data.client_id, 'backend-client');
  assert.match(data.nonce, /^[a-f0-9]{64}$/);
  assert.equal(result.cookies.get('google_nonce').value, data.nonce);
  assert.match(result.headers.get('set-cookie'), /HttpOnly/);
  assert.match(result.headers.get('set-cookie'), /Secure/);
  assert.equal(result.headers.get('cache-control'), 'no-store');
  assert.equal(upstream.mock.callCount(), 1);
});

test('offline, unconfigured, or HTML backends cannot advertise ready Google login', async () => {
  for (const response of [Response.json({ client_id: '' }), new Response('<html>Unavailable</html>', { status: 503 })]) {
    mock.method(globalThis, 'fetch', async () => response);
    const result = await google.GET();
    assert.equal(result.status, 503);
    assert.equal(result.cookies.get('google_nonce'), undefined);
    assert.equal((await result.json()).nonce, undefined);
    mock.restoreAll();
  }
  mock.method(globalThis, 'fetch', async () => { throw new TypeError('fetch failed'); });
  assert.equal((await google.GET()).status, 503);
});

test('Google rejects mismatched nonce and cross-origin posts without calling backend', async () => {
  const upstream = mock.method(globalThis, 'fetch', async () => { throw new Error('must not call'); });
  assert.equal((await google.POST(request('google', { nonce: 'other' }, undefined, 'google_nonce=expected'))).status, 403);
  assert.equal((await google.POST(request('google', { nonce: 'expected' }, 'https://evil.example', 'google_nonce=expected'))).status, 403);
  assert.equal((await login.POST(request('login', {}, 'https://evil.example'))).status, 403);
  assert.equal(upstream.mock.callCount(), 0);
});

test('valid Google login establishes a private session and consumes the nonce', async () => {
  mock.method(globalThis, 'fetch', async (_url, init) => {
    assert.deepEqual(JSON.parse(init.body), { credential: 'google-credential', nonce: 'expected' });
    return Response.json({ access_token: 'verified-token', email: 'owner@example.com', role: 'admin' });
  });
  const result = await google.POST(request('google', { credential: 'google-credential', nonce: 'expected' }, undefined, 'google_nonce=expected'));
  assert.equal(result.status, 200);
  assert.equal(result.cookies.get('access_token').value, 'verified-token');
  assert.equal(result.cookies.get('google_nonce').maxAge, 0);
  assert.equal((await result.json()).access_token, undefined);
});

test('password login sets a session only when the backend returns a token', async () => {
  mock.method(globalThis, 'fetch', async () => Response.json({ access_token: 'password-token' }));
  assert.equal((await login.POST(request('login'))).cookies.get('access_token').value, 'password-token');
  mock.restoreAll();
  mock.method(globalThis, 'fetch', async () => Response.json({ success: true }));
  for (const result of [await login.POST(request('login')), await google.POST(request('google', { nonce: 'expected' }, undefined, 'google_nonce=expected'))]) {
    assert.equal(result.status, 502);
    assert.equal(result.cookies.get('access_token'), undefined);
  }
});

test('backend rejections are preserved and never set a session', async () => {
  mock.method(globalThis, 'fetch', async () => Response.json({ detail: 'Account disabled' }, { status: 403 }));
  const result = await login.POST(request('login'));
  assert.equal(result.status, 403);
  assert.equal((await result.json()).detail, 'Account disabled');
  assert.equal(result.cookies.get('access_token'), undefined);
});

test('deadline bounds a stalled connection and a stalled response body', async () => {
  for (const stallBody of [false, true]) {
    mock.method(globalThis, 'fetch', async (_url, { signal }) => {
      const untilAborted = () => new Promise((_resolve, reject) => signal.addEventListener('abort', () => reject(new Error('aborted')), { once: true }));
      return stallBody ? { text: untilAborted } : untilAborted();
    });
    await assert.rejects(authRequest('/api/auth/login', {}, 10), /took too long/);
    mock.restoreAll();
  }
});

test('HTML errors and structured validation errors produce readable messages', async () => {
  for (const response of [new Response('<html>Gateway error</html>', { status: 502 }), Response.json({ detail: [{ msg: 'validation error' }] }, { status: 422 })]) {
    mock.method(globalThis, 'fetch', async () => response);
    await assert.rejects(authRequest('/api/auth/login'), (error) => typeof error.message === 'string' && !error.message.includes('[object Object]') && !error.message.includes('<html>'));
    mock.restoreAll();
  }
});
