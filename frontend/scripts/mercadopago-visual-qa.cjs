// Matriz local com APIs e SDK sintéticos. Nunca tokeniza cartão nem chama o provedor.
/* eslint-disable @typescript-eslint/no-require-imports */
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const origin = process.env.MP_QA_ORIGIN || 'http://127.0.0.1:3117';
assert.equal(new URL(origin).hostname, '127.0.0.1');
const output = path.resolve(process.env.MP_QA_OUTPUT || '../.codex-tmp/mercadopago-visual');
fs.mkdirSync(output, { recursive: true });
const id = '11111111-1111-4111-8111-111111111111';
const cart = { quantity: 2, can_prepare: true, mercadopago_available: true, pix_available: false,
  total_cents: 1400, cart_revision: 'a'.repeat(64),
  groups: [{ gallery_id: 'gallery', parent_gallery_id: 'parent', name: 'Festa da escola',
    payment_required: true, quantity: 2, total_cents: 1400, error: null,
    browse_url: '/library', items: [{ id: 'p1', name: 'FOTO_01.jpg' }, { id: 'p2', name: 'FOTO_02.jpg' }] }] };
const base = { id, provider: 'mercadopago', state: 'prepared', active: true, total_cents: 1400,
  method: 'credit_card', cart_revision: 'a'.repeat(64), public_key: 'APP_USR-public-synthetic',
  can_cancel: true, test_account: true, items: [] };
const sdk = `window.MercadoPago = function () {
  return { bricks: function () { return { create: async function (type, id, settings) {
    const host = document.getElementById(id);
    host.innerHTML = '<div style="padding:20px;border:1px solid #888;border-radius:10px"><p>Campos seguros do cartão (simulação local)</p><button type="button" style="padding:14px;width:100%">Pagar com cartão</button></div>';
    host.querySelector('button').onclick = () => settings.callbacks.onSubmit({
      token: 'single-use-synthetic', payment_method_id: 'visa',
      payer: { email: 'buyer@testuser.test', identification: { type: 'CPF', number: '12345678909' } }
    }, { paymentTypeId: 'credit_card' });
    settings.callbacks.onReady();
    return { unmount: async () => { host.innerHTML = ''; } };
  } }; } };
};`;

(async () => {
  const browser = await chromium.launch({ headless: true, channel: 'msedge' });
  const report = [];
  try {
    for (const width of [390, 768, 1440]) for (const theme of ['light', 'dark']) {
      const context = await browser.newContext({ viewport: { width, height: 950 },
        colorScheme: theme, locale: 'pt-BR', serviceWorkers: 'block' });
      const page = await context.newPage();
      page.setDefaultTimeout(60000);
      const errors = []; page.on('pageerror', e => errors.push(e.message));
      let payment = null; let submits = 0; let role = 'client'; let sdkBlocked = false;
      await page.addInitScript(theme => localStorage.setItem('pick-your-pic-theme', theme), theme);
      await page.route('**/*', async route => {
        const url = new URL(route.request().url());
        if (url.hostname === 'sdk.mercadopago.com') return sdkBlocked ? route.abort() : route.fulfill({ contentType: 'application/javascript', body: sdk });
        if (url.origin !== origin) return route.abort();
        if (!url.pathname.startsWith('/api/')) return route.continue();
        let body = {};
        if (url.pathname.endsWith('/auth/identity')) body = { role, identity: role === 'admin' ? 'fotografo@example.test' : '+55 11 99999-0000' };
        else if (url.pathname.endsWith('/auth/destination')) body = { destination: role === 'admin' ? '/admin' : '/library' };
        else if (url.pathname.endsWith('/push/subscription')) body = { available: false, active: false };
        else if (url.pathname.endsWith('/library/cart')) body = cart;
        else if (url.pathname.endsWith('/mercadopago/active')) body = { payment };
        else if (url.pathname.endsWith('/mercadopago/prepare')) {
          const input = route.request().postDataJSON();
          payment = { ...base, method: input.method }; body = payment;
        } else if (url.pathname.endsWith('/submit')) {
          const input = route.request().postDataJSON();
          assert.equal(input.total_amount, undefined); assert.equal(input.tenant_id, undefined);
          submits++; payment = { ...payment, state: 'pending', pix_copy_paste: payment.method === 'pix' ? 'PIX-SINTETICO' : null };
          body = payment;
        } else if (url.pathname.includes('/library/mercadopago/')) body = payment;
        else if (url.pathname.endsWith('/library/purchases')) body = {
          orders: [], payment_groups: [], provider_payment_groups: [],
          mercadopago_payment_groups: [{ ...base, method: 'pix', state: 'partially_refunded', active: false, orders: [] }],
        };
        else if (url.pathname.endsWith('/gallery-reopening-requests')) body = { requests: [] };
        else if (url.pathname.endsWith('/payment-communications')) body = {
          summary: { clients: 1, selected_carts: 0, selected_cents: 0, selected_pricing_unavailable: 0,
            reported_orders: 0, reported_cents: 0, confirmed_orders: 0, confirmed_cents: 0 },
          facets: { parent_galleries: [] }, templates: { confirmed: 'Confirmado', refused: 'Recusado' },
          selections_without_order: [], page: { next_cursor: null, limit: 12 },
          groups: [{ client: { id: 'client', name: 'Cliente de teste' }, financial_status: 'partially_refunded',
            totals: { orders: 1, reported_orders: 0, reported_cents: 0, confirmed_orders: 0, confirmed_cents: 0 },
            orders: [{ id: 'order', parent_gallery: { id: 'parent', name: 'Festa da escola', removed: false },
              gallery: { id: 'gallery', name: 'Galeria da família', removed: false }, total_cents: 1400,
              financial_status: 'partially_refunded', payment_provider: 'mercadopago', payment_method: 'pix',
              payment_status: 'pending', mercadopago: { ...base, state: 'partially_refunded', method: 'pix',
                provider_order_id: 'ORDSYNTHETIC', provider_payment_id: 'PAYSYNTHETIC',
                order_status: 'processed', order_detail: 'partially_refunded',
                transaction_status: 'processed', transaction_detail: 'partially_refunded' },
              created_at: '2026-10-24T12:00:00Z', selection_expires_at: null, communications: [],
              communication: null, delivery_statuses: [], folders: [],
              delivery: { album_url: null, version: 1, can_send: false, can_resend: false } }] }],
        };
        return route.fulfill({ json: body });
      });
      async function capture(name) {
        await page.evaluate(() => document.fonts.ready);
        assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), true, name + ': overflow');
        await page.screenshot({ path: path.join(output, `${name}-${width}-${theme}.png`), fullPage: true });
      }
      await page.goto(origin + '/library/checkout');
      await page.getByRole('button', { name: 'Pagar com cartão', exact: true }).waitFor();
      await capture('card');
      await page.getByRole('radio', { name: 'PIX Mercado Pago', exact: true }).click();
      await page.getByLabel('E-mail para o pagamento').fill('buyer@testuser.test');
      await page.getByLabel('CPF do pagador').fill('12345678909');
      await page.getByRole('button', { name: 'Gerar PIX', exact: true }).click();
      await page.getByRole('heading', { name: 'Aguardando pagamento', exact: true }).waitFor();
      assert.equal(submits, 1);
      await capture('pix-pending');
      await page.goto(origin + '/library/purchases');
      await page.getByText('Pagamento parcialmente reembolsado', { exact: true }).waitFor();
      await capture('purchases');
      role = 'admin';
      await page.goto(origin + '/admin/payments');
      await page.getByText('Ver pedido e entrega', { exact: true }).click();
      await page.getByText('ORDSYNTHETIC', { exact: true }).waitFor();
      await capture('admin');
      assert.equal(await page.getByRole('button', { name: /Confirmar pagamento/i }).count(), 0);
      if (width === 390 && theme === 'light') {
        payment = null; role = 'client'; sdkBlocked = true;
        await page.goto(origin + '/library/checkout');
        await page.getByText('Não foi possível carregar os campos seguros. Confira sua conexão e atualize.', { exact: true }).waitFor();
        await capture('sdk-error');
      }
      assert.deepEqual(errors, []);
      report.push({ width, theme, scenarios: 4, javascriptErrors: errors.length });
      await context.close();
    }
    fs.writeFileSync(path.join(output, 'report.json'), JSON.stringify(report, null, 2));
    process.stdout.write(JSON.stringify({ passed: report.length, output }) + '\n');
  } finally { await browser.close(); }
})().catch(error => { process.stderr.write(error.stack + '\n'); process.exitCode = 1; });
