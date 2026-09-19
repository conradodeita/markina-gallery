// QA local com fixtures sintéticas. Nenhuma decisão ou mensagem real é enviada.
/* eslint-disable @typescript-eslint/no-require-imports */
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const origin = process.env.PURCHASE_QA_ORIGIN || 'http://127.0.0.1:3106';
assert.equal(new URL(origin).hostname, '127.0.0.1');
const output = path.resolve(process.env.PURCHASE_QA_OUTPUT || '../.codex-tmp/purchase-flow-qa');
fs.mkdirSync(output, { recursive: true });
const deadline = new Date(Date.now() + 3 * 86400000).toISOString();
const item = (id) => ({ photo_id: `photo-${id}`, name: `FOTO_${id}.jpg`, preview_url: id % 2 ? `/gallery/private/photos/photo-${id}/preview` : `/library/history/items/item-${id}/preview`, delivery_url: null, delivery_reference_available: false });
const purchase = { id: 'purchase', gallery_name: 'Fotos da família', parent_gallery_name: 'Evento de teste', gallery_removed: false, commercial_state: 'purchased', confirmed_at: '2026-09-19T12:00:00Z', total_cents: 2800, items: [0, 1, 2, 3].map(item) };
const pending = { id: 'communication-1', order_id: 'order-1', gallery_name: 'Fotos da família', total_cents: 700, quantity: 1, created_at: '2026-09-19T12:00:00Z', status: 'pending_review', can_decide: true, can_correct: false };
const older = { ...pending, id: 'communication-2', order_id: 'order-2', quantity: 3, total_cents: 2100, created_at: '2026-09-18T12:00:00Z' };
const confirmed = { ...pending, id: 'communication-3', order_id: 'order-3', status: 'confirmed', can_decide: false, can_correct: true };
const privateGallery = { id: 'private', name: 'Fotos da família', parent_gallery_id: 'public', selection_expires_at: deadline, gallery_status: 'active', frozen: false, blocked: false, origin_removed: false, origin: { id: 'public', name: 'Evento', available: true }, folders: [] };
const journey = { id: 'public', name: 'Evento de teste', event_name: 'Fotos da família', status: 'active', primary_surface: 'public', public_gallery: null, private_gallery: privateGallery, selection: { quantity: 0 }, orders: [{ order_id: 'purchase', commercial_state: 'purchased', total_cents: 2800 }], actions: { continue_url: '/public-galleries/public', review_url: null } };
const svg = '<svg xmlns="http://www.w3.org/2000/svg" width="600" height="400"><rect width="600" height="400" fill="#435263"/><circle cx="300" cy="170" r="100" fill="#f2c343"/><text x="100" y="350" font-size="32" fill="white">PRÉVIA SINTÉTICA PROTEGIDA</text></svg>';

(async () => {
  const browser = await chromium.launch({ headless: true, channel: process.env.PURCHASE_QA_BROWSER || 'msedge' });
  const report = [];
  try {
    for (const width of [390, 768, 1440]) for (const theme of ['light', 'dark']) {
      const context = await browser.newContext({ viewport: { width, height: 950 }, colorScheme: theme, serviceWorkers: 'block' });
      const page = await context.newPage();
      const errors = []; page.on('pageerror', (error) => errors.push(error.message));
      let state = { ...pending };
      let posts = 0;
      function clientCard() { return { client_id: 'client', name: 'Cliente de teste', phone: '+5500000000000', derived_gallery_id: 'private', gallery_status: 'active', commercial_status: state.can_decide ? 'pending_review' : 'paid', available_count: 8, selected_count: state.can_decide ? 4 : 3, purchased_count: state.can_decide ? 1 : 2, selection_expires_at: deadline, financial_orders: [state, older, confirmed] }; }
      await page.route('**/api/**', async (route) => {
        const p = new URL(route.request().url()).pathname;
        if (p.endsWith('/preview')) return route.fulfill({ contentType: 'image/svg+xml', body: svg });
        let body = {};
        if (p === '/api/library') body = { journeys: [journey] };
        else if (p === '/api/library/purchases') body = { orders: [purchase, { ...purchase, id: 'reported', commercial_state: 'payment_reported', confirmed_at: null }] };
        else if (p === '/api/push/subscription') body = { available: false, active: false };
        else if (p.endsWith('/decision')) { posts++; state = { ...state, status: 'confirmed', can_decide: false, can_correct: true }; body = { status: 'confirmed' }; }
        else if (p.endsWith('/summary')) body = { name: 'Evento de teste', event_name: 'Fotografias', active: true, counts: { folders: 0, photos: 8, clients: 1 }, clients: [clientCard()] };
        else if (p.endsWith('/members')) body = { members: [{ ...clientCard(), membership_id: 'member', client_name: 'Cliente de teste', phone_e164: '+5500000000000', status: 'active', order_count: 3, confirmed_total_cents: 700 }] };
        else if (p.endsWith('/folders')) body = { folders: [] };
        else if (p.endsWith('/photos')) body = { photos: [] };
        else if (p.endsWith('/upload-batches')) body = { batches: [] };
        else if (p.endsWith('/facial-index')) body = { state: 'completed', progress: { ready: 8, total: 8 }, coverage: { percent: 100 } };
        else if (p.endsWith('/derived-galleries/private')) body = privateGallery;
        else if (p.endsWith('/payment-message-templates')) body = { templates: { confirmed: 'Pagamento confirmado: {{pedido}}.', refused: 'Pagamento não localizado: {{pedido}}.' } };
        return route.fulfill({ json: body });
      });
      await page.goto(`${origin}/library`);
      await page.getByRole('button', { name: 'Ver fotos (4)' }).first().click();
      const images = page.locator('.library-order-photo-grid img');
      await images.first().waitFor();
      await page.waitForFunction(() => [...document.querySelectorAll('.library-order-photo-grid img')].every((image) => image.complete && image.naturalWidth === 600));
      assert.equal(await images.count(), 4);
      assert.equal(await page.locator('.library-order-photo-grid').evaluate((grid) => getComputedStyle(grid).gridTemplateColumns.split(' ').length), width < 700 ? 2 : 4);
      assert.ok(await page.getByLabel('Prazo para novas seleções').count());
      const brokenOldPath = await page.evaluate(() => new Promise((resolve) => { const image = new Image(); image.onload = () => resolve(image.naturalWidth); image.onerror = () => resolve(0); image.src = '/library/history/items/item-0/preview'; }));
      assert.equal(brokenOldPath, 0, 'Reprodução: caminho antigo sem /api não é uma imagem');
      await page.screenshot({ path: path.join(output, `library-${width}-${theme}.png`), fullPage: true });
      await page.getByRole('button', { name: 'Ampliar prévia protegida de FOTO_0.jpg' }).press('Enter');
      await page.getByRole('dialog').waitFor();
      assert.equal(await page.getByRole('dialog').evaluate((node) => document.activeElement === node), true);
      await page.waitForFunction(() => document.querySelector('.library-photo-dialog img')?.naturalWidth === 600);
      await page.keyboard.press('Escape');
      assert.equal(await page.getByRole('dialog').count(), 0);
      for (const [name, url] of [['public', '/admin/galleries/sources/public'], ['private', '/admin/galleries/private']]) {
        await page.goto(origin + url);
        const payment = page.getByRole('region', { name: 'Pedido order-1', exact: true });
        await payment.waitFor();
        assert.equal(await page.getByRole('region', { name: 'Pedido order-2', exact: true }).count(), 1);
        await page.getByText('Prévia das mensagens globais', { exact: true }).click();
        await page.getByText('Confirmado: Pagamento confirmado: {{pedido}}.', { exact: true }).waitFor();
        await payment.scrollIntoViewIfNeeded();
        const overflow = await page.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1);
        assert.equal(overflow, false, `${name} ${width} ${theme}`);
        await page.screenshot({ path: path.join(output, `${name}-${width}-${theme}.png`), fullPage: true });
        if (name === 'public') {
          page.once('dialog', async (dialog) => { assert.ok(dialog.message().includes('order-1')); await dialog.accept(); });
          await payment.getByRole('button', { name: 'Confirmar pagamento', exact: true }).press('Enter');
          await payment.getByRole('button', { name: 'Corrigir confirmação', exact: true }).waitFor();
          assert.equal(posts, 1);
          assert.equal(await page.getByRole('region', { name: 'Pedido order-2', exact: true }).getByRole('button', { name: 'Confirmar pagamento' }).count(), 1);
        }
      }
      assert.deepEqual(errors, []);
      report.push({ width, theme, imageDecoded: true, wrongPathRejected: true, orderIsolated: true, overflow: false });
      await context.close();
    }
  } finally { await browser.close(); }
  console.log(JSON.stringify(report, null, 2));
})().catch((error) => { console.error(error); process.exitCode = 1; });
