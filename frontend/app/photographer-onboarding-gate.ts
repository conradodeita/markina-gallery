export const PHOTOGRAPHER_ONBOARDING_GATE_EVENT = "photographer-onboarding-required";

export function safePhotographerReturnPath(value: unknown): string | null {
  if (typeof value !== "string" || !value.startsWith("/admin/")
    || value.startsWith("//") || value.includes("\\") || /[?#\u0000-\u001f]/.test(value)) return null;
  let decoded = value;
  try { decoded = decodeURIComponent(value); } catch { return null; }
  if (decoded.split("/").some((segment) => segment === "." || segment === "..")
    || decoded.includes("\\") || /[\u0000-\u001f]/.test(decoded)) return null;
  return value;
}

export function notifyPhotographerOnboardingGate(detail: unknown) {
  if (typeof window === "undefined" || !detail || typeof detail !== "object") return false;
  const value = detail as { code?: unknown; settings_url?: unknown };
  if (value.code !== "photographer_onboarding_required" || value.settings_url !== "/admin/settings") return false;
  const returnTo = safePhotographerReturnPath(window.location.pathname) ?? "/admin";
  window.dispatchEvent(new CustomEvent(PHOTOGRAPHER_ONBOARDING_GATE_EVENT, { detail: { returnTo } }));
  return true;
}

export function photographerOnboardingSettingsHref(returnTo: unknown) {
  const safeReturnTo = safePhotographerReturnPath(returnTo);
  return safeReturnTo
    ? `/admin/settings?return_to=${encodeURIComponent(safeReturnTo)}#onboarding`
    : "/admin/settings#onboarding";
}
