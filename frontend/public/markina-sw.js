/* Sem CacheStorage: nenhum HTML privado, foto, token ou resposta de API é persistido. */
self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (event) => event.waitUntil(self.clients.claim()));

function allowedPushPath(path) {
  if (typeof path === "string" && /^\/library\/purchases(?:#order-[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})?$/.test(path)) return true;
  return typeof path === "string" && /^\/(?:admin(?:\/payments|\/galleries\/[0-9a-f-]{36}|\/galleries\/sources\/[0-9a-f-]{36}\/edit\/imagens)?|library|gallery\/[0-9a-f-]{36}|public-galleries\/[0-9a-f-]{36})$/.test(path);
}

self.addEventListener("push", (event) => {
  let payload;
  try { payload = event.data?.json(); } catch { return; }
  if (!payload || typeof payload.id !== "string" || !/^[0-9a-f-]{36}$/.test(payload.id)
    || typeof payload.title !== "string" || !payload.title || payload.title.length > 60
    || typeof payload.body !== "string" || !payload.body || payload.body.length > 140
    || !allowedPushPath(payload.path)) return;
  event.waitUntil(self.registration.showNotification(payload.title, {
    body: payload.body, tag: `pick-event-${payload.id}`, renotify: false,
    icon: "/api/branding/app-icon?size=192", badge: "/api/branding/app-icon?size=192",
    data: { path: payload.path },
  }));
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const path = event.notification.data?.path;
  if (!allowedPushPath(path)) return;
  event.waitUntil((async () => {
    const destination = new URL(path, self.location.origin).href;
    const tabs = await self.clients.matchAll({ type: "window", includeUncontrolled: true });
    const existing = tabs.find((tab) => new URL(tab.url).origin === self.location.origin);
    if (existing) {
      await existing.navigate(destination);
      await existing.focus();
    } else { await self.clients.openWindow(destination); }
  })());
});

self.addEventListener("message", (event) => {
  if (event.data?.type !== "CLEAR_PUSH_NOTIFICATIONS") return;
  if (!event.source?.url || new URL(event.source.url).origin !== self.location.origin) return;
  event.waitUntil(self.registration.getNotifications().then((notifications) => {
    notifications.forEach((notification) => notification.close());
  }));
});
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
