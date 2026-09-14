/* Sem CacheStorage: nenhum HTML privado, foto, token ou resposta de API é persistido. */
self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (event) => event.waitUntil(self.clients.claim()));
self.addEventListener("fetch", (event) => {
  const request = event.request;
  const url = new URL(request.url);
  if (request.method !== "GET" || request.mode !== "navigate" || url.origin !== self.location.origin
    || url.pathname.startsWith("/api/") || url.pathname === "/api") return;
  event.respondWith(fetch(request).catch(() => new Response(
    '<!doctype html><html lang="pt-BR"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Sem conexão · Pick-your-Pic</title><style>body{font:18px system-ui;background:#f3f4f5;color:#24221d;margin:0;padding:12vh 24px}main{max-width:440px;margin:auto}a{display:inline-block;padding:12px 20px;background:#f2c343;color:#24221d;border-radius:12px;text-decoration:none}</style><main><p>Pick-your-Pic</p><h1>Você está sem conexão</h1><p>Conecte-se à internet para continuar.</p><a href="/">Tentar novamente</a></main></html>',
    { status: 503, headers: { "Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-store", "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'" } },
  )));
});
