import { describe, expect, it } from "vitest";

import { clientMediaStatusMessage, folderAccessStatusLabel, mediaArchiveStatusLabel } from "./media-archive-status";

describe("estado da mídia de arquivo frio", () => {
  it("prioriza arquivo e expiração sobre a publicação das prévias", () => {
    const folder = { status: "released", access_expires_at: "2026-11-01T00:00:00Z" };
    const at = Date.parse("2026-11-09T00:00:00Z");
    expect(folderAccessStatusLabel(folder, at)).toBe("Prazo de acesso encerrado");
    expect(folderAccessStatusLabel({ ...folder, media_state: "archived" }, at)).toBe("Arquivada no arquivo frio");
    expect(folderAccessStatusLabel({ status: "released" }, at)).toBe("Disponível");
  });
  it("distingue arquivo concluído de recuperação em curso", () => {
    expect(mediaArchiveStatusLabel("archived")).toBe("Arquivada no arquivo frio");
    expect(clientMediaStatusMessage("archived")).toContain("Sua seleção continua salva");
    expect(mediaArchiveStatusLabel("restoring")).toBe("Recuperação em andamento");
    expect(clientMediaStatusMessage("restoring")).toContain("iniciou a recuperação");
  });

  it("mantém o estado disponível sem aviso e descreve uma conferência necessária", () => {
    expect(clientMediaStatusMessage("available")).toBeNull();
    expect(mediaArchiveStatusLabel("reconciliation_required")).toBe("Disponibilidade em conferência");
    expect(clientMediaStatusMessage("reconciliation_required")).toContain("em conferência");
  });
});
