// QA local do editor real; todas as APIs e imagens são sintéticas.
/* eslint-disable @typescript-eslint/no-require-imports */
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const origin = process.env.FOLDER_QA_ORIGIN || 'http://127.0.0.1:3036';
assert.equal(new URL(origin).hostname, '127.0.0.1');
const output = process.env.FOLDER_QA_OUTPUT || path.join(os.tmpdir(), 'pick-your-pic-folder-photo-qa');
fs.mkdirSync(output, { recursive: true });
const longName = '27f58b6e8c51377753'.repeat(6) + '.jpeg';
const photo = (id, name) => ({ id, name, preview_url: `/synthetic/${id}.svg`, status: 'completed', publication_state: 'published', error: null, can_delete: true, is_cover: false });
const shortPhotos = [photo('short', 'FOTO_001.jpg')];
const longPhotos = [photo('portrait', longName), photo('landscape', '2cd861cbf0f58ba2cf79'.repeat(6) + '.jpeg'), photo('square', 'FOTO_003.jpg')];
const folders = ['Primeira pasta', 'Segunda pasta'].map((name, index) => ({ id: `folder-${index + 1}`, name, status: 'released', position: index, photo_count: index ? 3 : 1, preview_url: null, released_at: null }));
const editor = {
  gallery: { id: 'source-qa', name: 'Galeria sintética', active: true, access_mode: 'invite_only', folder_display_mode: 'individual' },
  steps: ['ajustes', 'vendas', 'detalhes', 'imagens', 'clientes'].map((id) => ({ id, label: id, available: true, status: 'complete' })),
  counts: { folders: 2, registrations: 0, derived_galleries: 0 },
  capabilities: { sales_configuration: true, visual_customization: true, folder_management: true, client_links: true },
  actions: { can_create_folder: true, can_upload: true },
};

(async () => {
  const browser = await chromium.launch({ headless: true, channel: process.env.FOLDER_QA_BROWSER || 'msedge' });
  const results = [];
  let diagnosticPage;
  try {
    for (const width of [320, 360, 390, 768, 1440]) for (const theme of ['light', 'dark']) {
      const context = await browser.newContext({ viewport: { width, height: 950 }, colorScheme: theme, serviceWorkers: 'block' });
      const page = await context.newPage();
      diagnosticPage = page;
      const writes = [];
      const errors = [];
      page.on('pageerror', (error) => { errors.push(error.message); console.error(error.message); });
      await page.route('**/api/**', async (route) => {
        const request = route.request();
        const p = new URL(request.url()).pathname;
        if (request.method() !== 'GET') {
          writes.push({ path: p, method: request.method() });
          return route.fulfill({ status: 405, json: { detail: 'Somente leitura neste QA' } });
        }
        if (p.startsWith('/api/synthetic/')) {
          const [w, h] = p.includes('portrait') ? [400, 600] : p.includes('landscape') ? [600, 400] : [400, 400];
          return route.fulfill({ contentType: 'image/svg+xml', body: `<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}"><rect width="100%" height="100%" fill="#456"/><circle cx="${w / 2}" cy="${h / 2}" r="100" fill="#f2c343"/></svg>` });
        }
        let body = {};
        if (p.endsWith('/editor')) body = editor;
        else if (p.endsWith('/folders')) body = { folders };
        else if (p.endsWith('/photos')) body = { photos: p.includes('folder-2') ? longPhotos : shortPhotos };
        else if (p === '/api/push/subscription') body = { available: false, active: false };
        else if (p.endsWith('/configuration')) body = { enabled: false, strength: 50, generation: 0, exposure_tenths: 0 };
        else if (p.startsWith('/api/admin/preview-adjustment/galleries/')) body = { counts: { queued: 0, processing: 0, ready: 0, failed: 0, cancelled: 0 }, photos: [], next_cursor: null };
        await route.fulfill({ json: body });
      });
      await page.goto(`${origin}/admin/galleries/sources/source-qa/edit/imagens`);
      await page.getByRole('button', { name: 'Abrir pasta Primeira pasta', exact: true }).click();
      await page.locator('.folder-photo-grid article').first().waitFor();
      assert.equal(await page.locator('.folder-photo-grid > article > strong').first().textContent(), 'FOTO_001.jpg');
      await page.getByRole('button', { name: 'Abrir pasta Segunda pasta', exact: true }).click();
      await page.getByRole('button', { name: `Ampliar ${longName}`, exact: true }).waitFor();
      await page.waitForFunction(() => [...document.querySelectorAll('.folder-photo-grid img')].every((img) => img.complete && img.naturalWidth > 0));
      const measure = () => page.locator('.folder-photo-grid').evaluate((grid) => {
        const bounds = grid.getBoundingClientRect();
        const cards = [...grid.querySelectorAll('article')].map((card) => {
          const box = card.getBoundingClientRect();
          return {
            width: box.width,
            withinGrid: box.left >= bounds.left - 1 && box.right <= bounds.right + 1,
            contentsFit: card.scrollWidth <= card.clientWidth + 1,
            childrenFit: [...card.querySelectorAll('img, strong, small, button, label')].every((child) => {
              const rect = child.getBoundingClientRect();
              return rect.left >= box.left - 1 && rect.right <= box.right + 1 && child.scrollWidth <= child.clientWidth + 1;
            }),
          };
        });
        return { documentFits: document.documentElement.scrollWidth <= innerWidth + 1, cards };
      });
      const metrics = await measure();
      console.log(JSON.stringify({ width, theme, ...metrics }));
      await page.locator('.folder-photo-grid').screenshot({ path: path.join(output, `${width}-${theme}.png`) });
      const first = page.locator('.folder-photo-grid article').first();
      await first.getByRole('checkbox').check();
      assert.equal(await first.getByRole('checkbox').isChecked(), true);
      await first.getByRole('button', { name: `Ampliar ${longName}`, exact: true }).click();
      await page.getByRole('dialog', { name: `Prévia ampliada de ${longName}`, exact: true }).waitFor();
      await page.getByRole('button', { name: 'Fechar', exact: true }).click();
      assert.equal(await first.getByRole('checkbox').isChecked(), true);
      assert.deepEqual(writes, []);
      assert.deepEqual(errors, []);
      results.push({ width, theme, ...metrics, selectionAndPreview: true, mutations: writes.length });
      await context.close();
    }
    fs.writeFileSync(path.join(output, 'results.json'), JSON.stringify(results, null, 2));
    console.log(JSON.stringify(results));
    const failures = results.filter((result) => !result.documentFits || result.cards.some((card) => !card.withinGrid || !card.contentsFit || !card.childrenFit));
    assert.equal(failures.length, 0, `Overflow em ${failures.map(({ width, theme }) => `${width}/${theme}`).join(', ')}`);
  } catch (error) {
    if (diagnosticPage && !diagnosticPage.isClosed()) {
      console.error((await diagnosticPage.locator('body').innerText()).slice(0, 3000));
      await diagnosticPage.screenshot({ path: path.join(output, 'failure.png') });
    }
    throw error;
  } finally {
    await browser.close();
  }
})().catch((error) => { console.error(error); process.exitCode = 1; });
