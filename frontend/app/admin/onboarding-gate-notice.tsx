"use client";

import { useEffect, useState } from "react";
import {
  PHOTOGRAPHER_ONBOARDING_GATE_EVENT,
  photographerOnboardingSettingsHref,
  safePhotographerReturnPath,
} from "../photographer-onboarding-gate";

export function OnboardingGateNotice() {
  const [returnTo, setReturnTo] = useState<string | null>(null);

  useEffect(() => {
    function onGate(event: Event) {
      const detail = (event as CustomEvent<{ returnTo?: unknown }>).detail;
      setReturnTo(safePhotographerReturnPath(detail?.returnTo) ?? "/admin");
    }
    window.addEventListener(PHOTOGRAPHER_ONBOARDING_GATE_EVENT, onGate);
    return () => window.removeEventListener(PHOTOGRAPHER_ONBOARDING_GATE_EVENT, onGate);
  }, []);

  if (!returnTo) return null;
  return <aside className="onboarding-gate-notice" role="alert">
    <p>Esta ação ainda não foi concluída. Complete os itens pendentes em Configurações e depois volte para tentar novamente.</p>
    <a className="mk-button mk-button--secondary"
      href={photographerOnboardingSettingsHref(returnTo)} target="_blank" rel="noreferrer">
      Abrir Configurações
    </a>
    <button type="button" className="link-button" onClick={() => setReturnTo(null)}>Dispensar</button>
  </aside>;
}
