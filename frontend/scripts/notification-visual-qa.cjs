// Validação focada, somente localhost e dados sintéticos; nunca envia push/WhatsApp real.
/* eslint-disable @typescript-eslint/no-require-imports -- Script Node CommonJS independente, não é código do bundle. */
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const assert = require('node:assert/strict');
const path = require('node:path');
const fs = require('node:fs');
const origin = process.env.NOTIFICATION_QA_ORIGIN || 'http://127.0.0.1:3035';
assert.equal(new URL(origin).hostname, '127.0.0.1');
const output = path.resolve(process.env.NOTIFICATION_QA_OUTPUT || '../.codex-tmp/notification-qa');
fs.mkdirSync(output, { recursive: true });
const definitions = [
  ['first_access', 'Primeiro acesso', 'admin', '{{cliente}} acessou {{galeria}}.'],
  ['first_selection', 'Primeira seleção', 'admin', '{{cliente}} começou a escolher em {{galeria}}.'],
  ['private_photos_ready', 'Novas fotos disponíveis', 'client', 'Novas fotos disponíveis na sua galeria.'],
  ['payment_reported', 'Pagamento informado', 'admin', '{{cliente}} informou pagamento do pedido {{pedido}}.'],
  ['payment_confirmed', 'Pagamento confirmado', 'client', 'Confirmamos o pagamento do seu pedido.'],
  ['payment_refused', 'Pagamento não localizado', 'client', 'Não localizamos seu pagamento. Confira seu pedido.'],
  ['order_delivery_ready', 'Fotos disponíveis', 'client', 'As fotos do seu pedido estão disponíveis.'],
];
const settings = definitions.map(([event_type, label, recipient, body]) => ({ event_type, label, recipient, allowed_variables: ['cliente', 'galeria', ...(event_type.startsWith('payment_') ? ['pedido'] : [])], whatsapp_enabled: true, push_enabled: true, push_title: label, push_body: body, whatsapp_body: body, version: 1 }));
(async () => {
  const browser = await chromium.launch({ headless: true, channel: process.env.NOTIFICATION_QA_BROWSER || 'msedge' });
  const results = [];
  try {
    for (const width of [390, 768, 1440]) for (const theme of ['light', 'dark']) {
      const context = await browser.newContext({ viewport: { width, height: 950 }, colorScheme: theme, serviceWorkers: 'block' });
      const page = await context.newPage();
      let settingsRequests = 0;
      await page.addInitScript(() => {
        Object.defineProperty(window, 'Notification', { value: { requestPermission: async () => 'denied' }, configurable: true });
      });
      await page.route('**/api/**', async (route) => {
        const url = new URL(route.request().url());
        if (url.pathname.startsWith('/api/admin/notification-settings')) settingsRequests += 1;
        let body = {};
        if (url.pathname === '/api/push/subscription') body = { available: true, active: false, identity: 'admin:synthetic', public_key: 'BAAA' };
        if (url.pathname === '/api/admin/notification-settings') body = { settings };
        if (url.pathname.startsWith('/api/admin/notification-settings/')) body = { ...settings.find((item) => url.pathname.endsWith(item.event_type)), ...route.request().postDataJSON(), version: 2 };
        if (url.pathname === '/api/library') body = { galleries: [], journeys: [] };
        if (url.pathname === '/api/library/purchases') body = { orders: [], journeys: [] };
        await route.fulfill({ json: body });
      });
      await page.goto(`${origin}/admin/notifications`);
      await page.getByRole('button', { name: 'Agora não', exact: true }).click();
      await page.getByRole('heading', { name: 'Primeiro acesso', exact: true }).waitFor();
      assert.equal(await page.locator('details').count(), 7);
      assert.equal(await page.locator('details[open]').count(), 0);
      assert.equal(await page.getByRole('button', { name: 'Salvar evento' }).count(), 0);
      await page.screenshot({ path: path.join(output, `recolhida-${width}-${theme}.png`), fullPage: true });
      const firstHeader = page.locator('summary').filter({ hasText: 'Primeiro acesso' });
      const initialRequests = settingsRequests;
      await firstHeader.focus(); await page.keyboard.press('Enter');
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true, `overflow ${width}/${theme}`);
      const first = page.getByRole('form', { name: 'Primeiro acesso', exact: true });
      await first.getByLabel(/Título do push/).fill('Rascunho local');
      const toggle = first.getByLabel('Enviar notificação Push');
      await toggle.focus(); await page.keyboard.press('Space');
      assert.equal(await toggle.isChecked(), false);
      await page.locator('summary').filter({ hasText: 'Novas fotos disponíveis' }).click();
      await firstHeader.click();
      assert.equal(await page.locator('details[open]').count(), 1);
      await firstHeader.focus(); await page.keyboard.press('Space');
      assert.equal(await page.locator('details[open]').count(), 2);
      assert.equal(await first.getByLabel(/Título do push/).inputValue(), 'Rascunho local');
      assert.equal(await toggle.isChecked(), false);
      assert.equal(settingsRequests, initialRequests);
      await first.getByRole('button', { name: 'Salvar evento' }).click();
      await first.getByRole('status').waitFor();
      assert.equal(settingsRequests, initialRequests + 1);
      for (const card of await page.locator('details').all()) {
        if (await card.getAttribute('open') === null) await card.locator('summary').click();
      }
      assert.equal(await page.getByRole('form').count(), 7);
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true, `expanded overflow ${width}/${theme}`);
      await page.getByRole('button', { name: 'Ativar notificações', exact: true }).click();
      await page.getByText('Notificações bloqueadas. Libere nas permissões do navegador.').waitFor();
      const file = `central-${width}-${theme}.png`;
      await page.evaluate(() => window.scrollTo(0, 0));
      await page.getByRole('heading', { name: 'Notificações', exact: true }).scrollIntoViewIfNeeded();
      await page.evaluate(() => window.scrollTo(0, 0));
      await page.screenshot({ path: path.join(output, file), fullPage: true });
      await page.goto(`${origin}/library`);
      await page.getByRole('button', { name: 'Ativar notificações', exact: true }).waitFor();
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true, `client overflow ${width}/${theme}`);
      await page.screenshot({ path: path.join(output, `cliente-${width}-${theme}.png`), fullPage: true });
      results.push({ width, theme, central: file, keyboard: 'passed', permissionDenied: 'passed', overflow: false });
      await context.close();
    }
    fs.writeFileSync(path.join(output, 'results.json'), JSON.stringify(results, null, 2));
    console.log(JSON.stringify(results));
  } finally { await browser.close(); }
})().catch((error) => { console.error(error.message); process.exitCode = 1; });
