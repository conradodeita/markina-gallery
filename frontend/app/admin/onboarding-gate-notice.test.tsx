import { act, fireEvent, render, screen } from "@testing-library/react";
import { expect, it } from "vitest";

import { OnboardingGateNotice } from "./onboarding-gate-notice";
import { notifyPhotographerOnboardingGate } from "../photographer-onboarding-gate";

it("abre Configurações sem desmontar o fluxo original e oferece retorno interno", () => {
  window.history.replaceState({}, "", "/admin/credits?cpf=never-copy-this");
  render(<OnboardingGateNotice />);
  act(() => notifyPhotographerOnboardingGate({
    code: "photographer_onboarding_required", settings_url: "/admin/settings",
  }));

  expect(screen.getByRole("alert").textContent).toContain("tentar novamente");
  const link = screen.getByRole("link", { name: "Abrir Configurações" });
  expect(link.getAttribute("href")).toBe("/admin/settings?return_to=%2Fadmin%2Fcredits#onboarding");
  expect(link.getAttribute("target")).toBe("_blank");
  expect(link.getAttribute("rel")).toBe("noreferrer");
  fireEvent.click(screen.getByRole("button", { name: "Dispensar" }));
  expect(screen.queryByRole("alert")).toBeNull();
});
