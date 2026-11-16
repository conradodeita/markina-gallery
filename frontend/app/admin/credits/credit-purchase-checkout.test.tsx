import { fireEvent, render, screen } from "@testing-library/react";
import { useState } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import CreditPurchaseCheckout, { type CreditPurchase } from "./credit-purchase-checkout";
import { PaymentRequestError, paymentRequest } from "../../library/mercadopago";

vi.mock("../../library/checkout/card-payment", () => ({
  default: ({ onSubmit }: {
    onSubmit(data: {
      token: string;
      payment_method_id: string;
      payer: { email: string; identification: { number: string } };
    }): void;
  }) => (
    <button type="button" onClick={() => onSubmit({
      token: "card-token",
      payment_method_id: "visa",
      payer: { email: "payer@example.test", identification: { number: "12345678901" } },
    })}>
      Enviar pagamento de cartão
    </button>
  ),
}));

vi.mock("../../library/mercadopago", async (importOriginal) => {
  const original = await importOriginal<typeof import("../../library/mercadopago")>();
  return { ...original, paymentRequest: vi.fn() };
});

const prepared: CreditPurchase = {
  id: "purchase-1",
  package_id: "package-1",
  package_name: "Pacote 40",
  credit_quantity: 40,
  total_cents: 4900,
  currency_code: "BRL",
  method: null,
  state: "prepared",
  active: true,
  public_key: "APP_USR-public-key",
  created_at: "2026-11-01T12:00:00Z",
};

function CheckoutHarness({ initial = prepared }: { initial?: CreditPurchase }) {
  const [purchase, setPurchase] = useState(initial);
  return <CreditPurchaseCheckout purchase={purchase} onClose={() => undefined} onUpdated={setPurchase} />;
}

const paymentRequestMock = vi.mocked(paymentRequest);

describe("checkout transparente de créditos", () => {
  beforeEach(() => paymentRequestMock.mockReset());
  afterEach(() => vi.unstubAllGlobals());

  function useSavedPayerAddress() {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({
      name: "Fotógrafo de teste", email: "photographer@example.test", identification_number: "52998224725",
      address: {
        zip_code: "01311000", street_name: "Avenida Paulista", street_number: "1000",
        neighborhood: "Bela Vista", city: "São Paulo", state: "SP", complement: "Apto 4",
      },
    }))));
  }

  it("envia PIX do Mercado Pago e exibe a resposta pendente", async () => {
    const pending: CreditPurchase = {
      ...prepared,
      method: "pix",
      state: "pending",
      pix_copy_paste: "000201-pix",
      pix_qr_code: "data:image/png;base64,qr",
    };
    paymentRequestMock.mockResolvedValueOnce(pending);
    useSavedPayerAddress();
    render(<CheckoutHarness />);

    expect(await screen.findByLabelText("CEP")).toHaveProperty("value", "01311000");
    fireEvent.click(screen.getByRole("radio", { name: "PIX Mercado Pago" }));
    fireEvent.change(screen.getByLabelText("E-mail para o pagamento"), {
      target: { value: "payer@example.test" },
    });
    fireEvent.change(screen.getByLabelText("CPF do pagador"), { target: { value: "12345678901" } });
    fireEvent.click(screen.getByRole("button", { name: "Gerar PIX de R$ 49,00" }));

    expect(await screen.findByLabelText("PIX copia e cola")).toHaveProperty("value", "000201-pix");
    expect(screen.getByRole("img", { name: "QR Code PIX Mercado Pago" })).toBeTruthy();
    expect(paymentRequestMock).toHaveBeenCalledWith(
      "/admin/credits/purchases/purchase-1/submit",
      {
        method: "pix", email: "payer@example.test", identification_number: "12345678901",
        payer_address: {
          zip_code: "01311000", street_name: "Avenida Paulista", street_number: "1000",
          neighborhood: "Bela Vista", city: "São Paulo", state: "SP", complement: "Apto 4",
        },
      },
    );
  });

  it("confirma cartão e informa que o saldo foi atualizado", async () => {
    const confirmed: CreditPurchase = { ...prepared, method: "credit_card", state: "confirmed" };
    paymentRequestMock.mockResolvedValueOnce(confirmed);
    useSavedPayerAddress();
    render(<CheckoutHarness />);

    expect(await screen.findByLabelText("CEP")).toHaveProperty("value", "01311000");
    fireEvent.click(screen.getByRole("button", { name: "Enviar pagamento de cartão" }));

    expect(await screen.findByText("Pagamento confirmado. Os créditos já foram adicionados à carteira.")).toBeTruthy();
    expect(paymentRequestMock).toHaveBeenCalledWith(
      "/admin/credits/purchases/purchase-1/submit",
      {
        method: "credit_card",
        token: "card-token",
        payment_method_id: "visa",
        email: "payer@example.test",
        identification_number: "12345678901",
        payer_address: {
          zip_code: "01311000", street_name: "Avenida Paulista", street_number: "1000",
          neighborhood: "Bela Vista", city: "São Paulo", state: "SP", complement: "Apto 4",
        },
      },
    );
  });

  it("preserva tentativa ambígua para conferência sem exibir novo envio", async () => {
    paymentRequestMock.mockRejectedValueOnce(new PaymentRequestError("Falha de rede", 503));
    useSavedPayerAddress();
    render(<CheckoutHarness />);

    expect(await screen.findByLabelText("CEP")).toHaveProperty("value", "01311000");
    fireEvent.click(screen.getByRole("button", { name: "Enviar pagamento de cartão" }));

    expect(await screen.findByRole("alert")).toHaveProperty(
      "textContent",
      expect.stringContaining("O envio pode ter sido recebido"),
    );
    expect(await screen.findByRole("button", { name: "Atualizar pagamento" })).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Enviar pagamento de cartão" })).toBeNull();
  });

  it("permite preencher o endereço nesta compra quando o perfil salvo não está disponível", async () => {
    const pending: CreditPurchase = { ...prepared, method: "pix", state: "pending" };
    paymentRequestMock.mockResolvedValueOnce(pending);
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(
      JSON.stringify({ detail: "Complete seu perfil antes da compra de créditos." }),
      { status: 409, headers: { "Content-Type": "application/json" } },
    )));
    render(<CheckoutHarness />);

    expect(await screen.findByText(/Não foi possível preencher os dados salvos/)).toBeTruthy();
    fireEvent.change(screen.getByLabelText("CEP"), { target: { value: "01311000" } });
    fireEvent.change(screen.getByLabelText("Estado"), { target: { value: "SP" } });
    fireEvent.change(screen.getByLabelText("Logradouro"), { target: { value: "Avenida Paulista" } });
    fireEvent.change(screen.getByLabelText("Número"), { target: { value: "1000" } });
    fireEvent.change(screen.getByLabelText("Bairro"), { target: { value: "Bela Vista" } });
    fireEvent.change(screen.getByLabelText("Cidade"), { target: { value: "São Paulo" } });
    fireEvent.click(screen.getByRole("radio", { name: "PIX Mercado Pago" }));
    fireEvent.change(screen.getByLabelText("E-mail para o pagamento"), {
      target: { value: "payer@example.test" },
    });
    fireEvent.change(screen.getByLabelText("CPF do pagador"), {
      target: { value: "12345678901" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Gerar PIX de R$ 49,00" }));

    expect(await screen.findByText("PIX Mercado Pago")).toBeTruthy();
    expect(paymentRequestMock).toHaveBeenCalledWith(
      "/admin/credits/purchases/purchase-1/submit",
      expect.objectContaining({
        method: "pix",
        payer_address: {
          zip_code: "01311000", street_name: "Avenida Paulista", street_number: "1000",
          neighborhood: "Bela Vista", city: "São Paulo", state: "SP", complement: "",
        },
      }),
    );
  });
});
