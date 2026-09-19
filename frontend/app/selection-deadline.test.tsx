import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { SelectionDeadline, selectionTimeRemaining } from "./selection-deadline";

afterEach(() => vi.useRealTimers());
const now = Date.parse("2026-09-19T12:00:00Z");
describe("prazo autoritativo da seleção", () => {
  it.each([[2940, "2d 1h"], [90, "1h 30min"], [5, "5min"], [0.5, "Menos de 1 minuto"], [0, "Prazo de seleção expirado"], [-90, "Prazo de seleção expirado"]])("formata %s minutos sem negativos", (minutes, label) => {
    expect(selectionTimeRemaining(new Date(now + Number(minutes) * 60000).toISOString(), now)).toContain(label);
  });
  it("não inventa data ausente ou inválida", () => {
    const { rerender } = render(<SelectionDeadline expiresAt={null} />);
    expect(screen.queryByLabelText("Prazo para novas seleções")).toBeNull();
    rerender(<SelectionDeadline expiresAt="invalid" />);
    expect(screen.queryByLabelText("Prazo para novas seleções")).toBeNull();
  });
  it("atualiza por minuto, revalida no vencimento e refoco e aceita reabertura", async () => {
    vi.useFakeTimers(); vi.setSystemTime(now);
    const revalidate = vi.fn();
    const { rerender, unmount } = render(<SelectionDeadline expiresAt={new Date(now + 60000).toISOString()} onRevalidate={revalidate} />);
    await act(async () => {});
    expect(screen.getByText("1min para selecionar")).toBeTruthy();
    await act(async () => { vi.advanceTimersByTime(60000); });
    expect(screen.getByText("Prazo de seleção expirado")).toBeTruthy();
    expect(revalidate).toHaveBeenCalledTimes(1);
    await act(async () => { vi.advanceTimersByTime(60000); });
    expect(revalidate).toHaveBeenCalledTimes(1);
    fireEvent.focus(window);
    expect(revalidate).toHaveBeenCalledTimes(2);
    fireEvent(document, new Event("visibilitychange"));
    expect(revalidate).toHaveBeenCalledTimes(3);
    rerender(<SelectionDeadline expiresAt={new Date(now + 3600000).toISOString()} onRevalidate={revalidate} />);
    await act(async () => {});
    expect(screen.getByText("58min para selecionar")).toBeTruthy();
    unmount();
    expect(vi.getTimerCount()).toBe(0);
  });
});
