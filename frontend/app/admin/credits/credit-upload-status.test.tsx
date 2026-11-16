import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { useState } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { useCreditUploadStatus } from "./credit-upload-status";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

const photoId = "photo-asset-test-001";

function UploadStatusHarness() {
  const creditUpload = useCreditUploadStatus(false);
  const [readStatus, setReadStatus] = useState("pending");
  const photo = creditUpload.items.find((item) => item.photoId === photoId);

  return <>
    <button type="button" onClick={() => {
      void creditUpload.refreshPhoto(photoId, "photo.jpg").then(setReadStatus);
    }}>Refresh</button>
    <button type="button" onClick={() => creditUpload.startPhoto(photoId, "photo.jpg")}>Start</button>
    <span data-testid="photo-status">{photo?.status ?? "none"}</span>
    <span data-testid="read-status">{readStatus}</span>
  </>;
}

function jsonResponse(body: unknown) {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}

describe("estado de créditos por foto", () => {
  it("ignora a resposta da consulta anterior quando uma nova tentativa já começou", async () => {
    let resolveRead: ((response: Response) => void) | undefined;
    vi.stubGlobal("fetch", vi.fn(() => new Promise<Response>((resolve) => {
      resolveRead = resolve;
    })));
    render(<UploadStatusHarness />);

    fireEvent.click(screen.getByRole("button", { name: "Refresh" }));
    await waitFor(() => expect(fetch).toHaveBeenCalledTimes(1));

    fireEvent.click(screen.getByRole("button", { name: "Start" }));
    expect(screen.getByTestId("photo-status").textContent).toBe("uploading");

    await act(async () => {
      resolveRead?.(jsonResponse({
        wallet: {
          mode: "finite",
          available_credits: 2,
          reserved_credits: 0,
          pending_operations: 0,
          as_of: "2026-11-14T12:00:00Z",
        },
        operation: { status: "released" },
      }));
    });

    await waitFor(() => expect(screen.getByTestId("read-status").textContent).toBe("confirmation_pending"));
    expect(screen.getByTestId("photo-status").textContent).toBe("uploading");
  });
});
