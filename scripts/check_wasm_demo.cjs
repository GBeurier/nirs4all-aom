// Verify the staged release through the demo's existing PLS/Ridge browser self-test.
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const http = require('node:http');
const path = require('node:path');
const crypto = require('node:crypto');
const root = path.resolve(__dirname, '../demo/wasm');
const manifest = JSON.parse(fs.readFileSync(path.join(root, 'n4m/version.json'), 'utf8'));
for (const [name, hash] of Object.entries(manifest.files)) {
  assert.equal(crypto.createHash('sha256').update(fs.readFileSync(path.join(root, 'n4m', name))).digest('hex'), hash, name);
}
const server = http.createServer((req, res) => {
  const pathname = decodeURIComponent(new URL(req.url, 'http://localhost').pathname);
  const file = path.resolve(root, '.' + (pathname === '/' ? '/index.html' : pathname));
  if (!file.startsWith(root + path.sep) || !fs.existsSync(file) || !fs.statSync(file).isFile()) {
    res.writeHead(404); res.end(); return;
  }
  const mime = { '.html': 'text/html', '.js': 'text/javascript', '.wasm': 'application/wasm', '.json': 'application/json', '.css': 'text/css', '.svg': 'image/svg+xml' };
  res.setHeader('Content-Type', mime[path.extname(file)] || 'application/octet-stream');
  fs.createReadStream(file).pipe(res);
});
(async () => {
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  const browser = await chromium.launch({ headless: true, ...(process.env.AOM_CHROME ? { executablePath: process.env.AOM_CHROME } : {}) });
  try {
    const page = await browser.newPage();
    const errors = []; page.on('pageerror', e => errors.push(e.message));
    await page.goto(`http://127.0.0.1:${server.address().port}/?selftest=1`);
    await page.waitForFunction(() => ['pass', 'fail'].includes(document.documentElement.dataset.selftest), null, { timeout: 180000 });
    const result = await page.evaluate(() => ({ selftest: document.documentElement.dataset.selftest, runtime: document.querySelector('#runtime-version').textContent }));
    assert.equal(result.selftest, 'pass');
    assert.match(result.runtime, new RegExp('^n4m ' + manifest.version.replaceAll('.', '\\.') + '(?:\\+| )'));
    assert.deepEqual(errors, []);
    console.log(JSON.stringify({ ...result, package: manifest.package, version: manifest.version, checkedAssets: Object.keys(manifest.files).length, pageErrors: errors }, null, 2));
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; }).finally(() => server.close());
