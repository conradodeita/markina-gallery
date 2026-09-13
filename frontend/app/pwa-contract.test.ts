import { readFileSync } from "node:fs";
import { join } from "node:path";
import vm from "node:vm";
import { expect, it, vi } from "vitest";
import manifest from "./manifest";

it("publica identidade neutra sem links privados e ícones adequados", () => {
  const value = manifest();
  expect(value.start_url).toBe("/");
  expect(value.scope).toBe("/");
  expect(value.display).toBe("standalone");
  expect(value.icons?.map((icon) => icon.sizes)).toEqual(["192x192", "512x512"]);
  expect(value.icons?.map((icon) => icon.src)).toEqual(["/api/branding/app-icon?size=192", "/api/branding/app-icon?size=512"]);
  const layout = readFileSync(join(process.cwd(), "app/layout.tsx"), "utf8");
  expect(layout).toContain('apple: "/api/branding/app-icon?size=180"');
  expect(layout).toContain('icon: "/api/branding/favicon"');
  expect(value.background_color).toBe("#f3f4f5");
});

it("não intercepta API/fotos e responde offline sem armazenar dados privados", async () => {
  const handlers:Record<string, (event:unknown) => void> = {};
  const fetch = vi.fn().mockRejectedValue(new Error("offline"));
  const script = readFileSync(join(process.cwd(), "public/markina-sw.js"), "utf8");
  // Não oferecer CacheStorage/localStorage no contexto: qualquer uso falha o teste.
  vm.runInNewContext(script, {
    self:{ addEventListener:(name:string, handler:(event:unknown) => void) => { handlers[name] = handler; }, location:{ origin:"https://example.test" } },
    URL, Response, fetch,
  });
  const respondWith = vi.fn();
  handlers.fetch({ request:{ url:"https://example.test/api/private-photo", method:"GET", mode:"navigate" }, respondWith });
  handlers.fetch({ request:{ url:"https://example.test/private-photo", method:"GET", mode:"cors" }, respondWith });
  expect(respondWith).not.toHaveBeenCalled();
  const request = { url:"https://example.test/gallery/private-id", method:"GET", mode:"navigate" };
  handlers.fetch({ request, respondWith });
  const response:Response = await respondWith.mock.calls[0][0];
  expect(fetch).toHaveBeenCalledWith(request);
  expect(response.headers.get("cache-control")).toBe("no-store");
  const html = await response.text();
  expect(html).toContain("Você está sem conexão");
  expect(html).not.toContain("private-id");
});

it("mantém botão global, sem duplicar os shells, e tokens de contraste", () => {
  const layout = readFileSync(join(process.cwd(), "app/layout.tsx"), "utf8");
  expect(layout).toContain("<InstallApp />{children}");
  const tokens = readFileSync(join(process.cwd(), "app/design-tokens.css"), "utf8");
  const luminance = (hex:string) => {
    const channels = hex.match(/\w\w/g)!.map((pair) => parseInt(pair,16)/255).map((v) => v <= .04045 ? v/12.92 : ((v+.055)/1.055)**2.4);
    return channels[0]*.2126 + channels[1]*.7152 + channels[2]*.0722;
  };
  for (const name of ["brand", "ink", "ink-muted", "info", "success", "warning", "danger"]) {
    const hex = tokens.match(new RegExp(`--mk-${name}: #([a-f0-9]{6})`))![1];
    expect(1.05/(luminance(hex)+.05), name).toBeGreaterThan(4.5);
  }
  const yellow = tokens.match(/--mk-action: #([a-f0-9]{6})/)![1];
  const actionInk = tokens.match(/--mk-action-ink: #([a-f0-9]{6})/)![1];
  expect((luminance(yellow)+.05)/(luminance(actionInk)+.05)).toBeGreaterThan(7);
  expect(manifest().theme_color).toBe(`#${yellow}`);
});
