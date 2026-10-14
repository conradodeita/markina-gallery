import { readFileSync } from "node:fs";
import { join } from "node:path";

import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("next/link", () => ({ default: ({ children, href }: { children: React.ReactNode; href: string }) => <a href={href}>{children}</a> }));

import { ConfirmDialog, MarkinaButton, MetricCard, PageHeading, StatusBadge, SystemState } from "./ui-kit";

describe("componentes visuais Markina", () => {
  it("comunica estado e variante de ação", () => {
    render(<><MarkinaButton variant="secondary">Voltar</MarkinaButton><StatusBadge tone="success">Liberada</StatusBadge><SystemState title="Sem galerias" detail="Aguarde a liberação." /></>);
    expect(screen.getByRole("button", { name: "Voltar" }).className).toContain("secondary");
    expect(screen.getByText("Liberada").className).toContain("success");
    expect(screen.getByRole("status").textContent).toContain("Sem galerias");
  });

  it("permite cancelar diálogo por Escape", () => {
    const onCancel = vi.fn();
    render(<ConfirmDialog open title="Liberar lote" detail="Esta ação não inclui novas fotos depois." confirmLabel="Liberar" onCancel={onCancel} onConfirm={vi.fn()} />);
    fireEvent.keyDown(window, { key: "Escape" });
    expect(onCancel).toHaveBeenCalledOnce();
  });

  it("mantém ações do diálogo alcançáveis em viewport de baixa altura", () => {
    const css = readFileSync(join(process.cwd(), "app", "globals.css"), "utf8");
    const backdropRule = css.match(/\.mk-dialog-backdrop\s*\{([^}]*)\}/)?.[1] ?? "";
    const dialogRule = css.match(/\.mk-dialog\s*\{([^}]*)\}/)?.[1] ?? "";

    expect(backdropRule).toContain("overflow-y:auto");
    expect(dialogRule).toMatch(/max-height:calc\(100dvh\s*-\s*48px\)/);
    expect(dialogRule).toContain("overflow-y:auto");
  });

  it("mantém hierarquia e dados operacionais no kit compartilhado", () => {
    render(<><PageHeading eyebrow="Operação" title="Pendências de hoje" detail="Acompanhe o que exige atenção." /><MetricCard label="Pagamentos" value={3} detail="Aguardando confirmação" tone="warning" /></>);
    expect(screen.getByRole("heading", { name: "Pendências de hoje" })).toBeTruthy();
    expect(screen.getByText("Pagamentos").closest("section")?.className).toContain("warning");
  });
});
