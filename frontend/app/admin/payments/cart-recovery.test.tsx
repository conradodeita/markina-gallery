import { fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { CartRecoveryActions } from "./cart-recovery";

const status = { can_reopen: true, revision: 2, reopened_at: null };
const plan = { payment_id: "purchase-123", revision: 2, fingerprint: "a".repeat(64), restored_quantity: 3,
  quantity: 4, total_cents: 2800, previous_total_cents: 2100, card_available: true, pix_available: true };
const response = (value: object, code = 200) => Promise.resolve(new Response(JSON.stringify(value), { status: code }));
const props = { paymentId: "purchase-123", state: "verification_required", status, clientName: "Cliente Sintética" };
beforeEach(() => {
  HTMLDialogElement.prototype.showModal = vi.fn(function (this: HTMLDialogElement) { this.open = true; });
  HTMLDialogElement.prototype.close = vi.fn(function (this: HTMLDialogElement) { this.open = false; });
});
afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals(); document.body.style.overflow = ""; });

async function open() {
  const trigger = screen.getByRole("button", { name: "Reabrir carrinho" });
  trigger.focus(); fireEvent.click(trigger);
  await screen.findByText(/3 foto\(s\) da compra voltarão selecionadas/);
  return screen.getByRole("dialog", { name: "Reabrir carrinho" });
}

it("mostra a prévia integral e cancelar não confirma nem muda a compra", async () => {
  const fetcher = vi.fn<(path: string, options?: RequestInit) => Promise<Response>>(() => response(plan));
  const refresh = vi.fn();
  vi.stubGlobal("fetch", fetcher);
  render(<CartRecoveryActions {...props} onRefresh={refresh} />);
  const dialog = await open();
  expect(within(dialog).getByText(/4 foto\(s\).*novas seleções/).textContent).toContain("28,00");
  expect(within(dialog).getByText(/Meios disponíveis/).textContent).toContain("Cartão de crédito e PIX");
  expect(screen.getByRole("button", { name: "Confirmar e reabrir carrinho" })).toHaveProperty("disabled", true);
  expect(fetcher).toHaveBeenCalledTimes(1);
  expect(JSON.parse(String(fetcher.mock.calls[0]?.[1]?.body))).toEqual({ expected_revision: 2 });
  fireEvent.click(within(dialog).getByRole("button", { name: "Cancelar" }));
  expect(screen.queryByRole("dialog")).toBeNull();
  expect(document.activeElement).toBe(screen.getByRole("button", { name: "Reabrir carrinho" }));
  expect(document.body.style.overflow).toBe("");
  expect(fetcher).toHaveBeenCalledTimes(1);
  expect(refresh).not.toHaveBeenCalled();
});

it("confirma a compra uma vez, preserva o motivo e bloqueia duplo clique e Escape durante envio", async () => {
  let finish: (value: Response) => void = () => {};
  const fetcher = vi.fn<(path: string, options?: RequestInit) => Promise<Response>>((path) => path.endsWith("/preview") ? response(plan)
    : new Promise<Response>((resolve) => { finish = resolve; }));
  const refresh = vi.fn(async () => {});
  vi.stubGlobal("fetch", fetcher);
  render(<CartRecoveryActions {...props} onRefresh={refresh} />);
  const dialog = await open();
  fireEvent.change(screen.getByLabelText("Motivo da reabertura"), { target: { value: "Cliente quer retomar as fotos" } });
  fireEvent.click(screen.getByRole("checkbox"));
  const button = screen.getByRole("button", { name: "Confirmar e reabrir carrinho" });
  fireEvent.click(button); fireEvent.click(button);
  fireEvent(dialog, new Event("cancel", { cancelable: true }));
  expect(screen.getByRole("dialog")).toBeTruthy();
  expect(screen.getByRole("button", { name: "Cancelar" })).toHaveProperty("disabled", true);
  expect(fetcher.mock.calls.filter(([path]) => !path.endsWith("/preview"))).toHaveLength(1);
  const body = JSON.parse(String(fetcher.mock.calls[1][1]?.body));
  expect(body).toMatchObject({ expected_revision: 2, expected_fingerprint: plan.fingerprint,
    reason: "Cliente quer retomar as fotos", acknowledge_remote_checkout: true });
  expect(body.idempotency_key).toMatch(/^[0-9a-f-]{36}$/);
  finish(new Response(JSON.stringify({ already_reopened: false })));
  expect(await screen.findByText(/Carrinho reaberto/)).toBeTruthy();
  expect(refresh).toHaveBeenCalledOnce();
  expect(screen.queryByRole("button", { name: "Reabrir carrinho" })).toBeNull();
});

it("repete a mesma decisão após falha de rede sem gerar outra chave", async () => {
  let tries = 0;
  const bodies: string[] = [];
  vi.stubGlobal("fetch", vi.fn((path: string, options?: RequestInit) => {
    if (path.endsWith("/preview")) return response(plan);
    bodies.push(String(options?.body));
    return ++tries === 1 ? Promise.reject(new Error("Rede indisponível")) : response({ already_reopened: true });
  }));
  render(<CartRecoveryActions {...props} onRefresh={async () => {}} />);
  await open(); fireEvent.click(screen.getByRole("checkbox"));
  fireEvent.click(screen.getByRole("button", { name: "Confirmar e reabrir carrinho" }));
  expect(await screen.findByRole("alert")).toHaveProperty("textContent", "Rede indisponível");
  expect(screen.getByLabelText("Motivo da reabertura")).toHaveProperty("disabled", true);
  fireEvent.click(screen.getByRole("button", { name: "Confirmar e reabrir carrinho" }));
  await screen.findByText(/Carrinho reaberto/);
  expect(bodies).toHaveLength(2);
  expect(bodies[0]).toBe(bodies[1]);
});

it("conflito invalida a prévia e atualiza o painel sem reenviar", async () => {
  const refresh = vi.fn(async () => {});
  vi.stubGlobal("fetch", vi.fn((path: string) => path.endsWith("/preview") ? response(plan)
    : response({ detail: "A compra mudou. Atualize o painel." }, 409)));
  render(<CartRecoveryActions {...props} onRefresh={refresh} />);
  await open(); fireEvent.click(screen.getByRole("checkbox"));
  fireEvent.click(screen.getByRole("button", { name: "Confirmar e reabrir carrinho" }));
  expect(await screen.findByRole("alert")).toHaveProperty("textContent", "A compra mudou. Atualize o painel.");
  expect(screen.queryByRole("button", { name: "Confirmar e reabrir carrinho" })).toBeNull();
  expect(refresh).toHaveBeenCalledOnce();
});

it("falha na prévia mantém somente a opção de fechar", async () => {
  const fetcher = vi.fn(() => response({ detail: "As fotos não estão todas disponíveis." }, 409));
  vi.stubGlobal("fetch", fetcher);
  render(<CartRecoveryActions {...props} onRefresh={async () => {}} />);
  fireEvent.click(screen.getByRole("button", { name: "Reabrir carrinho" }));
  expect(await screen.findByRole("alert")).toHaveProperty("textContent", "As fotos não estão todas disponíveis.");
  expect(screen.queryByRole("button", { name: "Confirmar e reabrir carrinho" })).toBeNull();
  fireEvent(screen.getByRole("dialog"), new Event("cancel", { cancelable: true }));
  expect(screen.queryByRole("dialog")).toBeNull();
  expect(fetcher).toHaveBeenCalledOnce();
});

it.each(["confirmed", "failed_before_issue", "exception", "hold"])("não oferece ação para %s", (state) => {
  render(<CartRecoveryActions {...props} state={state} onRefresh={async () => {}} />);
  expect(screen.queryByRole("button", { name: "Reabrir carrinho" })).toBeNull();
});

it("reconhece recuperação já registrada e capacidade recusada", () => {
  const view = render(<CartRecoveryActions {...props} status={{ ...status, can_reopen: false }} onRefresh={async () => {}} />);
  expect(screen.queryByRole("button")).toBeNull();
  view.rerender(<CartRecoveryActions {...props} status={{ ...status, can_reopen: false, reopened_at: "2026-10-21T14:00:00Z" }} onRefresh={async () => {}} />);
  expect(screen.getByText(/Carrinho reaberto/)).toBeTruthy();
  expect(screen.queryByRole("button")).toBeNull();
});
