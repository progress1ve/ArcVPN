/* Browser acceptance for the standalone node website. No VPN benchmarks. */
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');

(async () => {
  const url = process.env.SITE_URL || 'http://127.0.0.1:18772/';
  const folder = process.env.SITE_EVIDENCE_DIR || path.join(process.env.TEMP || '/tmp', 'arccnet-tools-evidence');
  fs.mkdirSync(folder, { recursive: true });
  const browser = await chromium.launch({ headless: true, channel: process.env.BROWSER_CHANNEL || 'chrome' });
  const context = await browser.newContext({ locale: 'ru-RU', reducedMotion: 'reduce' });
  const page = await context.newPage();
  const errors = [], requests = [];
  page.on('pageerror', e => errors.push(e.message));
  page.on('request', r => requests.push(r.url()));
  const evidence = [];
  try {
    for (const width of [360, 768, 1280, 1600]) {
      await page.setViewportSize({ width, height: 1000 });
      const response = await page.goto(url, { waitUntil: 'commit' });
      assert.equal(response.status(), 200);
      await page.locator('#hero-title').waitFor();
      await page.evaluate(() => document.fonts.ready);
      assert.equal(await page.title(), 'Arccnet Tools — изображения в нужном формате');
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true, 'horizontal overflow');
      assert.equal(await page.locator('#convert').isDisabled(), true);
      await page.screenshot({ path: path.join(folder, `page-${width}.png`), fullPage: true });
      evidence.push({ width, overflow: false });
      if (width === 360) {
        await page.locator('#menu').click();
        assert.equal(await page.locator('#menu').getAttribute('aria-expanded'), 'true');
        await page.locator('#navigation a').first().click();
        assert.equal(await page.locator('#menu').getAttribute('aria-expanded'), 'false');
      }
    }
    const input = page.locator('#file');
    const sample = Buffer.from(await page.evaluate(() => {
      const c = document.createElement('canvas'); c.width = 16; c.height = 12;
      const x = c.getContext('2d'); x.fillStyle = '#ff0000'; x.fillRect(0, 0, 8, 12);
      return c.toDataURL('image/png').split(',')[1];
    }), 'base64');
    await input.setInputFiles({ name: 'sample.png', mimeType: 'image/png', buffer: sample });
    await page.locator('#selected').waitFor();
    assert.equal(await page.locator('#convert').isEnabled(), true);
    const conversions = [];
    for (const mime of ['image/webp', 'image/jpeg', 'image/png']) {
      await page.locator('#format').selectOption(mime);
      assert.equal(await page.locator('#quality').isDisabled(), mime === 'image/png');
      await page.locator('#convert').click();
      await page.locator('#result').waitFor();
      const result = await page.evaluate(async () => {
        const blob = await (await fetch(document.getElementById('download').href)).blob();
        const img = await createImageBitmap(blob);
        const c = document.createElement('canvas'); c.width = img.width; c.height = img.height;
        const x = c.getContext('2d'); x.drawImage(img, 0, 0);
        return { type: blob.type, bytes: blob.size, width: img.width, height: img.height, pixel: [...x.getImageData(15, 5, 1, 1).data] };
      });
      assert.equal(result.type, mime); assert.equal(result.width, 16); assert.equal(result.height, 12);
      assert.ok(result.bytes > 0);
      if (mime === 'image/jpeg') assert.ok(result.pixel.every(v => v >= 245), 'JPEG transparent background must be white');
      else assert.equal(result.pixel[3], 0, 'PNG/WebP alpha must survive');
      const [download] = await Promise.all([page.waitForEvent('download'), page.locator('#download').click()]);
      await download.saveAs(path.join(folder, download.suggestedFilename()));
      conversions.push(result);
    }
    await page.locator('#tool').screenshot({ path: path.join(folder, 'converted.png') });
    // A settings change invalidates the old download.
    await page.locator('#format').selectOption('image/jpeg');
    assert.equal(await page.locator('#result').isVisible(), false);
    await input.setInputFiles({ name: 'bad.txt', mimeType: 'text/plain', buffer: Buffer.from('not an image') });
    await page.locator('#error').waitFor();
    assert.match(await page.locator('#error').innerText(), /PNG, JPEG или WebP/);
    assert.equal(await page.locator('#convert').isDisabled(), true);
    await input.setInputFiles({ name: 'corrupt.png', mimeType: 'image/png', buffer: Buffer.from('broken') });
    await page.waitForFunction(() => document.getElementById('error').textContent.includes('Не удалось открыть'));
    await input.setInputFiles({ name: 'too-large.png', mimeType: 'image/png', buffer: Buffer.alloc(20 * 1024 * 1024 + 1) });
    await page.waitForFunction(() => document.getElementById('error').textContent.includes('больше 20 МБ'));
    // Recover after an invalid file, and verify that a name is treated as text.
    await input.setInputFiles({ name: '<img onerror=alert(1)>.png', mimeType: 'image/png', buffer: sample });
    await page.locator('#selected').waitFor();
    assert.equal(await page.locator('#file-name img').count(), 0);
    assert.equal(await page.locator('#convert').isEnabled(), true);
    await page.locator('#faq details').first().locator('summary').focus();
    await page.keyboard.press('Enter');
    assert.equal(await page.locator('#faq details').first().getAttribute('open'), '');
    const external = requests.filter(r => /^https?:/.test(r) && new URL(r).origin !== new URL(url).origin);
    assert.deepEqual(external, [], 'site must not call external services');
    assert.deepEqual(errors, []);
    const report = { url, viewports: evidence, conversions, externalRequests: external.length, jsErrors: errors.length, invalidFiles: 'unsupported/corrupt/over20MiB rejected, recovery passed' };
    fs.writeFileSync(path.join(folder, 'report.json'), JSON.stringify(report, null, 2));
    console.log(JSON.stringify(report));
  } finally { await context.close(); await browser.close(); }
})().catch(e => { console.error(e.stack); process.exitCode = 1; });
