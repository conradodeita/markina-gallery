import { afterEach, expect, it, vi } from "vitest";
import { navigateToCardCheckout } from "./checkout-navigation";

afterEach(() => vi.unstubAllGlobals());

it("abre o checkout na mesma aba sem criar popup", () => {
  const assign = vi.fn(), open = vi.fn();
  vi.stubGlobal("window", { location: { assign }, open });
  navigateToCardCheckout("https://checkout.infinitepay.io/owner/invoice");
  expect(assign).toHaveBeenCalledExactlyOnceWith("https://checkout.infinitepay.io/owner/invoice");
  expect(open).not.toHaveBeenCalled();
});
