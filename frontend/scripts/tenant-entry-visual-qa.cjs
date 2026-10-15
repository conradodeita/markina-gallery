// QA de componente: todas as APIs são sintéticas. Não executa o piloto 7.3,
// não autentica contas reais, não envia OTP e não usa banco/canais/monitor.
/* eslint-disable @typescript-eslint/no-require-imports */
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const assert = require('node:assert/strict');
const path = require('node:path');
const fs = require('node:fs');
const os = require('node:os');
const origin = process.env.TENANT_ENTRY_QA_ORIGIN || 'http://127.0.0.1:3037';
assert.equal(new URL(origin).hostname, '127.0.0.1');
const output = path.resolve(process.env.TENANT_ENTRY_QA_OUTPUT || path.join(os.tmpdir(), 'pyp-tenant-entry-qa'));
fs.mkdirSync(output, { recursive: true });

(async () => {
  const browser = await chromium.launch({ headless: true, channel: 'msedge' });
  const results = [];
  try {
    for (const width of [390, 768]) {
      for (const owner of ['A', 'B']) {
        const context = await browser.newContext({ viewport: { width, height: 844 } });
        const page = await context.newPage();
        const requests = [];
        const token = `synthetic-${owner}-link-with-more-than-32-characters`;
        const hydrationErrors = [];
        page.on('pageerror', error => hydrationErrors.push(error.message));
        await page.route('**/api/**', route => {
          const url = new URL(route.request().url());
          const body = route.request().postDataJSON();
          requests.push({ path: url.pathname, body });
          let status = 403;
          let json = { detail: 'Acesso negado.' };
          if (url.pathname.endsWith('/client/challenge')) {
            assert.equal(body.access_token, token);
            status = 202;
            json = { challenge_id: `synthetic-${owner}-challenge`, message: 'Código solicitado.' };
          } else if (url.pathname.endsWith('/client/resend')) {
            assert.equal(body.access_token, token);
            status = 202;
            json = { message: 'Novo código solicitado.' };
          } else if (url.pathname.endsWith('/client/verify')) {
            assert.equal(body.access_token, token);
            assert.equal(body.challenge_id, `synthetic-${owner}-challenge`);
            assert.equal(body.code, '123456');
            status = 401;
          }
          return route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(json) });
        });
        await page.goto(`${origin}/?access_token=${token}`, { waitUntil: 'networkidle' });
        await page.getByLabel('Nome completo', { exact: true }).fill(`Cliente sintética ${owner}`);
        await page.getByLabel('Nome completo', { exact: true }).press('Tab');
        await page.getByLabel('WhatsApp', { exact: true }).fill('11999990001');
        await page.getByLabel('WhatsApp', { exact: true }).press('Tab');
        await page.getByRole('button', { name: 'Receber código', exact: true }).press('Enter');
        const code = page.getByLabel('Código enviado por WhatsApp', { exact: true });
        await code.waitFor();
        assert.equal(await code.evaluate(element => element === document.activeElement), true);
        await page.getByRole('button', { name: 'Reenviar código', exact: true }).click();
        await page.getByText('Novo código solicitado.', { exact: true }).waitFor();
        await code.fill('123456');
        await code.press('Enter');
        await page.getByText('O código expirou ou não pôde ser validado. Solicite outro e tente novamente.', { exact: true }).waitFor();
        assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
        assert.equal(await page.evaluate(() => Object.keys(localStorage).some(key => /tenant|token|otp|challenge/i.test(key))), false);
        assert.deepEqual(hydrationErrors, []);
        const screenshot = path.join(output, `entry-${owner}-${width}.png`);
        await page.screenshot({ path: screenshot, fullPage: true });
        results.push({ width, owner, keyboard: 'passed', overflow: false, hydration: 'passed',
                       challenge: requests.some(row => row.path.endsWith('/client/challenge')),
                       verify: requests.some(row => row.path.endsWith('/client/verify')), screenshot });
        await context.close();
      }
    }
    const context = await browser.newContext({ viewport: { width: 390, height: 844 } });
    const page = await context.newPage();
    const paths = [];
    await page.route('**/api/**', route => {
      paths.push(new URL(route.request().url()).pathname);
      return route.fulfill({ status: 403, contentType: 'application/json', body: '{}' });
    });
    await page.goto(origin, { waitUntil: 'networkidle' });
    await page.getByRole('heading', { name: 'Abra o link do seu fotógrafo' }).waitFor();
    assert.equal(await page.getByLabel('WhatsApp', { exact: true }).count(), 0);
    assert.equal(paths.some(value => value.includes('/client/challenge')), false);
    await page.getByRole('tab', { name: 'Fotógrafo', exact: true }).press('Enter');
    await page.getByLabel('E-mail', { exact: true }).waitFor();
    await context.close();
    fs.writeFileSync(path.join(output, 'results.json'), JSON.stringify({ scope: 'component-only-mocked-apis', results, genericEntry: 'passed' }, null, 2));
    console.log(JSON.stringify({ output, cases: results.length + 1, status: 'passed' }));
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
