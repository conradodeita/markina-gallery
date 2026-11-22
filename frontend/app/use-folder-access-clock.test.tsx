import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { folderAccessStatusLabel } from "./media-archive-status";
import { useFolderAccessClock } from "./use-folder-access-clock";

const startsAt = Date.parse("2026-11-13T12:00:00.000Z");
const folder = {
  status: "released",
  access_expires_at: new Date(startsAt + 10_000).toISOString(),
};

function StatusProbe() {
  const observedAt = useFolderAccessClock([folder]);
  return <p>{folderAccessStatusLabel(folder, observedAt)}</p>;
}

function LongDeadlineProbe() {
  const observedAt = useFolderAccessClock([{ access_expires_at: new Date(startsAt + 30 * 24 * 60 * 60 * 1000).toISOString() }]);
  return <p data-testid="observed-at">{observedAt}</p>;
}

afterEach(() => {
  vi.useRealTimers();
});

it("atualiza o rótulo quando o prazo vence com a tela aberta", () => {
  vi.useFakeTimers();
  vi.setSystemTime(startsAt);
  render(<StatusProbe />);

  expect(screen.getByText("Disponível")).toBeTruthy();
  act(() => vi.advanceTimersByTime(10_001));
  expect(screen.getByText("Prazo de acesso encerrado")).toBeTruthy();
});

it("reavalia o prazo quando a tela volta ao foco após ficar em segundo plano", () => {
  vi.useFakeTimers();
  vi.setSystemTime(startsAt);
  render(<StatusProbe />);

  expect(screen.getByText("Disponível")).toBeTruthy();
  vi.setSystemTime(startsAt + 11_000);
  fireEvent.focus(window);
  expect(screen.getByText("Prazo de acesso encerrado")).toBeTruthy();
});

it("não agenda timers quase imediatos para prazos acima do limite do navegador", () => {
  vi.useFakeTimers();
  vi.setSystemTime(startsAt);
  render(<LongDeadlineProbe />);

  expect(screen.getByTestId("observed-at").textContent).toBe(String(startsAt));
  act(() => vi.advanceTimersByTime(1));
  expect(screen.getByTestId("observed-at").textContent).toBe(String(startsAt));
});
