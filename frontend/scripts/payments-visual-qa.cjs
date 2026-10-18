// QA local com APIs sintéticas: não envia decisões, dados ou mensagens reais.
/* eslint-disable @typescript-eslint/no-require-imports */
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const origin = process.env.PAYMENTS_QA_ORIGIN || 'http://localhost:3117';
assert.ok(['localhost', '127.0.0.1'].includes(new URL(origin).hostname));
const output = path.resolve(process.env.PAYMENTS_QA_OUTPUT || '../.codex-tmp/sales-visual-qa');
fs.mkdirSync(output, { recursive: true });
const reference = '2026-10-17T12:00:00Z';
const photos = [1, 2].map(id => ({ id: `item-${id}`, photo_id: `photo-${id}`, name: `FOTO_${id}.jpg`, unit_price_cents: 700,
  thumbnail_url: `/admin/orders/order-1/items/item-${id}/preview?size=thumbnail`,
  preview_url: `/admin/orders/order-1/items/item-${id}/preview?size=preview` }));
const order = { id: 'order-1', gallery: { id: 'private', name: 'Galeria da família', removed: false }, parent_gallery: { id: 'parent', name: 'Evento sintético', removed: false },
  financial_status: 'reported', total_cents: 1400, created_at: reference, selection_expires_at: reference,
  folders: [{ id: 'folder', name: 'Cerimônia', items: photos }],
  communication: { id: 'communication', order_id: 'order-1', gallery_name: 'Galeria da família', client_name: 'Maria de Teste', created_at: reference, total_cents: 1400, status: 'pending_review', can_decide: true, can_correct: false },
  delivery: { album_url: null, version: 0, can_send: false, can_resend: false } };
const groups = [
  { client: { id: 'client-1', name: 'Maria de Teste' }, financial_status: 'reported', totals: { orders: 1, reported_orders: 1, reported_cents: 1400, confirmed_cents: 0 }, orders: [order] },
  { client: { id: 'client-2', name: 'Cliente com nome extenso para verificar quebra e leitura no celular' }, financial_status: 'confirmed_undelivered', totals: { orders: 1, reported_orders: 0, reported_cents: 0, confirmed_cents: 1400 }, orders: [{ ...order, id: 'order-2', financial_status: 'confirmed_undelivered', communication: null, delivery: { album_url: null, version: 0, can_send: true, can_resend: false } }] },
];
function dashboard(params) {
  const state = params.get('financial_status');
  const filtered = groups.filter(g => (!state || state === 'priority' || g.financial_status === state) && (!params.get('client_id') || g.client.id === params.get('client_id')));
  return { groups: filtered,
    summary: { clients: filtered.length, selected_carts: 0, selected_cents: 0, selected_pricing_unavailable: 0,
      reported_orders: filtered.reduce((sum, g) => sum + g.totals.reported_orders, 0),
      reported_cents: filtered.reduce((sum, g) => sum + g.totals.reported_cents, 0),
      confirmed_orders: filtered.filter(g => g.financial_status === 'confirmed_undelivered').length,
      confirmed_cents: filtered.reduce((sum, g) => sum + g.totals.confirmed_cents, 0) },
    facets: { parent_galleries: [{ id: 'parent', name: 'Evento sintético', count: 2 }] }, templates: { confirmed: 'Olá {{cliente}}, pagamento confirmado.', refused: 'Olá {{cliente}}, pagamento não localizado.' }, selections_without_order: [], page: { next_cursor: null, limit: 12 } };
}
const svg = '<svg xmlns="http://www.w3.org/2000/svg" width="600" height="400"><rect width="600" height="400" fill="#444"/><circle cx="300" cy="180" r="100" fill="#bbb"/><text x="100" y="350" fill="white" font-size="30">PRÉVIA SINTÉTICA</text></svg>';

(async () => {
  const browser = await chromium.launch({ headless: true, channel: process.env.PAYMENTS_QA_BROWSER || 'msedge' });
  const report = [];
  try {
    for (const width of [390, 768, 1440]) for (const theme of ['light', 'dark']) {
      const context = await browser.newContext({ viewport: { width, height: 950 }, colorScheme: theme, serviceWorkers: 'block', locale: 'pt-BR', timezoneId: 'America/Sao_Paulo' });
      const page = await context.newPage();
      const requests = []; const errors = [];
      page.on('pageerror', error => errors.push(error.message));
      await page.addInitScript(({ theme }) => { localStorage.setItem('pick-your-pic-theme', theme); localStorage.setItem('pick-your-pic-appearance-finish', 'silver'); }, { theme });
      await page.route('**/api/**', async route => {
        const url = new URL(route.request().url()); requests.push(url);
        if (url.pathname.endsWith('/preview')) return route.fulfill({ contentType: 'image/svg+xml', body: svg });
        if (url.pathname.endsWith('export.csv')) return route.fulfill({ contentType: 'text/csv; charset=utf-8', body: '\ufeffNome do cliente;Item/descrição;Total dos itens/pedido;Data e hora\r\nMaria;2 fotografias — Evento;14,00;\r\n' });
        let body = {};
        if (url.pathname.endsWith('/payment-communications')) body = dashboard(url.searchParams);
        else if (url.pathname.endsWith('/gallery-reopening-requests')) body = { requests: [] };
        else if (url.pathname.endsWith('/clients')) body = { clients: [{ id: 'client-1', name: 'Maria de Teste' }] };
        else if (url.pathname.endsWith('/auth/identity')) body = { role: 'admin', identity: 'fotografo@example.test' };
        else if (url.pathname.endsWith('/auth/destination')) body = { destination: '/admin' };
        else if (url.pathname.endsWith('/push/subscription')) body = { available: false, active: false };
        else if (url.pathname.endsWith('/removed-photo-movements')) body = { items: [], galleries: [], page: { offset: 0, limit: 25, has_more: false } };
        return route.fulfill({ json: body });
      });
      await page.goto(origin + '/admin/payments');
      await page.getByRole('heading', { name: 'Maria de Teste', exact: true }).waitFor();
      assert.equal(await page.getByRole('link', { name: 'Estatísticas', exact: true }).count(), 0);
      assert.equal(requests.filter(u => u.pathname.endsWith('/preview')).length, 0, 'pedidos fechados não carregam imagens');
      assert.equal(await page.getByLabel('Situação financeira').inputValue(), 'priority');
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true, 'sem overflow horizontal');
      await page.screenshot({ path: path.join(output, `payments-${width}-${theme}.png`), fullPage: true });
      await page.getByText('Ver pedido e entrega', { exact: true }).first().click();
      const trigger = page.getByRole('button', { name: 'Ampliar FOTO_1.jpg' }).first();
      await trigger.waitFor();
      await page.waitForFunction(() => [...document.querySelectorAll('button[aria-label^="Ampliar"] img')].every(img => img.complete && img.naturalWidth === 600));
      assert.equal(requests.filter(u => u.searchParams.get('size') === 'preview').length, 0);
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true, 'detalhes sem overflow horizontal');
      await page.evaluate(() => scrollTo(0, 0));
      await page.screenshot({ path: path.join(output, `details-${width}-${theme}.png`), fullPage: true });
      await trigger.scrollIntoViewIfNeeded();
      const scroll = await page.evaluate(() => scrollY);
      await trigger.click();
      const dialog = page.getByRole('dialog'); await dialog.waitFor();
      assert.equal(await dialog.evaluate(node => node.matches(':modal')), true);
      await page.waitForFunction(() => document.querySelector('dialog img')?.naturalWidth === 600);
      assert.equal(await dialog.locator('img').count(), 1);
      assert.equal(requests.filter(u => u.searchParams.get('size') === 'preview').length, 1);
      assert.equal(await dialog.evaluate(node => node.contains(document.activeElement)), true);
      await page.keyboard.press('Shift+Tab');
      assert.equal(await dialog.evaluate(node => node.contains(document.activeElement)), true);
      await page.screenshot({ path: path.join(output, `lightbox-${width}-${theme}.png`) });
      await page.keyboard.press('ArrowRight');
      await dialog.getByText('FOTO_2.jpg', { exact: true }).waitFor();
      await page.keyboard.press('Escape');
      assert.equal(await dialog.count(), 0);
      assert.equal(await trigger.evaluate(node => document.activeElement === node), true);
      assert.ok(Math.abs(await page.evaluate(() => scrollY) - scroll) < 2);
      assert.equal(await page.getByText('Ver pedido e entrega', { exact: true }).first().evaluate(node => node.parentElement.open), true);
      await trigger.click();
      await page.getByRole('button', { name: 'Fechar fotografia', exact: true }).click();
      assert.equal(await dialog.count(), 0);
      await trigger.click();
      await page.mouse.click(2, 2);
      assert.equal(await dialog.count(), 0, 'clique fora do conteúdo fecha');
      const downloadPromise = page.waitForEvent('download');
      await page.getByRole('button', { name: 'Exportar CSV', exact: true }).click();
      const download = await downloadPromise;
      assert.equal(download.suggestedFilename(), 'pick-your-pic-vendas-pagamentos.csv');
      const exported = requests.find(u => u.pathname.endsWith('export.csv'));
      assert.equal(exported.searchParams.get('financial_status'), 'priority');
      assert.equal(exported.searchParams.has('cursor'), false);
      await page.getByLabel('Cliente / telefone').fill('Ma');
      await page.getByRole('option', { name: 'Maria de Teste', exact: true }).click();
      await page.waitForFunction(() => !document.body.textContent.includes('Atualizando resultados…'));
      assert.equal(requests.filter(u => u.pathname.endsWith('/payment-communications') && u.searchParams.get('client_id') === 'client-1').length, 1);
      await page.getByLabel('Exibir', { exact: false }).selectOption('removed');
      await page.getByText('Nenhum movimento neste filtro', { exact: true }).waitFor();
      const retired = await page.goto(origin + '/admin/statistics');
      assert.equal(retired.status(), 404);
      assert.deepEqual(errors, []);
      report.push({ width, theme, result: 'passed' });
      await context.close();
    }
    fs.writeFileSync(path.join(output, 'report.json'), JSON.stringify(report, null, 2));
    console.log(JSON.stringify(report));
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
