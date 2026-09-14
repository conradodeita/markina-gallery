import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { BrandLogo } from "./brand-logo";
import { PRODUCT_NAME } from "./product-brand";

afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals(); });

it("exibe arte configurada uma vez, sem duplicar o nome", () => {
  render(<BrandLogo src="/branding/logo" />);
  expect(screen.getByRole("img",{name:PRODUCT_NAME}).getAttribute("src")).toBe("/api/branding/logo");
  expect(screen.queryByText(PRODUCT_NAME)).toBeNull();
});

it("usa texto acessível sem arte ou quando ela falha", () => {
  const {rerender}=render(<BrandLogo src={null} />);
  expect(screen.getByText(PRODUCT_NAME)).toBeTruthy();
  rerender(<BrandLogo src="/branding/logo" />);
  fireEvent.error(screen.getByRole("img"));
  expect(screen.getByText(PRODUCT_NAME)).toBeTruthy();
});

it("busca branding em segundo plano sem bloquear navegação e recusa URL externa", async () => {
  vi.stubGlobal("fetch",vi.fn().mockResolvedValue(new Response(JSON.stringify({logo_url:"/branding/logo"}))));
  const {rerender}=render(<BrandLogo />);
  expect(screen.getByText(PRODUCT_NAME)).toBeTruthy();
  expect(await screen.findByRole("img",{name:PRODUCT_NAME})).toBeTruthy();
  rerender(<BrandLogo src="https://example.test/logo.png" />);
  expect(screen.queryByRole("img")).toBeNull();
  expect(screen.getByText(PRODUCT_NAME)).toBeTruthy();
});
