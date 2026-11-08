// Display-only probe for the shared nirs4all-ui Data section. It never starts a fit:
// the page is opened without ?selftest and no run button is clicked.
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const http = require('node:http');
const path = require('node:path');
const crypto = require('node:crypto');
const root = path.resolve(__dirname, '../demo/wasm');
const ui = path.join(root, 'assets/nirs4all-ui/browser');
const version = JSON.parse(fs.readFileSync(path.join(ui, 'VERSION.json'), 'utf8'));
for (const [name, hash] of Object.entries(version.files)) {
  assert.equal(crypto.createHash('sha256').update(fs.readFileSync(path.join(ui, name))).digest('hex'), hash, name);
}
const manifest = JSON.parse(fs.readFileSync(path.join(root, 'datasets/manifest.json'), 'utf8'));
const shown = (rows, limit) => Math.ceil(rows / Math.max(1, Math.ceil(rows / limit)));
const dims = (id, part) => {
  const lines = fs.readFileSync(path.join(root, 'datasets', id, `X${part}.csv`), 'utf8').split(/\r?\n/).filter((line) => line.trim());
  return { rows: lines.length - 1, cols: lines[0].split(',').length };
};
const server = http.createServer((req, res) => {
  const pathname = decodeURIComponent(new URL(req.url, 'http://localhost').pathname);
  const file = path.resolve(root, '.' + (pathname === '/' ? '/index.html' : pathname));
  if (!file.startsWith(root + path.sep) || !fs.existsSync(file) || !fs.statSync(file).isFile()) { res.writeHead(404); res.end(); return; }
  const mime = { '.html': 'text/html', '.js': 'text/javascript', '.wasm': 'application/wasm', '.json': 'application/json', '.css': 'text/css', '.svg': 'image/svg+xml' };
  res.setHeader('Content-Type', mime[path.extname(file)] || 'application/octet-stream');
  fs.createReadStream(file).pipe(res);
});
const csv = (rows, cols, header) => [header, ...Array.from({ length: rows }, (_, r) => Array.from({ length: cols }, (_, c) => (0.1 * r + Math.sin(c / 3 + r)).toFixed(4)).join(','))].join('\n') + '\n';
const yCsv = (rows) => 'target\n' + Array.from({ length: rows }, (_, r) => (1 + r / 3).toFixed(3)).join('\n') + '\n';
async function stats(page) {
  return page.$$eval('#dataset-preview dl > div', (nodes) => Object.fromEntries(nodes.map((n) => [n.querySelector('dt').textContent, n.querySelector('dd').textContent])));
}
async function expectExplorer(page, kind) {
  await page.waitForSelector('#spectra-explorer figure.n4q-explorer');
  assert.equal(await page.locator('#spectra-explorer figure').count(), 1, `${kind}: one explorer`);
  assert.equal(await page.locator('#dataset-preview article').count(), 1, `${kind}: one card`);
  assert.equal(await page.locator('.n4ui-b-root').count(), 2, `${kind}: two roots`);
  assert.equal(await page.locator('#spectra-chart').isHidden(), true, `${kind}: legacy plot hidden`);
  assert.equal(await page.locator('#spectra-explorer details.n4q-datatable table').count(), 1, `${kind}: band table`);
}
(async () => {
  await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
  const base = `http://127.0.0.1:${server.address().port}`;
  const browser = await chromium.launch({ headless: true, ...(process.env.AOM_CHROME ? { executablePath: process.env.AOM_CHROME } : {}) });
  const report = [];
  try {
    const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
    const errors = []; page.on('pageerror', (e) => errors.push(e.message));
    for (const dataset of manifest.datasets) {
      await page.goto(`${base}/?dataset=${dataset.id}`);
      await expectExplorer(page, dataset.id);
      const train = dims(dataset.id, 'cal'); const test = dims(dataset.id, 'val');
      const values = await stats(page);
      assert.equal(values.Calibration, `${train.rows} × ${train.cols}`);
      assert.equal(values.Validation, `${test.rows} × ${test.cols}`);
      assert.match(values['Spectral axis'], / → .* nm$/);
      assert.match(values.Response, / → /);
      const keptTrain = shown(train.rows, 28); const keptTest = shown(test.rows, 14);
      assert.equal(await page.locator('#spectra-explorer .n4q-explorer-line, #spectra-explorer .n4q-explorer-focus').count(), keptTrain + keptTest + 2, 'rows plus two means');
      assert.match(await page.textContent('#spectra-summary'), new RegExp(`Showing ${keptTrain + keptTest} of ${train.rows + test.rows} spectra rows`));
      await page.focus('#spectra-explorer svg.n4q-svg');
      await page.keyboard.press('ArrowDown');
      assert.equal(await page.locator('#spectra-explorer .n4q-explorer-focus').count(), 1, 'ArrowDown selects one series');
      await page.keyboard.press('Escape');
      assert.equal(await page.locator('#spectra-explorer .n4q-explorer-focus').count(), 0, 'Escape clears the selection');
      report.push({ dataset: dataset.id, rows: [train.rows, test.rows], cols: train.cols, plotted: keptTrain + keptTest + 2 });
    }
    // Dataset switch must remount, never duplicate.
    await page.goto(`${base}/?dataset=${manifest.datasets[0].id}`);
    await expectExplorer(page, 'switch-start');
    await page.locator('#dataset-options button').nth(1).click();
    await page.waitForFunction((label) => document.querySelector('#dataset-name').textContent === label, manifest.datasets[1].label);
    await expectExplorer(page, 'switch');
    // Local four-file upload: ascending axis uses the explorer, descending keeps the native-order plot.
    const upload = async (header) => {
      await page.setInputFiles('#x-cal-file', { name: 'Xcal.csv', mimeType: 'text/csv', buffer: Buffer.from(csv(6, 8, header)) });
      await page.setInputFiles('#y-cal-file', { name: 'Ycal.csv', mimeType: 'text/csv', buffer: Buffer.from(yCsv(6)) });
      await page.setInputFiles('#x-val-file', { name: 'Xval.csv', mimeType: 'text/csv', buffer: Buffer.from(csv(3, 8, header)) });
      await page.setInputFiles('#y-val-file', { name: 'Yval.csv', mimeType: 'text/csv', buffer: Buffer.from(yCsv(3)) });
      await page.selectOption('#upload-unit', 'nm');
      await page.click('#load-upload');
    };
    await upload('1100,1110,1120,1130,1140,1150,1160,1170');
    await page.waitForFunction(() => document.querySelector('#dataset-kind').textContent === 'Local upload');
    await expectExplorer(page, 'upload-ascending');
    assert.equal((await stats(page)).Calibration, '6 × 8');
    await upload('1170,1160,1150,1140,1130,1120,1110,1100');
    await page.waitForFunction(() => !document.querySelector('#spectra-mode-note').hidden);
    assert.equal(await page.locator('#spectra-explorer figure').count(), 0, 'descending: no explorer');
    assert.equal(await page.locator('#spectra-chart').isVisible(), true, 'descending: native-order plot');
    assert.match(await page.textContent('#spectra-mode-note'), /not strictly ascending/);
    // Layout widths, using the bundled set again.
    for (const width of [1280, 600]) {
      await page.setViewportSize({ width, height: 900 });
      await page.goto(`${base}/?dataset=${manifest.datasets[0].id}`);
      await expectExplorer(page, `width-${width}`);
      const box = await page.locator('#spectra-explorer svg.n4q-svg').boundingBox();
      assert.ok(box && box.width > 100 && box.x >= 0 && box.x + box.width <= width + 1, `explorer fits ${width}px`);
      assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1), `no horizontal overflow at ${width}px`);
    }
    assert.deepEqual(errors, []);
    console.log(JSON.stringify({ ui: version.version, checkedUiFiles: Object.keys(version.files).length, datasets: report, pageErrors: errors }, null, 2));
  } finally {
    await browser.close();
  }
})().catch((error) => { console.error(error); process.exitCode = 1; }).finally(() => server.close());
