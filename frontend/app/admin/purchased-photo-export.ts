import type { MouseEvent } from "react";

export function applyPurchasedPhotoExportTheme(event: MouseEvent<HTMLAnchorElement>) {
  const accent = window.getComputedStyle(document.documentElement).getPropertyValue("--mk-brand").trim();
  if (!/^#[\da-f]{6}$/i.test(accent)) return;
  const target = new URL(event.currentTarget.href);
  target.searchParams.set("highlight", accent);
  event.currentTarget.href = `${target.pathname}${target.search}${target.hash}`;
}
