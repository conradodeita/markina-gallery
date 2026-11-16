import { afterEach, describe, expect, it } from "vitest";

import {
  notifyPhotographerOnboardingGate,
  photographerOnboardingSettingsHref,
  safePhotographerReturnPath,
} from "./photographer-onboarding-gate";

afterEach(() => window.history.replaceState({}, "", "/"));

describe("retorno seguro do gate de onboarding", () => {
  it("preserva somente a rota interna, sem consulta que possa conter dados digitados", () => {
    window.history.replaceState({}, "", "/admin/credits?package_id=synthetic&cpf=secret#checkout");
    let observed: unknown;
    window.addEventListener("photographer-onboarding-required", (event) => {
      observed = (event as CustomEvent).detail;
    }, { once: true });

    expect(notifyPhotographerOnboardingGate({
      code: "photographer_onboarding_required", settings_url: "/admin/settings",
    })).toBe(true);
    expect(observed).toEqual({ returnTo: "/admin/credits" });
    expect(photographerOnboardingSettingsHref((observed as { returnTo: string }).returnTo))
      .toBe("/admin/settings?return_to=%2Fadmin%2Fcredits#onboarding");
  });

  it.each(["//evil.example", "/admin/../login", "/admin/settings?cpf=secret", "/admin\\settings"])(
    "recusa retorno não seguro %s",
    (path) => expect(safePhotographerReturnPath(path)).toBeNull(),
  );
});
