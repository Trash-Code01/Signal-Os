const { test, afterEach, mock } = require('node:test');
const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const { resolve } = require('node:path');
const { createRequire } = require('node:module');
const { runInThisContext } = require('node:vm');
const ts = require('typescript');

function load(name) {
  const file = resolve(__dirname, '../src/lib', name);
  const module = { exports: {} };
  const code = ts.transpileModule(readFileSync(file, 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  }).outputText;
  runInThisContext(`(function(require, module, exports) { ${code}\n})`, { filename: file })(createRequire(file), module, module.exports);
  return module.exports;
}

const { fetchAllCrmLeads } = load('fetchAllCrmLeads.ts');
const { formatLeadsForExport } = load('exportUtils.ts');
afterEach(() => mock.restoreAll());

test('all-lead export follows every API page and keeps discovery filters', async () => {
  const calls = [];
  mock.method(globalThis, 'fetch', async url => {
    const params = new URL(url, 'http://localhost').searchParams;
    calls.push(params);
    const start = (Number(params.get('page')) - 1) * 200;
    return Response.json({ total: 401, leads: Array.from({length: Math.min(200, 401 - start)}, (_, i) => ({id: start + i, name: 'Fixture'})) });
  });
  const leads = await fetchAllCrmLeads({website_filter:'no_website', channel:'facebook', sort_by:'best'});
  assert.equal(leads.length, 401);
  assert.equal(calls.length, 3);
  assert(calls.every(params => params.get('website_filter') === 'no_website' && params.get('channel') === 'facebook'));
});

test('failed export page never silently returns an incomplete download', async () => {
  let calls = 0;
  mock.method(globalThis, 'fetch', async () => ++calls === 1
    ? Response.json({total:2, leads:[{id:1,name:'Fixture'}]})
    : new Response('Unavailable', {status:503}));
  await assert.rejects(fetchAllCrmLeads(), /503/);
});

test('export retains website uncertainty and discovery provenance', () => {
  const [row] = formatLeadsForExport([{id:1,name:'Fixture',website_url:null,website_status:'unknown',
    discovery_sources:[{channel:'facebook',url:'https://facebook.com/fixture'}]}]);
  assert.equal(row['Website Status'], 'unknown');
  assert.equal(row['Discovery Channels'], 'facebook');
  assert.equal(row['Discovery Sources'], 'https://facebook.com/fixture');
});
